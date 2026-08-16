# v2.3 PLAN — the detect → localize → repair → verify loop

Status: design. Nothing built.

## 1. Position in the pipeline

The repair loop is a stage, not a model. It runs on a single image plus the
originals it must not damage.

```text
person + garment
       │
       ▼
klein 4B edit  ──►  candidate
       │
       ├── reliability check (blank / low-variance → reseed)   [exists, V2.1]
       ▼
intention-aware guardrail (acceptance map, restore/accept/repair)   [../ideas/INTENTION_AWARE_FIDELITY.md]
       │            └── emits repair_band + protected priors, reused directly below
       ▼
┌─────────────────────────────────────────────┐
│  v2.3 ARTIFACT REPAIR LOOP                  │
│   1 detect    per-class detectors           │
│   2 localize  mask + crop + margin          │
│   3 repair    weakest sufficient mechanism  │
│   4 verify    accept only if strictly better│
│      └── reject → keep the input unchanged  │
└─────────────────────────────────────────────┘
       ▼
auxiliary realism (SeedVR2 ×2, noise 0)
       ▼
final deterministic + VLM checks
```

Placement rationale (H5, to be ablated): repairing before the realism pass lets
SeedVR2 harmonize grain across the repair seam. The counter-argument — that the
realism pass sharpens whatever the repair got wrong — is why order is an
ablation arm, not an assumption.

**Relationship to the auxiliary stage.** They are complements with a hard
division of labour, forced by the evidence: the auxiliary stage owns global
realism (smoothness, photographic accuracy) and has *never* moved
`artifact_fix`; v2.3 owns localized non-logical content and touches nothing
globally. Neither is allowed into the other's territory.

**Relationship to the guardrail.** v2.3 is the implementation of the guardrail's
third decision class. The guardrail already classifies regions
`accept` / `restore` / `repair` and emits a repair band; it stops at "a
low-denoise inpainting pass *may* harmonize this". v2.3 is that pass, generalized
from seams to the full artifact taxonomy, with a verify stage the guardrail does
not currently specify. Where the guardrail's `restore` decision already covers an
artifact (mechanism R1 below), v2.3 defers to it rather than generating.

## 2. Interfaces

Mirrors the guardrail's component-interface style so the two stages compose.

```python
detect_artifacts(image, context) -> list[Finding]
    # context: original person, garment ref, garment mask, acceptance map,
    # protected priors, parsing maps. Detectors are per-class (EXPERIMENT.md §4).

localize(finding, image, context) -> RepairTask
    # mask (soft), crop bbox expanded by context margin, class, severity,
    # narrow text instruction, allowed mechanisms.

repair(task, mechanism_cfg) -> RepairCandidate
    # crop-native resolution. Must not write outside the dilated mask.

verify(base_image, candidate, task, refs) -> VerifyResult
    # accept | reject + reason codes + all metric deltas.

apply_repairs(image, context, cfg) -> RepairResult
    # orchestrates; returns final image, per-task decisions, and the JSON package.
```

```python
class Finding:      class_code; mask_path; bbox; severity; detector; score
class RepairTask:   finding; crop; margin_px; instruction; mechanisms: list[str]
class VerifyResult: accepted: bool; deltas: dict; reason_codes: list[str]
class RepairResult: image; tasks: list[VerifyResult]; fallback_used: bool
```

Persistence: one JSON package per candidate, same shape as the guardrail's
`v2.intent-map` package, with a `findings[]` array carrying class, severity,
mechanism tried, and every verify delta. Non-negotiable — a repair loop whose
decisions are not inspectable is not debuggable.

## 3. Candidate repair mechanisms, ranked

Ranked by **weakest sufficient intervention first**: prefer mechanisms that
cannot hallucinate, then mechanisms that regenerate the least. All are open
weights and license-clean; sources are
[`research/open-weights-model-catalog.md`](../../../research/open-weights-model-catalog.md)
§4.3–4.5.

| # | Mechanism | License / cost | Classes it serves | Why this rank | Risk |
|---|---|---|---|---|---|
| **R1** | **Restore-from-original** — copy the original person's pixels back through the guardrail acceptance map, feathered at the seam. No model. | free, deterministic | A1 (hands the edit had no business touching), A2 (ghost of old garment outline is *not* this — that needs fill), A4 (duplicated limb), A5 (background blob) | Zero hallucination risk, zero cost, and H4 predicts it covers ≥30% of findings. If the original hand was fine, generating a new one is strictly worse than restoring it. | Only valid where the original region is genuinely unedited and geometrically registered; leaves a seam to blend. Cannot help inside the new garment. |
| **R2** | **Hand detailer** — crop hand bbox + margin, inpaint at crop-native resolution with a soft mask, **denoise ≤ 0.3**. Candidates: InstantX Qwen-Image-ControlNet-Inpainting (Apache, 2B, 1328²) or SDXL-inpainting-0.1 (OpenRAIL++, T4-friendly). Paste back via GrowMask + 16–48px Gaussian feather + differential-diffusion seam blend. | Apache / OpenRAIL++; small | A1 primarily, A5 in-region | The recurring artifact site, and the mechanism is well-trodden. | **The catalog's explicit warning: ComfyUI Impact Pack FaceDetailer-style defaults *replace* the region.** Denoise must stay low; a "repaired" hand that is a different hand is a fidelity failure that preservation metrics will not catch. |
| **R3** | **Editor local crop** — send the expanded crop plus a narrow instruction to klein 4B itself ("correct only the left hand; preserve everything else exactly"), composite back through the acceptance map. Per TRY_APPROACH §5 "repair a local crop". | reuses the base model; no new weights | A1, A3, A5, garbled logos | No extra checkpoint to host, and the editor already understands the garment and scene. The only mechanism with a plausible shot at A3 (garment physics), which no inpainter can reason about. | The base model produced the artifact in the first place; it may reproduce it. Instruction-following on tiny crops is unverified. |
| **R4** | **EliGen entity-level regional attention** (DiffSynth, Apache) — regenerate the garment region with face/hands frozen at the attention level rather than by masking. | Apache; self-host only | A2, A3 | Attacks the cause (attention bleed) rather than the symptom, and the freeze is architectural, not a paste-back. | Self-host only — not testable through fal, so it lands after the first round. New to this program; unvalidated here. |
| **R5** | **Mask-fill repair** — LaMa (Apache, CPU-capable, via IOPaint) or Moebius (Apache, 0.22B linear-attention inpainter, claims FLUX-Fill parity at >15× speed). Fill only, no text guidance. | Apache; near-free | A4 (delete a duplicate), A2 (fill where the old garment was longer than the new one) | The correct tool for "remove this thing and make the hole disappear". Cannot invent a garment, which is exactly why it is safe here. | Moebius is Jun 2026 and unvalidated — treat as a probe. LaMa blurs on large holes. |
| **R6** | **Z-Image-Turbo inpaint** (`ZImageInpaintPipeline`, Apache, latent blend + soft masks) | Apache | A5 | Cheapest permissive diffusion repair. | **Deprioritized on our own evidence:** Z-Image measured destructive globally (AuraFace 0.72 on a real photograph that needed no repair). Admissible only strictly outside face and hand regions, and only if R2/R3 fail. |

**Rejected outright:**

| Rejected | Reason |
|---|---|
| Any whole-image realism pass as an artifact fix | `artifact_fix` = 3.00, 14/14 config-batches. Settled. |
| FaceDetailer-style default denoise (0.5+) | Replaces the region. Catalog warning; violates the fidelity gate by construction. |
| FLUX.1-Fill-dev | Non-commercial. Blocked, and no FLUX.2 Fill model exists as of Aug 2026. |
| Retrained / fine-tuned repair models | Out of scope; no training in V2. |

**Automatic QC on every composite:** BargainNet harmony score (libcom, Apache) as
a gate on the paste-back seam, plus PCTNet harmonization available as a
post-composite step if the harmony score fails.

## 4. Arbitration and fallback

The rule, stated once: **never ship a repair that scores worse than its input.**

Per repair task:

1. Try mechanisms in rank order, cheapest first, stopping at the first accepted repair.
2. `verify` compares candidate against the pre-repair image on:
   - `artifact_fix` (pairwise VLM) — must be > 3.00;
   - `no_new_artifacts` — must be ≥ 4;
   - fidelity deltas — `identity_cos`, `garment_sim`, `bg_psnr`, `pose_err`, all within tolerance (TEST.md §3);
   - **containment invariant** — pixels outside the dilated mask must be unchanged. Deterministic, free, and a hard assert: a repair that edits the whole frame is a bug, not a result.
3. Any failure → reject, log reason codes, fall through to the next mechanism.
4. All mechanisms rejected → **ship the unrepaired input**. The loop is allowed to do nothing; doing nothing is the default, not the exception.

Additional invariants, inherited from TRY_APPROACH §6 (preventing cumulative
degradation):

- At most **two** repair tasks applied per image, by descending severity — repeated encode/decode cycles accumulate drift.
- Repairs use the candidate as base (they are narrow); anything that would need a full regeneration is a **retry from the original**, not a repair.
- The original's protected pixels stay available for restoration after every operation.
- The strongest valid image is retained at every step; the loop returns the best that passes all constraints, not the highest mean score.

**The preservation trap.** Per the guardrail's own risk note, paste-back can
inflate preservation metrics while damaging realism. Therefore no repair is ever
approved on preservation metrics alone — `artifact_fix` and `no_new_artifacts`
are required, and human review is the tiebreaker where they disagree with the
deterministic deltas.

## 5. Build sequence

Each step is testable on its own and gated by the step before it.

| # | Step | Depends on | Output |
|---|---|---|---|
| 1 | Freeze the artifact test set and run the annotation pass (class + severity per image). No models beyond the judge. | — | labelled fixture, `v2/runs/artifacts/annotations.csv` |
| 2 | Build detectors (A1 keypoints, A2 boundary gradient + BargainNet, A4 instance count + self-similarity, A5 Laplacian outlier + OCR) and measure agreement with the annotation. **H6 gate.** | 1 | detection precision/recall table |
| 3 | Containment-invariant harness + `verify` stage, tested against deliberately-broken repairs. Build the guard before the thing it guards. | — | verify unit tests |
| 4 | **R1 restore-from-original**, reusing the guardrail acceptance map. **H4 gate.** | 2, 3 | first end-to-end repairs, zero model cost |
| 5 | **R2 hand detailer**, denoise sweep 0.15 / 0.25 / 0.40 (0.40 included as a deliberate breaking-point probe, as `zimage_s035` was in the aux screen). **H1, H3 gates.** | 2, 3 | per-config table |
| 6 | Arbitration: rank order, fallback, two-task cap. Full loop. | 4, 5 | `apply_repairs` |
| 7 | **R3 editor local crop** via klein; the only A3 candidate. | 6 | A3 exploratory results |
| 8 | Order ablation (repair→aux vs aux→repair). **H5 gate.** | 6 | order table |
| 9 | Self-host queue: **R4 EliGen**, **R5 Moebius/LaMa**. | 6 | second-round results |
| 10 | Comparison page in `v2/artifacts/`, generated by a script in `v2/build/`; then the parity re-run on downloaded weights before any number is called final. | 8 | `v2/artifacts/v23_artifact_repair.html` *(not yet generated — v2.3 has not run)* |

Steps 1–6 are the minimum that answers H1. If H1 falsifies at step 5, stop:
region-targeted repair does not work either, and the honest conclusion is that
artifacts must be attacked at the editing stage (prompt, seed, best-of-N
selection) rather than repaired at all.

## 6. Product surface

- **Default in the shipped pipeline:** on, but conservative — R1 and R2 only, severity ≥ 2, two-task cap, all gates enforced.
- **Cost:** R1 is free; R2 runs on a crop, not a frame, so the added latency is a fraction of a full generation. Exact figures pending measurement.
- **Failure mode by design:** the loop no-ops. An image with no detected artifact, or with only rejected repairs, exits byte-identical to how it entered. This is verifiable and should be asserted in tests.
- **Observability:** every finding, mechanism, and verify delta is written to the run package; the artifact rate per class becomes a standing regression metric alongside `wrong_person`.
