# fal vs self-hosted A100 on the v3.3 failure set — blind VLM judge (2026-08-31)

**Claim under test.** "fal's outputs are better than our self-hosted A100 outputs on the same pairs."

**Verdict.** On the 31 failure-set pairs the blind judge scores fal **+0.09 on fidelity** (1–5 scale;
FAL 3.87 vs A100 3.78) and **+0.05 on realism** (3.66 vs 3.60), with fal winning 19 pairs to 12
on fidelity-first-then-realism. **Neither difference is statistically distinguishable from a fresh
draw of the same model**: the fidelity 95% bootstrap CI is [−0.01, +0.20], sign test p = 0.15,
Wilcoxon p = 0.13, within-pair label-permutation p = 0.055 (two-sided); realism CI [−0.08, +0.20],
sign p = 1.0, permutation p = 0.39. The win margin (+7 pairs) has permutation p = 0.24. The
backend gap (+0.09 fidelity) is the same size as the gap between two seeds of the *same* backend
(A100 s49 vs s51: +0.16; A100 s49 vs s50: +0.09) and well below the within-pair seed-to-seed
spread (SD 0.24 on both backends). On the garment criterion — the one the failure classes are about
— A100 is marginally *ahead* (2.76 vs 2.70, n.s.), and the fail proxy (garment ≤ 2 or clean ≤ 2) is
**41/93 cells on both arms**. Fal is at most slightly better on identity/scene preservation
(+0.16, +0.17; CIs touch zero), not on the try-on itself.

So: fal is not better on these pairs in any way that separates it from a re-roll of the seeds.
If the effect is real it is ≤ 0.2 of a scale point on fidelity, and zero on garment correctness.

## 1. Setup

| | |
|---|---|
| pairs | 31, `v3/testsets/v34_failures.csv` (F1 9, F2 8, F3 12, F4 2; 4 seed-stable) |
| FAL arm | `v3/runs/v34/linkA/gen/{set_id}__Vnc__s{46,47,48}.jpg` — fal `fal-ai/flux-2/klein/4b/distilled/edit` |
| A100 arm | `v3/runs/v34/v34_a100_nocut_20260901_0323/gen/{set_id}__Vnc__s{49,50,51}.jpg` — A100-40GB, klein 4B bf16 |
| pipeline | same locked v3.3 pipeline, no ankle cut, on both; only backend and seed numbers differ |
| inputs | `v3/runs/ironman/20260830_0548/inputs/` (symlinked as `inputs/`) |
| judge | `v3/build/ironman_vlm.py::score()`, **gpt-5.5** via the Responses API, 8 workers, six 1–5 criteria + note per cell, three images per call (person, garment, result) downscaled to 768 px |
| blinding | the judge sees only the three images; arm names live in the filenames (`{set_id}__FAL__s46.jpg`, `{set_id}__A100__s49.jpg`), which are never sent |
| cells | 31 pairs × 3 seeds × 2 arms = **186, all scored** (no budget stop) |

The 30 controls were not judged: fal and A100 control outputs exist (`linkB_controls`, the A100
run), but 180 more cells (~$2.9) would have crossed the $5 cap.

**One run-time fix.** `ironman_vlm.py` caps `note` at 300 characters; gpt-5.5 writes ~350-char
notes, so 8 of the first 65 cells failed schema validation three times each and were left
unscored (the six integer scores were valid every time — verified on one raw response). The run
was stopped at 65 scored cells and resumed with `run_judge.py`, which imports the judge unchanged
and only raises the note cap to 2000. Prompt, model, images and scoring are identical across the
two segments; `meta/vlm_scores.csv` holds all 186 rows.

## 2. Paired difference FAL − A100 (unit = pair; each arm's value is the mean of its 3 seeds)

fidelity = mean(garment, identity, scene); realism = mean(clean, hands, realism). n = 31 pairs.
Bootstrap CI: 20,000 resamples over pairs. Sign test: exact binomial on non-zero differences.
Wilcoxon: signed-rank, zeros dropped. Permutation: within each pair, which 3 of its 6 cells are
labelled FAL is reshuffled (20,000 shuffles) — the "backend is just another seed" null.

| metric | FAL | A100 | diff | 95% CI | pairs +/−/0 | sign p | Wilcoxon p | perm p (2-sided) |
|---|---|---|---|---|---|---|---|---|
| **fidelity** | 3.867 | 3.778 | **+0.090** | [−0.011, +0.201] | 16 / 8 / 7 | 0.152 | 0.133 | 0.055 |
| **realism** | 3.656 | 3.602 | **+0.054** | [−0.079, +0.197] | 14 / 14 / 3 | 1.000 | 0.576 | 0.392 |
| mean of 6 | 3.762 | 3.690 | +0.072 | [−0.027, +0.186] | 15 / 15 / 1 | 1.000 | 0.416 | 0.111 |

Per criterion:

| criterion | FAL | A100 | diff | 95% CI | pairs +/−/0 | sign p | Wilcoxon p |
|---|---|---|---|---|---|---|---|
| garment | 2.699 | 2.763 | −0.065 | [−0.237, +0.097] | 8 / 13 / 10 | 0.383 | 0.550 |
| identity | 4.301 | 4.140 | +0.161 | [−0.000, +0.344] | 9 / 3 / 19 | 0.146 | 0.123 |
| scene | 4.602 | 4.430 | +0.172 | [−0.011, +0.398] | 11 / 7 / 13 | 0.481 | 0.137 |
| clean | 3.484 | 3.484 | 0.000 | [−0.172, +0.172] | 9 / 9 / 13 | 1.000 | 0.809 |
| hands | 3.688 | 3.613 | +0.075 | [−0.118, +0.312] | 10 / 8 / 13 | 0.815 | 0.840 |
| realism | 3.796 | 3.710 | +0.086 | [−0.054, +0.226] | 9 / 6 / 16 | 0.607 | 0.128 |

Reading: the whole fidelity gap comes from identity and scene (the person and background being
left alone), where fal is ~0.17 higher with CIs that touch zero; on garment — the criterion that
defines F1/F2/F3 — A100 is 0.06 ahead and it is noise. Cell-level fail proxy (garment ≤ 2 or
clean ≤ 2): **FAL 41/93, A100 41/93**.

## 3. Win counts (fidelity first, realism breaks ties)

| comparison | FAL | A100 | tie |
|---|---|---|---|
| per pair, on 3-seed means (31) | **19** | **12** | 0 |
| every FAL cell vs every A100 cell of the same pair, 3×3 (279) | 148 (53%) | 96 (34%) | 35 |
| position-paired cells 46↔49, 47↔50, 48↔51 (93) | 52 | 30 | 11 |

The +7 pair margin has permutation p = 0.24 two-sided (null SD 5.5 pairs).

**Fresh-draw baseline — the same win split between two seeds of the same backend** (31
comparisons each, first-listed seed / second / tie, mean fidelity difference):

| split | first | second | tie | fid diff |
|---|---|---|---|---|
| A100 s49 vs s50 | 13 | 11 | 7 | +0.086 |
| A100 s49 vs s51 | 17 | 8 | 6 | +0.161 |
| A100 s50 vs s51 | 13 | 11 | 7 | +0.075 |
| FAL s46 vs s47 | 13 | 13 | 5 | −0.032 |
| FAL s46 vs s48 | 17 | 11 | 3 | +0.011 |
| FAL s47 vs s48 | 12 | 11 | 8 | +0.043 |
| FAL s46 vs A100 s49 | 17 | 12 | 2 | 0.000 |
| FAL s47 vs A100 s50 | 16 | 11 | 4 | +0.118 |
| FAL s48 vs A100 s51 | 19 | 7 | 5 | +0.151 |

A100 seed 49 "beats" A100 seed 51 by 17–8 and +0.16 fidelity — a bigger margin than fal's over the
A100 on two of the three position-paired splits. Mean within-pair across-seed SD of fidelity:
FAL 0.237, A100 0.241; the backend difference (0.09) is ~0.4 of one seed's noise.

**Pairs where one backend wins at all three seeds.**
- FAL wins all 9 cross-seed cell comparisons (every FAL cell beats every A100 cell): 4 pairs —
  `dualuse_hugh_jackman_grey_suit_outdoor+dualuse_zendaya_white_blazer_skirt` (F2),
  `dualuse_scarlett_johansson_black_dress_backview_night+dualuse_woman_top_denim_skirt_nonceleb` (F3),
  `g027+p003` (F4), `p013+dualuse_scarlett_johansson_black_dress_backview_night` (F2).
- A100 wins all 9: **none** (closest: `g029+p004`, 0/8/1).
- Position-paired, FAL wins 3/3: the four above plus `dualuse_emma_watson_black_blazer_armscrossed+dualuse_scarlett_johansson_black_dress_backview_night`, `g004+g005`, `p011+p024` (7 pairs).
- Position-paired, A100 wins 3/3: `dualuse_lp_plaid_overcoat_brown_suit+g029`, `g029+p004` (2 pairs).

Note the four all-9 fal pairs: `hugh+zendaya` (fid 4.00 vs 3.67) is a seed-stable failure on both —
fal is "better" at rendering the wrap skirt as trousers, not at fixing it; `g027+p003` (F4, +1.11) is
the single largest gap in the set and is the one pair where the judge sees a real quality
difference (A100 fid 2.67, real 2.67).

## 4. Per class

| class | n | FAL fid | A100 fid | diff | 95% CI | sign p | FAL real | A100 real | diff | wins FAL/A100/tie |
|---|---|---|---|---|---|---|---|---|---|---|
| F1 wearer's clothing survives | 9 | 3.89 | 3.75 | +0.14 | [+0.04, +0.25] | 0.12 | 3.60 | 3.54 | +0.06 | 8 / 1 / 0 |
| F2 skirt/dress → trousers | 8 | 3.78 | 3.71 | +0.07 | [−0.14, +0.26] | 1.00 | 3.64 | 3.61 | +0.03 | 4 / 4 / 0 |
| F3 reference drift | 12 | 3.91 | 3.93 | −0.02 | [−0.14, +0.10] | 1.00 | 3.70 | 3.73 | −0.03 | 5 / 7 / 0 |
| F4 exposed skin | 2 | 3.89 | 3.28 | +0.61 | [+0.11, +1.11] | 0.50 | 3.67 | 3.06 | +0.61 | 2 / 0 / 0 |

F1 is the only class with a CI excluding zero (n = 9, 8 wins of 9, but sign p = 0.12 and the
margin is 0.14 — and the F1 garment scores are 2.0–3.0 on both arms, i.e. the leak is there on
both; fal scores higher on identity/scene around the leak). F3, the largest class, is a dead heat
tilted to the A100. F4 is two pairs.

Seed-stable pairs (the reviewer's "fail at every seed on every backend"), garment mean FAL / A100:
`emma+scarlett` 3.00 / 2.67 · `hugh+zendaya` 2.67 / 2.00 · `kimono+g005` 2.00 / 2.00 · `kimono+g024` 2.67 / 2.67.
The judge sees the same failure on both backends in all four.

## 5. `dualuse_lp_floral_kimono_set+g024` — all six cells

The reviewer's claim: fal passed at seeds 46 and 48, the A100 failed every seed. The judge, blind:

| cell | garment | identity | scene | clean | hands | realism | fid | real | note |
|---|---|---|---|---|---|---|---|---|---|
| FAL s46 | 3 | 4 | 4 | 4 | 4 | 4 | 3.67 | 4.00 | Reference sweater and blue pleated skirt are mostly transferred, but shoes are wrong, **original hat/bag/sandals remain**, and cut/proportions differ. Identity and pose/background are largely preserved with minor AI softness and slight foot/texture issues. |
| FAL s47 | 3 | 4 | 4 | 3 | 4 | 3 | 3.67 | 3.33 | Sweater and blue pleated skirt are recognizable, but proportions differ and reference white sneakers are missing; identity and pose are mostly preserved, with some odd layering/artifacts around the lower body. |
| FAL s48 | 2 | 4 | 4 | 3 | 3 | 3 | 3.33 | 3.00 | Reference sweater and blue pleated skirt are partially transferred, but **original floral cuffs/bag/sandals remain** and sneakers are missing; garment details are fused and inconsistent. Identity and studio background are mostly preserved, with some hand/texture artifacts. |
| A100 s49 | 3 | 4 | 4 | 4 | 3 | 4 | 3.67 | 3.67 | Reference sweater and blue pleated skirt are mostly transferred, but sweater cut/sleeves are distorted, shoes are not the reference sneakers, and **original bag remains**. Identity and studio scene are largely preserved, with minor body-shape changes. Hands are visible and somewhat awkward, especially near the skirt/bag. |
| A100 s50 | 2 | 4 | 5 | 3 | 4 | 4 | 3.67 | 3.67 | Reference sweater and blue pleated skirt are partially matched, but output **keeps original hat, bag, sandals** and adds loose blue pants instead of bare legs/white sneakers. Pose and plain studio background are essentially unchanged; identity is mostly preserved. Some awkward layering and fabric transitions reduce cleanliness. |
| A100 s51 | 3 | 4 | 4 | 3 | 4 | 4 | 3.67 | 3.67 | Top and blue pleated skirt resemble the reference, but shoes are wrong, **original hat/bag remain**, and sleeves/foot area are distorted. Identity and studio pose/background are mostly preserved. |

Pair means: fidelity FAL 3.56 vs A100 3.67, realism 3.44 vs 3.67 — **A100 ahead on both**;
cross-seed cells 3 FAL / 6 A100 / 0 tie. The judge calls the F1 leak (hat, bag, sandals or cuffs
of the kimono set surviving) in **all six cells**, including fal seeds 46 and 48, and gives fal s48
the lowest garment score of the six. This does not support "fal passed at 46 and 48"; it agrees
with the repo's own link-A record (`prd/v3/v3.4/RESULTS.md` §1.1: F1 "identical failure: the
kimono sleeves, hat and bag … are there in both") and §3.1 (still fails at 49/50/51).

## 6. Sanity — does the judge track the reviewer?

No cell-level overlap exists: `v33_ironman_votes_bca4.csv` covers the original A100 seeds
46/47/48 with the ankle cut (V vs BC), which are different images from both arms here. The one
available check is pair-level: the reviewer's count of "fail" verdicts per pair on the original run
(0–3, from `v34_failures.csv`) against the judge's garment mean over both arms:

| original fails | pairs | judge garment mean |
|---|---|---|
| 0 | 16 | 3.04 |
| 1 | 10 | 2.47 |
| 2 | 2 | 2.17 |
| 3 | 3 | 2.33 |

Spearman ρ = −0.56, p = 0.001. The judge's garment score orders pairs the way the reviewer's
failure counts do, on fresh images of the same pairs. Spot checks against the reviewer's §3.1
notes: `g005+g014` (reviewer: passes 1 of 3 — shorts leak at 49, split at 50) — judge garment A100
s49 = 2 ("camisole with shorts and only a partial skirt panel"), s50 = 2 ("shorts remain"), s51 = 4;
`p025+zendaya` (trousers at all new seeds) — garment 2 at every A100 seed and 2 at every fal seed.

## 7. Spend

| | |
|---|---|
| scored calls | 186 (all cells), tokens **355,353 in / 83,180 out** (exact, from the API `usage` field) |
| cost of scored calls | **$3.02** at the `PRICE` table in `ironman_vlm.py` (gpt-5.5: $5 / $15 per M tokens); $0.0163 per cell |
| wasted calls | 24 retry attempts on the 8 note-cap failures + ≤ 8 in-flight calls lost at the stop + 1 diagnostic probe (1,845 / 381 tokens) ≈ 33 calls, tokens not recorded, ≈ $0.54 at the same average |
| **total** | **≈ $3.56** (bound ≤ $3.6) of the $5 cap; nothing scored after the cap. Verify the $/M rates against the current OpenAI price list before quoting the dollar figure; the token counts are the numbers of record |

## 8. Caveats

- One judge, one prompt, temperature not pinned; the judge is harsh on garment across the board
  (mean 2.7 — this is the failure set) and lenient on identity/scene. Its per-cell noise is not
  measured here (no repeat calls); the pair-level analysis absorbs it as part of the seed spread.
- The identity/scene edge for fal (+0.16/+0.17) is consistent with the earlier observation that
  A100 frames "differ in framing detail" from fal's at the same prompt (RESULTS commit 40f96ed).
  If real, it is a small preservation difference in the sampler path, not better try-on.
- The set is selected on A100 failures at seeds 46–48; both arms here are fresh draws, so
  regression to the mean applies equally to both, which is what the same-backend seed splits show.
- n = 31 pairs with the observed paired SD of the fidelity difference (0.30) gives 77% power at
  α = 0.05 for a true difference of 0.15, 58% for 0.12 and 44% for 0.10 (paired t); a true fal
  advantage of ~0.1 cannot be excluded, but neither can zero.

## Files

- `meta/vlm_scores.csv` — 186 judged cells (scores, note, seconds, tokens)
- `meta/per_pair.csv` — per-pair means, diffs, winners, cross-seed and position-paired win counts
- `meta/analysis.json`, `meta/analysis_stdout.txt` — everything in §2–6 (`analyse.py`)
- `meta/null.json`, `meta/null_stdout.txt` — permutation null and seed splits (`null.py`)
- `meta/score_log.txt` — both judge segments; `run_judge.py` — the resume wrapper (note cap only)
- `gen/` — 186 symlinks, arm in the filename; `inputs/` → the iron-man inputs
