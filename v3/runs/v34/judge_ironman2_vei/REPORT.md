# Iron man 2, arm VEi, full 200-pair matrix — absolute VLM scoring vs the v3.3 record (2026-09-07)

**Question.** Where does the VEi arm stand on the full matrix, judged absolutely, and how does
it compare with the v3.3 lock's scored record? Context: the reviewer's eyeball impression of
iron man 2 is "bad".

**Verdict (short).** VEi lands ~0.1 fidelity behind the v3.3 lock's record (3.88 vs 3.99;
−0.094 on matched cells) — at the edge of calibration noise, and the deficit sits in
identity/scene, not garment. Absolute quality is mediocre on garment correctness for *both*
arms (garment mean ~3.0, zero pairs perfect); the "bad" impression is real for garment
transfer but is a property of the system on this matrix, not a VEi regression. Details in §6.

## 1. Setup

| | |
|---|---|
| cells | `v3/runs/v34/ironman2/gen/{set_id}__VEi__s{46,47,48}.jpg` — 200 pairs × 3 seeds = **600, all scored** (no budget stop, no schema failures, no unscored cells) |
| matrix | `v3/colab/matrix.csv` (200 pairs); inputs `v3/runs/v34/ironman2/inputs/{id}.jpg`, resolved by id |
| judge | `v3/build/ironman_vlm.py::score()`, **gpt-5.5** via the Responses API, 8 workers, six 1–5 criteria + note per cell, three images per call (person, garment, result) downscaled to 768 px; note cap raised 300→2000 from the start (`run_judge.py`, same as judge_vei / judge_fal_vs_a100) — prompt, model, images, scoring otherwise identical to the judge of record |
| blinding | single-arm absolute scoring; the judge sees only the three images, the arm name is never sent |
| baseline | `v33_ironman_vlm_scores_bca4.csv` (repo root), arm **V** = the v3.3 lock: **396 cells over 199 pairs** — seeds 46 (179), 47 (181), 48 (36 only; that run budget-stopped before seed 48 finished). Scored by an earlier run of the same judge family, so small calibration drift is possible; deltas < ~0.1 are treated as within calibration noise |

fidelity = mean(garment, identity, scene). Fail proxy (project convention): garment ≤ 2 or clean ≤ 2.

## 2. Per-criterion means

Full-set = VEi over all 600 cells vs V over its 396. Matched = both arms restricted to the
identical 396 (pair, seed) cells the baseline scored — the fair cut, since V's seed-48
coverage is thin.

| criterion | VEi (600) | V (396) | delta | VEi matched | V matched | delta |
|---|---|---|---|---|---|---|
| garment | 2.970 | 3.025 | −0.055 | 2.997 | 3.025 | −0.028 |
| identity | 4.177 | 4.308 | **−0.131** | 4.194 | 4.308 | −0.114 |
| scene | 4.505 | 4.636 | **−0.131** | 4.495 | 4.636 | −0.141 |
| clean | 3.780 | 3.768 | +0.012 | 3.775 | 3.768 | +0.008 |
| hands | 3.807 | 3.846 | −0.039 | 3.816 | 3.846 | −0.030 |
| realism | 3.930 | 3.944 | −0.014 | 3.934 | 3.944 | −0.010 |
| **fidelity** | **3.884** | **3.990** | **−0.106** | **3.896** | **3.990** | **−0.094** |
| mean of 6 | 3.861 | 3.921 | −0.060 | | | |

Paired per-pair fidelity (n = 199 shared pairs, V averaged over its scored seeds):
mean diff **−0.095**; VEi better on 62 pairs, V better on 119, tie 18.

## 3. Success rate (fail proxy: garment ≤ 2 or clean ≤ 2)

| | VEi (full) | V (its 396) | VEi matched | V matched |
|---|---|---|---|---|
| cell-level pass | **422/600 (70.3%)** — 178 fails | 304/396 (76.8%) — 92 fails | 283/396 (71.5%) — 113 fails | 304/396 (76.8%) |
| pairs passing at ALL scored seeds | **116/200 (58.0%)** (all 3 seeds) | 134/199 (67.3%)* | 127/199 (63.8%) | 134/199 (67.3%) |
| pairs passing at ≥1 seed | **165/200 (82.5%)** | 165/199 (82.9%) | 149/199 (74.9%)† | 165/199 (82.9%) |

\* V's per-pair seed coverage: 31 pairs × 1 seed, 139 × 2, 29 × 3 — fewer chances to fail
biases its all-seed pass rate up and its ≥1-seed rate down relative to a 3-seed run; the
matched columns remove that. † VEi's matched ≥1-seed rate drops because the matched cut has
only 1–2 seeds per pair for most pairs.

Read on matched cells: VEi fails ~5 points more of the matrix at cell level (28.5% vs 23.2%)
and ~3–8 points more at pair level. On the full run, 35/200 pairs (17.5%) fail the proxy at
all three seeds; 84/200 (42%) fail at least one seed.

## 4. The 10 worst pairs by VEi 3-seed mean fidelity

| fid | pair | class | what the judge saw |
|---|---|---|---|
| 3.00 | dualuse_lp_beige_long_coat_menswear+g018 | F3 | jacket rendered as a structured black blazer, not the reference's soft open-front cut; pose also shifts (g 2/2/2) |
| 3.00 | dualuse_lp_plaid_overcoat_brown_suit+g011 | **F1** | the wearer's plaid coat survives over the target dress; body/arms altered, footwear changed |
| 3.00 | g013+p006 | F3 (+identity loss) | only the floral skirt half transfers; s46 shows the *reference model on the white background* instead of the person (i1/s1) |
| 3.00 | g029+p012 | **F1** | houndstooth blazer + white shirt retained, only blue sleeves added; s46 again swaps person/scene (i1/s1) |
| 3.11 | g009+g011 | **F2** | fitted black midi dress becomes a long jumpsuit/pant silhouette with sheer lower legs |
| 3.11 | g009+p003 | **F2** | gathered burgundy dress becomes a wide-leg jumpsuit/pants garment; body shape changed |
| 3.22 | dualuse_lp_beige_long_coat_menswear+dualuse_lp_floral_kimono_set | F3 | floral print/color held but cut and styling differ, beret/bag accessories dropped, pose changed |
| 3.22 | dualuse_lp_beige_long_coat_menswear+g004 | **F1** | target top+trousers mostly there but the wearer's beige coat stays on; clutch omitted |
| 3.22 | g015+g030 | F3 | open gold-sequin shirt + white pleated bottom restyled into a closed gold top and long skirt |
| 3.22 | g029+p004 | F3 (+1-seed identity loss) | white henley drifts light blue; s46 collapses identity/scene (g5/i1/s1) |

Classes: F1 wearer's clothing survives ×3, F2 skirt/dress→trousers ×2, F3 reference drift ×5
(two of the F3s also carry a one-seed person/scene swap — the result shows the garment
reference's model instead of the person, which is what drags identity/scene means down).
No F4 (exposed skin) in the bottom 10.

## 5. Distribution sanity (VEi, 600 cells)

- Cells scoring 5/5/5 on garment/identity/scene: **0/600** (baseline V: also 0/396 — the judge essentially never gives a perfect fidelity triple).
- garment = 1: **9/600** (baseline V: 4/396). garment histogram 1:9, 2:165, 3:262, 4:163, 5:1 — the modal cell is a 3 ("close but not exact"), and garment 5 occurs once in 600 cells.
- identity 4.18 (147 fives), scene 4.51 (363 fives), clean 3.78, hands 3.81, realism 3.93 (histogram hugs 4) — the non-garment criteria are solid; garment is the bottleneck everywhere.

## 6. Verdict

On the full 200-pair matrix the VEi arm is **modestly worse than the v3.3 lock's record, at
the edge of what calibration drift could explain**: fidelity 3.88 vs 3.99 (−0.106 raw, −0.094
on matched cells — just above the ~0.1 noise line), V better on 119 pairs to VEi's 62, and a
cell-level fail rate ~5 points higher (28.5% vs 23.2% matched). The deficit is *not* garment
(−0.03 matched, well inside noise) or cleanliness (+0.01); it is identity (−0.11) and scene
(−0.14), partly driven by a handful of cells where VEi returns the garment reference's model
instead of the person. So: not better, plausibly slightly worse, certainly not an improvement.
On the reviewer's "bad" impression — the numbers half-support it. Absolute garment correctness
is genuinely mediocre: garment mean 2.97, a single garment-5 cell in 600, zero perfect
fidelity triples, 30% of cells failing the proxy and 42% of pairs failing at least one seed.
But that description fits the v3.3 record almost equally (garment 3.03, 23% cell fails, 0
perfect triples), and identity/scene/realism sit at 4.2–4.5 — so the eyeball "bad" is the
system's garment-transfer ceiling on this matrix plus the failure-set pairs (the worst tail:
F1 coats surviving, F2 dress→trousers, and two person-swap cells), not a collapse specific to
VEi. VEi simply fails the same matrix slightly more often than the lock does.

## 7. Spend

600 calls (3 smoke + 597 main), tokens **1,007,067 in / 244,711 out** (exact, from the API
usage field) ≈ **$8.71** at the `PRICE` table (gpt-5.5 $5/$15 per M) — $0.0145/cell, inside
the ~$9–10 projection, under the $20 guard. No retries burned, no unscored cells.

## Files

- `meta/vlm_scores.csv` — 600 judged cells (six scores, note, seconds, tokens)
- `meta/per_pair.csv` — per-pair fidelity means and fail counts, VEi vs baseline V
- `meta/analysis_stdout.txt` — full analysis output; `analyse.py` — the analysis
- `meta/score_log.txt` — judge run log; `run_judge.py` — the runner (note cap 300→2000 only)
- `gen/`, `inputs/` — symlinks into `../ironman2/`
- baseline: `v33_ironman_vlm_scores_bca4.csv` at the repo root (arm V rows; BC rows unused here)
