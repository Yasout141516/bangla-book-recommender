# 07 Roadmap

## Phase 0: Planning (current)
- [x] Decide project direction: metadata-based recommender (D-001)
- [x] Decide scope: Bangladesh, West Bengal and translated books (D-004)
- [x] Data model draft ([03](03-data-model.md))
- [x] Starter tag vocabulary v0.1 ([04](04-tag-vocabulary.md))
- [x] Data sources: research done ([05](05-data-sources.md)); RokomariBG, BanglaBook and the bn Wikipedia page list downloaded to `data/raw/`
- [x] License path: non-commercial portfolio project (D-010)
- [x] Profile RokomariBG ([report](reports/rokomaribg-profile.md)): about 13k fiction books with usable summaries
- [x] Storage formats and raw manifest (D-012, [08](08-data-pipeline.md))
- [x] Academic literature review ([09](09-literature-review.md))
- [x] Collect bn Wikipedia articles (342) and Wikidata Bengali writers (3,471)
- [x] Partial crawls of Boighor (493) and Boitoi (460), then paused (D-014, D-015)
- [x] Public GitHub repo with code and docs (D-016); detailed checklist in [PROGRESS.md](../PROGRESS.md)
- [x] Cleaning pipeline S1–S6 for RokomariBG ([10](10-cleaning-spec.md), [11](11-challenges-and-lessons.md))
- [x] UX plan for the demo, from a design review ([12](12-ux-plan.md), D-017)
- [ ] **Cleaning S7–S12**: category mapping, origin, authors, Wikidata linking, works ← next
- [ ] Parsers for Boighor, Boitoi and Wikipedia raw data → `data/interim/`
- [ ] Native reader review of the Bangla tag labels

## Phase 1: Seed catalogue (target 500–1,000 works)
- [ ] Collect a seed list of important books by genre (classics, bestsellers, award winners, popular series)
- [ ] Build the author table (Wikidata first, then store data)
- [ ] Collect raw source text for each work and store raw snapshots
- [ ] Write the labelling prompt (premise + tags from sources, fixed-list output, JSON)
- [ ] Label the seed catalogue; check a random 10% by hand
- [ ] Merge duplicate works and editions

## Phase 2: Evaluation set (deferred, D-011)
- [ ] Collect 100–200 real "suggest a book like…" queries with good answers
- [ ] Add queries in Bangla, English and romanised Bangla, plus misspelled and out-of-scope ones
- [ ] Define metrics: recall@10, nDCG@10, and a language check

## Phase 3: Retrieval MVP
- [ ] Normalise text; build `embedding_text`
- [ ] Compare embedding models (bge-m3, multilingual-e5, Cohere multilingual) on the eval set
- [ ] Hybrid search with filters (audience, genre, era, origin)
- [ ] LLM query understanding (text → search text + filters) and "similar to X" lookup
- [ ] LLM rerank with an explanation in the user's language

## Phase 4: Pilot
- [ ] Mobile-first web demo, built to the [UX plan](12-ux-plan.md) (decide the open accessibility items first)
- [ ] Share with a book community; collect 👍/👎 feedback
- [ ] Add reader signals (ratings, co-liked books)
- [ ] Scale the catalogue to 3–5k works

## Open questions
- Which sources are legally usable for premises and reviews? (see 05)
- Vector DB choice (Chroma vs Qdrant) and hosting
- Which LLMs for labelling and for reranking (cost vs Bangla quality)
