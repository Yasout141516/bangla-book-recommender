"""Text helpers for cleaning (spec: docs/10-cleaning-spec.md, steps S2-S6).

All functions are pure (no I/O) and tested in tests/test_text.py.
"""
import re
import unicodedata
from functools import lru_cache

from bnunicodenormalizer import Normalizer

_bn = Normalizer()
# ComplexRootNormalization breaks every conjunct missing from the library's own list. Measured on a
# 30k-summary sample it damaged more words than it fixed: অক্ষুণ্ন→অক্ষুণন, অবস্হা→অবসহা, ছ্যাঁকা→ছযাঁকা.
# Conjuncts are kept as written; the known legacy forms are repaired in repair_legacy_encoding instead.
del _bn.decomp_level_ops["ComplexRootNormalization"]


def _nfc(s):
    """Patterns and word lists must be in the same Unicode form as the cleaned text.
    NFC decomposes য় (U+09DF) into য + nukta, so a pattern typed with য় would never match."""
    return unicodedata.normalize("NFC", s)


def _re(pattern, flags=0):
    return re.compile(_nfc(pattern), flags)


def _nfc_words(*words):
    return tuple(_nfc(w) for w in words)


def _nfc_map(mapping):
    return {_nfc(k): v for k, v in mapping.items()}


# A run of Bangla-script characters, including the joiners that sit inside Bangla words.
BN_RUN = re.compile(r"[ঀ-৿‌‍]+")
# Bangla letters and signs only: the block also holds digits (U+09E6-U+09EF), which are not letters.
BN_LETTER = re.compile(r"[ঀ-৥ৰ-৿]")
LATIN_LETTER = re.compile(r"[A-Za-z]")
# Consonants, including ড় ঢ় য় and ৎ.
BN_CONSONANT = re.compile(r"[\u0995-\u09B9\u09DC-\u09DF\u09CE]")  # ASCII escapes: ড় য় are not NFC-stable
BN_DIGITS = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")
# The scraped "Show More" button label. In 3 books the rest of the page follows it
# ("Show More Title …", "Show More <div …"), so everything from it onward is dropped.
SHOW_MORE = re.compile(r"\s*Show More\b.*\Z", re.S)


# ---------- S2: text normalisation ----------

@lru_cache(maxsize=500_000)
def _normalize_bn_word(word):
    out = _bn(word)["normalized"]
    # The library returns None when it can't normalise; keep the original then.
    return word if out is None else out


# Two-part vowel signs stored in reversed order (a legacy-encoding conversion artifact):
# া + ে should be ো, and ৗ + ে should be ৌ. bnunicodenormalizer "fixes" these by deleting the ে,
# turning ছোট into ছাট (found in 8,102 RokomariBG summaries), so reorder them first.
# Two vowel signs never legitimately sit next to each other, so this is always safe.
REVERSED_VOWELS = [("\u09be\u09c7", "\u09cb"), ("\u09d7\u09c7", "\u09cc")]
# Legacy conversion also wrote তু inside স্ / ন্ conjuncts as ত্ত: বস্ত্ত for বস্তু, প্রস্ত্ততি for প্রস্তুতি
# (23 books). স্ত্ত and ন্ত্ত are not real conjuncts; the library drops a letter (বস্ত). র্ত্ত is a real old
# spelling (কর্ত্তা) and is left alone.
LEGACY_TU = re.compile("([সন]\u09cd\u09a4)\u09cd\u09a4\u09c1?")
# Legacy conversion also wrote থ as হ inside conjuncts. স্হ was an artifact in all 45 unique words found
# (অবস্হা→অবস্থা, স্হান→স্থান). ন্হ is only repaired in গ্রন্হ, because সিন্হা is a real surname spelling.
LEGACY_THA = [("স\u09cd\u09b9", "স\u09cd\u09a5"), ("গ্রন\u09cd\u09b9", "গ্রন\u09cd\u09a5")]


def repair_legacy_encoding(text):
    for bad, good in REVERSED_VOWELS + LEGACY_THA:
        text = text.replace(bad, good)
    return LEGACY_TU.sub("\\1\u09c1", text)


def _prepare(text):
    """The steps before the library runs: legacy repairs, then NFC."""
    return unicodedata.normalize("NFC", repair_legacy_encoding(text))


def bn_words(text):
    """The Bangla word runs exactly as the library sees them (used by the validation audits)."""
    return BN_RUN.findall(_prepare(text))


def normalize_bn(text):
    """Unicode-normalise Bangla text.

    bnunicodenormalizer runs only on Bangla-script runs, because on mixed tokens it deletes
    Latin letters and quotes ('e-গল্প' -> '-গল্প'). Everything else passes through unchanged.
    Legacy-encoding artifacts are repaired first. Leftover ZWJ/ZWNJ are removed. The result is NFC.
    """
    if not text:
        return text
    text = BN_RUN.sub(lambda m: _normalize_bn_word(m.group(0)), _prepare(text))
    text = text.replace("‌", "").replace("‍", "")
    return unicodedata.normalize("NFC", text)


def normalize_whitespace(text):
    if not text:
        return text
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\xa0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def strip_show_more(text):
    return SHOW_MORE.sub("", text or "").strip()


HTML_TAG = re.compile(r"<\s*/?\s*[A-Za-z][^<>]{0,40}>")
# Leftovers of <b>, </b>, <br> whose angle brackets were stripped by the scraper: "bফ্ল্যাপে…/bbr".
TAG_RESIDUE = re.compile(r"(?<![A-Za-z])(?:/?br?/?)+(?![A-Za-z])")


def strip_html(text):
    """Remove real tags, and tag residue only where it touches Bangla text or the string edge,
    so an English 'b' or 'br' between Latin words is left alone."""
    text = HTML_TAG.sub(" ", text)

    def repl(m):
        # TAG_RESIDUE already ensures no Latin letter touches the match; also require Bangla nearby.
        window = text[max(0, m.start() - 20):m.end() + 20]
        return " " if BN_LETTER.search(window) else m.group(0)

    return TAG_RESIDUE.sub(repl, text)


def clean_text(text):
    """Full S2 pipeline for a free-text field. Empty results become None."""
    if text is None:
        return None
    out = normalize_whitespace(normalize_bn(strip_html(strip_show_more(text))))
    return out or None


# ---------- S3: field normalisation ----------

def bn_digits_to_ascii(text):
    return text.translate(BN_DIGITS) if text else text


def _isbn10_ok(d):
    if not re.fullmatch(r"\d{9}[\dX]", d):
        return False
    total = sum((10 - i) * (10 if c == "X" else int(c)) for i, c in enumerate(d))
    return total % 11 == 0


def _isbn13_sum(d):
    return sum(int(c) * (1 if i % 2 == 0 else 3) for i, c in enumerate(d))


def _isbn13_ok(d):
    return bool(re.fullmatch(r"\d{13}", d)) and _isbn13_sum(d) % 10 == 0


def isbn_digits(raw):
    """Digits (and X) only, Bangla digits converted: '978-984-7760-49-0' -> '9789847760490'."""
    return re.sub(r"[^0-9Xx]", "", bn_digits_to_ascii(str(raw))).upper() if raw else ""


def normalize_isbn(raw):
    """Return (isbn13 or None, is_valid). Accepts ISBN-10 or ISBN-13 with hyphens or spaces."""
    if not raw:
        return None, False
    d = isbn_digits(raw)
    if len(d) == 13 and _isbn13_ok(d):
        return d, True
    if len(d) == 10 and _isbn10_ok(d):
        core = "978" + d[:9]
        check = (10 - _isbn13_sum(core) % 10) % 10
        return core + str(check), True
    return None, False


def isbn_origin(isbn13):
    """Registration group: 984 = Bangladesh, 81 / 93 = India."""
    if not isbn13:
        return None
    body = isbn13[3:]
    if body.startswith("984"):
        return "bangladesh"
    if body.startswith(("81", "93")):
        return "india"
    return "other"


# ---------- S4: script detection ----------

def script_of(text, threshold=0.7):
    """'bangla' / 'latin' / 'mixed' by share of letters; None when there are no letters."""
    if not text:
        return None
    bn = len(BN_LETTER.findall(text))
    la = len(LATIN_LETTER.findall(text))
    if bn + la == 0:
        return None
    if bn / (bn + la) >= threshold:
        return "bangla"
    if la / (bn + la) >= threshold:
        return "latin"
    return "mixed"


# ---------- S5: title cleaning ----------

BINDING = _nfc_map({"paperback": "paperback", "hardcover": "hardcover", "হার্ডকভার": "hardcover",
                    "পেপারব্যাক": "paperback"})
PAPER = _nfc_map({"সাদা": "white", "নিউজ": "newsprint", "অফসেট": "offset"})
BUNDLE_MARKERS = _nfc_words("রকমারি কালেকশন", "প্যাকেজ", "সেট", "কম্বো", "বক্স সেট", "Box Set", "Combo", "Package")
COLLECTION_WORDS = _nfc_words("সমগ্র", "রচনাবলী", "রচনাবলি", "অখণ্ড", "সংকলন", "অমনিবাস", "Omnibus")
SERIES_WORDS = _nfc_words("সিরিজ", "Series", "series")
# Store labels that are not part of the title.
MARKETING = _nfc_words("রকমারি কালেকশন", "পুরস্কারপ্রাপ্ত লেখকদের বই", "সিডি সহ", "CD সহ", "ফ্রি", "অফার")
LANGUAGE = _nfc_map({"বাংলা": "bn", "ইংরেজি": "en", "ইংলিশ": "en", "english": "en", "bangla": "bn", "bengali": "bn"})
# "(২য় খণ্ড)", "(Vol. 3)", or a bare "(২)".
VOLUME = _re(r"^\s*(?:Vol\.?|Volume|Part)?\s*(?P<n>[০-৯\d]+)\s*(?:ম|য়|র্থ|ষ্ঠ|তম|st|nd|rd|th)?\s*(?:খণ্ড|খন্ড|পর্ব|ভাগ|Volume|Vol\.?|Part)?\s*$", re.I)
PAREN = _re(r"\(([^()]*)\)|\[([^\[\]]*)\]")


def clean_title(raw):
    """S5. Returns a dict: title_clean, binding, paper, volume, series_hint, language_hint,
    is_bundle, is_collection.

    Parenthetical parts are classified; known noise is moved out of the title, and anything
    unknown (e.g. religious honorifics like (সা.)) stays in the title.
    """
    out = {"title_clean": None, "binding": None, "paper": None, "volume": None,
           "series_hint": None, "language_hint": None, "is_bundle": False, "is_collection": False}
    if not raw:
        return out
    t = normalize_whitespace(normalize_bn(raw))
    out["is_bundle"] = any(m.lower() in t.lower() for m in BUNDLE_MARKERS)

    def repl(m):
        inner = (m.group(1) if m.group(1) is not None else m.group(2)).strip()
        low = inner.lower()
        if low in BINDING:
            out["binding"] = BINDING[low]
            return " "
        if inner in PAPER:
            out["paper"] = PAPER[inner]
            return " "
        vm = VOLUME.match(inner)
        if vm:
            out["volume"] = int(bn_digits_to_ascii(vm.group("n")))
            return " "
        if low in LANGUAGE:
            out["language_hint"] = LANGUAGE[low]
            return " "
        if any(w in inner for w in SERIES_WORDS):
            out["series_hint"] = inner
            return " "
        if any(w in inner for w in MARKETING):
            return " "
        return m.group(0)

    t = PAREN.sub(repl, t)
    out["is_collection"] = any(w in t for w in COLLECTION_WORDS)
    out["title_clean"] = re.sub(r"\s+", " ", t).strip(" -–—,:") or None
    return out


# ---------- S6: summary classification ----------

# Leading labels Rokomari puts in front of the summary text.
_QUOTES = "\"'“”‘’"
_Q = rf"[{_QUOTES}]"
_QUOTED = rf"{_Q}[^{_QUOTES}\n]{{1,80}}{_Q}"               # a quoted book title: “শেষের কবিতা”
_TITLE = rf"(?:{_QUOTED}\s*)?"
_BOOK = r"(?:বইটির|বইটিতে|বইয়ের|বই\s*এর|বইএর|বইটি|গ্রন্থটির|গ্রন্থের)"
# The label word ends here, not inside a longer word. ঃ (U+0983) is in the Bangla block but is used as a colon.
_NOT_BN = r"(?![ঀ-ং঄-৿])"
_END = r"\s*[:ঃ\-–—]?\s*"


def _label(words, book="optional"):
    b = {"optional": rf"(?:{_BOOK}\s*)?", "required": rf"{_BOOK}\s*", "none": ""}[book]
    return _re(rf"^\W*{_TITLE}{b}(?:{words}){_NOT_BN}{_END}")


# Spellings of "flap" seen in the data; also used by the validation soft check.
FLAP_WORDS = _nfc_words("ফ্ল্যাপ", "ফ্যাপ", "ফ্লাপ")

# Checked in order; the first match wins.
LABELS = [
    # The flap label may end with a few more words before a colon ("…ফ্ল্যাপ থেকে নেওয়াঃ").
    # Consume them only when the colon is really there, otherwise the blurb's first words are eaten.
    ("flap", _label(rf"(?:লেখা\s*)?(?:প্রথম|দ্বিতীয়|শেষের|শেষ)?\s*(?:{'|'.join(FLAP_WORDS)})(?:-?এর|ে|ের)?(?:\s*(?:লেখা|লিখা|থেকে))?(?:\s*(?:নেওয়া|নেয়া))?(?:\s*কিছু)?(?:\s*কথা)?"
                    r"(?:[^\n:ঃ]{0,20}[:ঃ])?")),
    ("toc", _label(r"(?:সূচিপত্র|সূচীপত্র|সূচি|সূচী)(?:র|ের)?(?:\s*কিছু\s*অংশ)?|বইটিতে\s*যা\s*যা\s*(?:রয়েছে|আছে)")),
    ("blurb", _label(r"সম্পর্কে\s*(?:কিছু\s*)?কথা", book="required")),
    ("excerpt", _label(r"(?:কিছু\s*|একটি\s*)?(?:অংশবিশেষ|অংশ)", book="required")),
    ("summary", _label(r"সংক্ষিপ্ত\s*বিবরণী?|সারসংক্ষেপ|সারাংশ")),
    ("preface", _label(r"ভূমিকা|মুখবন্ধ|প্রসঙ্গকথা|প্রাককথন|লেখকের\s*কথা|শুরুর\s*কথা")),
    ("author_bio", _label(r"লেখক\s*পরিচিতি|লেখকের\s*পরিচয়", book="none")),
]
# A later label inside the text: cut there, so a flap text followed by a TOC keeps only the flap part.
TAIL_CUT = _re(rf"\s(?:সূচিপত্র|সূচীপত্র|সূচি\s*[:ঃ]|লেখক\s*পরিচিতি){_NOT_BN}")
# The hyphen must be escaped: unescaped, "'-–" is a character range that covers all of Bangla.
DIALOGUE_START = _re(r"^\s*[\"“‘'\-–—]")
# "“X” বইটি …" starts with a quote but is a blurb about the book, not dialogue.
QUOTED_TITLE_START = _re(
    rf"^\s*{_QUOTED}\s*(?:{_BOOK}|গ্রন্থটি|গ্রন্থ|উপন্যাসটি|উপন্যাস|গল্পগ্রন্থ|কাব্যগ্রন্থ|সিরিজ)")
USABLE_MIN = {"flap": 200, "blurb": 200, "summary": 200, "excerpt": 500}


def _cut_tail(text):
    return TAIL_CUT.split(text, maxsplit=1)[0].strip()


def classify_summary(text):
    """S6. Returns (summary_class, cleaned_text).

    Expects text that has already been through clean_text (NFC): the label patterns are NFC,
    so un-normalised input containing য় would silently miss them.
    Classes: empty, flap, blurb, summary, excerpt, toc, preface, author_bio, english.
    The leading label is removed from the returned text.
    """
    if not text:
        return "empty", None
    for cls, pat in LABELS:
        m = pat.match(text)
        if m:
            body = text[m.end():].strip()
            if cls in ("flap", "blurb", "excerpt", "summary"):
                body = _cut_tail(body)
            return (cls, body) if body else ("empty", None)
    if script_of(text) == "latin":
        return "english", text
    bullets = len(re.findall(r"(?:^|\s)[*•●■]\s", text))
    if bullets >= 5:
        return "toc", text
    lines = [ln for ln in text.split("\n") if ln.strip()]
    dialogue_lines = sum(bool(DIALOGUE_START.match(ln)) for ln in lines)
    if (DIALOGUE_START.match(text) and not QUOTED_TITLE_START.match(text)
            and dialogue_lines >= 2 and dialogue_lines / len(lines) >= 0.3):
        return "excerpt", text
    return "blurb", _cut_tail(text)


# ---------- S12: source-text quality ----------

_CONS_G = r"[\u0995-\u09b9\u09dc-\u09df\u09ce]\u09bc?"          # consonant (+ nukta); ASCII escapes because ড়/য় endpoints are not NFC-stable
_SHIFTED = "িে"                                        # ি ে: the signs seen shifted in the data
LIST_ITEM = re.compile(r"(?:^|\s)[০-৯\d]{1,2}\s*[.:)\-]\s")
LIST_ITEM_TEXT = re.compile(r"(?:^|\s)[০-৯\d]{1,2}\s*[.:)\-]\s*[^০-৯\d]{0,70}")


def unshift_vowels(word):
    """Undo a source artifact where ি/ে sits one consonant too far right: গছেনে → গেছেন, মানুষরে → মানুষের."""
    parts = re.findall(_CONS_G + "|.", word, flags=re.S)
    out, j = [], 0
    while j < len(parts):
        if (j + 1 < len(parts) and re.fullmatch(_CONS_G, parts[j]) and parts[j + 1] in _SHIFTED
                and out and re.fullmatch(_CONS_G, out[-1])):
            prev = out.pop()
            out += [prev, parts[j + 1], parts[j]]
            j += 2
        else:
            out.append(parts[j])
            j += 1
    return "".join(out)


def displaced_vowel_words(text, common_words):
    """Words that are not common but become a common word once ি/ে is moved back (see unshift_vowels)."""
    # 4+ characters: the 3-character false positives were names and real words (টমি, জনি, সনে, কনে).
    words = [w for w in re.findall(r"[\u0980-\u09FF]+", text or "") if len(w) >= 4]
    bad = [w for w in words if w not in common_words and unshift_vowels(w) != w and unshift_vowels(w) in common_words]
    return bad, len(words)


def is_garbled(text, common_words):
    """Garbled source text: >5% displaced-vowel words, or 3+ different ones. Measured on the catalogue:
    8/8 above 5% were garbled; 1–2 hits were mostly names (টমি, জনি) or real words (সনে, কনে)."""
    bad, n = displaced_vowel_words(text, common_words)
    return len(bad) / max(n, 1) > 0.05 or len(set(bad)) >= 3


def is_list_summary(text):
    """A summary that is essentially a numbered list (4+ items, <150 chars of prose outside the items).
    Of 54 catalogue summaries with a numbered list, 53 are blurbs that contain a list and are kept."""
    if not text or len(LIST_ITEM.findall(text)) < 4:
        return False
    prose = re.sub(r"\s+", " ", LIST_ITEM_TEXT.sub(" ", text)).strip()
    return len(prose) < 150


def summary_usable(cls, text):
    return bool(text) and len(text) >= USABLE_MIN.get(cls, 10**9)
