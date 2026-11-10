# AGENTS.md — Guide for AI coding assistants

Read this first, then `docs/ARCHITECTURE.md` and `docs/DECISIONS.md`.

## Project
Multi-scripture RAG (Bible + Quran) portfolio project. Ask questions in English or Chinese, get grounded answers with verse citations, and compare the same verse across translations.

## Current scope (phase 1)
- Languages: **English + Simplified Chinese only**. Russian is deferred.
- Order of work: frontend, ingest, hybrid retrieval, generation, and evals are in place for phase 1.

## Stack
- Backend: Python 3.12, `uv`, FastAPI, `pymilvus`
- DB: Milvus 2.5 standalone (docker-compose: etcd + MinIO + Milvus); dense + sparse hybrid search with RRF
- Embeddings: `BAAI/bge-m3` (1024-dim, multilingual, dense + sparse)
- LLM: OpenAI `gpt-4o-mini` by default (DeepSeek optional via `LLM_PROVIDER`)
- Evals: DeepEval
- Frontend: Vite + React + TypeScript in `frontend/`
- Optional: `go-embed-worker/` — concurrent batch embedding worker in Go

## Layout
```
data/bible/        kjv.jsonl, cuv.jsonl, synodal.jsonl, books.json
data/quran/        quran_en.jsonl, quran_zh.jsonl, quran_ru.jsonl, surahs.json
data/raw/          raw sources + Quran build.py (gitignored)
src/bible_rag/store/  Milvus schema (passages + chunks collections)
scripts/           download / ingest CLIs
src/bible_rag/     ingest, chunking, embedding, retrieval, generation, api
evals/datasets/    golden Q&A sets for DeepEval
frontend/          Vite React app
docs/              architecture, decisions, experiment results
```

## Data format (one verse per line, JSONL)
`translation, book_index, book_code, book_name, chapter, verse, text` (+ `corpus: "quran"` for Quran files).
Bible `book_code` is OSIS (`Gen`, `Ps`, `John`). Quran `book_code` is `Q001`..`Q114`, and `chapter == book_index`.

## Rules
- Every answer must cite references (e.g. `John 3:16`, `Q2:255`). If retrieval finds nothing relevant, say so; never invent verses.
- Keep native numbering in `passages`; cross-translation alignment uses `canon_ref` (KJV-style `Ps.23.1`, Quran `Q2.255`).
- `data/quran/quran_zh.jsonl` (Ma Jian) **is committed**. It remains under copyright until the end of 2028 and is for personal / research / non-commercial use only; do not treat it as public domain.
- Secrets live in `.env` (see `.env.example`); never hardcode keys.
- Small, focused PRs. Add tests in `tests/` for ingest and retrieval logic.
- The owner is learning: explain non-obvious design choices in PR descriptions.
