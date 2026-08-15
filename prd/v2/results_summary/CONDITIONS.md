# V2 Test Conditions — what is being tested, on what data, and why

The setup half of the results docs: the constraints that shape every choice, the
model pool and why each model is in it, the test sets and why they exist, and
what each evaluation layer measures. **No verdicts here** — results and current
leaders live in [V2.1_RESULTS.md](V2.1_RESULTS.md) (V2.0 kept as the
evidence record).

Sources: `execution_conventions.md` (constraints, test sets, Drive layout),
`prd/v2/SCORING_CRITERIA.md` (buckets, axes, schemas),
`research/open-weights-model-catalog.md` (candidate pool).

## 1. Constraints that shape everything

- **Deployed path: open weights only.** No proprietary hosted APIs in the
  shipped version — properly downloaded weights, self-hosted. This is why the
  V1 winner (seedream → qwen cascade) is dead regardless of how well it scored.
- **Testing exception.** fal endpoints may be used during iteration, but only
  where they host **open-weights checkpoints**, so results stay portable to
  self-hosting. fal is a serving substrate, never a model source.
- **Parity rule.** Any number claimed for the final version must be reproduced
  on downloaded weights (diffusers on a Colab A100). fal endpoints add their own
  preprocessing and defaults, so **every number in the results doc is
  directional until re-run self-hosted.**
- **The regression to fix:** identity degradation, carried over from V1.
- Weight caching: Drive-backed `HF_HOME` (2TB account) — a model downloads once
  and every later Colab session finds it in the cache.

## 2. Model pool — why each model is in it

Models are split into two buckets that are scored differently (see §4).

### Editing models — person + garment in, try-on out

Selected on **fidelity**; multi-image input means they carry the attention
failure modes (identity drift, garment leakage, background repaint).

| Model | License · access | Why it is in the pool |
|---|---|---|
| **FASHN VTON v1.5** | Apache 2.0 · `fal-ai/fashn/tryon/v1.5` | The only modern, dedicated, Apache-licensed try-on model with a clean training-data story; pixel-space (no VAE round-trip) directly targets identity degradation. Self-hostable at ~8GB. **v1.5 pinned deliberately — fal's newer v1.6 is FASHN's closed commercial model.** |
| **FLUX.2 klein 4B** | Apache 2.0 · `fal-ai/flux-2/klein/4b/distilled/edit` | #1 open model on VTEdit shop→model try-on; balanced across identity/garment/quality with no weak axis; sub-second, ~13GB. The 9B sibling is non-commercial, so 4B is the only usable size. |
| **Qwen-Image-Edit-2511** | Apache 2.0 · `fal-ai/qwen-image-edit-2511` | **The baseline — the model currently running on the Magic Hour website.** Everything must beat it. Also the family with the richest try-on LoRA ecosystem. |
| **FireRed-Image-Edit v1.1** | Apache 2.0 · `fal-ai/firered-image-edit-v1.1` | Open-source SOTA on general edit benchmarks, trained with an explicit identity-consistency loss — the most promising untested answer to the V1 regression. v1.1 chosen after confirming its weights are Apache. |
| Seedream 5 Lite → Qwen cascade | closed | V1's shipped winner. Present only as the historical reference point; ineligible for V2. |
| **HiDream-O1-Image** | MIT · `fal-ai/hidream-o1-image/edit` | Promoted 2026-08-14 when a fal endpoint turned up; pixel-native/no-VAE, the same argument that put FASHN in the pool. **Eliminated** — see V2.1. |
| JoyAI-Image-Edit-**Plus** · OOTDiffusion · OrthoTryOn | Apache / MIT · **no fal endpoint** | Catalog-vetted alternatives that require self-hosting to evaluate at all (fal's `joyai-image-edit` is the single-image Edit, not the multi-ref Plus). Deferred, with promotion triggers in [EXTENSION_ARMS.md](../EXTENSION_ARMS.md). |

### Auxiliary realism models — one image in, same image out but more realistic

Selected on **realism gain, gated on fidelity preservation**. Single-image input
means they are structurally free of the multi-image attention problems. They
exist because the editing bucket's weak axis is realism (artifacts, hands,
plastic skin), and repairing that at the editing stage risks fidelity.

| Candidate | Access | Why it is in the pool |
|---|---|---|
| **SeedVR2** (×2, `noise_scale` swept) | Apache 2.0 · `fal-ai/seedvr/upscale/image` | One-step restoration DiT, 2026 consensus SOTA open restorer; strongest identity-preservation evidence of any generative model surveyed. Known risk: oversharpening on lightly-degraded AI images — hence the `hf_ratio` metric and a noise sweep. |
| **Z-Image Turbo img2img** (strength 0.15 / 0.25 / 0.35) | Apache 2.0 · `fal-ai/z-image/turbo/image-to-image` | The de-plastic pass: best open-model skin texture, sub-second, cheap. Strength swept because fidelity preservation is config-dependent; 0.35 included deliberately as a breaking-point probe. |
| **Z-Image Base + PAI Fun tile-ControlNet + UltraReal LoRA** | Apache · **self-host only** | The tile ControlNet is what stops low-denoise refinement from drifting — the hypothesised fix for Turbo's identity drift. fal serves Base as text-to-image only, so this needs a Colab A100. Highest-priority queued test. |
| Real-ESRGAN · AuraSR-v2 | BSD-3 / Apache · self-host | **The zero-drift floor.** Neither can hallucinate, so they bound what "fidelity preservation" means and make the diffusion refiners' scores interpretable. |
| OSEDiff · DiffBIR v2 | Apache · self-host | Cheap one-step SR and heavy-degradation restoration respectively. |
| GFPGAN · RestoreFormer++ · PMRF | Apache / MIT · self-host | Face-region-only restorers; PMRF's objective is explicitly identity-faithful. Scoped to the face crop so they cannot touch the garment. |
| Frequency-separation detail transfer | n/a (numpy/OpenCV) | Not a model — fidelity insurance. Re-imposes the original's high-frequency garment detail after any refiner. |

### Composite — editing → auxiliary

The shipped product is a pipeline, not a single model. Current target:
**FLUX.2 klein 4B distilled → SeedVR2 (noise 0)** (editing base decided 2026-08-14, see
V2.1_RESULTS.md; FASHN v1.5 retained as the strict-preservation fallback). A superseded klein-based composite
(`composite_v2ow`: klein → geometric face paste-back → Z-Image refine →
AuraFace identity gate with best-of-N retry) is retained in the harness as a
reference implementation of the paste-back/gate machinery.

## 3. Test sets — what data exists and why

Two sets, answering different questions. Neither replaces the other, and
**scores are not comparable across sets** — always state which set a number
came from.

### `test_set/` — V1 set: human + garment-only, breadth-first

- **Shape:** 30 people + 30 garments, 30 curated 1:1 pairs (`pairs.csv`). Every
  garment reference is a product shot (flat-lay / ghost mannequin). One pair
  kind: **human + garment-only**.
- **Why it exists:** population coverage and fair comparison. Stratified quotas
  (10/10/10 skin tone, 10/10/10 body size, 15/15 gender, 7 hand-over-torso) so a
  model cannot win by being good on one demographic; difficulty graded 4 easy /
  14 medium / 12 hard, hard garments deliberately paired to hard poses.
- **Known limit:** normalized to 1024px max side — **too soft for identity
  metrics**, since face crops lose the detail AuraFace needs. This limitation is
  what motivated Testset2.
- **Used by:** the V2 notebook (triage → grid → holdout) and as the BEFORE set
  for the auxiliary screen.

### `Testset2/` — V2 set: high resolution, garment-only AND garment+human

- **Shape:** 8 people + 12 garments, full-resolution originals (up to
  5152×7728, capped to 1536 on the long side only at upload); mixed formats
  (jpg/webp/avif) normalized to JPEG by the harness. Two `_nonceleb` controls
  guard against celebrity memorization inflating identity scores.
- **Why it exists:** resolution-sensitive fidelity, and garment references that
  are *themselves photos of people* — a case `test_set/` cannot express at all.
- **Pair kinds** (13 pairs, matrix in `v2/build/ts2_harness.py`):

| kind | n | garment reference is… | what it tests |
|---|---|---|---|
| `product` — **garment only** | 6 | flat-lay / ghost mannequin, no person | the normal shop→model case at high res: print, text, fine stripes, lower-body items, plus a back-view pose control |
| `duo_lookbook` — **garment + human** | 4 | an editorial on-model photo | can a model lift a garment off another person (model2model) without importing that person |
| `duo_swap` — **garment + human** | 3 | a `people/` photo used as the garment source | pure clothes swapping: put what person B wears onto person A |

- **Why the duo kinds matter:** the benchmark literature has every open model
  collapsing here (VTEdit Model2Model: best 2.06, Qwen 1.17, klein 1.03), so the
  duo rows discriminate between arms while product rows mostly do not. The
  specific failure they hunt is **identity substitution** — the result showing
  the reference's person instead of the input's — tracked by `wrong_person`.
- **Duo mechanics:** on-model references show a whole outfit, so each duo pair
  carries a target-garment designation ("the long beige coat") injected into the
  prompt for prompt-based arms; FASHN gets `garment_photo_type="model"` instead
  of `"flat-lay"`.
- **Scoring caveat:** duo pairs compare the garment against a torso crop of a
  real photo (domain-matched to the output); product pairs compare against a
  flat-lay (domain gap). Duo garment scores are therefore inflated relative to
  product — compare arms *within* a kind, never scores *across* kinds.

## 4. What each evaluation layer measures

Two axes, applied differently per bucket (full definitions in
[SCORING_CRITERIA.md](../SCORING_CRITERIA.md)):

- **Fidelity** — garment (color/pattern/print/cut), identity (face/hair/body),
  background/scene. The main axis; garment carries ×2 weight.
- **Realism** — no additional artifacts (non-logical items), smoothness (no
  plastic skin), photographic accuracy.

| Layer | What it does | Authority |
|---|---|---|
| **Deterministic metrics** (free, local CPU) | FashionSigLIP garment similarity, AuraFace identity, pose displacement, background PSNR → fixed-anchor weighted composite (garment ×2). Anchors recalibrated on V1 outputs; the identity ceiling deliberately sits below paste-back saturation so compositing arms cannot max the score by construction. | Authoritative for **elimination** |
| **VLM judge** (blind gpt-5.5) | Six 1–5 criteria bucketed into fidelity (garment, identity, scene) and realism (clean, hands, realism), plus `wrong_person`. Schema-validated with self-correcting retries. | Authoritative for **realism**, where deterministic metrics are weak |
| **Auxiliary screen** | A different question: single-image models scored against **their own input** ("did it change what it was given?"). Realism gain, gated on VLM fidelity ≥ 4.5. | Selects the auxiliary model |
| **Human review** | Tiebreaker where the judges disagree; final selection call. | Final |

The judge is closed-weights (gpt-5.5) by design — it is an evaluation
instrument, not part of the deployed path.

## 5. Where things live

| What | Where |
|---|---|
| Comparison pages | `v2/artifacts/` (`index.html` is the hub) |
| Images, CSVs, run packages | `v2/runs/` (Testset2 under `v2/runs/ts2/`) |
| Harnesses | `v2/build/ts2_harness.py` · `aux_harness.py` · `make_compare.py` · `notebook_cells.py` |
| Criteria & schemas | `prd/v2/SCORING_CRITERIA.md` |
| Results | [V2.0_RESULTS.md](V2.0_RESULTS.md) |
| Conventions, Drive layout, test-set definitions | `execution_conventions.md` |
