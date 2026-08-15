# v2.1 Experiment — image realism and gloss reduction

## Goal

Make the editing base's output read as a real photograph, without changing what
the editing model got right. Realism is the second axis in
[SCORING_CRITERIA](../SCORING_CRITERIA.md); this workstream owns it.

## What is being tested

Single-image "auxiliary" models: one image in, the same image out but more
realistic. They are structurally free of the multi-image attention failures that
affect editing models, which is why realism repair is a separate stage rather
than a prompt change to the generator.

The unit under test is a **configuration, not a model** — fidelity preservation
depends on strength/noise settings, so each setting is ranked separately.

## What we are looking for

1. **Realism gain** — artifacts repaired, skin and fabric natural (no plastic or
   mush), and the image reading as a photograph.
2. **Fidelity preservation** — the model must not change what it was given.
   Every metric compares an output against **its own input**. This is a gate
   (VLM fidelity >= 4.5), not a tradeable score: a config that improves realism
   by rebuilding the face fails, regardless of how good it looks.
3. **Damage floor** — how much a pass changes an image that needed no repair at
   all. This is what separates "improved the image" from "rebuilt the image",
   and it cannot be measured on generated inputs alone.

## Hypotheses and outcomes

| # | Hypothesis | Outcome |
|---|---|---|
| 1 | A single-image pass can raise realism without measurably touching fidelity | **Supported.** All configs cleared the gate; `seedvr2_x2_noise0` reached VLM fidelity 5.00 with realism 4.31 |
| 2 | Fidelity preservation is config-dependent, so configs must be ranked individually | **Supported.** Z-Image at 0.35 strength collapsed to fidelity 3.25 while 0.25 passed at 4.63 |
| 3 | A restoration model and a de-plastic model are complementary and should stack | **Not supported.** The SeedVR2 -> Z-Image stack scored below SeedVR2 alone on every axis and lost identity (0.702 vs 0.943) |
| 4 | A realism pass repairs artifacts | **Refuted decisively.** `artifact_fix` = 3.00 (no change) for every config across two rounds and 14 config-batches. Handed to **v2.3** |
| 5 | High high-frequency gain indicates over-sharpening | **Refuted.** The control batch showed the same model at 1.20 on real photos vs 1.68 on generated ones — it restores in proportion to input softness |

## Open questions (why this is parked, not finished)

1. **Gloss is not actually solved.** The workstream is named for reducing gloss
   and plastic skin, but the winning mechanism is *restoration* (SeedVR2 sharpens
   what is there) — it does not de-gloss. The model that does de-gloss (Z-Image
   Turbo) destroys identity, on real photographs as well as generated ones.
   The untested candidate that could resolve this is **Z-Image Base + PAI Fun
   tile-ControlNet + UltraReal LoRA**, self-host only: the tile ControlNet is
   precisely the mechanism that should stop low-denoise refinement from drifting.
2. **No zero-drift floor yet.** Real-ESRGAN and AuraSR-v2 cannot hallucinate, so
   they bound what "fidelity preservation" means. Without them the diffusion
   refiners' scores have no reference point.
3. **Sample size.** 4 subjects in the first screen, 5 in the two-batch run.
4. **Parity rule.** Every number is from fal-hosted endpoints; nothing has been
   reproduced on downloaded weights.

Resume this workstream when (1) has a candidate worth self-hosting, or when a
downstream workstream shows realism regressing.
