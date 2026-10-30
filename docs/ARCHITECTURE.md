# Architecture

## Flow
```mermaid
flowchart LR
  Q[User question] --> E[bge-m3 embed]
  E --> H[Milvus hybrid search: dense HNSW + sparse]
  H --> F[RRF fusion]
  F --> R[optional rerank: bge-reranker-v2-m3]
  R --> P[Expand child -> parent context]
  P --> L[DeepSeek / Qwen with citation prompt]
  L --> A[Answer + citations]
  A --> X[Parallel verses via canon_ref]
```

## Milvus collections
- `passages`: pk `kjv:Matt.6.14`, corpus, translation, book_code, book_name, chapter, verse, canon_ref, text (+ 2-dim placeholder vector). Used for parent expansion and side-by-side compare.
- `chunks`: pk, corpus, translation, parent_key (`cuv:Matt.6`), canon_refs[], context_prefix, chunk_text, dense (1024, HNSW/COSINE), sparse (SPARSE_INVERTED_INDEX/IP).
- Schema code: `src/bible_rag/store/schema.py`.

## Chunking
- Child: single verse or 2–3 verse sliding window (retrieval unit).
- Parent: chapter or pericope (context for the LLM).
- Contextual retrieval: prepend a one-line LLM-generated context (book, chapter, theme) to each child before embedding.

## API (planned)
- `POST /api/ask` `{question, corpus?, translations?}` → `{answer, citations[]}`
- `GET /api/verse/{canon_ref}` → the same verse in all loaded translations

## Frontend
Single page: ask box + filters (corpus, language), answer with clickable citations, side-by-side verse comparison. Dev: Vite proxy `/api` → FastAPI. Prod: multi-stage Dockerfile builds `frontend/dist`, served by FastAPI as static files.

## Evaluation
DeepEval golden set (50–100 Q&A, EN + ZH, Bible + Quran). Metrics: contextual precision/recall, faithfulness, answer relevancy. Experiments: verse vs window chunks, with/without contextual prefix, with/without rerank. Results go in `docs/EXPERIMENTS.md`.
