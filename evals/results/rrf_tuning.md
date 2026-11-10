# RRF tuning on the smoke set

Smoke set: `evals/datasets/golden_smoke.jsonl` (60 items).
Scored: **50** items that have `expected_refs` (25 en + 25 zh).
Skipped: **10** items with no expected refs, listed at the end.

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
| dense | — | — | 50 | 0.491 | 0.507 | 25 | 0.423 | 0.483 | 25 | 0.560 | 0.532 |
| sparse | — | — | 50 | 0.592 | 0.546 | 25 | 0.609 | 0.596 | 25 | 0.575 | 0.496 |
| hybrid (20/20) | 20 | 20 | 50 | 0.655 | 0.609 | 25 | 0.723 | 0.658 | 25 | 0.587 | 0.560 |
| hybrid (20/60) | 20 | 60 | 50 | 0.655 | 0.609 | 25 | 0.723 | 0.658 | 25 | 0.587 | 0.560 |
| hybrid (50/20) | 50 | 20 | 50 | 0.665 | 0.596 | 25 | 0.703 | 0.634 | 25 | 0.627 | 0.558 |
| hybrid (50/60) | 50 | 60 | 50 | 0.645 | 0.591 | 25 | 0.663 | 0.626 | 25 | 0.627 | 0.556 |
| hybrid (100/20) | 100 | 20 | 50 | 0.659 | 0.593 | 25 | 0.683 | 0.621 | 25 | 0.635 | 0.565 |
| hybrid (100/60) | 100 | 60 | 50 | 0.643 | 0.590 | 25 | 0.631 | 0.612 | 25 | 0.655 | 0.568 |

Best config by Recall@10, ties broken by MRR: **hybrid (50/20) (Recall@10=0.665, MRR=0.596)**.

## Investigation: why hybrid drops `kjv:Col.3.13-15`

Query: `forgive others`. Target chunk: `kjv:Col.3.13-15` (KJV Colossians 3:13, "Forbearing one another, and forgiving one another"). Surah 40 (Ghafir) is titled **The Forgiver**, and every English chunk of that surah is prefixed with `The Forgiver 40` under the `book_chapter_header.v1` rule.

### no filter

| mode | rank of `kjv:Col.3.13-15` | first hit with Col.3.13 | first Q040 | Q040 in top 10 | Q040 in top 50 |
|---|---:|---:|---:|---:|---:|
| dense | 1 | 1 | 13 | 0 | 5 |
| sparse | >50 | >50 | 2 | 3 | 4 |
| hybrid | 16 | 16 | 2 | 3 | 4 |

Top 10, **dense**, no filter:

| rank | score | pk | text |
|---:|---:|---|---|
| 1 | 0.6169 | `kjv:Col.3.13-15` | Forbearing one another, and forgiving one another, if any man have a q |
| 2 | 0.6110 | `kjv:2Cor.2.9-11` | For to this end also did I write, that I might know the proof of you,  |
| 3 | 0.6037 | `kjv:Luke.17.3-5` | Take heed to yourselves: If thy brother trespass against thee, rebuke  |
| 4 | 0.6012 | `cuv:Col.3.13-15` | 倘若这人与那人有嫌隙，总要彼此包容，彼此饶恕；主怎样饶恕了你们，你们也要怎样饶恕人。在这一切之外，要存着爱心，爱心就是联络全德的。又要叫基督 |
| 5 | 0.5947 | `quran_en:Q005.5.39-41` | But whoso repenteth after his wrongdoing and amendeth, lo! Allah will  |
| 6 | 0.5943 | `kjv:2Cor.2.5-7` | But if any have caused grief, he hath not grieved me, but in part: tha |
| 7 | 0.5903 | `kjv:Matt.6.13-15` | And lead us not into temptation, but deliver us from evil: For thine i |
| 8 | 0.5900 | `cuv:Luke.17.3-5` | 你们要谨慎！若是你的弟兄得罪你，就劝戒他；他若懊悔，就饶恕他。倘若他一天七次得罪你，又七次回转，说：『我懊悔了』，你总要饶恕他。」使徒对主说 |
| 9 | 0.5850 | `cuv:Col.3.11-13` | 在此并不分希腊人、犹太人，受割礼的、未受割礼的，化外人、西古提人，为奴的、自主的，惟有基督是包括一切，又住在各人之内。所以，你们既是神的选民 |
| 10 | 0.5816 | `kjv:1Kgs.8.49-51` | Then hear thou their prayer and their supplication in heaven thy dwell |

Top 10, **sparse**, no filter:

| rank | score | pk | text |
|---:|---:|---|---|
| 1 | 0.1338 | `kjv:Luke.23.33-35` | And when they were come to the place, which is called Calvary, there t |
| 2 | 0.1322 | `quran_en:Q040.40.7-9` | Those who bear the Throne, and all who are round about it, hymn the pr |
| 3 | 0.1251 | `quran_en:Q004.4.17-19` | Forgiveness is only incumbent on Allah toward those who do evil in ign |
| 4 | 0.1214 | `quran_en:Q004.4.149-151` | If ye do good openly or keep it secret, or forgive evil, lo! Allah is  |
| 5 | 0.1180 | `quran_en:Q040.40.55-57` | Then have patience (O Muhammad). Lo! the promise of Allah is true. And |
| 6 | 0.1170 | `kjv:2Chr.6.19-21` | Have respect therefore to the prayer of thy servant, and to his suppli |
| 7 | 0.1123 | `kjv:2Cor.2.9-11` | For to this end also did I write, that I might know the proof of you,  |
| 8 | 0.1101 | `quran_en:Q040.40.53-55` | And We verily gave Moses the guidance, and We caused the Children of I |
| 9 | 0.1094 | `quran_en:Q002.2.263-265` | A kind word with forgiveness is better than almsgiving followed by inj |
| 10 | 0.1093 | `quran_en:Q009.9.43-45` | Allah forgive thee (O Muhammad)! Wherefor didst thou grant them leave  |

Top 10, **hybrid**, no filter:

| rank | score | pk | text |
|---:|---:|---|---|
| 1 | 0.0311 | `kjv:2Cor.2.9-11` | For to this end also did I write, that I might know the proof of you,  |
| 2 | 0.0298 | `quran_en:Q040.40.7-9` | Those who bear the Throne, and all who are round about it, hymn the pr |
| 3 | 0.0259 | `kjv:Luke.17.3-5` | Take heed to yourselves: If thy brother trespass against thee, rebuke  |
| 4 | 0.0256 | `kjv:2Cor.2.5-7` | But if any have caused grief, he hath not grieved me, but in part: tha |
| 5 | 0.0254 | `quran_en:Q002.2.263-265` | A kind word with forgiveness is better than almsgiving followed by inj |
| 6 | 0.0253 | `quran_en:Q040.40.53-55` | And We verily gave Moses the guidance, and We caused the Children of I |
| 7 | 0.0244 | `kjv:1Kgs.8.39-41` | Then hear thou in heaven thy dwelling place, and forgive, and do, and  |
| 8 | 0.0244 | `kjv:Matt.6.13-15` | And lead us not into temptation, but deliver us from evil: For thine i |
| 9 | 0.0241 | `quran_en:Q040.40.5-7` | The folk of Noah and the factions after them denied (their messengers) |
| 10 | 0.0241 | `kjv:1Kgs.8.49-51` | Then hear thou their prayer and their supplication in heaven thy dwell |

### corpus=bible

| mode | rank of `kjv:Col.3.13-15` | first hit with Col.3.13 | first Q040 | Q040 in top 10 | Q040 in top 50 |
|---|---:|---:|---:|---:|---:|
| dense | 1 | 1 | — | 0 | 0 |
| sparse | >50 | >50 | — | 0 | 0 |
| hybrid | 13 | 13 | — | 0 | 0 |

Top 10, **dense**, corpus=bible:

| rank | score | pk | text |
|---:|---:|---|---|
| 1 | 0.6169 | `kjv:Col.3.13-15` | Forbearing one another, and forgiving one another, if any man have a q |
| 2 | 0.6110 | `kjv:2Cor.2.9-11` | For to this end also did I write, that I might know the proof of you,  |
| 3 | 0.6037 | `kjv:Luke.17.3-5` | Take heed to yourselves: If thy brother trespass against thee, rebuke  |
| 4 | 0.6012 | `cuv:Col.3.13-15` | 倘若这人与那人有嫌隙，总要彼此包容，彼此饶恕；主怎样饶恕了你们，你们也要怎样饶恕人。在这一切之外，要存着爱心，爱心就是联络全德的。又要叫基督 |
| 5 | 0.5943 | `kjv:2Cor.2.5-7` | But if any have caused grief, he hath not grieved me, but in part: tha |
| 6 | 0.5903 | `kjv:Matt.6.13-15` | And lead us not into temptation, but deliver us from evil: For thine i |
| 7 | 0.5900 | `cuv:Luke.17.3-5` | 你们要谨慎！若是你的弟兄得罪你，就劝戒他；他若懊悔，就饶恕他。倘若他一天七次得罪你，又七次回转，说：『我懊悔了』，你总要饶恕他。」使徒对主说 |
| 8 | 0.5850 | `cuv:Col.3.11-13` | 在此并不分希腊人、犹太人，受割礼的、未受割礼的，化外人、西古提人，为奴的、自主的，惟有基督是包括一切，又住在各人之内。所以，你们既是神的选民 |
| 9 | 0.5816 | `kjv:1Kgs.8.49-51` | Then hear thou their prayer and their supplication in heaven thy dwell |
| 10 | 0.5810 | `cuv:2Cor.2.9-11` | 为此我先前也写信给你们，要试验你们，看你们凡事顺从不顺从。你们赦免谁，我也赦免谁。我若有所赦免的，是在基督面前为你们赦免的，免得撒但趁着机会 |

Top 10, **sparse**, corpus=bible:

| rank | score | pk | text |
|---:|---:|---|---|
| 1 | 0.1338 | `kjv:Luke.23.33-35` | And when they were come to the place, which is called Calvary, there t |
| 2 | 0.1170 | `kjv:2Chr.6.19-21` | Have respect therefore to the prayer of thy servant, and to his suppli |
| 3 | 0.1123 | `kjv:2Cor.2.9-11` | For to this end also did I write, that I might know the proof of you,  |
| 4 | 0.1093 | `kjv:Ps.86.5-7` | For thou, Lord, art good, and ready to forgive; and plenteous in mercy |
| 5 | 0.1056 | `kjv:Matt.6.11-13` | Give us this day our daily bread. And forgive us our debts, as we forg |
| 6 | 0.1043 | `kjv:2Chr.6.27-29` | Then hear thou from heaven, and forgive the sin of thy servants, and o |
| 7 | 0.1036 | `kjv:Ps.130.3-5` | If thou, Lord, shouldest mark iniquities, O Lord, who shall stand? But |
| 8 | 0.1032 | `kjv:2Chr.6.21-23` | Hearken therefore unto the supplications of thy servant, and of thy pe |
| 9 | 0.1031 | `kjv:Ps.86.3-5` | Be merciful unto me, O Lord: for I cry unto thee daily. Rejoice the so |
| 10 | 0.1013 | `kjv:1Sam.25.27-29` | And now this blessing which thine handmaid hath brought unto my lord,  |

Top 10, **hybrid**, corpus=bible:

| rank | score | pk | text |
|---:|---:|---|---|
| 1 | 0.0320 | `kjv:2Cor.2.9-11` | For to this end also did I write, that I might know the proof of you,  |
| 2 | 0.0290 | `kjv:Luke.17.3-5` | Take heed to yourselves: If thy brother trespass against thee, rebuke  |
| 3 | 0.0289 | `kjv:2Cor.2.5-7` | But if any have caused grief, he hath not grieved me, but in part: tha |
| 4 | 0.0278 | `kjv:1Kgs.8.39-41` | Then hear thou in heaven thy dwelling place, and forgive, and do, and  |
| 5 | 0.0275 | `kjv:Matt.6.13-15` | And lead us not into temptation, but deliver us from evil: For thine i |
| 6 | 0.0274 | `kjv:2Chr.6.21-23` | Hearken therefore unto the supplications of thy servant, and of thy pe |
| 7 | 0.0273 | `kjv:1Kgs.8.49-51` | Then hear thou their prayer and their supplication in heaven thy dwell |
| 8 | 0.0259 | `kjv:Matt.6.11-13` | Give us this day our daily bread. And forgive us our debts, as we forg |
| 9 | 0.0250 | `kjv:2Cor.2.7-9` | So that contrariwise ye ought rather to forgive him, and comfort him,  |
| 10 | 0.0240 | `kjv:Ps.130.3-5` | If thou, Lord, shouldest mark iniquities, O Lord, who shall stand? But |

### translation=kjv, corpus=bible

| mode | rank of `kjv:Col.3.13-15` | first hit with Col.3.13 | first Q040 | Q040 in top 10 | Q040 in top 50 |
|---|---:|---:|---:|---:|---:|
| dense | 1 | 1 | — | 0 | 0 |
| sparse | >50 | >50 | — | 0 | 0 |
| hybrid | 15 | 15 | — | 0 | 0 |

Top 10, **dense**, translation=kjv, corpus=bible:

| rank | score | pk | text |
|---:|---:|---|---|
| 1 | 0.6169 | `kjv:Col.3.13-15` | Forbearing one another, and forgiving one another, if any man have a q |
| 2 | 0.6110 | `kjv:2Cor.2.9-11` | For to this end also did I write, that I might know the proof of you,  |
| 3 | 0.6037 | `kjv:Luke.17.3-5` | Take heed to yourselves: If thy brother trespass against thee, rebuke  |
| 4 | 0.5943 | `kjv:2Cor.2.5-7` | But if any have caused grief, he hath not grieved me, but in part: tha |
| 5 | 0.5903 | `kjv:Matt.6.13-15` | And lead us not into temptation, but deliver us from evil: For thine i |
| 6 | 0.5816 | `kjv:1Kgs.8.49-51` | Then hear thou their prayer and their supplication in heaven thy dwell |
| 7 | 0.5799 | `kjv:1Kgs.8.39-41` | Then hear thou in heaven thy dwelling place, and forgive, and do, and  |
| 8 | 0.5791 | `kjv:1Pet.4.7-9` | But the end of all things is at hand: be ye therefore sober, and watch |
| 9 | 0.5786 | `kjv:Eph.4.30-32` | And grieve not the holy Spirit of God, whereby ye are sealed unto the  |
| 10 | 0.5783 | `kjv:Gal.6.1-3` | Brethren, if a man be overtaken in a fault, ye which are spiritual, re |

Top 10, **sparse**, translation=kjv, corpus=bible:

| rank | score | pk | text |
|---:|---:|---|---|
| 1 | 0.1338 | `kjv:Luke.23.33-35` | And when they were come to the place, which is called Calvary, there t |
| 2 | 0.1170 | `kjv:2Chr.6.19-21` | Have respect therefore to the prayer of thy servant, and to his suppli |
| 3 | 0.1123 | `kjv:2Cor.2.9-11` | For to this end also did I write, that I might know the proof of you,  |
| 4 | 0.1093 | `kjv:Ps.86.5-7` | For thou, Lord, art good, and ready to forgive; and plenteous in mercy |
| 5 | 0.1056 | `kjv:Matt.6.11-13` | Give us this day our daily bread. And forgive us our debts, as we forg |
| 6 | 0.1043 | `kjv:2Chr.6.27-29` | Then hear thou from heaven, and forgive the sin of thy servants, and o |
| 7 | 0.1036 | `kjv:Ps.130.3-5` | If thou, Lord, shouldest mark iniquities, O Lord, who shall stand? But |
| 8 | 0.1032 | `kjv:2Chr.6.21-23` | Hearken therefore unto the supplications of thy servant, and of thy pe |
| 9 | 0.1031 | `kjv:Ps.86.3-5` | Be merciful unto me, O Lord: for I cry unto thee daily. Rejoice the so |
| 10 | 0.1013 | `kjv:1Sam.25.27-29` | And now this blessing which thine handmaid hath brought unto my lord,  |

Top 10, **hybrid**, translation=kjv, corpus=bible:

| rank | score | pk | text |
|---:|---:|---|---|
| 1 | 0.0320 | `kjv:2Cor.2.9-11` | For to this end also did I write, that I might know the proof of you,  |
| 2 | 0.0291 | `kjv:2Cor.2.5-7` | But if any have caused grief, he hath not grieved me, but in part: tha |
| 3 | 0.0290 | `kjv:Luke.17.3-5` | Take heed to yourselves: If thy brother trespass against thee, rebuke  |
| 4 | 0.0286 | `kjv:1Kgs.8.39-41` | Then hear thou in heaven thy dwelling place, and forgive, and do, and  |
| 5 | 0.0284 | `kjv:2Chr.6.21-23` | Hearken therefore unto the supplications of thy servant, and of thy pe |
| 6 | 0.0280 | `kjv:1Kgs.8.49-51` | Then hear thou their prayer and their supplication in heaven thy dwell |
| 7 | 0.0277 | `kjv:Matt.6.13-15` | And lead us not into temptation, but deliver us from evil: For thine i |
| 8 | 0.0271 | `kjv:Matt.6.11-13` | Give us this day our daily bread. And forgive us our debts, as we forg |
| 9 | 0.0262 | `kjv:2Cor.2.7-9` | So that contrariwise ye ought rather to forgive him, and comfort him,  |
| 10 | 0.0255 | `kjv:Ps.130.3-5` | If thou, Lord, shouldest mark iniquities, O Lord, who shall stand? But |


## Findings

**Best config.** On this 50-item smoke slice, every hybrid grid point beats dense-only and sparse-only. The best Recall@10 is **hybrid with per-list limit 50 and k=20** (0.665 recall, 0.596 MRR). The code default (50/60) is close behind (0.645 / 0.591). The 20/20 and 20/60 grids are identical here and have the best MRR (0.609) with slightly lower recall (0.655). English recall is more sensitive to candidate depth; Chinese Recall@10 rises as the list grows (0.587 at 20 → 0.655 at 100/60). The default in `search()` is left at candidates=50, k=60; 50/20 is the best measured alternative on this slice.

**Col.3.13 is not a filter bug.** `build_filter` is attached to both `AnnSearchRequest`s. With `corpus=bible` or `translation=kjv, corpus=bible`, no Surah 40 chunk appears in the top 50 of dense, sparse, or hybrid (also covered by `test_hybrid_filter_applies_to_both_requests`). Quran hits only appear when the query is run with no corpus filter.

**Why hybrid still drops `kjv:Col.3.13-15`.** Two separate effects:

1. *Sparse misses the verse entirely.* Dense ranks `kjv:Col.3.13-15` first (cosine 0.6169): the verse says "forgiving one another / Christ forgave you", a paraphrase of "forgive others". Sparse never places that chunk in the top 200, even with a bible/kjv filter. Sparse's #1 is `kjv:Luke.23.33-35`, which contains the exact tokens **"forgive"** ("Father, forgive them") and **"others"** ("He saved others"). Colossians 3:13 uses "forgiving" / "forgave" / "one another", so it loses the lexical match. RRF only scores a document in lists where it appears, so a dense-only #1 gets `1/(k+1)` and loses to passages mid-ranked in *both* lists (for any k: a single-list rank-1 cannot beat a doc at ranks 2 and 3). That is why hybrid puts Colossians at 16 (no filter), 13 (bible), and 15 (kjv+bible) — out of the top 10 — even after Quran rows are filtered out.

2. *Unfiltered sparse boosts Surah 40.* Every English chunk of Surah 40 (Ghafir) is prefixed with `The Forgiver 40` (`book_chapter_header.v1`), and several verses also contain "forgive". Sparse therefore places Q040 chunks at ranks 2, 5 and 8. Some of those also make the dense candidate list (first Q040 is dense rank 13), so RRF lifts three Q040 chunks into the unfiltered hybrid top 10. This is a side effect of putting the English surah title in the embed prefix, not a broken filter. Changing the prefix (for example to a book code like `Q040 40`) would need a full re-embed and a new index fingerprint; it is left for a later experiment.

No retrieval-code change in this change set: the filter is correct, and switching the default RRF k or the prefix is a product/index decision.


## Skipped items (no expected refs)

10 items were excluded from Recall@10 / MRR
(negative, plus trap/numbering items whose expected behaviour is `not_found`):

- `en-166` (en, negative, `not_found`): What did the Buddha teach about the Four Noble Truths?
- `zh-166` (zh, negative, `not_found`): 佛陀关于四圣谛的教导是什么？
- `en-303` (en, negative, `not_found`): What will the weather be in Jerusalem tomorrow?
- `zh-303` (zh, negative, `not_found`): 明天耶路撒冷的天气怎么样？
- `en-330` (en, negative, `not_found`): How many players are on a football (soccer) team?
- `zh-330` (zh, negative, `not_found`): 一支足球队有多少名球员？
- `en-307` (en, trap, `not_found`): Which verse says Mary Magdalene was the wife of Jesus?
- `zh-307` (zh, trap, `not_found`): 哪节经文说抹大拉的马利亚是耶稣的妻子？
- `en-287` (en, numbering, `not_found`): What does Jude 2:1 say?
- `zh-287` (zh, numbering, `not_found`): 犹大书2章1节说什么？
