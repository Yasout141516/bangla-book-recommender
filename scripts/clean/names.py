"""Author-name helpers for S9-S10 (docs/10-cleaning-spec.md). Pure functions, tested in tests/test_names.py.

Word lists come from profiling the 16,601 RokomariBG author names (2026-09-26): the most common
first words, bracket contents and endings.
"""
import re

from scripts.clean import text as T

_w = T._nfc_words

# Bracket contents that are not names.
HONORIFICS = _w("রহ.", "রহঃ", "রহ", "রহ:", "র.", "র", "রঃ", "রা.", "রাঃ", "রা", "সা.", "সাঃ", "আ.", "আঃ",
                "রহিমাহুল্লাহ", "রাহিমাহুল্লাহ", "হাফিজাহুল্লাহ", "হাফিযাহুল্লাহ", "দা.বা.", "দাঃবাঃ")
RANK_TITLES = _w("অব.", "অব:", "অবঃ", "অব", "বীর উত্তম", "বীর বিক্রম", "বীর প্রতীক", "বীরপ্রতীক", "বীরউত্তম")
DESCRIPTORS = _w("টেক্সট", "বিসিএস", "ডিএমসি", "সাংবাদিক", "এম.এ", "অ্যাডভোকেট", "চিত্রশিল্পী", "কার্টুনিস্ট",
                 "ভারত", "আইসিটি", "অনুবাদক", "এল এল বি", "প্রফেসর", "ঢাবি", "ব্যাংকার", "বিএসসি", "অধ্যাপক",
                 "কবি", "লেখক", "সম্পাদক", "শিক্ষক", "ডাক্তার", "ইঞ্জিনিয়ার", "বাংলাদেশ")
# Leading titles: removed from the matching key only; the display name keeps them.
TITLES = _w("মাওলানা", "মাওলানা", "ড.", "ডঃ", "ড", "ডা.", "ডাঃ", "ডা", "ডক্টর", "প্রফেসর", "অধ্যাপক", "মুফতী",
            "মুফতি", "শাইখ", "শায়খ", "শেখ.", "আল্লামা", "হাফেজ", "হাফিজ", "হযরত", "হজরত", "প্রকৌশলী",
            "ইঞ্জিনিয়ার", "অ্যাডভোকেট", "এডভোকেট", "ব্যারিস্টার", "লে.", "লেঃ", "কর্নেল", "মেজর",
            "ব্রিগেডিয়ার", "জেনারেল", "ক্যাপ্টেন", "Dr.", "Prof.", "Professor")
# Trailing gallantry titles written without brackets: "… বীর প্রতীক".
TRAILING_TITLES = _w("বীর উত্তম", "বীর বিক্রম", "বীর প্রতীক")
MD = re.compile(T._nfc(r"(?:^|(?<=\s))(?:মোঃ|মো\.|মো:|মোহাম্মদ|মুহাম্মদ|মুহাম্মাদ|মোহাম্মাদ)(?=\s|$)"))
# Organisations listed as authors: the name has to END with one of these words.
ORG_ENDINGS = _w("সম্পাদনা পরিষদ", "সম্পাদনা পর্ষদ", "পরিষদ", "পর্ষদ", "প্রকাশনী", "প্রকাশন", "কুতুবখানা",
                 "লাইব্রেরি", "লাইব্রেরী", "বোর্ড", "টিম", "ফাউন্ডেশন", "একাডেমি", "একাডেমী", "ইনস্টিটিউট",
                 "বিভাগ", "Editorial Board", "Team", "Publications", "Publishers", "Foundation", "Limited", "Ltd")
ARABIC = re.compile(r"[؀-ۿݐ-ݿﭐ-﷿ﹰ-﻿]+")
BRACKET = re.compile(r"\(([^()]*)\)")


def parse_author(raw):
    """Split a raw author name into display name, matching key and extracted parts.

    Returns a dict: name_display, name_key, honorifics, rank_titles, descriptors, aliases, author_type.
    """
    out = {"name_display": None, "name_key": None, "honorifics": [], "rank_titles": [], "descriptors": [],
           "aliases": [], "author_type": "person"}
    if not raw:
        return out
    display = T.normalize_whitespace(T.normalize_bn(raw))
    # Remove Arabic-script parts (a name given in both Arabic and Bangla) and their empty brackets.
    display = re.sub(r"\(\s*\)", "", ARABIC.sub("", display))
    display = re.sub(r"\s+", " ", display).strip()
    out["name_display"] = display or None

    def repl(m):
        inner = m.group(1).strip().strip("-–,")
        if not inner:
            return " "
        if inner in HONORIFICS:
            out["honorifics"].append(inner)
        elif inner in RANK_TITLES:
            out["rank_titles"].append(inner)
        elif inner in DESCRIPTORS:
            out["descriptors"].append(inner)
        else:
            out["aliases"].append(inner)  # pen name or nickname: সুনীল গঙ্গোপাধ্যায় (নীললোহিত)
        return " "

    core = BRACKET.sub(repl, display)
    core = re.sub(r"\s+", " ", core).strip(" ,-–")
    if any(core == e or core.endswith(" " + e) for e in ORG_ENDINGS):
        out["author_type"] = "organisation"
    for t in TRAILING_TITLES:
        if core.endswith(" " + t):
            out["rank_titles"].append(t)
            core = core[: -len(t)].strip()
    words = core.split()
    while len(words) > 1 and words[0] in TITLES:   # strip leading titles, keep at least one word
        words = words[1:]
    key = " ".join(words)
    key = MD.sub("মোহাম্মদ", key)                 # মোঃ / মো. / মুহাম্মদ … → one form for matching
    key = re.sub(r"[.,:;'\"“”‘’]", " ", key)
    out["name_key"] = re.sub(r"\s+", " ", key).strip().lower() or None
    return out


def name_key(text):
    """The matching key for any name string (Wikidata labels and aliases use the same function)."""
    return parse_author(text)["name_key"]
