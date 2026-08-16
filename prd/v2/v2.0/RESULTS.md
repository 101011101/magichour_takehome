# v2.0 Results — klein 4B distilled is the editing base

**Status: closed, decided 2026-08-14 (Ray).**

> **Reconstructed 2026-08-15.** See [README.md](README.md). The numbers are not
> re-derived here — they live in the program scoreboards, which were written at
> the time. This document is the workstream-level index into them.

## Where the numbers are

| What | Where |
|---|---|
| **Evidence** — status board, all three run tables, per-arm elimination reasons | [../results_summary/V2.0_RESULTS.md](../results_summary/V2.0_RESULTS.md) |
| **Decision** — klein 4B distilled chosen, why not FASHN, accepted downsides, distilled-vs-base head-to-head | [../results_summary/V2.1_RESULTS.md](../results_summary/V2.1_RESULTS.md) |
| Setup, model pool rationale, test-set definitions | [../results_summary/CONDITIONS.md](../results_summary/CONDITIONS.md) |

The decision writeup carries a **V2.1** number because that is when it was
written down, not because the v2.1 workstream produced it. The runs behind it are
this workstream's; v2.1 (image realism) took klein as given.

## Artifact pages

| Page | What it shows |
|---|---|
| [`v2/artifacts/v20_arms_ts2.html`](../../../v2/artifacts/v20_arms_ts2.html) | The four editing arms on Testset2, 13 pairs, split by pair kind |
| [`v2/artifacts/v20_klein_variant.html`](../../../v2/artifacts/v20_klein_variant.html) | klein distilled vs base, ordered worst-for-base first |
| [`v2/artifacts/v20_coverage.html`](../../../v2/artifacts/v20_coverage.html) | Each arm's access path and the outstanding parity gap |
| [`v2/artifacts/v20_triage_v1set.html`](../../../v2/artifacts/v20_triage_v1set.html) | The first wave on the V1 `test_set/` — superseded composite, kept for the record |

## Decision

**FLUX.2 klein 4B distilled** (`fal-ai/flux-2/klein/4b/distilled/edit`) — leads
VLM fidelity (4.41), realism (4.03) and garment transfer (4.08) on Testset2, and
tops the V1-set deterministic triage (0.778), so it leads on both sets. Apache
2.0, ~13GB, sub-second: self-hostable without an A100.

**FASHN v1.5 is retained as the documented fallback** for the
strict-preservation case. It wins identity (0.971 vs 0.903), background (5.00
scene, 27.5 dB) and the deterministic composite (0.835) — it preserves the
original photo better than anything tested — but it transfers garments
conservatively (garment 3.33, lowest of the three serious arms), and garment
transfer is the ×2 objective. It also carries a hard availability risk: pose
detection runs in-pipeline and **errors the whole call** when it fails, on 1 of
13 pairs.

### Eliminated, with the reason

| Arm | Why |
|---|---|
| **FireRed-Image-Edit v1.1** | Failed garment transfer outright — VLM garment 2.00. The identity-consistency-loss hypothesis did not survive contact with the task |
| **HiDream-O1-Image** | **Re-renders the frame instead of editing it** (scene 3.08, bg PSNR 14.1 against FASHN's 5.00 / 27.5 dB, with visible reframing and pose change); **no-ops on outerwear** (garment 1/5 on three of four `duo_lookbook` coats); and the **only arm to substitute the reference's person** (`wrong_person` 0.15). Its single win was realism 4.08 — an argument for re-screening it in the auxiliary bucket, not the editing one |

## The three accepted downsides — and where each became a workstream

klein was chosen knowing what it is bad at. Each downside was routed to its own
workstream rather than waved off, which is the structure the rest of V2 runs on:

| Downside | Evidence at the time | Workstream |
|---|---|---|
| Occasional AI artifacts | Distilled-model texture artifacts; realism 4.03 — good, not perfect | [v2.1](../v2.1/) realism, then [v2.3](../v2.3/) for logical artifacts once v2.1 proved a global pass cannot repair them |
| Occasional generation failure | One solid-black frame in 16 triage runs (~6%) | [v2.2.3](../v2.2/) — deterministic failure gate with reseed |
| Weak attention with multiple identities | Weakest on `duo_swap` (3.89 vs FASHN's 4.22) | [v2.2.1](../v2.2/) — cropping the garment reference |

## What v2.0 got wrong

Recorded first-class, because it is the most useful output of this workstream.

**`wrong_person` = 0.00 across all 38 outputs was read as "the model2model
collapse did not happen."** It was the wrong reading. The metric was not
measuring what it appeared to: human review on the same class of outputs later
found attention and identity failures on **4 of 7 duo pairs**, three of which
were missed by the deterministic metrics *and* the VLM judge — one scoring above
the run mean. See [../v2.2/EXPERIMENT.md §2b](../v2.2/EXPERIMENT.md) for the
traceability record, and [../results_summary/V2.2_RESULTS.md](../results_summary/V2.2_RESULTS.md)
for the scale of it: the uncropped baseline failed **20 of 33 reviewed sets**.

Two specific instrument failures behind it:

1. **`garment_sim` rewards a plausible garment, not the reference garment.** It
   is an embedding cosine, so an output that transferred nothing still scores
   0.78 and the VLM scores it 4/5.
2. **A no-op scores perfectly on identity preservation.** An output identical to
   its input is maximally faithful to the person — and has not performed the
   task. Any identity number read without a no-op filter says the opposite of the
   truth.

The consequence for the program: **human review is the primary judge from v2.2
onward**, with deterministic metrics and the VLM rubric as supporting evidence.
The attention weakness was present in v2.0's data and invisible to v2.0's
instruments — the failure was in the measurement, not in the sample.

## Open, carried forward

1. **Parity** — every number is a fal number; nothing reproduced on downloaded
   weights ([../results_summary/V2.1.1_RESULTS.md](../results_summary/V2.1.1_RESULTS.md)).
2. **Sample size** — 4 / 4 / 13. Directional.
3. **The distilled-vs-base tie is confounded** by a negative prompt only the base
   can accept; the isolation run is still owed. Relevant again if LoRA
   fine-tuning is ever taken up, since base is the checkpoint BFL recommends for
   it ([../V2.x_DIRECTIONS.md](../V2.x_DIRECTIONS.md) direction 9).
4. **Cross-kind comparison invalid** — duo garment scores are inflated relative
   to product.
