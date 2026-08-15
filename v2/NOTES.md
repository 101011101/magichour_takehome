# Notes — V2 (open weights only)

Full V1 record: [../v1/NOTES.md](../v1/NOTES.md). Carry-forward summary:

## What V1 established

- Krea 2 and Ideogram cannot do try-on via API (single content-image slot, verified
  against specs + empirically). Krea 2 has a weights-level escape hatch (community
  LoRA + ComfyUI patch nodes) but a try-on analogue needs LoRA training — out of scope.
- Flux 2 Klein: 4B is Apache-2.0/ungated, 9B gated non-commercial; up to 4 reference
  images. BFL's hosted `/v1/flux-tools/vto-v2` is Klein under the hood.
- Dedicated VTO models beat general edit models on the average case; FASHN
  open-sourced a 972M Apache-2.0 model that fits a T4.
- Eval-first: deterministic CV (ArcFace identity, pose diff, background PSNR,
  garment sim) to score before adding guardrails. Harness is the durable product.
- V1 shipped (c1a5aa3): seedream5_lite → qwen_image3 cascade won blind VLM + human
  review on 18 held-out pairs; beat qwen_2511 baseline on every judging system.
  Dead for V2 — hosted/fal arms excluded by the open-weights directive.
- Known caveats inherited: garment_sim is a color-histogram proxy (structure-blind);
  identity degradation is the top quality problem to fix; identity-restore composites
  (v2/v3, 2026-08-09) were inconsistent and did not ship.

## Quality levers that carried over

- Preprocess inputs: background-remove garment, flat-lay normalize, aspect-match to
  native training resolution.
- Best-of-N seed search auto-ranked by DINOv2 garment sim + ArcFace identity.
- Prompts must name what to preserve, with explicit "image 1"/"image 2" references.

## V2 directive (Ray, 2026-08-09; amended 2026-08-13/14)

Open weights only in the deploy path. Output quality is the deliverable; harness
optional. Fix identity degradation.

Amendment (see `execution_conventions.md` testing exception, confirmed by Ray
2026-08-14): "no fal" applies to the deployed path, not to iteration — fal may
serve **open-weights checkpoints** during development (all five V2 arms have such
endpoints), then everything switches to downloaded weights once, at the parity
stage. fal is a serving substrate here, never a model source.

## Wave-1 results & pivot (2026-08-14)

- Triage (4 open-weights arms, new metrics): klein_4b 0.778 > fashn_v15 0.769 >>
  firered 0.600 > qwen_2511 0.518. FireRed eliminated (poor garment transfer
  despite identity-consistency training). klein produced one solid-black frame
  (distilled-model flake) — best-of-N mitigates.
- klein-based composite_v2ow on 12 grid pairs: det 0.707, 10/12 identity-gate
  passes; paste-back guard behaved correctly on head-covering garments.
- **Pivot (Ray):** fashn v1.5 is the editing base going forward; klein composite
  superseded. New composite = fashn -> auxiliary realism model. Two-bucket
  scoring (editing = fidelity; auxiliary = realism gated on fidelity
  preservation) recorded in prd/v2/SCORING_CRITERIA.md, with the
  auxiliary-model candidate pool and the pairwise VLM rubric for the
  aux-selection harness.

## Future steps (queued, 2026-08-14)

- **Outfit-swap eval (person→person garment transfer).** The Testset2 people are
  already wearing full outfits and every Testset2clothes image is on-model — so
  beyond the standard garment-image→person task, test *clothes swapping*: the
  source garment is what another person is wearing. Variants to compare later:
  (a) direct two-photo swap (model told "the coat worn in image 2"),
  (b) garment-region crop from the source photo used as a pseudo-product shot,
  (c) background-removed worn-garment cutout (BiRefNet) as the reference.
  This stresses garment *extraction* in a way flat-lay pairs can't, and matches
  a real product surface (users pointing at an outfit photo, not a catalog PNG).
  Testset2 + Testset2clothes (celebrity/editorial, all on-model) is the natural
  test bed; needs per-pair target-garment designation either way.
