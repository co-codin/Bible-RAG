# Bible-RAG golden evaluation datasets

Golden question/answer sets for checking the Bible-RAG retriever and generator in
**English** (KJV Bible, Pickthall Quran) and **Chinese** (Chinese Union Version
(和合本) Bible, Ma Jian (马坚) Quran).

| File | Items | Purpose |
|---|---|---|
| `golden_en.jsonl` | 643 | English questions; contexts come from `kjv` / `quran_en` |
| `golden_zh.jsonl` | 643 | Chinese questions; contexts come from `cuv` / `quran_zh` |
| `golden_smoke.jsonl` | 54 | Fixed, stratified subset (3 per category × 9 categories × en+zh) for fast CI runs |
| `build_golden.py` | – | Single source of truth: item definitions plus the builder and validator |

**Total: 1,286 items** (643 en + 643 zh), covering **66 Bible books** and **79 surahs**.

## Rebuild

```bash
cd evals/datasets
python build_golden.py                       # auto-detects ../../data (repo layout)
python build_golden.py --data-dir /path/to/data
BIBLE_RAG_DATA=/path/to/data python build_golden.py
python build_golden.py --check               # validate only, write nothing
```

The build is deterministic and safe to re-run. It **fails loudly** (exit 1, listing
every problem) if any of these are true:

- a ref is malformed, missing from the corpus or empty;
- a category is unknown;
- an answerable item has no refs, or has more than 5;
- a `not_found` item has refs;
- refs are duplicated;
- the `corpus` label does not match the refs (`both` needs refs from both corpora);
- an answer does not cite every one of its refs;
- a question is duplicated within a language;
- an auto-generated quote fragment is not unique in its translation.

At the end it prints stats by language, corpus, category, difficulty and behavior.

`expected_contexts` are **never hand-typed**. They are copied verbatim from the corpus
jsonl files at build time, so they always match what the index contains.

## Schema (one JSON object per line)

| Field | Type | Meaning |
|---|---|---|
| `id` | str | `en-001` … / `zh-001` …; the same number in en and zh is the same underlying item |
| `lang` | `en` \| `zh` | Language of the question and answer |
| `corpus` | `bible` \| `quran` \| `both` \| `none` | Which scripture(s) the answer comes from (`none` = out of scope) |
| `category` | str | See the categories below |
| `difficulty` | `easy` \| `medium` \| `hard` | Rough retrieval difficulty |
| `question` | str | User query (the DeepEval `input`) |
| `expected_answer` | str | Reference answer. It quotes the verse text and cites every ref as `(Gen.1.1)` / `（Q002.2.255）` |
| `expected_refs` | list[str] | 0–5 canonical refs: `Book.ch.v` with OSIS book codes (`Gen.1.1`, `1Cor.13.4`) or `Qnnn.ch.v` (`Q002.2.255`) |
| `expected_contexts` | list[obj] | `{canon_ref, translation, text}` with the exact corpus text, one per ref; `translation` is `kjv`/`quran_en` (en) or `cuv`/`quran_zh` (zh) |
| `answerable` | bool | `false` when the right behaviour is to say "not found" |
| `expected_behavior` | `answer` \| `not_found` \| `correct_premise` | `correct_premise` means: point out the false premise or misquote, then cite the real verse |
| `parallel_contexts` | list[obj] | *(`cross_lingual` only)* the same verses in the other language's translation |
| `notes` | str | *(optional)* numbering or translation caveats; `generated: …` marks template-generated items |

Refs can differ between languages when the versification differs. For example,
KJV 3 John has 14 verses while CUV splits verse 14 into 14–15. Each language file
holds the refs that are correct for its own translation.

## Categories

| Category | en | zh | Total | What it tests |
|---|---:|---:|---:|---|
| `factual` | 82 | 82 | 164 | Narrative and factual questions ("How was Naaman healed?", "What did Shu'eyb command Midian?") |
| `topical` | 29 | 29 | 58 | Multi-verse thematic questions (forgiveness, anger, orphans, …) |
| `verse_lookup` | 301 | 301 | 602 | "Quote John 3:16", "Which verse says '…'?", "Where is '…' found?" |
| `cross_lingual` | 70 | 70 | 140 | Question quotes the verse in the *other* language; the answer must find it in this language |
| `cross_corpus` | 31 | 31 | 62 | Bible vs Quran comparisons (Noah, Joseph's shirt, Abraham's guests, eye for an eye, …); includes stories the two tell differently |
| `paraphrase` | 50 | 50 | 100 | **Hard**: everyday wording with almost no keywords from the verse ("don't go to bed angry" → Eph 4:26) |
| `negative` | 28 | 28 | 56 | Out of scope (Bhagavad Gita, Book of Mormon, SQL, photosynthesis, …): must answer `not_found` and cite nothing |
| `trap` | 30 | 30 | 60 | Misquotes and false premises ("God helps those who help themselves", "Moses's ark", "Iblis was an angel", "40 pieces of silver") |
| `numbering` | 22 | 22 | 44 | Versification edge cases (Psalm superscriptions, Mal 4 / Heb Mal 3, Rev 12:18, John 7:53) and refs that do not exist (Genesis 51:1, Surah 115, al-Baqarah 287) |

**Corpus mix:**

| Corpus | Items |
|---|---:|
| bible | 718 |
| quran | 450 |
| both | 62 |
| none | 56 |

Among single-corpus items that is about 61% Bible and 39% Quran.

**Behavior mix:**

| Behavior | Items |
|---|---:|
| answer | 1,158 |
| correct_premise | 42 |
| not_found | 86 |

### Hand-written vs generated items

- **638 hand-written items:** factual, topical, cross_corpus, paraphrase, negative, trap
  and numbering, plus part of verse_lookup and cross_lingual. For each one the answer
  was written against the verse text that was fetched for it. Every quoted span in
  `expected_answer` is checked automatically against the contexts.
- **648 template-generated items:** 540 verse_lookup and 108 cross_lingual, built from
  curated ref lists. Their answer is the verbatim verse text, and they carry
  `notes: "generated: answer is the verbatim verse text"`.
  - Reverse-lookup questions ("Which verse says '…'?") quote a fragment of the verse.
  - The fragment is **normalised**: quote marks, parentheticals (Psalm superscriptions,
    CUV alternative-reading notes, Pickthall's bracketed glosses) and leading speech
    intros ("And he said, …", "…说：") are removed.
  - The fragment is also checked to be unique in that translation.
  - So a question fragment may not be a byte-exact substring of the context. Use
    normalised matching if you score on it.

## DeepEval mapping

| `LLMTestCase` field | Source |
|---|---|
| `input` | `question` |
| `expected_output` | `expected_answer` |
| `context` | `[c["text"] for c in expected_contexts]` (ground-truth passages) |
| `retrieval_context` | filled in **at eval time** with the texts your retriever returned |
| `actual_output` | filled in **at eval time** with your RAG answer |

Recommended metrics:

- **ContextualPrecisionMetric**: are the relevant retrieved chunks ranked above the irrelevant ones? Uses `expected_output`.
- **ContextualRecallMetric**: does `retrieval_context` cover everything in `expected_output`?
- **FaithfulnessMetric**: is `actual_output` supported by `retrieval_context`? This catches invented verses.
- **AnswerRelevancyMetric**: does `actual_output` address the `input`?

For `expected_behavior == "not_found"` (negative items and not_found traps),
`expected_contexts` is empty, so the contextual metrics are not meaningful. Score
these with a refusal check instead. For example, use a `GEval` criterion such as
"says the passage is not in the scriptures and cites no verse". A cheaper option
is to assert that no ref is cited. For `correct_premise`, also check that the
answer rejects the premise.

A cheap, deterministic retrieval metric is ref hit-rate / recall@k: compare
`expected_refs` against the `canon_ref`s your retriever returned.

### Loader snippet

```python
import json
from pathlib import Path
from deepeval import evaluate
from deepeval.test_case import LLMTestCase
from deepeval.metrics import (ContextualPrecisionMetric, ContextualRecallMetric,
                              FaithfulnessMetric, AnswerRelevancyMetric)

DATASETS = Path("evals/datasets")

def load(name="golden_en.jsonl"):
    with open(DATASETS / name, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]

def to_test_case(item, rag):                 # rag(question, lang) -> (answer, [chunk dicts])
    answer, chunks = rag(item["question"], item["lang"])
    return LLMTestCase(
        input=item["question"],
        actual_output=answer,
        expected_output=item["expected_answer"],
        context=[c["text"] for c in item["expected_contexts"]],
        retrieval_context=[c["text"] for c in chunks],
        additional_metadata={"id": item["id"], "category": item["category"],
                             "expected_refs": item["expected_refs"],
                             "retrieved_refs": [c.get("canon_ref") for c in chunks]},
    )

items = [it for it in load("golden_smoke.jsonl") if it["answerable"]]   # fast CI run
cases = [to_test_case(it, my_rag) for it in items]
evaluate(test_cases=cases, metrics=[ContextualPrecisionMetric(), ContextualRecallMetric(),
                                    FaithfulnessMetric(), AnswerRelevancyMetric()])
```

## Smoke subset

`golden_smoke.jsonl` is regenerated on every build. It takes 3 items per category,
evenly spaced through that category, in both languages (same item number), and keeps
the original ids. It has 54 records: 22 bible, 20 quran, 6 both and 6 none. It
includes negative, trap and numbering items, so the CI run also exercises "not found"
handling.

## Notes and caveats

- **Versification** follows the corpus (KJV/CUV English-style numbering, Hafs numbering
  for the Quran), not Hebrew/BHS numbering. `numbering` items carry `notes`
  explaining each difference.
- **Translation wording:** answers quote KJV (en) and CUV (zh) for the Bible, and Pickthall
  (en) and Ma Jian (zh) for the Quran. Names follow each translation: Pickthall
  "Saul/Goliath", "Elias", "Shu'eyb" vs Ma Jian 塔鲁特/查鲁特, 易勒雅斯, 舒阿卜.
- **Licensing:** the contexts embed verbatim corpus text. KJV and the 1919 CUV are public
  domain and Pickthall (1930) is generally treated as public domain, but **the Ma Jian
  translation is still under copyright**. Check redistribution terms before publishing
  `golden_zh.jsonl` outside the project.
