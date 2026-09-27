"""Tests for S7-S12 rules. Category names are real RokomariBG categories."""
from types import SimpleNamespace

import pytest

from scripts.clean.build_category_map import classify
from scripts.clean.categories_origin import origin
from scripts.clean.works import title_key


@pytest.mark.parametrize("name,action,fmt", [
    ("Story", "map", "short_story_collection"),
    ("Novel", "map", "novel"),
    ("Rhymes, Poems and Recitation", "map", "poetry"),
    ("Comics & Graphic Novels", "map", "comics"),             # comics wins over novel
    ("Drama/ Play", "map", "drama"),
    ("When 8-12: Fables", "map", "short_story_collection"),
    ("Novel, Poem, Short Story & Drama Collection", "map", None),   # mixed → no format
    # the substring bug: "story" inside "History"
    ("History and Tradition", "exclude", None),
    ("Islamic History", "exclude", None),
    ("Historical Novel", "map", "novel"),
    # false positives found while reviewing the 190 mapped categories
    ("Artificial Intelligence & Robotics", "unknown", None),
    ("Kindergarten: Play Group", "unknown", None),
    ("Drama Criticism and Others", "exclude", None),
    ("Non-Fiction", "exclude", None),
    # academic, promotions, generic buckets
    ("HSC 1st Year: Islamic History", "exclude", None),
    ("Amar Ekushe Boimela", "ignore", None),
    ("Book", "ignore", None),
    ("Others", "unknown", None),
])
def test_category_action_and_format(name, action, fmt):
    r = classify(name)
    assert r["action"] == action
    assert r["format"] == fmt


@pytest.mark.parametrize("name,field,value", [
    ("When 12-17: Novel", "audience", "teen"),
    ("When 4-8: Story", "audience", "children"),
    ("Children and Teens: Horror", "audience", "children"),
    ("West Bengal Books: Novel", "origin_hint", "west_bengal"),
    ("Translated Books: Novels", "origin_hint", "translated"),
    ("Foreign Language Books: Novel", "language_hint", "en"),
    # "Translated & English" is a Bangla translation category, not English-language
    ("Mystery, Detective, Horror, Thriller, Myth and Adventure: Translated & English", "language_hint", None),
    ("Bangla-English Poem", "language_hint", None),
    ("Mystery and Detective", "genre_hints", "detective"),
    ("Detective, Intelligence and Secret Agency,", "genre_hints", "detective|spy"),
    ("Novel: Political and Liberation war", "genre_hints", "liberation_war|social"),
])
def test_category_hints(name, field, value):
    assert classify(name)[field] == value


def _row(**kw):
    base = dict(language="bn", category_origin_hint=None, publisher_india=False, isbn_origin=None)
    base.update(kw)
    return SimpleNamespace(**base)


@pytest.mark.parametrize("row,expected", [
    (_row(language="en", publisher_india=True), ("english_language", "language_en", "high")),  # Salem's Lot case
    (_row(category_origin_hint="translated", publisher_india=True), ("translated", "translation_category", "high")),
    (_row(publisher_india=True), ("west_bengal", "publisher_india", "high")),
    (_row(category_origin_hint="west_bengal"), ("west_bengal", "west_bengal_category", "high")),
    (_row(isbn_origin="india"), ("west_bengal", "isbn_india", "medium")),
    (_row(isbn_origin="bangladesh"), ("bangladesh", "isbn_bangladesh", "medium")),
    (_row(), ("bangladesh", "default", "low")),
])
def test_origin_rule_order(row, expected):
    assert origin(row) == expected


def test_title_key():
    assert title_key("পথের পাঁচালী") == title_key(" পথের  পাঁচালী ")
    assert title_key("“শেষের কবিতা”") == title_key("শেষের কবিতা")
    assert title_key("Case Closed: Vol-1") == "case closed vol 1"


from scripts.clean.authors import country_origin


@pytest.mark.parametrize("countries,expected", [
    ("Pakistan|Bangladesh", "bangladesh"),
    ("British Raj|Bangladesh", "bangladesh"),
    ("Dominion of India|British Raj", "west_bengal"),      # Bibhutibhushan (d. 1950)
    ("India|British Raj", "west_bengal"),
    ("British Raj", None),                                 # Tagore: no signal about today's border
    ("Turkey", None),
    (None, None),
])
def test_country_origin(countries, expected):
    assert country_origin(countries) == expected


from scripts.clean.works import slug_volume, subtitle_signature, cluster_signatures


@pytest.mark.parametrize("slug,vol", [
    ("golposomogro-1st-part", 1), ("da-gargi-samagra-vol-5", 5), ("katay-katay-2nd-part", 2),
    ("nishuti-3", 3), ("upponassomogro-4th-khondo", 4), ("pother-pachali", None), ("1984", None),
])
def test_slug_volume(slug, vol):
    assert slug_volume(slug) == vol


@pytest.mark.parametrize("slug,n,sig", [
    ("masud-rana-dhongso-pahar", 2, "dhongso-pahar"),        # truncated title: different books
    ("masud-rana-kurukkhetro", 2, "kurukkhetro"),
    ("pother-pachali", 2, ""),                                # spelling variant: no signature
    ("golpoguccho-okhondo-sonkolon", 1, ""),                  # generic words only
    ("nouka-dubi", 1, ""),                                    # one-word title romanised as two words
])
def test_subtitle_signature(slug, n, sig):
    assert subtitle_signature(slug, n) == sig


def test_cluster_signatures():
    labels = cluster_signatures(["", "dhongso-pahar", "dhongso-pahad", "kurukkhetro"])
    assert labels[0] == "" and labels[1] == labels[2] and labels[1] != labels[3]
