# Input-guard evaluation

Measured with `make eval-guards` (no LLM). Official splits: all 136 trap items, all 108 negative items, and a 200-item normal sample (`seed=2026`). Thresholds were chosen on a 50/50 split of those groups (seed 2026) and then reported on the held-out half.

The semantic layer uses bge-m3 dense similarity to a small set of in-domain / out-of-domain prototype descriptions (`allow_margin=0.19`, `refuse_margin=-0.06`). Hard rule refusals (length, injection, other-canon) are never overridden. In the ambiguous band the cue-based rule stands.

## Official splits

| stage | trap | negative | trap+negative | false-refusal (normal 200) |
|---|---:|---:|---:|---:|
| Rules only, as of `fb93216` | 5/136 (3.7%) | 53/108 (49.1%) | 58/244 (23.8%) | 1/200 (0.5%), en-489 |
| Rules only, this change (Tobit / 摩尔门 added to other-canon) | 5/136 (3.7%) | 55/108 (50.9%) | 60/244 (24.6%) | 1/200 (0.5%), en-489 |
| Rules + bge-m3 (`allow=0.19`, `refuse=-0.06`) | 7/136 (5.1%) | 80/108 (74.1%) | 87/244 (35.7%) | 1/200 (0.5%), en-489 |

The only false refusal on the official 200-sample is still `en-489` ("Watch out for fake preachers who look harmless but are predators underneath — where is this warning?"), which has no scripture cue and is not close enough to the in-domain prototypes to be rescued.

## Tune / held-out (seed 2026, 50/50 of each official group)

Shipped margins `allow_margin=0.19`, `refuse_margin=-0.06`:

| split | negative | trap | false-refusal |
|---|---:|---:|---:|
| tune (54 / 68 / 100) | 42/54 (77.8%) | 3/68 (4.4%) | 1/100 (1.0%) |
| held-out (54 / 68 / 100) | 38/54 (70.4%) | 4/68 (5.9%) | 0/100 (0.0%) |

Held-out negative block rate stays well above the rules-only baseline; the official 200-sample false-refusal rate does not go up.

Modern-technology and modern-place questions (smartphones, internet, vaccines, Paris, electric cars, and so on) account for most of the new blocks. A few anachronisms still slip through (coffee, Constantine, the Apollo landing, chess) because they sit closer to the in-domain prototypes. Those remain for the retrieval / generation path to answer with "not found".
