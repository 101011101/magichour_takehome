# v2.1 Results — image realism and gloss reduction

**Status: conditional pass, parked.** Leader chosen and confirmed on independent
data; the gloss question remains open (EXPERIMENT.md, open question 1).

Artifacts (interactive, arrow-key viewers):
- [`v2/artifacts/v21_aux_screen.html`](../../../v2/artifacts/v21_aux_screen.html) — screen 1, config sweep
- [`v2/artifacts/v21_aux_batches.html`](../../../v2/artifacts/v21_aux_batches.html) — screen 2, two batches with control
- Data: `v2/runs/aux/`, `v2/runs/aux_batches/` (metrics.csv, vlm.csv, run packages)

## Chosen configuration

**`seedvr2_x2_noise0`** — SeedVR2, upscale x2, `noise_scale = 0`. Apache 2.0,
self-hostable, one step, seconds per image.

## Screen 1 — config sweep (6 configs x 4 inputs)

| config | realism | fidelity | id preserved | hf ratio | gate |
|---|---|---|---|---|---|
| **seedvr2_x2_noise0** | **4.31** | **5.00** | 0.839 | 2.59 | PASS |
| seedvr2_then_zimage | 4.25 | 4.75 | 0.676 | 2.16 | PASS |
| seedvr2_x2_noise01 | 4.25 | 4.88 | 0.781 | 2.47 | PASS |
| zimage_s025 | 3.88 | 4.63 | 0.490 | 0.80 | PASS |
| zimage_s015 | 3.75 | 4.38 | 0.491 | 0.79 | FAIL |
| zimage_s035 | 3.69 | 3.25 | 0.299 | 0.90 | FAIL |

## Screen 2 — two batches with a control (4 configs x 5 subjects x 2 batches)

| batch | config | realism | fidelity | id cos | ssim | hf ratio |
|---|---|---|---|---|---|---|
| klein | **seedvr2_x2_noise0** | **4.15** | 4.90 | **0.943** | 0.920 | 1.68 |
| klein | seedvr2_x2_noise01 | 4.10 | 5.00 | 0.892 | 0.913 | 1.62 |
| klein | seedvr2_then_zimage | 4.05 | 4.90 | 0.702 | 0.857 | 1.27 |
| klein | zimage_s025 | 4.00 | 4.80 | 0.613 | 0.853 | 0.84 |
| original | **seedvr2_x2_noise0** | **4.05** | 5.00 | **0.937** | 0.940 | 1.20 |
| original | seedvr2_x2_noise01 | 3.95 | 5.00 | 0.896 | 0.935 | 1.09 |
| original | seedvr2_then_zimage | 3.95 | 4.80 | 0.742 | 0.903 | 0.78 |
| original | zimage_s025 | 3.90 | 4.90 | 0.721 | 0.903 | 0.84 |

## Findings

1. **`seedvr2_x2_noise0` wins both batches** on realism and identity
   preservation — leader whether the input is a real photograph or a generated
   one. Independent confirmation of screen 1's pick.
2. **Noise off beats fal's default.** `noise_scale` 0 vs 0.1: fidelity 5.00 vs
   4.88, identity 0.943 vs 0.892. Use 0.
3. **The control exposed Z-Image as destructive.** On a real photograph needing
   no repair it still drops AuraFace to 0.72 (0.61 on generated inputs) and
   visibly restructures the face. That is damage, not a repair trade-off —
   invisible to screen 1, which only had generated inputs.
4. **`hf_ratio` interpretation settled.** Same model and settings measure 1.20 on
   real photos vs 1.68 on generated ones: it restores in proportion to input
   softness. High values indicate a soft input, not an over-sharpening model.
   Visual check on a plaid print confirmed genuine detail restoration.
5. **Higher-resolution inputs preserve identity better** — 0.94 at Testset2
   resolution vs 0.839 on 864x1296 inputs. Do not downscale before this stage.
6. **Stacking is not worth it.** SeedVR2 -> Z-Image is worse than SeedVR2 alone
   on every axis and costs identity (0.702 vs 0.943).
7. **No configuration ever repaired an artifact.** `artifact_fix` = 3.00 across
   two rounds and 14 config-batches. Handed to **v2.3** as its founding premise:
   artifact repair needs a region-targeted mechanism.

## Carried to other workstreams

| Finding | Goes to |
|---|---|
| Global realism passes never repair artifacts | **v2.3** |
| Realism stage cannot fix garment or identity accuracy | **v2.2** |
| Z-Image Base + tile-CN + UltraReal still untested (the gloss candidate) | parked here |
