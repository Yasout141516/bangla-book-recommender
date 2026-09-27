# Progress

Last updated: 2026-09-26. Decisions are referenced as D-xxx ([decision log](docs/02-decision-log.md)).

## ✅ Phase 0: Research and planning (done)
- [x] Researched Bangla RAG directions (legal, government services, books) and chose a **metadata-only book recommender** (D-001)
- [x] Scope: Bangladeshi + West Bengal + translated books (D-004); no spoilers (D-003); non-commercial (D-010)
- [x] Data model: works, authors, series, editions, sources, with provenance on every field (D-005–D-007)
- [x] Tag vocabulary v0.1: 17 genres, 10 moods, 24 themes, plus format, audience, pace, tone, setting, era, content notes (D-002)
- [x] Evaluated ~30 data sources for coverage, license and access ([05](docs/05-data-sources.md))
- [x] Literature review: RokomariBG, BanglaBook, narrative-driven recommendation, LLM rerankers, LLM tag enrichment, entity resolution, Bangla text processing ([09](docs/09-literature-review.md))

## ✅ Phase 1a: Data collection (done)
- [x] RokomariBG: all 13 files (books, authors, categories, publishers, reviews, relation files)
- [x] BanglaBook review CSVs
- [x] Bangla Wikipedia: 342 book/novel articles (`scripts/collect_wikipedia.py`)
- [x] Wikidata: 3,471 Bengali-language writers (`scripts/collect_wikidata_authors.py`)
- [x] Polite, resumable crawler (`scripts/crawl.py`); partial crawls of Boighor (493) and Boitoi (460), then paused (D-014, D-015)
- [x] Storage conventions and a raw manifest with checksums (`scripts/make_manifest.py`, D-012)
- [x] RokomariBG profiling report (`scripts/profile_rokomaribg.py`): **9,804 fiction works with usable metadata**

## ⏳ Phase 1b: Cleaning pipeline (next)
Steps are detailed in [08 Data pipeline](docs/08-data-pipeline.md).
- [x] **Clean RokomariBG books → `data/interim/rokomari_books.parquet`** (`python -m scripts.clean.rokomari_books`)
  - [x] S1 deduplicate by `book_id`, keeping the longest summary (D-013)
  - [x] S2 strip "Show More" and HTML residue; normalise whitespace; legacy-encoding repairs; `bnunicodenormalizer` (one harmful step disabled) + NFC; clean ZWJ/ZWNJ
  - [x] S3 Bangla digits → ASCII; validate ISBN-10/13; explicit nulls
  - [x] S4 detect the script of each field (Bangla / Latin / mixed)
  - [x] S5 clean titles: binding, paper, volume, series, language, bundle and collection markers
  - [x] S6 classify summaries: flap / blurb / summary / excerpt / toc / preface / author_bio / english / empty
  - [x] 102 unit tests; validation script with 18 hard checks, all passing ([report](docs/reports/validation-s1-s6.md))
  - [x] Problems and fixes written up in [docs/11](docs/11-challenges-and-lessons.md)
  - Result then: "9,497 fiction works". **Superseded:** that count used substring matching, so "story" matched "History" (docs/11 #18)
- [x] **S7 category mapping**: `data/mappings/category_map.csv` (1,516 categories, rules + all 189 mapped categories read by hand); format, genre hints, audience, origin/language hints (D-018, D-019)
- [x] **S8 origin and language**: literary origin, with the author's nationality first (D-021); English-language books identified and excluded
- [x] **S9 author table**: names parsed (pen names, honorifics, ranks, descriptors, organisations); 16,601 Rokomari ids
- [x] **S10 Wikidata linking**: 357 ids → 355 people; hand-checked precision 37/40 correct, 0/40 wrong (D-020)
- [x] **S11 works**: 127,302 editions → 120,189 works; merge only with a known author; volume from title or URL slug (D-022)
- [x] **S12 catalogue**: **14,155 works** in the catalogue; every excluded work keeps its reasons
- [x] Validation: 22 hard checks for S7–S12 ([report](docs/reports/validation-s7-s12.md)); 171 unit tests in total
- [x] Full rebuild from raw data: 7 min 46 s, identical numbers
- [ ] Parsers for Wikipedia, Boighor and Boitoi pages → attach better premises for matching works (optional)

### Catalogue (2026-09-27)
| | Works |
|---|---|
| In catalogue | **14,155** |
| Format | novel 6,510 · stories 2,967 · poetry 1,973 · comics 397 · drama 264 · mixed/unknown 2,044 |
| Origin | Bangladesh 10,559 · translated 1,889 · West Bengal 1,707 |
| Summary source | blurb 11,482 · flap text 2,658 |
| Volumes grouped as series entries | 548 works in 258 groups |

**Next phase: see [HANDOFF.md](HANDOFF.md).**

## 🔜 Phase 2: Labelling
- [ ] Prompt: spoiler-free `premise_bn` / `premise_en` / `hook` from source text only (D-008)
- [ ] Tag prompts, one facet at a time, from the fixed vocabulary (KAR-style); drop tags the source doesn't support (Doc2Query--)
- [ ] Label a 200-book pilot; hand-check it; refine prompts; then label all ~9.8k
- [ ] Native reader review of the Bangla tag labels

## 🔜 Phase 3: Retrieval and reranking
- [ ] Build `embedding_text`; compare bge-m3, multilingual-e5 and others
- [ ] Hybrid search (dense + sparse) with filters; "similar to X" lookup
- [ ] Query understanding (romanised → Bangla transliteration, filter extraction)
- [ ] LLM reranker with explanations; shuffle candidates to reduce position bias

## 🔜 Phase 4: Evaluation and demo (deferred, D-011)
- [ ] Eval set: 100–200 real + synthetic taste queries (Bangla / English / romanised), hand-checked
- [ ] Metrics: recall@10, nDCG@10, answer-language check
- [ ] Simple web demo

## Known issues and open questions
- Some summaries start with marketing text ("…ক্যারেকটার কার্ড ফ্রি") or list series titles; not removed by rules.
- Series issues that differ only by subtitle (রোমাঞ্চ) can still merge into one work.
- 2,871 catalogue works still have a low-confidence (default) origin.
- Rules can't tell a narrative opening (the first scene of the book) from flap copy written as a scene. An LLM check on a sample is planned for labelling.
- Some summaries are study-guide style (character analysis) rather than blurbs; not detected by rules.
- The West Bengal share is small (~1.2k). Boighor and Boitoi can resume later if needed.
- Wikidata's genre field is noisy (e.g. "film promotion"); use it only for author identity.
- The choice of LLMs for labelling and reranking (cost vs Bangla quality) is still open.
