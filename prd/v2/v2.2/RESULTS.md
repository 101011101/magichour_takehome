# v2.2 Results

## v2.2.1 — garment reference cropping

**Status: cropper built and validated. Klein trials not yet run.**
Interactive screen: [`v2/artifacts/crop_screen.html`](../../../v2/artifacts/crop_screen.html)
(13 references, 117 images). Tool: `v2/build/garment_crop.py`. All work local, CPU,
zero spend.

### Crop variants (naming: C for crop)

| | Variant | What it contains |
|---|---|---|
| **C1** | `bbox` | Whole-subject crop, background untouched |
| **C2** | `bbox_nobg` | Same crop, background white, the wearer kept |
| **C3** | `no_face` | Background white **and head removed** (hair + face skin), body skin kept |
| **C4** | `clothes_only` | Every clothing class (coat, trousers, shoes, accessories); skin and face removed |

C3 and C4 also carry an RGBA PNG with true alpha and an SVG mask contour as
inspection artifacts. Model-facing images are explicitly white-flattened RGB —
never rely on an endpoint to flatten alpha, since a default black flatten would
be far worse than white.

### The original cropping solution, and why it was replaced

The first implementation used **MediaPipe Selfie Multiclass (256×256)** as the sole
segmenter: threshold its probability map to a binary mask, upsample ~6× to the
reference resolution, refine with a guided filter, and cut. It worked
semantically — all 13 references produced usable crops, clothes-class confidence
0.82–0.90 — but every boundary was a visible staircase.

The cause was structural, not a tuning problem: **a binary label upsampled 6×
cannot produce a smooth edge.** Measured across all 13 references, the fraction of
pixels with genuinely fractional alpha was **exactly 0.00%** — the old boundary
was a hard label by construction.

One earlier approach was tried and discarded before that: a **YCrCb/HSV
skin-colour heuristic** to separate clothes from skin. It failed exactly where
predicted — a wedge was torn out of the beige coat on the dark-skinned model, and
the brown plaid overcoat was read as skin and destroyed. That is a bias failure,
not a threshold failure; no parameter value fixes it. It survives only as a
fallback route.

### The new solution

Three changes, the middle one load-bearing:

1. **BiRefNet_lite (224MB ONNX, MIT) supplies the subject alpha at 1024×1024.**
   MediaPipe multiclass is demoted to *semantic labels only*. BiRefNet decides
   what the subject is; multiclass decides which part is which.
2. **Composition is subtractive, not intersective.** `subject × clothes_class`
   notched 6px blocks out of the peacoat outline, because at the silhouette the
   clothes class is exactly as coarse as the 256×256 map it came from. Now
   **C3 = matte − head** and **C4 = C3 − body skin**: head and skin are interior
   and localised, so the high-resolution matte always owns the outline.
3. **Whole-body crop replaces the category band.** The shoulders-to-hips /
   hips-down prior is deleted. This dissolves the hem bug by construction — the
   navy peacoat previously dragged the jeans in as a band artifact; coat, jeans
   and boots now come through whole. Target-garment selection is the prompt's
   job, not the cropper's. A `select_region` knob is stubbed and defaulted off.

**A prescribed step was tested and dropped.** Trimap + guided-filter matting over
the BiRefNet output made results *worse* — white speckles punched ~15px into the
peacoat sleeve, because guided filtering transfers image structure into alpha and
dark fabric on a white ground is the worst case. The raw matte is already clean
soft alpha and is used as-is. Trimap refinement is confined to the internal
clothes-vs-skin boundary, which genuinely is a coarse label.

### Improvement

Metric: `jag` = mean |second difference| of the sub-pixel boundary column, plus
the fraction of genuinely fractional alpha. Same boundary, same source
coordinates, old pipeline vs new.

| Reference | jag old → new | soft alpha old → new |
|---|---|---|
| lp_beige_long_coat | 0.427 → **0.048** | 0% → 0.8% |
| hugh_jackman_grey_suit | 0.180 → **0.019** | 0% → 1.1% |
| gal_gadot_blue_dress | 0.219 → **0.025** | 0% → 1.1% |
| navy_peacoat | 0.157 → **0.025** | 0% → 0.8% |
| lp_plaid_overcoat | 0.247 → **0.031** | 0% → 0.7% |
| lp_floral_kimono | 0.253 → 0.255 | 0% → 0.9% |
| man_black_suit | 0.309 → 0.381 | 0% → 0.6% |
| 6 product references | all improved (e.g. 0.590 → 0.212) | 0% → 0.3–1.2% |

![Edge quality, old vs new](images/v221_edge_before_after_beige_coat.png)

*Beige coat boundary at 4× zoom. Left: 256×256 map thresholded and upsampled —
jag 0.43, zero soft-alpha pixels. Right: BiRefNet 1024 matte used as-is —
jag 0.05, 0.82% soft alpha. Per-reference versions of this comparison are the
last item in each set on the screen page.*

**The two rising numbers are not regressions.** On the black suit and the kimono
the new boundary follows real geometry — a lapel fold, a hanging fabric tie —
that the old pipeline's 9–15px morphological smoothing rounded away. The metric
penalises true structure. Visual review confirms both are better: the old black
suit had a light halo and 6px steps along the lapel; the new one cuts tight. No
reference is worse than the old pipeline.

Residual defects, all unchanged or improved versus old: the body-skin class at
256×256 still leaves a sliver of neck and part of one hand on the Jackman
reference, and cuff slivers at the peacoat wrists.

| C3 `no_face` | C4 `clothes_only` |
|---|---|
| ![C3](images/v221_c3_no_face_example.jpg) | ![C4](images/v221_c4_clothes_only_example.jpg) |

### Runtime

| Stage | Cost |
|---|---|
| BiRefNet matte, first pass | 104–320 s per duo reference on CPU (4 cores, contended) — **cached** to `v2/runs/.cache/matte/` |
| Everything downstream, matte cached | 0.5–2.0 s per duo reference, 0.1–0.3 s per product reference |
| Full 13-reference re-run | ~8 s |

Parallelism was tested and **made it slower**: 3 worker processes drove free RAM
to ~16MB, onnxruntime's mmap began paging, and total CPU fell to ~35%. Default is
1 worker. Not a production concern — on GPU BiRefNet runs ~17 FPS at 1024², and
garment crops are cacheable per catalog image rather than recomputed per request.

### Decisions out of v2.2.1

- **C3 and C4 advance to the klein trials** — the next phase of v2.2.1. They test
  the ladder directly: is removing the head enough, or is stripping all skin
  better? Cost is ~$0.40 for 13 pairs each; `base` outputs already exist.
- **C2 carries forward into v2.2.2** — background removed with the wearer kept
  whole is the variant the person-crop-and-composite work needs.
- C1 remains a control.

## v2.2.2 — person crop and composite

Not started. Proceeds after the v2.2.1 klein trials.

## v2.2.3 — failure gate

Not started. Built but not called during the v2.2.1/v2.2.2 runs, so failure rates
stay measurable rather than being silently replaced by retries.
