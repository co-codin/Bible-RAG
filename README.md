# Bible-RAG

Multilingual retrieval-augmented QA over the **Bible** and the **Quran**. Ask in English or Chinese, get answers grounded in scripture with verse citations, and compare the same verse across translations side by side.

## Status

Phase 1 (English + Simplified Chinese) retrieval, API, frontend, input/output guards, and eval sets are in place. Generation and the full DeepEval run need API keys (left unset for now).

- **Retrieval:** bge-m3 dense + sparse hybrid search in Milvus Lite, fused with RRF (default candidates=50, k=60). Pre-built index: [etsin-ai/bible-rag-index](https://huggingface.co/datasets/etsin-ai/bible-rag-index). `make index-check` verifies the fingerprint.
- **`GET` / `POST /search`:** hybrid (or dense-only / sparse-only) search. No LLM key required.
- **`GET /verse/{canon_ref}`:** side-by-side lookup of a verse or same-chapter range across KJV/CUV or Quran EN/ZH. Reads the corpus JSONL (the published index may have an empty `passages` collection). No LLM key required.
- **`POST /answer`:** input guard → hybrid search → OpenAI generation (`gpt-4o-mini`) → output guard. Off-topic / injection refusals return 200 with `refused=true`. A missing key returns **503** only when the model would actually be called.
- **Guards:** rules (length, injection, other-canon, scripture cues) plus a cheap bge-m3 topic check. On the official splits, rules + bge-m3 block **80/108** negative items (up from 53/108) with the same **1/200** false-refusal rate. Details: [evals/results/guard_eval.md](evals/results/guard_eval.md).
- **Evals:** 3,010 golden items; `make eval-guards` needs no keys; `make eval-deepeval` needs `OPENAI_API_KEY` and `ANTHROPIC_API_KEY` and should not be run until those keys are intended for use.
- **Frontend:** Vite app, live API by default (`make fe-dev`). Mock data only with `VITE_USE_MOCK=true` (`make fe-mock`).

Still later: an optional reranker, parent-chapter expansion for the LLM, and the Russian translations (need a verse map).

## Stack
Python 3.12 · FastAPI · Milvus Lite · bge-m3 · OpenAI (DeepSeek optional) · DeepEval · Vite + React + TypeScript

## Data
| Corpus | English | Chinese | Russian (later) |
|---|---|---|---|
| Bible | KJV (public domain) | Chinese Union Version, Simplified (public domain) | Synodal 1876 (public domain) |
| Quran | Pickthall 1930 (public domain) | Ma Jian (copyrighted until end of 2028; in the repo, non-commercial use) | Sablukov 1878 (public domain) |

Bible texts come from [getBible](https://api.getbible.net/v2/); Quran translations from [Tanzil](https://tanzil.net/trans/) (non-commercial terms apply).

## Quick start

```bash
cp .env.example .env
uv sync
# Download the pre-built Milvus Lite index (or `make chunks` to embed locally):
make fetch-index
make index-check

# API: http://localhost:8000  (GET/POST /search, GET /verse/{ref}, POST /answer, GET /health)
make api

# Frontend: http://localhost:5173  (live API is the default)
make fe-install
make fe-dev
# canned answers only:
make fe-mock
```

Examples (the first call that needs bge-m3 on a fresh process is slow):

```bash
curl -s http://localhost:8000/health
curl -sG http://localhost:8000/search --data-urlencode 'query=爱人如己' --data-urlencode 'translation=cuv' --data-urlencode 'limit=3'
curl -s http://localhost:8000/verse/John.3.16
curl -s http://localhost:8000/verse/2Chr.30.19
```

`/search` accepts `query` (required, max 1000 characters), optional `translation` (`kjv` | `cuv` | `quran_en` | `quran_zh`), `corpus` (`bible` | `quran`), `mode` (`hybrid` default, or `dense` / `sparse`), and `limit` (1–20, default 10).

`GET /verse/{canon_ref}` accepts a single verse (`John.3.16`, `Q2:255`) or a same-chapter range (`Matt.6.14-16`). CUV verses that were merged into the previous verse in the source data (stored as a lone "a") are shown with the previous verse and a short note; the JSONL itself is not changed.

`POST /answer` runs the input guard, hybrid search, generation, and the output guard. Generation defaults to OpenAI (`gpt-4o-mini`, `OPENAI_API_KEY`). Set `LLM_PROVIDER=deepseek` to use DeepSeek instead. If the key is missing, `/answer` returns 503 when it would have to call the model (off-topic refusals still return 200). Input-guard rates: `make eval-guards` (no LLM). Full DeepEval: `make eval-deepeval` (needs `OPENAI_API_KEY` and `ANTHROPIC_API_KEY`; do not run it until the keys are intended for use).


## Project layout
See [AGENTS.md](AGENTS.md) and [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).


## Retrieval tuning

Smoke-set comparison of dense-only, sparse-only, and hybrid RRF (50 scored items from `evals/datasets/golden_smoke.jsonl`; 10 items with no expected refs skipped). Each question is encoded once; the same vectors are reused across configs. A `corpus` filter is applied when the item is labelled `bible` or `quran`.

| config | candidates | k | Recall@10 | MRR | Recall@10 (en) | MRR (en) | Recall@10 (zh) | MRR (zh) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| dense | — | — | 0.491 | 0.507 | 0.423 | 0.483 | 0.560 | 0.532 |
| sparse | — | — | 0.592 | 0.546 | 0.609 | 0.596 | 0.575 | 0.496 |
| hybrid (20/20) | 20 | 20 | 0.655 | 0.609 | 0.723 | 0.658 | 0.587 | 0.560 |
| hybrid (20/60) | 20 | 60 | 0.655 | 0.609 | 0.723 | 0.658 | 0.587 | 0.560 |
| hybrid (50/20) | 50 | 20 | 0.665 | 0.596 | 0.703 | 0.634 | 0.627 | 0.558 |
| hybrid (50/60) (default) | 50 | 60 | 0.645 | 0.591 | 0.663 | 0.626 | 0.627 | 0.556 |
| hybrid (100/20) | 100 | 20 | 0.659 | 0.593 | 0.683 | 0.621 | 0.635 | 0.565 |
| hybrid (100/60) | 100 | 60 | 0.643 | 0.590 | 0.631 | 0.612 | 0.655 | 0.568 |

Best on this slice: **hybrid, candidates=50, k=20** (Recall@10 0.665, MRR 0.596). Every hybrid grid point beats dense-only and sparse-only. The code default remains 50/60.

For the query `forgive others`, dense ranks `kjv:Col.3.13-15` first, but hybrid drops it out of the top 10 (rank 16 unfiltered, 13 with `corpus=bible`). This is not a broken filter: both `AnnSearchRequest`s get the same expression, and a bible filter admits no Surah 40 rows. Sparse never places that Colossians chunk in its top 200 — the verse says "forgiving one another", while sparse's #1 (`kjv:Luke.23.33-35`) contains the exact tokens "forgive" and "others". RRF only scores a document in lists where it appears, so a dense-only #1 loses to passages mid-ranked in both lists. Unfiltered hybrid also lifts Surah 40 (Ghafir, **The Forgiver**) because every English chunk of that surah is prefixed with `The Forgiver 40`. Full ranks, protocol and skipped items: [evals/results/rrf_tuning.md](evals/results/rrf_tuning.md). Re-run with `python scripts/tune_rrf.py`.

## License
Code: MIT (planned). Scripture texts keep their own licenses listed above.
