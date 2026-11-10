from pathlib import Path

import pytest

from bible_rag.embedding.bge_m3 import DENSE_DIM
from bible_rag.retrieval.hybrid import build_filter, search

DB = Path(__file__).resolve().parents[1] / ".milvus" / "bible_rag.db"

# Dummy vectors so tests can hit Milvus without loading bge-m3.
_DENSE = [[0.0] * DENSE_DIM]
_DENSE[0][0] = 1.0
_SPARSE = [{1: 1.0}]


def test_build_filter_rejects_unsafe_values():
    with pytest.raises(ValueError, match="bad translation"):
        build_filter(translation="kjv or 1==1")
    with pytest.raises(ValueError, match="bad corpus"):
        build_filter(corpus="bible'; drop")
    with pytest.raises(ValueError, match="bad translation"):
        build_filter(translation="KJV")
    with pytest.raises(ValueError, match="bad translation"):
        build_filter(translation="kjv-1")


def test_build_filter_builds_and_joins_clauses():
    assert build_filter() == ""
    assert build_filter(None, None) == ""
    assert build_filter(translation="quran_en") == 'translation == "quran_en"'
    assert build_filter(corpus="bible") == 'corpus == "bible"'
    assert build_filter("cuv", "bible") == 'translation == "cuv" and corpus == "bible"'


def test_search_rejects_bad_mode_and_partial_vectors():
    with pytest.raises(ValueError, match="mode must be"):
        search("forgive others", mode="rrf", dense=_DENSE, sparse=_SPARSE)
    with pytest.raises(ValueError, match="provided together"):
        search("forgive others", dense=_DENSE)
    with pytest.raises(ValueError, match="must be >= 1"):
        search("forgive others", candidates=0, dense=_DENSE, sparse=_SPARSE)


@pytest.mark.skipif(not DB.exists(), reason="no local Milvus Lite db")
def test_hybrid_filter_applies_to_both_requests():
    """The same expr is attached to both AnnSearchRequests; Quran rows must not leak."""
    kwargs = {"query": "dummy", "dense": _DENSE, "sparse": _SPARSE, "uri": str(DB), "limit": 10}
    bible = search(corpus="bible", **kwargs)
    assert bible
    assert all(h.translation in {"kjv", "cuv"} for h in bible)
    assert all(not h.pk.startswith("quran") for h in bible)

    quran = search(corpus="quran", **kwargs)
    assert quran
    assert all(h.translation in {"quran_en", "quran_zh"} for h in quran)

    kjv = search(translation="kjv", corpus="bible", **kwargs)
    assert kjv
    assert all(h.translation == "kjv" for h in kjv)
