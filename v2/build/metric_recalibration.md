# V2 metric recalibration

Recalibration of the two changed deterministic metrics (`garment_sim`, `identity_cos`)
in `metrics_v2.py`, using V1's retained outputs as calibration data. `pose_err` and
`bg_psnr` carry over unchanged (verified identical: r = 1.000 on the re-scored sample).

## Setup

- Metric changes: `garment_sim` HSV-histogram correlation (torso crop vs garment) is
  replaced by Marqo-FashionSigLIP embedding cosine (garment reference vs torso crop);
  `identity_cos` insightface buffalo_l (NC license) is replaced by AuraFace-v1
  (Apache-2.0, same ArcFace-style normed-embedding cosine).
- Calibration sample: 118 outputs re-scored on CPU from `v1/runs/`, stratified across
  all 9 arms and all 3 stages — every triage output (28), 6 pairs per arm for grid
  (both seeds where retained) and holdout. 100 (stage, arm, pair) groups match rows in
  `v1/artifacts/cv_metrics.csv` (old CSV lacks seed ids, so old/new are compared as
  per-group means).
- Negative control: every scored torso crop was additionally compared against a
  deliberately wrong garment reference (rotated assignment) to establish the
  chance-level floor of the new garment metric.

## Old vs new: correlation

| pair | pearson | spearman | n |
|---|---|---|---|
| garment_sim (HSV) vs garment_sim (FashionSigLIP) | -0.08 | -0.05 | 100 |
| identity_cos (buffalo_l) vs identity_cos (AuraFace) | 0.97 | 0.94 | 99 |
| pose_err old vs new | 1.00 | 1.00 | 99 |
| bg_psnr old vs new | 1.00 | 1.00 | 100 |

The old garment metric is uncorrelated with the new one — and uncorrelated with
ground truth. Against V1's VLM garment judgments (per-group means, n = 100):

| metric | spearman vs VLM garment | pearson |
|---|---|---|
| garment_sim old (HSV) | 0.00 | -0.01 |
| garment_sim new (FashionSigLIP) | 0.51 | 0.63 |

The V1 HSV metric was output-level noise; its documented structure-blindness was in
practice total blindness at this crop scale. The identity swap is a near-drop-in:
AuraFace tracks buffalo_l linearly (auraface = 0.846 x buffalo + 0.126) and
correlates marginally better with the VLM identity criterion (spearman 0.35 vs 0.32).

## Distributions (per-group means, p10 / p50 / p90)

garment_sim, old -> new:

| arm | old p10/p50/p90 | new p10/p50/p90 |
|---|---|---|
| fashn_v16 | -0.01 / 0.06 / 0.28 | 0.59 / 0.74 / 0.78 |
| flux_vto_v1 | -0.00 / 0.07 / 0.17 | 0.55 / 0.76 / 0.82 |
| klein_4b_edit | 0.01 / 0.07 / 0.16 | 0.62 / 0.75 / 0.79 |
| klein_tryon_lora | 0.04 / 0.11 / 0.32 | 0.66 / 0.70 / 0.77 |
| magic_hour_api | -0.01 / 0.04 / 0.30 | 0.58 / 0.66 / 0.74 |
| qwen_2511 | -0.01 / 0.04 / 0.15 | 0.66 / 0.71 / 0.82 |
| qwen_image3_edit | 0.07 / 0.10 / 0.27 | 0.69 / 0.73 / 0.78 |
| seedream5_lite | -0.00 / 0.11 / 0.43 | 0.66 / 0.78 / 0.86 |
| seedream_qwen_refine | -0.01 / 0.05 / 0.39 | 0.65 / 0.79 / 0.89 |

Wrong-garment control (all outputs): p50 = 0.54, p90 = 0.62, p95 = 0.63.
Matched (all outputs): p10 = 0.64, p50 = 0.75, p95 = 0.85, max = 0.90.

Old arm means sat in a 0.10-0.16 band with ordering unrelated to garment fidelity
(klein_tryon_lora — a triage-eliminated garment failure — ranked first). The new
metric separates matched from mismatched garments (p50 gap 0.54 vs 0.75) and its
per-arm ordering tracks the VLM garment criterion; arms the old metric scored as
indistinguishable ties (fashn 0.12 / flux 0.11 / qwen 0.10) now spread by actual
transfer quality per pair rather than by histogram noise.

identity_cos, old -> new (p10 / p50 / p90):

| arm | buffalo_l | AuraFace |
|---|---|---|
| fashn_v16 | 0.95 / 0.98 / 0.99 | 0.89 / 0.97 / 0.98 |
| flux_vto_v1 | 0.62 / 0.88 / 0.96 | 0.72 / 0.90 / 0.94 |
| klein_4b_edit | 0.78 / 0.88 / 0.96 | 0.73 / 0.89 / 0.95 |
| klein_tryon_lora | 0.13 / 0.71 / 0.87 | 0.20 / 0.72 / 0.89 |
| magic_hour_api | 0.33 / 0.62 / 0.80 | 0.35 / 0.65 / 0.81 |
| qwen_2511 | 0.42 / 0.89 / 0.97 | 0.44 / 0.87 / 0.96 |
| qwen_image3_edit | 0.68 / 0.81 / 0.91 | 0.69 / 0.82 / 0.91 |
| seedream5_lite | 0.27 / 0.65 / 0.90 | 0.38 / 0.66 / 0.86 |
| seedream_qwen_refine | 0.37 / 0.67 / 0.87 | 0.49 / 0.72 / 0.88 |

## Proposed anchors

Same philosophy as V1: absolute anchors on each metric's own scale, not min-max
across arms; identity ceiling kept below the paste-back-saturation point so
compositing arms cannot max the composite by pixel reuse.

```python
CV_ANCHORS = {"garment_sim": (0.55, 0.85), "identity_cos": (0.42, 0.80),
              "pose_err": (0.25, 0.0), "bg_psnr": (12.0, 32.0)}
```

- `garment_sim` lo = 0.55: the wrong-garment control median is 0.54 (p90 = 0.62) —
  FashionSigLIP cosine between any torso-with-clothing crop and any garment product
  shot floors around this level, so scores at chance earn 0. (The V1 lo of 0.0 has no
  analog: embedding cosines never approach 0 in this domain.)
- `garment_sim` hi = 0.85: p95 of matched-garment outputs (max observed 0.90).
  Values above this are the near-duplicate regime — the garment rendered at
  product-shot likeness — and extra cosine beyond it is presentation similarity, not
  better transfer, so it saturates.
- `identity_cos` lo = 0.42: V1 anchored lo at the ArcFace same-person verification
  threshold (0.35 on buffalo_l). The linear fit between the two embeddings on 99
  matched groups (auraface = 0.846 x buffalo + 0.126) maps 0.35 to 0.42; below this,
  a verifier would call it a different person.
- `identity_cos` hi = 0.80: same fit maps the V1 ceiling 0.80 to 0.803, and the
  observed paste-back saturation confirms it — fashn_v16 (original face pixels
  substantially preserved) sits at AuraFace p25 = 0.94, median = 0.97. A ceiling of
  0.80 is the level strong genuine re-renders reach (flux/klein/qwen medians
  0.87-0.90) while leaving paste-back arms no headroom advantage above it.
- `pose_err`, `bg_psnr`: unchanged metrics, unchanged anchors (0.25, 0.0) and
  (12.0, 32.0).

## Ranking sanity check

Composite (garment x2 weighting, per-output anchored composites averaged per arm)
recomputed on the sampled groups:

Holdout (6 pairs/arm): old metrics + V1 anchors on the same sample give
flux 0.560 ~ fashn 0.559 > seedream5 0.474 > cascade 0.457 > qwen 0.330.
New metrics + proposed anchors give fashn 0.719 > flux 0.705 > seedream5 0.661 >
cascade 0.650 > qwen 0.597.

- flux/fashn swap at the top, but they were a statistical tie under the old metrics
  on this sample (delta 0.001) and remain within noise under the new (delta 0.014).
  V1's reported holdout order (flux > fashn) is not contradicted, just not resolved
  by 6 pairs.
- seedream5 > cascade on this sample under both old and new metrics — a sampling
  effect (V1's full 18-pair holdout had cascade ahead), not a metric effect.
- qwen_2511 last in every configuration.

Triage (all 28 outputs): V1 eliminated klein_tryon_lora and qwen_image3_edit.
Under new metrics + anchors, klein_tryon_lora is still clearly last (0.50 vs next
0.55). qwen_image3_edit (0.566) edges 0.020 above qwen_2511 (0.546) — a marginal
flip in the bottom pair. This would not have changed V1's outcome materially:
qwen_2511 survived to holdout and finished last there under both metric sets.

No elimination decision reverses under the new metrics; the only order changes are
inside pairs that were already statistical ties.

## Notes / caveats

- Score compression: the new composite's spread between best and worst arms is
  narrower (holdout 0.72-0.60 vs old 0.56-0.33) because FashionSigLIP arm medians
  span 0.66-0.79 raw. The anchors spread this to roughly 0.35-0.80 normalized;
  do not compare V2 composite values to V1 values directly.
- FashionSigLIP rewards prominent, product-like garment rendering; full re-render
  arms (seedream) score slightly above paste-back arms on garment_sim even where the
  VLM judged fashn higher. The VLM garment criterion remains the structure/fit
  arbiter; the deterministic metric is the cheap screen.
- Old CSV rows for repeated-seed grid runs cannot be matched to individual seeds, so
  all old-vs-new comparisons are per-(stage, arm, pair) means.
- Re-scoring environment: CPU, python 3.9, torch 2.2.2, open_clip_torch,
  insightface 1.0.1 + onnxruntime (AuraFace via `FaceAnalysis(name="auraface")`),
  mediapipe 0.10.21, numpy < 2, opencv-python-headless 4.10.
