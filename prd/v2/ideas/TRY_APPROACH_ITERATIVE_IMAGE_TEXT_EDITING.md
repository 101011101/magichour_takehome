# TryApproach: Iterative Image-and-Text Garment Editing

## High-level overview

This approach combines the original person image with a precise text description of
the target garment, then places the image-editing model inside an automated correction
loop.

The central hypothesis is that image-and-text editing models can follow garment
instructions more reliably than a general two-image transfer request. The person
image supplies the identity, pose, composition, lighting, and background that must be
preserved. The garment description focuses the model's instruction attention on a
narrower problem: generating the requested clothing without requiring the model to
interpret a second image containing unrelated visual information.

```text
Original person image
+ structured garment description
              ↓
      image-and-text editor
              ↓
         candidate image
              ↓
 intention-aware fidelity constraint
              ↓
    evaluate and issue correction
              ↓
      repeat until accepted
```

The garment reference image is first converted into a structured description
covering:

- Garment category
- Color and material
- Silhouette and proportions
- Neckline and sleeves
- Closures, pockets, seams, and construction
- Pattern, print, logo, and distinctive details

The editor then receives the original person image and this garment description.
Because it only needs to understand the person from the image, the garment instruction
remains isolated in text and does not compete with the face, background, or pose
contained in a second reference image.

Every generated candidate passes through the
[Intention-Aware Fidelity Guardrail](./INTENTION_AWARE_FIDELITY.md). The guardrail
compares the candidate with the original, groups changes into semantic regions, and
determines whether each change is likely intentional or accidental.

It produces a deterministic gradient acceptance map:

- Intended garment regions remain editable.
- Face, hair, hands, skin, pose, and background regions are restored or protected.
- Uncertain garment boundaries receive a narrow repair mask.
- Subsequent corrections are cropped to the failed region instead of regenerating
  the full image.

The guardrail does not directly control the model's internal attention. Instead, it
deterministically controls the pixels and crop supplied to each correction pass. This
effectively focuses each iteration on the permitted region while preventing unrelated
changes from accumulating.

The loop evaluates garment accuracy, identity, pose, background, and visual quality
after every attempt. When the garment is incorrect, it revises the text instruction
and retries from the original image. When only a local detail is incorrect, it crops
that region, applies the intention-aware constraint, and performs a targeted repair.

The intended result is a controlled optimization loop:

```text
Describe garment
      ↓
Generate candidate
      ↓
Preserve intended changes
      ↓
Restore accidental changes
      ↓
Measure remaining failures
      ↓
Retry only where necessary
```

This is one experimental approach within the larger V2 pipeline. Its purpose is to
test whether strong image-and-text editing, combined with deterministic regional
constraints, can achieve better instruction adherence than direct two-image transfer
while maintaining higher identity and scene fidelity.

## How it works

### 1. Convert the garment image into a structured instruction

A vision-language model analyzes the garment reference once and produces a validated,
model-independent description. Structured fields prevent important details from being
lost inside an unconstrained caption.

```json
{
  "category": "biker jacket",
  "color": ["black"],
  "material": ["leather"],
  "silhouette": "cropped and fitted",
  "neckline": "wide notched lapels",
  "sleeves": "long fitted sleeves",
  "closures": ["asymmetric silver zipper"],
  "construction": ["two diagonal zip pockets"],
  "pattern": "solid",
  "branding": "none visible",
  "distinctive_details": ["waist-length hem", "silver hardware"]
}
```

The schema is rendered into a concise edit instruction. The prompt states both what
must change and what must remain invariant.

```text
Replace only the existing upper-body garment with a cropped, fitted black leather
biker jacket. Preserve the wide notched lapels, asymmetric silver zipper, diagonal
zip pockets, fitted sleeves, waist-length hem, and silver hardware. Preserve the
person's identity, face, hair, hands, pose, body proportions, lighting, framing, and
background.
```

Text is expected to preserve garment semantics and named attributes, not guarantee an
exact reconstruction of every source pixel. Logos, unusual prints, and distinctive
construction details should be flagged as high-risk attributes during evaluation.

### 2. Generate the first candidate

The image-and-text editor receives:

- the original person image;
- the structured garment instruction;
- a fixed model configuration and seed, where supported.

The original image remains the stable source of truth throughout the run. The first
output is only a candidate and is never accepted without preservation and garment
checks.

### 3. Apply the intention-aware fidelity constraint

The candidate is compared with the original image. Changed pixels are grouped into
object-like regions and scored using:

- overlap with the expected garment area;
- semantic similarity to clothing;
- agreement with the garment description;
- spatial coherence and attachment to the body;
- overlap with protected face, hair, hand, skin, and background regions;
- similarity to the original background or protected content.

Each region is classified as:

| Decision | Meaning | Action |
|---|---|---|
| `accept` | Likely intentional garment edit | Keep candidate content |
| `restore` | Likely accidental regeneration | Copy original content back |
| `repair` | Intended edit with uncertain structure or boundary | Create a local repair task |

Region decisions are rasterized into the gradient acceptance map defined in the
[guardrail design](./INTENTION_AWARE_FIDELITY.md). Semantic scoring determines which
content survives; Gaussian feathering only smooths the transition boundary.

### 4. Evaluate the guarded candidate

The guarded candidate is evaluated along independent axes:

```json
{
  "garment": {
    "category": 0.96,
    "color": 0.92,
    "silhouette": 0.78,
    "construction": 0.71,
    "distinctive_details": 0.69
  },
  "preservation": {
    "identity": 0.95,
    "pose": 0.97,
    "background": 0.99,
    "hands": 0.90
  },
  "quality": {
    "seams": 0.81,
    "artifacts": 0.92,
    "realism": 0.89
  }
}
```

Preservation requirements are constraints, not interchangeable weighted scores. A
high-quality garment cannot compensate for a failed identity or changed background.
Likewise, perfect preservation cannot compensate for failing to apply the garment.

### 5. Plan the next correction

The evaluator returns explicit reason codes and selects one of three actions.

#### Accept

Return the guarded candidate when all required thresholds pass.

#### Retry from the original image

Start a new full attempt when:

- the requested garment was ignored;
- the garment category or silhouette is fundamentally wrong;
- pose, composition, or realism failed globally;
- local repair would require changing most of the garment.

The correction controller revises only the failed portions of the instruction and,
where possible, changes the seed. It does not append an unlimited history of prompts.

#### Repair a local crop

Use the guarded candidate when the garment is broadly correct but a localized detail
failed, such as a sleeve, collar, closure, logo, seam, or compositing boundary.

The failed region is expanded by a context margin. The editor receives the crop and a
narrow instruction:

```text
Correct only the jacket's left lapel and zipper. Match the specified black leather,
wide-lapel construction and asymmetric silver zipper. Preserve the face, hair, arm,
hand, background, and remaining jacket exactly.
```

The repaired crop is placed back through the gradient acceptance map, then evaluated
again.

### 6. Prevent cumulative degradation

The system must avoid unrestricted full-image edit chains:

```text
Avoid:
original → edit 1 → edit 2 → edit 3 → edit 4
```

Repeated encoding and regeneration can accumulate identity drift, softness, pose
changes, and background damage. Instead:

- full retries always start from the original person image;
- only narrow repairs use the guarded candidate as their base;
- original protected pixels remain available for restoration after every operation;
- the strongest valid candidate is retained at every iteration.

### 7. Stop and select

The loop stops when:

- all required thresholds pass;
- the iteration budget is exhausted;
- improvement falls below a configured minimum;
- the same failure repeats;
- a correction improves the garment but violates a preservation constraint.

An initial budget should remain small: up to three full attempts and two local
repairs. The selector returns the best candidate that passes all minimum constraints,
not simply the candidate with the highest average score.

## Pipeline interface

```python
def iterative_image_text_try_on(
    person_image,
    garment_description,
    model_config,
    guardrail_config,
    evaluation_config,
    loop_config,
) -> TryApproachResult:
    ...
```

```python
garment_spec = describe_garment(garment_image)

for attempt in range(loop_config.max_full_attempts):
    candidate = edit_from_original(
        person_image,
        garment_spec,
        correction=current_correction,
    )

    guarded = preserve_intended_changes(
        original=person_image,
        candidate=candidate,
        garment_spec=garment_spec,
    )

    evaluation = evaluate_try_on(
        original=person_image,
        garment_spec=garment_spec,
        result=guarded,
    )

    if evaluation.passes:
        return guarded

    current_correction = plan_correction(evaluation)

    if current_correction.is_local:
        guarded = repair_local_crop(guarded, current_correction)

return select_best_valid_candidate()
```

## Initial build sequence

1. Define and validate the garment-description schema.
2. Generate a single image-and-text candidate from the original person image.
3. Connect the existing garment, identity, pose, background, and quality evaluators.
4. Apply the intention-aware gradient acceptance map.
5. Add full retries from the original with targeted prompt revisions.
6. Add constrained crop-and-repair passes.
7. Compare the approach against direct two-image editing on the same dev and held-out
   pairs.

Each step must be tested as an ablation. The approach succeeds only if it improves
garment adherence without trading away identity, pose, or scene fidelity.

## Risks and open questions

- Text may not preserve exact logos, prints, seams, or uncommon garment construction.
- The captioning model may omit or hallucinate garment attributes.
- Image-and-text editing may still regenerate content outside the requested region.
- Incorrect intention scoring may erase valid garment extensions or retain accidental
  changes.
- Crop repairs may produce visible boundaries or inconsistent garment structure.
- Extra attempts increase latency and compute cost.
- Some image editors may respond better to a garment reference image than to even a
  highly detailed description; direct two-image editing remains the control arm.

All iterations must persist the garment schema, prompt, seed, crops, masks, region
decisions, evaluation scores, correction action, and resulting image. This makes the
loop reproducible and its failures diagnosable.
