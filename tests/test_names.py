"""Tests for scripts/clean/names.py. Names are real RokomariBG author values unless noted."""
import pytest

from scripts.clean import names as N
from scripts.clean import text as T


def nk(s):
    return T.normalize_bn(s).lower()


@pytest.mark.parametrize("raw,field,value", [
    ("সুনীল গঙ্গোপাধ্যায় (নীললোহিত)", "aliases", ["নীললোহিত"]),
    ("অখিল নিয়োগী (স্বপনবুড়ো)", "aliases", ["স্বপনবুড়ো"]),
    ("হযরত শেখ সাদী (রহঃ)", "honorifics", ["রহঃ"]),
    ("ইমাম হাফিজ শামসুদ্দিন আয-যাহাবী (রহ.)", "honorifics", ["রহ."]),
    ("লে. কর্নেল (অব.) কাজী সাজ্জাদ আলী জহির বীর প্রতীক", "rank_titles", ["অব.", "বীর প্রতীক"]),
])
def test_bracket_and_title_parts(raw, field, value):
    assert N.parse_author(raw)[field] == [T.normalize_bn(v) for v in value]


@pytest.mark.parametrize("raw,key", [
    ("সুনীল গঙ্গোপাধ্যায় (নীললোহিত)", "সুনীল গঙ্গোপাধ্যায়"),
    ("ড. এনামুল হক", "এনামুল হক"),
    ("প্রফেসর ডা. দেওয়ান আবদুর রহীম", "দেওয়ান আবদুর রহীম"),
    ("মাওলানা আব্দুল্লাহ ‍সুহাইব", "আব্দুল্লাহ সুহাইব"),
    ("লে. কর্নেল (অব.) কাজী সাজ্জাদ আলী জহির বীর প্রতীক", "কাজী সাজ্জাদ আলী জহির"),
    ("মোঃ রফিকুল ইসলাম", "মোহাম্মদ রফিকুল ইসলাম"),     # মোঃ / মো. / মুহাম্মদ → one form
    ("মো. রফিকুল ইসলাম", "মোহাম্মদ রফিকুল ইসলাম"),
    ("মুহাম্মদ রফিকুল ইসলাম", "মোহাম্মদ রফিকুল ইসলাম"),
])
def test_name_key(raw, key):
    assert N.name_key(raw) == nk(key)


def test_single_word_title_is_kept():
    # A name that is only a title word must not become empty.
    assert N.name_key("মাওলানা") == nk("মাওলানা")


def test_arabic_script_part_removed():
    r = N.parse_author("(شيخ الاسلام مفتي محمد تقي عثماني) শাইখুল ইসলাম মুফতী মুহাম্মাদ তাকী উসমানী")
    assert "ش" not in r["name_display"]
    assert r["name_key"].startswith(nk("শাইখুল"))


@pytest.mark.parametrize("raw,kind", [
    ("মাকতাবাতুল হাসান অনুবাদ পর্ষদ", "organisation"),
    ("নাদিয়াতুল কোরআন অনুবাদ ও সম্পাদনা পরিষদ", "organisation"),
    ("পাঞ্জেরী সম্পাদনা পর্ষদ", "organisation"),
    # Traps found while profiling: organisation words at the START are people's names.
    ("টিম ডি. হিউইটসন", "person"),
    ("টিমোথি হাইজেনবট্টাম", "person"),
    ("ফারবোর্ড ফাহিমি", "person"),
    ("শফিকুল ইসলাম", "person"),
])
def test_author_type(raw, kind):
    assert N.parse_author(raw)["author_type"] == kind


def test_descriptor_not_alias():
    r = N.parse_author("রফিক আহমেদ (সাংবাদিক)")     # made-up name, real descriptor
    assert r["descriptors"] == [T.normalize_bn("সাংবাদিক")] and r["aliases"] == []


def test_empty():
    assert N.parse_author(None)["name_key"] is None
    assert N.parse_author("")["author_type"] == "person"


def test_latin_names_lowercased():
    assert N.name_key("Humayun Ahmed") == "humayun ahmed"
