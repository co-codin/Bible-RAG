"""Load verse JSONL files into the Milvus `passages` collection.

Usage:
    python -m bible_rag.ingest.passages            # phase 1: EN + ZH
    python -m bible_rag.ingest.passages --drop     # recreate collections first
"""
from __future__ import annotations

import argparse
import json
from collections.abc import Iterator
from pathlib import Path

from pymilvus import MilvusClient

from bible_rag.store.schema import PASSAGES, init

DATA = Path(__file__).resolve().parents[3] / "data"

# Phase 1 sources: (file, corpus, translation code stored in Milvus)
SOURCES = [
    (DATA / "bible" / "kjv.jsonl", "bible", "kjv"),
    (DATA / "bible" / "cuv.jsonl", "bible", "cuv"),
    (DATA / "quran" / "quran_en.jsonl", "quran", "quran_en"),
    (DATA / "quran" / "quran_zh.jsonl", "quran", "quran_zh"),
]

BATCH = 2000
PLACEHOLDER = [0.0, 0.0]


def canon_ref(book_code: str, chapter: int, verse: int) -> str:
    # EN and ZH share KJV numbering, so native ref == canon ref in phase 1.
    # Russian (LXX Psalms) will need a verse_map lookup here later.
    return f"{book_code}.{chapter}.{verse}"


def read_rows(path: Path, corpus: str, translation: str) -> Iterator[dict]:
    with path.open(encoding="utf-8") as f:
        for line in f:
            v = json.loads(line)
            text = v["text"].strip()
            if not text:  # CUV has a few empty / merged verses
                continue
            ref = canon_ref(v["book_code"], v["chapter"], v["verse"])
            yield {
                "pk": f"{translation}:{ref}",
                "corpus": corpus,
                "translation": translation,
                "book_code": v["book_code"],
                "book_name": v["book_name"],
                "chapter": v["chapter"],
                "verse": v["verse"],
                "canon_ref": ref,
                "text": text,
                "_placeholder": PLACEHOLDER,
            }


def batched(rows: Iterator[dict], size: int) -> Iterator[list[dict]]:
    batch: list[dict] = []
    for r in rows:
        batch.append(r)
        if len(batch) == size:
            yield batch
            batch = []
    if batch:
        yield batch


def refs_of(path: Path) -> set[tuple[str, int, int]]:
    with path.open(encoding="utf-8") as f:
        return {(v["book_code"], v["chapter"], v["verse"]) for v in map(json.loads, f)}


def check_alignment() -> None:
    """Report KJV vs CUV verse refs that don't line up (31,102 vs 31,103)."""
    kjv = refs_of(DATA / "bible" / "kjv.jsonl")
    cuv = refs_of(DATA / "bible" / "cuv.jsonl")
    print(f"only in kjv: {sorted(kjv - cuv)}")
    print(f"only in cuv: {sorted(cuv - kjv)}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--uri", default="http://localhost:19530")
    ap.add_argument("--drop", action="store_true")
    args = ap.parse_args()

    init(args.uri, drop=args.drop)
    client = MilvusClient(uri=args.uri)

    check_alignment()
    for path, corpus, translation in SOURCES:
        n = 0
        for batch in batched(read_rows(path, corpus, translation), BATCH):
            client.upsert(PASSAGES, batch)  # upsert -> safe to re-run
            n += len(batch)
        print(f"{translation:9} {n:6} rows")

    client.flush(PASSAGES)
    print("total:", client.query(PASSAGES, filter="", output_fields=["count(*)"]))


if __name__ == "__main__":
    main()
