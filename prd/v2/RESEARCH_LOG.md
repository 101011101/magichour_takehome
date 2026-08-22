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

## 2026-08-19 — attention modulation test, and the descent hypothesis

**Done.** Ran the Attention Modulation Test: 200 generations, 20 pairs × 10 arms,
klein 4B distilled, seed 46, person image and prompt held fixed so the only variable
is the garment reference. Ten arms across four mechanisms — remove the person
(`control`, `QX_qwen_p1`), remove only the head (`BC_klein`), remove nothing but
destroy identity (blur / twirl / pixelate, on both an original and a balded base),
and remove nothing at all (`BALD_raw`). Built the ranking UI with top-ties and
cut-off bars. Ranked by eye. Cost ≈ $3.1 fal. Artifacts:
`v2/artifacts/v221_attention_mod.html`, `v221_attention_mod_rankings (1).csv`,
write-up in `prd/v2/v2.2/RESULTS.md`.

**Observed.** Mean rank / top-tier / cut, over 20 sets: `control` 2.25 / 75% / 5%;
`BC_klein` 2.45 / 80% / 0%; `QX_qwen_p1` 4.40 / 55% / 15%; the six destruction arms
5.35–6.80; `BALD_raw` 8.70 / 15% / **85%**. `QX_qwen_p1` ranks were
1,1,1,1,1,1,2,2,2,2,2,5,6,6,9,9,9,9,9,10 — stdev 3.56 against `BC_klein`'s 0.76.
`D3B` (pixelate, bald) was cut 0% of the time. In 9 of 20 rows all six destruction
arms landed in the same tier; a row averaged 5.7 of 10 arms in the top tier; the six
arms' mean rank spread within a row was 5.8 of a possible 9. Cut rate /O → /B: blur
30→10%, twirl 40→10%, pixelate 30→0%. Reviewer: Ray, by eye, 2026-08-19.

**Concluded.** *Inference, and the load-bearing one for the program.*

**A descent toward a solution klein can already produce is what the attention deficit
chips away at.** With enough attention available the model converges to essentially
the same result regardless of which arm produced the reference — 9 of 20 rows put all
six destruction arms in one tier. The model is not short of capability; competing
content in the reference is what stops it going all the way. The failure is a deficit,
not an inability.

**The consequence is the important part: if the deficit is what matters, the manner of
removing it is free to vary.** Cropping, balding, blurring and pixelating are
interchangeable to the extent that each removes the same distraction — which is why
they cluster in the same tier. That interchangeability is a **degree of freedom for
cost**, and it is where V3's optimisation work should live: pick the cheapest
mechanism that removes enough attention, rather than the most thorough one.

Supporting, narrower conclusions: **the crop earns its place** (`BALD_raw` cut 85% —
removing the head is not sufficient); **pixelation is the best destruction mechanism**
because it removes attention while preserving context, and its cell size is a
continuous dial rather than a switch; **Qwen extraction is bimodal**, six wins and
five bottom-two placements, so it belongs in the harness as a conditional option, not
a fixed step.

Recorded caveat: convergence holds at **tier** level, not rank level — the six arms
average a 5.8-of-9 rank spread within a row. "Same quality band" is supported;
"identical outputs" is not.

**Next.** Finish the trials and deliver the v2 harness. Then plan v3 around cost
optimisation, using the interchangeability above as the lever. Pixelation modulation
(sweeping cell size as a continuous attention dial) is the first experiment that
would sharpen the descent hypothesis into something tunable. BG and the mannequin
remain paused behind this.

**Status note sent to Runbo, 2026-08-19** — recorded verbatim because it is the
first external statement of the descent hypothesis:

> Quick 5-day update: v2 (open source) has been going well. The initial translation
> met most requirements, and I have been working on a couple of edge cases where it
> occasionally fails. Through experimentation, I've found the likely cause to be
> attention overload. The way attention is given to certain items significantly
> boosts the success rate. I expect to complete these trials and deliver a v2 harness
> in the coming days. At the same time as delivering v2, I will also plan v3, which
> will implement cost optimization leveraging the data from v2. The v2 trials have
> shown that some type of descent is likely occurring toward a perfect solution that
> Klein can output, and the attention deficit chips away at it. Thus, as long as the
> attention deficit is removed, the manner in which it is done can be varied. This
> aspect is also where I anticipate cost-saving measures to be created.
>
> Upon completion of v2 I will draft up a report and would love to set up a call to
> discuss any details. Thank you for this opportunity.
>
> Sincerely, Ray Tan

## 2026-08-19 (later) — v2.2 checkpoint

**Done.** Closed out v2.2.1 with the Attention Modulation Test: 38 sets × 10 arms,
plus a high-damage cohort added after the first test set was found to exclude the
failure mode it was meant to measure, plus PHEAD (a free deterministic arm) and a
routing-signal probe. Built four review pages with drag-ranking and ternary-verdict
UIs. Total fal spend for the phase ≈ $9.

**Observed.** Over 38 sets: BC_klein 74% perfect / 5% fail, PHEAD 63% / 21%,
QX 58% / 8%, control 53% / 34%. Split by condition, `control` goes 75%→28% perfect
and 10%→61% fail between low- and high-damage references; every bald-based arm moves
by 3–4 points. Failure correlation is positive among all subtractive arms (+0.17 to
+0.58) and negative between QX and all of them (−0.07 to −0.21). BC_klein and QX have
five failures between them and no overlap. A router built from torso lean,
non-frontality and garment-share puts 6 of 8 BC_klein-weak garments in the top 8
(36% baseline).

**Concluded.** *Inference.* The attention deficit is addressed, and the mechanism
split is the reason: subtraction and regeneration fail for structurally different
causes, so pairing one of each covers what neither covers alone. **Two statistics
used earlier were withdrawn** — mean rank and win-count both treat a tied-first band
as an ordering. **The retry design in the original v2.2.3 spec is invalid**: failure
is a property of the garment, not the roll, so a gate must escalate mechanism rather
than reseed. v2.2.2 is deferred rather than complete — the arms probably made it
unnecessary, but background was never measured on its own axis and the rankings were
holistic, so the stronger claim is unsupported. BG and the mannequin are dropped;
their trigger conditions were never met.

**Next.** v2.2.3 — the failure gate, with routing as a second half. That closes v2.2.
Then v2.3 (artifacts) and v2.4 (auxiliary cleanup). Routing feeds the V3 cost work
but does not constitute it, and is not yet validated.

---

## 2026-08-21 — the deterministic gate is a coin flip; the harness becomes tiered

**Did.** Fixed AuraFace (HF snapshot layout against insightface's expected
`<root>/models/<name>/` — it had been silently disabled and downloading nothing),
re-graded all 456 AMT outputs with identity live, then built
`v2/artifacts/v223_cheapest_usable.html` and had the three cascade arms judged blind,
usable or not, 114 cells.

**Found.** Identity is a genuinely good check — 100% precision at every threshold
from 0.1 to 0.6, never once flagging a frame the reviewer liked — and it is useless
to us. It fires on `BALD_raw` and the D\*O arms, all of which keep a head in the
garment reference, and on **zero of PHEAD, BC_klein and QX**, reading 1.00 on all
eight PHEAD failures. Those arms remove the reference person, so identity
substitution is the one failure they structurally cannot have.

The blind test settled it: **AUC 0.506** against the reviewer, mean gate score 0.684
on usable cells against 0.674 on unusable, and best-threshold agreement (71.1%)
*below* the accept-everything baseline (71.9%). Every sub-check flat.

**The control is what makes it conclusive.** The same reviewer had labelled the same
outputs months earlier under a different question, and the two passes line up 95% /
44% / 0% across perfect / ok / fail. The target is stable and a semantic label
predicts it almost perfectly. The noise is in the instrument.

**Concluded.** *Inference.* Pixel statistics cannot see semantic failure, and no
amount of calibration changes that — this is not a threshold problem. The binary gate
does not ship; identity stays as a free monitor, never a spend decision. The router
is deferred on a second independent ground: it is only worth building on top of a gate
that can catch its mistakes, and there is none.

**The replacement, as a hypothesis.** A **three-tier** control signal — *perfect*
ships and stops, *ok* or *fail* escalates, and where every arm fails a VLM picks the
least-bad of the three already generated. Three tiers rather than two because *ok* is
where the reviewer's own binary call splits 44/56; it is the only band where the
decision is interesting. The VLM is affordable precisely because it fires on ~5% of
requests, is asked a forced-choice question rather than the absolute "is this good"
it demonstrably fails, and is wrong only on requests that were already failing.
**The whole design rests on a tier judge that does not exist** — the simulation
substitutes a human label. Falsifying test: build it, measure it against the
reviewer's tiers, and if it cannot reproduce them, the harness collapses back to a
flat BC_klein.

**Also corrected.** QX goes second, not third. Of PHEAD's 13 unusable sets QX rescues
11 and BC_klein 6 — both PHEAD and BC_klein subtract and share a failure mode, while
QX regenerates. 1.789 generations per request against 2.053, same coverage. This is
the per-cell confirmation of the 1.421-vs-1.526 result already in the cost analysis,
and it means the stronger arm alone is the weaker second step.

**Next.** Build and validate the tier judge, or accept flat BC_klein and close v2.2.
The self-hosted parity run remains owed regardless.

---

## 2026-08-21b — the absolute re-mark; routing works, the gate does not

**Did.** Rebuilt the pick sheet as an absolute three-tier pass (`v223_perfect_tier.html`)
after Ray objected that usable and perfect are different questions and that the
objective is to maximise perfection. Re-marked all 114 cells. Renamed three harness
pages from `v221_` to `v223_` — they were v2.2.3 work carrying a v2.2.1 prefix — and
fixed two `check_links.py` bugs found in the process (bare backticked filenames always
resolved against the repo root and so always reported broken; `index.html`'s own hrefs
were never scanned at all).

**Found.** QX's tier profile is the finding: **20 perfect / 17 ok / 1 fail**. Lowest
ceiling, by far the lowest floor. The binary sheet had scored it 71% "usable" and
hidden that most of those were merely `ok`. Ray's read of it as a safety net rather
than a quality arm was correct and the binary data had obscured it.

Settled harness: hair router picks PHEAD or BC_klein, one escalation to QX on failure,
VLM picks between the two candidates. **1.526 gen/request, 32 perfect / 6 ok / 0 fail.**
Flat BC_klein is 2.000 gen for 28 / 6 / 4. The headline is the zero, not the perfect
rate.

**Three of my own recommendations were wrong and are corrected.** (1) I had said route
high-hair references to QX; on absolute marks BC_klein takes 5 of those to perfect
against QX's 4 — Ray's original call. The binary marks had inverted it because QX's
`ok`s counted as wins. (2) A third arm on escalation buys nothing: the un-chosen
subtractive arm is `fail` on 3 of the 5 escalated sets because it shares PHEAD's
failure mode. (3) The §2b ruling against a VLM priced a *closed frontier* API. A
self-hosted 7-8B open VLM is ~$0.0003 against ~$0.015 per generation, so at 2
generations per wasted escalation **it can be wrong 100 times per save and break even**.

**Concluded.** *Inference.* Routing is the half that works and the gate the half that
does not — the reverse of the "gate first, routing second" assumption v2.2.3 was built
on. A router predicting from the *input* has a physically-motivated free feature (hair
over garment, AUC 0.862); every check reading the *output* sits at 0.38-0.57. And no
deterministic artefact check is available even in principle: published AI-artefact
detectors answer "was this generated", which is true of 100% of these frames.

**Also.** The AMT tier is retired as the label of record. `perfect` there meant tied
for first among ten arms — relative, and unable to drive an absolute stop decision. It
agrees with the absolute pass on 81% of cells, so earlier conclusions built on it were
directionally right and quantitatively loose.

**Next.** Validate the VLM artefact check against the 114 absolute tiers — GPU time,
no fal spend. Then recompute the hair threshold over all 48 references. That closes
v2.2. The self-hosted parity run remains owed regardless.

---

## 2026-08-22 — the VLM gate works, but not at the question we assumed

**Did.** Built a Colab notebook (free T4, Qwen3-VL-8B at 4-bit) and graded five prompt
formulations against the 114 absolute tiers — 570 inferences, no fal spend. Also ran a
pairwise selection test in both image orderings.

**Found.** The **artefact prompt returned CLEAN on all 114 outputs** and never fired
once, including on every frame marked `fail`. Only `garment` — the one prompt that sees
the reference image — beat the accept-everything baseline, at 70.2% against 62.3%.
Every output-only formulation sat exactly on the baseline.

**Concluded.** *Inference.* Our failures are not artefacts. They are competent
photographs of the wrong thing — a plausible-but-different garment, or the input
returned unchanged — so there is nothing in the pixels that looks broken. This is the
same reason the deterministic gate failed, arriving from a different direction, and it
means **VLM-A must take the garment reference as input.** The original spec had it
screening the output alone.

Counter-intuitively, **more context was worse**: `transfer`, which sees person and
reference and output, scored below `garment`. At 8B three images appear to dilute
attention.

**VLM-B is dropped.** Pairwise selection agreed with itself on **34% of pairs** when the
images were swapped — worse than chance, so it reads position, not content — and chose
the already-failed arm 2 times in 5. Always taking QX scores 5/5. Scoring each candidate
independently and comparing (no position to be biased by) reached 4/5: structurally
better, still beaten by the trivial rule, n = 5.

**A correction to this log's own record.** The crash guard was written up as justified
by production robustness alone. That was wrong: the no-op check catches `HD_p023`, where
the model returned the person unchanged — a clean, plausible photograph that every
output-only prompt correctly calls clean. The deterministic checks and the VLM are
**complementary**, not competing.

**Shipped configuration**, on Ray's call to take the safer of two: escalate if
`tryon != PERFECT` **or** `garment == FAIL`, always to QX. **2.105 generations/request,
30 perfect / 7 ok / 1 fail**, against flat BC_klein at 2.000 for 28/6/4 — same cost, a
quarter of the failures. The cheaper gate (`garment == FAIL` alone, 1.737 gen, 31/5/2)
beats BC_klein on both axes and remains defensible.

**The hair router checked out**: never worse on 95% of sets, matching always-BC_klein's
perfect count at 63% of the cost. Worth recording that **30 of 38 are ties** — it is
mostly choosing the cheaper of two arms that both work.

**Caveat carried forward.** The model hedges — 331 of 570 verdicts are `OK`, only 49
`FAIL` — which is what caps recall at 51%. A binary forced choice and fp16 are both
untried. These numbers are Qwen3-VL-8B at 4-bit with these prompts, not a ceiling on
open VLMs.

**Next.** v2.2 is closed. The end-to-end run over the assembled pipeline, with the
SeedVR2 realism pass included so that the long-owed "composite never validated end to
end" gap closes in the same pass. Then the report. The self-hosted parity run remains
owed and now needs rented compute — the local machine has no GPU.

---

## 2026-08-22b — the realism pass is real, and it needs a gate on both sides

**Did.** Replayed the harness over stored arm outputs, took the frame it ships for each
of the 38 sets, and ran only that frame through `SeedVR2 ×2, noise_scale = 0` — the
v2.1 winner. 38 calls, $1.52, no new generations. Built a drag-wipe review page with
zoom to 12×, because at a mean absolute pixel change of 2.28/255 side-by-side
thumbnails show nothing.

**Found.** Ray's verdict by eye: the resolution increase is a **noticeable
improvement**. The instruments say the same change is small — under 1% of pixels, 12%
more high-frequency energy — and that it **cost identity on 7 of 38 frames, worst
0.772**. That is inside the range that got Z-Image Turbo eliminated in v2.1, where the
same SeedVR2 configuration had measured 0.943.

**The trigger fell out of the data.** The frames that lose identity are the frames
SeedVR2 **failed to sharpen**: where `hf_ratio < 1.0`, mean identity is 0.891 against
0.941 elsewhere, and `corr(hf_ratio, identity) = +0.512`. One signal covers both
problems — when the pass works it is safe, and when it fails it announces itself. That
is what makes a post-hoc check viable rather than requiring a good pre-hoc predictor,
which is just as well, because the pre-hoc signal is weak (`hf_before` correlates with
gain at only −0.148).

**Concluded.** *Inference.* Ship the pass **conditional on both ends**: skip when
`hf_before >= 2.5` (already sharp, so dead cost), and **revert to the original when
`identity_cos < 0.90`** (it damaged the face). 29 calls instead of 38, **no delivered
frame below 0.90 identity**, and 1.110 of the 1.121 mean sharpening gain retained. Both
checks are free and already in the pipeline.

**Revert, never retry** — SeedVR2 takes a seed but accepts no prompt, and the failure is
a property of the frame rather than the roll. Same reasoning that killed reseeding at
the escalation stage; it generalises.

**Caveat carried forward, and it matters.** AuraFace is comparing an 832×1248 frame
against a 2× upscale of itself, so part of the measured identity drop is resampling
rather than damage, and the absolute number should not be set against v2.1's 0.943.
The policy does not depend on the absolute value — the trigger uses relative ordering —
but a matched-scale re-measure is owed. The 2.5 and 0.90 cut-points are fitted on 38
frames; the mechanism is the transferable part.

**This closes two long-open items:** "klein → SeedVR2 never validated end to end", open
since v2.1, and v2.4's pre-registered question 3, "should the auxiliary stage be
conditional on a measured realism deficit?" Yes, and on the output as well as the input.

**Next.** The end-to-end run over one assembled program, then the report. The
self-hosted parity run remains owed and needs rented compute. v2.4's actual question —
does anything *beat* SeedVR2, and can anything de-gloss — is untouched.

---

## 2026-08-22c — a one-image spot-check found the bug the statistics hid

**Did.** Ray questioned a single cell in the progression grid — `HD_p028+navy_peacoat`,
the harness's one shipped failure — on the grounds that the frame did not look like it
could have come from the arm the record named. Checked the run record, then opened the
person input and the shipped output side by side.

**Found.** The person had been **substituted entirely**: the input is a man with short
auburn hair in a navy peacoat, the shipped frame a woman with long dark hair. An
earlier explanation in the same conversation had claimed "the person keeps their hair
in every arm's output, so hair in the final frame is not evidence of a wrong pick."
That explanation was wrong, and Ray's instinct was right.

**`chk_identity` on the shipped frame reads 0.755.** The check saw it. The escalation
rule did not consult identity.

**The root error.** This log recorded on 2026-08-21 that identity "fires on zero of the
three cascade arms." **That was measured at threshold 0.5.** At 0.90 it fires exactly
once in 114 cells, and that once is the only frame the harness got wrong. A rare,
precise detector was written off as dead because it was tested at the wrong operating
point, and the conclusion propagated into four documents.

**Concluded.** *Inference.* Adding `identity < 0.90` to the escalation rule takes the
harness from **2.105 gen/request, 30 perfect / 7 ok / 1 fail** to **2.158, 31 / 7 / 0**
— the last shipped failure removed for +0.05 generations per request. Now the default.

**On whether the VLM makes the deterministic checks redundant** — asked directly, and
the answer is no. All five VLM prompts passed the swapped-person frame, **including
`transfer`, which was shown the person photo and asked whether the right person was in
the result.** Head to head over 114 cells the VLM caught 26 failures the checks missed
and the checks caught 1 the VLM missed — and that 1 was the only one that shipped. A
no-op and an identity swap both produce a *competent, coherent photograph of the wrong
thing*; there is nothing in the image for a semantic judge to find. **Recall is the
wrong metric for deciding whether to drop a check that costs nothing.**

**Methodological note, and the third instance of the same lesson.** Every stage of this
pipeline has been debugged by looking, not by measuring — no-op outputs scoring
perfectly on identity, the bald-frame garment-lost metric collapsing by construction,
furniture in every crop. This is the fourth: an aggregate statistic (AUC 0.506) was
correct about the composite and wrong about a component, and only a human opening one
image caught it.

**Next.** Unchanged: the end-to-end run, self-hosted parity, the `segformer_b2_clothes`
licence, the report.
