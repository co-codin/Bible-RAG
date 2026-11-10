"""Measure input-guard block rate and false-refusal rate. No LLM is used.

Usage:
    uv run python -m evals.eval_guards
    uv run python -m evals.eval_guards --sample 100 --seed 2026
"""

from __future__ import annotations

import argparse
import json
import random
from collections import Counter
from pathlib import Path

from bible_rag.generation.guards import check_input

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


def evaluate(items: list[dict]) -> dict[str, int]:
    blocked = 0
    reasons: Counter[str] = Counter()
    for item in items:
        decision = check_input(item["question"])
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


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--sample", type=int, default=200, help="normal items to sample for false refusals"
    )
    ap.add_argument("--seed", type=int, default=2026)
    args = ap.parse_args()

    all_items = load_all()
    trap = [it for it in all_items if it.get("category") == "trap"]
    negative = [it for it in all_items if it.get("category") == "negative"]
    targeted = trap + negative
    normal = sample_normal(all_items, args.sample, args.seed)

    print(f"input guard eval  sample_seed={args.seed}  normal_sample={len(normal)}")
    print(f"{'split':<22} {'n':>6} {'blocked':>8} {'rate':>8}  reasons")
    rows = []
    for label, group in (
        ("trap", trap),
        ("negative", negative),
        ("trap+negative", targeted),
        ("normal_sample", normal),
    ):
        stats = evaluate(group)
        r = rate(stats["blocked"], stats["n"])
        reasons = dict(stats["reasons"])
        print(f"{label:<22} {stats['n']:>6} {stats['blocked']:>8} {r:>7.1%}  {reasons}")
        rows.append((label, stats, r, reasons))

    trap_neg = evaluate(targeted)
    false = evaluate(normal)
    print()
    print(
        f"block rate (trap+negative): {rate(trap_neg['blocked'], trap_neg['n']):.3%}  "
        f"({trap_neg['blocked']}/{trap_neg['n']})"
    )
    print(
        f"false-refusal rate (normal sample): {rate(false['blocked'], false['n']):.3%}  "
        f"({false['blocked']}/{false['n']})"
    )

    # Show up to 8 blocked normal questions, if any, so a false-refusal is inspectable.
    blocked_normal = [it for it in normal if not check_input(it["question"]).ok]
    if blocked_normal:
        print("\nfalse refusals (up to 8):")
        for it in blocked_normal[:8]:
            d = check_input(it["question"])
            print(f"  {it['id']} [{d.reason}] {it['question']}")

    # And a few blocked vs allowed negatives, for sanity.
    print("\nnegative examples:")
    shown = {"blocked": 0, "allowed": 0}
    for it in negative:
        d = check_input(it["question"])
        key = "blocked" if not d.ok else "allowed"
        if shown[key] >= 3:
            continue
        shown[key] += 1
        state = f"blocked:{d.reason}" if not d.ok else "allowed"
        print(f"  {it['id']} [{state}] {it['question']}")


if __name__ == "__main__":
    main()
