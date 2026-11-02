"""Index versioning: a fingerprint of everything that determines the vectors in `chunks`.

The Milvus file is a build artifact (~an hour of CPU embedding), so we ship it
pre-built (`make fetch-index`) instead of rebuilding everywhere. That is only
safe if the index was built from the same inputs the code expects now:

    model name + pinned revision   -> different weights = incompatible vectors
    chunk params (window, stride)  -> different pks / chunk boundaries
    context_prefix rule id         -> different embedded text
    sha256 of every input corpus   -> fixed typo in a verse = stale chunk text

All of these go into one sha256 `fingerprint`. A full `ingest.chunks` run writes
`manifest.json` next to the db; the API calls `check()` at startup and refuses to
serve from an index whose fingerprint does not match the current code + data.

CLI:
    python -m bible_rag.index_manifest show
    python -m bible_rag.index_manifest check --uri ./.milvus/bible_rag.db
    python -m bible_rag.index_manifest write --uri ./.milvus/bible_rag.db
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from bible_rag.chunking.windows import CONTEXT_PREFIX_RULE, STRIDE, WINDOW
from bible_rag.embedding.bge_m3 import DENSE_DIM, MODEL_NAME, MODEL_REVISION
from bible_rag.ingest.passages import DATA, SOURCES

MANIFEST_NAME = "manifest.json"
SCHEMA_VERSION = 1  # bump if the manifest layout itself changes
DEFAULT_LOCAL_DIR = Path(".milvus")


class IndexMismatchError(RuntimeError):
    """The index on disk was built from different model / params / data than the code expects."""


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def build_params() -> dict:
    """Everything that changes the content of `chunks`, as plain JSON."""
    return {
        "model": {"name": MODEL_NAME, "revision": MODEL_REVISION, "dense_dim": DENSE_DIM},
        "chunking": {"window": WINDOW, "stride": STRIDE},
        "context_prefix_rule": CONTEXT_PREFIX_RULE,
        "corpora": {
            translation: {
                "file": str(path.relative_to(DATA.parent)),
                "sha256": sha256_file(path) if path.exists() else None,
            }
            for path, _corpus, translation in SOURCES
        },
    }


def fingerprint(params: dict | None = None) -> str:
    params = params if params is not None else build_params()
    blob = json.dumps(params, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(blob).hexdigest()


def manifest_path(uri: str) -> Path:
    """Milvus Lite: next to the .db file. Milvus server: ./.milvus/manifest.json."""
    if uri.endswith(".db"):
        return Path(uri).parent / MANIFEST_NAME
    return DEFAULT_LOCAL_DIR / MANIFEST_NAME


def write_manifest(uri: str, counts: dict[str, int]) -> Path:
    params = build_params()
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "fingerprint": fingerprint(params),
        "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "db_file": Path(uri).name if uri.endswith(".db") else None,
        "counts": counts,
        "total": sum(counts.values()),
        "dims": {"dense": DENSE_DIM, "sparse": "bge-m3 lexical weights (vocab ids)"},
        "params": params,
    }
    path = manifest_path(uri)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def load_manifest(uri: str) -> dict:
    path = manifest_path(uri)
    if not path.exists():
        raise IndexMismatchError(
            f"no {MANIFEST_NAME} at {path}; build the index (`make chunks`) or `make fetch-index`"
        )
    return json.loads(path.read_text(encoding="utf-8"))


def diff_params(expected: dict, actual: dict, prefix: str = "") -> list[str]:
    """Human-readable list of differing leaves, e.g. 'chunking.window: 3 != 2'."""
    out = []
    for key in sorted(set(expected) | set(actual)):
        e, a = expected.get(key), actual.get(key)
        name = f"{prefix}{key}"
        if isinstance(e, dict) and isinstance(a, dict):
            out += diff_params(e, a, name + ".")
        elif e != a:
            out.append(f"{name}: index={a!r} code={e!r}")
    return out


def check(uri: str) -> dict:
    """Call at API startup. Returns the manifest, raises IndexMismatchError on any mismatch."""
    manifest = load_manifest(uri)
    expected = build_params()
    want = fingerprint(expected)
    if manifest.get("fingerprint") != want:
        details = diff_params(expected, manifest.get("params", {})) or ["(params identical?)"]
        raise IndexMismatchError(
            f"index fingerprint {str(manifest.get('fingerprint'))[:12]} != expected {want[:12]}:\n  "
            + "\n  ".join(details)
            + "\nrebuild with `make chunks` or fetch a matching index"
        )
    return manifest


def count_chunks(uri: str, translations: list[str]) -> dict[str, int]:
    from pymilvus import MilvusClient

    from bible_rag.store.schema import CHUNKS

    client = MilvusClient(uri=uri)
    client.load_collection(CHUNKS)
    return {
        t: client.query(CHUNKS, filter=f'translation == "{t}"', output_fields=["count(*)"])[0][
            "count(*)"
        ]
        for t in translations
    }


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("cmd", choices=["show", "check", "write"])
    ap.add_argument("--uri", default="./.milvus/bible_rag.db")
    a = ap.parse_args()
    if a.cmd == "show":
        print(json.dumps({"fingerprint": fingerprint(), "params": build_params()}, indent=2))
    elif a.cmd == "write":
        counts = count_chunks(a.uri, [t for _, _, t in SOURCES])
        print(f"wrote {write_manifest(a.uri, counts)}: {counts}")
    else:
        try:
            m = check(a.uri)
        except IndexMismatchError as e:
            sys.exit(f"MISMATCH: {e}")
        print(f"OK {m['fingerprint'][:12]} built {m['created_at']} total={m['total']}")


if __name__ == "__main__":
    main()
