"""Validate S7-S12 outputs: category map, book-level fields, authors, works and the catalogue.

Usage:  python -m scripts.clean.validate_s7_s12
Output: docs/reports/validation-s7-s12.md, and exit code 1 if any hard check fails.
"""
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / "docs" / "reports" / "validation-s7-s12.md"
GENRES = {"detective", "thriller", "spy", "crime", "horror", "supernatural", "sci_fi", "fantasy", "adventure",
          "romance", "family_drama", "social", "historical", "liberation_war", "humor_satire", "psychological",
          "mythology"}                                     # docs/04-tag-vocabulary.md
FORMATS = {"novel", "novella", "short_story_collection", "poetry", "drama", "nonfiction", "memoir", "comics"}
ORIGINS = {"bangladesh", "west_bengal", "translated", "english_language"}


def main():
    cmap = pd.read_csv(ROOT / "data" / "mappings" / "category_map.csv", dtype={"category_id": str}).fillna("")
    books = pd.read_parquet(ROOT / "data" / "interim" / "rokomari_books_s8.parquet")
    authors = pd.read_parquet(ROOT / "data" / "interim" / "authors.parquet")
    works = pd.read_parquet(ROOT / "data" / "processed" / "works.parquet")
    editions = pd.read_parquet(ROOT / "data" / "processed" / "editions.parquet")
    results = []

    def check(kind, name, passed, detail=""):
        results.append((kind, name, bool(passed), detail))

    # --- S7 category map ---
    check("hard", "every category has an action",
          cmap.action.isin(["map", "exclude", "ignore", "unknown"]).all())
    mapped = cmap[cmap.action == "map"]
    history = mapped[mapped.category_name.str.contains(r"(?<![A-Za-z])History(?![A-Za-z])", regex=True)
                     & ~mapped.category_name.str.contains("Historical")]
    check("hard", "no 'History' category is mapped as fiction (the story ⊂ History bug)", history.empty,
          f"{history.category_name.tolist()[:5]}")
    bad_words = mapped[mapped.category_name.str.contains(r"Artificial Intelligence|Kindergarten|Non-?Fiction", regex=True)]
    check("hard", "known false positives are not mapped (AI & Robotics, Kindergarten, Non-Fiction)",
          bad_words.empty, f"{bad_words.category_name.tolist()[:5]}")
    hints = {h for s in mapped.genre_hints for h in s.split("|") if h}
    check("hard", "genre hints use only the tag vocabulary", hints <= GENRES, f"{sorted(hints - GENRES)}")
    check("hard", "formats use only the vocabulary", set(mapped.format) - {""} <= FORMATS,
          f"{sorted(set(mapped.format) - {''} - FORMATS)}")

    # --- S8 book level ---
    check("hard", "book_id unique and complete (127,302)", books.book_id.is_unique and len(books) == 127_302,
          f"{len(books):,}")
    check("hard", "origin values are from the allowed set", books.origin.isin(ORIGINS).all())
    check("hard", "English-language books have origin english_language",
          (books.origin[books.language == "en"] == "english_language").all())
    check("hard", "every fiction book has a mapped category",
          books.category_actions[books.is_fiction].fillna("").str.contains("map").all())

    # --- S9-S10 authors ---
    linked = authors[authors.wikidata_qid.notna()]
    check("hard", "one row per Rokomari author id", authors.rokomari_author_id.is_unique, f"{len(authors):,}")
    check("hard", "linked authors all passed the evidence rules (exact key, fiction author, unique key)",
          (linked.match_method == "exact_key").all() and linked.has_fiction.all() and (linked.same_key_count == 1).all())
    check("hard", "no organisation is linked to a Wikidata person", (linked.author_type == "person").all())
    check("hard", "author_id is au_<QID> for every linked author",
          (linked.author_id == "au_" + linked.wikidata_qid).all())

    # --- S11 works ---
    check("hard", "work_id unique", works.work_id.is_unique)
    check("hard", "every edition belongs to exactly one work",
          editions.book_id.is_unique and set(editions.work_id) == set(works.work_id)
          and works.n_editions.sum() == len(editions), f"{works.n_editions.sum():,} vs {len(editions):,}")
    multi = editions[editions.work_id.isin(works.work_id[works.n_editions > 1])]
    g = multi.groupby("work_id")
    title_key = lambda t: re.sub(r"\s+", " ", re.sub(r"[\"'“”‘’.,:;!?()\[\]\-–—_/]", " ", (t or "").lower())).strip()
    same_title = g.title_clean.agg(lambda s: s.map(title_key).nunique() == 1).all()
    same_author = g.main_author_id.agg(lambda s: s.notna().all() and s.nunique() == 1).all()
    check("hard", "merged editions share one title key and one known main author", same_title and same_author)
    check("hard", "no edition without a known author is merged",
          multi.main_author_id.notna().all(), f"{multi.main_author_id.isna().sum()}")
    wh = {h for hs in works.genre_hints for h in hs}
    check("hard", "work genre hints use only the vocabulary", wh <= GENRES)

    # --- S12 catalogue ---
    cat = works[works.in_catalogue]
    check("hard", "in_catalogue ⇔ no exclude reasons",
          (works.in_catalogue == (works.exclude_reasons.str.len() == 0)).all())
    check("hard", "catalogue works are fiction, Bangla, not bundles, with a usable summary",
          cat.is_fiction.all() and (cat.language == "bn").all() and (~cat.is_bundle).all() and cat.summary_usable.all())
    check("hard", "catalogue works have a title and a summary of ≥200 chars",
          cat.title_bn.notna().all() and (cat.summary.fillna("").str.len() >= 200).all())
    check("hard", "catalogue origins are Bangladeshi, West Bengal or translated",
          cat.origin.isin({"bangladesh", "west_bengal", "translated"}).all(), f"{cat.origin.value_counts().to_dict()}")

    # --- soft: measured by hand, recorded here so the numbers stay visible ---
    check("soft", "Wikidata link precision, hand-checked random sample of 40 (2026-09-26)", True,
          "37 correct, 3 unverifiable, 0 wrong (first version: ~28/40 correct → rules tightened)")
    check("soft", "catalogue works whose origin is a low-confidence default", True,
          f"{(cat.origin_confidence == 'low').sum():,} of {len(cat):,}")
    check("soft", "catalogue works with no format (mixed or unknown category)", True,
          f"{cat.format.isna().sum():,} of {len(cat):,}")
    check("soft", "series issues differing only by subtitle can still merge (e.g. রোমাঞ্চ)", True,
          "not detectable from titles; URL-slug volume numbers catch the numbered cases")

    hard = [r for r in results if r[0] == "hard"]
    passed = sum(r[2] for r in hard)
    lines = ["# Validation report: S7–S12", "", "Generated by `python -m scripts.clean.validate_s7_s12`.", "",
             "| Kind | Check | Result | Detail |", "|---|---|---|---|"]
    for kind, name, ok, detail in results:
        mark = ("✅ pass" if ok else "❌ FAIL") if kind == "hard" else "ℹ️"
        lines.append(f"| {kind} | {name} | {mark} | {detail} |")
    lines += ["", f"**{passed} of {len(hard)} hard checks passed.**"]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[4:]))
    sys.exit(0 if passed == len(hard) else 1)


if __name__ == "__main__":
    main()
