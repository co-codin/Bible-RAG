"""Hybrid retrieval over the `chunks` collection: dense + sparse, fused with RRF.

Why two searches?
    dense  (bge-m3 1024-d vector, COSINE): matches *meaning*. "forgive others" finds
           "forbearing one another" even with no shared words, and works across
           languages (an English query can hit Chinese verses).
    sparse (bge-m3 lexical weights, IP):   matches *words*. Good at names, rare terms
           and exact phrases ("Night of Power", "饶恕"), where dense can drift.
Each is good where the other is weak, so we run both and merge the rankings.

Why RRF (Reciprocal Rank Fusion)?
    Cosine scores (~0.3-0.7) and sparse IP scores (~0.0-0.3) live on different
    scales, so adding them is meaningless. RRF ignores raw scores and only uses
    ranks:  score(doc) = sum over lists of 1 / (k + rank).  With k=60 a doc ranked
    1st in one list scores 1/61 ≈ 0.0164; ranked 1st in both, 2/61 ≈ 0.0328.
    Being decent in both lists beats being great in only one.

One bge-m3 forward pass gives both query vectors, and Milvus runs both searches
and the fusion server-side in a single `hybrid_search` call.

CLI:
    python -m bible_rag.retrieval.hybrid "forgive others"
    python -m bible_rag.retrieval.hybrid "饶恕" --translation cuv
    python -m bible_rag.retrieval.hybrid "饶恕" --mode dense      # or sparse, for comparison
"""

from __future__ import annotations

import argparse
import os
import re
from dataclasses import dataclass
from functools import cache

from pymilvus import AnnSearchRequest, MilvusClient, RRFRanker

from bible_rag.store.schema import CHUNKS

DEFAULT_URI = os.environ.get("MILVUS_URI", "./.milvus/bible_rag.db")

CANDIDATES = 50  # per-list depth: how many hits each search hands to the fusion step
RRF_K = 60  # standard RRF constant; larger k flattens the gap between ranks
TOP_K = 10  # final number of hits returned

OUTPUT_FIELDS = ["pk", "translation", "parent_key", "canon_refs", "chunk_text"]
_SAFE = re.compile(r"^[a-z_]+$")  # filter values go into an expression string


@dataclass(frozen=True)
class Hit:
    pk: str  # cuv:Matt.6.13-15
    translation: str  # kjv | cuv | quran_en | quran_zh
    parent_key: str  # cuv:Matt.6  (the chapter, for LLM context later)
    canon_refs: list[str]  # ["Matt.6.13", "Matt.6.14", "Matt.6.15"]
    chunk_text: str
    score: float  # RRF score in hybrid mode, cosine / IP in single modes


# --- lazy singletons --------------------------------------------------------
# Loading bge-m3 takes seconds and ~2 GB of RAM, so do it once, on first use
# (importing this module stays cheap). @cache turns each function into a
# memoised zero-arg factory: the first call builds the object, later calls reuse it.


@cache
def _model():
    from bible_rag.embedding.bge_m3 import BGEM3  # heavy: pulls in torch

    return BGEM3()


@cache
def _client(uri: str) -> MilvusClient:
    client = MilvusClient(uri=uri)
    client.load_collection(CHUNKS)  # a reopened collection starts 'released'
    return client


# --- helpers ----------------------------------------------------------------


def build_filter(translation: str | None = None, corpus: str | None = None) -> str:
    """Milvus boolean expression, e.g. 'translation == "cuv" and corpus == "bible"'."""
    parts = []
    for field, value in (("translation", translation), ("corpus", corpus)):
        if value:
            if not _SAFE.match(value):
                raise ValueError(f"bad {field} value: {value!r}")
            parts.append(f'{field} == "{value}"')
    return " and ".join(parts)


def _to_hits(results) -> list[Hit]:
    return [
        Hit(
            pk=h["entity"]["pk"],
            translation=h["entity"]["translation"],
            parent_key=h["entity"]["parent_key"],
            canon_refs=list(h["entity"]["canon_refs"]),
            chunk_text=h["entity"]["chunk_text"],
            score=float(h["distance"]),
        )
        for h in results[0]  # one query in -> one result list out
    ]


# --- public API -------------------------------------------------------------


def search(
    query: str,
    translation: str | None = None,
    corpus: str | None = None,
    limit: int = TOP_K,
    mode: str = "hybrid",
    uri: str = DEFAULT_URI,
    candidates: int = CANDIDATES,
    rrf_k: int = RRF_K,
    dense: list[list[float]] | None = None,
    sparse: list[dict[int, float]] | None = None,
) -> list[Hit]:
    """Top `limit` chunks for `query`. mode: 'hybrid' (default), 'dense' or 'sparse'.

    `candidates` is the per-list depth handed to RRF (hybrid only). `rrf_k` is the
    RRF constant k. Pass precomputed `dense` and `sparse` (both, from one encode)
    to skip the model — used by the tuning script to reuse embeddings across configs.
    """
    if mode not in ("hybrid", "dense", "sparse"):
        raise ValueError(f"mode must be hybrid, dense or sparse, not {mode!r}")
    if candidates < 1 or rrf_k < 1 or limit < 1:
        raise ValueError("candidates, rrf_k and limit must be >= 1")
    if (dense is None) ^ (sparse is None):
        raise ValueError("dense and sparse must be provided together")
    if dense is None:
        dense, sparse = _model().encode([query])  # one forward pass -> both vectors
    expr = build_filter(translation, corpus)
    client = _client(uri)

    dense_params = {"metric_type": "COSINE", "params": {"ef": max(64, candidates)}}
    sparse_params = {"metric_type": "IP"}

    if mode in ("dense", "sparse"):  # single-list search, for comparisons
        field, data, params = (
            ("dense", dense, dense_params) if mode == "dense" else ("sparse", sparse, sparse_params)
        )
        res = client.search(
            CHUNKS,
            data=data,
            anns_field=field,
            search_params=params,
            filter=expr,
            limit=limit,
            output_fields=OUTPUT_FIELDS,
        )
        return _to_hits(res)

    # Two candidate lists, each filtered the same way, then fused by RRF.
    requests = [
        AnnSearchRequest(dense, "dense", dense_params, limit=candidates, expr=expr or None),
        AnnSearchRequest(sparse, "sparse", sparse_params, limit=candidates, expr=expr or None),
    ]
    res = client.hybrid_search(
        CHUNKS,
        reqs=requests,
        ranker=RRFRanker(k=rrf_k),
        limit=limit,
        output_fields=OUTPUT_FIELDS,
    )
    return _to_hits(res)


def main() -> None:
    ap = argparse.ArgumentParser(description="Hybrid (dense + sparse, RRF) search over chunks")
    ap.add_argument("query")
    ap.add_argument("--translation", help="kjv | cuv | quran_en | quran_zh")
    ap.add_argument("--corpus", help="bible | quran")
    ap.add_argument("--mode", default="hybrid", choices=["hybrid", "dense", "sparse"])
    ap.add_argument("--limit", type=int, default=TOP_K)
    ap.add_argument(
        "--candidates", type=int, default=CANDIDATES, help="per-list depth for RRF (hybrid)"
    )
    ap.add_argument("--rrf-k", type=int, default=RRF_K, dest="rrf_k", help="RRF constant k")
    ap.add_argument("--uri", default=DEFAULT_URI)
    a = ap.parse_args()

    hits = search(
        a.query,
        a.translation,
        a.corpus,
        a.limit,
        a.mode,
        a.uri,
        candidates=a.candidates,
        rrf_k=a.rrf_k,
    )
    print(f"{a.mode} | {a.query!r} | {build_filter(a.translation, a.corpus) or 'no filter'}")
    for i, h in enumerate(hits, 1):
        text = h.chunk_text.replace("\n", " ")
        print(f"{i:2}. {h.score:.4f}  {h.pk:28} {text[:60]}")


if __name__ == "__main__":
    main()
