# 02 Decision log

Each entry records what was decided, why, and when. New entries go at the bottom.
To change a decision, add a new entry that supersedes the old one. Don't edit old entries.

---

### D-001: Build a metadata-based recommender, not RAG over full text
- **Date:** 2026-09-26
- **Decision:** Store only metadata for each book (genre, premise, taste tags). Don't store full text.
- **Why:** The goal is "find books with a similar plot or taste", which needs only summaries.
  This avoids copyright problems with full text and scanning/OCR work, and makes a catalogue of
  thousands of books practical.
- **Alternatives considered:** RAG over NCTB textbooks, or over public-domain literature (still
  possible as separate projects).

### D-002: Start with a small, fixed tag vocabulary
- **Date:** 2026-09-26
- **Decision:** Taste tags come from fixed bilingual lists (see [04](04-tag-vocabulary.md)).
  The LLM must pick from the lists. It may suggest new terms, but those are logged, not stored as tags.
- **Why:** Free-form tags split into synonyms ("dark", "gloomy", "grim"), which hurts filtering and matching.
  Starting small keeps labelling consistent. The lists grow based on real user searches.

### D-003: No spoiler plot summaries
- **Date:** 2026-09-26
- **Decision:** Store only a spoiler-free premise and a one-line hook. No full plot summaries.
  The tag `ending_feel` (happy/sad/…) is also dropped for now, because it reveals the ending.
- **Why:** Simpler, no risk of showing spoilers, less generated text to check.
- **Trade-off:** We lose matching on things like "twist ending like X". We can revisit this later.

### D-004: Include West Bengal and translated books from the start
- **Date:** 2026-09-26
- **Decision:** The catalogue covers Bangladeshi, West Bengal and translated or adapted books from version 1.
- **Why:** Bangladeshi readers read heavily across all three (Feluda, Byomkesh, Sunil, Shirshendu,
  Sheba translations). Leaving them out would make recommendations feel incomplete.
- **Implications:** Needs the `origin` field, translator links and `original_work` in the data model,
  plus sources covering Indian publishers.

### D-005: Separate author table from the start
- **Date:** 2026-09-26
- **Decision:** Authors (and translators) live in their own table, with all name spellings and aliases.
  Books reference them by `author_id`.
- **Why:** The same author appears as হুমায়ূন আহমেদ / Humayun Ahmed / Humayun Ahmad. Merging duplicates
  later is painful. The table also lets us compute public-domain status from the death year.

### D-006: Work and edition are separate entities
- **Date:** 2026-09-26
- **Decision:** A *work* (the book) is separate from its *editions* (publisher, year, ISBN, store link).
  Recommendations operate on works.
- **Why:** The same book appears under many publishers and printings, and must be recommended once.

### D-007: Record where every field came from
- **Date:** 2026-09-26
- **Decision:** Each record lists its sources (URL, type, license, fetch date) and which fields an LLM generated.
- **Why:** Lets us audit and fix LLM output, respect licenses and re-generate fields selectively.

### D-008: Premises are written by us, from sources, never from LLM memory
- **Date:** 2026-09-26
- **Decision:** The premise is written by an LLM **from retrieved source text** (Wikipedia plot,
  store blurb, reviews), in our own words. Never generated from the model's memory. Publisher
  blurbs are not republished word for word.
- **Why:** LLMs invent plots for lesser-known Bangla books, and blurbs are copyrighted.

### D-009: Data source strategy
- **Date:** 2026-09-26
- **Decision:**
  - RokomariBG is the catalogue backbone.
  - Premises are written from RokomariBG flap text, Boighor and Boitoi blurbs, and Wikipedia.
  - Wikidata supplies author IDs.
  - Eval queries are collected by hand or with consent.
  - We don't scrape Goodreads, Facebook, Amazon or deybooks.
- **Why:** RokomariBG is the only large, already-structured Bangla book dataset with summaries and reviews
  (see [05](05-data-sources.md)). The excluded sites forbid automated access in their terms.
- **Open:** license path (non-commercial vs commercial). See 05 §E. → Resolved by D-010.

### D-010: Non-commercial portfolio project
- **Date:** 2026-09-26
- **Decision:** This is a non-commercial resume/portfolio project. Non-commercial datasets (RokomariBG
  CC BY-NC, BanglaBook CC BY-NC-SA) may be used, with attribution. No monetisation. Any published data
  keeps the NC terms.
- **Why:** Stated goal is a strong RAG project for a resume.

### D-011: Focus on data collection, ingestion and cleaning first; eval queries later
- **Date:** 2026-09-26
- **Decision:** The current phase is building the data pipeline (collect → clean → deduplicate → label).
  Collecting evaluation queries is deferred.
- **Why:** The user's choice. A clean catalogue is also the prerequisite for everything else.

### D-012: Storage formats per pipeline stage
- **Date:** 2026-09-26
- **Decision:**
  - Raw data is kept as the original files, byte for byte, with sha256 checksums in `data/raw/MANIFEST.json`.
  - Scraped pages are stored as gzip-compressed HTML plus a JSONL fetch log.
  - Cleaned and merged tables are stored as Parquet.
  - LLM outputs are stored as append-only JSONL.
  - CSV is used only for viewing exports, written as UTF-8 with BOM.
- **Why:**
  - Converting raw data loses fidelity and reproducibility.
  - CSV breaks on Bangla text containing commas, quotes and newlines, and has no types or lists.
  - Parquet is typed, compressed and handles list columns.
  - JSONL is safe for incremental, resumable writes.
  - Details: [08](08-data-pipeline.md).

### D-013: Deduplicate RokomariBG rows by `book_id`, keeping the longest summary
- **Date:** 2026-09-26
- **Decision:** Treat the 22k repeated `book_id` groups as re-scrapes of the same book: title and URL are identical in 100% of groups.
- **Why:** Verified during profiling ([report](reports/rokomaribg-profile.md)).

### D-014: How we crawl Boighor and Boitoi
- **Date:** 2026-09-26
- **Decision:**
  - **Boitoi:** book URLs come from its public sitemap (robots.txt allows everything).
  - **Boighor:** book codes aren't sequential (codes below ~eb0025xx return no book), and there's no sitemap.
    Codes are listed through `api.boighor.com/api/getBooksByCategorys`, the same endpoint the public site
    calls when a category page is scrolled. The API host has no robots.txt, and the main site's robots.txt allows everything.
    Book details come from the public book pages.
  - For both: 1 request per second, an honest User-Agent, resumable, and the crawl stops by itself when it gets
    blocked. Raw HTML and listing responses are kept (D-012).
- **Why:** Fills the premise gaps. 58% of Rokomari books have no summary, including many West Bengal books.
- **Caveat:** Using the site's own listing API is a grey area. It's acceptable here only because the project is
  non-commercial, low-rate and uses the data read-only. Stop if either site objects.

### D-015: Pause the Boighor and Boitoi crawls; keep what was collected
- **Date:** 2026-09-26
- **Decision:** Both crawls were stopped. The pages already collected (Boighor 493, Boitoi 460) are kept and used
  only as a supplement: blurbs and genre tags where they match catalogue books. RokomariBG stays the backbone.
- **Why:** RokomariBG alone gives about 9.8k fiction works with usable metadata, which is enough for the project. The Boitoi
  crawl was slow (~20 pages/minute, ~13 hours estimated). `scripts/crawl.py` can resume both later.
- **Publishing:** raw data (including crawled pages) is **not** published in the public repo. Only code, docs,
  the manifest and generated reports are.

### D-016: Public GitHub repo for code and docs only
- **Date:** 2026-09-26
- **Decision:** Publish the project as a public GitHub repo. `data/` stays git-ignored except `data/raw/MANIFEST.json`.
  Anyone can rebuild the data with the scripts and the links in the manifest.
- **Why:** Portfolio visibility. Dataset licenses (NC, NC-SA) and store blurbs (copyrighted) don't allow redistribution.

### D-017: Demo UX decisions from a design review
- **Date:** 2026-09-26
- **Decision:** 11 UX decisions, each approved individually, recorded in [12 UX plan](12-ux-plan.md):
  - mobile-first web; first screen = input + 4 example queries
  - result card: title → reason → tags → premise → source line
  - progressive loading; honest fallback for weak matches; did-you-mean picker for "similar to X"
  - LLM error → message + retry
  - tag chips + more-like-this + toggles for refining
  - 👍/👎 per card + optional reason
  - Noto Sans Bengali, mobile-first
- **Deferred:** accessibility details, type scale, and whether matches stay on screen when the LLM fails.
- **Why:** the plan had no UI decisions; making them now keeps the retrieval work aimed at what users will see.
