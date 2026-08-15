# v2.2 — Accuracy, failure reduction, and reference attention

**Status:** designed, not yet run. No generation or judging has been paid for
against this workstream.

**Owner:** Ray. **Base model:** FLUX.2 klein 4B (fixed by
[V2.1_RESULTS.md](../results_summary/V2.1_RESULTS.md); v2.2 does not re-open the
model choice).

## Summary

v2.1 closed the editing-base contest and accepted three klein downsides.
**v2.2 attacks exactly two of them — attention and failure — and nothing else.**
The question it answers is narrow: *did the model make the correct change?*
Three ways that fails, all three in scope:

1. **It pastes the wrong person** — content from the garment reference (the
   reference model's face, body, background) leaks into the output.
2. **It transfers the wrong clothes** — a plausible garment that is not the
   reference garment, or the garment rendered imprecisely.
3. **It does nothing, or returns garbage** — the requested change is simply not
   made, or the frame is degenerate (one solid-black frame in 16 triage runs).

Sub-workstreams:

| | Scope |
|---|---|
| **v2.2.1** | Crop the **garment** reference — segment the clothes/body the model can see, place on white — and measure how much attention improves |
| **v2.2.2** | Crop **both** garment and person; run the edit on the person crop; composite the person back onto the original background |
| **v2.2.3** | Failure catch — first check whether v2.2.1/v2.2.2 already remove the "transformation simply not made" class; add deterministic gates with automatic reseed only if failures survive |

**Out of scope, moved out 2026-08-15:** protected-region restore (former
component [C]) and the predicted-warp metric (former [D]). Region restore is
parked in [../V2.x_DIRECTIONS.md](../V2.x_DIRECTIONS.md) direction 1, with its
candidate slots (v2.2.4 or v2.5) and the condition that would trigger each —
v2.2.2 may make it unnecessary by preventing background damage structurally.
Artifact and seam repair remain v2.3.

Everything in the deployed path is open-weights and has a pass-through fallback;
every claim below is a hypothesis until the ablation in [TEST.md](TEST.md) is run.

## Documents

| Doc | Contents |
|---|---|
| [EXPERIMENT.md](EXPERIMENT.md) | Goals, the five falsifiable hypotheses, per-hypothesis success and failure criteria, and the named failure modes being attacked. |
| [PLAN.md](PLAN.md) | Where each mitigation sits in the pipeline, interfaces and signatures, fallback chains, config knobs, and the build sequence in dependency order. |
| [TEST.md](TEST.md) | Test set, arms and configs, deterministic and VLM metrics, gates, sample sizes, the A/B ablation on identical seeds, files and flags to add, and the cost estimate. |
| [RESULTS.md](RESULTS.md) | Stub — status "not yet run", empty tables in their final shape, artifacts link placeholder. |

## How this fits

v2.2 is one workstream of the V2 program. Program-level results, the current
model leaderboard, and the standing decisions live in
[`prd/v2/results_summary/`](../results_summary/) —
[CONDITIONS.md](../results_summary/CONDITIONS.md) for constraints, model pool,
and test sets; [V2.1_RESULTS.md](../results_summary/V2.1_RESULTS.md) for the
decision this workstream inherits. Scoring rules are fixed in
[SCORING_CRITERIA.md](../SCORING_CRITERIA.md) and are not redefined here.

Scope boundaries with the sibling workstreams:

| Concern | Owner |
|---|---|
| Editing-base selection | v2.1 (closed) |
| Reference attention, garment accuracy, generation-failure handling, accidental regeneration of protected regions | **v2.2** |
| Seam and artifact repair, region-targeted detailing, the auxiliary realism stage | v2.3 |

[INTENTION_AWARE_FIDELITY.md](../ideas/INTENTION_AWARE_FIDELITY.md) is split
across v2.2 and v2.3 along that line: its accept/restore decision for protected
content is here, its `repair` band and seam-harmonization pass are v2.3.
