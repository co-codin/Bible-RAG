"""End-to-end answer pipeline: input guard -> retrieval -> generate -> output guard."""

from __future__ import annotations

from dataclasses import dataclass, field

from bible_rag.generation.guards import (
    NOT_FOUND,
    GuardDecision,
    check_input,
    check_output,
    detect_lang,
)
from bible_rag.generation.llm import LLMClient, LLMUnavailable, get_llm
from bible_rag.generation.prompt import build_messages
from bible_rag.retrieval.hybrid import DEFAULT_URI, Hit, search


@dataclass
class AnswerResult:
    query: str
    answer: str | None = None
    citations: list[str] = field(default_factory=list)
    hits: list[Hit] = field(default_factory=list)
    refused: bool = False
    refusal_reason: str | None = None
    refusal_message: str | None = None


def _from_input_guard(query: str, decision: GuardDecision) -> AnswerResult:
    return AnswerResult(
        query=query,
        refused=True,
        refusal_reason=decision.reason,
        refusal_message=decision.message,
    )


def answer_question(
    query: str,
    *,
    translation: str | None = None,
    corpus: str | None = None,
    mode: str = "hybrid",
    limit: int = 10,
    lang: str | None = None,
    uri: str | None = None,
    search_fn=None,
    llm: LLMClient | None = None,
    llm_factory=None,
) -> AnswerResult:
    """Run the guarded generation pipeline.

    `llm` should be passed in tests (a FakeLLMClient). If it is omitted, the
    factory is called only after the input guard passes and retrieval returns
    hits, and it raises LLMUnavailable when the configured key is missing.
    Defaults are resolved at call time so tests can monkeypatch `search` / `get_llm`.
    """
    if search_fn is None:
        search_fn = search
    lang = lang or detect_lang(query)
    decision = check_input(query)
    if not decision.ok:
        return _from_input_guard(query, decision)

    hits = search_fn(
        query=query,
        translation=translation,
        corpus=corpus,
        limit=limit,
        mode=mode,
        uri=uri or DEFAULT_URI,
    )
    if not hits:
        return AnswerResult(query=query, answer=NOT_FOUND[lang], citations=[], hits=[])

    client = llm if llm is not None else (llm_factory or get_llm)()
    messages = build_messages(query, hits, lang=lang)
    raw = client.complete(messages)
    out = check_output(raw, hits, lang=lang)
    if not out.ok:
        return AnswerResult(
            query=query,
            hits=hits,
            refused=True,
            refusal_reason=out.reason,
            refusal_message=out.message,
        )
    return AnswerResult(
        query=query,
        answer=out.answer,
        citations=out.citations,
        hits=hits,
    )


# Re-export so callers can catch the 503-style error without an extra import path.
__all__ = ["AnswerResult", "LLMUnavailable", "answer_question"]
