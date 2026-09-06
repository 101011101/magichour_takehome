# VEi vs VE vs VS on the v3.4 failure set — blind VLM judge (2026-09-06)

**Claim under test.** "VEi (small-canvas reference, SR after call 1 — link H) is better than
VE (klein-upscaled reference, link E) and VS (SR inputs, link G)." Reviewer, 2026-09-06:
"it looks pretty good for VEi" (RESULTS.md §9).

**Verdict.** The blind judge supports half the claim. **VEi is clearly better than VS**:
+0.125 fidelity (3.81 vs 3.69, 95% CI [+0.04, +0.23], permutation p = 0.008), 23 pairs to 7,
and the pair-win margin (+16) has permutation p = 0.003 — outside the seed-noise envelope
(95% of |null| < 0.09; same-arm seed splits reach at most 0.12). **VEi is not better than VE**:
it is 0.068 *behind* on fidelity (3.81 vs 3.88, CI [−0.14, +0.01], perm p = 0.093 — inside the
noise envelope) and loses 21 pairs to 10; on realism (−0.093, sign p = 0.036) and the mean of
six (−0.081, perm p = 0.030) the deficit is marginally outside noise, driven by `hands`
(−0.151, CI excluding zero), not by garment correctness (−0.097, n.s.). The judge's ordering
is **VE ≥ VEi > VS**. VEi does hold `g027+p003` at all three seeds (fid 3.78 vs VS 2.78, its
largest single-pair edge, +1.00) — the footprint result of §9 stands — but VE holds it too,
and slightly better (4.00). VEi buys nothing over VE on this set; its case over VE has to be
cost (cheapest 1 MP arm, 4.4 s/pair) or the g027 framing at V34-exact reference content, not
judged quality.

## 1. Setup

| | |
|---|---|
| pairs | 31, `v3/testsets/v34_failures.csv` (F1 9, F2 8, F3 12, F4 2; 4 seed-stable) |
| VEi arm | `v3/runs/v34/v34_a100_vei_20260906_0334/gen/{set_id}__VEi__s{49,50,51}.jpg` — link H, small-canvas ref + SR after call 1 |
| VE arm | `v3/runs/v34/v34_a100_ve_20260904_0611/gen/{set_id}__VE__s{49,50,51}.jpg` — link E, klein-upscaled reference |
| VS arm | `v3/runs/v34/v34_a100_vs_20260905_0550/gen/{set_id}__VS__s{49,50,51}.jpg` — link G, SR inputs |
| pipeline | all three A100, same locked pipeline and the same seeds 49/50/51 — arms differ only in the reference recipe, so cells pair seed-for-seed |
| inputs | `v3/runs/ironman/20260830_0548/inputs/` (symlinked as `inputs/`) |
| judge | `v3/build/ironman_vlm.py::score()`, **gpt-5.5** via the Responses API, 8 workers, the six 1–5 criteria + note per cell, three images per call (person, garment, result) downscaled to 768 px; note cap raised 300→2000 chars from the start (`run_judge.py`), the fix judge_fal_vs_a100 needed mid-run — prompt, model, images, scoring otherwise identical |
| blinding | the judge sees only the three images; arm names live in the filenames, which are never sent (same method as judge_fal_vs_a100) |
| cells | 31 pairs × 3 seeds × 3 arms = **279, all scored** in one segment (no budget stop, no schema failures) |

Rubric (verbatim from `ironman_vlm.py`, the judge of record; RESULTS.md §9 calls it the
"five-metric judge" but the schema has six criteria): **garment** = is the output garment
exactly the reference (color, print, cut, every piece); **identity** = same face/hair/body as
image 1; **scene** = pose and background unchanged from image 1; **clean** = free of AI
artifacts in skin, seams and textures (extra limbs or feet count here); **hands** = hands
specifically are anatomically correct — score 5 if no hands are visible; **realism** = the
image reads as a real photograph rather than an AI render. fidelity = mean(garment, identity,
scene); realism axis = mean(clean, hands, realism); fidelity first, realism breaks ties
(SCORING_CRITERIA §4).

## 2. Paired differences (unit = pair; each arm's value is the mean of its 3 seeds; n = 31)

Bootstrap CI: 20,000 resamples over pairs. Permutation: within each pair, which 3 of its 6
cells carry the first arm's label is reshuffled (20,000 shuffles) — the "arm is just another
seed" null, as in judge_fal_vs_a100.

**VEi − VE** (the candidate against the incumbent recipe):

| metric | VEi | VE | diff | 95% CI | pairs +/−/0 | sign p | Wilcoxon p | perm p (2-sided) |
|---|---|---|---|---|---|---|---|---|
| **fidelity** | 3.810 | 3.878 | **−0.068** | [−0.143, +0.007] | 10 / 18 / 3 | 0.185 | 0.135 | 0.093 |
| **realism** | 3.692 | 3.785 | **−0.093** | [−0.176, −0.014] | 8 / 20 / 3 | 0.036 | 0.030 | 0.073 |
| mean of 6 | 3.751 | 3.832 | −0.081 | [−0.149, −0.013] | 10 / 18 / 3 | 0.185 | 0.032 | 0.030 |
| garment | 2.602 | 2.699 | −0.097 | [−0.215, +0.022] | 4 / 10 / 17 | 0.180 | 0.225 | |
| identity | 4.247 | 4.301 | −0.054 | [−0.194, +0.075] | 9 / 10 / 12 | 1.000 | 0.277 | |
| scene | 4.581 | 4.634 | −0.054 | [−0.172, +0.054] | 6 / 9 / 16 | 0.607 | 0.411 | |
| clean | 3.570 | 3.645 | −0.075 | [−0.215, +0.054] | 7 / 9 / 15 | 0.804 | 0.416 | |
| hands | 3.667 | 3.817 | **−0.151** | [−0.290, −0.022] | 5 / 14 / 12 | 0.064 | 0.061 | |
| realism | 3.839 | 3.892 | −0.054 | [−0.172, +0.065] | 7 / 10 / 14 | 0.629 | 0.202 | |

Pair winners: **VE 21 · VEi 10 · tie 0** (win margin −11, perm p = 0.066, null SD 5.6).
Cross-seed 3×3 cells (279): VEi 94 · VE 147 · tie 38. Same-seed cells (93): VEi 29 · VE 48 · tie 16.
VE wins all 9 cross-seed comparisons on 5 pairs (`kimono+g024`, `g029+p004`, `p003+p026`,
`p011+p024`, `p020+navy_peacoat`); VEi on none.

**VEi − VS**:

| metric | VEi | VS | diff | 95% CI | pairs +/−/0 | sign p | Wilcoxon p | perm p (2-sided) |
|---|---|---|---|---|---|---|---|---|
| **fidelity** | 3.810 | 3.685 | **+0.125** | [+0.036, +0.229] | 20 / 6 / 5 | 0.009 | 0.033 | 0.008 |
| **realism** | 3.692 | 3.591 | **+0.100** | [−0.014, +0.233] | 16 / 12 / 3 | 0.572 | 0.198 | 0.094 |
| mean of 6 | 3.751 | 3.638 | +0.113 | [+0.022, +0.220] | 20 / 8 / 3 | 0.036 | 0.029 | 0.011 |
| garment | 2.602 | 2.505 | +0.097 | [−0.043, +0.237] | 12 / 9 / 10 | 0.664 | 0.165 | |
| identity | 4.247 | 4.097 | **+0.151** | [+0.032, +0.269] | 15 / 5 / 11 | 0.041 | 0.056 | |
| scene | 4.581 | 4.452 | +0.129 | [−0.054, +0.344] | 11 / 9 / 11 | 0.824 | 0.542 | |
| clean | 3.570 | 3.495 | +0.075 | [−0.054, +0.215] | 10 / 8 / 13 | 0.815 | 0.175 | |
| hands | 3.667 | 3.667 | 0.000 | [−0.194, +0.247] | 7 / 11 / 13 | 0.481 | 0.568 | |
| realism | 3.839 | 3.613 | **+0.226** | [+0.086, +0.366] | 14 / 3 / 14 | 0.013 | 0.015 | |

Pair winners: **VEi 23 · VS 7 · tie 1** (win margin +16, perm p = 0.003, null SD 5.5).
Cross-seed cells: VEi 150 · VS 92 · tie 37. Same-seed cells: VEi 53 · VS 27 · tie 13.
VEi wins all 9 on 4 pairs (`g004+g005`, `g005+g014`, `g027+p003`, `p011+p024`); VS on 1 (`p003+p026`).

**VE − VS** (context): VE +0.194 fidelity [+0.10, +0.31], perm p < 0.001, 24 pairs to 7 —
the incumbent beats VS even more clearly than VEi does; the three-arm ordering is consistent.

## 3. Is the gap inside seed noise? (the judge_fal_vs_a100 yardstick)

- Within-pair across-seed SD of fidelity: VEi 0.216, VE 0.214, VS 0.268 (prior run: 0.237/0.241).
- Same-arm seed-vs-seed splits (fresh-draw baseline, 31 comparisons each): fid diffs range
  −0.097…+0.118 (|max| 0.118: VEi s50 vs s51 at 18/11/2), prior run's max was 0.161.
- Permutation null: SD 0.038–0.058 per metric; 95% of |null| < 0.075 (fid, VEivVE),
  < 0.090 (fid, VEivVS).

**VEi vs VE: inside noise on fidelity, at the edge beyond it on realism.** The −0.068 fid gap
is under the 95% permutation envelope (0.075), the same size as one seed split (−0.097…+0.118),
and its CI covers zero. The mean-of-6 (−0.081, perm p = 0.030) and realism-axis (−0.093, sign
p = 0.036, CI excluding zero) deficits are marginally outside — if anything is real it is a small
hands/cleanliness cost of the SR step, ~0.1 of a scale point, not a garment or identity effect.
By the prior report's standard ("not distinguishable from a fresh draw") VEi is at best tied
with VE and the evidence leans worse, never better.

**VEi vs VS: outside noise.** +0.125 fid exceeds the 95% envelope (0.090) and every same-arm
seed split; perm p = 0.008 on fidelity, 0.003 on the pair-win margin, and the bootstrap CI
excludes zero on fid, mean6, identity and realism.

## 4. Per class (fidelity)

| class | n | VEi | VE | VS | VEi−VE | CI | wins (VEi/VE/tie) | VEi−VS | CI | wins (VEi/VS/tie) |
|---|---|---|---|---|---|---|---|---|---|---|
| F1 wearer's clothing survives | 9 | 3.80 | 3.96 | 3.68 | −0.16 | [−0.31, −0.01] | 2 / 7 / 0 | +0.12 | [−0.06, +0.33] | 5 / 3 / 1 |
| F2 skirt/dress → trousers | 8 | 3.69 | 3.69 | 3.65 | 0.00 | [−0.17, +0.14] | 4 / 4 / 0 | +0.04 | [−0.08, +0.14] | 6 / 2 / 0 |
| F3 reference drift | 12 | 3.91 | 3.94 | 3.81 | −0.03 | [−0.13, +0.07] | 4 / 8 / 0 | +0.10 | [−0.01, +0.20] | 10 / 2 / 0 |
| F4 exposed skin | 2 | 3.72 | 3.89 | 3.11 | −0.17 | [−0.22, −0.11] | 0 / 2 / 0 | +0.61 | [+0.22, +1.00] | 2 / 0 / 0 |

F1 is where VEi loses to VE (CI excludes zero at n = 9); F2/F3 are dead heats. Cell-level fail
proxy (garment ≤ 2 or clean ≤ 2): VEi 48/93, VE 45/93, VS 52/93 — no arm moves the failure
classes; garment means are 2.5–2.7 on all three. Seed-stable pairs stay failed on all arms
(garment means 1.3–2.7).

## 5. Notable pairs (3-seed means, fid/realism-axis)

- **`g027+p003`** (F4, the framing/dwarfism pair): VEi 3.78/3.89, VE 4.00/3.89, **VS 2.78/2.44**.
  VEi beats VS by +1.00 fid — its largest edge anywhere, all 9 cross-seed cells — the judge
  sees VS lose the crop/pose ("crop and pose change significantly", "retains the Ramones
  graphic") while VEi and VE hold the white-background waist-up frame. But **VE wins the pair**
  over VEi (fid 4.00 vs 3.78): §9's "second recipe ever to hold it" is confirmed, "better
  than VE at it" is not.
- **`g029+p004`** (F2): VEi's worst loss — 3.44 vs VE 3.89 (VE wins all 9 cross-seed cells)
  and vs VS 3.78. Garment is 1–2 on *all* arms (the white tee never transfers; the houndstooth
  blazer survives everywhere); VEi additionally invents a "light blue hybrid jacket" (garment 1
  at s49/s51). VEi is strictly the worst arm on this pair.
- **`p019+dualuse_gal_gadot_blue_dress_redcarpet`** (F4): VE 3.78 > VEi 3.67 > VS 3.44. The
  gown fails identically on all three (garment 1–2 every cell; "beige collar/sleeves remain,
  cutout/slit/skirt missing"). VS's fal-run first-ever success did not transfer to the A100;
  VEi does not fix this pair either.
- **`p015+p016`** (F3): exact three-way fidelity tie at 3.78. Realism tiebreaks: VE 4.00 >
  VEi 3.89 > VS 3.67, so the pair goes to VE over VEi and to VEi over VS. Garment 1–3 on all
  arms (the ruffled-hem dress becomes a plain yellow top everywhere).

## 6. Spend

| | |
|---|---|
| scored calls | 279 (all cells, one segment), tokens **481,545 in / 111,038 out** (exact, from the API `usage` field) |
| cost | **$4.07** at the `PRICE` table in `ironman_vlm.py` (gpt-5.5: $5 / $15 per M); $0.0146 per cell; no retries, no unscored cells |
| | verify the $/M rates against the current OpenAI price list before quoting the dollar figure; the token counts are the numbers of record |

## 7. Caveats

- Same single-judge/prompt caveats as judge_fal_vs_a100 §8: one judge, temperature not
  pinned, per-cell noise absorbed into the seed spread by the pair-level analysis.
- All three arms share seeds 49/50/51, so "same-seed" pairing is exact (stronger than the
  prior report's position-pairing across different seed numbers); the permutation null is
  computed the same way regardless.
- VEi is the newest run (2026-09-06) but the judge saw all 279 cells interleaved in one
  blinded batch; no ordering by arm.
- n = 31: a true VEi−VE fidelity difference of ~±0.07 cannot be separated from zero at this
  size (the prior report's power table applies).

## Files

- `meta/vlm_scores.csv` — 279 judged cells (scores, note, seconds, tokens)
- `meta/per_pair.csv` — per-pair 3-seed means per arm, diffs, winners, cross-seed and same-seed win counts for all three comparisons
- `meta/analysis.json`, `meta/analysis_stdout.txt` — everything in §2–5 incl. permutation nulls and seed splits (`analyse.py`)
- `meta/score_log.txt` — the judge run log; `run_judge.py` — the runner (note cap 300→2000 only)
- `gen/` — 279 symlinks into the three run dirs, arm in the filename; `inputs/` → the iron-man inputs
