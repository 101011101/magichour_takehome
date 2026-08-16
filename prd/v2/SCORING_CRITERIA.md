# V2 Scoring Criteria — model buckets, axes, and evaluation schemas

Decision record. **Current (2026-08-14, supersedes the line below): FLUX.2
klein 4B distilled is the editing base** — best fidelity, realism and garment transfer on
Testset2 (results_summary/V2.1_RESULTS.md). Earlier in the same day FASHN v1.5
led on triage and held the slot; it is now the strict-preservation fallback.
Throughout, V2 builds its own composite = editing model + auxiliary realism
model. This doc fixes the judging criteria for both deterministic and VLM
evaluation, and the selection criteria for the auxiliary-model search.

## 1. Model buckets

| Bucket | Role | Input shape | What it must do | Known failure class |
|---|---|---|---|---|
| **Editing models** | Garment transfer (the try-on step) | person + garment (multi-image) | Maximize **fidelity** | Multi-image attention issues: identity drift, garment leakage, background repaint |
| **Auxiliary models** | Realism repair after editing | **single image** | Maximize **realism** while **preserving fidelity** | Over-smoothing, detail hallucination, face/print drift at high strength |

The buckets are scored on the same two axes but with different priorities:
editing models are selected on fidelity (realism is secondary — the aux stage
exists to fix it); auxiliary models are selected on realism gain *times*
fidelity preservation — an aux model that touches fidelity is disqualified
regardless of how good it looks. Auxiliary models take one image, so they are
structurally free of the multi-image attention issues.

## 2. Axes

### Fidelity (main axis)
1. **Garment** — color, pattern, print, cut transferred faithfully.
2. **Identity** — face, hair, skin tone, body unchanged.
3. **Background** — scene preserved, no repaint or crop drift.
(Pose consistency rides with identity/background as a fidelity component.)

### Realism (second axis)
1. **No additional artifacts** — no non-logical items: extra limbs/fingers,
   floating seams, impossible garment physics, duplicated objects.
2. **Smoothness** — no plastic skin, banding, tiling seams, or denoise mush.
3. **Photographic accuracy** — reads as a real photo: lighting, grain,
   shadows, material response.

## 3. Deterministic schemas

### Editing models (references = original person + garment images)
| Metric | Implementation | Axis |
|---|---|---|
| `garment_sim` | FashionSigLIP cosine, garment ref vs result torso crop | fidelity (x2 weight) |
| `identity_cos` | AuraFace cosine, person ref vs result | fidelity |
| `bg_psnr` | PSNR outside person mask, person ref vs result | fidelity |
| `pose_err` | landmark displacement / torso, person ref vs result | fidelity |
Anchored composite as shipped in the V2 notebook (recalibrated anchors).

### Auxiliary models (reference = the aux model's OWN INPUT image)
Fidelity here means "did not change the content it was given":
| Metric | Implementation | Axis |
|---|---|---|
| `id_preserve` | AuraFace cosine, aux input vs aux output (target ~=1.0; gate, not score) | fidelity |
| `garment_preserve` | FashionSigLIP cosine + high-frequency (Laplacian) energy ratio on garment crop, input vs output | fidelity |
| `content_lpips` | LPIPS input vs output (low = untouched; catches global repaint) | fidelity |
| `realism_gain` | no-reference IQA delta (candidates: HPSv3, ARNIQA/MUSIQ-class scorer) output minus input | realism |
Deterministic realism scoring is weak in general — the VLM axis is primary for
realism; deterministic metrics primarily enforce the fidelity-preservation gate.

## 4. VLM schemas (judge: gpt-5.5, blind, schema-validated)

### Editing models — inputs: person, garment, result (current rubric, re-bucketed)
- fidelity = mean(garment, identity, scene)
- realism = mean(clean, hands, realism)
- Report both axes per arm; selection weight: fidelity first.

### Auxiliary models — inputs: BEFORE image, AFTER image (pairwise)
Six 1-5 criteria:
| Criterion | Question to the judge | Axis |
|---|---|---|
| `artifact_fix` | Did artifacts present in BEFORE get repaired in AFTER? | realism |
| `no_new_artifacts` | Are there zero new non-logical items in AFTER? | realism |
| `smoothness` | Skin/fabric natural, no plastic or mush? | realism |
| `photo_real` | Does AFTER read as a real photograph? | realism |
| `garment_untouched` | Garment color/pattern/print identical to BEFORE? | fidelity |
| `identity_untouched` | Face/hair/body identical to BEFORE? | fidelity |
- realism = mean(artifact_fix, no_new_artifacts, smoothness, photo_real)
- fidelity = mean(garment_untouched, identity_untouched)
- **Selection score = realism gain, gated on fidelity >= 4.5.** A single
  fidelity criterion at <=3 disqualifies the run configuration (that strength /
  step count), not necessarily the model.

## 5. Auxiliary-model search (the next harness)

Requirement: single-image input, improves realism, does not touch fidelity.
Sweep strength/steps per model — fidelity preservation is config-dependent;
score each config, not just each model. Candidate pool (open weights,
license-clean, from `research/open-weights-model-catalog.md` §4.5):

| Candidate | Class | Note |
|---|---|---|
| Z-Image-Turbo img2img (strength sweep 0.1-0.3) | diffusion refiner | current composite refiner; cheap, natural skin |
| SeedVR2 3B | one-step restoration DiT | 2026 consensus SOTA restorer; watch small-logo regularization |
| RealVisXL V5 / Juggernaut @ 0.15-0.25 denoise (+CN-Tile) | SDXL img2img | classic de-plastic pass |
| Real-ESRGAN (general x4v3) | GAN SR | zero-drift baseline — cannot hallucinate; floor for fidelity preservation |
| AuraSR-v2 | GigaGAN SR | crisper than ESRGAN, no diffusion hallucination |
| OSEDiff | one-step SR | cheap middle ground |
| GFPGAN / RestoreFormer++ / PMRF (face crop only, blend 0.3-0.5) | face restorers | scoped to the face region; PMRF is the identity-faithful objective |
| DiffBIR v2 | restoration | heavy-degradation cases |
| Frequency-separation detail transfer + wavelet color fix | non-model insurance | re-imposes original high frequencies after any refiner |

Harness shape (to be built): take N fixed BEFORE images (fashn v1.5 outputs
spanning easy/hard pairs) -> run every candidate config -> deterministic
fidelity-preservation gate -> pairwise VLM rubric above -> leaderboard =
realism gain among configs that passed the gate.

## 6. Standing decisions

- **Editing base (decided 2026-08-14): FLUX.2 klein 4B distilled** — best fidelity,
  realism and garment transfer on Testset2; downsides (occasional AI
  artifacts, occasional generation failure, weaker attention with multiple
  identities) are accepted and mitigated. See results_summary/V2.1_RESULTS.md.
- Superseded pick — FASHN v1.5 (triage: identity 0.991, bg_psnr 30.5, best
  garment_sim 0.713; the dedicated-VTO arm) — held the slot on triage, now the
  fallback for strict original-photo preservation; `composite_v2ow` (the earlier
  klein paste-back pipeline) is superseded as "ours".
- New composite target: **klein 4B -> best auxiliary model** (+ face
  paste-back / identity gate retained only if measurements show fashn needs
  them — its triage identity of 0.991 suggests it may not).
- **Auxiliary leader (conditional): `seedvr2_x2_noise0`** — SeedVR2 at
  upscale x2, noise_scale 0. VLM fidelity 5.00/5, realism 4.31, AuraFace
  preservation 0.839. To be re-run on a wider BEFORE set before it is fixed;
  rolling scoreboard in results_summary/V2.0_RESULTS.md.
- VLM judge stays gpt-5.5 (not in the deploy path); all deployed models remain
  open-weights only.

## 7. First aux screen — findings (2026-08-14, 6 configs x 4 FASHN v1.5 outputs)

Results in `v2/artifacts/v21_aux_screen.html` (+ aux_metrics.csv, aux_vlm.csv).

1. **SeedVR2 sweeps the fidelity axis.** noise_scale 0 scored VLM fidelity
   **5.00/5** (garment and identity both perfect) with realism 4.31 — best of
   every config. noise_scale 0.1 (fal default) is measurably worse on both
   fidelity (4.88) and AuraFace preservation (0.781 vs 0.839): **run noise at 0**,
   as predicted.
2. **`hf_ratio` needs a visual companion, not a threshold.** SeedVR2 measured
   2.59x high-frequency energy, which reads as oversharpening; inspection of a
   2x-zoomed plaid print shows genuine restoration (soft input -> correctly
   resolved grid, no invented detail), and the VLM independently scored
   garment_untouched 5.00. Confound: outputs are compared after LANCZOS
   downscale from 2x, which itself crispens. **Fix for the next round:** compare
   at native resolution against a bicubic-upscaled BEFORE, and treat hf_ratio as
   a flag that triggers a crop review, never as an automatic fail.
3. **Z-Image Turbo img2img drifts identity even at low denoise** — AuraFace
   input->output cosine 0.49 at strength 0.15-0.25 (vs SeedVR2's 0.84). It
   passes the VLM eye test but measurably rebuilds the face. This is direct
   evidence for the tile-ControlNet argument: **test Z-Image *Base* + PAI Fun
   tile-CN self-hosted** (fal serves Base as text-to-image only, so the Base
   de-plastic stack is not testable through fal).
4. **No aux config repairs artifacts** — `artifact_fix` was exactly 3.00 (= no
   change) for all six. Global realism passes do not fix bad hands or illogical
   items. **Design consequence:** artifacts must be addressed at the editing
   stage or by a region-targeted repair step (detailer/inpaint on hands), not by
   the realism pass. Add that as a third bucket if the problem persists.
5. Gate behaviour: zimage_s035 failed hard (fidelity 3.25) as the intended
   breaking-point probe; zimage_s015 failed at 4.375. Sample is 4 images per
   config — directional; widen before any final pick.
