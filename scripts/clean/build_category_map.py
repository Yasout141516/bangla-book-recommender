"""S7 step 1: build the category mapping table from ordered keyword rules.

Usage:  python -m scripts.clean.build_category_map
Output: data/mappings/category_map.csv   (committed to git: our own work, reviewed by hand)

Each Rokomari category gets an action:
  exclude  - non-fiction subject or academic/exam material
  unknown  - neither recognisably fiction nor non-fiction ("Others"); carries only origin/audience hints
  ignore   - store promotion or a generic bucket that says nothing about the book
  map      - fiction/poetry/drama; carries format, genre hints, audience and origin/language hints
Genre hints are candidates for the later LLM labelling step, not final genres: Rokomari often
combines five genres in one category ("Mystery, Detective, Horror, Thriller and Adventure").

All keywords match whole words. Substring matching made "story" match "History", which
counted history books as fiction (see docs/11).
"""
import gzip
import json
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw" / "rokomaribg"
OUT = ROOT / "data" / "mappings" / "category_map.csv"


def w(*words):
    """Whole-word, case-insensitive alternation."""
    return re.compile(r"(?<![A-Za-z])(?:" + "|".join(words) + r")(?![A-Za-z])", re.I)


# ---- rules, checked in order ----
ACADEMIC = w("HSC", "SSC", "JSC", "PSC", "Honors", "Honours", "Degree", "Masters", "Department", "Admission",
             "Text ?Books?", "Pattho", "Sohayika", "University", "Madrasa", "BCS", "Recruitment", "Job",
             "Exam", "Exams", "Class", "Board", "Guide", "Suggestion", "Model Test", "Medical", "Medicine",
             "Engineering", "Nursing", "Teacher registration")
FICTION = w("Novels?", "Stor(?:y|ies)", "Fiction", "Thriller", "Mystery", "Detective", "Horror", "Supernatural",
            "Adventure", "Fantasy", "Romance", "Romantic", "Humou?r", "Jokes", "Comics?", "Graphic", "Fairy tales?",
            "Poems?", "Poetry", "Rhymes?", "Ballad", "Drama", "Myth", "Mythological", "legendary", "Fables?",
            "Intelligence and Secret Agency", "Secret Agency", "Para Psychological", "Literature: Stories",
            "Literature: Novels", "Literature: Poetry")
# Fiction words that don't make a category fiction on their own.
NOT_FICTION = w("Non-Fiction", "Non Fiction", "Drama Criticism", "Poem Criticism", "Criticism", "Folk Music",
                "Music", "Films", "Magazine")
NONFICTION = w("History", "Historical Research", "Islamic", "Religious", "Quran", "Hadith", "Sunnah", "Sirat\\w*",
               "Seerat", "Self-Help", "Motivational", "Business", "Economics", "Science", "Technology",
               "Mathematics", "Computer", "Politics", "Political History", "Law", "Health", "Fitness", "Travel",
               "Articles?", "Philosophy", "Biograph\\w*", "Memories", "Interviews", "Dictionary", "Language",
               "Reference", "Psychology", "Agricultur\\w*", "Cooking", "Recipe", "Parenting", "Archaeolog\\w*",
               "Civilization", "Culture", "Society", "Journal", "Research")
PROMO = w("Boimela", "Book ?Fair", "Granthamela", "July Triumph", "In Stock", "Offer", "Combo", "Package",
          "Pre-?order", "Best ?Sellers?", "New Arrival", "Collections? & Box Sets", "Box Sets?")
GENERIC = {"book", "fiction", "translated books", "foreign language books", "west bengal books",
           "west bengal books: collection", "bangladesh", "children & teens"}

FORMAT = [  # first match wins
    ("comics", w("Comics?", "Graphic")),
    ("poetry", w("Poems?", "Poetry", "Rhymes?", "Ballad")),
    ("drama", w("Drama")),
    ("novel", w("Novels?")),
    ("short_story_collection", w("Stor(?:y|ies)", "Fairy tales?", "Fables?")),
]
GENRE = [
    ("detective", w("Detective", "Mystery")),
    ("spy", w("Intelligence and Secret Agency", "Secret Agency")),
    ("thriller", w("Thriller")),
    ("horror", w("Horror")),
    ("supernatural", w("Supernatural", "Para Psychological")),
    ("sci_fi", w("Science Fiction")),
    ("fantasy", w("Fantasy", "Fairy tales?")),
    ("adventure", w("Adventure", "Travel Novel")),
    ("romance", w("Romance", "Romantic")),
    ("humor_satire", w("Humou?r", "Jokes")),
    ("liberation_war", w("Liberation war", "'71", "1971")),
    ("historical", w("Historical", "Biographical novel", "Mughal")),
    ("mythology", w("Myth", "Mythological", "legendary")),
    ("psychological", w("Para Psychological", "Psychological")),
    ("social", w("Political Novel", "Political Story", "Political and Liberation war")),
]
AUDIENCE = [("children", re.compile(r"When\s*(?:4-8|8-12)|Children(?:\s*(?:and|&)\s*Teens)?|Children’s", re.I)),
            ("teen", re.compile(r"When\s*12-17", re.I))]


def classify(name):
    n = name.strip()
    low = n.lower()
    row = {"action": None, "rule": None, "format": None, "genre_hints": "", "audience": None,
           "origin_hint": None, "language_hint": None, "religious": False, "is_collection": False}
    if w("West Bengal").search(n):
        row["origin_hint"] = "west_bengal"
    if w("Translated", "Translation").search(n):
        row["origin_hint"] = "translated"
    # English-language books (not Bangla). "Translated & English" and "Bangla-English" are Bangla or bilingual.
    if w("Foreign Language Books?").search(n) or (
            w("English").search(n) and not w("Translated", "Bangla-English").search(n)):
        row["language_hint"] = "en"
    row["religious"] = bool(w("Islamic", "Religious", "Devotional").search(n))
    row["is_collection"] = bool(w("Compilation", "Collections?", "Box Sets?", "Omnibus").search(n))

    if ACADEMIC.search(n):
        row.update(action="exclude", rule="academic")
    elif PROMO.search(n):
        row.update(action="ignore", rule="promotion")
    elif low in GENERIC:
        row.update(action="ignore", rule="generic")
    elif FICTION.search(n) and not NOT_FICTION.search(n) and not (
            w("History").search(n) and not w("Historical Novel", "Historical Story").search(n)):
        row.update(action="map", rule="fiction")
    elif NONFICTION.search(n) or NOT_FICTION.search(n):
        row.update(action="exclude", rule="nonfiction")
    else:
        # Not recognisably fiction or non-fiction ("Others", "Literature Collection", "Liberation War 1971").
        row.update(action="unknown", rule="unmatched")

    if row["action"] == "map":
        formats = [f for f, p in FORMAT if p.search(n)]
        # Comics wins ("Comics & Graphic Novels"); otherwise several formats means a mixed category.
        row["format"] = "comics" if "comics" in formats else (formats[0] if len(formats) == 1 else None)
        row["genre_hints"] = "|".join(g for g, p in GENRE if p.search(n))
        row["audience"] = next((a for a, p in AUDIENCE if p.search(n)), None)
    return row


def main():
    with gzip.open(RAW / "category.json.gz", "rt", encoding="utf-8") as fh:
        cats = pd.DataFrame(json.load(fh))
    with gzip.open(RAW / "book_to_category.json.gz", "rt", encoding="utf-8") as fh:
        links = pd.DataFrame(json.load(fh)).drop_duplicates()
    books = links.groupby("category_id").size().rename("books")
    cats = cats.merge(books, left_on="category_id", right_index=True, how="left")
    cats["books"] = cats.books.fillna(0).astype(int)
    rows = pd.DataFrame([classify(n) for n in cats.category_name])
    out = pd.concat([cats[["category_id", "category_name", "books"]].reset_index(drop=True), rows], axis=1)
    out = out.sort_values("books", ascending=False)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT, index=False, encoding="utf-8")
    print(f"Wrote {OUT}: {len(out)} categories")
    print(out.groupby(["action", "rule"]).agg(categories=("category_id", "size"), book_links=("books", "sum")))


if __name__ == "__main__":
    main()
