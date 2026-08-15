# v2.1 Test design

Two screens were run. The second exists because the first could not answer the
question that mattered.

## Screen 1 — configuration sweep

| | |
|---|---|
| Inputs | 4 editing-model outputs (FASHN v1.5, the base at the time) |
| Configs | 6: SeedVR2 x2 at noise 0 and 0.1; Z-Image Turbo img2img at strength 0.15 / 0.25 / 0.35; SeedVR2 -> Z-Image stack |
| Deterministic | AuraFace `id_preserve`, FashionSigLIP `garment_preserve`, `hf_ratio` (high-frequency energy after/before on the torso crop), `content_ssim` — all against the config's **own input** |
| VLM | Blind gpt-5.5, pairwise BEFORE/AFTER, six 1-5 criteria: `artifact_fix`, `no_new_artifacts`, `smoothness`, `photo_real` (realism) + `garment_untouched`, `identity_untouched` (fidelity) |
| Gate | VLM fidelity >= 4.5 |
| Harness | `v2/build/aux_harness.py --generate --score --judge --html` |
| Cost | 24 generations, ~$0.64 fal + judging |

**Limitation that forced screen 2:** every BEFORE was already AI-generated, so
the screen could measure "which config improves a generated image" but not "what
does this config cost when the input is already correct". A model that rebuilds
faces is indistinguishable from one that repairs them if you only ever feed it
damaged inputs.

## Screen 2 — two batches, with a control

Same subjects in both batches, so any difference is attributable to *real photo
vs generated image* rather than to different content.

| Batch | Input | Question |
|---|---|---|
| **A `original`** (control) | The 5 Testset2 person photos — real, undamaged | A realism pass should be a **no-op**. Whatever changes here is damage the model inflicts regardless of input quality |
| **B `klein`** | klein 4B try-on outputs for the same 5 subjects | The deployed case: repair a generated image |

| | |
|---|---|
| Configs | 4 (the two Z-Image strengths that already failed the gate were dropped) |
| Metrics | As screen 1 |
| Harness | `v2/build/aux_batch.py --generate --score --judge --html` |
| Cost | 40 generations, ~$1.40 fal + ~$1.00 judging |

## Metric caveats carried forward

1. Outputs are compared after LANCZOS downscale from 2x, which itself crispens.
   The next round should compare at native resolution against a bicubic-upscaled
   BEFORE.
2. `hf_ratio` requires a visual companion — a crop review at 2x zoom — before it
   is read as over-sharpening.

## Not yet run

- Zero-drift floor: Real-ESRGAN, AuraSR-v2 (neither can hallucinate).
- Z-Image **Base** + PAI Fun tile-ControlNet + UltraReal LoRA — self-host only.
- Face-scoped restorers: GFPGAN, RestoreFormer++, PMRF.
- Wider BEFORE set; parity re-run on downloaded weights.
