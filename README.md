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
_Coming soon._ Planned:
```bash
cp .env.example .env
docker compose up -d
uv sync
uv run python -m scripts.ingest
uv run uvicorn bible_rag.api.main:app --reload
cd frontend && npm install && npm run dev
```

## Project layout
See [AGENTS.md](AGENTS.md) and [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## License
Code: MIT (planned). Scripture texts keep their own licenses listed above.
