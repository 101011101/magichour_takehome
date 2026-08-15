# V2 Proposal — Intention-Aware Fidelity Guardrail

## Executive summary

- **Problem:** try-on models regenerate more than the garment — faces, hands, and
  backgrounds drift even on successful outputs. Restoring everything kills the edit;
  accepting everything kills fidelity.
- **Idea:** a deterministic post-generation stage that decides, per changed region,
  whether the change was intentional (`accept`), accidental (`restore`), or
  uncertain (`repair`), and composites accordingly.
- **Output is a gradient acceptance map**, not a binary crop mask: soft blend of
  candidate and original, Gaussian-feathered only at seams.
- **Pipeline:** register + color-normalize candidate → decompose scene into semantic
  groups (person parts / garment zone / background) → detect changed regions →
  score intent per region with an explicit, inspectable function → composite →
  seam-only low-strength repair.
- **Reason about objects, not pixels:** regions are semantically pure by
  construction (split at group boundaries), so a whole new jacket is one `accept`
  decision and a face tweak is one `restore` decision.
- **No new trained models:** OpenCV base plus off-the-shelf open-weight
  segmentation (person matte, human parsing, garment seg). Weights and thresholds
  are frozen config in the V2 Key.
- **Position:** after candidate generation, before final validation. Any
  low-confidence step falls back to the raw candidate.
- **Success bar:** ablation vs the same raw candidates — identity and background
  preservation improve, garment fidelity and pose do not regress.

### Proposed flow

```text
person + garment
       │
       ▼
open-weight try-on model ──► candidate image
                                  │
original person ──────────────────┤
garment reference ────────────────┤
                                  ▼
                    intention-aware fidelity guardrail
                    1. register + normalize candidate
                    2. decompose scene into semantic groups
                    3. locate and group changes
                    4. score each changed region
                    5. build gradient acceptance map
                    6. composite, then repair uncertain seams
                                  │
                                  ▼
                     final deterministic + VLM checks
                                  │
                                  ▼
                            final try-on image
```

The key judgment call the stage makes: a new jacket may differ greatly from the
original shirt but is still likely intentional — it occupies the torso, overlaps the
expected edit area, resembles clothing, and matches the garment reference. A small
change to the face or a background patch is likely accidental even if visually
plausible. Change magnitude is evidence, never intent by itself.

## System structure

### 1. Alignment and normalization

Register the candidate to the original (ECC or feature-based homography) to absorb
the crop, scale, and aspect drift editing models introduce, and normalize global
color and exposure (channel mean/std or histogram matching) so whole-image tint
shifts do not register as content changes. Without this step the difference map
saturates and every region appears edited. Record registration confidence; when low,
skip the guardrail and return the raw candidate.

### 2. Semantic scene decomposition

Segment the original into a small fixed set of semantic groups before any diffing:

- **person matte** (BiRefNet / RMBG-2.0, or SAM 2 with a person prompt) — the most
  reliable link in the chain;
- **person parts** — face, hair, hands, skin, torso via human parsing
  (Sapiens or SCHP);
- **garment zone** — garment segmentation plus dilation; this is the expected-edit
  prior;
- **background** — everything outside the person matte.

Face, hair, hands, skin, and background form the **protected-content prior**:
changes there need strong evidence to survive. Priors are soft (distance transform +
feathering) and guide classification without dictating it — a new garment may extend
past the original garment boundary when the evidence supports it.

### 3. Change detection and region formation

Diff the aligned, normalized pair with perceptual color (Lab), edge, and
feature-space differences. Threshold, denoise with morphology, and group changed
pixels into connected components or superpixels. **Split any component that crosses
a semantic group boundary** so every region belongs to exactly one group and one
decision. Each region gets a stable ID for the run.

### 4. Intention scoring

Describe each region by geometry, semantic group, overlap with the priors,
appearance (change magnitude, texture, color), similarity to the garment reference
vs the original background, and — when best-of-N is enabled — stability across
candidates. Neighboring regions form a lightweight graph so context counts: a
garment-shaped region attached to the torso is not scored like a lookalike region
attached to the background.

Score with an explicit function, not a trained classifier:

```text
intent(region) =
    + expected_edit_overlap
    + garment_reference_similarity
    + clothing_semantic_similarity
    + spatial_coherence
    + body_attachment_consistency
    + candidate_stability
    - protected_content_overlap
    - background_similarity
    - isolated_or_fragmented_change
```

| Decision | Meaning | Action |
|---|---|---|
| `accept` | High-confidence intended edit | Keep candidate region |
| `repair` | Plausible edit, uncertain boundary | Blend, then seam-only repair |
| `restore` | High-confidence accidental regeneration | Copy original region back |

Decisions are made per region, then feathered at boundaries — never per pixel, which
would shred garment interiors into broken seams.

### 5. Gradient acceptance and composition

Rasterize decisions into an acceptance map `A(x, y)` in `[0, 1]`; smooth only the
transition band. Feathering controls seams — it is not the intention classifier.

```text
composite(x, y) = A(x, y) * candidate(x, y)
                + (1 - A(x, y)) * original(x, y)
```

Composite with the registered, normalized candidate so accepted regions match
restored pixels in geometry and tone. `repair` regions produce a narrow uncertainty
band that a low-denoise, crop-native inpainting pass may harmonize; protected areas
are restored once more afterward as a final invariant.

### 6. Validation and fallback

Score raw candidate and guarded composite on the same V2 axes (garment fidelity,
identity, pose, background, artifacts). Reject the guarded version if it "improves"
preservation by erasing the requested outfit.

Fallbacks:

- Low registration confidence → return raw candidate.
- Low segmentation/matching confidence → return raw candidate.
- Garment fidelity drops past tolerance → return raw candidate.
- Only the seam is uncertain → keep composite, skip generative repair.
- Persist all intermediate masks, scores, and reason codes for debugging.

## Data schema

One JSON analysis package per candidate; masks and maps stored as image/NumPy
artifacts referenced by path.

```json
{
  "schema_version": "v2.intent-map.2",
  "run_id": "pair_model_seed",
  "inputs": { "person_image": "...", "garment_image": "...",
              "candidate_image": "...", "model_id": "...", "seed": 1234 },
  "maps": { "semantic_groups": "...", "edit_prior": "...",
            "protected_prior": "...", "difference": "...",
            "acceptance": "...", "repair_band": "..." },
  "regions": [
    {
      "region_id": 1,
      "semantic_group": "garment_zone",
      "mask_path": "regions/1.png",
      "features": { "change_magnitude": 0.81, "expected_edit_overlap": 0.94,
                    "garment_reference_similarity": 0.86,
                    "protected_content_overlap": 0.03 },
      "intent_score": 0.89,
      "decision": "accept",
      "reason_codes": ["GARMENT_MATCH", "EXPECTED_LOCATION", "COHERENT_REGION"]
    }
  ],
  "output": { "composite_image": "result.png", "fallback_used": false },
  "metrics": { "raw": {}, "guarded": {}, "delta": {} }
}
```

## Component interfaces

```python
align_candidate(original_image, candidate_image, config) -> AlignedCandidate
decompose_scene(person_image, config) -> SemanticGroups, SpatialPriors
detect_change_regions(original, aligned_candidate, groups, config) -> list[Region]
score_intention(regions, region_graph, config) -> list[RegionDecision]
build_acceptance_map(decisions, image_shape, config) -> AcceptanceMap, RepairMask
compose_and_repair(original, aligned_candidate, acceptance_map,
                   repair_mask, config) -> GuardrailResult
```

The public pipeline stays model-agnostic:

```python
candidate = try_on(person_img, garment_img, model_cfg)
guarded = preserve_intent(person_img, garment_img, candidate, guardrail_cfg)
result = validate_and_select(candidate, guarded, eval_cfg)
```

## Build sequence

1. **Baseline:** alignment, scene decomposition, difference map, region scoring,
   soft compositing; no repair model.
2. **Semantic matching:** garment/background embeddings and region-graph context.
3. **Boundary repair:** seam-only low-denoise pass behind an ablation flag.
4. **Stability evidence:** reuse best-of-N candidates as cross-seed agreement.
5. **Calibration:** tune on dev split only, freeze thresholds in the Key, report
   held-out raw-vs-guarded results.

## Non-goals and risks

- Does not replace the try-on generator or the evaluation harness, and does not
  guarantee semantic correctness — low-confidence cases must fall back.
- Pixel-perfect paste-back can inflate preservation metrics while damaging realism
  or garment fidelity; every claim requires raw-vs-guarded ablations and visual
  review.
- Region-level mistakes can erase legitimate accessories or retain garment
  remnants; intermediate artifacts and reason codes are required for diagnosis.
- Global color normalization pulls the candidate toward the original's tone, which
  is correct for background and skin but can nudge the new garment away from the
  reference color; if ablations show this, exclude high-acceptance regions from the
  color-matching estimate.
