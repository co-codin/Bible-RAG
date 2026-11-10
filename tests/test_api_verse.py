"""API tests for GET /verse. Uses the corpus JSONL (passages collection may be empty)."""

from fastapi.testclient import TestClient

from bible_rag.api.main import app


def test_verse_john_316():
    with TestClient(app) as client:
        res = client.get("/verse/John.3.16")
    assert res.status_code == 200
    body = res.json()
    assert body["canon_ref"] == "John.3.16"
    assert body["corpus"] == "bible"
    assert body["book_code"] == "John"
    assert body["chapter"] == 3
    assert body["verse_start"] == 16
    assert body["book_name"]["en"]
    assert body["book_name"]["zh"]
    verse = body["verses"][0]
    assert verse["en"]["translation"] == "kjv"
    assert "begotten Son" in verse["en"]["text"]
    assert verse["zh"]["translation"] == "cuv"
    assert verse["zh"]["merged_with_previous"] is False


def test_verse_quran_short_ref_and_range():
    with TestClient(app) as client:
        one = client.get("/verse/Q2:255")
        rng = client.get("/verse/Matt.6.14-15")
    assert one.status_code == 200
    body = one.json()
    assert body["canon_ref"] == "Q002.2.255"
    assert body["corpus"] == "quran"
    assert body["verses"][0]["en"]["translation"] == "quran_en"
    assert body["verses"][0]["zh"]["translation"] == "quran_zh"

    assert rng.status_code == 200
    assert [v["verse"] for v in rng.json()["verses"]] == [14, 15]


def test_verse_cuv_merged_placeholder():
    with TestClient(app) as client:
        res = client.get("/verse/2Chr.30.19")
    assert res.status_code == 200
    zh = res.json()["verses"][0]["zh"]
    assert zh["merged_with_previous"] is True
    assert zh["text"] != "a"
    assert zh["note"]


def test_verse_rejects_bad_and_missing_refs():
    with TestClient(app) as client:
        assert client.get("/verse/not-a-ref").status_code == 422
        assert client.get("/verse/Foo.1.1").status_code == 422
        assert client.get("/verse/Matt.6.18-14").status_code == 422
        assert client.get("/verse/Q002.3.1").status_code == 422
        assert client.get("/verse/Matt.99.1").status_code == 404
