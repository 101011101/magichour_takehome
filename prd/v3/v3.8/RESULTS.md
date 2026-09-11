# v3.8 — RESULTS

Per-case detail, numbers and methodology for the call-2 prompt investigation, per
[SCHEMA.md](../SCHEMA.md). The decision this evidence supports is not here; it belongs in
`EXPERIMENT.md`.

**A note on names.** This investigation's code, runs and pages are named `v36`
(`v3/runs/v36/`, `v3/build/v36_*.py`, `v3/report/v36_*.html`) because they were written
before v3.7 concluded and the numbering was settled. The paths are left as they are rather
than renamed, so every command in this document runs as written; the document is v3.8
because that is where it falls chronologically.

Call 1 is frozen throughout v3.8. Every arm below was handed the two images the shipped
`BC_klein` cell was handed — `ironman2/inputs/{person}.jpg` and
`ironman2_bc/refs/{garment}__BC.jpg` (klein bald pass, then the V2 cropper with the head
subtracted, not SR'd) — on `BC`'s own call-2 canvas. The only variable anywhere in this
document is the text of call 2.

## 1. The prompts

| arm | call 2 |
|---|---|
| `E0` / `BC` | *Dress the person in image 1 in the clothing shown in image 2. Keep the person's face, identity, body and the background exactly as they are.* — unchanged since V2's attention-modulation run |
| `ER` | ***Replace the clothing in image 1 with** the clothing in image 2.* Same second sentence. |
| `EFR` | `ER` + a paragraph: complete replacement, nothing showing through, no two fabrics blending, no fabric onto skin |
| `EX` | removal, then dressing, then piece count, limb count and framing — five sentences |
| `ERD` | `ER` + a limb clause **built per cell** from a MediaPipe Pose read of image 1; names only parts in frame, says nothing when none are |
| `ERS` | `ER` + that clause **always** |

## 2. The 600-cell head-to-head — the run, and the rates as first marked (2026-09-10)

> **Superseded in part by [§3](#3-the-marking-instrument-and-what-it-did-to-2s-numbers).** The
> run facts, costs, timings and per-cell lists below stand. The two **rates** — 4.83% vs 3.00%
> — and the **18 : 7** join do not: they were marked in two different sittings, and a re-mark of
> `BC` on the same page by the same reviewer turned 29 failures into 50. The marking noise is
> the size of the effect. §3 carries the blind passes that measure the arms against one bar and
> the rate range that replaces these numbers. Kept here because it is the record of what was run
> and what was marked.

**Run.** `v3/colab/v36_ironman_er.ipynb` on an A100: **600 klein calls, 23.8 min, CAD 0.273**
at 0.689 CAD/h, median call 2.28 s. The whole iron-man-2 matrix, 200 pairs × seeds 46/47/48
— **the same 600 cells `BC`'s blind count was made on**, unsampled and unfiltered. Outputs
`v3/runs/v36/ironman_er/`, bundle on Drive (`v3_runs/v36_ironman_er_20260910_2259.zip`).

**Protocol.** Both arms were marked on the same page, `v3/build/bc_count_page.py`, one
button per cell, no prior verdict present in the page or its source. `BC` →
`v3/testsets/bc_count.csv`; `ER` → `v3/testsets/er_count.csv`.

| | failures | rate |
|---|---|---|
| `BC_klein` | 29 / 600 | **4.83%** |
| `ER` | 18 / 600 | **3.00%** |

**−1.83 points absolute, −37.9% relative.** Joined per cell, which is the comparison that
survives any drift in strictness between the two marking sessions:

| | ER clean | ER fails |
|---|---|---|
| **BC clean** | 564 | **7** |
| **BC fails** | **18** | 11 |

18 cells `ER` repairs against 7 it breaks. McNemar exact **p = 0.043** on the 25 discordant
cells.

**The 18 `ER` repairs.**
`dualuse_hugh_jackman_grey_suit_outdoor+dualuse_zendaya_white_blazer_skirt`@46 ·
`dualuse_navy_peacoat_onmodel+g030`@47 ·
`dualuse_scarlett_johansson_black_dress_backview_night+g013`@48 ·
`dualuse_woman_top_denim_skirt_nonceleb+dualuse_zendaya_white_blazer_skirt`@47,48 ·
`g005+g009`@48 · `g005+p002`@47 · `g013+p006`@46,48 · `g027+g029`@48 · `p008+p021`@48 ·
`p011+p024`@47 · `p012+dualuse_queen_latifah_gown_stage`@47 ·
`p013+dualuse_scarlett_johansson_black_dress_backview_night`@46,48 · `p016+p029`@46 ·
`p022+dualuse_queen_latifah_gown_stage`@46,47

**The 7 `ER` regressions**, which are the cells a sceptic should look at first.
`dualuse_lp_floral_kimono_set+g005`@48 ·
`dualuse_woman_top_denim_skirt_nonceleb+dualuse_lp_plaid_overcoat_brown_suit`@47 ·
`g005+g009`@46 · `g005+g014`@47 · `g024+p010`@47 · `g027+p011`@48 ·
`p008+dualuse_emma_watson_black_blazer_armscrossed`@48

`g005+g009` appears on both lists at different seeds, which is the seed lottery of §6 rather
than a contradiction.

**Measurement failure mode, stated rather than hidden.** The two marking passes were made on
the same page under the same protocol but **not in the same sitting** — `BC` earlier on
2026-09-10, `ER` after the run landed. A stricter or more lenient session accounts for some
unknown share of a 1.8-point gap. The per-cell join above is the mitigation: 18-against-7 is
a statement about individual cells changing verdict and does not depend on the two sessions
sharing a threshold. A 100-cell `BC` re-mark in the `ER` sitting was specified to close this
and has not been done.

## 3. The marking instrument, and what it did to §2's numbers (2026-09-10)

§2's comparison is two rates marked in two sittings. This section is the re-mark that tests
whether that protocol can carry the claim, and two blind passes built to answer the same
question without it. The short of it: **the marking noise is the same size as the effect**,
and the arm difference that survives an instrument which does not need two sweeps to agree is
smaller than §2's and still in `ER`'s favour.

**The re-mark.** The same reviewer, the same page (`v3/build/bc_count_page.py`), the same 600
`BC` cells, a later sitting, no prior verdict visible. Pass 1 is
`v3/testsets/bc_count.csv`; pass 2 is `v3/testsets/bc2_count.csv`.

| | pass 1 | pass 2 |
|---|---|---|
| `BC` failures / 600 | 29 | **50** |
| rate | 4.83% | **8.33%** |

| | |
|---|---|
| cells agreeing | 569 / 600 = **94.8%** |
| failed in both | 24 |
| pass 1 only | 5 |
| pass 2 only | 26 |
| Jaccard on failures | **0.44** |
| strict : lenient | **1.72×** |

Cell agreement of 94.8% sounds like a well-behaved instrument and is not one: nearly every
cell is an easy pass, so agreement is dominated by the 550 neither pass calls. On the thing
being counted — failures — the two passes overlap on **24 of 55 distinct failed cells**. A
3.5-point swing in the marked rate of one unchanged arm is larger than the 1.83-point gap §2
reports between two arms. Nothing in §2 is arithmetically wrong; the protocol underneath it
simply cannot resolve a difference of that size.

**Blind pass A — the discordant cells.** `v3/build/v36_discordant_page.py`: the **25 cells
where the pass-1 `BC` sweep and the `ER` sweep disagree** (the off-diagonal of §2's join),
both outputs in front of one eye in one sitting, **arm labels hidden and left/right randomised
per cell** at a fixed seed. One question — which would you ship. Marks
`v3/testsets/v36_discordant.csv`, unblinding key exported beside each answer.

| verdict | cells |
|---|---|
| `ER` better | 5 |
| `BC` better | 3 |
| both fine | 6 |
| both bad | 11 |

**17 of 25 = 68% of the disagreements were threshold, not arm** — cells where one sitting drew
the line differently over two outputs a single sitting calls the same. Of the 8 that were a
real difference, 5–3 favours `ER`, which is not a result: two-sided exact **p ≈ 0.73**. This
pass is the direct measurement of the objection §2 raises against itself, and it lands
against §2.

**Blind pass B — does `ER` fail where `BC` fails.** `v3/build/v36_bcfail_page.py`, built from
**pass 2** (the strict sitting). For each of the 50 cells `BC` pass 2 failed, `BC` and `ER`
were shown side by side in **one** sitting and marked `same` (`ER` has the same problem) or
`clean` (`ER` is fine). A second block carries the other direction: the cells `BC` passes and
the `ER` sweep failed, marked the same way, so the pass yields a cost beside the rescue rather
than a rescue alone. Marks `v3/testsets/v36_bcfail.csv`, page `v3/report/v36_bcfail.html`.

| block | cells | `ER` same | `ER` clean |
|---|---|---|---|
| `bcfail` — `BC` pass-2 failures | 50 | **34 (68%)** | **16 (32%)** |
| `eronly` — `BC` passes, `ER` sweep failed | 3 | 3 | 0 |

This is the instrument that does not require two sweeps to share a threshold: every judgement
is a comparison of two images under one bar, so a drifting bar moves both sides together.
**`ER` repairs 32% of `BC`'s failures** (16/50; Wilson 95% CI **21–46%**).

**The other 68% is the reference-side floor, measured rather than argued.** On 34 of `BC`'s 50
failures `ER` has the same defect. Those are cells where the fault is upstream of call 2's
verb — the reference, the crop, the pair — and no wording of call 2 reaches them. §6's
all-seeds-failing pairs are the same claim from the seed side; this is it counted directly on
a per-cell basis.

**What that implies for the rate, and why it is a floor.**

| | failures / 600 | rate |
|---|---|---|
| `BC`, pass 2 | 50 | 8.33% |
| `ER`, `bcfail` block | 34 | 5.67% |
| `ER`, + the 3 `eronly` cells as marked | **37** | **6.17%** |

**`ER` lands at 37 of 600 = 6.17%, a 26% relative reduction against `BC`'s 50** — real, and
about two thirds the size of §2's −37.9%. 37 is a count: 34 shared failures judged under this
bar, plus the 3 cells the sweep found failing under `ER` and passing under `BC`.

**37 is a floor, not a point estimate, and the asymmetry is one-directional.** The `bcfail`
block is complete: every cell `BC` pass 2 failed was looked at, and 34 is exact. The other
side is not complete: the 3 `eronly` cells come from the **`ER` sweep, marked on the lenient
footing** — the footing that found 29 `BC` failures where the strict sitting found 50 — and
the 550 cells `BC` pass 2 passed were never re-examined for `ER` failures at all. A strict
sweep of `ER` can only add to 37, never subtract, so 6.17% is the best case for `ER` and the
true figure is somewhere above it.

An earlier draft scaled those 3 by the 1.72× leniency ratio to put an upper end at ~39. That
ratio was measured on `BC`'s two sittings and has not been measured on `ER`; a scaled guess
does not belong beside two counts, and it is dropped.

**What would close it.** Mark `ER`'s own 600 cells in a fresh sitting **against the bar pass 2
used** — ideally interleaved with a `BC` re-mark on the same page so one threshold covers both
arms — and the `eronly` side stops being scaled. Until then the honest form of v3.8's headline
is a range with a measured floor, not a point.

**Two caveats on these passes themselves.** The discordant pass is blind to the arm; the
`bcfail` pass is **not** — left is always `BC`, right is always `ER`, and the reviewer knew it.
It is protected against threshold drift, not against expectation. And both passes are the same
single reviewer whose two `BC` sweeps differ by 1.72×; nothing here is a second pair of eyes.

## 4. The 150-cell prompt comparison (2026-09-10)

**Run.** 450 calls on an A100, 17.9 min, CAD 0.205, plus 300 more for the limb arms
(12.2 min, CAD 0.14). Set: `v36_editset.csv` — the 29 cells `BC` failed and 121 it passed,
sampled `random.Random(46)`. Both sides on purpose: the 29 say what a prompt buys, the 121
say what it costs. Page `v3/report/v36_a100.html`; head-to-head page
`v3/report/v36_er_vs_bc.html`; marks `v3/testsets/v36_er_vs_bc.csv`.

Marked head to head, `ER` was better on **7** cells (6 of them cells `BC` failed), the same
on 1, and **worse on none**. The remaining 142 were left unmarked as showing no difference
worth calling.

`EFR` and `EX` were not adopted: neither beat `ER` on the failure set, `EX` reframes and
invents lower bodies, and one `EFR` regression was seen on a passing cell
(`dualuse_queen_latifah_gown_stage`@47, the wearer's gold coat sleeve surviving). Longer
prompts drift a 4-step distilled model; that is the pattern across `EL`, `EX` and `ERS`.

## 5. The limb clause, measured (2026-09-10)

V2's dynamic-prompt rule — *never name a body part the crop excludes* — has governed call 1
since v3.1 as an assumption. v3.8 measured it on call 2.

**Instrument.** `v3/build/v36_spawn_check.py`. The pose read that **built** the prompt
(`run_v36.limbs`: MediaPipe Pose landmark visibility plus an in-frame coordinate, wrists
15/16, ankles 27/28, foot-index 31/32) is run again over each arm's **output**, so the
measurement and the instruction agree by construction on what "in frame" means. BiRefNet
cannot answer this question at all — a matte is a silhouette with no part labels.

On the **59 of 150 cells whose photograph has no feet in frame**, feet appear in the output:

| arm | cells with invented feet |
|---|---|
| `E0` | 3 (5%) |
| `ER` | 2 (3%) |
| `ERD` (says nothing about feet here) | **2 (3%)** |
| `ERS` (names feet anyway) | **21 (36%)** |

Naming an absent limb raises invented lower bodies roughly twelvefold. It is also the
explanation for the reframing seen in `EL` and `EX`. `v3/runs/v36/a100/meta/spawned_feet.csv`.

**Two controls that make the above readable.**

1. **Determinism.** On the 86 cells where `ERD` and `ERS` were sent *identical text*, the
   outputs are **byte-identical**. Every difference measured in v3.8 is the prompt, not
   sampling noise.
2. **fal is not the A100.** Same prompt, same seed, same canvas rule — and most archived
   `BC` failures do not reproduce on fal (the fal probe, 87 calls, $1.30). Any arm compared
   against a record must run on the hardware the record was made on. This is why every
   number in §2–§4 is A100.

## 6. Seed behaviour of the failures

Both arms' 600 cells are 200 pairs at three seeds, so the record says how much of each
failure rate is a seed lottery rather than a broken pair.

| | `BC` | `ER` |
|---|---|---|
| pairs with at least one failure | 19 / 200 | 14 / 200 |
| pairs failing at **every** seed | 2 (1.0%) | **1 (0.5%)** |
| given a failed cell, another seed of the same pair passes | 34/58 = 59% | 26/36 = **72%** |
| expected residual after one retry at a fresh seed | 2.00% | **0.83%** |

**`ER`'s failures are less clustered**, and that is a property separate from the rate. Given a
pair fails at all, `BC` fails at **1.53** of its three seeds on average and at two or more
**42%** of the time; `ER` fails at **1.29** and at two or more only **21%**. So a retry meets
another failed seed **10/36 = 28%** of the time on `ER` against **24/58 = 41%** on `BC`.

| | `BC` | `ER` |
|---|---|---|
| failed seeds per set, given the set fails at all | 1.53 of 3 | **1.29 of 3** |
| two or more of the three fail | 42% | **21%** |
| all three fail | 11% | **7%** |
| a retry hits another failed seed | 41% | **28%** |
| failure rate after one retry | 4.83% × 41% = 2.00% | 3.00% × 28% = **0.83%** |

**What a randomised seed does not change:** the headline rate itself. A first draw is a random
cell and 3.00% of cells fail; the policy buys the *second* draw. The floor either arm
approaches is the every-seed-failing pairs — whose *reference* is wrong, which no seed repairs.

**The clustering is also why the gain is far short of independence.** If seeds were
independent at 3.00%, a retry would meet a failure 3% of the time rather than 28%, and the
residual would be 0.09% rather than 0.83%. Failures cluster by pair: a cell that failed is
evidence its pair is hard.

Cost of the policy is bounded by the failure rate itself: only rejected images are redrawn,
so one retry adds ~3% to the call count on `ER`. At the measured CAD 0.45 per 1000 images
(call 2 only, references already built) that is not a material cost.

## 7. The VLM defect judge (2026-09-10)

**Instrument.** `v3/build/v36_vlm_defects.py`, gpt-5-mini, three images per call (person,
reference, result), three booleans and nothing else — limb over-count, clothing phasing,
other artifacts. Blind to the arm: the prompt never mentions which produced the result or
that a comparison exists. Both arms over the same 600 cells, **1200 calls, $2.43**.
`v3/runs/v36/ironman_er/meta/vlm_defects.csv`.

| defect | BC | ER | BC-only | ER-only |
|---|---|---|---|---|
| limb over-count | 7 (1.2%) | 9 (1.5%) | 5 | 7 |
| clothing phasing | 116 (19.3%) | **90 (15.0%)** | **72** | 46 |
| other artifacts | 283 (47.2%) | 248 (41.3%) | 108 | 73 |
| any | 297 (49.5%) | 264 (44.0%) | 102 | 69 |

**The instrument's own failure mode, which bounds what may be quoted from it.** Against the
blind human record, the judge's discrimination differs sharply by category:

| flag | fires on the 29 human FAILs | fires on the 571 human passes | lift |
|---|---|---|---|
| limb over-count | 10.3% | 0.7% | **14.8×** |
| phasing | 48.3% | 17.9% | 2.7× |
| artifacts | 86.2% | 45.2% | 1.9× |

The **artifacts** flag fires on 45% of cells a human passed: it is scoring "a seam is visible
if I look hard", not "this failed". Its marginal rate is meaningless as a quality number and
its McNemar row is directional at best. **Limb over-count** is the sharpest discriminator any
instrument in this project has produced, but at 7–9 events per 600 it cannot power a
comparison. **Phasing** is the one category with both usable discrimination and enough
events: 72-against-46 in `ER`'s favour, and it is precisely the class the verb change
targets — the wearer's own clothing surviving underneath.

The judge's paired direction agrees with the human record on the two categories it measures
usably, which is corroboration, not confirmation: the same 600 cells were judged by both, so
the two results are not independent.

## 8. Cost, measured

| | |
|---|---|
| `ER` call 2, median | 2.28 s (mean 2.37 s) |
| `BC` call 2, mean | 2.40 s |
| a 600-cell arm, self-hosted A100 @ CAD 0.689/h | CAD 0.273 (`BC`: 0.277) |
| the same 600 calls on fal | USD 9.00 |
| **per 1000 finished images**, references already built | **CAD 0.45** — USD 15.00 on fal |
| per 1000 including reference build, at this fold's ratio (93 references) | CAD 0.54 (GPU crops) / CAD 0.78 (CPU crops) |
| klein load, once per session | 354 s ≈ CAD 0.07 |

`ER` adds no call, no model and no measurable time: the difference against `BC` is one verb.

## 9. Evidence paths

| what | where |
|---|---|
| `ER` iron-man run | `v3/runs/v36/ironman_er/`, Drive `v3_runs/v36_ironman_er_20260910_2259.zip` |
| the 150-cell prompt run | `v3/runs/v36/a100/`, Drive `v3_runs/v36_editprompts_*.zip`, `v36_limbclause_*.zip` |
| blind counts | `v3/testsets/bc_count.csv` (`BC` pass 1), `v3/testsets/bc2_count.csv` (`BC` pass 2), `v3/testsets/er_count.csv` |
| blind discordant pass | `v3/testsets/v36_discordant.csv`, page `v3/report/v36_discordant.html`, built by `v3/build/v36_discordant_page.py` |
| `BC`-failure side-by-side pass | `v3/testsets/v36_bcfail.csv`, page `v3/report/v36_bcfail.html`, built by `v3/build/v36_bcfail_page.py` |
| head-to-head marks | `v3/testsets/v36_er_vs_bc.csv` |
| invented-limb measurement | `v3/runs/v36/a100/meta/spawned_feet.csv` |
| VLM defect judge | `v3/runs/v36/ironman_er/meta/vlm_defects.csv` |
| pages | `v3/report/er_count.html`, `v36_a100.html`, `v36_er_vs_bc.html`, `v36_discordant.html`, `v36_bcfail.html`, `v36_report.html`, `v36_findings.html` |
