# 09 Literature review

Compiled 2026-09-26. Links were verified by opening them, except where marked. Focus: what this project can reuse,
especially for data collection and cleaning.

## State of the art and the gap
Bangla book recommendation has **one benchmark, RokomariBG**. It focuses on user interactions (top-N and
sequential recommendation), and on it content features and author loyalty beat collaborative filtering.
BanglaBook covers review sentiment, not retrieval. Narrative-driven and LLM-based recommendation, and LLM reranking,
are well established, but in **English** and mostly for movies or places.

**No published work combines:**
1. free-text **taste** queries in Bangla, English and romanised Bangla
2. a **metadata-only** catalogue enriched with LLM taste tags (mood, pace, themes, setting)
3. hybrid multilingual retrieval with an LLM reranker that explains its choices

There is also no public Bangla taste-query evaluation set. Building even a small one is a contribution in itself.

---

## 1. Bangla book recommendation

### RokomariBG (2026) ⭐ our data backbone
- **Paper:** Ahmed, Chowdhury, Reza, Bhattacharjee, Adnan, McAuley, Sadeq. "Towards Personalized Bangla Book Recommendation:
  A Large-Scale Heterogeneous Book Graph Dataset." arXiv [2602.12129](https://arxiv.org/html/2602.12129v2) ·
  [code](https://github.com/backlashblitz/Bangla-Book-Recommendation-Dataset)
- **Collection:** scraped public Rokomari pages (respecting robots.txt) and parsed the HTML to JSON with BeautifulSoup.
- **Cleaning:**
  - dedupe by URL hash plus entity ID
  - convert Bangla numerals; parse comma-separated numbers
  - clamp ratings to [1, 5]; standardise prices
  - store missing values as explicit nulls
  - remove PII and replace users with anonymous IDs
- **Scale:** 127,302 books · 16,601 authors · 1,515 categories · 2,757 publishers · 209,602 reviews from 63,723 users
- **Relations:** book–author, book–publisher, book–category, author–category, author–publisher, publisher–category,
  review–user, review–book
- **Results:**
  - Top-N NDCG@10: two-tower with side features **0.113**, TF-IDF content **0.108**, LightGCN 0.070.
  - Sequential Hit@10: "continue with the same author" **0.163**, beating SASRec (0.074) and BERT4Rec (0.078).
  - Removing relational knowledge: 0.103 → 0.076.
- **Limitations:** 53.7% of users have only one review; 65.8% of ratings are five-star; 75–92% category cold-start;
  mixed Bangla and English text.
- **Takeaways for us:**
  - **Content-based retrieval is competitive on Bangla data**, which supports our metadata-only design (D-001).
  - **Same-author is a strong signal**, so use it as a feature for "similar to X".
  - Ratings carry little signal (too many 5-stars), so use review **text** for mood, not star ratings.

### BanglaBook (Findings of ACL 2023)
- **Paper:** Kabir, Mahfuz, Raiyan, Mahmud, Hasan. [ACL Anthology](https://aclanthology.org/2023.findings-acl.80/) ·
  [GitHub](https://github.com/mohsinulkabir14/BanglaBook) · [HF](https://huggingface.co/datasets/Starscream-11813/BanglaBook)
- **Collection:** 204,659 reviews scraped from Rokomari and Wafilife (BeautifulSoup and Selenium; author pages first, then book pages).
  Reviews without a rating were dropped, leaving 158,065. 68,694 romanised, English or mixed reviews were
  Google-translated to Bangla and checked by hand. Ratings 1–2 map to negative, 3 to neutral, 4–5 to positive.
- **Takeaways for us:**
  - **About 43% of user text is not in Bangla script**, so handling romanised Bangla is essential.
  - Its title/author table is a ready cross-source set for testing entity resolution.

No other verifiable Bangla book-recommendation paper was found.

---

## 2. Natural-language and narrative-driven recommendation
| Paper | Link | What it shows | Takeaway for us |
|---|---|---|---|
| Bogers & Koolen, *Defining and Supporting Narrative-driven Recommendation*, RecSys 2017 | [DOI](https://dx.doi.org/10.1145/3109859.3109893) | Defines narrative-driven recommendation (NDR); studies real **book** requests from LibraryThing forums | Their request-type analysis (mood, plot, "similar to", setting) checks our tag facets and later eval queries |
| Mysore, McCallum, Zamani, *LLM Augmented Narrative Driven Recommendations*, RecSys 2023 | [arXiv 2306.02250](https://arxiv.org/abs/2306.02250) | An LLM writes synthetic narrative queries per item; small retrievers trained on them win | Generate synthetic Bangla, English and romanised taste queries per book for eval and training |
| He et al., *LLMs as Zero-Shot Conversational Recommenders*, CIKM 2023 | [arXiv 2308.10053](https://arxiv.org/abs/2308.10053) · [code](https://github.com/AaronHeee/LLMs-as-Zero-Shot-Conversational-RecSys) | Reddit-Movie: 634k real requests; LLMs win zero-shot but have popularity bias | A pipeline for matching book titles mentioned in free text to catalogue items; watch for popularity bias |
| Eberhard, Ruprechter, Helic, *LLMs as Narrative-Driven Recommenders*, 2024 | [arXiv 2410.13604](https://arxiv.org/abs/2410.13604) | Zero-shot prompting matches fancier prompting; mid-size open models are competitive | A simple zero-shot rerank prompt is enough |
| Hou et al., *LLMs are Zero-Shot Rankers for Recommender Systems*, ECIR 2024 | [arXiv 2305.08845](https://arxiv.org/abs/2305.08845) | LLM rankers are biased by candidate position and popularity; shuffling candidates helps | Shuffle candidates across rerank passes |
| Sun et al., *Is ChatGPT Good at Search? (RankGPT)*, EMNLP 2023 | [arXiv 2304.09542](https://arxiv.org/abs/2304.09542) · [code](https://github.com/sunnweiwei/RankGPT) | Listwise reranking with a sliding window | Reranker implementation |
| Sanner et al., *LLMs are Competitive Near Cold-start Recommenders…*, RecSys 2023 | [ACM](https://dl.acm.org/doi/10.1145/3604915.3608845) | Natural-language preferences alone are competitive with item-based CF | Supports taste-only input |
| Hou et al., *BLaIR*, ACL 2026 | [arXiv 2403.03952](https://arxiv.org/abs/2403.03952) | Metadata–language embeddings; Amazon-C4, built by an LLM rewriting reviews into requests | A recipe for semi-synthetic queries built from reviews |
| Wan & McAuley 2018; Wan et al., *Fine-Grained Spoiler Detection*, ACL 2019 | [Goodreads datasets](https://cseweb.ucsd.edu/~jmcauley/datasets/goodreads.html) · [ACL](https://aclanthology.org/P19-1248/) | `work_id` groups editions; shelves act as crowd tags; spoilers cluster late in reviews | Work/edition model (D-006); run a spoiler check on premises (D-003) |

## 3. LLM enrichment of item metadata
| Paper | Link | Takeaway for us |
|---|---|---|
| LLMRec (Wei et al., WSDM 2024) | [arXiv 2311.00423](https://arxiv.org/abs/2311.00423) | Generate attributes, **then filter out the noisy ones** |
| KAR (Xi et al., RecSys 2024) | [arXiv 2306.10933](https://arxiv.org/abs/2306.10933) | "Factorization prompting": **ask for one facet at a time** (mood, pace, themes…) |
| Doc2Query-- (Gospodinov et al., ECIR 2023) | [arXiv 2301.03266](https://arxiv.org/abs/2301.03266) | Generated expansions hallucinate. **Filtering gave up to +16% and a 48% smaller index**, so score each tag against its source text and drop weak tags |

## 4. Catalogue entity resolution
| Work | Link | Takeaway for us |
|---|---|---|
| OCLC FRBR Work-Set Algorithm | [OCLC](https://www.oclc.org/research/activities/frbralgorithm.html) | Group editions into works using a key of `norm(author)`\|`norm(title)` |
| Peeters & Bizer, *Entity Matching using LLMs*, EDBT 2025 | [arXiv 2310.11244](https://arxiv.org/abs/2310.11244) | LLM makes the final match/no-match call on ambiguous pairs, after cheap pre-filtering |
| Ekbal et al., *Transliteration of Named Entity: Bengali and English*, FLAIRS 2007 | [AAAI](https://aaai.org/papers/flairs-2007-045/) | Background for matching author names across scripts |

## 5. Bangla text processing
| Work | Link | Takeaway for us |
|---|---|---|
| Ansary et al., *Unicode Normalization and Grapheme Parsing of Indic Languages*, LREC-COLING 2024 | [arXiv 2306.01743](https://arxiv.org/abs/2306.01743) · [code](https://github.com/mnansary/bnUnicodeNormalizer) | Run `bnunicodenormalizer` on every Bangla field |
| BanglaBERT (Bhattacharjee et al., Findings NAACL 2022) | [ACL](https://aclanthology.org/2022.findings-naacl.98/) | csebuetnlp `normalizer`, an alternative that matches BanglaBERT and BanglaT5 |
| Aksharantar / IndicXlit (Madhani et al., Findings EMNLP 2023) | [arXiv 2205.03018](https://arxiv.org/abs/2205.03018) · [code](https://github.com/AI4Bharat/IndicXlit) | Convert romanised Bangla to Bangla script and back: queries, plus Latin aliases for titles and authors |
| BanglaTLit (Fahim et al., Findings EMNLP 2024) | [ACL](https://aclanthology.org/2024.findings-emnlp.859/) | 42.7k romanised→Bangla pairs to test transliteration |
| Dakshina (Roark et al., LREC 2020) | [ACL](https://aclanthology.org/2020.lrec-1.294/) | Romanisation lexicon with multiple spellings per word, for alias lists |
| Gharami et al., *Modeling Romanized Hindi and Bengali*, 2025 | [arXiv 2511.22769](https://arxiv.org/abs/2511.22769) | About 1M Bengali transliteration pairs |
| BGE-M3 (Chen et al., 2024) | [arXiv 2402.03216](https://arxiv.org/abs/2402.03216) | Dense and sparse vectors from one model, which fits our hybrid design |
| Multilingual-E5 (Wang et al., 2024) | [arXiv 2402.05672](https://arxiv.org/abs/2402.05672) | Embedding model to compare against |
| MIRACL (Zhang et al., TACL 2023; includes Bengali) · MMTEB | [ACL](https://aclanthology.org/2023.tacl-1.63/) · [arXiv 2502.13595](https://arxiv.org/abs/2502.13595) | Where embedding models' Bengali retrieval scores are reported |

No dedicated Bangla embedding benchmark ("Bangla-MTEB") was found.

---

## Techniques adopted into our pipeline
These are reflected in [08 Data pipeline](08-data-pipeline.md):
1. Deduplicate by source ID or URL (RokomariBG)
2. `bnunicodenormalizer` plus NFC; clean ZWJ/ZWNJ and whitespace (Ansary et al.)
3. Normalise fields: Bangla digits → ASCII, validate ISBN checksums, explicit nulls (RokomariBG)
4. Detect script and language for each field (BanglaBook's finding that 43% is not in Bangla script)
5. Transliteration aliases for titles and authors (IndicXlit, Dakshina)
6. Group editions into works with a normalised author+title key (OCLC FRBR)
7. Author entity resolution: cheap pre-filtering, then an LLM decides (Peeters & Bizer)
8. Map Rokomari's 1,515 categories to our fixed taxonomy
9. Premises from blurbs, not reviews, plus a spoiler check (Wan et al.)
10. Tag labelling one facet at a time from the fixed vocabulary, **then filter tags by support** (KAR, LLMRec, Doc2Query--)
11. Later: synthetic trilingual eval queries checked by humans (Mysore et al., BLaIR); shuffle candidates in the reranker (Hou et al.)
