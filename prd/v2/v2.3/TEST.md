# v2.3 TEST — artifact-bearing fixture, gates, ablations, cost

Status: not yet run.

## 1. What the tests have to establish

1. That artifacts can be **detected** automatically at a usable precision/recall (H6).
2. That a **region-targeted** repair moves `artifact_fix` off 3.00 (H1) — the number no global pass has ever moved.
3. That repair **costs nothing in fidelity** (H3) and **adds nothing new** (H7).
4. Which **mechanism** and which **denoise / margin** settings do it (mechanism ranking, PLAN §3).
5. Where the stage **belongs** relative to the auxiliary realism pass (H5).

## 2. The artifact-bearing fixture

Uniform sampling wastes the budget — klein's artifacts are occasional. The
fixture is deliberately enriched, and that enrichment is declared so no one later
reads its artifact rate as a population rate.

| Source | What | n (target) | Role |
|---|---|---|---|
| **A** | klein 4B outputs on Testset2, `v2/runs/ts2/outputs/klein_4b_edit__ts2_*.png` | 13 | The deployed case. Includes the two known-bad rows: **`ts2_12`** (VLM clean 2, scene 1, realism 2 — the worst klein output on record) and **`ts2_07`** (clean 3). |
| **B** | klein triage outputs on the V1 `test_set/`, `v2/runs/triage_klein_4b_edit_*` | 4 | Lower-resolution regime; different failure texture. |
| **C** | Other arms' outputs as **artifact donors** — `fashn_v15` (triage hands 3.25), `firered_edit`, `hidream_o1_edit` | ~10 | Populates classes klein produces too rarely to sample. **Off-base: never used for shipping decisions**, only to exercise and calibrate detectors and mechanisms. |
| **D** | Deliberate bad generations — klein reseeded on the hardest pairs, plus the `test_set/` hand-over-torso quota (7 pairs) which is the A1 stress case by construction | ~10 | Guarantees severity-3 cases exist to repair. |
| **E** | **Clean control** — real photographs from `Testset2/people/`, unedited | 5 | The aux two-batch methodology, reused: run the whole loop on images that need no repair. Anything it changes is damage. A loop that fires on a real photograph is broken. |

Target: **~40 images plus the 5 controls**, stratified to at least **5
severity-≥2 instances per taxonomy class A1–A5**. If a class cannot reach 5
instances from A–D, that is itself a finding (that class is rare) and it is
reported rather than padded.

**Annotation pass (step 1, before any repair runs).** Every fixture image gets a
VLM proposal of `{class, bbox, severity}` per finding, confirmed or corrected by
human review, then **frozen**. The frozen annotation is the ground truth for
detector precision/recall (H6) and the denominator for repair rate. It is a
property of the fixture, not of a run, and does not get re-derived per config.

Stored as `v2/runs/artifacts/` (images, `annotations.csv`, `findings.jsonl`,
per-config metric CSVs), following the existing `v2/runs/` conventions.

## 3. Metrics and gates

### Primary (realism, VLM — authoritative per CONDITIONS.md §4)

| Metric | Instrument | Bar |
|---|---|---|
| `artifact_fix` | pairwise VLM, BEFORE = pre-repair, AFTER = post-repair | > 3.00 to be non-null; ≥ 3.5 per class to call a mechanism useful |
| `no_new_artifacts` | same call | ≥ 4 required; this is a **hard run-time gate**, not a report line |
| `clean`, `hands`, `realism` | editing rubric on the final image | comparable to the existing arm tables |

### Fidelity-preservation gate (deterministic, hard, per repair)

Measured pre- vs post-repair on the same image. Any breach rejects the repair.

| Metric | Tolerance | Rationale |
|---|---|---|
| `identity_cos` (AuraFace) | Δ ≥ −0.01 | Identity degradation is the standing V2 regression. Zero appetite. |
| `garment_sim` (FashionSigLIP) | Δ ≥ −0.01 | Garment is the ×2-weight objective. |
| `bg_psnr` | Δ ≥ −0.5 dB | Repairs must not repaint the scene. |
| `pose_err` | Δ ≥ −0.005 (torso-normalized) | A repaired hand must be in the same place. |
| **containment** | pixels outside the dilated repair mask **unchanged** (feather band excepted) | Free, deterministic, and catches the whole class of "the repair pass rewrote the frame" bugs. Hard assert. |
| BargainNet harmony (libcom) | must not decrease | Automatic seam QC on the composite. |

### Guards against known failure modes

| Guard | What it catches | Source of the concern |
|---|---|---|
| **No-new-artifacts guard** | Repair that fixes A1 and creates A2 | SCORING_CRITERIA §4 rubric |
| **Clean-control guard** | The loop firing on images that need no repair | aux two-batch Batch A methodology |
| **Preservation-inflation guard** — realism must be reported alongside every preservation delta; a repair may not be approved on preservation alone | Paste-back that scores beautifully and looks worse | INTENTION_AWARE_FIDELITY §risks |
| **`wrong_person`** carried through unchanged | Multi-identity regression | V2.1 standing check |

## 4. Ablation design

Fixed: fixture, seeds, judge, prompt templates. One variable per arm.

| # | Arm | Varies | Answers |
|---|---|---|---|
| 0 | **Control — no repair** | — | The baseline every arm is scored against |
| 1 | R1 restore-from-original only | mechanism | H4; the zero-model floor, the analogue of Real-ESRGAN's zero-drift floor in the aux screen |
| 2 | R2 hand detailer @ denoise 0.15 | denoise | H3 |
| 3 | R2 hand detailer @ denoise 0.25 | denoise | H3 |
| 4 | R2 hand detailer @ denoise 0.40 | denoise | **Deliberate breaking-point probe** — expected to fail the fidelity gate, included so the gate's behaviour is demonstrated, as `zimage_s035` was in the aux screen |
| 5 | R3 editor local crop (klein, narrow instruction) | mechanism | A3 viability |
| 6 | Full loop, rank-ordered arbitration | mechanism | The shipped configuration |
| 7 | Full loop, mask margin 8 / 16 / 32 px | localization | Seam quality vs containment |
| 8 | repair → aux vs aux → repair | order | H5 |
| 9 | Full loop on the **clean control** set | input | Damage measurement |
| — | R4 EliGen, R5 Moebius/LaMa | mechanism | Deferred to the self-host round |

Arms 2–4 and 7 run only on the A1 subset (the classes they serve); arms 0, 1, 6,
8 run on the full fixture. Detector evaluation (H6) is a separate, model-free
pass over the frozen annotation and costs nothing.

## 5. Sample sizes and cost

**Sample size is small and the conclusions are directional.** This is the same
caveat carried by every V2 number (13 pairs on Testset2, 4 on triage, 4 images on
the first aux screen) and it is not being quietly dropped here. With ~40 images
and ~5 instances per class, a per-class result rests on single digits. Human
review is part of the instrument, not a garnish.

Rough volumes:

| Item | Count |
|---|---|
| Fixture images (A–D) | ~40 |
| Clean controls (E) | 5 |
| Annotation judge calls | ~45 (one per image) |
| Repair generations, arms 1–8 | ~40 × 8 arms, most on **crops** not frames ≈ 320 |
| Pairwise judge calls (BEFORE/AFTER per repaired image per arm) | ≈ 300 |

**Cost estimate — unverified, stated as an estimate.** Assumptions: crop-level
repairs cost materially less than the ~$0.20/image full-pipeline figure observed
on prior runs, since they run at crop resolution; judge calls are priced as in
the aux screens. On those assumptions the full matrix lands in the
**$10–20** range, dominated by judge calls rather than generation. R1 and the
detector evaluation are free. Nothing here is spent until the numbers are
confirmed against a metered dry run of ~10 calls.

**Parity rule.** Every repair mechanism selected through fal must be re-run on
downloaded weights before any figure is claimed final — same rule as the editing
and auxiliary buckets (CONDITIONS.md §1). SDXL-inpainting and LaMa are small
enough to run locally; the Qwen inpainting stack and EliGen need the Colab A100.

## 6. Reporting

Results go into [RESULTS.md](RESULTS.md) using the tables already stubbed there,
and a visual comparison page at `v2/artifacts/artifact_repair.html` generated by
a script in `v2/build/` (following `make_compare.py` / `aux_batch.py`). Every
repaired image is shown as BEFORE / crop-zoom / AFTER, because artifact claims
that cannot be checked at crop zoom are not claims. Rolled up to
`prd/v2/results_summary/` once there is a verdict.
