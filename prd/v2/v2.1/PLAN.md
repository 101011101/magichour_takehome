# v2.1 Plan — architecture of the realism stage

## Where it sits

```text
person + garment
      │
      ▼
editing model (klein 4B — decided in V2.1_RESULTS)
      │  candidate try-on
      ▼
auxiliary realism model        ← this workstream
      │  same content, more photographic
      ▼
fidelity gate  ──fail──► ship the pre-pass candidate
      │ pass
      ▼
final image
```

Two properties make this a separate stage rather than a setting on the
generator:

- **Single-image input.** The auxiliary model never sees the garment reference,
  so it cannot import content from it — the failure class that dominates the
  editing bucket does not exist here.
- **Its reference is its own input.** "Fidelity" in this stage means *did not
  change what it was given*, which makes preservation directly measurable
  without needing the original person or garment.

## Interfaces

```python
# config, not model, is the unit: strength/noise change the fidelity outcome
aux_refine(image, config) -> image
score_preservation(before, after) -> {id_preserve, garment_preserve,
                                      hf_ratio, content_ssim}
judge_pairwise(before, after) -> {realism: 1-5 x4, fidelity: 1-5 x2}
```

Implemented in `v2/build/aux_harness.py` (config sweep) and
`v2/build/aux_batch.py` (batch comparison). Both write run packages plus a CSV,
and generate a page into `v2/artifacts/`.

## Gates and fallbacks

| Rule | Value | Behaviour on failure |
|---|---|---|
| Fidelity gate | VLM fidelity >= 4.5 | Config is disqualified, not down-weighted |
| Hard disqualifier | any fidelity criterion <= 3 | That configuration is rejected outright |
| Identity guard | AuraFace input->output cosine | Below threshold, ship the pre-pass candidate |
| `hf_ratio` | high-frequency energy after/before | **Review trigger, never an auto-fail** — it responds to input softness, not model behaviour (see EXPERIMENT hypothesis 5) |

The stage is optional by construction: if the pass fails its gate, the pipeline
ships the editing model's output unchanged. Realism repair must never be able to
make the product worse.

## Chosen configuration

`seedvr2_x2_noise0` — SeedVR2 via `fal-ai/seedvr/upscale/image`, upscale factor
2, **`noise_scale = 0`** (fal's default of 0.1 is measurably worse on both
fidelity and identity), Apache 2.0, self-hostable.

Two implementation notes for the deployed path:
- Output is 2x the input; downstream steps and storage must expect the larger
  size, or downscale explicitly.
- The model preserves identity better on higher-resolution inputs (0.94 at
  Testset2 resolution vs 0.839 on 864x1296 inputs), so do not downscale before
  the pass.

## Not adopted

- **Stacking** (SeedVR2 -> Z-Image): worse on every axis than SeedVR2 alone.
- **Z-Image Turbo at any strength**: fails the damage-floor test — it restructures
  faces even on real photographs that needed no repair.
- **Artifact repair in this stage**: proven ineffective; owned by **v2.3**.
