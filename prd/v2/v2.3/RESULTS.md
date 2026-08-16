# v2.3 RESULTS — artifact reduction

**Status: not yet run.** Every table below is an empty schema. No number in this
file is claimed until it is filled from a real run and the parity rule is
satisfied.

Design: [EXPERIMENT.md](EXPERIMENT.md) · [PLAN.md](PLAN.md) · [TEST.md](TEST.md).
Program-level results: [`prd/v2/results_summary/`](../results_summary/).

| Field | Value |
|---|---|
| Run date | — |
| Fixture | `v2/runs/artifacts/` (n = —, controls = —) |
| Editing base | FLUX.2 klein 4B |
| Judge | gpt-5.5, blind, schema-validated |
| Weights source | fal (directional) / downloaded (parity) — — |
| Comparison page | `v2/artifacts/v23_artifact_repair.html` *(not yet generated — v2.3 has not run)* — *not yet generated* |

## 1. Fixture composition

| Source | Description | n | Severity ≥2 findings |
|---|---|---|---|
| A | klein on Testset2 | — | — |
| B | klein on triage `test_set/` | — | — |
| C | Donor arms (off-base) | — | — |
| D | Deliberate bad generations | — | — |
| E | Clean controls (real photos) | — | n/a |

## 2. Artifact class distribution (frozen annotation)

Answers H2.

| Class | Definition | instances | % of severity ≥2 | mean severity |
|---|---|---|---|---|
| A1 anatomical / hands | | — | — | — |
| A2 seam / compositing | | — | — | — |
| A3 garment physics | | — | — | — |
| A4 duplication | | — | — | — |
| A5 texture / localized | | — | — | — |

## 3. Detector agreement (H6)

Bar: precision ≥ 0.7 at recall ≥ 0.6.

| Class | Detector | precision | recall | verdict |
|---|---|---|---|---|
| A1 | DWPose/RTMPose keypoints | — | — | — |
| A2 | boundary gradient + BargainNet | — | — | — |
| A3 | (none — VLM only) | n/a | n/a | n/a |
| A4 | SAM 3 instance count + self-similarity | — | — | — |
| A5 | Laplacian outlier + OCR | — | — | — |

## 4. Repair leaderboard

Primary table. **3.00 = no change** — the value 14/14 global config-batches
scored. Anything at 3.00 here means region targeting failed too (H1 falsified).

| arm | mechanism | artifact_fix | no_new_artifacts | clean | hands | realism | fidelity gate | accepted / attempted |
|---|---|---|---|---|---|---|---|---|
| 0 | no repair (control) | 3.00 (def.) | — | — | — | — | n/a | n/a |
| 1 | R1 restore-from-original | — | — | — | — | — | — | — |
| 2 | R2 detailer d=0.15 | — | — | — | — | — | — | — |
| 3 | R2 detailer d=0.25 | — | — | — | — | — | — | — |
| 4 | R2 detailer d=0.40 (probe) | — | — | — | — | — | — | — |
| 5 | R3 editor local crop | — | — | — | — | — | — | — |
| 6 | full loop | — | — | — | — | — | — | — |

## 5. Per-class repair outcome

| Class | best mechanism | artifact_fix | no_new_artifacts | meets §5 bar (EXPERIMENT) |
|---|---|---|---|---|
| A1 | — | — | — | — |
| A2 | — | — | — | — |
| A3 | — | — | — | — |
| A4 | — | — | — | — |
| A5 | — | — | — | — |

## 6. Fidelity preservation (H3, H7)

Deltas are post-repair minus pre-repair. Negative beyond tolerance = gate breach.

| arm | Δ identity_cos | Δ garment_sim | Δ bg_psnr | Δ pose_err | containment pass | BargainNet Δ | breaches |
|---|---|---|---|---|---|---|---|
| 1 | — | — | — | — | — | — | — |
| 2 | — | — | — | — | — | — | — |
| 3 | — | — | — | — | — | — | — |
| 4 | — | — | — | — | — | — | — |
| 5 | — | — | — | — | — | — | — |
| 6 | — | — | — | — | — | — | — |

## 7. Order ablation (H5)

| order | artifact_fix | realism | identity_cos | garment_sim | notes |
|---|---|---|---|---|---|
| repair → aux (SeedVR2) | — | — | — | — | — |
| aux (SeedVR2) → repair | — | — | — | — | — |

## 8. Clean-control damage (arm 9)

A loop that fires on a real photograph is broken. Repairs attempted should be ~0.

| metric | value |
|---|---|
| Findings raised on clean photos | — |
| Repairs attempted | — |
| Repairs accepted | — |
| Δ identity_cos | — |
| Δ realism | — |

## 9. Mask margin sweep

| margin (px) | artifact_fix | seam quality (BargainNet) | containment pass |
|---|---|---|---|
| 8 | — | — | — |
| 16 | — | — | — |
| 32 | — | — | — |

## 10. Hypothesis verdicts

| # | Hypothesis | Verdict | Evidence |
|---|---|---|---|
| H1 | Region-targeted repair moves artifact_fix above 3.00 | — | — |
| H2 | Hands are ≥40% of severity-≥2 findings | — | — |
| H3 | Denoise ≤0.3 preserves fidelity, ≥0.5 does not | — | — |
| H4 | ≥30% of findings are repairable by restore-from-original | — | — |
| H5 | Repair before aux beats repair after | — | — |
| H6 | Detection reaches precision 0.7 @ recall 0.6 | — | — |
| H7 | <10% of accepted repairs introduce a new artifact | — | — |

## 11. Caveats (to carry forward)

1. Sample size — directional evidence plus human review, not a settled result.
2. Fixture is deliberately artifact-enriched; its artifact rate is **not** a population rate.
3. Donor-arm images (source C) calibrate detectors only and must not enter any shipping decision.
4. Parity rule outstanding until the selected mechanism is re-run on downloaded weights.
5. Preservation-inflation risk — no repair approved on preservation metrics alone.

## 12. Next

- —
