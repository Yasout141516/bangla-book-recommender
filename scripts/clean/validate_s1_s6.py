"""Validate the S1-S6 output (data/interim/rokomari_books.parquet) against its raw input.

Usage:  python -m scripts.clean.validate_s1_s6
Output: docs/reports/validation-s1-s6.md, and exit code 1 if any hard check fails.

Hard checks are invariants that must hold for every row (the two word-level audits use a
20k-summary sample). Soft checks count known, accepted limitations so they stay visible.
"""
import gzip
import json
import re
import sys
import unicodedata
from pathlib import Path

import pandas as pd

from scripts.clean import text as T
from scripts.clean.rokomari_books import OUT as INTERIM, RAW, ROOT

REPORT = ROOT / "docs" / "reports" / "validation-s1-s6.md"
AUDIT_SAMPLE = 20_000

# Accepted consonant/conjunct removals by the normaliser:
#  - doubled conjuncts: old spellings after র (ধৈর্য্য→ধৈর্য) and typos (সমস্য্যা→সমস্যা, সম্পর্র্কে→সম্পর্কে)
#  - ত্ + consonant → ৎ (khanda-ta, standard spelling: উত্স→উৎস)
#  - words reviewed by hand on 2026-09-26, pinned to the output that was approved
DOUBLED = re.compile(r"্(.)্\1|(.)্\2্")
CONJUNCT = re.compile(r"[ক-হড়-য়](?=্[ক-হড়-য়])")
REVIEWED_OK = {"স্ব্প্নকল্পনার": "স্বপ্নকল্পনার",   # extra-hasanta typo fixed
               "সুব্হ্": "সুবহ"}                     # neutral transliteration of Arabic subh


def accepted(word, out):
    return bool(DOUBLED.search(word)) or ("ত্" in word and "ৎ" in out) or REVIEWED_OK.get(word) == out


def raw_book_ids():
    with gzip.open(RAW, "rt", encoding="utf-8") as fh:
        return [r["book_id"] for r in json.load(fh)]


def audit_words(summaries):
    """One pass over the unique words: which lose a consonant, which lose a conjunct, unexplained."""
    words = {w for s in summaries for w in T.bn_words(s)}
    lost_consonant, unexplained_consonant, broken_conjunct = [], [], []
    for w in words:
        out = T._normalize_bn_word(w)
        w_nfd, out_nfd = unicodedata.normalize("NFD", w), unicodedata.normalize("NFD", out)
        ok = accepted(w, out)
        if len(T.BN_CONSONANT.findall(out_nfd)) < len(T.BN_CONSONANT.findall(w_nfd)):
            lost_consonant.append(w)
            if not ok:
                unexplained_consonant.append(w)
        if len(CONJUNCT.findall(out_nfd)) < len(CONJUNCT.findall(w_nfd)) and not ok:
            broken_conjunct.append(w)
    return lost_consonant, unexplained_consonant, broken_conjunct


def main():
    df = pd.read_parquet(INTERIM)
    ids = raw_book_ids()
    results = []  # (kind, name, passed, detail)

    def check(kind, name, passed, detail=""):
        results.append((kind, name, bool(passed), detail))

    summ = df.summary_clean.fillna("")
    title = df.title_clean.fillna("")

    # --- row-level invariants ---
    check("hard", "book_id is unique", df.book_id.is_unique)
    n_raw = len(set(ids))
    check("hard", "row count equals unique raw book_ids", len(df) == n_raw, f"{len(df):,} vs {n_raw:,}")
    check("hard", "every raw book_id is present", set(ids) == set(df.book_id))

    has = df.summary_clean.notna()
    not_sub = sum(c not in f for c, f in zip(df.summary_clean[has], df.summary_norm[has]))
    check("hard", "summary_clean is a substring of the normalised raw summary (nothing invented)",
          not_sub == 0, f"{not_sub:,} violations")

    check("hard", "no 'Show More' left in summaries", not summ.str.contains("Show More").any())
    reversed_pat = "|".join(bad for bad, _ in T.REVERSED_VOWELS)
    check("hard", "no reversed vowel signs (া+ে / ৗ+ে) left",
          not summ.str.contains(reversed_pat).any() and not title.str.contains(reversed_pat).any())
    joiners = "‌|‍"
    check("hard", "no ZWJ/ZWNJ left in cleaned text",
          not summ.str.contains(joiners).any() and not title.str.contains(joiners).any())
    mid = summ.map(lambda s: bool(s) and unicodedata.category(s[0]) in ("Mn", "Mc"))
    check("hard", "no summary starts with a combining mark (cut mid-word)", mid.sum() == 0, f"{mid.sum()}")

    sample = df.summary_clean.dropna().sample(5000, random_state=0)
    idem = sum(T.normalize_bn(s) != s for s in sample)
    check("hard", "normalisation is idempotent (5,000-row sample)", idem == 0, f"{idem} changed on a second pass")
    nfc = sum(not unicodedata.is_normalized("NFC", s) for s in sample)
    check("hard", "cleaned summaries are NFC (5,000-row sample)", nfc == 0, f"{nfc}")

    check("hard", "every isbn13 passes its checksum",
          df.isbn13.dropna().map(lambda x: T.normalize_isbn(x) == (x, True)).all())
    check("hard", "isbn_valid is true exactly when isbn13 is set", (df.isbn_valid == df.isbn13.notna()).all())
    check("hard", "rating_avg is null or within [1, 5]", df.rating_avg.dropna().between(1, 5).all())
    usable = df[df.summary_usable]
    check("hard", "usable summaries meet the length rule",
          all(T.summary_usable(c, s) for c, s in zip(usable.summary_class, usable.summary_clean)))

    # Title: every word of the cleaned title must come from the normalised raw title.
    norm_raw = df.title_raw.map(lambda t: T.normalize_whitespace(T.normalize_bn(t)) if t else "")
    bad_title = sum(any(w not in r for w in c.split()) for c, r in zip(title, norm_raw))
    check("hard", "cleaned title words all come from the raw title", bad_title == 0, f"{bad_title}")
    check("hard", "no title emptied", df.title_raw[df.title_clean.isna()].isna().all())

    # --- normaliser audit: consonants and conjuncts must survive, except accepted patterns ---
    lost, unexplained, broken = audit_words(df.summary_raw.dropna().sample(AUDIT_SAMPLE, random_state=1))
    check("hard", f"normaliser removes consonants only in accepted patterns ({AUDIT_SAMPLE:,}-summary sample)",
          not unexplained, f"{len(lost)} words lost a consonant; unexplained: {unexplained[:5]}")
    # A consonant count misses a broken conjunct: বিষণ্ন → বিষণন keeps both consonants.
    check("hard", f"no conjunct is broken except accepted patterns ({AUDIT_SAMPLE:,}-summary sample)",
          not broken, f"{len(broken)} words, e.g. {[(w, T._normalize_bn_word(w)) for w in broken[:4]]}")

    # --- soft checks (known limitations) ---
    blurb_start = summ[df.summary_class == "blurb"].str[:120]
    flap_left = blurb_start.str.contains("|".join(T.FLAP_WORDS)).sum()
    check("soft", "blurbs still containing a flap word in the first 120 chars (missed label variants)",
          True, f"{flap_left:,} of {len(blurb_start):,}")
    check("soft", "tag residue (/bbr, br+Bangla) left", True,
          f"{summ.str.contains(r'(?<![A-Za-z])/?bbr|(?<![A-Za-z])br(?=[ঀ-৿])', regex=True).sum()}")
    check("soft", "excerpt class is small because rules can't tell narrative openings from blurbs", True,
          f"excerpt={int((df.summary_class == 'excerpt').sum())}")

    hard = [r for r in results if r[0] == "hard"]
    passed = sum(r[2] for r in hard)
    lines = ["# Validation report: S1–S6", "",
             "Generated by `python -m scripts.clean.validate_s1_s6`. Hard checks must all pass.", "",
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
