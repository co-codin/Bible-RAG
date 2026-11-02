from itertools import pairwise

from bible_rag.chunking.windows import Verse, chunk_chapter, chunk_verses, window_spans


def test_spans_short_chapters_are_one_chunk():
    assert window_spans(0) == []
    assert window_spans(1) == [(0, 1)]
    assert window_spans(3) == [(0, 3)]


def test_spans_odd_and_even():
    assert window_spans(5) == [(0, 3), (2, 5)]
    assert window_spans(7) == [(0, 3), (2, 5), (4, 7)]
    assert window_spans(4) == [(0, 3), (1, 4)]
    assert window_spans(6) == [(0, 3), (2, 5), (3, 6)]


def test_spans_cover_every_index_and_overlap():
    for n in range(1, 200):
        spans = window_spans(n)
        covered = {i for s, e in spans for i in range(s, e)}
        assert covered == set(range(n))
        assert spans[-1][1] == n
        assert all(e - s == min(3, n) for s, e in spans)
        for (_, e1), (s2, _) in pairwise(spans):
            assert s2 < e1  # neighbours overlap


def _ch(n, code="Matt", name="Matthew", ch=6):
    return [Verse(code, name, ch, i, f"v{i}.") for i in range(1, n + 1)]


def test_chunk_keys_and_text():
    chunks = chunk_chapter(_ch(5), "bible", "kjv")
    assert [c.pk for c in chunks] == ["kjv:Matt.6.1-3", "kjv:Matt.6.3-5"]
    c = chunks[1]
    assert c.parent_key == "kjv:Matt.6"
    assert c.canon_refs == ["Matt.6.3", "Matt.6.4", "Matt.6.5"]
    assert c.chunk_text == "v3. v4. v5."
    assert c.context_prefix == "Matthew 6"
    assert c.embed_text == "Matthew 6\nv3. v4. v5."


def test_chinese_joined_without_spaces():
    c = chunk_chapter(_ch(2, name="马太福音"), "bible", "cuv")[0]
    assert c.pk == "cuv:Matt.6.1-2"
    assert c.chunk_text == "v1.v2."


def test_single_verse_pk_and_skipped_verses():
    one = chunk_chapter([Verse("Q001", "The Opening", 1, 7, "x")], "quran", "quran_en")[0]
    assert one.pk == "quran_en:Q001.1.7"
    # a missing verse (e.g. 3John 1:15 absent in KJV) just shrinks the window, refs stay native
    vs = [v for v in _ch(5) if v.verse != 2]
    assert [c.canon_refs for c in chunk_chapter(vs, "bible", "kjv")] == [
        ["Matt.6.1", "Matt.6.3", "Matt.6.4"],
        ["Matt.6.3", "Matt.6.4", "Matt.6.5"],
    ]


def test_chunk_verses_groups_by_chapter():
    vs = _ch(4, ch=1) + _ch(2, ch=2)
    pks = [c.pk for c in chunk_verses(vs, "bible", "kjv")]
    assert pks == ["kjv:Matt.1.1-3", "kjv:Matt.1.2-4", "kjv:Matt.2.1-2"]
