"""S9-S10 of docs/10-cleaning-spec.md: clean author names, build the author table, link to Wikidata.

Usage:  python -m scripts.clean.authors
Input:  data/raw/rokomaribg/{author,book_to_author}.json.gz, data/raw/wikidata/*/authors.json
Output: data/interim/authors.parquet   (one row per Rokomari author_id, with our author_id)
        docs/reports/cleaning-s9-s10.md

Linking rule: a Rokomari author of at least one fiction book is linked only when its matching key
equals the key of exactly one Wikidata person's label or (non-truncated) alias, and no other Rokomari
author has the same key. Keys with several Wikidata candidates are recorded as
ambiguous and left unlinked (a wrong link is worse than a missing one). Rokomari IDs are merged into
one author only when they link to the same Wikidata person, never on the name alone.
"""
import datetime
import gzip
import json
from collections import defaultdict
from pathlib import Path

import pandas as pd

from scripts.clean import names as N
from scripts.clean import text as T

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "interim" / "authors.parquet"
BOOKS = ROOT / "data" / "interim" / "rokomari_books_s8.parquet"
REPORT = ROOT / "docs" / "reports" / "cleaning-s9-s10.md"
PD_YEARS = 60  # Bangladesh copyright term: life + 60 (to verify against the current Act)


def load_json_gz(path):
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        return json.load(fh)


def load_wikidata():
    path = sorted((RAW / "wikidata").glob("*/authors.json"))[-1]
    rows = json.loads(path.read_text(encoding="utf-8"))["results"]["bindings"]
    g = lambda r, k: r.get(k, {}).get("value", "")
    people = []
    for r in rows:
        year = lambda v: int(v[:4]) if v[:4].isdigit() else None
        people.append({
            "qid": g(r, "person").rsplit("/", 1)[-1],
            "wd_label_bn": g(r, "bnLabel") or None,
            "wd_label_en": g(r, "enLabel") or None,
            "wd_aliases_bn": [a for a in g(r, "bnAliases").split("|") if a],
            "wd_aliases_en": [a for a in g(r, "enAliases").split("|") if a],
            "birth_year": year(g(r, "birthDate")),
            "death_year": year(g(r, "deathDate")),
            "wd_countries": g(r, "countries") or None,
        })
    return pd.DataFrame(people), path.relative_to(ROOT).as_posix()


def wikidata_index(wd):
    """Matching key -> set of QIDs, from Bangla/English labels and aliases.

    Aliases that are only a truncation of the label are skipped: Wikidata lists "ফয়েজ আহমদ" as an alias
    of Faiz Ahmad Taiyeb (b. 1982), which collides with the journalist Foyez Ahmad. A real pen name
    (বিদ্যুৎ মিত্র for Qazi Anwar Hussain) shares no words with the label and is kept.
    """
    index = defaultdict(set)
    for r in wd.itertuples():
        for label, aliases in ((r.wd_label_bn, r.wd_aliases_bn), (r.wd_label_en, r.wd_aliases_en)):
            label_key = N.name_key(label) if label else None
            if label_key:
                index[label_key].add(r.qid)
            label_words = set((label_key or "").split())
            for alias in aliases:
                key = N.name_key(alias)
                if key and not set(key.split()) <= label_words:
                    index[key].add(r.qid)
    return index


def country_origin(countries):
    """Wikidata citizenship → literary origin. "British Raj" alone (authors who died before 1947:
    Tagore, Mir Mosharraf Hossain) says nothing about today's border, so it gives no signal."""
    parts = set(countries.split("|")) if isinstance(countries, str) else set()
    if parts & {"Bangladesh", "East Pakistan", "Pakistan"}:
        return "bangladesh"
    if parts & {"India", "Dominion of India"}:
        return "west_bengal"
    return None


def main():
    raw = pd.DataFrame(load_json_gz(RAW / "rokomaribg" / "author.json.gz"))
    links = pd.DataFrame(load_json_gz(RAW / "rokomaribg" / "book_to_author.json.gz")).drop_duplicates()
    raw["book_count"] = raw.author_id.map(links.groupby("author_id").size()).fillna(0).astype(int)

    parsed = pd.DataFrame([N.parse_author(n) for n in raw.author], index=raw.index)
    a = pd.concat([raw[["author_id", "author", "bio", "follower_count", "book_count"]], parsed], axis=1)
    a = a.rename(columns={"author_id": "rokomari_author_id", "author": "name_raw"})
    a["bio_bn"] = a.bio.map(T.clean_text)
    a["same_key_count"] = a.groupby("name_key").rokomari_author_id.transform("size")

    wd, wd_path = load_wikidata()
    index = wikidata_index(wd)

    # Only authors of catalogue (fiction) books are linked: a name match is weak evidence, and outside
    # fiction most matches were textbook authors sharing a common name with a Wikidata writer.
    books = pd.read_parquet(BOOKS, columns=["book_id", "is_fiction"]).astype({"book_id": str})
    fiction_ids = set(books.book_id[books.is_fiction])
    links_s = links.astype(str)
    fiction_authors = set(links_s.author_id[links_s.book_id.isin(fiction_ids)])
    a["has_fiction"] = a.rokomari_author_id.astype(str).isin(fiction_authors)

    def link(row):
        if row.author_type != "person" or not row.name_key:
            return None, "not_person" if row.author_type != "person" else "no_key", 0
        if not row.has_fiction:
            return None, "not_fiction_author", 0
        qids = index.get(row.name_key, set())
        if not qids:
            return None, "no_match", 0
        if len(qids) > 1:
            return None, "ambiguous_wikidata", len(qids)
        if row.same_key_count > 1:
            # Several Rokomari authors share this name; we can't tell which one Wikidata means.
            return None, "ambiguous_rokomari", 1
        return next(iter(qids)), "exact_key", 1

    res = a.apply(link, axis=1, result_type="expand")
    a["wikidata_qid"], a["match_method"], a["candidates"] = res[0], res[1], res[2]
    a = a.merge(wd, left_on="wikidata_qid", right_on="qid", how="left").drop(columns=["qid"])
    a["origin_hint"] = a.wd_countries.map(country_origin)
    this_year = datetime.date.today().year
    a["public_domain_bd"] = a.death_year.map(lambda y: bool(y) and y + PD_YEARS < this_year if pd.notna(y) else False)
    # Our author_id: one per Wikidata person (merging Rokomari duplicates), else one per Rokomari id.
    a["author_id"] = a.apply(lambda r: f"au_{r.wikidata_qid}" if r.wikidata_qid else f"au_rk{r.rokomari_author_id}",
                             axis=1)
    a["wikidata_source"] = wd_path
    OUT.parent.mkdir(parents=True, exist_ok=True)
    a.drop(columns=["bio"]).to_parquet(OUT, index=False)

    persons = a[a.author_type == "person"]
    linked = a[a.wikidata_qid.notna()]
    total_links = int(a.book_count.sum())
    lines = ["# Cleaning report: S9–S10 (authors, Wikidata)", "",
             "Generated by `python -m scripts.clean.authors`.", "",
             f"- Rokomari author ids: {len(a):,} ({(a.author_type == 'organisation').sum():,} organisations)",
             f"- With aliases (pen names/nicknames in brackets): {(a.aliases.str.len() > 0).sum():,}; "
             f"honorifics: {(a.honorifics.str.len() > 0).sum():,}; rank titles: {(a.rank_titles.str.len() > 0).sum():,}",
             f"- Matching keys shared by more than one Rokomari id: {(a.same_key_count > 1).sum():,} ids "
             f"(not merged on name alone)",
             f"- Wikidata people indexed: {len(wd):,} ({len(index):,} distinct keys)",
             "", "## Linking", "| method | Rokomari ids | book links |", "|---|---|---|"]
    for m, d in a.groupby("match_method"):
        lines.append(f"| {m} | {len(d):,} | {int(d.book_count.sum()):,} |")
    lines += ["",
              f"- **Linked: {len(linked):,} Rokomari ids → {linked.wikidata_qid.nunique():,} Wikidata people, "
              f"covering {int(linked.book_count.sum()):,} of {total_links:,} book–author links "
              f"({linked.book_count.sum() / total_links:.1%}).**",
              f"- Rokomari ids merged because they link to the same person: "
              f"{int((linked.groupby('wikidata_qid').size() > 1).sum()):,} people with 2+ ids",
              f"- Our author table: {a.author_id.nunique():,} authors"]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
