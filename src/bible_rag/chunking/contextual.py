"""Contextual retrieval prefixes (experiment, not implemented yet).

Plan: one DeepSeek call per chapter. Send the whole chapter plus the list of
child windows, ask for a JSON object {pk: one-sentence context}. Cache results
in data/cache/context/<translation>.jsonl so runs are resumable. The sentence
replaces the plain "<book> <chapter>" header in Chunk.context_prefix, and the
evals compare retrieval with vs. without it.
"""

from __future__ import annotations

from bible_rag.chunking.windows import Chunk


def add_context(chunks: list[Chunk]) -> list[Chunk]:
    # TODO: implement the per-chapter DeepSeek call + cache described above.
    raise NotImplementedError(
        "contextual prefixes are a later experiment; run without --contextual"
    )
