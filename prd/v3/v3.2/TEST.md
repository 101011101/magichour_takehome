# v3.2 — TEST

**Status: specified and run (2026-08-27).** The matrix for v3.2 is **the v3.0 run-B
fold, unchanged** — [`v30_matrix_b.csv`](../../../v3/testsets/v30_matrix_b.csv), 28
pairs, every `test_set3` image used exactly once. Its selection rationale, exclusions
and the rendered table are in [v3.0/TEST.md](../v3.0/TEST.md#1-run-b-the-fold) and are
not repeated here; a change to the set would be a new test.

Reusing the fold is the point: BC and QX outputs for the same 28 pairs, same seed, same
prompt, are already in `v3/runs/v3.0b/gen/`, so the new arms are directly comparable
with no re-spend.

---

## 1. Arms

| tag | reference | image 1 | klein calls |
|---|---|---|---|
| `BC` | bald pass → CPU crop (`refs/{g}__BC.jpg`) | person | 2 (existing) |
| `PH` | CPU crop of the **raw** reference, no bald pass (`refs/{g}__RAWCROP.jpg`) | person | 1 |
| `PH2` | same `__RAWCROP.jpg` | **the `PH` output** | 2 total |

`PH` is PHEAD from V2 — the cropper with `cranium=False`, i.e. the head is removed by the
parser mask only. It is generated here rather than copied because V2's PHEAD frames are
over different pairs.

## 2. Run conditions — identical to run B

| | |
|---|---|
| model | `fal-ai/flux-2/klein/4b/distilled/edit`, 4 steps, guidance fixed |
| seed | **46**, both passes |
| prompt | the V2 AMT prompt verbatim, both passes: *"Dress the person in image 1 in the clothing shown in image 2. Keep the person's face, identity, body and the background exactly as they are."* |
| resolution | inputs ≤1.15 MP; fal normalises output to ~832×1248. **Pass 2's image 1 is fal's pass-1 output at that size**, not the original person photo |
| not varied | prompt wording between passes, seed between passes, reference between passes, crop parameters. A second pass with a different prompt ("refine", "sharpen the garment") is a different experiment |

**Budget.** 28 + 28 = **56 klein calls at $0.015 = $0.84.** The crop is CPU, free, and
runs before anything is paid for.

**Command.** `python3 v3/build/run_v30.py --run b --only crop,ph,ph2`. Stages are
resumable; `ph2` only runs on sets whose `PH` frame exists.

## 3. Review protocol

Same ternary as run B — **perfect / ok / fail** — plus the band on every non-perfect.
Two additions specific to this arm:

1. **Mark PH and PH2 side by side, per set**, and record the *direction* (up, same,
   down). The question is what the second pass does, not the PH2 rate on its own.
2. **Mark the person separately from the garment on PH2.** The second pass is the first
   arm in V3 where identity and background have been through klein twice; a garment
   win that costs the face is a fail, and the ternary alone would hide where it came
   from.

Unblinded, one reviewer, one seed — the same deviations as run B, stated as such.
