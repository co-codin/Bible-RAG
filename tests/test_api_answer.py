"""API tests for POST /answer. The LLM is always a FakeLLMClient."""

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from bible_rag.api.main import app
from bible_rag.generation.llm import FakeLLMClient
from bible_rag.retrieval.hybrid import Hit

HIT = Hit(
    pk="kjv:Matt.6.13-15",
    translation="kjv",
    parent_key="kjv:Matt.6",
    canon_refs=["Matt.6.13", "Matt.6.14", "Matt.6.15"],
    chunk_text="Matthew 6\nFor if ye forgive men their trespasses...",
    score=0.03,
)


@pytest.fixture
def client(monkeypatch):
    # Do not let a box-level key leak into these tests.
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.setattr(
        "bible_rag.generation.answer.search",
        MagicMock(return_value=[HIT]),
    )
    monkeypatch.setattr(
        "bible_rag.generation.answer.get_llm",
        lambda: FakeLLMClient("The Father forgives those who forgive others [[Matt.6.14]]."),
    )
    with TestClient(app) as test_client:
        yield test_client


def test_answer_returns_citations(client):
    res = client.post("/answer", json={"query": "What does the Bible say about forgiveness?"})
    assert res.status_code == 200
    body = res.json()
    assert body["refused"] is False
    assert body["citations"] == ["Matt.6.14"]
    assert "[[Matt.6.14]]" in body["answer"]
    assert body["hits"][0]["pk"] == "kjv:Matt.6.13-15"


def test_answer_refuses_off_topic_without_a_key(client):
    res = client.post("/answer", json={"query": "Who won the 2018 FIFA World Cup?"})
    assert res.status_code == 200
    body = res.json()
    assert body["refused"] is True
    assert body["refusal_reason"] == "off_topic"
    assert body["answer"] is None
    assert body["refusal_message"]


def test_answer_rejects_bad_query(client):
    assert client.post("/answer", json={"query": ""}).status_code == 422
    assert client.post("/answer", json={"query": "love", "limit": 21}).status_code == 422


def test_answer_returns_503_when_key_missing(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.setattr(
        "bible_rag.generation.answer.search",
        MagicMock(return_value=[HIT]),
    )
    # No get_llm patch: the factory should raise and the API should map it to 503.
    with TestClient(app) as test_client:
        res = test_client.post(
            "/answer", json={"query": "What does the Bible say about forgiveness?"}
        )
    assert res.status_code == 503
    assert "OPENAI_API_KEY is not set" in res.json()["detail"]
