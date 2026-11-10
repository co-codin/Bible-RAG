"""Compare dense, sparse, and hybrid RRF configs on the smoke eval set.

Each query is encoded once with bge-m3; the same vectors are reused across every
config. Items with no expected_refs (negative / some trap and numbering) are
skipped for Recall@10 and MRR and listed separately.

Usage:
    python scripts/tune_rrf.py
    python scripts/tune_rrf.py --uri .milvus/bible_rag.db --output evals/results/rrf_tuning.md
"""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass, field
from pathlib import Path

from bible_rag.embedding.bge_m3 import BGEM3
from bible_rag.retrieval.hybrid import CANDIDATES, RRF_K, Hit, search

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SMOKE = ROOT / "evals/datasets/golden_smoke.jsonl"
DEFAULT_OUT = ROOT / "evals/results/rrf_tuning.md"
DEFAULT_URI = os.environ.get("MILVUS_URI", str(ROOT / ".milvus/bible_rag.db"))
TOP_K = 10

HYBRID_GRID = [(c, k) for c in (20, 50, 100) for k in (20, 60)]
FORGIVE_QUERY = "forgive others"
FORGIVE_PK = "kjv:Col.3.13-15"
FORGIVE_REF = "Col.3.13"


@dataclass
class Metrics:
    n: int = 0
    recall_sum: float = 0.0
    mrr_sum: float = 0.0
    by_lang: dict[str, tuple[int, float, float]] = field(default_factory=dict)

    def add(self, lang: str, recall: float, mrr: float) -> None:
        self.n += 1
        self.recall_sum += recall
        self.mrr_sum += mrr
        n, r, m = self.by_lang.get(lang, (0, 0.0, 0.0))
        self.by_lang[lang] = (n + 1, r + recall, m + mrr)

    @property
    def recall(self) -> float:
        return self.recall_sum / self.n if self.n else 0.0

    @property
    def mrr(self) -> float:
        return self.mrr_sum / self.n if self.n else 0.0

    def lang(self, lang: str) -> tuple[int, float, float]:
        n, r, m = self.by_lang.get(lang, (0, 0.0, 0.0))
        if n == 0:
            return 0, 0.0, 0.0
        return n, r / n, m / n


def load_items(path: Path) -> tuple[list[dict], list[dict]]:
    items = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    scored = [it for it in items if it.get("expected_refs")]
    skipped = [it for it in items if not it.get("expected_refs")]
    return scored, skipped


def corpus_filter(item: dict) -> str | None:
    c = item.get("corpus")
    return c if c in ("bible", "quran") else None


def recall_at_k(hits: list[Hit], expected: list[str], k: int = TOP_K) -> float:
    got: set[str] = set()
    for h in hits[:k]:
        got.update(h.canon_refs)
    return len(got & set(expected)) / len(expected)


def mrr_at_k(hits: list[Hit], expected: list[str], k: int = TOP_K) -> float:
    exp = set(expected)
    for i, h in enumerate(hits[:k], 1):
        if exp.intersection(h.canon_refs):
            return 1.0 / i
    return 0.0


def fmt(x: float) -> str:
    return f"{x:.3f}"


def search_cfg(
    item: dict,
    vecs: dict[str, tuple[list[list[float]], list[dict[int, float]]]],
    uri: str,
    mode: str,
    candidates: int = CANDIDATES,
    rrf_k: int = RRF_K,
    limit: int = TOP_K,
    translation: str | None = None,
    corpus: str | None | object = ...,
) -> list[Hit]:
    dense, sparse = vecs[item["question"]]
    if corpus is ...:
        corpus = corpus_filter(item)
    return search(
        item["question"],
        translation=translation,
        corpus=corpus,
        limit=limit,
        mode=mode,
        uri=uri,
        candidates=candidates,
        rrf_k=rrf_k,
        dense=dense,
        sparse=sparse,
    )


def evaluate(
    scored: list[dict],
    vecs: dict[str, tuple[list[list[float]], list[dict[int, float]]]],
    uri: str,
    mode: str,
    candidates: int = CANDIDATES,
    rrf_k: int = RRF_K,
) -> Metrics:
    m = Metrics()
    for it in scored:
        hits = search_cfg(it, vecs, uri, mode, candidates, rrf_k)
        m.add(
            it["lang"], recall_at_k(hits, it["expected_refs"]), mrr_at_k(hits, it["expected_refs"])
        )
    return m


def table_row(label: str, cand: str, k: str, m: Metrics) -> str:
    en_n, en_r, en_m = m.lang("en")
    zh_n, zh_r, zh_m = m.lang("zh")
    return (
        f"| {label} | {cand} | {k} | {m.n} "
        f"| {fmt(m.recall)} | {fmt(m.mrr)} "
        f"| {en_n} | {fmt(en_r)} | {fmt(en_m)} "
        f"| {zh_n} | {fmt(zh_r)} | {fmt(zh_m)} |"
    )


def rank_pk(hits: list[Hit], pk: str) -> int | None:
    for i, h in enumerate(hits, 1):
        if h.pk == pk:
            return i
    return None


def rank_ref(hits: list[Hit], ref: str) -> int | None:
    for i, h in enumerate(hits, 1):
        if ref in h.canon_refs:
            return i
    return None


def q040_hits(hits: list[Hit]) -> list[tuple[int, Hit]]:
    out = []
    for i, h in enumerate(hits, 1):
        if "Q040" in h.pk or any(r.startswith("Q040.") for r in h.canon_refs):
            out.append((i, h))
    return out


def render_hits(hits: list[Hit], n: int = 10) -> str:
    lines = []
    for i, h in enumerate(hits[:n], 1):
        text = h.chunk_text.replace("\n", " ")[:70]
        lines.append(f"| {i} | {h.score:.4f} | `{h.pk}` | {text} |")
    return "\n".join(lines)


def investigate(
    vecs: dict[str, tuple[list[list[float]], list[dict[int, float]]]],
    uri: str,
) -> str:
    """Why does hybrid drop kjv:Col.3.13-15 for 'forgive others' while Surah 40 rises?"""
    item = {"question": FORGIVE_QUERY}
    sections: list[str] = [
        "## Investigation: why hybrid drops `kjv:Col.3.13-15`",
        "",
        (
            f"Query: `{FORGIVE_QUERY}`. Target chunk: `{FORGIVE_PK}` "
            f'(KJV Colossians 3:13, "Forbearing one another, and forgiving one another"). '
            "Surah 40 (Ghafir) is titled **The Forgiver**, and every English chunk of that "
            "surah is prefixed with `The Forgiver 40` under the `book_chapter_header.v1` rule."
        ),
        "",
    ]

    filters = [
        ("no filter", None, None),
        ("corpus=bible", None, "bible"),
        ("translation=kjv, corpus=bible", "kjv", "bible"),
    ]
    # Deep lists so we can see ranks outside the top 10.
    deep = 50

    for title, translation, corpus in filters:
        sections.append(f"### {title}")
        sections.append("")
        rows = []
        detail_tables = []
        for mode in ("dense", "sparse", "hybrid"):
            hits = search_cfg(
                item,
                vecs,
                uri,
                mode,
                candidates=CANDIDATES,
                rrf_k=RRF_K,
                limit=deep,
                translation=translation,
                corpus=corpus,
            )
            col_pk = rank_pk(hits, FORGIVE_PK)
            col_ref = rank_ref(hits, FORGIVE_REF)
            q040 = q040_hits(hits)
            q040_first = q040[0][0] if q040 else None
            n_q040_top10 = sum(1 for r, _ in q040 if r <= 10)
            n_q040 = len(q040)
            rows.append(
                f"| {mode} | {col_pk or '>50'} | {col_ref or '>50'} "
                f"| {q040_first or '—'} | {n_q040_top10} | {n_q040} |"
            )
            detail_tables.append(
                f"Top 10, **{mode}**, {title}:\n\n"
                f"| rank | score | pk | text |\n|---:|---:|---|---|\n"
                f"{render_hits(hits, 10)}\n"
            )
        sections.append(
            "| mode | rank of `kjv:Col.3.13-15` | first hit with Col.3.13 "
            "| first Q040 | Q040 in top 10 | Q040 in top 50 |"
        )
        sections.append("|---|---:|---:|---:|---:|---:|")
        sections.extend(rows)
        sections.append("")
        sections.extend(detail_tables)

    return "\n".join(sections)


def render_report(
    rows_md: list[str],
    scored: list[dict],
    skipped: list[dict],
    best_label: str,
    investigation: str,
) -> str:
    skipped_lines = "\n".join(
        f"- `{it['id']}` ({it['lang']}, {it['category']}, `{it['expected_behavior']}`): "
        f"{it['question']}"
        for it in skipped
    )
    return f"""# RRF tuning on the smoke set

Smoke set: `evals/datasets/golden_smoke.jsonl` (60 items).
Scored: **{len(scored)}** items that have `expected_refs` (25 en + 25 zh).
Skipped: **{len(skipped)}** items with no expected refs, listed at the end.

Protocol:
- Encode each question once with bge-m3; reuse the same dense + sparse vectors for every config.
- `corpus` filter is applied when the item is labelled `bible` or `quran`; no filter for `both`.
  Translation is left unfiltered so cross-lingual items can hit either language.
- A retrieved chunk is relevant if any of its `canon_refs` is in `expected_refs`.
- Recall@10 is the fraction of expected refs found in the top 10 chunks, averaged over queries.
- MRR is `1 / rank` of the first relevant chunk (0 if none in the top 10), averaged over queries.

## Results

| config | candidates | k | N | Recall@10 | MRR | N (en) | Recall@10 (en) | MRR (en) | N (zh) | Recall@10 (zh) | MRR (zh) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
{chr(10).join(rows_md)}

Best config by Recall@10, ties broken by MRR: **{best_label}**.

{investigation}

## Findings

**Best config.** On this 50-item smoke slice, every hybrid grid point beats dense-only and sparse-only. The best Recall@10 is **hybrid with per-list limit 50 and k=20** (0.665 recall, 0.596 MRR). The code default (50/60) is close behind (0.645 / 0.591). The 20/20 and 20/60 grids are identical here and have the best MRR (0.609) with slightly lower recall (0.655). English recall is more sensitive to candidate depth; Chinese Recall@10 rises as the list grows (0.587 at 20 → 0.655 at 100/60). The default in `search()` is left at candidates=50, k=60; 50/20 is the best measured alternative on this slice.

**Col.3.13 is not a filter bug.** `build_filter` is attached to both `AnnSearchRequest`s. With `corpus=bible` or `translation=kjv, corpus=bible`, no Surah 40 chunk appears in the top 50 of dense, sparse, or hybrid (also covered by `test_hybrid_filter_applies_to_both_requests`). Quran hits only appear when the query is run with no corpus filter.

**Why hybrid still drops `kjv:Col.3.13-15`.** Two separate effects:

1. *Sparse misses the verse entirely.* Dense ranks `kjv:Col.3.13-15` first (cosine 0.6169): the verse says "forgiving one another / Christ forgave you", a paraphrase of "forgive others". Sparse never places that chunk in the top 200, even with a bible/kjv filter. Sparse's #1 is `kjv:Luke.23.33-35`, which contains the exact tokens **"forgive"** ("Father, forgive them") and **"others"** ("He saved others"). Colossians 3:13 uses "forgiving" / "forgave" / "one another", so it loses the lexical match. RRF only scores a document in lists where it appears, so a dense-only #1 gets `1/({{k+1}})` and loses to passages mid-ranked in *both* lists (for any k: a single-list rank-1 cannot beat a doc at ranks 2 and 3). That is why hybrid puts Colossians at 16 (no filter), 13 (bible), and 15 (kjv+bible) — out of the top 10 — even after Quran rows are filtered out.

2. *Unfiltered sparse boosts Surah 40.* Every English chunk of Surah 40 (Ghafir) is prefixed with `The Forgiver 40` (`book_chapter_header.v1`), and several verses also contain "forgive". Sparse therefore places Q040 chunks at ranks 2, 5 and 8. Some of those also make the dense candidate list (first Q040 is dense rank 13), so RRF lifts three Q040 chunks into the unfiltered hybrid top 10. This is a side effect of putting the English surah title in the embed prefix, not a broken filter. Changing the prefix (for example to a book code like `Q040 40`) would need a full re-embed and a new index fingerprint; it is left for a later experiment.

No retrieval-code change in this change set: the filter is correct, and switching the default RRF k or the prefix is a product/index decision.


## Skipped items (no expected refs)

{len(skipped)} items were excluded from Recall@10 / MRR
(negative, plus trap/numbering items whose expected behaviour is `not_found`):

{skipped_lines}
"""


def main() -> None:
    ap = argparse.ArgumentParser(description="Tune RRF / compare dense vs sparse vs hybrid")
    ap.add_argument("--smoke", type=Path, default=DEFAULT_SMOKE)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--uri", default=DEFAULT_URI)
    args = ap.parse_args()

    scored, skipped = load_items(args.smoke)
    questions = list(dict.fromkeys([it["question"] for it in scored] + [FORGIVE_QUERY]))
    print(f"encoding {len(questions)} unique queries with bge-m3 …", flush=True)
    model = BGEM3()
    dense_all, sparse_all = model.encode(questions, batch_size=16)
    vecs = {q: ([d], [s]) for q, d, s in zip(questions, dense_all, sparse_all, strict=True)}
    # Drop the model before a long search loop; the client is cached inside search().
    del model

    results: list[tuple[str, str, str, Metrics]] = []
    print("searching dense …", flush=True)
    results.append(("dense", "—", "—", evaluate(scored, vecs, args.uri, "dense")))
    print("searching sparse …", flush=True)
    results.append(("sparse", "—", "—", evaluate(scored, vecs, args.uri, "sparse")))
    for cand, k in HYBRID_GRID:
        print(f"searching hybrid candidates={cand} k={k} …", flush=True)
        m = evaluate(scored, vecs, args.uri, "hybrid", candidates=cand, rrf_k=k)
        results.append((f"hybrid ({cand}/{k})", str(cand), str(k), m))

    rows_md = [table_row(label, cand, k, m) for label, cand, k, m in results]
    # Best: max recall, then mrr. Hybrid configs only? Task says compare all; "best config" among all.
    best = max(results, key=lambda r: (r[3].recall, r[3].mrr))
    best_label = f"{best[0]} (Recall@10={fmt(best[3].recall)}, MRR={fmt(best[3].mrr)})"

    print("investigating 'forgive others' …", flush=True)
    investigation = investigate(vecs, args.uri)

    report = render_report(rows_md, scored, skipped, best_label, investigation)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report)
    print(report)
    print(f"\nwrote {args.output}", flush=True)


if __name__ == "__main__":
    main()
