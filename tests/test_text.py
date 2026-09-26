"""Tests for scripts/clean/text.py. Examples are real values from RokomariBG unless noted."""
import re
import unicodedata

import pytest

from scripts.clean import text as T


# ---------- S2: normalisation ----------

@pytest.mark.parametrize("a,b", [
    ("য়", "য়"),            # য় precomposed vs য + nukta
    ("কো", "কো"),           # ো precomposed vs ে + া
])
def test_equivalent_forms_become_equal(a, b):
    assert T.normalize_bn(a) == T.normalize_bn(b)


def test_broken_hasanta_is_repaired():
    assert T.normalize_bn("বই্্") == "বই"


@pytest.mark.parametrize("raw,expected", [
    ("মাওলানা আব্দুল্লাহ ‍সুহাইব", "মাওলানা আব্দুল্লাহ সুহাইব"),
    ("আমান‌উল্লাহ বিন নেছার", "আমানউল্লাহ বিন নেছার"),
])
def test_joiners_removed(raw, expected):
    assert T.normalize_bn(raw) == expected


def test_no_joiners_left_anywhere():
    out = T.normalize_bn("মুফতী মুহাম্মদ তৈয়‍্যেব হোসাইন")
    assert "‌" not in out and "‍" not in out


def test_latin_and_punctuation_survive():
    # The library alone turns 'e-গল্প' into '-গল্প' and drops curly quotes.
    assert T.normalize_bn("ফান e গল্প") == "ফান e গল্প"
    assert T.normalize_bn("e-গল্প") == "e-গল্প"
    assert T.normalize_bn("“আদিত্য, প্লিজ…”").startswith("“")
    assert T.normalize_bn("The book authored by Dr. Syed") == "The book authored by Dr. Syed"


def test_normalisation_is_idempotent():
    s = "হুমায়ূন আহমেদ (রহঃ) ২য় খণ্ড — ‘শেষের কবিতা’"
    once = T.normalize_bn(s)
    assert T.normalize_bn(once) == once
    assert unicodedata.is_normalized("NFC", once)


def test_empty_values():
    assert T.normalize_bn("") == ""
    assert T.normalize_bn(None) is None
    assert T.clean_text(None) is None
    assert T.clean_text("Show More") is None
    assert T.clean_text("   ") is None


def test_show_more_and_whitespace():
    raw = "প্রথম লাইন।\r\n\r\n\r\n\r\nদ্বিতীয়   লাইন।  Show More"
    assert T.clean_text(raw) == "প্রথম লাইন।\n\nদ্বিতীয় লাইন।"


# ---------- S3: fields ----------

@pytest.mark.parametrize("raw,isbn13,valid", [
    ("9789849156437", "9789849156437", True),
    ("8170661838", "9788170661832", True),       # ISBN-10 -> ISBN-13
    ("978-984-7760-49-0", "9789847760490", True),
    ("98483253611", None, False),                # 11 digits (real malformed value)
    ("9789849156438", None, False),              # wrong check digit (made up)
    (None, None, False),
])
def test_isbn(raw, isbn13, valid):
    assert T.normalize_isbn(raw) == (isbn13, valid)


def test_isbn_with_bangla_digits():
    assert T.normalize_isbn("৯৭৮৯৮৪৯১৫৬৪৩৭") == ("9789849156437", True)


@pytest.mark.parametrize("isbn13,origin", [
    ("9789849156437", "bangladesh"),
    ("9788170661832", "india"),
    ("9789353592332", "india"),
    ("9780061374814", "other"),
    (None, None),
])
def test_isbn_origin(isbn13, origin):
    assert T.isbn_origin(isbn13) == origin


def test_bangla_digits():
    assert T.bn_digits_to_ascii("পৃষ্ঠা ২১৬") == "পৃষ্ঠা 216"


# ---------- S4: script ----------

@pytest.mark.parametrize("s,expected", [
    ("সুশাসনের সন্ধানে", "bangla"),
    ("Some Aspects of Islam", "latin"),
    ("ফান e গল্প", "bangla"),
    ("PEC Communicative English মডেল টেস্ট", "latin"),
    ("বাংলা English মিশ্র text", "mixed"),
    ("১২৩ - ৪৫৬", None),
    ("", None),
])
def test_script_of(s, expected):
    assert T.script_of(s) == expected


# ---------- S5: titles ----------

def test_title_paper_and_collection():
    r = T.clean_title("গল্পগুচ্ছ (সাদা) অখণ্ড")
    assert r["title_clean"] == "গল্পগুচ্ছ অখণ্ড"
    assert r["paper"] == "white"
    assert r["is_collection"] is True


@pytest.mark.parametrize("raw,field,value,title", [
    ("মহুয়ার দেশে (সাদা)", "paper", "white", "মহুয়ার দেশে"),
    ("Some Book (Paperback)", "binding", "paperback", "Some Book"),
    ("Some Book (Hardcover)", "binding", "hardcover", "Some Book"),
    ("তিন গোয়েন্দা (২য় খণ্ড)", "volume", 2, "তিন গোয়েন্দা"),
    ("ভলিউম ১ ( কিশোর মুসা রবিন সিরিজ )", "series_hint", "কিশোর মুসা রবিন সিরিজ", "ভলিউম ১"),
])
def test_title_suffixes(raw, field, value, title):
    r = T.clean_title(raw)
    assert r[field] == value
    assert r["title_clean"] == T.normalize_bn(title)


def test_title_bundle():
    r = T.clean_title("বইমেলা ২০১২ এ প্রকাশিত হুমায়ুন আহমেদের বই (রকমারি কালেকশন)")
    assert r["is_bundle"] is True
    assert "রকমারি কালেকশন" not in r["title_clean"]


def test_title_keeps_honorifics():
    # Religious honorifics are part of the title and stay.
    assert "(সা.)" in T.clean_title("সীরাতে রাসূল (সা.)")["title_clean"]


def test_title_empty():
    assert T.clean_title(None)["title_clean"] is None


# ---------- S6: summaries ----------

def test_flap_label_removed():
    s = "\"সুশাসনের সন্ধানে\" বইটির প্রথম ফ্ল্যাপ-এর লেখাঃ দুর্নীতি, দুঃশাসন, গণসম্পদের অপচয়"
    cls, body = T.classify_summary(s)
    assert cls == "flap"
    assert body.startswith("দুর্নীতি")


def test_flap_short_label():
    cls, body = T.classify_summary("ফ্ল্যাপে লেখা কিছু কথা ঢাকার পুরনো ইতিহাস গৌরবময়।")
    assert cls == "flap" and body.startswith("ঢাকার")


def test_excerpt_label():
    cls, body = T.classify_summary("‘শেষের কবিতা’ বইয়ের কিছু অংশঃ অমিত-চরিত অমিত রায় ব্যারিস্টার।")
    assert cls == "excerpt" and body.startswith("অমিত-চরিত")


def test_toc_label():
    cls, _ = T.classify_summary("সূচিপত্র * বদরের যুদ্ধ * ওহুদের যুদ্ধ * খন্দকের যুদ্ধ")
    assert cls == "toc"


def test_toc_by_bullets_without_label():
    cls, _ = T.classify_summary("* দূরত্ব * নীল দংশন * আয়না বিবির পালা * নারীরা * গল্প কোলকাতার * এক")
    assert cls == "toc"


def test_plain_bangla_blurb_is_not_dialogue():
    # Regression: an unescaped '-' in the dialogue regex made every Bangla text look like dialogue.
    s = "বিদেশি একটি সংস্থা বাংলাদেশে লুকিয়ে একের পর এক মানুষ উৎসর্গ করে যাচ্ছে কোনো এক অপবিশ্বাসের নামে।"
    assert T.classify_summary(s)[0] == "blurb"


def test_dialogue_excerpt():
    s = "“আদিত্য, প্লিজ…”\nআদিত্য একদম ঘেঁষে দাঁড়িয়ে বলল,\n“প্লিজ কী?”\nসে হাত বাড়িয়ে দিল।"
    assert T.classify_summary(s)[0] == "excerpt"


def test_english_summary():
    s = "The book authored by Dr. Syed Mahmudul Hasan provides a broad overview of the religious aspects."
    assert T.classify_summary(s)[0] == "english"


def test_flap_then_toc_is_cut():
    s = "ফ্ল্যাপে লেখা কিছু কথা এটি একটি চমৎকার উপন্যাস। সূচিপত্র * এক * দুই"
    cls, body = T.classify_summary(s)
    assert cls == "flap"
    assert "সূচিপত্র" not in body


def test_empty_summary():
    assert T.classify_summary(None) == ("empty", None)


@pytest.mark.parametrize("cls,length,usable", [
    ("blurb", 200, True), ("blurb", 199, False), ("flap", 250, True),
    ("excerpt", 499, False), ("excerpt", 500, True), ("toc", 5000, False), ("english", 5000, False),
])
def test_summary_usable(cls, length, usable):
    assert T.summary_usable(cls, "ক" * length) is usable


# ---------- Regressions found while reviewing the S1-S6 output (2026-09-26) ----------

@pytest.mark.parametrize("raw,cls,start", [
    # label words must not match inside a longer word
    ("সূচিপত্রের কিছু অংশ: Chapter-1 Windows শুরু করা", "toc", "Chapter-1"),
    ("আল আরাবিয়্যাতু বাইনা ইয়াদাই আওলাদিনা সিরিজটির সংক্ষিপ্ত বিবরণী 'আল আরাবিয়্যাতু' ( আরবি", "blurb", "আল আরাবিয়্যাতু"),
    # an unquoted phrase before a label word is text, not a title
    ("কৃষ্ণদ্বৈপায়ন ব্যাস কৃত মহাভারত ভূমিকা এই পুস্তক ব্যাসকৃত মহাভারতের সারাংশের অনুবাদ।", "blurb", "কৃষ্ণদ্বৈপায়ন"),
    # a quoted title followed by বইটি is a blurb, not dialogue
    ("\"গণিতের হাত-পা ও রুবিক্স কিউব\" বইটি সম্পর্কে কিছু কথা: গণিত যতটাই না শেখার জিনিস", "blurb", "গণিত যতটাই"),
    ("‘তারিখে উম্মতে মুসলিমা’ গ্রন্থটির পটভূমি সৃষ্টির সূচনাকাল থেকে", "blurb", "‘তারিখে"),
    # label spelling variants
    ("ফ্ল্যাপে লিখা কথা এদেশের কিশোর বয়সীদের উদ্দেশ্যে লেখা", "flap", "এদেশের"),
    ("বইটিতে যা যা রয়েছেঃ * স্ত্রী ও সন্তানদের জন্য ব্যয় করার সাওয়াব", "toc", "*"),
])
def test_review_regressions(raw, cls, start):
    got_cls, body = T.classify_summary(raw)
    assert got_cls == cls
    assert body.startswith(start)


def test_single_quoted_line_is_not_dialogue():
    s = "“জীবন সুন্দর” — এই কথাটি দিয়েই শুরু হয় উপন্যাসের গল্প। একজন তরুণের সংগ্রামের কাহিনি।"
    assert T.classify_summary(s)[0] == "blurb"


@pytest.mark.parametrize("raw,field,value,title", [
    ("শ্রেষ্ঠ গল্প (পুরস্কারপ্রাপ্ত লেখকদের বই)", None, None, "শ্রেষ্ঠ গল্প"),
    ("ইংরেজি শিখুন (সিডি সহ)", None, None, "ইংরেজি শিখুন"),
    ("গীতাঞ্জলি (বাংলা)", "language_hint", "bn", "গীতাঞ্জলি"),
    ("মাসুদ রানা (২)", "volume", 2, "মাসুদ রানা"),
])
def test_title_review_regressions(raw, field, value, title):
    r = T.clean_title(raw)
    if field:
        assert r[field] == value
    assert r["title_clean"] == T.normalize_bn(title)


def _module_strings(value):
    """Every string inside a module-level constant: patterns, words, dict keys, nested lists."""
    if isinstance(value, re.Pattern):
        yield value.pattern
    elif isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for k, v in value.items():
            yield from _module_strings(k)
            yield from _module_strings(v)
    elif isinstance(value, (list, tuple, set)):
        for v in value:
            yield from _module_strings(v)


def test_all_patterns_and_word_lists_are_nfc():
    # Regression: patterns typed with precomposed য় (U+09DF) never match NFC text. Walks every
    # module-level constant, so a new pattern or word list can't skip the check by being unlisted.
    # REVERSED_VOWELS and LEGACY_* hold deliberately un-normalised input forms and are exempt.
    exempt = {"REVERSED_VOWELS", "LEGACY_TU", "LEGACY_THA", "BN_DIGITS"}
    for name, value in vars(T).items():
        if name.startswith("__") or name in exempt or callable(value) and not isinstance(value, re.Pattern):
            continue
        for s in _module_strings(value):
            assert unicodedata.is_normalized("NFC", s), f"{name}: {s[:60]!r}"


@pytest.mark.parametrize("raw,expected", [
    ("bফ্ল্যাপে লেখা কিছু কথা/bbr প্রকৃতি ও পরিবেশ", "ফ্ল্যাপে লেখা কিছু কথা প্রকৃতি ও পরিবেশ"),
    ("শুরুটা ২০১৬ থেকেই । brদিন গড়াতে গড়াতে", "শুরুটা ২০১৬ থেকেই । দিন গড়াতে গড়াতে"),
    ("<b>উপন্যাস</b><br>একটি গল্প", "উপন্যাস একটি গল্প"),
    ("Chapter b of the book", "Chapter b of the book"),     # English text untouched
    ("Vitamin B12 and br-code", "Vitamin B12 and br-code"),
])
def test_html_residue(raw, expected):
    assert T.clean_text(raw) == T.normalize_bn(expected)


def test_flap_residue_then_label():
    cls, body = T.classify_summary(T.clean_text("bফ্ল্যাপে লিখা কথা/bbr/ রুনু বসে আছে ইঞ্জিন বসানো ছোট্ট একটা নৌকার পাটাতনে।"))
    assert cls == "flap" and body.startswith("রুনু")


@pytest.mark.parametrize("raw,cls,start", [
    ("\"গুপ্ত জীবন প্রকাশ্য মৃত্যু\" বইটির শেষের ফ্ল্যাপ-এর লেখাঃ এই কাহিনী শুকুর মাহাম্মদের।", "flap", "এই কাহিনী"),
    ("“হাজার চুরাশির মা” বইয়ের ভূমিকাঃ মহাশ্বেতা দেবী। তিনি উপন্যাসিক।", "preface", "মহাশ্বেতা"),
    ("“ইতিহাস” বইটিতে লেখা ফ্ল্যাপের কথাঃ মানুষের ইতিহাস প্রাচীন।", "flap", "মানুষের"),
    ("“জীবন” বইটিতে ফ্ল্যাপে লিখা কথা এই উপন্যাসের শুরু।", "flap", "এই উপন্যাসের"),
    ("\"ডেথ সিটি\" বইয়ের ফ্যাপের লেখা: স্বর্ণলোভী ভূত", "flap", "স্বর্ণলোভী"),
    ("বই এর প্রথম ফ্লাপ হলদিপোঁতা ধাওড়া একটি অখ্যাত জনপদ", "flap", "হলদিপোঁতা"),
])
def test_label_variants(raw, cls, start):
    got, body = T.classify_summary(T.clean_text(raw))
    assert got == cls and body.startswith(start)


def test_residue_before_punctuation():
    assert "/bbr" not in T.clean_text("স্মরণিকা অপ্রকাশিত /bbr* বেদ-এর অবদান")
    assert "/bbr" not in T.clean_text("বইয়ের শুরুর কথা:/bbr তারিণীখুড়ো গল্প বলেন")


@pytest.mark.parametrize("raw,expected", [
    # real raw values: ো stored as া + ে (reversed); the library alone deletes the ে
    ("ছােটবেলাতেই", "ছোটবেলাতেই"),
    ("কথাগুলাে", "কথাগুলো"),
    ("গােল্ডেন", "গোল্ডেন"),
    ("কৗেশল", "কৌশল"),               # ৌ reversed (made up; no case in the data)
])
def test_reversed_vowel_signs_repaired(raw, expected):
    assert T.normalize_bn(raw) == T.normalize_bn(expected)
    assert "াে" not in T.normalize_bn(raw)


@pytest.mark.parametrize("raw", [
    "ছোট",          # ছোট with ো precomposed
    "ছোট",   # ছোট with ো as ে + া in the correct order
])
def test_correct_o_kar_untouched(raw):
    assert T.normalize_bn(raw) == "ছোট"


@pytest.mark.parametrize("raw,expected", [
    # real raw values: তু written as ত্ত inside স্/ন্ conjuncts by legacy conversion
    ("বস্ত্তনিষ্ঠ", "বস্তুনিষ্ঠ"),
    ("প্রস্ত্ততি", "প্রস্তুতি"),
    ("আগন্ত্তক", "আগন্তুক"),
    ("বস্ত্তুত", "বস্তুত"),        # already has ু: must not get a second one
])
def test_legacy_tu_repaired(raw, expected):
    assert T.normalize_bn(raw) == T.normalize_bn(expected)


def test_real_tta_conjuncts_untouched():
    # উত্তর (ত্ত after a vowel) and কর্ত্তা (old র্ত্ত spelling) are real words: the legacy repair
    # must not touch them.
    assert "ত্ত" in T.normalize_bn("উত্তর")
    assert T.repair_legacy_encoding("কর্ত্তা") == "কর্ত্তা"


def test_show_more_followed_by_page_junk():
    raw = "হাই স্কুল ইংলিশ গ্রামার বই। Show More Title হাই স্কুল ইংলিশ গ্রামার <div class=\"tab-pane\">"
    assert T.clean_text(raw) == T.normalize_bn("হাই স্কুল ইংলিশ গ্রামার বই।")


@pytest.mark.parametrize("raw,expected", [
    ("বিষণ্ন", "বিষণ্ন"),            # conjunct kept (the library alone made বিষণন)
    ("অক্ষুণ্ন", "অক্ষুণ্ন"),
    ("ছ্যাঁকা", "ছ্যাঁকা"),
    ("অবস্হা", "অবস্থা"),            # legacy হ-for-থ repaired
    ("স্হান", "স্থান"),
    ("গ্রন্হটি", "গ্রন্থটি"),
    ("সিন্হা", "সিন্হা"),            # real surname spelling, not repaired
    ("ফিক্হ", "ফিক্হ"),              # transliteration of fiqh, kept
])
def test_conjuncts_preserved_or_repaired(raw, expected):
    assert T.normalize_bn(raw) == unicodedata.normalize("NFC", expected)
