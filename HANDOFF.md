# Handoff: start of the LLM labelling phase

Written 2026-09-27 at the end of the data-collection and cleaning phase. Start here in a new chat.
Repo: https://github.com/Yasout141516/bangla-book-recommender (last commit `c704883`). Local: `E:\TeslaProject\bangla-book-recommender`.

---

## 1. The project in one paragraph
A taste-based search and recommendation tool for **Bangla fiction**. The user describes what they want ("a slow, dark
mystery set in old Dhaka", "himu type boi", "books like Sonar Kella") in Bangla, English or romanised Bangla,
and gets 5 books, each with a one-line reason. Each book is stored as **metadata only**: title, author, a spoiler-free
premise and taste tags from a fixed vocabulary. It is **not RAG over full text** and **no chunking is needed**, because
one book is one short record. This is a non-commercial portfolio/resume project (D-010).

## 2. Where things stand
| Phase | Status |
|---|---|
| Research, data sources, literature review | ✅ docs/05, docs/09 |
| Data collection | ✅ RokomariBG, BanglaBook, bn Wikipedia (342), Wikidata writers (3,471); Boighor 493 / Boitoi 460 pages (paused) |
| Cleaning S1–S12 | ✅ 193 tests, 18 + 22 hard validation checks, full rebuild reproduces |
| UX plan, diagrams | ✅ docs/12, diagrams/ |
| **LLM labelling** | ⏳ **next: this handoff** |
| Embedding text, index, retrieval, rerank, eval, demo | 🔜 |

The user decided **not to clean further** (the "good enough" point). Remaining data issues are documented in PROGRESS.md
and docs/11; don't reopen them unless labelling shows they matter.

## 3. The input for labelling
`data/processed/works.parquet`: filter `in_catalogue == True` → **14,155 works**.
(The data is git-ignored. Rebuild it with the commands in §8 if the folder is missing.)

Columns that matter for labelling:
| Column | Meaning |
|---|---|
| `work_id` | `bk_000123`; the stable id to key all labels on |
| `title_bn` | cleaned Bangla title. **Can be truncated** (RokomariBG cuts subtitles; 38 Masud Rana novels were all "মাসুদ রানা") |
| `slug_title` | romanised full title from the Rokomari URL (`masud rana dhongso pahar`); use it to disambiguate |
| `main_author_id` → `processed/authors.parquet` (`name_display`, `wd_label_en`, `birth_year`, `death_year`) | author; 4,267 catalogue works have none |
| `summary` | the source text for the premise. `summary_class` ∈ blurb (11,482), flap (2,658), summary (9), excerpt (6). Median 739 chars, p90 1,444, max 23,692 → **truncate long ones** |
| `format` | novel 6,510 · short_story_collection 2,967 · poetry 1,973 · comics 397 · drama 264 · **None 2,044** |
| `genre_hints` | candidate genres from Rokomari categories (list; empty for 8,249). **Hints, not answers** (D-018) |
| `audience` | children / teen / None (11,160 unknown) |
| `origin`, `origin_confidence` | bangladesh 10,559 · translated 1,889 · west_bengal 1,707; ~2,871 are low-confidence defaults |
| `religious`, `is_collection`, `series_group_id`, `volume` | flags; volumes of one book share `series_group_id` |
| `rating_count`, `review_count` | reader signals (6.3k works have ≥1 review) |

Review text for mood signals: `data/raw/rokomaribg/review.json.gz` + `book_to_review.json.gz` (map book → work via
`processed/editions.parquet`). Optional.

## 4. What labelling must produce
The target fields are in [docs/03-data-model.md](docs/03-data-model.md). The allowed values are in
[docs/04-tag-vocabulary.md](docs/04-tag-vocabulary.md) (v0.2; `drama` added).

| Field | Rule |
|---|---|
| `premise_bn` | 2–4 sentences, **spoiler-free**, in our own words, **written only from `summary` (+ title/author)**. Never from model memory (D-008) |
| `premise_en` | English version of the same premise |
| `hook` | one line |
| `genres` (1–3) | from the fixed list; `genre_hints` may guide but not decide |
| `moods` (1–3), `pace`, `tone`, `themes` (2–5), `setting_region` (1–2), `setting_places` (0–3, open), `setting_era`, `content_notes` | fixed lists only |
| `format`, `audience` | fill only when missing |
| `suggested_new_tags` | when nothing fits: logged, **not** stored as tags (D-002) |
| `confidence` + per-field `evidence` quote | so weak tags can be filtered (Doc2Query-- lesson) |

Output: **append-only JSONL** in `data/labels/` (D-012), one record per work, with `work_id`, `model`, `prompt_version`,
`created_at`. The run must be resumable: skip `work_id`s already labelled.

## 5. Plan for the labelling phase
1. **Pick the LLM** (open decision, §7). Compare 2–3 candidates on the same **20 books** for Bangla quality,
   spoiler-free premises, tag accuracy and cost per 1k books. Then extrapolate to 14,155.
2. **Write the prompt** (`prompts/label_v1.md`, versioned):
   - Following the literature (KAR / LLMRec / Doc2Query--, docs/09): ask for tags from the fixed lists, one facet at a
     time or with a strict JSON schema; require an evidence quote per tag; drop unsupported tags.
   - Tell the model: the summary may start with marketing text, a flap label or a series list, so ignore those. The title
     may be truncated, so use `slug_title`. Don't invent plot beyond the summary. No spoilers.
3. **Pilot on 200 works:** a stratified sample across format, origin and summary_class, including poetry, drama,
   comics, children's books and truncated-title series.
   - Hand-check a random 50: premise faithful? spoilers? tags right? Bangla natural?
   - Record the measured error rates, then fix the prompt.
4. **Validate automatically:** JSON schema valid, tags ⊂ vocabulary, premise length, premise language (Bangla-script
   share), no names or facts absent from the summary (spot-check), no premise identical to the blurb (copyright, D-008).
5. **Full run** over 14,155: resumable, rate-limited, with cost tracking. Then a label-quality report (like the cleaning reports).
6. **Open questions to settle during the pilot:** do mood/pace/themes make sense for **poetry (1,973)** and **comics**?
   What about **religious fiction (511)** and **collections (1,025)**? (docs/11, PROGRESS "Scope" questions)

After labelling: design `embedding_text` and compare 2–3 variants; bge-m3 dense + sparse; hybrid search with filters;
"similar to X"; LLM rerank with shuffled candidates; eval set (Phase 2, deferred); mobile web demo (docs/12).

## 6. Rules and lessons to carry forward
- **Verify, don't assume.** Every number in the docs was measured. The user explicitly asked not to hallucinate.
  Hand-check samples: the worst bugs were silent and only reading found them (docs/11 #9, #20, #25).
- **Measure a detector's precision before acting on it.** A typo detector flagged 306 books, but only about 25% were
  really broken (docs/11 #26). Check what a requested action would remove before doing it.
- **Unicode:** NFC decomposes `য়`; `ঃ` sits inside the Bangla block; regex ranges with literal `ড়/য়` endpoints aren't
  NFC-stable (use `\u` escapes); an unescaped `-` in a character class matched all of Bangla. A test walks every module
  constant and checks NFC.
- **Don't write code through shell heredocs with backslashes.** A `\b` became a literal backspace once (docs/11 #16).
  Use direct file edits.
- **Windows:** set `PYTHONIOENCODING=utf-8`; use `npx.cmd` / `shell=True` for node tools.
- **Document everything:** decisions → docs/02 (next is **D-024**); obstacles → docs/11 (next is **#28**), with
  numbers, for the user's interview prep; progress → PROGRESS.md; commit and push after each milestone.
- The user wants a **portfolio-quality** project and to understand the *why* of each step. Explain in plain terms
  and ask before big scope or format decisions.

## 7. Open decisions for the user
1. **Which LLM for labelling** (Bangla quality vs cost for ~14k books; also used later for rerank/explanations).
2. **Poetry, comics, religious fiction and collections:** label them all the same way, or tag some differently or exclude them?
3. From the design review (docs/12): accessibility details, loading-vs-error behaviour, type scale, weak-match
   threshold, UI language. These aren't needed until the demo.
4. Optional small jobs, parked:
   - a 27-row origin table for "British Raj"-only authors (Tagore, Sarat, Bankim…)
   - repairing the 11 garbled summaries with `unshift_vowels` instead of excluding them
   - parsers for Wikipedia/Boighor/Boitoi to improve premises of the classics

## 8. Commands
```bash
cd E:\TeslaProject\bangla-book-recommender
pip install -r requirements.txt
set PYTHONIOENCODING=utf-8            # PowerShell: $env:PYTHONIOENCODING="utf-8"

# rebuild the processed data from data/raw (~8 min), then validate and test
python -m scripts.clean.rokomari_books
python -m scripts.clean.build_category_map
python -m scripts.clean.categories_origin
python -m scripts.clean.authors
python -m scripts.clean.works
python -m scripts.clean.validate_s1_s6
python -m scripts.clean.validate_s7_s12
python -m pytest tests
```

## 9. Key files
| Path | What |
|---|---|
| `README.md`, `PROGRESS.md` | overview and checklist |
| `docs/02-decision-log.md` | D-001…D-023 |
| `docs/03-data-model.md`, `docs/04-tag-vocabulary.md` | target record and tag lists |
| `docs/10-cleaning-spec.md`, `docs/11-challenges-and-lessons.md` | how the data was cleaned and what went wrong |
| `docs/12-ux-plan.md` | what the demo shows (the result card uses premise, reason, tags) |
| `scripts/clean/*.py`, `tests/` | pipeline and tests |
| `data/processed/works.parquet` | **labelling input** (git-ignored) |
| `data/labels/` | **labelling output goes here** (JSONL) |
| `data/raw/MANIFEST.json` | every raw file with source, license and checksum |
