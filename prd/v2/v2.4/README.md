# v2.4 — Auxiliary realism, revisited

**Subject:** whether anything beats `seedvr2_x2_noise0` in the auxiliary slot.
**Status:** deferred by decision (Ray, 2026-08-15) — the current auxiliary model
is good enough, so this workstream is parked until v2.1.1, v2.2 and v2.3 land.
Nothing here is scheduled and nothing has been run.
**Last updated:** 2026-08-15.

## Summary

The auxiliary stage takes a single image and returns the same image, more
realistic — scored against **its own input**, gated on fidelity preservation
(`SCORING_CRITERIA.md`). `seedvr2_x2_noise0` won that screen twice: once on
FASHN outputs, then again on a two-batch run whose **control batch of real
photographs** killed Z-Image Turbo by exposing it as destructive on inputs that
needed no repair ([V2.1_RESULTS.md](../results_summary/V2.1_RESULTS.md)).

That is a stronger evidence base than most of the pipeline has, which is why
this workstream is deferred rather than active: **the marginal value of a better
aux model is currently lower than validating the composite end to end, proving
parity on downloaded weights, or repairing artifacts** — the last of which the
aux stage provably cannot do (`artifact_fix` = 3.00 across 14 config-batches;
that finding founded [v2.3](../v2.3/)).

## What this workstream would test

| Candidate | Why it is queued |
|---|---|
| **Z-Image Base + PAI Fun tile-ControlNet + UltraReal LoRA** | The highest-priority queued test. Z-Image *Turbo* drifts identity badly (AuraFace 0.61–0.72); the tile-ControlNet variant is the direct attempt to keep its realism without the drift. **Self-host only** — fal serves Z-Image Base as text-to-image. Cells already written: notebook §13 |
| Real-ESRGAN · AuraSR-v2 | The **zero-drift floor**. Neither hallucinates, so they bound how much of SeedVR2's realism gain is genuinely restoration rather than invention — this is what makes the diffusion refiners' scores interpretable |
| HiDream-O1-Image | Eliminated as an *editing* arm, but scored the highest VLM realism of any arm tested (4.08). Worth one screen in the bucket where realism is the objective |
| OSEDiff · DiffBIR v2 | Cheap one-step / heavy-degradation Apache alternatives, untested |
| GFPGAN · RestoreFormer++ · PMRF | Face-crop scope only. PMRF's objective ("restore without changing who it is") is the right shape for the identity problem |
| Frequency-separation detail transfer | Not a model — the garment-fidelity insurance policy: paste the original high-frequency detail back inside the garment mask after any refinement pass |

## Open questions it would answer

1. Does anything beat SeedVR2 at noise 0 on **both** batches — generated inputs
   *and* the real-photo control — or is the current leader already the ceiling?
2. How much of SeedVR2's realism gain survives comparison against the zero-drift
   floor? If Real-ESRGAN scores close, the diffusion refiner is buying little.
3. Does the aux stage need to run at all when the editing base already produces
   a clean frame, or should it be **conditional** on a measured realism deficit?
4. Does the leader hold on **downloaded weights** (parity rule) — SeedVR2's
   numbers, like everything else, are currently fal numbers.

## Documents

Per the workstream schema in [../README.md](../README.md), this directory will
carry `EXPERIMENT.md`, `PLAN.md`, `TEST.md` and `RESULTS.md`. They are **not
written yet** — they are due before any run, and this workstream has none
scheduled. This README is deliberately the only document here.

## How this fits

Deferred behind, in order: **v2.1.1** (klein parity on downloaded weights,
distilled vs base), the klein → SeedVR2 composite validated end to end, **v2.2**
(accuracy, failures, attention) and **v2.3** (artifacts). Program-level state
lives in [`prd/v2/results_summary/`](../results_summary/); nothing here
supersedes it.

Constraints inherited without exception: **open weights only in the deployed
path**; fal permitted for iteration on open-weights checkpoints only; every
final number re-run on downloaded weights; the VLM judge (gpt-5.5) is an
instrument, not part of the product.
