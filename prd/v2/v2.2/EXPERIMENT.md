# v2.2 Experiment — attention and failure

## 1. Goal

One question: **did the model make the correct change?** Not how pretty the
result is, not how realistic — whether the edit that was asked for is the edit
that happened. Three ways it fails, all in scope:

| # | Failure | What it looks like |
|---|---|---|
| **F1** | **Wrong person** | Content from the garment reference leaks in — the reference model's face, body or background appears in the output |
| **F2** | **Wrong clothes** | A plausible garment that is not the reference garment, or the reference garment rendered imprecisely |
| **F3** | **No change, or garbage** | The transformation is simply not made, or the frame is degenerate |

Realism, gloss, seams and artifacts are **not** in scope (v2.1 and v2.3). Region
restore and the predicted-warp metric were removed from this workstream on
2026-08-15 — see [../V2.x_DIRECTIONS.md](../V2.x_DIRECTIONS.md).

## 2. Approach

The premise: klein's attention is diluted across everything in the reference
images. It sees a garment *and* a stranger's face *and* a room, and spreads
attention roughly uniformly across all of it. Remove what is not the subject and
the attention lands where it should.

| | Scope | Mechanism |
|---|---|---|
| **2.2.1** | Crop the **garment** reference | Segment the clothes (and the body carrying them, where visible), place on white, crop tight with a safety margin |
| **2.2.2** | Crop **both** — garment and person | 2.2.1, plus: crop the person out, run the edit on that crop, composite the person back onto the original background |
| **2.2.3** | Failure catch | Deterministic gate that detects a failed generation |

**F1 is expected to be solved structurally by 2.2.1**, not by a detector.
Cropping the reference removes the reference person's head and background, so
there is nothing left to leak. klein already scored `wrong_person` 0.00 on all 13
pairs before any cropping; this should hold, and it is checked by eye rather than
gated.

## 3. What 2.2.3 is

A deterministic, CPU-only gate that decides whether a generated frame is usable.
It produces a verdict and reason codes per output; when enabled, a rejected
output triggers a re-call of the model on a fresh deterministic seed.

F3 has two shapes and each needs its own check:

| Shape | Appearance | Detection |
|---|---|---|
| **Degenerate** | Solid black, constant colour, blur-out — not a photograph at all | Pixel statistics: global standard deviation, Laplacian variance, unique-colour count |
| **No-op** | A perfectly good photograph that is the *input*, unchanged | Compare output against the person input: high SSIM plus near-zero change inside the garment region |

A no-op is invisible to pixel statistics — nothing is wrong with the image, it is
just the wrong image. The two checks are independent and both are required.

## 4. How this is measured

**All v2.2 comparisons are against the v2.2 series itself** — base klein, 2.2.1,
2.2.2. No cross-arm comparison: FASHN, Qwen and HiDream numbers are not re-run
and are not targets here. The question is whether these mitigations improve *our
chosen base*, not whether a different model would have been better; that contest
closed in [V2.1_RESULTS.md](../results_summary/V2.1_RESULTS.md).

Three configurations, identical seeds, one arm (`klein_4b_edit`, distilled):

| config | garment crop | person crop + composite |
|---|---|---|
| `base` | off | off |
| `v221` | on | off |
| `v222` | on | on |

**Human review is the primary judge for now.** Ray reviews outputs side by side;
deterministic metrics and the VLM rubric are supporting evidence, not the
verdict. Numeric thresholds are deliberately not pre-registered — with 13 pairs
and an eye-led verdict, fake precision would be worse than none. Direction of
movement is what matters, and thresholds can be set once the first run shows the
spread.

### On 2.2.2's structural advantage

2.2.2 composites the original background back, so background and identity scores
improve **by construction**. This is a genuine product win, not a measurement
artifact: the paste-back ships with the product. It is also self-correcting — an
inaccurate crop-back shows up as seams, misregistration and a *worse* score, so
the metric penalises exactly the failure mode that matters.

One guard: garment fidelity is reported on its own axis, so a strong background
score can never mask a garment regression inside a weighted composite.

## 5. Open design decision

**Silhouette paste-back or box paste-back** for 2.2.2. Cutting the exact
silhouette clips or halos when the new garment is bulkier than the old one (a
puffer over a tee) and would require background inpainting for the revealed
strip. Cropping a generous box preserves everything outside it by construction
and gives the model room, at the cost of leaving the background *inside* the box
to the model. To be settled before build — see [PLAN.md](PLAN.md).
