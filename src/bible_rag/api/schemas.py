"""Request and response models for the search API."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

TRANSLATIONS = frozenset({"kjv", "cuv", "quran_en", "quran_zh"})
CORPORA = frozenset({"bible", "quran"})
MODES = frozenset({"hybrid", "dense", "sparse"})

MAX_QUERY_LEN = 1000
MAX_LIMIT = 20
DEFAULT_LIMIT = 10
Mode = Literal["hybrid", "dense", "sparse"]


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=MAX_QUERY_LEN)
    translation: str | None = None
    corpus: str | None = None
    mode: Mode = "hybrid"
    limit: int = Field(default=DEFAULT_LIMIT, ge=1, le=MAX_LIMIT)

    @field_validator("query")
    @classmethod
    def query_stripped(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("query must not be empty")
        if len(value) > MAX_QUERY_LEN:
            raise ValueError(f"query must be at most {MAX_QUERY_LEN} characters")
        return value

    @field_validator("translation")
    @classmethod
    def translation_known(cls, value: str | None) -> str | None:
        if value is None or value == "":
            return None
        if value not in TRANSLATIONS:
            raise ValueError(f"translation must be one of {sorted(TRANSLATIONS)}")
        return value

    @field_validator("corpus")
    @classmethod
    def corpus_known(cls, value: str | None) -> str | None:
        if value is None or value == "":
            return None
        if value not in CORPORA:
            raise ValueError(f"corpus must be one of {sorted(CORPORA)}")
        return value


class HitOut(BaseModel):
    pk: str
    translation: str
    parent_key: str
    canon_refs: list[str]
    chunk_text: str
    score: float


class SearchResponse(BaseModel):
    query: str
    translation: str | None
    corpus: str | None
    mode: Mode
    limit: int
    hits: list[HitOut]


class HealthResponse(BaseModel):
    status: str
    index: str
    fingerprint: str | None = None
