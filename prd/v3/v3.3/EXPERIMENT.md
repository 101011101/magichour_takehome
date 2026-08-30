# v3.3 — EXPERIMENT

**Status: LOCKED 2026-08-30.** The architecture is in [SOLUTION.md](SOLUTION.md). What follows is the record of how it was arrived at; it is not amended after the lock. Opened 2026-08-28. One sub-investigation, one behaviour: **can klein do the
extraction call as well as Qwen does?**

Post-synthesis conclusions only, per [SCHEMA.md](../SCHEMA.md). Cases and per-reference
evidence are in [RESULTS.md](RESULTS.md); the matrix is [TEST.md](TEST.md).

---

## Why this arm

[v3.1](../v3.1/SOLUTION.md) is locked as two calls to two different models:

```
A4 crop → Qwen-Image-Edit-2511 (mannequin reference) → FLUX.2 klein (try-on)
```

That is two models in the deploy path. The deployment target runs klein on its own GPU
([V2 pivot](../../v2/README.md)); Qwen-Image-Edit-2511 is a second 20B-class model that
has to be hosted beside it, warm, for one call per pair. **If klein can produce the
mannequin reference, the whole pipeline is one model** — one set of weights, one
runtime, and every prompt finding from v3.1 carried over unchanged.

There is one prior data point and it cuts both ways. During V2's AC-A phase klein was
measured as a *garment* extractor and the numbers were never used: on a drift metric
klein distilled kept ×0.80 of the edge detail where Qwen kept ×0.51, and was better on
hue — but drifted **lightness 27 against Qwen's 12**
([`v3/report/artefacts.html`](../../../v3/report/artefacts.html), the AC-A drift table).
That was the QX-style *isolated garment* prompt on a raw photograph. The mannequin prompt
on the A4 crop has never been sent to klein.

## What is held fixed

**Everything except the model behind call 1.** Stated so the comparison is one variable:

| stage | v3.1 (MQ) | v3.3 (MK) |
|---|---|---|
| input | A4 crop — BiRefNet_lite @1024², head kept, white ground | **same files**, `v3/runs/v3.0b/inputs/*__A4.jpg` — *holds for links 1–1.2; links 1.3–1.4 edited the raw frame and cropped after, corrected in phase 2* |
| colour word | MediaPipe face → median L\*a\*b\* → ten-step ladder | same reader, same ladder |
| framing | MediaPipe Pose on the crop → `FRAME_CLAUSE` | same reader, same table |
| prompt | `PREFIX + <colour> + SUFFIX + FRAME_CLAUSE[category]` | **identical string** |
| seed | 46 | 46 |
| call 1 | `fal-ai/qwen-image-edit-2511` | **`fal-ai/flux-2/klein/4b/distilled/edit`** |
| call 2 | klein, `EDIT_PROMPT` | not run in this link |

The implementation is the locked Colab library, `v3/colab/lib/v3lib.py`, imported
directly — not the repo-side `run_mq.py`, which still carries the pre-dynamic clause
([v3.1 SOLUTION §7](../v3.1/SOLUTION.md#7-where-the-implementation-is)).

## The chain

### 1 — The reference only: crop → klein mannequin **← this run**

**What is investigated.** Whether klein, given the A4 crop and the v3.1 prompt verbatim,
returns a mannequin reference that passes the same checks the Qwen one was held to:

1. **the outfit is complete** — every piece the photograph shows, nothing invented
   (v3.1 link 1's failure class);
2. **the person is gone** — no face, skin, hair (the `zendaya`-under-`p7.3.1` failure);
3. **the extent matches the crop** — a waist-up crop returns a waist-up mannequin
   (link 3.1);
4. **the colour word binds to the mannequin, not the garment** (link 3.2's `tan polo`);
5. **garment fidelity** — colour, print, texture, cut. This is where the AC-A lightness
   drift would show.

**How.** All 28 garment references of the run-B fold, one klein call each, with the
prompt assembled per pair from the paired person's face and the crop's framing — exactly
as `run_all.py` does for MQ. 28 calls, ~$0.42 at the measured klein price. Output:
`v3/runs/v3.0b/refs/{garment}__MK__{person}.jpg`, prompts as sent in
`v3/runs/v3.0b/_v33_prompts.json`.

**What is shown.** Three columns per reference on `v3/report/v33_klein_extract.html`:
the A4 crop (the input), the klein mannequin (the candidate), and the Qwen mannequin
already on disk from v3.1 link 10 for orientation — with the caveat that **the Qwen
column was generated before dynamic prompting** and carries no pose clause, so it is
context and not a controlled comparison. Above each row, the colour and framing the
readers produced, so a bad output traces to a bad read.

**Decision rule.** This is a gate, by eye, on the five checks above. If the klein
references are acceptable, link 2 runs them through call 2 and scores against MQ on the
same pairs. If they are not, the failure class says whether it is a prompt problem
(klein reads the words differently — worth one iteration) or a model problem (klein
cannot regenerate a body it has not seen — stop).

**Result.** **28/28 generated. The structural checks pass on every reference; fidelity
fails on 7.** Person gone, extent honoured, colour bound, nothing invented from slots —
28/28 each, so the v3.1 prompt transfers to klein unchanged
([RESULTS §1.1](RESULTS.md#11-the-four-structural-checks-pass-on-every-reference)).
Where klein diverges is surface and silhouette: sequin, satin, embroidery and pleats come
back as their nearest smooth material, and two ambiguous hems became two legs — a dress
returned as a jumpsuit ([§1.2](RESULTS.md#12-fidelity-is-where-klein-diverges--7-of-28)).
**21/28 at parity by eye.** This is the AC-A lightness/surface drift showing up in the
mannequin setting, not a prompt problem — so a prompt iteration is unlikely to buy it
back. Whether 21/28 is enough is a product call: the failures cluster on exactly the
garments a try-on is judged hardest on.

**Reviewer's verdict (2026-08-28): not approved.** The klein mannequins are poor, and the hypothesis
raised is capacity — a 4B distilled model cannot render a plausible body *and* hold the
garment, so it trades the garment away. That predicts a specific fix: stop asking for
the body.

### 1.1 — Drop the mannequin: the outfit alone **← run, `k1` and `k4` both work**

**How.** Four garment-only wordings on the 5 serious link-1 failures plus 3 parity
references, same crop and seed, 32 calls. Each carries one grounded extent sentence from
the framing reader — a garment-only prompt against a waist-up crop can invent trousers
just as a mannequin one can ([v3.1 link 3 B](../v3.1/EXPERIMENT.md#3--three-defects-that-have-to-be-fixed-before-scoring-means-anything--two-fixed-one-parked)).
→ [RESULTS §2](RESULTS.md#2-link-11--drop-the-mannequin-klein-extracts-the-outfit-alone)

**Result. The hypothesis holds.** `k1_ghost` (invisible body) and `k4_qx` (v3.1's QX
prompt verbatim) each pass **7/8**, and between them fix **every** link-1 fidelity
failure — the sequins, the embroidery, the coat's colour, the dress that had become a
jumpsuit. klein keeps *more* surface than Qwen's QX on the same references. The mannequin
was costing the garment.

The two misses are v3.1's two prompt rules, unchanged: `k1` leaked the person once (the
drape clause kept the person in scope) and `k4` dropped a piece once (the singular
"clothing"). `k2_flat` invented bottoms by enumerating "top above bottom"; `k3_minimal`
returned **the person in a white outfit** on all eight — a bare "no person" does nothing.

### 1.2 — Over all 28, with a body-context form and an extent ablation **← run**

**How.** `k1` and `k4` over all 28, plus three new arms on all 28: `k5_form` (an
*invisible* mannequin form carrying v3.1's own extent+pose clause — body context without
a rendered body, the reviewer's ask), `k1_noext` (`k1` with no extent sentence — does the
framing reader matter here), and `k6_ghost2` (`k1` plus the body's absence stated
part by part, to close `k1`'s leak). 124 calls, 0 failures.
→ [RESULTS §3](RESULTS.md#3-link-12--the-garment-only-prompts-over-all-28-plus-a-form-and-an-ablation)

**Result.** Two usable references, failing in opposite directions. **`k4_qx` removes the
person 28/28** but presents the clothes flat and drops a piece on 2. **`k1_ghost` keeps
the worn drape and every piece 28/28** but leaks skin on 9 — every one a garment that
exposes legs, hands or a neckline: the pairing defect of v3.1 §3c.31, moved from the
edit to the reference.

Three things settled on the way:

- **Extent is not klein's problem.** `k1_noext` matches `k1` on every non-full-body
  crop; klein does not invent legs under a waist-up crop the way Qwen did. The clause is
  kept because it is free, not because it is doing work here.
- **Naming a slot fills it, even to say it is empty.** `k6`'s "no hand, no leg, no face"
  rendered a grey silhouette with hands, legs and a face on 24/28. `k5`'s "invisible
  mannequin" rendered a white mannequin on 27/28. This is v3.1 rule 1 in its strongest
  form, and it closes the door on fixing the leak with words about the body.
- **The link-1 failure was the skin-toned body, not a body.** `k5`'s white mannequin
  holds sequins, embroidery and coat colour that `MK` lost — but white is the
  low-amplitude case v3.1 built the colour reader to avoid.

~~**Next: link 2 on both `k1` and `k4`.**~~ *Superseded by link 1.3: the reviewer judged the
garment-only arms unusable and the head swap replaced them as the candidate.*

### 1.3 — Reviewer's verdict, and the head swap **← run, 28/28 clean**

**Verdict on links 1–1.2:** everything is unusable except, possibly, the `MK` mannequin.
On `k1`'s behaviour — taking a chunk out of the head and stopping — the answer is that
**klein is an editor**: it does the smallest edit that satisfies the words, removes the
region it can identify as "the person", and leaves the rest. Qwen re-renders; klein
subtracts. → [RESULTS §4](RESULTS.md#4-link-13--reviewers-verdict-on-13-and-the-head-swap-arm)

**So ask it for a subtraction.** `MH`: klein *replaces the head with a featureless
mannequin head and changes nothing else*, then the result goes through the A4 crop. One
call, one matte, and **no garment pixel is regenerated** — the reference is the real
garment with the identity removed.

**Result.** **28/28**: head replaced, hair gone including off the shoulders, garment
pixel-identical outside the head, crop clean. Sequins, embroidery, pleats and satin —
everything the regenerative arms lost — are untouched, because nothing touched them.
Skin on arms, hands and legs is kept, by design.

**What it is:** `BC` (bald pass → crop, v3.1's highest-floor arm) with a mannequin head
in place of a scalp. It inherits `BC`'s cut-boundary risk in the edit and none of the
regeneration risk. Whether the edit treats a mannequin head differently from a scalp is
a `BC`-vs-`MH` question on pairs where `BC` is already on disk.

**Reviewer's verdict: the replacement has merit and looks good — klein is good at
producing this. `MH` is marked the most promising arm in v3.3.**

### 1.4 — Can klein pose the person inside the head swap? **← run**

**Why.** `MH` keeps whatever pose was photographed, and v3.1 established that pose is
what the edit has to reconcile ([§3c.28](../v3.1/RESULTS.md#3c28-the-colour-word-does-not-only-set-colour--it-decides-what-kind-of-object-is-rendered)).
v3.1 also built the mechanism for saying it safely — one table emitting extent and pose
together, never naming a body part the crop excludes. Does that transfer from a
mannequin prompt to a person edit?

**How.** Four arms on all 28, each the head-swap sentence plus one thing: a **constant
pose** (`MH_pose` — names feet regardless), **pose + framing from one table**
(`MH_posefr` — the v3.1 rule), **framing only** (`MH_fr` — no pose word), and the head
swap with a **specific head colour** from the tone reader on the paired person
(`MH_col`). 112 calls, then the A4 crop on each.
→ [RESULTS §5](RESULTS.md#5-link-14--can-klein-pose-the-person-inside-the-head-swap-edit)

**Result. Yes — and only with the framing rule.** `MH_posefr` re-poses all 28 to neutral
and holds the extent on **28/28**; the constant-pose arm invents a whole standing body on
**7 of the 9** partial crops, and `emma_watson` came back as two — a full-frame duplication
artefact, confounded by the missing pre-crop ([RESULTS §5.5](RESULTS.md#55-reviewers-notes-on-45-recorded-2026-08-29)). Same words, one keyed on the
crop and one not. **The v3.1 rule — never name a body part the crop excludes — transfers
from a mannequin prompt to a person edit unchanged.** Prints, sequins, pleats and colour
survived the re-pose on this fold. `MH_col` binds the colour to the head and nothing else,
28/28. `MH_fr` is indistinguishable from `MH`.

**What it costs.** A re-pose re-renders the garment wherever a limb moves; `MH` never
does. On these 28 that cost was not visible, but it is a risk `MH` does not carry.

**Next: link 2 on `MH` and `MH_posefr`** — the pair asks the edit one question: does a
neutral pose in the reference beat a faithful one?

---

## Phase 2 — the version on the crop, and how far the words go

Opened 2026-08-29. Phase 1 produced a version — [SOLUTION.md](SOLUTION.md) — and two
procedural corrections: **the A4 crop comes first**, and **the dynamic pose+framing
clause is the arm**. Phase 2 runs on that template (without the colour word, so one
prompt is the baseline for both questions) and asks how much finer control the words
give: over the legs and feet, and over where the mannequin stops.

Set-up, arms and cases are in [RESULTS §6](RESULTS.md#6-phase-2--set-up-written-before-the-run-2026-08-29).

### 3 — Can the words point the feet at the camera? **← run, negative**

**Why.** `MH_posefr` neutralises the pose but says nothing about where the feet point;
`g013` and `g009` came back with angled legs. Three additions to the baseline — feet,
hips, and the reviewer's *"no turned feet …"* form — each keyed on the framing read so
the addition itself never names a part the crop excludes. The negative arm is the test
of rule 1 on this template.

**Result. No sentence earns a place.** Crop-first `P0` already puts the feet close to
straight; the feet sentence moves `g009` marginally and `g013` not at all. The hip
sentence, allowed on `waist_up`, **invented legs on 4 of 7** `waist_up` crops — rule 1. The negation did
nothing either way on 19/19, which sharpens the rule: **a negation names a slot and fills
it only if the slot is empty** (`k6`'s parts were absent; these were present).
Crop-first also removed the `emma_watson` duplication, and exposed two costs of the
re-pose that phase 1 missed: `g013`'s sandals regenerated as bare feet, `scarlett`'s
split hem as trousers.
→ [RESULTS §6.3](RESULTS.md#63-results--206-klein-calls--3-reruns-206-re-crops-reviewed-on-the-crops)

### 4 — Can the words keep the mannequin off the neck and arms? **← run, negative**

**Why.** The head swap leaks mannequin material onto the neck and arms (`g027`, `g029`).
Four wordings of the replaced region: *neck up*, *face only*, a positive
skin-preservation sentence, and the *"no mannequin material on …"* form.

**Result. No.** The neck goes with the head under every wording — it is the blend region
of the replacement, not a slot the prompt reaches. *Face only* is worse: naming a face
rendered one (nose, brow, on three references). The arm tint from phase 1 does not
reproduce on the crop-first template. The head-swap sentence stays as it is.
→ [RESULTS §6.3](RESULTS.md#63-results--206-klein-calls--3-reruns-206-re-crops-reviewed-on-the-crops)

---

## Phase 3 — pose wording, with the garment held

Opened 2026-08-29. Phase 2 closed the region question (`M1 neck-up` is the head-swap
sentence, [RESULTS §6.4](RESULTS.md#64-reviewers-notes-on-phase-2-2026-08-29)) and found
that the pose wording which names feet is what turns a skirt into trousers. Phase 3 asks
whether a coarser pose word — *legs straight*, *feet point towards the camera* — and a
sentence that holds the garment through the change buy the pose without the split.
Set-up in [RESULTS §7](RESULTS.md#7-phase-3--pose-wording-only-set-up-written-before-the-run-2026-08-29).

### 5 — Legs straight, feet towards the camera, and a garment held through the re-pose **← run, `Q3` adopted**

**How.** Six arms on the `M1` baseline, each one added sentence keyed on the framing
read, over all 28. The cases are the ones that split: `scarlett`, `g013`, and the skirts.
→ [RESULTS §7.1](RESULTS.md#71-results--107-klein-calls--2-re-seeds-seed-47-gal_gadot-q1-scarlett-q4-107-re-crops)

**Result. The garment-neutral hold sentence is the fix; the leg and foot words do
nothing.** *"The clothing stays exactly the same through the change of pose — the same
pieces, the same shape, the same length"* (`Q3`) keeps `scarlett`'s dress a dress with
its slit, on all 28, with no invention. The version that names garment types — *"a
dress stays a dress, a skirt stays a skirt"* — **put skirts on three men in trousers**:
rule 1 in its positive form, naming a garment type fills that slot. *Legs straight* and
*feet point towards the camera* are indistinguishable from the baseline. `g013`'s
sandals are not recovered by any wording; footwear is a cost of the re-pose that stays
open. **`Q3` joins the version's prompt.**

**Review, and two probes** ([RESULTS §7.2](RESULTS.md#72-review-of-link-5-and-two-probes-2026-08-29)).
`g012` grows a third foot under `Q3` — recorded as a known defect. An arms-down sentence
fixes `p030`'s raised arms on that reference; deferred to after call 2. *"Feet straight"*
is indistinguishable from `Q3` except on `g012`, which is one case and not adopted.
**`Q0` and `Q3` are the two references going into call 2.**

---

## Phase 4 — the edit

### 2 — Through call 2 **← run; parity** *(numbered 2 because it was opened in phase 1)*

`Q0` and `Q3` — both crop-first, `M1`, re-posed; `Q3` with the garment-hold sentence —
through the klein edit on the same 28 pairs, beside `BC` and `MQ` already in `gen/`. 56
calls. Set-up in [RESULTS §8](RESULTS.md#8-phase-4--call-2-set-up-written-before-the-run).
The pair prices the hold sentence at the output, and both price the re-pose against the
incumbents. (`MH`, pose kept, is not in this run by the reviewer's decision; it stays on
disk as the fallback.)

**Result. At the output, `Q3` is indistinguishable from `BC` and `MQ` on 24 of 28.**
The same edit makes the same try-on from a klein reference as from a Qwen one — **one
model, two calls, at parity with the v3.1 locked arm by eye.** Every difference on the
other four traces to the reference, none to the edit: `scarlett`'s hem comes through as
whatever the reference made of it (`Q0` trousers, `Q3` dress — the hold sentence pays
at the output); bags in the reference are worn in the output on `Q0`/`Q3`/`BC`, and only
`MQ` is without them, because Qwen dropped them at extraction. The known foot defects
(`g013`, `g012`) do not propagate where the person supplies the part. `p019 + g011`
cooks on all four arms, as v3.1 predicted it would for any reference.
→ [RESULTS §8.1](RESULTS.md#81-results--56-klein-edits-0-failures-no-black-frames-reviewed-by-eye-unscored)

---

## Phase 5 — feet out of the reference

Opened 2026-08-29. `p021 + g013` doubled its feet at the output: the wearer's sneakers
and the reference's bare mannequin feet were both reconciled. The reviewer's call is
that footwear is too much data to carry — have klein ignore it or cut it off.

### 6 — Does removing the feet from the reference remove the doubling? **← probe run, null; not extended**

**How.** Four placements of the cut — after klein on the finished reference (at the
ankles; at the ankles-or-hem), before klein on the crop so the clause never names feet,
and in the prompt — on `g013` and `g012` first, each through the edit on its own pair.
Set-up in [RESULTS §9](RESULTS.md#9-phase-5--feet-out-of-the-reference-set-up-written-before-the-run-2026-08-29).

**Result. No.** Feet cut out of the reference by three routes, and both outputs are
indistinguishable from the control: the output's feet are the wearer's own, and `p021`'s
"four legs" are two trouser legs over spread knees plus her sneakers — **a seated-pose
property of the person**, which no reference edit reaches. The cut is safe (no boundary
line came back) but buys nothing; the prompt version rendered the feet it named.
**Reviewer's decision: adopt the cut anyway** — safe, cheap, and footwear is a variable
the pipeline need not carry. The seated case is researched in
[RESULTS §9.2](RESULTS.md#92-reviewers-decision-on-feet-and-a-research-note-on-the-seated-case-2026-08-29):
the wearer's own two-leg silhouette in image 1 is what the dress is made to fill —
a pairing property (seated knees-apart × dress), proposed for a detector, not a fix.
→ [RESULTS §9.1](RESULTS.md#91-probe-results--g013-g012-4-reference-calls-10-edits-0-failures)

---

## Phase 6 — the first change to call 2

Opened 2026-08-29. Every prompt experiment in V3 has been on call 1; the edit prompt has
been a constant since V2. `p021 + g013`'s third tube comes from image 1's layout
([RESULTS §9.2](RESULTS.md#92-reviewers-decision-on-feet-and-a-research-note-on-the-seated-case-2026-08-29)),
which only call 2 sees — so if words can reach it, they are words in call 2.

### 7 — Does a body-count sentence in the edit prompt stop the third tube? **← run; `E3` adopted**

**How.** Four sentences appended to the edit prompt — the reviewer's *"do not add any
body parts"*, a positive count, a grounding in image 1, and a garment-side form — on the
failing pair and three clean ones, `Q3` reference held fixed. 16 edits.
Set-up in [RESULTS §10](RESULTS.md#10-phase-6--a-body-count-sentence-in-call-2-set-up-written-before-the-run-2026-08-29).

**Result. Yes — with the grounded positive, and only that.** *"The person's body, limbs
and feet are exactly as in image 1 — nothing added, nothing removed"* (`E3`) removes
the third tube on `p021` and changes nothing on the three clean pairs. The count
sentence removed it too, but by re-rendering the person with identity and pose drift
on all three — v3.1 §4.2's cost. The negation does nothing either way (the parts it
names are present — no empty slot); the garment-side sentence is partial with a side
effect. `E3` is v3.1 rule 2 — *tell the model what is there* — reaching call 2 for the
first time. (First read from the contact sheet as inert; corrected on the reviewer's
full-size reading.) **On all 28, `E3` is indistinguishable from the V2 prompt on 27 and
fixes the 28th — adopted.** The edit prompt changes for the first time in V3.
→ [RESULTS §10.2](RESULTS.md#102-e3-on-all-28--24-further-edits-0-failures)
→ [RESULTS §10.1](RESULTS.md#101-results--16-edits-0-failures)

---

## Phase 7 — arms in partial crops

### 8 — Does an arms row in `PERSON_CLAUSE` bring `p030`'s arms down, at the output? **← run; adopted**

One-row change to the table (`chest_up` gains *"arms down, relaxed at the sides"* — the
only row without an arms phrase); `p030` is the only reference whose prompt changes.
Regenerated and edited. Set-up in [RESULTS §11](RESULTS.md#11-phase-7--arms-in-partial-crops-set-up-written-before-the-run-2026-08-29).

**Result. The reference is fixed; the output is unchanged.** Arms down, clean bust,
framing held. The output is identical because the wearer supplies his own arms — the
same neutrality every reference-pose change has shown where the person's pose dominates.
Adopted as a row of the table, which is the form v3.1 set for pose wording.
→ [RESULTS §11.1](RESULTS.md#111-result--1-reference-call-1-edit-0-failures)

---

## Phase 8 — the version, whole, on the fold

### 9 — Does the complete version have side effects on ordinary pairs? **← run; none**

Every adopted piece — `Q3` reference, ankle cut, arms row, `E3` edit — run together on
all 28, beside the `E3`-without-cut outputs. **Indistinguishable on 27 of 28**; the one
difference is the cut doing its job (`p025`'s wearer keeps her own boots instead of the
reference's shoes). → [RESULTS §12.1](RESULTS.md#121-result--indistinguishable-on-27-of-28-one-intended-difference)

**Reviewer: `Q3` and `E3` approved.** The version in [SOLUTION.md](SOLUTION.md) is the
one that ran here.

---

## Conclusion

*Reached; locked 2026-08-30.* v3.3 asked whether klein could take the extraction call. It
cannot regenerate a mannequin or an isolated garment to Qwen's standard (links 1–1.2),
but it does not need to: **asked for the edit it is built for — replace the head, re-pose,
hold the garment — on the A4 crop, it produces a reference that the try-on edit cannot
tell from Qwen's.** The deploy path is one model. [SOLUTION.md](SOLUTION.md) carries the
version. Open: accessory carry-over (a product decision), the `chest_up` arms sentence,
person-side pose cases beyond what the `E3` sentence reaches, the tone ladder inherited from v3.1, and — as in every V3
investigation so far — a scored comparison rather than a reviewer's eye.

Same 28 pairs, same edit prompt and seed. `MH` first — beside `BC` and `MQ`, both already
in `v3/runs/v3.0b/gen/` — 28 klein calls. `MK`, `k1` and `k4` only if the reviewer wants
them; on the reference evidence they are behind `MH`.

---

## Conclusion

*Not reached.*
