"""Chunk verses, embed them with bge-m3, and upsert into the Milvus `chunks` collection.

Usage:
    python -m bible_rag.ingest.chunks --uri ./.milvus/bible_rag.db
    python -m bible_rag.ingest.chunks --translations kjv,cuv --limit 500 --batch 32

Pipeline (three stages, two bounded queues):

    producer thread          main thread               writer thread
    chunk verses  --q_in-->  bge-m3 encode  --q_out--> upsert 512 rows / call
    (pure Python, fast)      (GPU/CPU bound, slow)     (disk I/O)

Why threads: the model forward pass releases the GIL inside torch, so chunking
and Milvus writes run *while* the model is busy instead of in between batches.
Why bounded queues: back-pressure. If embedding is the bottleneck (it is), the
producer blocks once `q_in` is full instead of chunking the whole Bible into
RAM; if writes stall, the embedder blocks on `q_out`.
The model lives on one thread only: one model copy, no GPU contention.

Re-running is safe: rows are upserted by pk, and pks already in the collection
are skipped (pass --force to re-embed them anyway).
"""

from __future__ import annotations

import argparse
import queue
import threading
import time
from collections.abc import Iterator

from pymilvus import MilvusClient
from tqdm import tqdm

from bible_rag.chunking.windows import Chunk, chunk_translation
from bible_rag.store.schema import CHUNKS, init

DEFAULT_TRANSLATIONS = ["kjv", "cuv", "quran_en", "quran_zh"]
WRITE_BATCH = 512
_DONE = object()  # sentinel that tells the next stage to stop


def existing_pks(client: MilvusClient, translation: str) -> set[str]:
    """pks of this translation already in Milvus (for resume)."""
    it = client.query_iterator(
        CHUNKS, batch_size=5000, filter=f'translation == "{translation}"', output_fields=["pk"]
    )
    pks: set[str] = set()
    while True:
        page = it.next()
        if not page:
            it.close()
            return pks
        pks.update(r["pk"] for r in page)


def to_row(c: Chunk, dense: list[float], sparse: dict[int, float]) -> dict:
    return {
        "pk": c.pk,
        "corpus": c.corpus,
        "translation": c.translation,
        "parent_key": c.parent_key,
        "canon_refs": c.canon_refs,
        "context_prefix": c.context_prefix,
        "chunk_text": c.chunk_text,
        "dense": dense,
        "sparse": sparse,
    }


def plan(translations: list[str], skip: set[str], limit: int | None) -> list[Chunk]:
    """All chunks still to embed. Chunking is cheap (~1 s), so we materialise the list to get
    an exact progress-bar total; the expensive tensors are still produced lazily below."""
    todo: list[Chunk] = []
    for t in translations:
        got = list(chunk_translation(t))
        if limit:  # first N chunks of the book order, so a smoke run is idempotent too
            got = got[:limit]
        todo.extend(c for c in got if c.pk not in skip)
    return todo


def batches(chunks: list[Chunk], size: int) -> Iterator[list[Chunk]]:
    for i in range(0, len(chunks), size):
        yield chunks[i : i + size]


def run(
    uri: str, translations: list[str], limit: int | None, batch: int, force: bool, contextual: bool
) -> None:
    t0 = time.perf_counter()
    init(uri)
    client = MilvusClient(uri=uri)
    client.load_collection(CHUNKS)  # a reopened collection starts 'released'; query needs it loaded

    skip: set[str] = set()
    if not force:
        for t in translations:
            have = existing_pks(client, t)
            skip |= have
            print(f"{t:9} already in Milvus: {len(have):6}")

    todo = plan(translations, skip, limit)
    if contextual:
        from bible_rag.chunking.contextual import add_context

        todo = add_context(todo)  # TODO: experiment, currently raises NotImplementedError
    print(f"to embed: {len(todo)} chunks (batch={batch})")
    if not todo:
        print(
            "nothing to embed; refresh the manifest with `python -m bible_rag.index_manifest write`"
        )
        return

    from bible_rag.embedding.bge_m3 import BGEM3  # heavy import, only when needed

    model = BGEM3()
    print(f"bge-m3 on {model.device}, load {time.perf_counter() - t0:.1f}s")

    q_in: queue.Queue = queue.Queue(maxsize=8)
    q_out: queue.Queue = queue.Queue(maxsize=8)
    errors: list[BaseException] = []
    written = {"n": 0}

    def producer() -> None:
        try:
            # Hand the model several mini-batches at once: FlagEmbedding sorts each call's
            # texts by length, so bigger calls mean less padding (faster, esp. on CPU).
            for b in batches(todo, batch * 8):
                q_in.put(b)
        finally:
            q_in.put(_DONE)

    def writer() -> None:
        buf: list[dict] = []
        try:
            while True:
                item = q_out.get()
                if item is not _DONE:
                    buf.extend(item)
                if len(buf) >= WRITE_BATCH or (item is _DONE and buf):
                    client.upsert(CHUNKS, buf)
                    written["n"] += len(buf)
                    buf = []
                if item is _DONE:
                    return
        except BaseException as e:  # noqa: BLE001 - surface any error in the main thread
            errors.append(e)
            while q_out.get() is not _DONE:  # drain so the embedder never blocks forever
                pass

    threads = [
        threading.Thread(target=producer, daemon=True),
        threading.Thread(target=writer, daemon=True),
    ]
    for th in threads:
        th.start()

    t_embed = time.perf_counter()
    bar = tqdm(total=len(todo), unit="chunk", mininterval=10)
    try:
        while (b := q_in.get()) is not _DONE:
            if errors:
                raise errors[0]
            dense, sparse = model.encode([c.embed_text for c in b], batch_size=batch)
            q_out.put([to_row(c, d, s) for c, d, s in zip(b, dense, sparse, strict=True)])
            bar.update(len(b))
    finally:
        q_out.put(_DONE)
        bar.close()
        for th in threads:
            th.join()
    if errors:
        raise errors[0]

    embed_s = time.perf_counter() - t_embed
    client.flush(CHUNKS)
    print(
        f"embedded+written {written['n']} chunks in {embed_s:.0f}s "
        f"({written['n'] / embed_s:.1f} chunks/s); total {time.perf_counter() - t0:.0f}s"
    )
    counts = {}
    for t in translations:
        n = client.query(CHUNKS, filter=f'translation == "{t}"', output_fields=["count(*)"])
        counts[t] = n[0]["count(*)"]
        print(f"{t:9} rows in chunks: {counts[t]}")

    # Only a complete build gets a manifest: a --limit / partial run must never look shippable.
    if limit is None and not contextual and set(translations) == set(DEFAULT_TRANSLATIONS):
        from bible_rag.index_manifest import write_manifest

        print(f"manifest: {write_manifest(uri, counts)}")


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--uri", default="http://localhost:19530")
    ap.add_argument("--translations", default=",".join(DEFAULT_TRANSLATIONS))
    ap.add_argument(
        "--limit", type=int, default=None, help="only the first N chunks per translation"
    )
    ap.add_argument("--batch", type=int, default=64, help="texts per model.encode call")
    ap.add_argument("--force", action="store_true", help="re-embed chunks already in Milvus")
    ap.add_argument(
        "--contextual", action="store_true", help="LLM context prefixes (TODO, not implemented yet)"
    )
    a = ap.parse_args()
    run(
        a.uri,
        [t.strip() for t in a.translations.split(",") if t.strip()],
        a.limit,
        a.batch,
        a.force,
        a.contextual,
    )


if __name__ == "__main__":
    main()
