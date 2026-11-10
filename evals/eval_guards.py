"""Measure input-guard block rate and false-refusal rate. No LLM is used.

By default this prints a rules-only (before) table and a rules+bge-m3
(after) table on the same official splits, then a tune / held-out report
used to choose the similarity margins.

Usage:
    uv run python -m evals.eval_guards
    uv run python -m evals.eval_guards --rules-only
    uv run python -m evals.eval_guards --sample 200 --seed 2026
"""

from __future__ import annotations

import argparse
import json
import random
from collections import Counter
from pathlib import Path

from bible_rag.generation.guards import check_input
from bible_rag.generation.topic import (
    DEFAULT_ALLOW_MARGIN,
    DEFAULT_REFUSE_MARGIN,
    TopicChecker,
    reset_checker,
)

DATASETS = Path(__file__).resolve().parent / "datasets"
NORMAL_CATEGORIES_EXCLUDED = frozenset({"trap", "negative"})


def load_jsonl(path: Path) -> list[dict]:
    items = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                items.append(json.loads(line))
    return items


def load_all() -> list[dict]:
    items = []
    for name in ("golden_en.jsonl", "golden_zh.jsonl"):
        items.extend(load_jsonl(DATASETS / name))
    return items


def evaluate(items: list[dict], **kwargs) -> dict:
    blocked = 0
    reasons: Counter[str] = Counter()
    for item in items:
        decision = check_input(item["question"], **kwargs)
        if not decision.ok:
            blocked += 1
            reasons[decision.reason or "unknown"] += 1
    return {"n": len(items), "blocked": blocked, "reasons": reasons}


def sample_normal(items: list[dict], n: int, seed: int) -> list[dict]:
    pool = [it for it in items if it.get("category") not in NORMAL_CATEGORIES_EXCLUDED]
    rng = random.Random(seed)
    if n >= len(pool):
        return pool
    return rng.sample(pool, n)


def rate(blocked: int, n: int) -> float:
    return blocked / n if n else 0.0


def split_items(items: list[dict], seed: int, frac: float = 0.5) -> tuple[list[dict], list[dict]]:
    rng = random.Random(seed)
    shuffled = list(items)
    rng.shuffle(shuffled)
    cut = int(len(shuffled) * frac)
    return shuffled[:cut], shuffled[cut:]


def print_table(title: str, rows: list[tuple[str, dict, float, dict]], extra: str = "") -> None:
    print(title)
    if extra:
        print(extra)
    print(f"{'split':<22} {'n':>6} {'blocked':>8} {'rate':>8}  reasons")
    for label, stats, r, reasons in rows:
        print(f"{label:<22} {stats['n']:>6} {stats['blocked']:>8} {r:>7.1%}  {reasons}")
    print()


def table_for(
    groups: list[tuple[str, list[dict]]], **kwargs
) -> list[tuple[str, dict, float, dict]]:
    rows = []
    for label, group in groups:
        stats = evaluate(group, **kwargs)
        rows.append((label, stats, rate(stats["blocked"], stats["n"]), dict(stats["reasons"])))
    return rows


def show_false_refusals(normal: list[dict], **kwargs) -> None:
    blocked = [it for it in normal if not check_input(it["question"], **kwargs).ok]
    if not blocked:
        return
    print("false refusals (up to 8):")
    for it in blocked[:8]:
        d = check_input(it["question"], **kwargs)
        print(f"  {it['id']} [{d.reason}] {it['question']}")
    print()


def _load_semantic_checker() -> TopicChecker:
    # Force the real encoder on, even if the process inherited GUARD_SEMANTIC=0.
    import os

    os.environ["GUARD_SEMANTIC"] = "1"
    reset_checker()
    from bible_rag.generation.topic import BgeM3Embedder, allow_margin, refuse_margin

    print("loading bge-m3 for the semantic topic check...")
    return TopicChecker(BgeM3Embedder(), allow=allow_margin(), refuse=refuse_margin())


def _precompute(checker: TopicChecker, items: list[dict]) -> dict[str, tuple[float, float, float]]:
    """Encode every unique question once; return query -> (margin, sim_in, sim_out)."""
    unique = list(dict.fromkeys(it["question"] for it in items))
    from bible_rag.generation.topic import cosine, l2_normalize

    dense = checker.embedder.encode_dense(unique)
    scores = {}
    for text, raw in zip(unique, dense, strict=True):
        vec = l2_normalize(raw)
        sim_in = max(cosine(vec, p) for p in checker._in_vecs)
        sim_out = max(cosine(vec, p) for p in checker._out_vecs)
        scores[text] = (sim_in - sim_out, sim_in, sim_out)
    return scores


# The line above with _l2 is sloppy - let me not include that placeholder.
# I'll rewrite _precompute cleanly in a fix if needed.


def policy(rules_ok: bool, hard: bool, margin: float, allow: float, refuse: float) -> bool:
    """Return True if the combined policy allows the question."""
    if hard and not rules_ok:
        return False
    if margin >= allow:
        return True
    if margin <= refuse:
        return False
    return rules_ok


def is_hard_refusal(question: str) -> bool:
    """True when rules refuse for a reason the semantic layer must not override.

    Injection, length, and other-canon are hard. A cue-less off-topic refusal
    is not hard (the semantic layer may still allow a clearly in-domain query).
    """
    from bible_rag.generation.guards import (
        _BIBLE_OR_QURAN,
        _INJECTION,
        _OTHER_CANON,
        MAX_QUERY_LEN,
    )

    stripped = question.strip()
    if not stripped or len(stripped) > MAX_QUERY_LEN:
        return True
    if _INJECTION.search(stripped):
        return True
    return bool(_OTHER_CANON.search(stripped) and not _BIBLE_OR_QURAN.search(stripped))


def sweep_thresholds(
    items: list[dict],
    scores: dict[str, tuple[float, float, float]],
    allow_grid: list[float],
    refuse_grid: list[float],
    max_false_rate: float,
    max_trap_rate: float,
) -> tuple[float, float, dict]:
    """Pick margins on the tune set: maximize negative block rate under budgets."""
    best = None
    for allow in allow_grid:
        for refuse in refuse_grid:
            if refuse >= allow:
                continue
            stats = _split_stats(items, scores, allow, refuse)
            if stats["false_rate"] > max_false_rate:
                continue
            if stats["trap_rate"] > max_trap_rate:
                continue
            key = (stats["neg_rate"], -stats["false_rate"], -stats["trap_rate"], allow, refuse)
            if best is None or key > best[0]:
                best = (key, allow, refuse, stats)
    if best is None:
        return DEFAULT_ALLOW_MARGIN, DEFAULT_REFUSE_MARGIN, {}
    return best[1], best[2], best[3]


def _split_stats(items, scores, allow, refuse) -> dict:
    groups = {"negative": [0, 0], "trap": [0, 0], "normal": [0, 0]}
    for it in items:
        cat = it.get("category")
        bucket = "normal"
        if cat == "negative":
            bucket = "negative"
        elif cat == "trap":
            bucket = "trap"
        q = it["question"]
        margin = scores[q][0]
        rules_ok = check_input(q, use_semantic=False).ok
        hard = is_hard_refusal(q)
        allowed = policy(rules_ok, hard, margin, allow, refuse)
        groups[bucket][0] += 1
        if not allowed:
            groups[bucket][1] += 1
    return {
        "neg_n": groups["negative"][0],
        "neg_blocked": groups["negative"][1],
        "neg_rate": rate(groups["negative"][1], groups["negative"][0]),
        "trap_n": groups["trap"][0],
        "trap_blocked": groups["trap"][1],
        "trap_rate": rate(groups["trap"][1], groups["trap"][0]),
        "false_n": groups["normal"][0],
        "false_blocked": groups["normal"][1],
        "false_rate": rate(groups["normal"][1], groups["normal"][0]),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--sample", type=int, default=200, help="normal items to sample for false refusals"
    )
    ap.add_argument("--seed", type=int, default=2026)
    ap.add_argument("--rules-only", action="store_true", help="skip the bge-m3 topic layer")
    args = ap.parse_args()

    all_items = load_all()
    trap = [it for it in all_items if it.get("category") == "trap"]
    negative = [it for it in all_items if it.get("category") == "negative"]
    targeted = trap + negative
    normal = sample_normal(all_items, args.sample, args.seed)
    official = [
        ("trap", trap),
        ("negative", negative),
        ("trap+negative", targeted),
        ("normal_sample", normal),
    ]

    before = table_for(official, use_semantic=False)
    print_table(
        "input guard eval  (rules only, before)",
        before,
        extra=f"sample_seed={args.seed}  normal_sample={len(normal)}",
    )
    trap_neg = evaluate(targeted, use_semantic=False)
    false = evaluate(normal, use_semantic=False)
    print(
        f"block rate (trap+negative): {rate(trap_neg['blocked'], trap_neg['n']):.3%}  "
        f"({trap_neg['blocked']}/{trap_neg['n']})"
    )
    print(
        f"false-refusal rate (normal sample): {rate(false['blocked'], false['n']):.3%}  "
        f"({false['blocked']}/{false['n']})"
    )
    print()
    show_false_refusals(normal, use_semantic=False)

    if args.rules_only:
        return

    checker = _load_semantic_checker()
    after_kw = {"checker": checker, "use_semantic": True}
    after = table_for(official, **after_kw)
    print_table(
        "input guard eval  (rules + bge-m3, after)",
        after,
        extra=(
            f"sample_seed={args.seed}  normal_sample={len(normal)}  "
            f"allow_margin={checker.allow}  refuse_margin={checker.refuse}"
        ),
    )
    trap_neg_a = evaluate(targeted, **after_kw)
    false_a = evaluate(normal, **after_kw)
    print(
        f"block rate (trap+negative): {rate(trap_neg_a['blocked'], trap_neg_a['n']):.3%}  "
        f"({trap_neg_a['blocked']}/{trap_neg_a['n']})"
    )
    print(
        f"false-refusal rate (normal sample): {rate(false_a['blocked'], false_a['n']):.3%}  "
        f"({false_a['blocked']}/{false_a['n']})"
    )
    print()
    show_false_refusals(normal, **after_kw)

    # Tune / held-out: half of each official group, same seed as the 200-sample.
    neg_tune, neg_hold = split_items(negative, args.seed)
    trap_tune, trap_hold = split_items(trap, args.seed)
    nor_tune, nor_hold = split_items(normal, args.seed)
    tune_items = neg_tune + trap_tune + nor_tune
    hold_items = neg_hold + trap_hold + nor_hold
    print("encoding questions for the threshold sweep...")
    scores = _precompute(checker, all_items)

    shipped_tune = _split_stats(tune_items, scores, checker.allow, checker.refuse)
    shipped_hold = _split_stats(hold_items, scores, checker.allow, checker.refuse)
    print(
        f"shipped margins (allow_margin={checker.allow}, refuse_margin={checker.refuse}) "
        "on the tune/held-out split:"
    )
    for label, stats in (("tune", shipped_tune), ("held-out", shipped_hold)):
        print(
            f"  {label:<8} "
            f"negative {stats['neg_blocked']}/{stats['neg_n']} ({stats['neg_rate']:.1%})  "
            f"trap {stats['trap_blocked']}/{stats['trap_n']} ({stats['trap_rate']:.1%})  "
            f"false-refusal {stats['false_blocked']}/{stats['false_n']} ({stats['false_rate']:.1%})"
        )

    allow_grid = [round(x * 0.01, 2) for x in range(21)]  # 0.00 .. 0.20
    refuse_grid = [round(x * 0.01, 2) for x in range(-15, 5)]  # -0.15 .. 0.04
    # Budgets vs the rules-only baseline on the tune set: do not raise the
    # normal false-refusal rate above 2%, or the trap block rate above 8%.
    allow, refuse, tune_stats = sweep_thresholds(
        tune_items,
        scores,
        allow_grid,
        refuse_grid,
        max_false_rate=0.02,
        max_trap_rate=0.08,
    )
    hold_stats = _split_stats(hold_items, scores, allow, refuse)
    print(f"sweep suggestion on the tune split: allow_margin={allow}  refuse_margin={refuse}")
    if tune_stats:
        print(
            "  tune     "
            f"negative {tune_stats['neg_blocked']}/{tune_stats['neg_n']} "
            f"({tune_stats['neg_rate']:.1%})  "
            f"trap {tune_stats['trap_blocked']}/{tune_stats['trap_n']} "
            f"({tune_stats['trap_rate']:.1%})  "
            f"false-refusal {tune_stats['false_blocked']}/{tune_stats['false_n']} "
            f"({tune_stats['false_rate']:.1%})"
        )
    print(
        "  held-out "
        f"negative {hold_stats['neg_blocked']}/{hold_stats['neg_n']} "
        f"({hold_stats['neg_rate']:.1%})  "
        f"trap {hold_stats['trap_blocked']}/{hold_stats['trap_n']} "
        f"({hold_stats['trap_rate']:.1%})  "
        f"false-refusal {hold_stats['false_blocked']}/{hold_stats['false_n']} "
        f"({hold_stats['false_rate']:.1%})"
    )
    print()
    print("Note: /answer uses the shipped margins above, not the sweep suggestion.")


if __name__ == "__main__":
    main()
