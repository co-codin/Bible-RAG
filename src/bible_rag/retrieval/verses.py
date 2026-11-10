"""Look up a verse or verse range by canon_ref across translations.

Used by GET /verse for side-by-side comparison. Rows are read from the corpus
JSONL files; if the Milvus `passages` collection is present and non-empty it is
tried first, but the published Hugging Face index currently ships `chunks` only
(`passages` may have zero rows).

CUV source data uses a lone "a" as a placeholder when a verse was merged into
the previous verse (e.g. cuv:2Chr.30.19). The JSONL is left unchanged so the
index fingerprint stays valid; this module fixes the text at read/display time.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path

from bible_rag.ingest.passages import SOURCES
from bible_rag.ingest.passages import canon_ref as make_canon_ref
from bible_rag.store.schema import PASSAGES

REPO_ROOT = Path(__file__).resolve().parents[3]
DATA = REPO_ROOT / "data"
DEFAULT_URI = os.environ.get("MILVUS_URI", "./.milvus/bible_rag.db")

MAX_RANGE = 50

# CUV (and only CUV in this corpus) marks a verse merged into the previous one
# with a lone Latin "a". Also treat a stray leading "a" stuck to Chinese text.
_PLACEHOLDER = re.compile(r"^a$")
_LEADING_STRAY_A = re.compile(r"^a(?=[\u4e00-\u9fff])")

_BIBLE_REF = re.compile(r"^([1-3]?[A-Za-z][A-Za-z]+)\.(\d+)\.(\d+)(?:-(\d+))?$")
_QURAN_FULL = re.compile(r"^Q(\d{1,3})\.(\d+)\.(\d+)(?:-(\d+))?$", re.IGNORECASE)
_QURAN_SHORT = re.compile(r"^Q(\d{1,3})[:.](\d+)(?:-(\d+))?$", re.IGNORECASE)


class VerseRefError(ValueError):
    """The ref is syntactically invalid or names an unknown book / empty range."""


class VerseNotFound(LookupError):
    """The ref is valid but no verse in that range exists in the corpus."""


@dataclass(frozen=True)
class ParsedRef:
    corpus: str
    book_code: str
    chapter: int
    verse_start: int
    verse_end: int

    @property
    def canon_ref(self) -> str:
        if self.verse_start == self.verse_end:
            return make_canon_ref(self.book_code, self.chapter, self.verse_start)
        return f"{make_canon_ref(self.book_code, self.chapter, self.verse_start)}-{self.verse_end}"

    def refs(self) -> list[str]:
        return [
            make_canon_ref(self.book_code, self.chapter, v)
            for v in range(self.verse_start, self.verse_end + 1)
        ]


@dataclass(frozen=True)
class VerseRow:
    corpus: str
    translation: str
    book_code: str
    book_name: str
    chapter: int
    verse: int
    canon_ref: str
    text: str


@dataclass(frozen=True)
class VerseSide:
    translation: str
    text: str
    merged_with_previous: bool = False
    note: str | None = None


@dataclass(frozen=True)
class VerseItem:
    canon_ref: str
    verse: int
    en: VerseSide | None
    zh: VerseSide | None


@dataclass(frozen=True)
class VerseRecord:
    canon_ref: str
    corpus: str
    book_code: str
    chapter: int
    verse_start: int
    verse_end: int
    book_name: dict[str, str]
    verses: list[VerseItem] = field(default_factory=list)


# --- book metadata ----------------------------------------------------------


@cache
def _bible_books() -> dict[str, dict]:
    data = json.loads((DATA / "bible" / "books.json").read_text(encoding="utf-8"))
    return {entry["osis"]: entry for entry in data.values()}


@cache
def _osis_lookup() -> dict[str, str]:
    return {code.lower(): code for code in _bible_books()}


@cache
def _surahs() -> dict[int, dict]:
    rows = json.loads((DATA / "quran" / "surahs.json").read_text(encoding="utf-8"))
    return {int(entry["index"]): entry for entry in rows}


def book_names(book_code: str, corpus: str) -> dict[str, str]:
    if corpus == "quran":
        surah = int(book_code[1:])
        entry = _surahs()[surah]
        return {"en": entry["en"], "zh": entry["zh"]}
    entry = _bible_books()[book_code]
    return {"en": entry["en"], "zh": entry["zh"]}


# --- CUV placeholder --------------------------------------------------------


def is_cuv_placeholder(text: str) -> bool:
    return bool(_PLACEHOLDER.fullmatch(text.strip()))


def display_verse_text(text: str) -> str:
    """Strip CUV merge placeholders and a stray leading 'a' before Chinese text.

    Does not change the on-disk JSONL (that would invalidate the index fingerprint).
    """
    stripped = text.strip()
    if is_cuv_placeholder(stripped):
        return ""
    return _LEADING_STRAY_A.sub("", stripped)


def _merge_note(lang: str) -> str:
    if lang == "zh":
        return "和合本将本节经文并入上一节；此处显示上一节经文。"
    return "This verse is combined with the previous verse in the Chinese Union Version; the previous verse is shown."


# --- parsing ----------------------------------------------------------------


def parse_ref(raw: str) -> ParsedRef:
    value = (raw or "").strip()
    if not value:
        raise VerseRefError("canon_ref must not be empty")

    m = _QURAN_FULL.fullmatch(value) or _QURAN_SHORT.fullmatch(value)
    if m:
        surah = int(m.group(1))
        if surah < 1 or surah > 114:
            raise VerseRefError(f"unknown surah number {surah}")
        if _QURAN_FULL.fullmatch(value):
            chapter = int(m.group(2))
            start = int(m.group(3))
            end = int(m.group(4) or start)
            if chapter != surah:
                raise VerseRefError(
                    f"Quran chapter must equal the surah number; got Q{surah:03d}.{chapter}.{start}"
                )
        else:
            start = int(m.group(2))
            end = int(m.group(3) or start)
        _check_range(start, end)
        book = f"Q{surah:03d}"
        return ParsedRef("quran", book, surah, start, end)

    m = _BIBLE_REF.fullmatch(value)
    if not m:
        raise VerseRefError(f"invalid canon_ref: {raw!r}")
    osis = _osis_lookup().get(m.group(1).lower())
    if osis is None:
        raise VerseRefError(f"unknown book code: {m.group(1)}")
    chapter = int(m.group(2))
    start = int(m.group(3))
    end = int(m.group(4) or start)
    if chapter < 1:
        raise VerseRefError("chapter must be >= 1")
    _check_range(start, end)
    return ParsedRef("bible", osis, chapter, start, end)


def _check_range(start: int, end: int) -> None:
    if start < 1 or end < 1:
        raise VerseRefError("verse numbers must be >= 1")
    if end < start:
        raise VerseRefError("verse range end must be >= start")
    if end - start + 1 > MAX_RANGE:
        raise VerseRefError(f"verse range is longer than {MAX_RANGE} verses")


# --- corpus index -----------------------------------------------------------


def _row_from_json(obj: dict, corpus: str, translation: str) -> VerseRow | None:
    text = obj.get("text") or ""
    if not text.strip():
        return None
    chapter = int(obj["chapter"])
    verse = int(obj["verse"])
    book_code = obj["book_code"]
    return VerseRow(
        corpus=corpus,
        translation=translation,
        book_code=book_code,
        book_name=obj["book_name"],
        chapter=chapter,
        verse=verse,
        canon_ref=make_canon_ref(book_code, chapter, verse),
        text=text,
    )


@cache
def _jsonl_index() -> dict[str, list[VerseRow]]:
    index: dict[str, list[VerseRow]] = {}
    for path, corpus, translation in SOURCES:
        if not path.exists():
            continue
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue
                row = _row_from_json(json.loads(line), corpus, translation)
                if row is None:
                    continue
                index.setdefault(row.canon_ref, []).append(row)
    return index


def _milvus_rows(refs: list[str], uri: str) -> list[VerseRow] | None:
    """Return rows from Milvus, or None if the collection is missing/empty/unusable."""
    try:
        from pymilvus import MilvusClient
    except ImportError:
        return None
    try:
        client = MilvusClient(uri=uri)
        if not client.has_collection(PASSAGES):
            return None
        client.load_collection(PASSAGES)
        stats = client.get_collection_stats(PASSAGES)
        if int(stats.get("row_count") or 0) == 0:
            return None
        quoted = ", ".join(f'"{_escape(r)}"' for r in refs)
        fields = [
            "pk",
            "corpus",
            "translation",
            "book_code",
            "book_name",
            "chapter",
            "verse",
            "canon_ref",
            "text",
        ]
        hits = client.query(
            PASSAGES,
            filter=f"canon_ref in [{quoted}]",
            output_fields=fields,
            limit=max(len(refs) * 8, 16),
        )
        rows = []
        for h in hits:
            text = h.get("text") or ""
            if not text.strip():
                continue
            rows.append(
                VerseRow(
                    corpus=h["corpus"],
                    translation=h["translation"],
                    book_code=h["book_code"],
                    book_name=h["book_name"],
                    chapter=int(h["chapter"]),
                    verse=int(h["verse"]),
                    canon_ref=h["canon_ref"],
                    text=text,
                )
            )
        return rows
    except Exception:  # noqa: BLE001 — fall back to JSONL if the db is unusable
        return None


def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _rows_for(refs: list[str], uri: str) -> list[VerseRow]:
    milvus = _milvus_rows(refs, uri)
    if milvus is not None:
        return milvus
    index = _jsonl_index()
    rows: list[VerseRow] = []
    for ref in refs:
        rows.extend(index.get(ref, []))
    return rows


def _previous_cuv_text(parsed: ParsedRef, verse: int, uri: str) -> str | None:
    if verse <= 1:
        return None
    prev_ref = make_canon_ref(parsed.book_code, parsed.chapter, verse - 1)
    for row in _rows_for([prev_ref], uri):
        if row.translation == "cuv":
            text = display_verse_text(row.text)
            return text or None
    return None


def _side_for(row: VerseRow | None, parsed: ParsedRef, verse: int, uri: str) -> VerseSide | None:
    if row is None:
        return None
    if row.translation == "cuv" and is_cuv_placeholder(row.text.strip()):
        prev = _previous_cuv_text(parsed, verse, uri)
        lang = "zh"
        return VerseSide(
            translation=row.translation,
            text=prev or "",
            merged_with_previous=True,
            note=_merge_note(lang),
        )
    return VerseSide(translation=row.translation, text=display_verse_text(row.text))


def lookup_verses(raw: str, *, uri: str | None = None) -> VerseRecord:
    parsed = parse_ref(raw)
    uri = uri or DEFAULT_URI
    refs = parsed.refs()
    rows = _rows_for(refs, uri)
    by_ref: dict[str, dict[str, VerseRow]] = {ref: {} for ref in refs}
    for row in rows:
        if row.corpus != parsed.corpus:
            continue
        by_ref.setdefault(row.canon_ref, {})[row.translation] = row

    items: list[VerseItem] = []
    for ref in refs:
        bucket = by_ref.get(ref, {})
        if not bucket:
            continue
        any_row = next(iter(bucket.values()))
        en_row = next((bucket[t] for t in ("kjv", "quran_en") if t in bucket), None)
        zh_row = next((bucket[t] for t in ("cuv", "quran_zh") if t in bucket), None)
        items.append(
            VerseItem(
                canon_ref=ref,
                verse=any_row.verse,
                en=_side_for(en_row, parsed, any_row.verse, uri),
                zh=_side_for(zh_row, parsed, any_row.verse, uri),
            )
        )

    if not items:
        raise VerseNotFound(f"no verses found for {parsed.canon_ref}")

    return VerseRecord(
        canon_ref=parsed.canon_ref,
        corpus=parsed.corpus,
        book_code=parsed.book_code,
        chapter=parsed.chapter,
        verse_start=items[0].verse,
        verse_end=items[-1].verse,
        book_name=book_names(parsed.book_code, parsed.corpus),
        verses=items,
    )


def cuv_placeholder_refs() -> list[str]:
    """Canon refs in cuv.jsonl whose stored text is a lone 'a' (for tests/checks)."""
    refs = []
    path = DATA / "bible" / "cuv.jsonl"
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            obj = json.loads(line)
            if is_cuv_placeholder(obj.get("text") or ""):
                refs.append(make_canon_ref(obj["book_code"], obj["chapter"], obj["verse"]))
    return refs
