# v2.3 EXPERIMENT — artifact taxonomy, detection, and hypotheses

Status: not yet run. Everything below is design and hypothesis.

## 1. Goal

Reduce the rate and severity of artifacts in klein 4B try-on outputs, without
losing garment fidelity, identity, or scene, and without introducing new
artifacts in the act of repairing old ones.

## 2. Founding evidence

| Finding | Source | Consequence for v2.3 |
|---|---|---|
| `artifact_fix` = **3.00 exactly** (no change) for every configuration, across 2 independent rounds and 14 config-batches | [V2.1_RESULTS.md](../results_summary/V2.1_RESULTS.md) §aux two-batch, [SCORING_CRITERIA.md](../SCORING_CRITERIA.md) §7.4 | Whole-image passes do not repair artifacts. v2.3 must be **region-targeted** or it will reproduce 3.00. |
| klein's accepted downside is "occasional AI artifacts"; realism 4.03 | V2.1_RESULTS.md | The problem is real but sparse — the test set must be enriched for artifacts, not sampled uniformly. |
| Hands are the recurring site: triage hands FASHN **3.25**, klein **4.15**; Testset2 hands klein 4.15, FASHN 4.08 | V2.0/V2.1 results, `v2/runs/ts2/ts2_vlm.csv` | A hand-region detailer is the first concrete mechanism. |
| Z-Image at global strength drops AuraFace to 0.72 **on a real photograph that needed no repair** | V2.1 aux two-batch, control arm | Any repair mechanism must be region-limited and must be run against a clean control. |
| Pixel-perfect paste-back can inflate preservation metrics while damaging realism | [INTENTION_AWARE_FIDELITY.md](../ideas/INTENTION_AWARE_FIDELITY.md) §risks | Preservation metrics alone cannot approve a repair. Realism must be scored alongside, every time. |

## 3. Artifact taxonomy

"Reduce artifacts" is unmeasurable without a class list. The definition is
inherited from the realism axis in [SCORING_CRITERIA.md](../SCORING_CRITERIA.md)
§2 — *"no additional artifacts — non-logical items: extra limbs/fingers,
floating seams, impossible garment physics, duplicated objects"* — and split
into the five classes below. Each class is a separate detector, a separate
repair path, and a separate success bar.

| Code | Class | Definition (what counts) | Explicitly not this class |
|---|---|---|---|
| **A1** | Anatomical / hands | Extra, missing, fused or malformed fingers; extra or missing limbs; impossible joint angles; hand merging into garment | A hand that is simply blurry (→ A5) |
| **A2** | Seam / compositing | Floating seams; hard or haloed edge at garment↔skin or garment↔background boundary; tone, grain or lighting discontinuity across a boundary; ghost of the original garment at its old outline | Legitimate garment construction seams |
| **A3** | Garment physics | Garment that cannot exist: sleeve terminating in nothing, collar detached from neck, strap passing through an arm, drape contradicting gravity or pose, occlusion order violated (garment behind an arm it should cover) | A garment that is the wrong garment (that is a fidelity failure, not an artifact) |
| **A4** | Duplication | Duplicated objects, limbs, buttons, pockets, logos, or a second person; repeated garment element that appears once in the reference | Symmetric elements that are correct by design (two cuffs) |
| **A5** | Texture / distilled | Localized high-frequency noise blobs, mush patches, banding, tiling; garbled text or logo on a print that is legible in the reference | Global plastic-skin smoothness — that belongs to the auxiliary realism stage, not here |

**Scope boundary.** A5 overlaps the auxiliary stage. v2.3 owns A5 only where it
is **localized and bounded** (a garbled logo, a noise blob) — global softness and
plastic skin remain with SeedVR2. A1–A4 are wholly v2.3's, because the evidence
says the auxiliary bucket never repairs them.

## 4. Detection and scoring, per class

Two independent readings per class: a **deterministic detector** (free, local,
runs on every image) and the **VLM reading** (authoritative for realism, per
CONDITIONS.md §4). Where the detector is weak, that is stated rather than
papered over.

| Class | Deterministic detector | Confidence | VLM signal | Localization source |
|---|---|---|---|---|
| A1 | DWPose / RTMPose hand keypoints: per-finger confidence, keypoint count vs 21, left/right instance count vs expected; flag on low-confidence or count mismatch | medium — keypoint failure correlates with malformed hands but also with occlusion | `hands` criterion (editing rubric); `no_new_artifacts` | hand bbox from keypoints, dilated |
| A2 | Gradient-magnitude ratio along the garment-mask boundary band vs garment interior; BargainNet harmony score (libcom) on the composite; PSNR discontinuity across the band | medium-high — this is a well-posed signal | `clean` criterion; `artifact_fix` pairwise | the mask boundary band itself |
| A3 | **None reliable.** Declared unsolved. Optional weak proxy: garment-mask connectivity (a garment component not adjacent to the person mask) | low | `realism` + `clean`; VLM is the only usable detector here | VLM-returned region description → SAM 3 text prompt |
| A4 | SAM 3 text-promptable instance counts ("person", "hand", "button") vs expected; normalized cross-correlation self-similarity scan for repeated patches | medium | `clean` | the duplicate instance mask |
| A5 | Local Laplacian-energy outlier map vs image median; OCR (legibility of text prints, reference vs output) | medium | `clean`, `realism`; `smoothness` on the aux rubric | outlier blob mask |

**Severity.** Each finding is scored `severity ∈ {1,2,3}` (1 = visible only at
crop zoom, 2 = visible at full frame, 3 = ruins the image). Repair is attempted
for severity ≥ 2 first; severity 1 is logged and used only for regression
tracking. Severity is assigned by the VLM annotation pass and frozen with the
test set (TEST.md §2), so it is a property of the fixture, not of a run.

**Scoring an artifact repair.** Unchanged instruments, per SCORING_CRITERIA.md §4:
- `artifact_fix` (pairwise, BEFORE = pre-repair image, AFTER = post-repair image) — the primary number. 3.00 = no change, which is the value to beat.
- `no_new_artifacts` — the guard. A repair that fixes A1 and creates A2 is a failure.
- Editing-rubric `clean`, `hands`, `realism` on the final image — comparable to the existing arm tables.
- Fidelity preservation via the deterministic editing metrics (`garment_sim`, `identity_cos`, `bg_psnr`, `pose_err`), measured pre- vs post-repair.

## 5. Success bar, per class

Per-class targets on the artifact-bearing subset (TEST.md §2). These are targets
set in advance, not predictions.

| Class | Success looks like | Minimum to call the mechanism useful |
|---|---|---|
| A1 | Finger count and keypoint confidence restored; VLM `hands` improves ≥ +0.5 on the affected subset | `artifact_fix` ≥ 3.5, `no_new_artifacts` ≥ 4.5 |
| A2 | Boundary gradient ratio returns to the garment-interior distribution; BargainNet harmony improves | `artifact_fix` ≥ 3.5, no fidelity gate breach |
| A3 | VLM stops naming the physics violation in its note field | Any movement above 3.00 is informative; treat as exploratory |
| A4 | Instance count matches expectation after repair | `artifact_fix` ≥ 3.5, `no_new_artifacts` = 5.0 (a duplicate repair that adds anything is a hard failure) |
| A5 | Text legibility restored / blob energy back to median | `artifact_fix` ≥ 3.5 without garment_sim loss |

**Program-level bar:** mean `artifact_fix` > 3.00 with statistical daylight over
the 14 config-batches of 3.00 that preceded it, and zero fidelity-gate breaches.
Given the sample sizes available (TEST.md §5) this will be directional evidence
plus human review, not a settled result — the same caveat carried by every other
V2 number.

## 6. Hypotheses (falsifiable)

| # | Hypothesis | Falsified if |
|---|---|---|
| **H1** | A region-targeted repair moves `artifact_fix` above 3.00, which no global pass has ever done (0/14 config-batches). | Targeted repair also scores 3.00, or the gain is inside judge noise on a repeat run. |
| **H2** | Hands (A1) are the single most frequent artifact class in klein outputs, ≥ 40% of severity-≥2 findings. | Another class dominates. Consequence: build that class's mechanism first instead. |
| **H3** | Low-denoise crop repair (≤ 0.3) preserves fidelity: Δ`identity_cos` ≥ −0.01 and Δ`garment_sim` ≥ −0.01 vs the pre-repair image, while denoise ≥ 0.5 does not. | A ≤0.3 repair still drifts identity or garment beyond tolerance — in which case generative repair on person regions is off the table and only restore-from-original survives. |
| **H4** | A meaningful fraction (≥ 30%) of severity-≥2 findings sit in regions the edit should never have touched (hands, background, face), so they are repairable by copying the original pixels back — zero model cost. | Most artifacts fall inside the legitimately edited garment region, where the original has no valid pixels to restore. |
| **H5** | Repair before the auxiliary realism stage beats repair after it, because SeedVR2 then harmonizes the repair seam rather than sharpening it. | Order makes no measurable difference, or after-aux wins. |
| **H6** | Deterministic detection is good enough to drive the loop unsupervised: precision ≥ 0.7 at recall ≥ 0.6 against the frozen VLM+human annotation. | Detection is noise. Consequence: fall back to VLM-proposed localization (a judge call per image), which is viable for evaluation but expensive in the deployed path. |
| **H7** | The verify stage keeps the loop safe: fewer than 10% of accepted repairs introduce a new artifact (`no_new_artifacts` < 4). | The guard leaks — repair is net-negative and must ship disabled by default. |

## 7. Non-goals

- Not a replacement for the auxiliary realism stage. SeedVR2 stays; it handles
  smoothness and photographic accuracy, which it demonstrably does well.
- Not a fidelity workstream. Fidelity here is a constraint, never an objective —
  a repair that improves `garment_sim` is not thereby a good repair.
- Not retraining anything. Off-the-shelf open-weight checkpoints only.
- Not the blank-frame / generation-failure problem. That is a reliability
  concern with its own mechanism (blank detection + reseed) already noted in
  V2.1; a black frame is not an artifact to repair, it is a run to discard.
