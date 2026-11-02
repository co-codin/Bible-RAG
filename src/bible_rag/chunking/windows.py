"""Split verse JSONL files into retrieval chunks (child windows).

Each translation is chunked separately. Verses are grouped by chapter, then
cut into sliding windows of WINDOW verses that advance by STRIDE verses, so
neighbouring windows overlap by one verse and a sentence that runs across a
verse boundary is never cut in half.

    Matt.6 (34 verses) -> Matt.6.1-3, Matt.6.3-5, ..., Matt.6.31-33, Matt.6.32-34

The last window is pulled back so it always ends on the final verse (the tail
is never dropped). A chapter with <= WINDOW verses becomes a single chunk.

The chapter is the parent (`parent_key`, e.g. `cuv:Matt.6`): at answer time
we retrieve small children and can hand the whole chapter to the LLM.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from itertools import groupby
from pathlib import Path

from bible_rag.ingest.passages import SOURCES, canon_ref

WINDOW = 3
STRIDE = 2


@dataclass(frozen=True)
class Verse:
    book_code: str
    book_name: str
    chapter: int
    verse: int
    text: str


@dataclass
class Chunk:
    pk: str  # cuv:Matt.6.13-15
    corpus: str  # bible | quran
    translation: str  # kjv | cuv | quran_en | quran_zh
    parent_key: str  # cuv:Matt.6
    canon_refs: list[str]  # ["Matt.6.13", "Matt.6.14", "Matt.6.15"]
    context_prefix: str  # "Matthew 6" (LLM-written sentence in the contextual experiment)
    chunk_text: str
    meta: dict = field(default_factory=dict, compare=False)

    @property
    def embed_text(self) -> str:
        """What actually goes into bge-m3: header line + verses."""
        return (
            f"{self.context_prefix}\n{self.chunk_text}" if self.context_prefix else self.chunk_text
        )


def window_spans(n: int, window: int = WINDOW, stride: int = STRIDE) -> list[tuple[int, int]]:
    """Half-open [start, end) index spans covering n items.

    >>> window_spans(7)
    [(0, 3), (2, 5), (4, 7)]
    >>> window_spans(6)
    [(0, 3), (2, 5), (3, 6)]
    """
    if n <= 0:
        return []
    if n <= window:
        return [(0, n)]
    spans = [(s, s + window) for s in range(0, n - window + 1, stride)]
    if spans[-1][1] < n:  # tail not covered -> one more window ending on the last verse
        spans.append((n - window, n))
    return spans


def joiner(translation: str) -> str:
    # Chinese text has no spaces between sentences; English needs one.
    return "" if translation.endswith("zh") or translation == "cuv" else " "


def read_verses(path: Path) -> Iterator[Verse]:
    with path.open(encoding="utf-8") as f:
        for line in f:
            v = json.loads(line)
            text = v["text"].strip()
            if not text:  # CUV has a few empty / merged verses
                continue
            yield Verse(v["book_code"], v["book_name"], int(v["chapter"]), int(v["verse"]), text)


def chunk_chapter(verses: list[Verse], corpus: str, translation: str) -> list[Chunk]:
    verses = sorted(verses, key=lambda v: v.verse)
    if not verses:
        return []
    first = verses[0]
    parent = f"{translation}:{first.book_code}.{first.chapter}"
    prefix = f"{first.book_name} {first.chapter}"
    sep = joiner(translation)
    out = []
    for s, e in window_spans(len(verses)):
        win = verses[s:e]
        lo, hi = win[0].verse, win[-1].verse
        vrange = f"{lo}" if lo == hi else f"{lo}-{hi}"
        out.append(
            Chunk(
                pk=f"{parent}.{vrange}",
                corpus=corpus,
                translation=translation,
                parent_key=parent,
                canon_refs=[canon_ref(v.book_code, v.chapter, v.verse) for v in win],
                context_prefix=prefix,
                chunk_text=sep.join(v.text for v in win),
            )
        )
    return out


def chunk_verses(verses: Iterable[Verse], corpus: str, translation: str) -> Iterator[Chunk]:
    """Verses must arrive grouped by (book, chapter), as they are in the data files."""
    for _, group in groupby(verses, key=lambda v: (v.book_code, v.chapter)):
        yield from chunk_chapter(list(group), corpus, translation)


def chunk_translation(translation: str) -> Iterator[Chunk]:
    for path, corpus, code in SOURCES:
        if code == translation:
            yield from chunk_verses(read_verses(path), corpus, code)
            return
    raise ValueError(f"unknown translation {translation!r}; known: {[s[2] for s in SOURCES]}")
