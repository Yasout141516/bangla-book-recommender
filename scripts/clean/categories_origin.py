"""S7-S8 of docs/10-cleaning-spec.md: category → format/genre hints/audience, and origin, per book.

Usage:  python -m scripts.clean.categories_origin
Input:  data/interim/rokomari_books.parquet (S1-S6), data/mappings/category_map.csv,
        data/raw/rokomaribg/{book_to_category,publisher}.json.gz
Output: data/interim/rokomari_books_s8.parquet, docs/reports/cleaning-s7-s8.md
"""
import gzip
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw" / "rokomaribg"
IN = ROOT / "data" / "interim" / "rokomari_books.parquet"
MAP = ROOT / "data" / "mappings" / "category_map.csv"
OUT = ROOT / "data" / "interim" / "rokomari_books_s8.parquet"
REPORT = ROOT / "docs" / "reports" / "cleaning-s7-s8.md"

# When a book's categories disagree, the more specific format wins.
FORMAT_PRIORITY = ["comics", "poetry", "drama", "novel", "short_story_collection"]
AUDIENCE_ORDER = ["children", "teen"]  # youngest first


def to_bool(series):
    """Nullable/object true-false column → plain bool, missing = False."""
    return series.astype("boolean").fillna(False).astype(bool)


def load_raw(name):
    with gzip.open(RAW / f"{name}.json.gz", "rt", encoding="utf-8") as fh:
        return pd.DataFrame(json.load(fh))


def book_categories(books, cmap):
    """One row per (book, category) with the category's mapping; includes the primary category."""
    links = load_raw("book_to_category")[["book_id", "category_id"]]
    primary = books[["book_id", "primary_category_id"]].rename(columns={"primary_category_id": "category_id"})
    links = pd.concat([links, primary]).dropna().astype(str).drop_duplicates()
    return links.merge(cmap.astype({"category_id": str}), on="category_id", how="left")


def aggregate(bc):
    """Collapse per-book category rows into book-level S7 fields."""
    bc = bc.fillna({"action": "unknown", "format": "", "genre_hints": "", "audience": "",
                    "origin_hint": "", "language_hint": ""})
    for col in ("religious", "is_collection"):
        bc[col] = to_bool(bc[col])
    bc["is_translated"] = bc.origin_hint == "translated"
    bc["is_wb"] = bc.origin_hint == "west_bengal"
    bc["is_en"] = bc.language_hint == "en"
    g = bc.groupby("book_id")
    mapped = bc[bc.action == "map"]
    gm = mapped.groupby("book_id")

    def first_by(values, order):
        present = set(values) - {""}
        return next((v for v in order if v in present), None)

    out = pd.DataFrame(index=g.size().index)
    out["n_categories"] = g.size()
    out["category_actions"] = g.action.agg(lambda a: "|".join(sorted(set(a))))
    out["is_fiction"] = out.index.isin(mapped.book_id)
    out["format"] = gm.format.agg(lambda f: first_by(f, FORMAT_PRIORITY))
    out["format_conflict"] = gm.format.agg(lambda f: len(set(f) - {""}) > 1)
    out["genre_hints"] = gm.genre_hints.agg(
        lambda h: "|".join(sorted({x for s in h for x in s.split("|") if x})) or None)
    out["audience"] = gm.audience.agg(lambda a: first_by(a, AUDIENCE_ORDER))
    tr, wb = g.is_translated.any(), g.is_wb.any()
    out["category_origin_hint"] = pd.Series(None, index=out.index, dtype=object)
    out.loc[wb[wb].index, "category_origin_hint"] = "west_bengal"
    out.loc[tr[tr].index, "category_origin_hint"] = "translated"   # translated wins over west_bengal
    out["category_language_en"] = g.is_en.any()
    out["religious"] = g.religious.any()
    out["category_collection"] = g.is_collection.any()
    out["excluded_reason"] = g.rule.agg(lambda r: "|".join(sorted(set(r.dropna()) - {"fiction"})) or None)
    return out.reset_index()


def origin(row):
    """S8 rule order; first match wins. Returns (origin, rule, confidence)."""
    if row.language == "en":
        # English-language editions: an Indian publisher doesn't make Salem's Lot a West Bengal book.
        return "english_language", "language_en", "high"
    if row.category_origin_hint == "translated":
        return "translated", "translation_category", "high"
    if row.publisher_india:
        return "west_bengal", "publisher_india", "high"
    if row.category_origin_hint == "west_bengal":
        return "west_bengal", "west_bengal_category", "high"
    if row.isbn_origin == "india":
        return "west_bengal", "isbn_india", "medium"
    if row.isbn_origin == "bangladesh":
        return "bangladesh", "isbn_bangladesh", "medium"
    return "bangladesh", "default", "low"


def main():
    books = pd.read_parquet(IN)
    books["book_id"] = books.book_id.astype(str)
    cmap = pd.read_csv(MAP, dtype={"category_id": str})
    s7 = aggregate(book_categories(books, cmap))
    df = books.merge(s7, on="book_id", how="left")
    for col in ("is_fiction", "format_conflict", "category_language_en", "religious", "category_collection",
                "is_bundle", "is_collection"):
        df[col] = to_bool(df[col])

    pubs = load_raw("publisher").astype({"publisher_id": str}).set_index("publisher_id").publisher_name
    df["publisher_name"] = df.publisher_id.astype(str).map(pubs)
    df["publisher_india"] = df.publisher_name.fillna("").str.contains(r"\(India\)", regex=True)
    # English-language book: a Latin-script title plus either an English category or a summary that is
    # not Bangla (Latin, mixed or missing). A Latin title with a Bangla summary stays "bn": in a sample
    # of 576 such fiction books these were Bangla novels with English titles ("Z") or English kids' books
    # described in Bangla; both get a Bangla premise.
    latin_title = df.title_script == "latin"
    en = latin_title & (df.category_language_en | (df.summary_script != "bangla"))
    df["language"] = en.map({True: "en", False: "bn"})
    df["is_collection_any"] = df.is_collection | df.category_collection

    o = df.apply(origin, axis=1, result_type="expand")
    df["origin"], df["origin_rule"], df["origin_confidence"] = o[0], o[1], o[2]

    df.to_parquet(OUT, index=False)

    fic = df[df.is_fiction]
    lines = ["# Cleaning report: S7–S8 (categories, origin)", "",
             "Generated by `python -m scripts.clean.categories_origin`.", "",
             f"- Books: {len(df):,}; **fiction (any mapped category): {len(fic):,}**",
             f"- Fiction by format: {fic.format.value_counts(dropna=False).to_dict()}",
             f"- Fiction with a format conflict between categories: {int(fic.format_conflict.sum()):,}",
             f"- Fiction with genre hints: {int(fic.genre_hints.notna().sum()):,}",
             f"- Fiction by audience: {fic.audience.value_counts(dropna=False).to_dict()}",
             f"- Fiction by language: {fic.language.value_counts().to_dict()}",
             f"- Fiction marked religious: {int(fic.religious.sum()):,}",
             "", "## Origin (fiction)", "| origin | rule | confidence | books |", "|---|---|---|---|"]
    for (a, b, c), n in fic.groupby(["origin", "origin_rule", "origin_confidence"]).size().items():
        lines.append(f"| {a} | {b} | {c} | {n:,} |")
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
