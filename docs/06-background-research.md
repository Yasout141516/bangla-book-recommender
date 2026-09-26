# 06 Background research

Summary of earlier research (2026-09-25/26) that shaped this project. Most of the reviewed work is
about Bangladeshi legal and government documents. The lessons below are the ones that carry over to
a Bangla book recommender.

## Papers reviewed
| Work | Topic | Released data | What carries over |
|---|---|---|---|
| Mahadi et al., 2026 ([arXiv 2607.23446](https://arxiv.org/abs/2607.23446)) | Legal QA, fine-tuned Qwen3.5 on Bangla/English | [HF dataset](https://huggingface.co/datasets/momahadi/bangladesh-legal-qa-dataset) | Small models often answer Bangla questions in English; force the output language |
| MINA, Wasi et al., Findings of ACL 2026 ([ACL](https://aclanthology.org/2026.findings-acl.1295/)) | Legal assistant agent, two-stage RAG | Not yet | Two-stage retrieval (find the group first, then the item) helps. Cohere multilingual embeddings |
| UKIL, Wasi et al., 2024 ([arXiv 2410.17210](https://arxiv.org/abs/2410.17210)) | English statute corpus and a GPT-2 model | [UKIL-DB-EN](https://huggingface.co/datasets/ciol-research/UKIL-DB-EN) (Apache-2.0) | Not directly |
| LegalRAG, Kabir et al., 2025 ([arXiv 2504.16121](https://arxiv.org/abs/2504.16121)) | RAG over Police Gazettes | No | bge-m3 + Chroma with MMR works for Bangla. Include misspelled, dialect and out-of-scope questions in the test set |
| Aftahee et al., 2025 ([arXiv 2511.05627](https://arxiv.org/abs/2511.05627)) | LLM reliability on Bangla legal questions | No | ROUGE and BLEU are useless for Bangla. LLM judges disagree with humans, so check the judge against human ratings. LLMs invent facts confidently |
| Bhowmik et al., 2025 ([arXiv 2507.23248](https://arxiv.org/abs/2507.23248)) | Open models on Bangla benchmarks | [GitHub](https://github.com/BengaliAI/bn-llm-benchmark) (CC BY 4.0) | Bangla is ~0.18 points worse on average; the gap shrinks at 70B. Bangla uses 3–5x more tokens |
| LegalBench-RAG ([GitHub](https://github.com/zeroentropy-cc/legalbenchrag)) | Benchmark for retrieval alone | CC BY 4.0 | Evaluate retrieval separately from final answers. A general reranker made results worse, so test before adopting one |
| KoBLEX ([GitHub](https://github.com/daehuikim/KoBLEX)) | Korean legal QA | CC BY-NC | Have the LLM write a hypothetical target text before searching. Benchmark pipeline: LLM draft, LLM filter, expert review |

## Lessons applied to this project
1. **Don't let the LLM write facts from memory.** Premises come only from source text (D-008).
2. **Output language.** Answer in the user's language and check it automatically.
3. **Normalise Bangla text** (e.g. with `bnunicodenormalizer`) before indexing, so variant spellings match.
4. **Accept romanised Bangla** ("himu series er moto boi"). Transliterate or expand the query first.
5. **Hybrid retrieval.** bge-m3 gives dense and sparse vectors together. Test other embedding models on our own data.
6. **Separate evaluation.** Measure retrieval with recall@k on real queries, and judge reranking and explanations separately.
7. **Token budget.** Bangla costs more tokens, so keep premises short and cache common queries.

## Existing products (as of 2026-09)
- Rokomari and Goodreads offer "similar books" based on category and purchases or ratings.
- No known Bangla book search by description of taste. Confirm with the community-sources research (see [05](05-data-sources.md)).
