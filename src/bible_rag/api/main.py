"""FastAPI app: hybrid search over the local Milvus Lite index.

The model and Milvus client stay lazy (see `bible_rag.retrieval.hybrid`); the first
`/search` call loads bge-m3. At startup we only check the index manifest, and only
when a manifest file is present, so unit tests and a missing db still boot.

    uv run uvicorn bible_rag.api.main:app --reload --port 8000
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import Annotated

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError

from bible_rag.api.schemas import (
    DEFAULT_LIMIT,
    MAX_LIMIT,
    MAX_QUERY_LEN,
    HealthResponse,
    HitOut,
    SearchRequest,
    SearchResponse,
)
from bible_rag.index_manifest import IndexMismatchError, check, manifest_path
from bible_rag.retrieval.hybrid import DEFAULT_URI, search

load_dotenv()

DEFAULT_CORS = "http://localhost:5173,http://127.0.0.1:5173"


def _milvus_uri() -> str:
    return os.environ.get("MILVUS_URI", DEFAULT_URI)


def _cors_origins() -> list[str]:
    raw = os.environ.get("CORS_ORIGINS", DEFAULT_CORS)
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


@asynccontextmanager
async def lifespan(app: FastAPI):
    uri = _milvus_uri()
    app.state.manifest = None
    if manifest_path(uri).exists():
        try:
            app.state.manifest = check(uri)
        except IndexMismatchError as exc:
            raise RuntimeError(f"refusing to serve a mismatched index: {exc}") from exc
    yield


app = FastAPI(title="Bible-RAG", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _index_status() -> tuple[str, str | None]:
    manifest = getattr(app.state, "manifest", None)
    if not manifest:
        return "missing", None
    return "ready", manifest.get("fingerprint")


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    index, fingerprint = _index_status()
    return HealthResponse(status="ok", index=index, fingerprint=fingerprint)


def _run_search(req: SearchRequest) -> SearchResponse:
    try:
        hits = search(
            query=req.query,
            translation=req.translation,
            corpus=req.corpus,
            limit=req.limit,
            mode=req.mode,
            uri=_milvus_uri(),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return SearchResponse(
        query=req.query,
        translation=req.translation,
        corpus=req.corpus,
        mode=req.mode,
        limit=req.limit,
        hits=[
            HitOut(
                pk=h.pk,
                translation=h.translation,
                parent_key=h.parent_key,
                canon_refs=list(h.canon_refs),
                chunk_text=h.chunk_text,
                score=h.score,
            )
            for h in hits
        ],
    )


def _search_query(
    query: Annotated[str, Query(min_length=1, max_length=MAX_QUERY_LEN)],
    translation: Annotated[str | None, Query()] = None,
    corpus: Annotated[str | None, Query()] = None,
    mode: Annotated[str, Query()] = "hybrid",
    limit: Annotated[int, Query(ge=1, le=MAX_LIMIT)] = DEFAULT_LIMIT,
) -> SearchRequest:
    try:
        return SearchRequest(
            query=query, translation=translation, corpus=corpus, mode=mode, limit=limit
        )
    except ValidationError as exc:
        raise RequestValidationError(exc.errors()) from exc


@app.get("/search", response_model=SearchResponse)
def search_get(req: Annotated[SearchRequest, Depends(_search_query)]) -> SearchResponse:
    return _run_search(req)


@app.post("/search", response_model=SearchResponse)
def search_post(req: SearchRequest) -> SearchResponse:
    return _run_search(req)
