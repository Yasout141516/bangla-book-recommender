# 10 Cleaning specification (RokomariBG first)

A detailed specification of the cleaning pipeline. Each step lists **what** it does, **why**, **how**,
**real examples** from the data, the **output fields** and a **check** that must pass. Numbers come from
[the profile report](reports/rokomaribg-profile.md) and from sampling on 2026-09-26.

**Implementation status (2026-09-26):** S1–S6 are implemented in `scripts/clean/` and validated
([report](reports/validation-s1-s6.md)). While building them, S2 gained steps this spec didn't foresee:
legacy-encoding repairs (reversed vowel signs, ত্ত→তু, স্হ→স্থ), HTML residue removal, and disabling one harmful
library step. See [11 Challenges and lessons](11-challenges-and-lessons.md).

**S7–S12 are implemented too** ([validation](reports/validation-s7-s12.md)). Differences from the plan below, each in the
decision log:
- S7 gives **genre hints**, not final genres (D-018)
- `drama` was added as a format (D-019)
- Wikidata linking uses evidence rules, and the fuzzy-matching and LLM steps weren't needed yet (D-020)
- origin means literary origin, with the author's nationality first (D-021)
- editions merge only with a known author, with the URL slug as a volume source (D-022)

**Run order:**
```
python -m scripts.clean.rokomari_books      # S1–S6  → data/interim/rokomari_books.parquet
python -m scripts.clean.build_category_map  # S7 map → data/mappings/category_map.csv (committed)
python -m scripts.clean.categories_origin   # S7–S8  → data/interim/rokomari_books_s8.parquet
python -m scripts.clean.authors             # S9–S10 → data/interim/authors.parquet
python -m scripts.clean.works               # S11–S12 → data/processed/{works,editions,authors}.parquet
python -m scripts.clean.validate_s1_s6 && python -m scripts.clean.validate_s7_s12
```

Principles:
- Raw data is never modified. Every step reads the previous stage and writes a new one.
- Every transformation is **reversible or recorded**: keep the original value next to the cleaned value.
- Rules are applied in order, and every rule counts how many rows it changed. The pipeline prints these counts.
- When in doubt, **flag, don't delete**. Filtering happens once, at the end (step 12).

```
raw/rokomaribg/*.json.gz
  │  S1  load + deduplicate rows
  │  S2  text normalisation (Unicode, whitespace, artifacts)
  │  S3  field normalisation (ISBN, numbers, nulls)
  │  S4  script / language detection
  │  S5  title cleaning
  │  S6  summary classification + cleaning
  │  S7  category → genre / format mapping
  │  S8  origin (bangladesh / west_bengal / translated)
  ▼
interim/rokomari_books.parquet
  │  S9  author cleaning + author table
  │  S10 Wikidata linking + aliases
  ▼
interim/authors.parquet
  │  S11 edition → work grouping
  │  S12 catalogue filter
  ▼
processed/works.parquet · authors.parquet · editions.parquet · sources.parquet
```

---

## S1. Load and deduplicate rows
- **What:** one row per Rokomari `book_id`.
- **Why:** `book.json` has 149,515 rows for 127,302 IDs. 22,118 IDs repeat (up to 5 times). Titles and URLs are identical in 100% of these groups, so they are re-scrapes (D-013).
- **How:** strip "Show More" first (S2), then keep the row with the longest summary. Ties go to the row with the most non-null fields.
- **Output:** `book_id`, `dup_count` (how many raw rows were merged).
- **Check:** `book_id` is unique; row count is 127,302.

## S2. Text normalisation (all text fields)
- **What / why:** the same text can be stored in different Unicode forms, so identical strings don't match.
- **How, in order:**
  1. Remove the scraper artifact: trailing `Show More` (99.7% of summaries).
  2. Unicode: `bnunicodenormalizer` (fixes broken vowel signs, nukta and hasanta order), then NFC.
  3. **ZWJ/ZWNJ:** remove ZWJ (U+200D) and ZWNJ (U+200C) except where ZWNJ is legitimate (after hasanta, e.g. `আহ্‌মাদ`); normalise to one form.
     Examples found: `'মাওলানা আব্দুল্লাহ ‍সুহাইব'`, `'আমান‌উল্লাহ বিন নেছার'`, `'মুফতী মুহাম্মদ তৈয়‍্যেব হোসাইন'`
  4. Whitespace: `\r\n` → `\n`; collapse runs of spaces; trim.
  5. Punctuation: curly quotes `“ ” ‘ ’` → one quote style for matching keys (display text keeps the original); `ঃ` used as a colon → `:` in keys only.
- **Output:** each cleaned text field, with the original kept as `<field>_raw`.
- **Check:** no `Show More` left; no strings that change when normalised again (idempotent).

## S3. Field normalisation
- **Numbers:** Bangla digits `০১২৩৪৫৬৭৮৯` → ASCII in `book_pages` and prices; negative or zero pages → null.
- **ISBN:** strip hyphens and spaces; validate the ISBN-10 or ISBN-13 checksum; convert ISBN-10 → ISBN-13; invalid → `isbn_valid=false` (keep the raw value).
  - Raw values are mostly clean (`9789849156437`, `8170661838`), but 6.6% are malformed (e.g. 11 digits like `98483253611`).
- **Ratings:** `average_rating` in [1, 5], else null. `rating_count == 0` → rating is null (not 0).
- **Nulls:** empty strings → real null.
- **Output:** `isbn13`, `isbn_valid`, `pages`, `rating_avg`, `rating_count`, `review_count`.
- **Check:** every non-null `isbn13` passes its checksum.

## S4. Script and language detection
- **What:** for the title, summary and author name, the share of Bangla (U+0980–U+09FF) vs Latin letters.
- **Why:** 24.5% of titles are in Latin script only (foreign or English books), and 4% of summaries are mostly English. BanglaBook found 43% of user text is not in Bangla script.
- **How:** `script = bangla` if >70% Bangla letters, `latin` if >70% Latin, else `mixed`.
- **Output:** `title_script`, `summary_script`.
- **Used by:** S6 (English summaries), S12 (filter), and later the alias generation.

## S5. Title cleaning
- **What:** split marketing and format noise out of the title into fields.
- **Real examples:**
  | Raw title | Clean title | Extracted |
  |---|---|---|
  | `গল্পগুচ্ছ (সাদা) অখণ্ড` | `গল্পগুচ্ছ` | `paper=white`, `volume=complete (অখণ্ড)` |
  | `… (Paperback)` / `(Hardcover)` | … | `binding` |
  | `… (২য় খণ্ড)` | … | `volume=2` |
  | `… ( কিশোর মুসা রবিন সিরিজ )` | … | `series_hint="কিশোর মুসা রবিন সিরিজ"` |
  | `বইমেলা ২০১২ এ প্রকাশিত হুমায়ুন আহমেদের বই (রকমারি কালেকশন)` | — | `is_bundle=true` (a store collection, not a book) |
  | `আহমদ ছফা রচনাবলী ১, ২, ৩, ৪ (রকমারি কালেকশন)` | — | `is_bundle=true` |
- **How:** a table of known suffix patterns, each mapped to a field (binding, paper, volume, series, bundle, honorific). Collected-works markers (`সমগ্র`, `রচনাবলী`, `অখণ্ড`, `সংকলন`) set `is_collection=true`.
  Religious honorifics in titles (`(সা.)`, `(রা.)`) are part of the title and are kept.
- **Output:** `title_clean`, `title_raw`, `binding`, `volume`, `series_hint`, `is_bundle`, `is_collection`.
- **Check:** print the 50 most common remaining trailing parentheses and review them by hand. Anything frequent that isn't handled becomes a new rule.

## S6. Summary classification and cleaning ⭐ most important step
- **Why:** the summary becomes the source of the premise (D-008). A table of contents or an excerpt produces a bad premise.
- **Key finding:** Rokomari summaries often **start with a label that says what kind of text follows**:
  | Leading label (examples) | Meaning | Class |
  |---|---|---|
  | `"X" বইটির প্রথম ফ্ল্যাপ-এর লেখাঃ`, `ফ্ল্যাপে লেখা কিছু কথা` | "text from the flap" | `flap` ✅ best |
  | `‘শেষের কবিতা’ বইয়ের কিছু অংশঃ` | "some part of the book" | `excerpt` ⚠️ |
  | `সূচিপত্র * বদরের যুদ্ধ * ওহুদের যুদ্ধ …` | table of contents | `toc` ❌ |
  | `ভূমিকা`, `মুখবন্ধ`, `প্রসঙ্গকথা` | preface or foreword | `preface` ⚠️ |
  | `লেখক পরিচিতি`, author bio text | about the author | `author_bio` ❌ (goes to the author table) |
  | no label | usually a blurb | `blurb` ✅ (check further) |
- **How:**
  1. **Label rules:** regexes for the leading labels above; remove the label and keep the class.
  2. **Structure rules:** many `*` / `•` separators or numbered lines → `toc`; many quotation marks or dialogue lines at the start → probable `excerpt`.
  3. **Language:** `summary_script == latin` → `english` (usable for `premise_en`, not `premise_bn`).
  4. **Unclear cases:** a small LLM classifier on a sample of ~300, to measure rule accuracy. Apply it to the rest only if the rules are weak.
- **Split mixed summaries:** a summary may contain a flap part followed by a table of contents. Cut at the first TOC or bio label and keep the parts separately.
- **Output:** `summary_clean`, `summary_class`, `summary_len`, `summary_usable` (flap/blurb ≥ 200 chars, or an excerpt ≥ 500 chars marked lower quality).
- **Check:** a hand-labelled sample of 100 summaries; target ≥ 90% class accuracy.

## S7. Category → genre and format mapping
- **Why:** 1,515 categories, many unrelated to genre. Sample: `Commerce Department Admission`, `HSC 2nd Year: Accounting Text Books`,
  `Ophthalmology`, `Teacher registration-college stage`, `Story`, `Pre-Independence Bangladesh`, `When 12-17: Reference and Self-help book`.
- **How:** a **hand-made mapping file** `data/mappings/category_map.csv` (committed to git, since it's our own work):
  `category_id, category_name, books_count, action, genre, format, audience, origin_hint`
  - `action`: `map` / `ignore` (merchandising such as "Boimela 2025", "July Triumph!!") / `exclude` (academic, exam, medical)
  - Only the ~300 categories that cover fiction need a careful mapping; the rest are set to `exclude` in bulk by keyword.
  - Age prefixes (`When 4-8:`, `When 8-12:`, `When 12-17:`) → `audience`.
  - `West Bengal Books …` → `origin_hint=west_bengal`; `Translated …` → `origin_hint=translated`.
- **Output:** `genres[]` (seed labels, to be refined by the LLM later), `format`, `audience`, `excluded_reason`.
- **Check:** every category with ≥ 20 books has an action; the mapping covers ≥ 95% of fiction books.

## S8. Origin
- **Rule order (first match wins):**
  1. A translation category or a translator in the author links → `translated`
  2. Publisher name contains `(India)` (e.g. `Ananda Publishers (India)`, `Deys Publishing (India)`) → `west_bengal`
  3. A `West Bengal Books` category → `west_bengal`
  4. ISBN registration group `81`/`93` → `west_bengal`; `984` → `bangladesh`
  5. Otherwise → `bangladesh` with `origin_confidence=low`
- **Output:** `origin`, `origin_rule` (which rule fired), `origin_confidence`.
- **Check:** spot-check 30 books per class.

## S9. Author cleaning and author table
- **Real problems found:**
  | Problem | Example | Handling |
  |---|---|---|
  | Pen name in brackets | `অখিল নিয়োগী (স্বপনবুড়ো)`, `সুনীল গঙ্গোপাধ্যায় (নীললোহিত)` | name + `aliases=[pen name]` |
  | Religious honorifics | `হযরত শেখ সাদী (রহঃ)`, `… আত তিরমিযী (রহঃ)` | strip for the matching key; keep for display |
  | Titles and ranks | `ড. এনামুল হক`, `প্রফেসর ডা. …`, `লে. কর্নেল (অব.) … বীর প্রতীক` | strip `ড.` `ডা.` `প্রফেসর` `অধ্যাপক` `মাওলানা` `মুফতী`, ranks and gallantry titles for the key |
  | Not a person | `মাকতাবাতুল হাসান অনুবাদ পর্ষদ`, `… অনুবাদ ও সম্পাদনা পরিষদ`, `পাঞ্জেরী সম্পাদনা পর্ষদ` | `author_type=organisation` |
  | Hidden characters | ZWJ/ZWNJ (S2) | normalised |
  | Same name, different IDs | `শফিকুল ইসলাম` ×3, `মোঃ রফিকুল ইসলাম` ×3 | **don't merge on name alone.** Common names are often different people; merge only with evidence (same publisher and category, or the same Wikidata ID) |
  | Arabic + Bangla names | `(شيخ الاسلام …) শাইখুল ইসলাম …` | strip the Arabic-script part for the key |
- **Watch out for false positives:** a naive "organisation" rule matching `টিম` (team) also flags `টিম ডি. হিউইটসন` (Tim D. Hewitson) and `টিমোথি …`;
  `বোর্ড` (board) flags `ফারবোর্ড ফাহিমি`. So organisation words must match **whole words at the end** of the name (`… পর্ষদ`, `… পরিষদ`, `… সম্পাদনা পর্ষদ`).
- **Output (authors table):** `author_id` (ours), `rokomari_author_ids[]`, `name_bn`, `name_key`, `display_name`, `honorifics`, `aliases[]`,
  `author_type` (person/organisation), `bio_bn`, `book_count`.
- **Check:** the top 200 authors by book count are reviewed by hand.

## S10. Wikidata linking and aliases
- **How:**
  1. Exact match of `name_key` against Wikidata bn labels and aliases (also normalised). The baseline is 489 authors / 15% of book links; normalisation should raise it.
  2. Fuzzy match (character n-gram similarity ≥ 0.9) for the remaining authors with ≥ 5 books.
  3. Ambiguous candidates (several Wikidata people with similar names): an LLM decides, given birth/death years, country and book titles (Peeters & Bizer).
- **Aliases:** English label and aliases from Wikidata; romanised spelling from IndicXlit for the rest (`হুমায়ূন আহমেদ` → `humayun ahmed`).
- **Output:** `wikidata_qid`, `name_en`, `birth_year`, `death_year`, `aliases_latin[]`, `match_method`, `match_score`.
- **Check:** precision on 100 random links ≥ 95% (wrong links are worse than missing ones).

## S11. Group editions into works
- **Why:** 14.4% of books share a title and author with another book.
- **How:**
  1. Key = `norm(title_clean)` + `|` + the main author's `author_id`. Normalisation removes punctuation, volume and binding markers, and collected-works words.
  2. Books with the same key become one **work**. Each book stays an **edition** of that work.
  3. Keep bundles (`is_bundle`) and collected works (`is_collection`) as separate works, flagged, so they aren't recommended as novels.
  4. Work-level fields: best summary (flap > blurb > excerpt, then longest); sum of review counts; earliest first year; union of genres.
- **Output:** `works.parquet` (work_id, edition_ids[], best fields) and `editions.parquet`.
- **Check:** the 50 largest groups reviewed by hand (to catch over-merging).

## S12. Catalogue filter
- **Keep:** fiction formats (novel, novella, stories, comics, poetry kept but flagged), not excluded by category, not a bundle, **usable summary** (S6).
- **Expected size:** about 9.8k works before S6 is applied, **somewhat fewer after** (excerpts and TOCs removed).
- **Output:** `processed/works.parquet` with `in_catalogue=true/false` and `exclude_reason`.
  Nothing is deleted, so the filter can be changed later.

---

## Implementation plan
| File | Contents |
|---|---|
| `scripts/clean/text.py` | normalisation helpers (S2–S4), unit-tested |
| `scripts/clean/rokomari_books.py` | S1–S8 → `interim/rokomari_books.parquet` |
| `scripts/clean/authors.py` | S9–S10 → `interim/authors.parquet` |
| `scripts/clean/works.py` | S11–S12 → `processed/*.parquet` |
| `data/mappings/category_map.csv` | hand-made category mapping (committed to git) |
| `data/mappings/title_suffixes.csv`, `author_honorifics.csv` | rule tables (committed) |
| `tests/test_text.py` | tests using the real examples above |
| `docs/reports/cleaning-report.md` | generated: rows changed per rule, class counts, checks passed/failed |

Supplements (Wikipedia, Boighor, Boitoi) get their own parsers afterwards and join at S11 by matching title + author.
