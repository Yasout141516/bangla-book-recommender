"""S11-S12 of docs/10-cleaning-spec.md: group editions into works, then mark the catalogue.

Usage:  python -m scripts.clean.works
Input:  data/interim/rokomari_books_s8.parquet, data/interim/authors.parquet,
        data/raw/rokomaribg/book_to_author.json.gz
Output: data/processed/{works,editions,authors}.parquet, docs/reports/cleaning-s11-s12.md

Work key = normalised title + our author_id + volume. The volume is part of the key so that
volume 1 and volume 2 of a series stay separate works; collected-works words (সমগ্র, রচনাবলী) stay
in the title so a collection is never merged with a single book. Nothing is deleted: every work
gets in_catalogue and, if excluded, the reasons.
"""
import gzip
import json
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
BOOKS = ROOT / "data" / "interim" / "rokomari_books_s8.parquet"
AUTHORS = ROOT / "data" / "interim" / "authors.parquet"
LINKS = ROOT / "data" / "raw" / "rokomaribg" / "book_to_author.json.gz"
OUT = ROOT / "data" / "processed"
REPORT = ROOT / "docs" / "reports" / "cleaning-s11-s12.md"

SUMMARY_RANK = {"flap": 0, "blurb": 1, "summary": 2, "excerpt": 3}
CONFIDENCE_RANK = {"high": 0, "medium": 1, "low": 2}
AUDIENCE_ORDER = ["children", "teen"]
PLACEHOLDER_TITLES = {"book", "books", "বই", "untitled", "n/a"}


def title_key(title):
    """Matching key for a cleaned title: lowercase, punctuation and spacing removed."""
    t = (title or "").lower()
    t = re.sub(r"[\"'“”‘’.,:;!?()\[\]\-–—_/]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def main():
    books = pd.read_parquet(BOOKS)
    books["book_id"] = books.book_id.astype(str)
    authors = pd.read_parquet(AUTHORS)
    authors["rokomari_author_id"] = authors.rokomari_author_id.astype(str)
    with gzip.open(LINKS, "rt", encoding="utf-8") as fh:
        links = pd.DataFrame(json.load(fh)).drop_duplicates().astype(str)

    # Our author ids per book. The main author is the book's own author_id field when present,
    # otherwise the first link (RokomariBG records no author order or roles).
    rk_to_ours = authors.set_index("rokomari_author_id").author_id
    links["author"] = links.author_id.map(rk_to_ours)
    per_book = links.groupby("book_id").author.agg(lambda a: sorted(set(a.dropna())))
    books["author_ids"] = books.book_id.map(per_book).apply(lambda v: v if isinstance(v, list) else [])
    main = books.primary_author_id.astype(str).map(rk_to_ours)
    books["main_author_id"] = main.fillna(books.author_ids.map(lambda a: a[0] if a else None))

    # S11: group editions into works. Bundles are never merged with anything.
    books["title_key"] = books.title_clean.map(title_key)
    # Volume: from the title, else from a trailing number in the URL slug. Rokomari titles often drop
    # the volume ("বিমল কুমার সমগ্র" for bimal-kumar-samagara-2, "নিশুতি" for nishuti-3…6). In groups
    # known to be one book (পথের পাঁচালী, 96 editions) no slug ends in a number, so it isn't a uniqueness suffix.
    slug_vol = pd.to_numeric(books.book_url.fillna("").str.extract(r"[a-z]-(\d{1,2})/?$")[0], errors="coerce")
    books["volume_used"] = books.volume.astype("Float64").fillna(slug_vol.astype("Float64"))
    vol = books.volume_used.astype("Int64").astype(str).replace("<NA>", "")
    books["work_key"] = books.title_key + "|" + books.main_author_id.fillna("?") + "|" + vol
    # Never merge without evidence: store bundles, placeholder titles ("Book": 336 unrelated items), and
    # books with no known author (46,610 editions; merging them by title alone joined different manga
    # volumes such as "One Piece" and "Case Closed").
    no_merge = (books.is_bundle | books.title_key.isin(PLACEHOLDER_TITLES) | (books.title_key == "")
                | books.main_author_id.isna())
    books.loc[no_merge, "work_key"] = "single|" + books.book_id[no_merge]
    codes = {k: f"bk_{i:06d}" for i, k in enumerate(sorted(books.work_key.unique()), 1)}
    books["work_id"] = books.work_key.map(codes)

    author_origin = authors.drop_duplicates("author_id").set_index("author_id").origin_hint

    # Best edition per work (its summary and title are used): usable first, then summary class, then length.
    b = books.assign(_unusable=~books.summary_usable, _rank=books.summary_class.map(SUMMARY_RANK).fillna(9),
                     _conf=books.origin_confidence.map(CONFIDENCE_RANK), _en=books.language != "bn")
    best = (b.sort_values(["work_id", "_unusable", "_rank", "summary_len"], ascending=[True, True, True, False])
             .drop_duplicates("work_id").set_index("work_id"))
    # Most confident origin among the editions, preferring Bangla editions (a Bangla work shouldn't take
    # "english_language" from an English edition in the same group).
    top = b.sort_values(["work_id", "_en", "_conf"]).drop_duplicates("work_id").set_index("work_id")
    g = b.groupby("work_id")

    works = pd.DataFrame({
        "title_bn": best.title_clean, "title_raw": best.title_raw, "volume": best.volume,
        "series_hint": g.series_hint.first(),
        "main_author_id": best.main_author_id,
        "author_ids": g.author_ids.agg(lambda s: sorted({a for ids in s for a in ids})),
        "edition_ids": g.book_id.agg(sorted), "n_editions": g.size(),
        "is_fiction": g.is_fiction.any(),
        "format": g.format.agg(lambda f: f.dropna().mode().iloc[0] if f.notna().any() else None),
        "genre_hints": g.genre_hints.agg(lambda h: sorted({x for s in h.dropna() for x in s.split("|")})),
        "audience": g.audience.agg(lambda a: next((x for x in AUDIENCE_ORDER if x in set(a.dropna())), None)),
        "religious": g.religious.any(),
        "language": g.language.agg(lambda l: "bn" if (l == "bn").any() else "en"),
        "origin": top.origin, "origin_rule": top.origin_rule, "origin_confidence": top.origin_confidence,
        "is_bundle": g.is_bundle.all(), "is_collection": g.is_collection_any.any(),
        "summary_source_book_id": best.book_id, "summary_class": best.summary_class,
        "summary": best.summary_clean, "summary_len": best.summary_len.astype(int),
        "summary_usable": best.summary_usable, "pages": best.pages,
        "isbn13": g.isbn13.agg(lambda i: sorted(set(i.dropna()))),
        "rating_count": g.rating_count.sum(), "review_count": g.review_count.sum(),
    })
    # Rating: average weighted by rating count over editions that have a rating.
    rated = b[b.rating_avg.notna() & (b.rating_count > 0)].assign(_w=lambda d: d.rating_avg * d.rating_count)
    rg = rated.groupby("work_id")
    works["rating_avg"] = rg._w.sum() / rg.rating_count.sum()
    # Origin means literary origin (where the author is from), not where this edition was printed:
    # a Dhaka reprint of Bibhutibhushan is still a West Bengal book. So for untranslated Bangla works the
    # main author's Wikidata nationality outranks publisher, category and ISBN evidence.
    from_author = works.main_author_id.map(author_origin)
    use = (works.origin != "translated") & (works.language == "bn") & from_author.isin(["bangladesh", "west_bengal"])
    works.loc[use, "origin"] = from_author[use]
    works.loc[use, "origin_rule"] = "author_wikidata"
    works.loc[use, "origin_confidence"] = "high"
    works["source"] = "rokomaribg"
    works = works.reset_index()

    # S12: the catalogue. Every excluded work keeps its reasons.
    reasons = pd.DataFrame({
        "not_fiction": ~works.is_fiction,
        "english_language": works.language != "bn",
        "store_bundle": works.is_bundle,
        "no_usable_summary": ~works.summary_usable,
    })
    works["exclude_reasons"] = reasons.apply(lambda r: [k for k, v in r.items() if v], axis=1)
    works["in_catalogue"] = works.exclude_reasons.str.len() == 0

    OUT.mkdir(parents=True, exist_ok=True)
    works.to_parquet(OUT / "works.parquet", index=False)
    books[["book_id", "work_id", "title_clean", "title_raw", "main_author_id", "author_ids", "binding", "paper",
           "volume", "isbn13", "pages", "publisher_name", "rating_avg", "rating_count", "review_count",
           "summary_class", "summary_usable", "book_url"]].to_parquet(OUT / "editions.parquet", index=False)
    used = {a for ids in works.author_ids for a in ids}
    authors[authors.author_id.isin(used)].to_parquet(OUT / "authors.parquet", index=False)

    cat = works[works.in_catalogue]
    first_reason = works.exclude_reasons.map(lambda r: r[0] if r else "in_catalogue")
    lines = ["# Cleaning report: S11–S12 (works, catalogue)", "",
             "Generated by `python -m scripts.clean.works`.", "",
             f"- Books (editions): {len(books):,} → **works: {len(works):,}**; "
             f"works with 2+ editions: {(works.n_editions > 1).sum():,}; largest group: {works.n_editions.max()} editions",
             f"- **In catalogue: {len(cat):,} works**",
             f"- Excluded, by first reason: {first_reason[first_reason != 'in_catalogue'].value_counts().to_dict()}",
             "", "## Catalogue breakdown",
             f"- Format: {cat.format.value_counts(dropna=False).to_dict()}",
             f"- Summary class: {cat.summary_class.value_counts().to_dict()}",
             f"- Origin: {cat.origin.value_counts().to_dict()}",
             f"- Origin confidence: {cat.origin_confidence.value_counts().to_dict()}",
             f"- Origin from author nationality (Wikidata): {(cat.origin_rule == 'author_wikidata').sum():,}",
             f"- Audience: {cat.audience.value_counts(dropna=False).to_dict()}",
             f"- With genre hints: {(cat.genre_hints.str.len() > 0).sum():,}; religious: {cat.religious.sum():,}; "
             f"collections: {cat.is_collection.sum():,}",
             f"- Main author linked to Wikidata: {cat.main_author_id.fillna('').str.startswith('au_Q').sum():,}",
             f"- With at least one review: {(cat.review_count > 0).sum():,}"]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
