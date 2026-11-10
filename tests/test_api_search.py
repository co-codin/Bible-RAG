"""API tests. Unit tests monkeypatch `search` so bge-m3 is never loaded."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from bible_rag.api.main import app
from bible_rag.api.schemas import MAX_QUERY_LEN
from bible_rag.retrieval.hybrid import Hit

DB = Path(__file__).resolve().parents[1] / ".milvus" / "bible_rag.db"

SAMPLE_HITS = [
    Hit(
        pk="cuv:Rom.13.8-10",
        translation="cuv",
        parent_key="cuv:Rom.13",
        canon_refs=["Rom.13.8", "Rom.13.9", "Rom.13.10"],
        chunk_text="罗马书 13\n爱人不可虚假。",
        score=0.0328,
    ),
    Hit(
        pk="cuv:Matt.22.37-39",
        translation="cuv",
        parent_key="cuv:Matt.22",
        canon_refs=["Matt.22.37", "Matt.22.38", "Matt.22.39"],
        chunk_text="马太福音 22\n要爱人如己。",
        score=0.0301,
    ),
    Hit(
        pk="cuv:Jas.2.7-9",
        translation="cuv",
        parent_key="cuv:Jas.2",
        canon_refs=["Jas.2.7", "Jas.2.8", "Jas.2.9"],
        chunk_text="雅各书 2\n要爱人如己。",
        score=0.0280,
    ),
]


@pytest.fixture
def client(monkeypatch):
    mocked = MagicMock(return_value=SAMPLE_HITS)
    monkeypatch.setattr("bible_rag.api.main.search", mocked)
    with TestClient(app) as test_client:
        yield test_client, mocked


def test_health_ok(client):
    test_client, _ = client
    res = test_client.get("/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert body["index"] in {"ready", "missing"}
    if body["index"] == "ready":
        assert body["fingerprint"]


def test_post_search_returns_hits(client):
    test_client, mocked = client
    res = test_client.post(
        "/search",
        json={"query": "爱人如己", "translation": "cuv", "mode": "hybrid", "limit": 3},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["query"] == "爱人如己"
    assert body["translation"] == "cuv"
    assert body["mode"] == "hybrid"
    assert body["limit"] == 3
    assert len(body["hits"]) == 3
    assert body["hits"][0]["pk"] == "cuv:Rom.13.8-10"
    assert body["hits"][0]["canon_refs"] == ["Rom.13.8", "Rom.13.9", "Rom.13.10"]
    mocked.assert_called_once()
    kwargs = mocked.call_args.kwargs
    assert kwargs["query"] == "爱人如己"
    assert kwargs["translation"] == "cuv"
    assert kwargs["limit"] == 3
    assert kwargs["mode"] == "hybrid"


def test_get_search_returns_hits(client):
    test_client, mocked = client
    res = test_client.get(
        "/search",
        params={"query": "love thy neighbour", "translation": "kjv", "limit": 5},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["query"] == "love thy neighbour"
    assert body["hits"][0]["score"] == pytest.approx(0.0328)
    assert mocked.call_args.kwargs["translation"] == "kjv"
    assert mocked.call_args.kwargs["limit"] == 5
    assert mocked.call_args.kwargs["mode"] == "hybrid"


def test_search_rejects_empty_and_whitespace_query(client):
    test_client, mocked = client
    assert test_client.post("/search", json={"query": ""}).status_code == 422
    assert test_client.post("/search", json={"query": "   "}).status_code == 422
    assert test_client.get("/search").status_code == 422
    assert test_client.get("/search", params={"query": "  "}).status_code == 422
    mocked.assert_not_called()


def test_search_rejects_too_long_query(client):
    test_client, mocked = client
    too_long = "a" * (MAX_QUERY_LEN + 1)
    assert test_client.post("/search", json={"query": too_long}).status_code == 422
    assert test_client.get("/search", params={"query": too_long}).status_code == 422
    mocked.assert_not_called()


def test_search_rejects_bad_params(client):
    test_client, mocked = client
    assert (
        test_client.post("/search", json={"query": "love", "translation": "KJV"}).status_code == 422
    )
    assert test_client.post("/search", json={"query": "love", "corpus": "all"}).status_code == 422
    assert test_client.post("/search", json={"query": "love", "mode": "rrf"}).status_code == 422
    assert test_client.post("/search", json={"query": "love", "limit": 21}).status_code == 422
    assert test_client.post("/search", json={"query": "love", "limit": 0}).status_code == 422
    assert (
        test_client.get("/search", params={"query": "love", "translation": "synodal"}).status_code
        == 422
    )
    mocked.assert_not_called()


@pytest.mark.skipif(not DB.exists(), reason="no local Milvus Lite db")
def test_search_integration_against_local_db():
    with TestClient(app) as test_client:
        res = test_client.get(
            "/search",
            params={"query": "love thy neighbour", "translation": "kjv", "limit": 3},
        )
    assert res.status_code == 200
    body = res.json()
    assert body["hits"], body
    assert len(body["hits"]) <= 3
    for hit in body["hits"]:
        assert hit["translation"] == "kjv"
        assert hit["canon_refs"]
        assert hit["pk"].startswith("kjv:")
        assert hit["chunk_text"]
        assert isinstance(hit["score"], float)
