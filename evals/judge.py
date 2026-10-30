"""LLM-as-a-judge model for DeepEval metrics (Claude via Anthropic API).

Reads ANTHROPIC_API_KEY and EVAL_JUDGE_MODEL from .env.
Usage:
    from evals.judge import judge
    FaithfulnessMetric(model=judge(), threshold=0.7)
"""
import os

from deepeval.models import AnthropicModel
from dotenv import load_dotenv

load_dotenv()


def judge() -> AnthropicModel:
    return AnthropicModel(
        model=os.getenv("EVAL_JUDGE_MODEL", "claude-haiku-5-5"),
        temperature=0,
    )
