# v3.2 — RESULTS

**Status: concluded, 2026-08-27.** The evidence layer for the PHEAD-twice investigation. Per
[SCHEMA.md](../SCHEMA.md) this reports what was observed and how; the decision belongs
in [EXPERIMENT.md](EXPERIMENT.md).

---

## 1. What has been run

| | |
|---|---|
| matrix | the run-B fold, [`v30_matrix_b.csv`](../../../v3/testsets/v30_matrix_b.csv), 28 pairs |
| references | `v3/runs/v3.0b/refs/{g}__RAWCROP.jpg` — raw reference through the cropper, no bald pass |
| `PH` | `v3/runs/v3.0b/gen/{set_id}__PH.jpg` |
| `PH2` | `v3/runs/v3.0b/gen/{set_id}__PH2.jpg` |
| conditions | seed 46, V2 AMT prompt, both passes; see [TEST.md](TEST.md) |
| page | `v3/report/v32_phead_twice.html` — BC · PH · PH2 per pair, with the BC and RAWCROP references |

| generated 2026-08-27 | crops 28/28 (CPU); `PH` 28/28, `PH2` 28/28 — no endpoint failures; 56 klein calls, ~$0.84 |

## 2. Verdict

**Reviewer verdict, 2026-08-27, over all 28 pairs on `v3/report/v32_phead_twice.html`:
v3.2 is completely unusable.** Not tier-scored per set, for the same reason v3.1's
prompt sweep was not: the failure is categorical, not marginal, and a per-set ternary
would record the same thing 28 times.

## 3. Observed

**The second pass persists PHEAD's defects; it does not correct them.** Whatever PH got
wrong — the copied cut boundary, the hair fringe read as a hem, a half-resolved garment,
an unchanged input — PH2 carries forward as-is. The second pass is given a target that
already agrees with the reference's boundary, and it agrees with it again. Nothing that
was wrong in PH was observed to come right in PH2.

Against the hypotheses in [EXPERIMENT.md](EXPERIMENT.md):

| # | hypothesis | outcome |
|---|---|---|
| H1 | the second pass never makes a usable output unusable | not the question that mattered — it also never makes an unusable one usable |
| H2 | questionable → perfect | **not observed** — half-resolved garments stay half-resolved |
| H3 | identity/background drift accumulates | not separable from the above; the outputs are unusable before the person side is reached |
| H4 | PH2 matches BC on low hair damage | **no** — PH2 inherits PH's failures wholesale, so it sits at PH, not at BC |

Mechanistically this is the prediction from
[INVESTIGATION.md §3.1](../INVESTIGATION.md#31-image-2-is-not-conditioning-it-is-clean-tokens-in-the-same-attention-sequence):
a second pass cannot add signal the reference does not carry, and the reference is the
same file both times. **The pass-1 output is a worse image 1 than the original person
photo, not a better one**, because it already contains the copied boundary.

## 4. Measurements that are not trustworthy

- **n = 28, one seed, one reviewer, unblinded** — as for every run-B arm.
- **Pass 2 starts from fal's ~832×1248 output**, not the ≤1.15 MP input. Any
  sharpness difference between PH and PH2 has a resampling component that this run
  does not separate from the model's.
