"""Cheap semantic topic check for the input guard, using bge-m3 dense vectors.

The query is compared to a small set of in-domain and out-of-domain prototype
descriptions. The decision uses the margin ``max(sim_in) - max(sim_out)``:

* margin >= allow_margin  -> clearly in-domain
* margin <= refuse_margin -> clearly out-of-domain
* in between              -> ambiguous; the rule layer keeps its decision

No LLM is used. Prototypes stay general (kinds of questions, not the eval
items themselves) so thresholds can be tuned on a held-out split.
"""

from __future__ import annotations

import math
import os
from dataclasses import dataclass
from typing import Protocol

# Defaults chosen on a tune split of the golden set; see evals/eval_guards.py.
# Override with GUARD_TOPIC_ALLOW_MARGIN / GUARD_TOPIC_REFUSE_MARGIN if needed.
DEFAULT_ALLOW_MARGIN = 0.19
DEFAULT_REFUSE_MARGIN = -0.06

IN_DOMAIN_PROTOTYPES: tuple[str, ...] = (
    "A question about a teaching, commandment, parable, or story in the Bible.",
    "A question about a prophet, apostle, king, or other person in the Bible or the Quran.",
    "Looking up a Bible or Quran verse, quotation, chapter, or reference.",
    "A question about a teaching, story, or law in the Quran or a named surah.",
    "A question that retells a biblical or Quranic story in everyday words and asks where that warning or teaching is found.",
    "What does the Bible say about forgiveness, love, money, prayer, or marriage?",
    "What does the Quran say about patience, charity, justice, or faith?",
    "询问圣经或古兰经中的经文、教导、人物、故事或引用出处。",
    "用自己的话转述圣经或古兰经里的故事或教导，并询问这是哪一节。",
    "圣经里怎么讲爱、饶恕、金钱、祷告或婚姻？",
    "古兰经怎么讲坚忍、施舍、公正或信仰？",
)

OUT_DOMAIN_PROTOTYPES: tuple[str, ...] = (
    "What does the Bible say about a modern invention, modern technology, or a modern social practice that did not exist in the ancient world?",
    "Which Bible verse mentions a modern city, a modern country, a modern landmark, or a person from the last two thousand years?",
    "What does the Quran say about modern science, modern devices, digital technology, or the internet?",
    "Which surah mentions a modern city, a modern landmark, or a modern country?",
    "Does the Bible forbid a modern medical treatment, a modern product, or a modern lifestyle?",
    "A question about sports, cooking recipes, computer programming, or general trivia unrelated to scripture.",
    "圣经怎样谈论一种古代世界不存在的现代发明、现代科技或现代生活方式？",
    "哪节圣经提到一座现代城市、现代国家、现代地标，或近两千年来的历史人物？",
    "古兰经对现代科学、现代装置、数字技术或互联网怎么说？",
    "古兰经哪一章提到一座现代城市或现代地标？",
    "圣经是否禁止一种现代医疗或现代产品？",
    "与经文无关的体育、烹饪做法、编程或常识问题。",
)


class DenseEmbedder(Protocol):
    def encode_dense(self, texts: list[str]) -> list[list[float]]: ...


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    return float(raw)


def allow_margin() -> float:
    return _env_float("GUARD_TOPIC_ALLOW_MARGIN", DEFAULT_ALLOW_MARGIN)


def refuse_margin() -> float:
    return _env_float("GUARD_TOPIC_REFUSE_MARGIN", DEFAULT_REFUSE_MARGIN)


def semantic_enabled() -> bool:
    return os.environ.get("GUARD_SEMANTIC", "1").strip().lower() in {"1", "true", "yes", "on"}


def l2_normalize(vec: list[float]) -> list[float]:
    norm = math.sqrt(sum(x * x for x in vec))
    if norm == 0:
        return vec
    return [x / norm for x in vec]


def cosine(a: list[float], b: list[float]) -> float:
    # Vectors may already be normalized; we still guard against length mismatch.
    n = min(len(a), len(b))
    return sum(a[i] * b[i] for i in range(n))


@dataclass(frozen=True)
class TopicDecision:
    label: str  # "in" | "out" | "ambiguous"
    margin: float
    sim_in: float
    sim_out: float

    @property
    def clearly_in(self) -> bool:
        return self.label == "in"

    @property
    def clearly_out(self) -> bool:
        return self.label == "out"


class TopicChecker:
    def __init__(
        self,
        embedder: DenseEmbedder,
        *,
        in_prototypes: tuple[str, ...] = IN_DOMAIN_PROTOTYPES,
        out_prototypes: tuple[str, ...] = OUT_DOMAIN_PROTOTYPES,
        allow: float | None = None,
        refuse: float | None = None,
    ):
        self.embedder = embedder
        self.allow = DEFAULT_ALLOW_MARGIN if allow is None else allow
        self.refuse = DEFAULT_REFUSE_MARGIN if refuse is None else refuse
        if self.refuse >= self.allow:
            raise ValueError("refuse margin must be strictly less than allow margin")
        self._in_vecs = [l2_normalize(v) for v in embedder.encode_dense(list(in_prototypes))]
        self._out_vecs = [l2_normalize(v) for v in embedder.encode_dense(list(out_prototypes))]

    def score(self, query: str) -> tuple[float, float, float]:
        vec = l2_normalize(self.embedder.encode_dense([query])[0])
        sim_in = max(cosine(vec, p) for p in self._in_vecs)
        sim_out = max(cosine(vec, p) for p in self._out_vecs)
        return sim_in - sim_out, sim_in, sim_out

    def decide(
        self, query: str, *, allow: float | None = None, refuse: float | None = None
    ) -> TopicDecision:
        margin, sim_in, sim_out = self.score(query)
        high = self.allow if allow is None else allow
        low = self.refuse if refuse is None else refuse
        if margin >= high:
            label = "in"
        elif margin <= low:
            label = "out"
        else:
            label = "ambiguous"
        return TopicDecision(label=label, margin=margin, sim_in=sim_in, sim_out=sim_out)


class BgeM3Embedder:
    """Thin wrapper around the shared bge-m3 singleton."""

    def encode_dense(self, texts: list[str]) -> list[list[float]]:
        from bible_rag.embedding.bge_m3 import get_model

        return get_model().encode_dense(texts)


_checker: TopicChecker | None = None


def get_checker(embedder: DenseEmbedder | None = None) -> TopicChecker | None:
    """Return a process-wide checker, or None if semantic checks are disabled.

    Pass an embedder (in tests, a fake) to build a fresh checker that is not
    cached as the default.
    """
    if embedder is not None:
        return TopicChecker(
            embedder,
            allow=allow_margin(),
            refuse=refuse_margin(),
        )
    if not semantic_enabled():
        return None
    global _checker
    if _checker is None:
        _checker = TopicChecker(
            BgeM3Embedder(),
            allow=allow_margin(),
            refuse=refuse_margin(),
        )
    return _checker


def reset_checker() -> None:
    global _checker
    _checker = None
