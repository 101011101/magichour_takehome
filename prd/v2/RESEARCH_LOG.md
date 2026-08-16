# V2 research log

A dated record of what was done, what was decided, and what was believed at the
time. **Append only** — entries are not edited once written; if a belief turns
out to be wrong, that is recorded in a later entry rather than corrected in
place. This is the document that makes the reasoning behind the PRD reviewable
after the fact, and it is the source the daily work descriptions are written
from.

**Owner:** Ray. **Program:** virtual try-on on open weights, for deployment.

## How to write an entry

One heading per working day. Four fields, in this order — the separation between
the third and fourth is the point of the format:

| Field | What goes in it |
|---|---|
| **Done** | What was built or run. Files, commands, costs |
| **Observed** | What was seen, stated without interpretation. Name the artifact, the pair IDs, who looked, and when |
| **Concluded** | What is inferred from the observation, marked as inference. May be wrong |
| **Next** | The decision the next session opens with, and the condition that would change it |

Rules that keep this useful: record negative and inconvenient results **first**,
never delete a superseded conclusion, and always name the file a claim came
from so a reader can go check it.

---

## 2026-08-13 — migration to open weights (6 h)

**Done.** Moved the V1 takehome onto a deployable open-weights footing. Surveyed
open-weights editors adjacent to the V1 model choices; designed the harness
around their known weaknesses; planned and generated the test set; drafted the V2
harness schemas, including the intention-cropping mask (a deterministic way to
accept or deny a change) and the candidate feature list — cropping methods, text
pipeline, enhancement models. Built and ran the simplest version of v2.0.

**Observed.** —

**Concluded.** The V1 cascade does not survive the open-weights constraint
intact; the harness has to compensate for weaknesses the hosted models did not
have.

**Next.** Run the v2.0 arm comparison.

## 2026-08-14 — v2.0 arm selection and v2.1 (11 h)

**Done.**

- Completed the open-weights MVP for garment editing: v2.0 run against the major
  open-weights editors. → `v2/artifacts/v20_arms_ts2.html`
- Re-tested klein 4B in both variants, distilled and base, after finding that
  base checkpoints sometimes outperform their distilled versions.
  → `v2/artifacts/v20_klein_variant.html`
- Executed v2.1 for image quality: surveyed open weights that preserve fidelity,
  planned the test set, eval methodology and harness, and ran it.
  → `v2/artifacts/v21_aux_screen.html`, `v2/artifacts/v21_aux_batches.html`
- Planned v2.1–v2.4 against klein's three accepted downsides.
- Designed v2.2 and its three sub-workstreams.

**Observed.** FASHN and klein were the top two arms. klein 4B carried three
distinct problems: a high failure rate, AI artifacts, and image-quality loss. In
the v2.1 screen, SeedVR2 led on noise reduction while preserving fidelity —
many candidate models altered the original image even when instructed not to.

**Concluded.** klein 4B is the editing base. Its three downsides are separable
and each gets its own workstream: attention and failure (v2.2), artifacts (v2.3),
auxiliary quality pass (v2.4), with image quality already answered by v2.1.
*Inference, from earlier trials:* garments photographed **on people** drain
klein's attention, producing an incorrect garment edit, the wrong person, or no
result at all — which is what v2.2.1's cropping is meant to test.

**Next.** v2.2.1 cropping system, test and eval. v2.2.2 person-crop plus a
re-stitch that predicts AI intentionality, with a harness measuring re-stitch
accuracy. v2.2.3 deterministic failure gate with reseed, evaluated on recall
accuracy so reseeds only fire when necessary. v2.3 architecture to be designed.
v2.4 auxiliary composite — early trials promising.

## 2026-08-15 — cropper, baseline failure record, scope cut

**Done.** Built and swept the cropper over 48 references, variants C1–C4
(`v2/artifacts/v221_crop_screen.html`); selected **BiRefNet** as the matting
model and moved the pre-pass to PyTorch BiRefNet on GPU (commits `56c780e`,
`0d8cd94`). Ran the klein trials on cropped references
(`v2/artifacts/v221_klein_trial.html`, `v2/artifacts/v221_duo_transfer.html`) and
built the annotated review page (`v2/artifacts/v221_review.html`, 33 sets,
exports CSV).

**Observed.** Human review by eye of the **uncropped klein baseline** on
Testset2, observer Ray, method visual inspection of the 13 base outputs with no
metric consulted. Four failures: ts2_09 and ts2_10 AI artefacts, ts2_11 failed to
transfer the clothes, ts2_12 wrong individual with two people overlaid and the
wrong background. All four are duo pairs — **4 of 7 duo pairs failed; 0 of 6
product pairs failed**.

**Three of the four were missed by the automated judges.** ts2_09 scored 0.865,
*above* the 9-pair mean of 0.824. ts2_11 was scored 4/5 on garment by the VLM on
an output that transferred no garment. Only ts2_12 was caught, by a collapsed
`bg_psnr` of 6.7 dB and a VLM scene score of 1. Full table in
[v2.2/EXPERIMENT.md §2b](v2.2/EXPERIMENT.md).

The cropper over-cuts: head removal takes the collar on several worn references
(p004, p022 clearest), and small-subject frames lose garment area (p016, mask
1.4%). C4 punches holes where hands cross the garment.

**Concluded.** *Inference.* The duo/product split supports the attention premise:
a garment reference containing a person causes an attention deficit, and the
three symptoms map onto F1/F2/F3. Separately — and this is the more uncomfortable
finding — `garment_sim` is an embedding cosine that rewards a *plausible*
garment, so a non-transfer scores 0.78 and the VLM rewards it. Neither instrument
answers "is this the reference garment". **Human review is therefore the primary
judge for v2.2**, with the deterministic metrics and VLM rubric as supporting
evidence only.

**Scope cut.** Region restore and the predicted-warp metric removed from v2.2 and
parked in [V2.x_DIRECTIONS.md](V2.x_DIRECTIONS.md) directions 1 and 2, each with
its trigger condition. v2.2 is attention and failure only. Rationale: v2.2.2
prevents background damage structurally, which may make region restore
unnecessary — measure before building.

**Also.** Renamed the artifact pages to `<workstream>_<subject>.html` so each
page names the `prd/v2/` folder that owns it; `v2/artifacts/index.html` now
carries the convention and groups the pages by workstream.

**Documentation debt closed.** v2.0 — the arm screen that chose klein — had no
workstream folder, only a scoreboard, so the most consequential experiment in the
program was the one with no `EXPERIMENT.md` or `TEST.md`. Written up as
[v2.0/](v2.0/) and **labelled as reconstructed after the runs**, not as
pre-registration. Its `EXPERIMENT.md §4` and `RESULTS.md` record the thing v2.0
got wrong — reading `wrong_person` = 0.00 as evidence that model2model collapse
did not happen, when the metric could not see it.

Related: `V2.1_RESULTS.md`'s headline decision is v2.0's result, not v2.1's — it
carries that number because that is when it was written down. Noted in the file
itself and in the new `results_summary/README.md`, which states how the
program-level and workstream-level numbering relate.

**Next.** The v2.2.1 review pass over the 33 annotated sets, which decides
whether C3.2 or C4 ships and whether directions 11 (garment regeneration) and 12
(grey mannequin) trigger. Open design decision still unsettled: silhouette versus
box paste-back for v2.2.2 — see [v2.2/PLAN.md](v2.2/PLAN.md).

**Methodology debt, recorded so it is not forgotten.** Three known weaknesses in
how v2.2.1 is being judged:

1. Variant selection and reporting use the same 13 pairs, so the ladder is being
   fit to the set it will be scored on. A held-out split has not been reserved.
2. Review is unblinded and single-rater — the observer knows which arm produced
   which image while judging it.
3. Every claim so far is about klein specifically; nothing has been tested on a
   second editor, so it is not known whether the attention effect is a property
   of klein or of conditioning-image editors generally.

None of these invalidate a shipping decision. All three limit what can be
claimed, and (1) and (2) get cheaper to fix the earlier they are fixed.
