# v2.3 — Artifact reduction and removal

**Subject:** reducing or removing artefacts in try-on outputs.
**Status:** design complete, nothing run. All numbers in this workstream are
hypotheses until [RESULTS.md](RESULTS.md) is filled.
**Last updated:** 2026-08-14.

## Summary

klein 4B is the editing base, and its one accepted quality downside is
"occasional AI artifacts" ([V2.1_RESULTS.md](../results_summary/V2.1_RESULTS.md)).
The auxiliary realism stage cannot fix them: across two independent rounds and
14 config-batches, the VLM `artifact_fix` criterion scored **exactly 3.00
(= no change) for every configuration** — no global realism pass has ever
repaired an artifact. That is the founding premise of this workstream. v2.3
therefore builds a **detect → localize → repair → verify** loop that operates on
regions, not on whole images: find the artifact, cut a crop around it, repair it
with the weakest mechanism that will do the job, and ship the repair only if it
measurably beats the input it replaced. It sits between the editing model and
the auxiliary realism stage, reuses the `repair` decision class and seam-band
machinery already specified in
[INTENTION_AWARE_FIDELITY.md](../ideas/INTENTION_AWARE_FIDELITY.md) and the
crop-repair action in
[TRY_APPROACH_ITERATIVE_IMAGE_TEXT_EDITING.md](../ideas/TRY_APPROACH_ITERATIVE_IMAGE_TEXT_EDITING.md),
and adds no new evaluation axes — it uses the existing realism definitions from
[SCORING_CRITERIA.md](../SCORING_CRITERIA.md).

## Documents

| Doc | One line |
|---|---|
| [EXPERIMENT.md](EXPERIMENT.md) | The artifact taxonomy (five classes), how each class is detected and scored, and seven falsifiable hypotheses. |
| [PLAN.md](PLAN.md) | Architecture: where the repair loop sits, its interfaces, the six candidate repair mechanisms ranked, the never-worse fallback rule, and the build sequence. |
| [TEST.md](TEST.md) | How the artifact-bearing test set is assembled, the metrics and hard gates, the ablation matrix, sample sizes and cost estimate. |
| [RESULTS.md](RESULTS.md) | Stub. Schema and empty tables, ready to fill; status "not yet run". |

## How this fits

v2.3 is one workstream. Program-level results, the model pool, the test-set
definitions and the standing decisions live one level up in
[`prd/v2/results_summary/`](../results_summary/) —
[CONDITIONS.md](../results_summary/CONDITIONS.md) for setup,
[V2.1_RESULTS.md](../results_summary/V2.1_RESULTS.md) for current verdicts.
Nothing in this directory supersedes those; when v2.3 produces results they get
rolled up there.

Constraints inherited without exception: **open weights only in the deployed
path**; fal permitted for iteration on open-weights checkpoints only; every
final number re-run on downloaded weights (parity rule); the VLM judge (gpt-5.5)
is an instrument, not part of the product.
