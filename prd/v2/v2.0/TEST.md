# v2.0 Test — three runs, two sets, five editing arms

> **Reconstructed 2026-08-15, after the runs.** See [README.md](README.md).
> Sample sizes below were what was affordable, not what was designed for; where
> a run was underpowered it says so.

## 1. Test sets

Two sets answering different questions. **Scores are not comparable across
sets** — always state which set a number came from. Full definitions:
[CONDITIONS.md §3](../results_summary/CONDITIONS.md).

| Set | Shape | What it is for | Known limit |
|---|---|---|---|
| **`test_set/`** (V1) | 30 people + 30 garments, 30 curated 1:1 pairs; every garment reference is a product shot; stratified quotas (10/10/10 skin tone, 10/10/10 body size, 15/15 gender, 7 hand-over-torso); graded 4 easy / 14 medium / 12 hard | Population coverage and fair comparison — a model cannot win by being good on one demographic | Normalized to 1024px max side, **too soft for identity metrics** (face crops lose the detail AuraFace needs). This is what motivated Testset2 |
| **`Testset2/`** (V2) | 8 people + 12 garments, full-resolution originals (up to 5152×7728, capped at 1536 long side on upload); mixed jpg/webp/avif normalized to JPEG; two `_nonceleb` controls | Resolution-sensitive fidelity, **and** garment references that are themselves photos of people — a case `test_set/` cannot express | 13 pairs total, so 3–6 per pair kind. Thin |

The `_nonceleb` controls exist to guard against celebrity memorization inflating
identity scores — a real risk when the people set includes recognisable faces.

### Testset2 pair kinds

| kind | n | garment reference is… | what it tests |
|---|---|---|---|
| `product` | 6 | flat-lay / ghost mannequin, no person | the normal shop→model case at high res: print, text, fine stripes, lower-body items, plus a back-view pose control |
| `duo_lookbook` | 4 | an editorial on-model photo | can a model lift a garment off another person without importing that person |
| `duo_swap` | 3 | a `people/` photo used as the garment source | pure clothes swapping: put what person B wears onto person A |

Duo pairs carry a target-garment designation ("the long beige coat") injected
into the prompt for prompt-based arms; FASHN receives
`garment_photo_type="model"` instead of `"flat-lay"`.

## 2. Run 1 — `test_set/` triage

**4 arms × 4 pairs.** Deterministic composite plus blind VLM bucketed into the
two axes. Purpose: cheap elimination before spending on the high-res set.

Arms: `klein_4b_edit`, `fashn_v15`, `firered_edit`, `qwen_2511` (baseline).

Survival rule: survivors advance to Testset2; the baseline advances by rule
regardless of score, since the product must be shown to beat what is currently
shipping.

## 3. Run 2 — auxiliary screen

**6 configs × 4 images.** Each config scored **against its own input**, not
against a ground truth — the question is "did it change what it was given?".

Gate: **VLM fidelity ≥ 4.5**. Configs: SeedVR2 ×2 at `noise_scale` 0 and 0.1,
Z-Image Turbo img2img at strength 0.15 / 0.25 / 0.35, and the SeedVR2→Z-Image
stack.

Strength 0.35 was included deliberately as a **breaking-point probe** — a config
expected to fail, so the axis has a known-bad end and the passing configs are
interpretable relative to something.

**Design flaw, found in v2.1 and recorded here:** every BEFORE image in this
screen was already AI-generated (FASHN outputs), so the screen could not
distinguish *repair* from *damage*. A model that restructures a face looks
acceptable when the face was synthetic to begin with. v2.1's two-batch design
fixed this by adding a **control batch of real photographs**, where any change is
damage by definition — and that control is what eliminated Z-Image Turbo.

## 4. Run 3 — `Testset2/` editing comparison

**4 arms × 13 high-res pairs**, 51/52 generations succeeded. `hidream_o1_edit`
was added 2026-08-14 when a fal endpoint appeared (~$0.55 for the arm); the other
three arms are unchanged from run 1.

Reported per arm: VLM fidelity, VLM realism, garment, identity, scene, AuraFace
identity cosine, background PSNR, deterministic composite, and `wrong_person`.
Also broken out **by pair kind**, since the duo kinds are what discriminate
between arms and the product rows mostly do not.

## 5. Follow-on — klein distilled vs base (2026-08-15)

Run after the decision, to check whether the chosen checkpoint was the right one
of the two Apache siblings. Same 13 Testset2 pairs, same seed and prompt.

| arm | checkpoint | sampling |
|---|---|---|
| `klein_4b_edit` | `.../4b/distilled/edit` | ~4 steps, guidance 0 (distilled: no true CFG) |
| `klein_4b_base_edit` | `.../4b/base/edit` | 28 steps, guidance 5.0, **plus a negative prompt** naming the failure modes |

**This comparison is confounded and is recorded as such.** The negative prompt is
available only to the base variant, and every term in it pushes the model to
change less — which plausibly produces both the base's strong identity/scene and
its weak garment. An isolation run (base, same seeds, no negative prompt) is
required before attributing any difference to the checkpoint itself.

A second suspected confound was **investigated and dismissed**: an earlier note
claimed the base rendered smaller frames. Output dimensions are identical on all
13 pairs (both 1.01–1.04 MP). The arm that does render small is FASHN
(0.39–0.89 MP), the likely source of the original figure.

## 6. Cost

≈ $3.5 fal generation + $2.3 judging across all three runs.

## 7. What this test design cannot answer

1. **Anything about self-hosted behaviour.** All numbers are fal numbers; fal
   applies its own preprocessing and defaults. Under the parity rule every figure
   is directional until reproduced on downloaded weights.
2. **Whether a failure is a flake or a seed.** The distilled klein's one
   solid-black frame (1 in 16 triage runs) was never reseeded, so
   "distillation flake" versus "unlucky seed" is not separable from this data.
3. **Whether the instruments see what a human sees.** Not tested here — and
   v2.2 subsequently showed they do not, on exactly this data.
