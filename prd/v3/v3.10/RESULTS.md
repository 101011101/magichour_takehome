# v3.10 — RESULTS

Per-case detail, numbers and methodology for the canvas run, per [SCHEMA.md](../SCHEMA.md).
The decision this evidence supports is not here; it belongs in
[EXPERIMENT.md](EXPERIMENT.md).

The question: **does call 2 have to scale the person photo up to 1 MP?** One variable, call
2's canvas. Everything else — reference, prompt, weights, sampler, seed, hardware — is held
fixed by [TEST.md](TEST.md).

## 1. The run (2026-09-12)

`v3/colab/v310_a100.ipynb` on an A100-SXM4-40GB: **1,056 klein calls, 38.3 min, CAD 0.44**
at 0.689 CAD/h (USD 15.84 for the same calls on fal). Call 2 only — the references are iron
man 2's archived `refs/{g}__BC.jpg`, handed to both arms unchanged, so no bald pass and no
crop ran in this experiment. Outputs `v3/runs/v310/a100/`, bundle
`v310_a100_20260912_1936.zip`.

Weights: `Photoroom/FLUX.2-klein-4b-fp8-diffusers` `transformer_bf16` @ `408c457f` with BFL's
text encoder, VAE, scheduler and tokenizer @ `e7b7dc27` — the production transformer, recorded
in `meta/cost_v310.json`.

| | |
|---|---|
| cells in the fold | 600 (200 pairs × seeds 46/47/48) |
| no-ops — person photo already at the bound, both rules give one canvas | **144** |
| comparable cells | **456** |
| generations | `SCALE` 600 + `NOSCALE` 456 = 1,056 |
| `NOSCALE` canvas as a fraction of `SCALE`'s, by area | 0.571–0.849, mean **0.701** |

**Measured latency**, from `meta/cost_v310.json`: call 2 mean **2.377 s** under `SCALE`
against **1.903 s** under `NOSCALE` — **19.9% faster**. This is a property of the canvas, not
of the marking, and nothing below can take it away.

## 2. The instrument

`v3/build/v310_count_page.py` → `v3/report/v310_count.html` → `v3/testsets/v310_count.csv`.

**Not an A/B.** Each arm is counted on its own. The 456 comparable cells appear twice — once
per arm — as **912 cards in one shuffled stream**, one image per card, and the reviewer clicks
every image they would not ship. So each arm gets a *rate*, counted by one eye under one bar in
one sitting, rather than a preference between two images.

The arm is not printed on the card and the prior verdict is not shown; both ride in the export.
Hiding them costs nothing and stops the count drifting toward whichever rule the reviewer
expects to win.

**All 912 cards were marked.** No partial sitting, no denominator to argue about.

## 3. The rates

| arm | failures | rate | 95% CI (Wilson) |
|---|---|---|---|
| `SCALE` — the shipped rule | 18 / 456 | **3.95%** | 2.51–6.15% |
| `NOSCALE` — never upscale | 12 / 456 | **2.63%** | 1.51–4.54% |

Joined per cell, which is the comparison that does not depend on the two counts sharing a
threshold — they were made in the same sitting, but the join is stronger anyway:

| | `NOSCALE` clean | `NOSCALE` fails |
|---|---|---|
| **`SCALE` clean** | 427 | **11** |
| **`SCALE` fails** | **17** | 1 |

**17 cells `NOSCALE` rescues against 11 it breaks.** McNemar exact **p = 0.345** on the 28
discordant cells.

**What that p-value means here, and what it does not.** It says a 17 : 11 split is well inside
what chance produces at this sample size. It does **not** say the arms are equal, and it does
not license reading 3.95% and 2.63% as the same number — the point estimate favours `NOSCALE`
and the sample cannot resolve a gap of that size. Six net cells out of 456 is the entire
difference.

**The 456 cells are the whole fold minus the no-ops.** Nothing was sampled and nothing was
filtered, so this comparison carries no selection of its own.

## 4. The subgroup split, and why it must not be read as a cost

Split by each cell's prior blind verdict:

| prior verdict | cells | `SCALE` | `NOSCALE` | rescues : breaks | p |
|---|---|---|---|---|---|
| clean (both sweeps passed it) | 420 | 3 = **0.71%** | 10 = **2.38%** | 3 : 10 | 0.092 |
| fail (either sweep failed it) | 36 | 15 = **41.67%** | 2 = **5.56%** | 14 : 1 | 0.001 |

Read naively this says `NOSCALE` rescues failures and breaks working cells. **That reading is
wrong, and an earlier reading of this run made it.** It was corrected the same day, and the
correction is the reason this section exists.

**The groups are defined by the incumbent's own record.** The prior verdicts come from the
blind sweeps of `bc2_count` and `er_count`, made on archive outputs produced **under the
`SCALE` rule**. So each arm's relationship to its label differs:

- A cell labelled *fail* is one the shipped rule failed. Re-drawn, the shipped rule can mostly
  only improve — regression toward its own mean — and 15 of 36 still failing is that regression
  landing short. `NOSCALE` inherits no such debt.
- A cell labelled *clean* is one the shipped rule passed. Re-drawn, it is flattered on exactly
  those cells, and 3 of 420 is what that flattery looks like.

Conditioning on a noisy prior measurement biases the arm that produced it, in opposite
directions in the two groups. Both columns are confounded; **neither subgroup number is
evidence of cost or benefit**, and the 0.71% against 2.38% is not a measured harm. The
unbiased comparison is §3's, over all 456.

The two biases also very nearly account for the overall gap: the fail group is 7.9% of the
cells and favours `NOSCALE` by ~36 points, the clean group 92.1% and favours `SCALE` by ~1.7
points, which is ~1.3 points net — the size of the observed 3.95% − 2.63%. That arithmetic is
a caution about how little the headline gap can be leaned on, not a claim the gap is spurious.

**What would remove the confound:** marking a fresh sample with no prior labels in play, or a
second reviewer over the same cards. Neither has been done.

## 5. Failure clustering — the one clean difference

Both arms' cells are pairs at three seeds, so the record says how much of each rate is a seed
lottery rather than a broken pair. This property is computed from the marks alone and does
**not** depend on the prior labels, so §4's confound does not reach it.

| | `SCALE` | `NOSCALE` |
|---|---|---|
| failures | 18 | 12 |
| distinct pairs carrying them | 11 | 11 |
| failures per failing pair | 1×6, 2×3, 3×2 | **1×10, 2×1** |
| pairs failing at **every** comparable seed | **2** (`g004+g005`, `g013+p006`) | **0** |

`NOSCALE` has no pair that fails at every seed; `SCALE` has two. Under the shipped retry policy
— a rejected image is redrawn at a fresh seed ([v3.8 RESULTS §6](../v3.8/RESULTS.md)) — a
failure with no seed-stable pair behind it is a failure a retry can reach. On this fold
`NOSCALE`'s residue after one retry is smaller than its rate suggests, and `SCALE`'s is floored
by two pairs no seed repairs.

## 6. The cells

**`SCALE` failures (18).** Prior verdict in brackets.
`dualuse_lp_navy_quarterzip_knit_LOWRES+dualuse_lp_plaid_overcoat_brown_suit`@47 [clean] ·
`g004+g005`@46,47,48 [fail] · `g005+g009`@46,47 [fail] · `g005+p002`@48 [fail] ·
`g013+p006`@46 [fail], @47 [clean], @48 [fail] · `g014+g029`@46 [clean], @47 [fail] ·
`g015+g018`@48 [fail] · `g027+p011`@48 [fail] ·
`p008+dualuse_emma_watson_black_blazer_armscrossed`@47,48 [fail] · `p008+p013`@47 [fail] ·
`p012+dualuse_queen_latifah_gown_stage`@46 [fail]

**`NOSCALE` failures (12).**
`g005+g009`@47 [fail] · `g009+g011`@47 [clean] · `g012+p005`@46 [clean] ·
`g027+p011`@47 [clean] · `g029+g030`@48 [clean] · `p004+p009`@46 [clean] ·
`p006+p011`@48 [fail] · `p008+p009`@48 [clean] · `p011+p024`@46,48 [clean] ·
`p028+g015`@47 [clean] · `p028+p029`@46 [clean]

**Both arms fail:** `g005+g009`@47 — one cell in 456. `g005+g009` is the one-trouser-leg,
one-bare-knee geometry case the V3 list files as unreachable by prompt — "if it matters it
needs a mask, not words" ([V3 TODO](../TODO.md)). It is unreachable by canvas too.

14 of `SCALE`'s 18 failures sit on prior-fail cells; 10 of `NOSCALE`'s 12 sit on prior-clean
ones. That distribution is §4's confound made visible, not two different failure modes.

## 7. What this run cannot say

- **One reviewer.** The same reviewer's bar moved **1.72×** between two sittings on these very
  cells ([v3.8 RESULTS §3](../v3.8/RESULTS.md)). One sitting removes drift *within* this run;
  it does not make the bar right.
- **The resolution tell.** `NOSCALE`'s output is genuinely fewer pixels. Both sides render at
  the same display width and the lightbox matches, so pixel count cannot give the arm away —
  but a smaller canvas resampled up can still read softer, and that route to identifying the
  arm cannot be closed by this page. Declared in advance in [TEST.md §5](TEST.md).
- **Not poolable with [v3.9](../v3.9/RESULTS.md).** v3.9 rebuilt its references under the 1 MP
  bound; this run uses the archive's, built at 1.15 MP. Same question, different inputs — the
  two sets of marks must not be merged, and v3.9's 36 failure cards are a replication here, not
  additional evidence.
- **Nothing about the references.** The bald pass and the crop did not run. Whatever share of
  the remaining failures is reference-side (v3.8 measured 68% of one arm's) is untouched by
  either canvas.

## 8. Evidence paths

| what | where |
|---|---|
| the run | `v3/runs/v310/a100/`, zip `v310_a100_20260912_1936.zip` |
| run meta, per-cell canvases | `v3/runs/v310/a100/meta/{cost_v310,v310_meta}.json` |
| the marks | `v3/testsets/v310_count.csv` (912 rows) |
| the counting page | `v3/report/v310_count.html`, built by `v3/build/v310_count_page.py` |
| the set of record | `v3/colab/v310_set.csv`, built by `v3/build/make_v310_set.py` |
| the runner | `v3/colab/lib/run_v310.py` |
