"""Unit tests for canon_ref parsing, JSONL verse lookup, and the CUV placeholder fix."""

import pytest

from bible_rag.retrieval.verses import (
    VerseNotFound,
    VerseRefError,
    cuv_placeholder_refs,
    display_verse_text,
    is_cuv_placeholder,
    lookup_verses,
    parse_ref,
)


def test_parse_bible_and_quran_refs():
    matt = parse_ref("Matt.6.14")
    assert matt.corpus == "bible" and matt.book_code == "Matt"
    assert matt.chapter == 6 and matt.verse_start == 14 and matt.canon_ref == "Matt.6.14"

    rng = parse_ref("John.3.16-18")
    assert rng.verse_start == 16 and rng.verse_end == 18
    assert rng.canon_ref == "John.3.16-18"
    assert rng.refs() == ["John.3.16", "John.3.17", "John.3.18"]

    # numbered book, case-insensitive
    chr19 = parse_ref("2chr.30.19")
    assert chr19.book_code == "2Chr" and chr19.canon_ref == "2Chr.30.19"

    q = parse_ref("Q2:255")
    assert q.corpus == "quran" and q.book_code == "Q002"
    assert q.chapter == 2 and q.verse_start == 255 and q.canon_ref == "Q002.2.255"

    qfull = parse_ref("Q002.2.255-257")
    assert qfull.refs() == ["Q002.2.255", "Q002.2.256", "Q002.2.257"]


def test_parse_rejects_invalid_refs():
    with pytest.raises(VerseRefError):
        parse_ref("")
    with pytest.raises(VerseRefError):
        parse_ref("not-a-ref")
    with pytest.raises(VerseRefError):
        parse_ref("Foo.1.1")
    with pytest.raises(VerseRefError):
        parse_ref("Matt.6.18-14")
    with pytest.raises(VerseRefError):
        parse_ref("Matt.0.1")
    with pytest.raises(VerseRefError):
        parse_ref("Q002.3.1")  # chapter must equal surah
    with pytest.raises(VerseRefError):
        parse_ref("Q200:1")
    with pytest.raises(VerseRefError):
        parse_ref("John.3.16-99")  # 84 verses, over MAX_RANGE=50


def test_lookup_john_316_both_translations():
    rec = lookup_verses("John.3.16")
    assert rec.corpus == "bible"
    assert rec.book_name["en"] == "John" or rec.book_name["en"].startswith("John")
    assert rec.book_name["zh"]
    assert rec.verse_start == rec.verse_end == 16
    assert len(rec.verses) == 1
    verse = rec.verses[0]
    assert verse.en and verse.en.translation == "kjv"
    assert "begotten Son" in verse.en.text
    assert verse.zh and verse.zh.translation == "cuv"
    assert "独生子" in verse.zh.text
    assert verse.zh.merged_with_previous is False


def test_lookup_quran_throne_verse():
    rec = lookup_verses("Q2:255")
    assert rec.corpus == "quran"
    assert rec.book_code == "Q002"
    assert rec.book_name["en"]
    assert rec.book_name["zh"]
    verse = rec.verses[0]
    assert verse.en and verse.en.translation == "quran_en"
    assert verse.zh and verse.zh.translation == "quran_zh"
    assert "Allah" in verse.en.text or "Allah" in verse.en.text.title()
    assert verse.zh.text  # Ma Jian is present


def test_lookup_range_and_missing():
    rec = lookup_verses("Matt.6.14-15")
    assert rec.canon_ref == "Matt.6.14-15"
    assert [v.verse for v in rec.verses] == [14, 15]
    assert rec.verses[0].en and "forgive" in rec.verses[0].en.text.lower()

    with pytest.raises(VerseNotFound):
        lookup_verses("Matt.99.1")
    with pytest.raises(VerseRefError):
        lookup_verses("Nope.1.1")


def test_cuv_placeholder_helpers():
    assert is_cuv_placeholder("a")
    assert is_cuv_placeholder(" a\n")
    assert not is_cuv_placeholder("爱")
    assert not is_cuv_placeholder("and the Lord")
    assert display_verse_text("a") == ""
    assert display_verse_text("a凡专心寻求神") == "凡专心寻求神"
    assert display_verse_text("凡专心寻求神") == "凡专心寻求神"


def test_cuv_2chr_30_19_is_merged_with_previous():
    rec = lookup_verses("2Chr.30.19")
    verse = rec.verses[0]
    assert verse.en and verse.en.text
    assert "prepareth his heart" in verse.en.text.lower() or "heart" in verse.en.text.lower()
    assert verse.zh is not None
    assert verse.zh.merged_with_previous is True
    assert verse.zh.note
    # Display shows the previous verse (30.18), not the raw placeholder "a".
    assert verse.zh.text != "a"
    assert "希西家" in verse.zh.text or "饶恕" in verse.zh.text or "寻求" in verse.zh.text


def test_cuv_placeholder_scan_includes_known_merged_verse():
    refs = cuv_placeholder_refs()
    assert "2Chr.30.19" in refs
    # These are merge stubs, not real one-letter verses.
    assert all(isinstance(r, str) and r.count(".") == 2 for r in refs)
    assert len(refs) >= 1
