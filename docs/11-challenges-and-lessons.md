# 11 Challenges and lessons learned

Problems met while building the data pipeline: how each was noticed, the root cause, the fix,
and the measured impact. Every number here was measured on the project data (RokomariBG, 127,302 unique books)
and can be reproduced with the scripts named. Written partly as interview preparation
("Tell me about a problem you faced").

**Summary:** the hardest bugs were **silent**. The code ran and the output looked like valid Bangla,
but words were being changed. They were caught by three layers: unit tests built from real data, automatic
data checks, and **reading samples by hand**. The worst bug (reversed vowel signs, #9) was found only by reading.

---

## A. Data collection

### 1. The research agent's download was incomplete
- **Symptom:** `review.json` had no `book_id`, so reviews couldn't be linked to books.
- **Cause:** only 3 of the 13 RokomariBG files had been downloaded; the link files (book↔author/category/publisher/review) were missing.
- **Fix:** listed the repo tree through the GitHub API and downloaded all 13 files. The first attempt through
  `media.githubusercontent.com` produced **empty files**, which `gzip -t` caught; `raw.githubusercontent.com` worked.
- **Lesson:** verify downloads (integrity check, expected files) instead of trusting a summary.

### 2. Boighor's book codes are not sequential
- **Symptom:** a crawler going through `eb000001, eb000002, …` found **0 books in the first 236 codes**.
- **Cause:** only recent codes (around `eb0025xx` and up) are valid book pages.
- **Fix:** read the site's JavaScript bundle, found the listing endpoint the site itself calls
  (`api.boighor.com/api/getBooksByCategorys`), and used it only to list book codes (D-014).
- **Lesson:** test a crawler on a small sample and read its log before a full run.

### 3. Crawling was slower than estimated
- Boitoi ran at about **20 pages/minute** (≈13 h for 16k books), so crawling was paused (D-015) after
  493 Boighor and 460 Boitoi pages. RokomariBG alone gives enough books. The crawler is resumable.

### 4. Author names don't match across sources
- **Symptom:** exact matching linked only **489 of 16,601** Rokomari authors to Wikidata (covering 15% of book–author links).
- **Causes:** pen names in brackets (`সুনীল গঙ্গোপাধ্যায় (নীললোহিত)`), hidden joiner characters, honorifics,
  organisations listed as authors, and common names shared by different people (`শফিকুল ইসলাম` under 3 IDs).
- **Status:** planned for S9–S10 (normalise, then fuzzy matching, then an LLM for ambiguous pairs).

---

## B. Data quality found by profiling

### 5. 58% of books have no summary
- 99.7% of summaries end with a scraped button label, `Show More`. For **73,825 books** that label is the whole summary.
- 22,118 book IDs appear 2–5 times (identical re-scrapes), so 149,515 rows become 127,302 books.
- The usable fiction catalogue is therefore about **9.8k works**, not 127k (profile report).

---

## C. Cleaning bugs (S1–S6)

### 6. An unescaped hyphen in a regex matched all of Bangla
- **Symptom:** the first run classified **39,876 summaries as "excerpt" but only 312 as "blurb"**, which is implausible.
- **Cause:** in the character class `[\"“‘'-–—]`, the hyphen between `'` and `–` makes a *range* from U+0027 to U+2013,
  which contains every Bangla character. So every text "started with dialogue".
- **Fix:** escape the hyphen. Blurbs went to 33,907. A regression test was added.
- **Lesson:** a class distribution that looks wrong is a bug signal. Check the counts before using the output.

### 7. The Unicode normaliser library damages text that isn't Bangla
- **Found by:** probing `bnunicodenormalizer` before using it.
  - `'e-গল্প'` became `'-গল্প'` (Latin letters deleted), curly quotes were dropped, and `None` came back for English words.
  - Speed: about **0.37 ms per word**, which would be close to an hour on all summaries.
- **Fix:** run it **only on runs of Bangla letters**, with a cache of unique words. The summary normalisation takes about 95 s.

### 8. The flap-label rule ate the first words of the blurb
- **Found by:** a unit test built from a real example.
- **Cause:** after `লেখা`, the pattern consumed up to 20 characters until an *optional* colon, so
  `ফ্ল্যাপে লেখা কিছু কথা ঢাকার পুরনো…` became `ো ইতিহাস…`.
- **Fix:** consume the extra words only when a colon is really present.

### 9. ⭐ Reversed vowel signs: ছোট became ছাট (the worst bug)
- **Found by:** reading 20 random cleaned fiction summaries by hand. `ছাটবেলাতেই`, `কথাগুলা` and `গাল্ডেন` looked wrong.
- **Cause:** the raw text stores **ো as া + ে (reversed order)**, an artifact of converting from old (Bijoy) encodings.
  The library's `FixDiacritics` step "repairs" this by **deleting the ে**, so the word silently changes.
- **Impact:** **8,102 summaries (63,008 words), 12 titles and 1 author name** in RokomariBG.
- **Fix:** reorder `া+ে` → `ো` (and `ৗ+ে` → `ৌ`) *before* the library runs. Two vowel signs can never be adjacent,
  so this is always safe. Regression tests and a hard validation check were added.
- **Lesson:** automatic checks couldn't catch this, because the damaged words are valid Bangla.
  **Always read samples of the output.**

### 9b. A second legacy artifact: তু written as ত্ত
- **Found by:** the validation script's consonant audit flagged `বস্ত্ত`→`বস্ত` and `প্রস্ত্ততি`→`প্রস্ততি`.
- **Cause:** legacy conversion wrote `তু` inside `স্`/`ন্` conjuncts as `ত্ত`. `স্ত্ত` and `ন্ত্ত` aren't real conjuncts, and the library dropped a letter.
- **Impact:** 23 books, 30 words (বস্তু, প্রস্তুতি, উদ্বাস্তু, আগন্তুক…). `র্ত্ত` (38 occurrences) is a real old spelling (`কর্ত্তা`) and is left alone.
- **Fix:** repair `স্ত্ত`/`ন্ত্ত` → `স্তু`/`ন্তু` first, without doubling an existing `ু` (`বস্ত্তুত`→`বস্তুত`).

### 9c. The library breaks conjuncts it doesn't know, and my audit was blind to it
- **Found by:** reading samples again. `বিষণন` wasn't in the raw text; the raw word was `বিষণ্ন`.
- **Cause:** the library's `ComplexRootNormalization` removes the hasanta from any conjunct missing from its internal list.
  My consonant audit didn't notice, because removing a hasanta keeps both consonants.
- **Measured:** it changed 742 word occurrences in a 30k-summary sample. It damaged more than it fixed:
  `অক্ষুণ্ন`→`অক্ষুণন`, `অবস্হা`→`অবসহা`, `ছ্যাঁকা`→`ছযাঁকা`. Some changes were neutral (`মাহ্দী`→`মাহদী`).
- **Fix:** disable that one step (`del _bn.decomp_level_ops["ComplexRootNormalization"]`), and add a **conjunct-preservation**
  hard check to the validation script.
- **Related legacy artifact:** `স্হ` for `স্থ` appeared in 62 books (all 45 unique words were artifacts: অবস্হা→অবস্থা, স্হান→স্থান),
  and `ন্হ` in 21 books, mostly `গ্রন্হ` for `গ্রন্থ`. `স্হ` and `গ্রন্হ` are now repaired. `সিন্হা` (a real surname spelling) and `ফিক্হ` (*fiqh*) are left alone.
- **Accepted changes, reviewed by hand:** `ত্` + consonant → `ৎ` (standard: `উত্স`→`উৎস`, 20 of 22 flagged words), one typo fix and one transliteration.
- **Lesson:** an audit only finds what it measures. Test the audit itself, and widen it when reading finds something it missed.

### 9d. "Show More" in the middle of the text
- In 3 books the scraper captured the rest of the page after the button label (`Show More Title …`, `Show More <div class=…`).
  The fix is to cut from the first `Show More` onward; a hard check confirms none remain.

### 10. NFC decomposes য়, so patterns never matched
- **Symptom:** the excerpt label `“শেষের কবিতা” বইয়ের কিছু অংশঃ` stopped matching after a rewrite.
- **Cause:** Unicode excludes `য়` (U+09DF) from composition, so NFC turns it into `য` + nukta. Patterns typed with
  the single character never match NFC text. Word lists have the same problem.
- **Fix:** run every pattern and word list through NFC where it's defined, plus a test that fails if any pattern isn't NFC.

### 11. `ঃ` is inside the Bangla Unicode block
- **Cause:** a "label word must end here" check (no Bangla character follows) rejected `অংশঃ`, because `ঃ` (visarga,
  used as a colon) is in the same block as letters.
- **Fix:** exclude U+0983 from the check.

### 12. Label words matched inside longer words
- **Symptom:** `সূচিপত্রের কিছু অংশ…` became `ের কিছু অংশ…`; 16 summaries started mid-word.
- **Cause:** the pattern for `সূচি` matched the start of `সূচিপত্রের`, and an optional "title" prefix could be any 80 characters.
- **Fix:** labels must end at a word boundary, and the title prefix must be in quotes. Mid-word starts: 16 → 0.

### 13. Quoted titles read as dialogue
- **Symptom:** 4,316 of the 6,281 "excerpts" actually began `"বইয়ের নাম" বইটি…` (a blurb about the book).
- **Fix:** a quoted title followed by বইটি/গ্রন্থ counts as a blurb, and dialogue needs at least 2 dialogue lines.

### 14. HTML leftovers
- The scraper removed angle brackets but left the tag names: `bফ্ল্যাপে লেখা কিছু কথা/bbr`. About 81 summaries were affected, and 4 still had real tags.
- **Fix:** remove the fragments only when no Latin letter touches them and Bangla is nearby, so English words like "b" or "br-code" survive. Residue left: 2.

### 15. Some raw data is already broken
- Example: a summary starts `হরের পুরনো গলি…` in the raw data (the first letter of `শহরের` is missing).
  Typos like `শেস` (শেষ) and `বিশার` (বিশাল) are also in the source. Each was checked against the raw text
  before blaming the source; `বিষণন` looked like the same kind of source typo but was our bug (#9c).

### 16. Tooling: an invisible backspace character in the code
- A scripted patch written through a shell heredoc turned `\b` into a literal backspace (U+0008) inside a regex.
  The code looked right when printed, but the pattern couldn't match. Tests caught it, and `cat -A` showed the `^H`.
- **Fix:** edit code files directly, not through a shell string, and scan for control characters.

---

## D. Accepted limitations (measured, not fixed)
| Limitation | Measured | Why accepted |
|---|---|---|
| Spelling modernisation by the normaliser (`ধৈর্য্য`→`ধৈর্য`, `কর্ম্ম`→`কর্ম`) | 357 unique words / 714 occurrences in all summaries + titles | Correct modern spelling; improves matching |
| Missed label variants in blurbs | 171 of 38,698 blurbs (counting all three spellings of "flap") | 0.4%; the text is still a usable blurb |
| Narrative openings counted as blurbs | excerpt class = 19 | Rules can't tell an opening scene from flap copy; an LLM check on a sample is planned for labelling |

---

### 17. Code-quality pass (`/simplify`)
- Four reviews (reuse, simplification, efficiency, altitude) found duplicated constants between the cleaner and the
  validator (so a fix in one wouldn't reach the other), a stat counted with a different regex from the rule it reports on
  (it missed the 3 mid-text "Show More" cases), and a hand-written NFC test list.
- The NFC test now **walks every module constant** instead of a hand-written list. It immediately found one more pattern,
  a consonant range with literal `ড়`/`য়` endpoints, which would have broken under NFC.
- **Behaviour check:** the pipeline was rerun and its report diffed against the run before the refactor. The only changes
  were intended (+3 Show More count, +516 flap texts from the added `ফ্লাপ` spelling, confirmed by count).

## E. S7–S12: categories, origin, authors, works

### 18. "story" matched inside "History": history books counted as fiction
- **Found by:** listing categories whose names matched the fiction keywords before writing the S7 rules.
  "History and Tradition" (1,216 books), "Islamic History" and dozens more were on the list.
- **Impact:** the earlier headline figures (9,804, then 9,497 "fiction works") included history non-fiction.
- **Fix:** every keyword matches whole words only, plus a hard validation check that no "History" category is mapped
  (except "Historical Novel/Story").
- **Lesson:** a substring match on English words is a bug waiting to happen; check keyword hits by reading them.

### 19. Keyword rules had false positives that only reading caught
- Reading all 190 mapped categories found 5 wrong ones:
  - `Artificial Intelligence & Robotics` became spy fiction (via "Intelligence")
  - `Kindergarten: Play Group` became drama (via "Play")
  - a mixed "Novel, Poem, Short Story & Drama Collection" got format poetry
  - "…Translated & English" was flagged as English-language
  - `Fables` categories were missed
- Each was fixed in the rule, not patched per category, and each has a regression test.

### 20. Wikidata linking: 70% precision on the first try
- **Found by:** hand-checking 40 random links. Only about 28 of 40 were clearly correct.
- **Causes:**
  1. Wikidata's own aliases include truncated names (`ফয়েজ আহমদ` is an alias of Faiz Ahmad Taiyeb, b. 1982, and collides with the journalist Foyez Ahmad).
  2. Bracketed nicknames (`(রফিক)`, `(রাসেল)`) linked to unrelated people.
  3. Common names: textbook authors matched a Wikidata writer with the same name.
- **Fix:** skip aliases that are truncations of the label; no linking through nicknames; link only authors of fiction books;
  never link when several Rokomari authors share the name.
- **Result:** a new random sample of 40 had 37 correct, 3 unverifiable and 0 wrong. Coverage dropped (600 → 357 linked
  Rokomari authors), but the links that matter survive (Humayun Ahmed, Tagore, Satyajit Ray, Sunil, and pen names such as
  বনফুল → Balai Chand Mukhopadhyay).
- **Lesson:** precision beats coverage for links. A wrong link spreads wrong facts (nationality, dates) to every book.

### 21. Over-merging editions into works
- **Symptom:** the largest "work" had 336 editions. It was titled `Book`, and consisted of unrelated items.
- **Causes:** placeholder titles, and 46,610 editions with no author link being merged by title alone. That joined
  different manga volumes (`One Piece` 57, `Case Closed` 72) and a truncated title (`আল`, 73).
- **Fix:** never merge without an author or with a placeholder title. After the fix, the largest group is
  *পথের পাঁচালী* (96 real reprints).

### 22. Volumes missing from titles
- **Symptom:** `বিমল কুমার সমগ্র` (4 editions, 312–1,176 pages) and `নিশুতি` merged separate volumes.
- **Found by:** comparing page counts inside merged groups, then reading the URL slugs:
  `bimal-kumar-samagara-2`, `nishuti-3…6`.
- **Check before using it:** slugs in known-good groups (*পথের পাঁচালী*, *নৌকাডুবি*) never end in a number, so a trailing
  number is a volume, not a uniqueness suffix. It's used only when the title gives no volume.
- **Remaining:** issues that differ only by subtitle (`রোমাঞ্চ`: apode / taboo / ishwari) still merge.

### 23. What "origin" means
- **Symptom:** Bibhutibhushan's *লবটুলিয়ার কাহিনি* was labelled Bangladesh, because a Dhaka publisher reprinted it.
- **Decision:** origin is **literary origin** (where the author is from), not where this edition was printed. The main
  author's Wikidata nationality now outranks publisher, category and ISBN evidence.
- **Subtlety:** pre-1947 authors are only "British Raj" in Wikidata (Tagore, Mir Mosharraf Hossain), which says nothing
  about today's border, so that gives no signal and the book-level evidence decides.
- Also: English-language Indian editions (*Salem's Lot* from an Indian publisher) were labelled West Bengal; English books
  now get `english_language` and are excluded from the Bangla catalogue.

### 24. Performance: a Python loop over 116k groups
- The first S11 version sorted each work group separately and didn't finish in 10 minutes. The vectorised version
  (sort once, `drop_duplicates`, `groupby` aggregations) runs in about 80 seconds with the same logic.

## How validation works
1. **Unit tests** (171 tests in `tests/`): real messy values from the data, plus a regression test for every bug above.
2. **Validation script** (`python -m scripts.clean.validate_s1_s6` → [report](reports/validation-s1-s6.md)): hard invariants on every row.
   - Examples: IDs unique; the cleaned summary is a substring of the raw summary, so nothing is invented;
     no reversed vowel signs; normalising twice changes nothing; every ISBN passes its checksum;
     no consonant or conjunct is lost except reviewed patterns.
   - 18 hard checks for S1–S6 and 22 for S7–S12 (`validate_s7_s12`). Each script exits with an error if any fails. The two word-level audits use a 20k-summary sample; the others check every row.
3. **Reading samples** of every class after each change. This caught #9, #12 and #13.

## Interview talking points
- *"The most dangerous bugs were silent."* The reversed-vowel bug changed 63k words, and every automatic check passed,
  because `ছাট` is a valid Bangla word. I found it by reading output samples, then wrote a check so it can't come back.
- *"Don't trust a library blindly."* The standard Bangla normaliser deletes Latin text, deletes vowel signs on
  legacy-encoded input, and breaks conjuncts it doesn't know (বিষণ্ন→বিষণন). I wrapped it: Bangla-only runs,
  legacy repairs first, one harmful step disabled after measuring it, and audits of every consonant and conjunct it removes.
- *"An audit only finds what it measures."* My consonant audit passed while conjuncts were being broken. Reading samples
  exposed the gap, so I added a conjunct check.
- *"Unicode details matter."* NFC decomposes `য়`, `ঃ` is in the letter block, and an unescaped hyphen matched all of Bangla.
- *"Measure before you trust."* A class split of 39,876 vs 312 was the signal that a rule was broken.
