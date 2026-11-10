"""Wire DeepEval to the guarded RAG pipeline.

This script is a runner, not a test module (pytest should not collect it).
It needs keys and makes live LLM calls, so it is not executed in CI or in
local work that only exercises unit tests:

    OPENAI_API_KEY   generation (or DEEPSEEK_API_KEY if LLM_PROVIDER=deepseek)
    ANTHROPIC_API_KEY  DeepEval judge (see evals/judge.py)

Usage:
    uv run python -m evals.run_deepeval              # golden_smoke, answerable items
    uv run python -m evals.run_deepeval --dataset golden_en.jsonl
    uv run python -m evals.run_deepeval --limit 10

Do not run this without explicit approval and keys; it embeds queries and
calls both the generator and the judge.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

DATASETS = Path(__file__).resolve().parent / "datasets"


def _missing_keys() -> list[str]:
    missing = []
    provider = (os.environ.get("LLM_PROVIDER") or "openai").strip().lower()
    if provider == "deepseek":
        if not (os.environ.get("DEEPSEEK_API_KEY") or "").strip():
            missing.append("DEEPSEEK_API_KEY")
    else:
        if not (os.environ.get("OPENAI_API_KEY") or "").strip():
            missing.append("OPENAI_API_KEY")
    if not (os.environ.get("ANTHROPIC_API_KEY") or "").strip():
        missing.append("ANTHROPIC_API_KEY")
    return missing


def load_items(name: str, limit: int | None, answerable_only: bool) -> list[dict]:
    path = DATASETS / name
    items = [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]
    if answerable_only:
        items = [it for it in items if it.get("answerable")]
    if limit is not None:
        items = items[:limit]
    return items


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dataset", default="golden_smoke.jsonl")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument(
        "--include-unanswerable",
        action="store_true",
        help="also keep items whose expected behaviour is not_found",
    )
    args = ap.parse_args()

    missing = _missing_keys()
    if missing:
        sys.exit(
            "DeepEval runner needs these environment variables: "
            + ", ".join(missing)
            + ". Refusing to start so no accidental live calls are made."
        )

    # Imports that load evaluation SDKs stay below the key check.
    from deepeval import evaluate
    from deepeval.metrics import (
        AnswerRelevancyMetric,
        ContextualPrecisionMetric,
        ContextualRecallMetric,
        FaithfulnessMetric,
    )
    from deepeval.test_case import LLMTestCase

    from bible_rag.generation.answer import answer_question
    from evals.judge import judge

    items = load_items(args.dataset, args.limit, answerable_only=not args.include_unanswerable)
    if not items:
        sys.exit(f"no items loaded from {args.dataset}")

    model = judge()
    metrics = [
        ContextualPrecisionMetric(model=model, threshold=0.5),
        ContextualRecallMetric(model=model, threshold=0.5),
        FaithfulnessMetric(model=model, threshold=0.5),
        AnswerRelevancyMetric(model=model, threshold=0.5),
    ]

    cases = []
    for item in items:
        result = answer_question(
            item["question"],
            corpus=item["corpus"] if item.get("corpus") in {"bible", "quran"} else None,
            lang=item.get("lang"),
        )
        answer = result.answer or result.refusal_message or ""
        cases.append(
            LLMTestCase(
                input=item["question"],
                actual_output=answer,
                expected_output=item.get("expected_answer") or "",
                context=[c["text"] for c in item.get("expected_contexts") or []],
                retrieval_context=[h.chunk_text for h in result.hits],
                additional_metadata={
                    "id": item.get("id"),
                    "category": item.get("category"),
                    "expected_refs": item.get("expected_refs"),
                    "retrieved_refs": [ref for h in result.hits for ref in h.canon_refs],
                    "citations": result.citations,
                    "refused": result.refused,
                    "refusal_reason": result.refusal_reason,
                },
            )
        )

    evaluate(test_cases=cases, metrics=metrics)


if __name__ == "__main__":
    main()
