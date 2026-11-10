# Bible-RAG

Multilingual retrieval-augmented QA over the **Bible** and the **Quran**. Ask in English or Chinese, get answers grounded in scripture with verse citations, and compare the same verse across translations side by side.

> Status: work in progress (phase 1: English + Chinese, frontend first).

## Features (planned)
- Hybrid search: Milvus (bge-m3 dense + sparse), fused with RRF, optional reranker
- Parent-child chunking with contextual retrieval
- Cross-lingual retrieval (ask in Chinese, find English verses and vice versa)
- Cited answers via DeepSeek / Qwen
- Evaluation with DeepEval and documented chunking/rerank experiments
- React UI with side-by-side verse comparison

## Stack
Python 3.12 · FastAPI · Milvus · bge-m3 · DeepSeek / Qwen · DeepEval · Vite + React + TypeScript · Docker Compose

## Data
| Corpus | English | Chinese | Russian (later) |
|---|---|---|---|
| Bible | KJV (public domain) | Chinese Union Version, Simplified (public domain) | Synodal 1876 (public domain) |
| Quran | Pickthall 1930 (public domain) | Ma Jian (copyrighted, built locally, not in repo) | Sablukov 1878 (public domain) |

Bible texts come from [getBible](https://api.getbible.net/v2/); Quran translations from [Tanzil](https://tanzil.net/trans/) (non-commercial terms apply).

## Quick start

```bash
cp .env.example .env
uv sync
# Download the pre-built Milvus Lite index (or `make chunks` to embed locally):
make fetch-index
make index-check

# API: http://localhost:8000  (GET/POST /search, GET /health)
make api

# Frontend: http://localhost:5173
make fe-install
make fe-mock          # canned answers
# or, with the API already running:
make fe-dev           # live hybrid search (VITE_USE_MOCK=false)
```

Search examples (the first `/search` call on a fresh process loads bge-m3, so it is slow):

```bash
curl -s http://localhost:8000/health
curl -sG http://localhost:8000/search --data-urlencode 'query=爱人如己' --data-urlencode 'translation=cuv' --data-urlencode 'limit=3'
curl -sG http://localhost:8000/search --data-urlencode 'query=love thy neighbour' --data-urlencode 'translation=kjv' --data-urlencode 'limit=3'
```

`/search` accepts `query` (required, max 1000 characters), optional `translation` (`kjv` | `cuv` | `quran_en` | `quran_zh`), `corpus` (`bible` | `quran`), `mode` (`hybrid` default, or `dense` / `sparse`), and `limit` (1–20, default 10).

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
