# v2.0 Experiment — which open-weights editor do we build on

> **Reconstructed 2026-08-15, after the runs.** See [README.md](README.md). The
> question and criteria below were operative during the work — they are visible
> in the harness, the prompt design and the scoring weights — but they were not
> written down before the runs. Read this as a record, not a pre-registration.

## 1. Goal

One question: **which open-weights image editor should the try-on product be
built on?**

The V1 winner (Seedream 5 Lite → Qwen cascade) is closed-weights and therefore
ineligible — the V2 deployed path must be self-hostable open weights
([CONDITIONS.md §1](../results_summary/CONDITIONS.md)). This is a re-selection
from scratch, not a migration.

Two sub-questions came with it, and both were answered in the same runs:

| | Question |
|---|---|
| **A** | Which editing model transfers a garment best while preserving the person and the scene? |
| **B** | Does a **second, single-image stage** meaningfully repair the realism the editing stage loses — and if so, which model? |

B exists because the two are not separable by inspection: an editor that
preserves everything but transfers conservatively might still win once a realism
pass is applied on top, and an editor that transfers well but looks synthetic
might be rescued by one. The base that ships is the base that wins *after* the
second stage, so both had to be screened before either could be decided.

## 2. The hypothesis each candidate represented

Candidates were not a convenience sample. Each was in the pool because it
embodied a specific claim about the V1 regression — **identity degradation** —
and screening them tests those claims, not just the models.

| Model | The claim it represents |
|---|---|
| **FASHN VTON v1.5** | A *dedicated* try-on model, pixel-space with no VAE round-trip, should preserve identity better than a general editor. The only modern Apache-licensed dedicated try-on model with a clean training-data story |
| **FLUX.2 klein 4B** | A strong *general* editor with no weak axis beats a specialist. #1 open model on VTEdit shop→model; ~13GB, sub-second, Apache 2.0 |
| **FireRed-Image-Edit v1.1** | An explicit **identity-consistency loss** in training is the most direct answer to the V1 regression |
| **HiDream-O1-Image** | Pixel-native / no-VAE — the same argument that put FASHN in the pool, applied to a general editor (MIT) |
| **Qwen-Image-Edit-2511** | **The baseline.** The model currently running on the Magic Hour website; everything must beat it |

The 9B klein sibling is non-commercial, so 4B is the only usable size.
JoyAI-Image-Edit-Plus, OOTDiffusion and OrthoTryOn had no hosted endpoint and
were deferred to [EXTENSION_ARMS.md](../EXTENSION_ARMS.md) with promotion
triggers rather than dropped.

## 3. What would count as an answer

The objective is not a single score. Fidelity decomposes, the parts trade against
each other, and the product cares about them unequally:

- **Garment transfer carries ×2 weight.** It is the thing the product does. A
  model that preserves the original photo perfectly by changing very little has
  not performed the task.
- **Identity and background are preservation axes** — necessary, but a model
  cannot win on them alone, by the point above.
- **Realism is a second axis**, separable because a single-image stage can repair
  it after the fact. This is what makes B a real question rather than a tiebreak.

Elimination was to be driven by deterministic metrics; realism by the blind VLM
judge, which is where deterministic metrics are weak; and human review was the
final tiebreaker. Full definitions:
[SCORING_CRITERIA.md](../SCORING_CRITERIA.md), authority table in
[CONDITIONS.md §4](../results_summary/CONDITIONS.md).

## 4. What was expected to happen, and did not

Recorded because the failed prediction is the more useful half.

**Expected: model2model collapse on duo pairs.** The benchmark literature has
every open model failing when the garment reference is *itself a photo of a
person* (VTEdit Model2Model: best 2.06, Qwen 1.17, klein 1.03). Testset2 was
built with `duo_lookbook` and `duo_swap` kinds specifically to catch this, and
`wrong_person` was added as a metric to track it.

**Observed: `wrong_person` = 0.00 across all 38 outputs** for klein, FASHN and
Qwen. No identity substitution on any duo pair. The inference at the time was
that explicit target-garment prompting ("take *the grey suit* worn by the person
in image 2; do not copy their face or background") plus FASHN's
`garment_photo_type="model"` were sufficient.

**That inference was wrong, and was corrected by v2.2.** The metric was not
measuring what it appeared to. Human review of the same class of outputs found
identity and attention failures on 4 of 7 duo pairs that `wrong_person`, the
deterministic composite and the VLM judge all scored as fine — see
[../v2.2/EXPERIMENT.md §2b](../v2.2/EXPERIMENT.md). The attention weakness was
real in v2.0's data and was not visible to v2.0's instruments.

This is the single most important thing v2.0 got wrong, and it is why v2.2 makes
human review the primary judge.

## 5. Open questions this workstream did not answer

Carried forward rather than closed:

1. **Parity.** Every number is a fal number. Nothing has been reproduced on
   downloaded weights — the standing risk is recorded in
   [../results_summary/V2.1.1_RESULTS.md](../results_summary/V2.1.1_RESULTS.md).
2. **Sample size.** 4 pairs (triage), 4 images (aux screen), 13 pairs (Testset2).
   Directional evidence plus product judgement, not a settled result.
3. **Cross-kind comparison is invalid** — duo garment scores are inflated
   relative to product because the reference is domain-matched to the output
   ([CONDITIONS.md §3](../results_summary/CONDITIONS.md)).
4. **The distilled-vs-base tie was left confounded.** The base variant ran with a
   preservation-only negative prompt that the distilled cannot accept; every term
   in it pushes the model to change less, which plausibly produced both the base's
   strong identity/scene and its weak garment. An isolation run is still owed.
