# V2 Potential Feature List

Candidate features not yet committed to the V2 pipeline. Each entry records what the
feature is, where it lives (production path vs eval-only), and what "working" means.
Features graduate out of this list into their own PRD when picked up.

## 1. Garment image cropper (production path — must be guaranteed to work)

Deterministic pre-processing of the garment reference before it reaches the try-on
model: segment the garment, fill the background white, and crop tightly to the
garment bounding box with a small safety margin.

**Why:** multi-image editors spread attention roughly uniformly across reference
tokens, so background and catalog-pose content in the garment photo leaks into the
output. A white background encodes to near-constant, low-information latents; a tight
crop reduces reference token count and raises the effective resolution of exactly the
high-frequency garment detail (logos, patterns, text) that is lost first. It also
moves the input toward the in-shop distribution the models were trained on.

**Guarantee requirement.** This stage is in the production path and must never
produce a broken input. Fallback chain, in order:

1. Full segmentation + white fill + margin crop, only when segmentation confidence
   passes a threshold and the mask is a single dominant component.
2. Bounding-box-only crop (no background fill) when segmentation is low-confidence.
3. Pass through the original garment image untouched when detection fails entirely.

Constraints: white fill, never alpha (model VAEs are 3-channel); keep a margin so
sleeve/hem edges are never clipped; deterministic output for identical input; log
which fallback tier was used per run.

**Done when:** zero garment truncations on the test set under manual review, valid
image output for 100% of inputs, and an ablation showing garment-fidelity and
pose-leakage improvement (or at minimum no regression) versus uncropped references.

## 2. Quick VLM check (evals only)

A lightweight VLM pass over candidate outputs inside the eval harness. Coarse
pass/fail questions only: is the requested garment present, is the person intact, is
there a gross artifact (missing limb, duplicated garment, garbage region).

**Scope guard:** evals only, never the production path, and never the fidelity
judge. VLM judges are demonstrably insensitive to localized damage (subtle face
drift, small texture loss) — the exact failure modes V2 targets — so this check
filters gross failures cheaply while the deterministic metrics (identity embedding,
masked-region diff, predicted warp below) carry the fidelity verdict.

**Done when:** the check runs per-candidate at negligible cost, catches the obvious
failure class, and its pass/fail agreement is spot-checked against human review on a
small sample.

## 3. Predicted-warp garment fidelity metric (evals only)

Estimate how the garment reference *should* map onto the output and score how well it
actually did — distinguishing a transferred garment from a hallucinated lookalike.

Pipeline: segment the garment region in the output; match features between the
reference garment and that region (DINOv2 patch features or LoFTR; SIFT for strongly
textured garments); fit a thin-plate-spline transform to the correspondences (a
single affine/homography matrix is too rigid for cloth drape); warp the reference and
compare the overlay against the output garment region with SSIM/LPIPS plus a color
histogram distance. Persist a checkerboard overlay or difference heatmap per run for
visual review.

**Interpretation:** high correspondence-match rate + low post-warp distance means the
model transferred the actual garment; low match rate or high distance means it
synthesized a similar-looking substitute.

**Caveats:** mask occluded areas (arms crossing the torso) out of the score; the
metric is weakest on solid-color garments (few features to match), so always report
the match rate alongside the score as a reliability signal.

**Relation to other work:** completes a deterministic eval triad — identity embedding
for the face, predicted warp for the garment, and the change-map gating in
`INTENTION_AWARE_FIDELITY.md` for everything else — with no VLM in the scoring loop.
