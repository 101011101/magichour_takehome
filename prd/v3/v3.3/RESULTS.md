# v3.3 — RESULTS

**Status: open; sections 1–6 reported, call 2 not run.** Evidence for [EXPERIMENT.md](EXPERIMENT.md). One reviewer, unblinded, by eye against the
five gate checks. Page: `v3/report/v33_klein_extract.html`; runner `v3/build/run_v33_extract.py`. Outputs:
`v3/runs/v3.0b/refs/{garment}__MK__{person}.jpg`; prompts as sent:
`v3/runs/v3.0b/_v33_prompts.json`.

## 1. Link 1 — klein as the extractor, 28 references

**28/28 generated, 0 failures, 28 klein calls (~$0.42).**

### 1.1 The four structural checks pass on every reference

| check | result |
|---|---|
| person gone (no face, skin, hair) | **28/28** — no `zendaya`-class leak; every output is a featureless mannequin |
| extent matches the crop | **28/28** — the 3 `waist_up` (`p029`, `emma_watson`, `g029`), 1 `chest_up` (`p030`) and the `knee_up`/`full_body` cases all stop where the crop stops |
| colour word binds to the mannequin | **28/28** — no garment took the skin colour; white garments (`p029`, `p030`, `zendaya`, `g009`) stayed white |
| nothing invented from accessory slots | **28/28** — backpack (`p029`), handbag (`g004`, `LOWRES` knit), clutch dropped; no hats or bags appear that were not there |

The prompt findings of v3.1 transfer to klein **without change**: the same words produce
the same permissions in the other model.

### 1.2 Fidelity is where klein diverges — 7 of 28

| # | reference | what klein did | Qwen (v3.1) |
|---|---|---|---|
| 7 | `queen_latifah_gown_stage` | gold embroidered kimono-coat rendered as a plain beige/grey coat, embroidery gone, a belt added | gold and embroidery kept |
| 8 | `scarlett_johansson_black_dress_backview` | **the dress became a jumpsuit** — a split hem read as two legs | dress |
| 11 | `lp_beige_long_coat_menswear` | coat lightness/warmth lost — beige to grey — and an invented inner strap | closer on colour |
| 23 | `g015` | navy satin slip: skirt rendered **sheer**, legs visible through it | opaque |
| 28 | `g030` | gold sequin jacket rendered as smooth metallic foil, front left open | sequin texture kept |
| 9 | `woman_top_denim_skirt` | denim skirt read as shorts (minor, hem ambiguous in the crop) | skirt |
| 25 | `g024` | pleated skirt lost its pleats, smooth panel | pleats kept |

**21/28 are at parity with or indistinguishable from the Qwen reference by eye** —
including the hard prints (`g027` Ramones tee, `g012`, `g013`, the floral kimono set,
`g029` houndstooth, the plaid overcoat).

### 1.3 The failure class

All seven are **material or silhouette re-interpretation, not prompt disobedience**:
sequin, satin, embroidery and pleats — surfaces with high-frequency structure — come
back as their nearest smooth material, and two ambiguous hems (`scarlett`, `denim_skirt`)
were resolved as two legs. This is the AC-A finding
([`v3/report/artefacts.html`](../../../v3/report/artefacts.html)) in the mannequin setting:
klein distilled drifts on lightness and surface, and here it also restructures. It is
**not** the boundary-copying failure v3.0 documented for klein as an *editor* — there is
no crop boundary in any output.

### 1.4 What this cannot claim

- The Qwen column is the **pre-dynamic** reference (no pose clause). The prompt is the
  same for the mannequin/colour/extent clauses, so checks 1–4 are comparable; the pose is
  not.
- One seed. Whether the seven are seed-stable is untested.
- Reference quality is not try-on quality — v3.1 link 2's caveat stands. Link 2 answers
  it.

## 2. Link 1.1 — drop the mannequin: klein extracts the outfit alone

**Reviewer verdict on §1, recorded verbatim in substance:** the klein mannequins are
poor. Hypothesis raised: a 4B distilled model does not have the capacity to render a
plausible body *and* hold the garment, so it trades the garment away — ask it for the
clothes only and the budget goes to the clothes.

**How.** Four wordings × 8 references (the 5 serious §1.2 failures + 3 parity cases
`g027`, `g018`, `gal_gadot`), same A4 crop, same seed, 32 klein calls, 0 failures.
Outputs `v3/runs/v3.0b/refs/{g}__k{1..4}_*.jpg`, prompts `_v33_garment_prompts.json`,
runner `v3/build/run_v33_garment.py`, page `v3/report/v33_garment_only.html`. Qwen's `QX` reference for each is on disk for
orientation.

| | wording | extent |
|---|---|---|
| `k1_ghost` | the outfit "as if worn by an invisible body", drape and position kept, person gone, exact copy, the bag guard | + one grounded sentence from the framing reader |
| `k2_flat` | every piece laid flat "top above bottom, each piece whole and separate" | same |
| `k3_minimal` | 22 words: "whole outfit on pure white, no person, every piece exactly as photographed" | same |
| `k4_qx` | v3.1's `QX_PROMPT` verbatim — the control against Qwen's QX | none (as QX) |

### 2.1 Per-variant, 8 references

| variant | pass | what happened |
|---|---|---|
| **`k1_ghost`** | **7/8** | every §1.2 failure fixed: Latifah's gold embroidery, the beige coat's colour, `g015` opaque, `g030`'s sequins, Scarlett's dress a dress. **One leak** — `scarlett`: the arm, legs and heels came back around the dress (person not gone) |
| `k2_flat` | 2/8 | **"top above bottom" invented bottoms**: a dress became cami + trousers (`scarlett`, `g015`, `gal_gadot`), shorts appeared under the Ramones tee and the `g018` blazer. Rule 1 of v3.1 again — naming a slot fills it |
| `k3_minimal` | **0/8** | **returned the person, wearing a white version of the outfit**, on all eight. "no person" is a negation and was ignored; the garment colour collapsed to white every time. Fails the same way `zendaya`-under-`p7.3.1` did, only worse |
| **`k4_qx`** | **7/8** | as good as `k1` on fidelity — sequin, embroidery, coat colour all right. One drop — `g018` came back as the blazer alone, no trousers (the v3.1 link 1 "the clothing" singular failure) |

### 2.2 Against Qwen's QX on the same eight

klein `k1`/`k4` keep **more** surface than Qwen: the sequins on `g030` and the embroidery
on `queen_latifah` are sharper than the Qwen QX reference. This is the AC-A finding the
right way round — klein keeps edge detail (×0.80 vs ×0.51), and without a body to render
the lightness drift did not show. `g018` is the one place Qwen QX is more complete.

### 2.3 What the eight say

- **The hypothesis holds on this cohort.** The five references klein could not hold as a
  mannequin it holds as garment-only. The mannequin was costing the garment.
- **The two failures are the two v3.1 prompt rules, unchanged:** `k1` leaked the person
  (the drape clause "position it has on the person" kept the person in scope) and `k4`
  dropped a piece (the singular). Neither is a capacity failure.
- `k2` and `k3` are dead: enumeration invents, and a bare negation does nothing.

### 2.4 What this cannot claim

Eight references, chosen because five of them failed §1 — not a fair sample. One seed.
Reference only; no edit has been run on any of these. Whether klein copies an
invisible-body reference into a try-on the way it copied cut boundaries in v3.0 is
exactly what link 2 has to answer.

## 3. Link 1.2 — the garment-only prompts over all 28, plus a form and an ablation

**Correction to §1 and §2's orientation column.** v3.1's dynamic-prompt Qwen references
exist for **8 references only** (link 14, `refs/{g}__dyn.jpg`: `p029`, `emma_watson`,
`g018`, `p030`, `queen_latifah`, `g013`, `g014`, `man_black_suit`). The 28-pair MQ run
predates dynamic prompting. The page now shows the dynamic Qwen where it exists and
labels the rest pre-dynamic.

**Are the k prompts dynamic?** Yes on extent: every variant except `k4` (QX verbatim,
the control) and `k1_noext` (the ablation) carries one sentence keyed on the framing
reader. No colour word — there is no mannequin to colour. `k5` carries v3.1's own
`FRAME_CLAUSE` (extent *and* pose) with the noun swapped to "form".

**How.** `k1_ghost`, `k4_qx`, `k5_form`, `k1_noext`, then `k6_ghost2`, each over all 28
garment references. 124 klein calls, 0 failures. `k2`/`k3` stay at the 8-reference probe.
Outputs `refs/{g}__k*.jpg`, prompts `_v33_garment_prompts.json`.

| | wording, beyond `k1` | intent |
|---|---|---|
| `k1_noext` | `k1` with **no** extent sentence | is the framing reader doing anything here |
| `k5_form` | *"worn by an invisible mannequin: the clothes hold the shape of a body — shoulders, chest, waist, hips — but the mannequin itself cannot be seen, so the collar, cuffs and hem open onto nothing"* + `FRAME_CLAUSE` | keep body context without rendering a body — the reviewer's ask |
| `k6_ghost2` | `k1` + *"where a sleeve ends there is no hand, where a hem ends there is no leg and no foot, at the collar there is no neck, no face and no hair"* | state the body's absence concretely, the way the bag guard does, to close `k1`'s limb leak |

### 3.1 Per variant, 28 references

| variant | person gone | pieces complete | fidelity | what happened |
|---|---|---|---|---|
| **`k4_qx`** | **28/28** | 26/28 | best | flat, product-shot presentation rather than worn drape. Drops: `g018` trousers, `man_black_suit` shirt and tie. `g009` kept the bag |
| **`k1_ghost`** | 19/28 | 28/28 | best | worn drape kept. **9 leaks, all exposed skin**: legs under dresses, skirts and shorts (`gal_gadot`, `scarlett`, `denim_skirt`, `g005`, `g014`, `g024`), hands (`man_black_suit`, `g029`), hair (`scarlett`) |
| `k1_noext` | 18/28 | 28/28 | best | **indistinguishable from `k1` on extent** — no invented legs under any of the 9 non-full-body crops in either arm. One extra leak: `p029` kept the hands and phone |
| `k5_form` | 1/28 | 28/28 | good | **"invisible mannequin" rendered a visible white mannequin, with a head, on 27/28.** Fidelity held — sequins, embroidery, coat colour — so the §1 problem was the skin-toned body, not a body as such. But white is v3.1's low-amplitude case: `p029`, `p030`, `zendaya`, `g009` are white-on-white again |
| `k6_ghost2` | 4/28 | 28/28 | good | **naming the absent parts rendered them.** A flat grey silhouette body fills exactly the slots the sentence names — hands, legs, feet, neck, head — on 24/28; `p030` grew hair. Worse than `k1` on every leak case and on cases `k1` had clean |

### 3.2 What the 28 say

1. **Extent is not the problem for klein.** `k1` and `k1_noext` produce the same extent
   on every non-full-body crop. Qwen invented trousers under waist-up crops
   ([v3.1 link 3 B](../v3.1/EXPERIMENT.md)); klein, given the crop, does not. The extent
   sentence costs nothing and is kept, but it is not what is deciding these outputs.
2. **Naming a slot fills it — even to say it is empty.** `k6` is the cleanest instance
   of v3.1 rule 1 yet: "no hand … no leg … no face" produced a grey body with hands,
   legs and a face. `k2`'s "top above bottom" invented bottoms. `k5`'s "invisible
   mannequin" produced a mannequin. The concrete-negative form that worked for the bag
   works because a bag is one object; a body is a list of slots.
3. **The leak is skin, and it is the pairing again.** `k1` fails exactly where the
   garment exposes skin — bare legs, hands, an open neckline. That is the region
   v3.1 §3c.31 identified as the one the edit cannot recover either. Garment-only does
   not remove the problem; it moves it from the edit to the reference.
4. **`k4` removes the person because it never mentions a body at all** — "the clothing
   … isolated … remove the person entirely." The price is the drape and an occasional
   dropped piece: the v3.1 link 1 singular.

### 3.3 Where that leaves the candidates

Two references are usable from this run, and they fail in opposite directions:

- **`k4_qx`**: clean 28/28, flat, drops a piece on 2/28.
- **`k1_ghost`**: draped, complete 28/28, leaks skin on 9/28 — every one on a garment
  that exposes skin.

Neither has been through call 2. ~~**Link 2 should run both**~~ *(superseded by §4: the head
swap replaced the garment-only arms)*, beside `MQ` and `BC`, on the same 28 pairs — because whether klein copies a leaked leg, or a flat drape, into a
try-on is the thing no reference comparison can say.

### 3.4 What this cannot claim

One seed, one reviewer, by eye. The Qwen comparison column is dynamic on 8 and
pre-dynamic on 20. No edit has been run.

## 4. Link 1.3 — reviewer's verdict on §1–§3, and the head-swap arm

**Reviewer, on the full page:** essentially everything in §2–§3 is unusable; the only
arm with any merit is `MK`, the mannequin. Reviewer's question on `k1`: why does it take
a chunk out of the head and stop? Answer: klein is an editor. It performs the smallest
edit that satisfies the words — it locates what it can identify as "the person" (the
head, sometimes the skin) and removes that region, leaving the rest as it was. Qwen
re-renders the picture; klein subtracts from it. That is the v3.0 finding — klein
reproduces whatever its input contains — seen from the extraction side.

**Which is the argument for the next arm.** If klein subtracts, ask it for a subtraction:
**replace the head with a mannequin head and change nothing else**, then hand the result
to the A4 crop. The reference is then a real photograph of the real garment with the
identity removed — the `BC` shape (bald pass → crop) with a mannequin head instead of a
scalp. One klein call, one matte, no regeneration of any garment pixel.

`MH` = klein head-swap → BiRefNet A4 crop. Prompt, colour-free:

> *Replace this person's head with a smooth, featureless mannequin head of the same size,
> in the same position and facing the same way — no face, no hair. Keep the clothing, the
> body, the hands, the pose and the background exactly as they are.*

### 4.1 Result — 28 klein calls, 28 A4 crops, 0 failures

Outputs `refs/{g}__MHraw.jpg` (klein output, full frame) and `refs/{g}__MH.jpg` (after
the A4 crop). Runner `v3/build/run_v33_headswap.py`; on `v3/report/v33_klein_extract.html`.

| check | result |
|---|---|
| head replaced, face and hair gone | **28/28.** Every reference comes back with a smooth featureless head where the person's was, hair removed including where it fell on the shoulders (`scarlett`, `g009`, `g024`, `g029`) |
| garment untouched | **28/28 by construction** — klein edited the head region only; sequins (`g030`), embroidery (`queen_latifah`), pleats (`g024`), the satin slip (`g015`), the Ramones print, all pixel-identical to the photograph outside the head |
| body, hands, pose, background kept | 28/28 — skin on arms, hands and legs is **kept**, by design; this is the `BC` shape (bald → crop), not a mannequin |
| extent | the photograph's own — nothing to invent, nothing to cut |
| A4 crop on the swapped frame | clean on all 28; the matte handles the mannequin head as subject |

Small things, none blocking: the head's colour is whatever klein chose (mostly beige,
`g005` grey, `man_black_suit` dark); `p030` (arms raised over the head, chest-up) gets a
head tucked under the arms, plausible but odd; `g027` keeps the neck tattoo.

### 4.2 What this is and is not

`MH` is **`BC` with a mannequin head instead of a scalp**: a real photograph of the real
garment, identity removed, cropped. It carries `BC`'s properties — the highest floor of
any arm in v3.1 (no `fail`, five `ok`) and `BC`'s known weakness, the **cut boundary klein
copies into the edit** (v3.0), plus exposed skin the edit has to reconcile against the
wearer's. What it does *not* carry is any regeneration risk: there is no prompt that can
lose a garment it never re-rendered.

Against `BC`, the difference is small and specific: `BC` leaves a scalp, `MH` leaves a
mannequin head. Whether the edit treats those differently is the question for link 2,
and it is a `BC`-vs-`MH` question on the same 28 pairs, both already on disk for `BC`.

### 4.3 Reviewer's verdict on MH

**The replacement has merit and looks good; klein is good at producing this result.**
Marked as **the most promising arm in v3.3**. The reason it works is the reason the
regenerative arms did not: klein is asked for the kind of edit it is built for — a
local replacement with everything else held — and the garment is never in the model's
hands at all.

## 5. Link 1.4 — can klein pose the person, inside the head-swap edit?

**Why.** `MH` keeps the photograph's pose. v3.1 found that pose matters downstream
(§3c.28: strides and a second leg are what the edit has to reconcile), and it built one
table, `FRAME_CLAUSE`, that emits extent and pose together so they never disagree. The
question is whether that machinery transfers to a *person* edit: can klein re-pose the
wearer to neutral while swapping the head, and does the dynamic framing rule — never
name a body part the crop excludes — hold it in place.

**Four arms, all on the raw normalised photograph, then the A4 crop.** The head-swap
sentence is common to all; what changes is what follows it.

| arm | adds to the head swap | dynamic? |
|---|---|---|
| `MH_pose` | a **constant** pose sentence: *"…stands upright in a neutral pose, facing forward, arms relaxed at the sides, feet together."* | no — names feet whether or not the crop has them |
| `MH_posefr` | **pose + framing from one table**, `PERSON_CLAUSE[framing]` — the v3.1 `FRAME_CLAUSE` rewritten for a person; below the hip there are no feet to put together | yes |
| `MH_fr` | **framing only**: *"The photograph shows the person from the head to the hip only; keep exactly that framing."* No pose word | yes |
| `MH_col` | the head swap alone, with the mannequin head given a **specific colour** from the tone reader on the paired person: *"a smooth, featureless `dark beige skin` mannequin head"* | yes (colour per pair) |

For the two posing arms, "the pose" is removed from the *keep exactly as they are* list —
otherwise the sentence contradicts itself. Framing category from `v3lib.framing()` on the
raw photograph, colour from `v3lib.tone()` on the paired person; prompts as sent in
`_v33_pose_prompts.json`; outputs `refs/{g}__{arm}raw.jpg` and `refs/{g}__{arm}.jpg`.
112 klein calls, 112 crops. Runner `v3/build/run_v33_pose.py`; page `v3/report/v33_pose.html`.

**What would count.** Per arm: is the head swapped (the baseline must not regress); did
the pose change and to what; did the extent change — legs invented under a waist-up
photograph is the failure `MH_pose` is expected to produce and `MH_posefr` to avoid; and
is the garment still pixel-faithful, which a re-pose cannot guarantee the way a head swap
can. `MH_col`: does the colour bind to the head and only the head.

### 5.1 Result — 112 klein calls, 0 failures; reviewed on the raw frames; the 112 A4 crops completed after review and are on the page

Framing read on the 28 raw photographs: 19 `full_body`, 6 `waist_up` (`emma_watson`,
`queen_latifah`, `g018`, `g027`, `g029`, `g030`), 2 `chest_up` (`p029`, `p030`), 1 unread. On
the A4 crops phase 2 read 19 `full_body`, 7 `waist_up`, 1 `knee_up` (`queen_latifah`), 1
`chest_up` (`p030`) — `p029` and `g015` move to `waist_up` on the crop.

| arm | head swapped | pose changed | extent held | garment | verdict |
|---|---|---|---|---|---|
| `MH_pose` (constant, names feet) | 28/28 | 28/28 → neutral, feet together, facing front | **19/28 — every full-body holds; 8 of the 9 non-full-body crops zoom out to invent a whole standing body with legs.** `emma_watson` came back as **two** full-length mannequins | held on the full-body cases; softened where a body was invented | the predicted failure, exactly where predicted |
| **`MH_posefr`** (pose + extent, one table) | 28/28 | 28/28 → neutral; arms down, facing front; `g024` and `scarlett` turned from side-on to frontal | **28/28** — every waist-up stays waist-up, `p030` stays chest-up, no legs invented anywhere | prints (`g027`, `g012`, `g013`, kimono), sequins (`g030`), pleats (`g024`) and the beige coat's colour all held through the re-pose; drape re-rendered where limbs moved | **works. The v3.1 rule transfers to a person edit unchanged** |
| `MH_fr` (framing only, keep pose) | 28/28 | none (as instructed) | 28/28 | pixel-faithful, as `MH` | indistinguishable from `MH`; the extent sentence is inert when nothing asks for a change |
| `MH_col` (head colour from the paired person) | 28/28 | none | 28/28 | pixel-faithful, as `MH` | **colour binds to the head and only the head, 28/28** — `black skin` gives a black head (`man_black_suit`, `g009`, `g029`), `dark brown` a dark brown one (`g027`, `g012`); garment untouched |

### 5.2 What the run says

1. **klein can re-pose the person, and the dynamic framing rule is what makes it safe.**
   `MH_pose` and `MH_posefr` differ only in whether the pose sentence is keyed on the
   framing read; the constant one invents a body on 8/9 partial crops, the keyed one on
   0/9. Same mechanism as v3.1 link 14, now on a person rather than a mannequin.
2. **Re-posing costs pixel fidelity by construction, and in practice costs little.** `MH`
   never re-renders the garment; `MH_posefr` must, wherever a limb moves. On this fold
   the re-render held print, sequin, pleat and colour. Hands-in-pockets, crossed arms and
   the phone in `p029` are gone — that is the point of a neutral pose, and it is also a
   garment-region regeneration that `MH` never risks.
3. **`MH_col` is free.** The head colour is a one-word slot the reader already fills, it
   binds correctly on 28/28, and it changes nothing else. Whether a head that matches the
   wearer's tone helps the edit is a link-2 question.
4. **`MH_fr` adds nothing to `MH`.** An extent sentence with no pose instruction has
   nothing to hold in place.

### 5.3 Candidates going into link 2

`MH` (photograph's pose, pixel-faithful) and `MH_posefr` (neutral pose, extent held,
re-rendered drape), each optionally with the colour word. The pair isolates one question
for the edit: **does a neutral pose in the reference beat a faithful one?**

### 5.4 What this cannot claim

One seed, one reviewer, raw frames (the A4 crops were still running at review; the crop
does not change pose or extent). No edit run. The 8 waist-up cases are the whole evidence
for the framing rule on a person.

### 5.5 Reviewer's notes on §4–§5, recorded 2026-08-29

1. **The pose is good. Open: leg and feet control.** On `g013` and `g009` the legs and
   feet are not pointed straight at the camera. Asked for: variants on foot direction,
   hip control, and negative prompting. Constraint found while recording this: the fal
   klein edit endpoint exposes **no `negative_prompt` field** (input schema: `image_urls`,
   `prompt`, `seed`, `num_inference_steps`, `image_size`, `num_images`,
   `output_format`, `enable_safety_checker`, `sync_mode`), and v3.1 rule 1 plus `k6`
   (§3.1) say that negation *inside* the prompt names a slot and fills it. Any "negative"
   arm therefore has to be positive wording about where the feet point.
2. **`emma_watson` under `MH_pose` duplicated.** Reviewer attributes this to the missing
   pre-crop (v3.1 §3c.12: a landscape canvas produces two figures). Confirmed: **the MH
   inputs were NOT cropped beforehand** — links 1.3 and 1.4 ran klein on the raw
   normalised photograph, full frame with background, and the A4 crop was applied *after*.
   So that one case is confounded. The other 7 `MH_pose` failures are **not**
   duplication — they are zoom-outs that invent a whole body under a partial crop — and
   that is the naming-feet failure v3.1 link 3 B found on inputs that *were* cropped. The
   two arms are therefore not both passing; the honest reading is that `MH_posefr` passes
   28/28 and `MH_pose` has one confounded and seven real failures. **Decision for the next
   phase: crop first, then klein, then a cheap bbox re-crop** — see §5.6.
3. **The mannequin head is good, but the mannequin material spreads to the arms on
   some references.** Asked for: variants on the replaced region — neck up, face only —
   and negative prompting (same constraint as 1).
4. **`MH_col` is good with no major corruption; it goes into the next version.** A
   `SOLUTION.md` is to carry the current version so the experiment chain does not have to
   be re-read to know what has passed. The colour word is to be revisited after inquiries
   1–3.

### 5.6 The crop-order question, settled for the next phase

Every klein arm so far ran on the full frame and cropped afterwards. v3.1 established
that the crop is the reference's biggest lever (§3c.12, link 9) and that klein attends to
what it is given. For the next phase the order is **A4 crop → klein edit → bbox re-crop**:
the A4 crops already exist for all 28 (`inputs/{g}__A4.jpg`, white ground, head kept), so
the edit sees a subject on white and a portrait canvas; the re-crop after the edit is a
40 ms pose-bbox, needed only because a re-pose can move the silhouette. No second matte.

## 6. Phase 2 — set-up, written before the run (2026-08-29)

**Template, fixed for every arm:** `inputs/{g}__A4.jpg` (the v3.1 crop, white ground,
head kept) → klein edit, seed 46 → bbox re-crop on the near-white ground (no second
matte). Prompt = head swap + `PERSON_CLAUSE[framing]`, **no colour word**. Framing read
on the A4 crop, as in v3.1. Prompts as sent: `_v33_p2_prompts.json`; outputs
`refs/{g}__p2_{arm}raw.jpg` and `refs/{g}__p2_{arm}.jpg`; runner
`v3/build/run_v33_phase2.py`; page `v3/report/v33_phase2.html`.

**Note on "negative prompt".** The reviewer's term means an in-prompt clause of the form
*"no <thing>"* — not an endpoint parameter (the endpoint has none). Two arms below carry
one, so the question v3.1 rule 1 and `k6` raise — does *"no X"* produce X — is tested on
this template rather than assumed.

### 6.1 Link 3 — pose variants: legs and feet

The specific cases: **`g013`** and **`g009`** — under `MH_posefr` the legs and feet are
not pointed straight at the camera. Every arm is `P0` plus one sentence, and the added
sentence is itself keyed on the framing read so that it never names a part the crop
excludes: foot wording only on `full_body`, knee wording on `knee_up`, hip wording on
`waist_up` and above. Cells whose wording would be identical to `P0` are not re-run
(same prompt, same seed, same output).

| arm | adds | on |
|---|---|---|
| `P0` | nothing — the template baseline, crop-first for the first time | all 28 |
| `P1 feet` | *"Both feet flat on the ground, side by side, toes pointing straight at the camera."* / `knee_up`: *"Both legs straight, knees pointing at the camera."* | 20 cells (crop read: 19 `full_body` + 1 `knee_up`) |
| `P2 hips` | *"Hips square to the camera, weight even on both legs, legs straight."* | 27 cells |
| `P3 no-` | *"No turned feet, no bent knee, no twist in the hips."* — the reviewer's negative form | 19 `full_body` |

**What counts.** On `g013`/`g009` specifically: do the feet point at the camera. On all:
did the sentence change anything else — extent, garment, the head swap.

### 6.2 Link 4 — the head-swap region: keeping the mannequin off the arms

The specific cases: **`g027`** (neck and ears rendered as mannequin, arms tinted) and
**`g029`**, plus the `MH_col` frames generally, where mannequin material reaches the
neck and arms. Every arm changes the head-swap sentence only; the pose clause is `P0`'s.

| arm | head-swap sentence |
|---|---|
| `M1 neck-up` | *"Replace this person's head, from the neck up, with a smooth, featureless mannequin head of the same size, in the same position and facing the same way — no face, no hair."* |
| `M2 face-only` | *"Replace only this person's face with a smooth, featureless mannequin face, and remove the hair; the neck is unchanged."* |
| `M3 skin-kept` | `P0`'s sentence + *"The skin of the neck, the arms and the hands stays exactly as photographed — the same colour and texture."* (positive) |
| `M4 no-` | `P0`'s sentence + *"No mannequin material on the neck, the arms or the hands."* (the negative form) |

**What counts.** On `g027`/`g029`: is the neck skin, are the arms untinted. On all: is
the head still fully replaced (hair gone), and did the region wording cost the pose.


### 6.3 Results — 206 klein calls + 3 reruns, 206 re-crops; reviewed on the crops

**Procedure notes.** (a) Three cells came back as a **solid black frame** at seed 46 —
`scarlett` `P1_feet`, `scarlett` `M1_neckup`, `gal_gadot` `M2_faceonly` — and stayed
black with `enable_safety_checker=false`, so it is the model at that seed, not
moderation; **seed 47 rendered all three** and is recorded in the prompt json for those
cells only. (b) The framing reader on the *crop* differs from the raw-frame read in
phase 1: `queen_latifah` is now `knee_up` and `g015` `waist_up` (the dress hides the
ankles). Both clauses fired correctly for what the crop shows. (c) **Crop-first removes
the duplication**: `emma_watson` `P0` is one figure, waist-up.

#### Link 3 — legs and feet (`g013`, `g009`)

| arm | on `g013` / `g009` | elsewhere |
|---|---|---|
| `P0` | feet already close to straight on the crop-first baseline — `g013` toes forward, `g009` a slight outward angle. **`g013`'s sandals are gone: bare mannequin feet** (a re-pose regenerates footwear) | 28/28 extent held; `emma_watson` no longer duplicates; **`scarlett`'s dress re-rendered as a jumpsuit** in every pose arm — the re-pose reads the split hem as two legs, the §1.2 failure returning through call 1 |
| `P1 feet` | `g009` marginally more forward; `g013` unchanged. **Not a decisive lever** | no side effects on the 19 full-body |
| `P2 hips` | no change on the two cases | **"legs straight" on a `waist_up` crop invents legs**: `p029` and `emma_watson` came back full-length; `g029`, `g030` zoomed out. 4 of 7 waist-up. Rule 1 again — the hip sentence was allowed on `waist_up` and names legs |
| `P3 no-` | no change | **no artefact either.** "No turned feet, no bent knee" neither fixed nor broke anything on 19/19 |

**Reading.** The residual angle on `g009` is below what words move; the crop-first `P0`
already delivers most of what the feet sentence was for. `P2` is withdrawn from
`waist_up`. `P3` is the first negation in v3.3 that did not fill its slot — the parts it
names (feet, knees, hips) already exist in the frame, so there is no slot to fill; `k6`'s
grey body appeared where the named parts were *absent*. That is a sharper form of rule 1:
**a negation names a slot; it fills it only if the slot is empty.**

#### Link 4 — the head-swap region (`g027`, `g029`)

| arm | `g027` / `g029` | elsewhere |
|---|---|---|
| `P0` | head **and neck** rendered as mannequin down to the collar; **arms are skin** on the crop-first run — the arm tint seen in phase 1 does not reproduce here | — |
| `M1 neck-up` | identical to `P0` | identical |
| `M2 face-only` | **facial features rendered** — nose and brow on `g027`, `g029`, `p030` (lips and closed eyes). Naming "face" produced a face | same on `p030` |
| `M3 skin-kept` (positive) | neck still mannequin; no change | head colour drifts lighter on `beige_coat`, `zendaya` |
| `M4 no-` (negative) | neck still mannequin; no change, no artefact | — |

**Reading.** The neck goes with the head on every wording: it is where the replacement
region blends, not a slot the prompt reaches. **None of the four wordings moves it**, and
`M2` makes it worse by naming a face. The arm concern from phase 1 is not reproduced
crop-first. The neck is accepted as-is for now; if it matters at call 2, the lever is not
the prompt.

#### What phase 2 settles

1. Crop-first is the procedure; the `P0` template is the baseline going forward.
2. The pose+framing clause is kept unchanged. No feet/hip/negation sentence earns a
   place; `P2` on `waist_up` is actively harmful.
3. The head-swap sentence is kept unchanged. Region wording does not reach the neck.
4. **Two costs of the re-pose are now on record:** footwear regenerated (`g013`) and
   a split hem read as trousers (`scarlett`). `MH` without the pose clause has neither.
   That is the trade link 2 has to price.

### 6.4 Reviewer's notes on phase 2 (2026-08-29)

1. **`M1 neck-up` is good enough; it goes into the version.** The neck is accepted as
   part of the replaced region.
2. **The feet-specific wording is what splits a skirt or dress into trousers** — when the
   sentence names feet or toes, the hem is read as two legs (`scarlett`, and `g013`'s
   sandals becoming bare feet). *"Legs straight"* may be sufficient on its own.
3. Try *"feet point towards the camera"* rather than *"toes pointing straight at the camera"*.
4. Try a garment-integrity sentence alongside the pose change — the clothing stays the
   same through the re-pose, a skirt stays a skirt.
5. **`p030`**: arms raised over the head in a `chest_up` crop; the `chest_up` clause says
   nothing about arms, so they stay up and the head is rendered beneath them. The
   rendering of the arms is off. Recorded; not addressed in phase 3.

## 7. Phase 3 — pose wording only, set-up written before the run (2026-08-29)

**Template, fixed:** `A4 crop → klein (M1 head swap + PERSON_CLAUSE[framing] + one added
sentence) → bbox re-crop`, seed 46, no colour word. `Q0` is the phase-2 `M1` cell, not
re-run. Every added sentence is keyed on the framing read and fires only where the part
it names is in frame; a cell whose prompt equals `Q0`'s is not re-run. Prompts
`_v33_p3_prompts.json`; outputs `refs/{g}__p3_{arm}raw.jpg` / `.jpg`; runner
`v3/build/run_v33_phase3.py`; page `v3/report/v33_phase3.html`.

| arm | adds | fires on |
|---|---|---|
| `Q0` | nothing — `M1` + `PERSON_CLAUSE`, the version's baseline | — |
| `Q1 legs` | *"Legs straight."* | `full_body`, `knee_up` |
| `Q2 legs+garment` | *"Legs straight. Every garment keeps its shape through the change of pose: a dress stays a dress, a skirt stays a skirt, its hem hanging as one piece."* | `full_body`, `knee_up` |
| `Q3 garment` | *"The clothing stays exactly the same through the change of pose — the same pieces, the same shape, the same length."* | all |
| `Q4 feet` | *"Feet point towards the camera."* | `full_body` |
| `Q5 legs+feet+garment` | `Q2`'s sentence + *"Feet point towards the camera."* | `full_body` (`knee_up` gets `Q2`'s) |

**Cases to read first:** `scarlett` (dress → trousers under every phase-2 pose arm),
`g013` (sandals → bare feet), `g009` (residual foot angle), `g015`, `g024` (skirt),
`gal_gadot` (slit dress).

### 7.1 Results — 107 klein calls + 2 re-seeds (seed 47: `gal_gadot` `Q1`, `scarlett` `Q4`), 107 re-crops

| arm | `scarlett` (dress → trousers?) | garment invention | other |
|---|---|---|---|
| `Q0` (`M1` baseline) | trousers | — | `g013` bare feet |
| `Q1 legs` | trousers | none | no visible change from `Q0` on 20/20 |
| `Q2 legs + "a dress stays a dress, a skirt stays a skirt"` | **dress** | **a skirt appears over the trousers on `hugh_jackman`, `man_black_suit`, `navy_quarterzip`** — naming a skirt produced one, on men in trousers. `gal_gadot`'s slit closed into a wrap hem; `queen_latifah`'s coat shortened | rule 1, positive form |
| **`Q3 "the clothing stays exactly the same — same pieces, same shape, same length"`** | **dress, slit kept** | **none on 28/28** | pleats, prints, `zendaya`'s trousers all held; `g013` still bare feet |
| `Q4 feet` | trousers | none | feet direction not visibly changed on `g009`; nothing gained over `Q0` |
| `Q5 legs + hem + feet` | dress | **skirts on `hugh_jackman`, `navy_quarterzip`**; `gal_gadot`'s slit closed | as `Q2` |

**Reading.**
1. **The garment-held sentence fixes the split, and only its garment-neutral form is
   safe.** `Q3` names no garment type and holds `scarlett`'s dress as a dress with the
   slit intact, on every framing, with no invention anywhere. `Q2`/`Q5` say *"a skirt
   stays a skirt"* and put skirts on three men — rule 1 in its positive form: **naming a
   garment type fills that slot too.**
2. **"Legs straight" and "feet point towards the camera" do nothing on their own** (`Q1`,
   `Q4` indistinguishable from `Q0`), and `Q4` still splits `scarlett`. The residual foot
   angle on `g009` is not reachable by wording; the split was never about the legs — it
   is the re-pose reading a hem, and `Q3` addresses the hem directly.
3. **`g013`'s sandals are not recovered by any arm.** Footwear regeneration is a cost of
   the re-pose that the garment sentence does not cover; footwear is not "clothing" to
   the model. Left open.

**Adopted:** `Q3`'s sentence joins the version's prompt, unconditionally (it fires on all
framings and names nothing). `Q1`, `Q2`, `Q4`, `Q5` rejected.

### 7.2 Review of link 5, and two probes (2026-08-29)

**Reviewer's cases.** (a) **`p030`** — arms raised over the head in a `chest_up` crop
stay raised under every arm; asked for an arms-down sentence, on that reference only.
(b) **`g012` under `Q3`** — **a third foot appears under the hem** (confirmed on the
crop: three feet). (c) Try *"feet straight"* rather than *"feet point towards the
camera"*. (d) **`Q0` and `Q3` are the two references marked for call 2.**

**Probes** — all on the `Q3` prompt, runner `v3/build/run_v33_probe.py`, 21 calls.

| probe | on | result |
|---|---|---|
| `A1` + *"Arms down, relaxed at the sides."* | `p030` | **fixed** — arms down, head clear, bust framing kept |
| `A2` + *"Arms at the sides."* | `p030` | **fixed** — same |
| `Q6` + *"Feet straight."* | 19 `full_body` | indistinguishable from `Q3` on 18/19; **`g012` returns two feet.** One case, one seed: cannot be told apart from re-sampling, so `Q6` is *not* adopted on this evidence |

**Recorded, not adopted yet:** an arms sentence works on `p030` and would belong in the
`chest_up` (and possibly `waist_up`) rows of `PERSON_CLAUSE` — the reviewer's decision
is to iterate that after call 2. The `g012` extra foot stands as a known `Q3` defect at
seed 46.

## 8. Phase 4 — call 2, set-up written before the run

**What goes through the edit.** Two references per pair, both crop-first, both `M1`:

| arm | reference | what it is |
|---|---|---|
| `Q0` | `refs/{g}__p3_Q0.jpg` | head swap + pose+framing, no hold sentence |
| `Q3` | `refs/{g}__p3_Q3_garment.jpg` | the version: + the garment-hold sentence |

Against `BC` and `MQ`, already in `gen/` for the same 28 pairs, same edit prompt
(`v3lib.EDIT_PROMPT`), seed 46. 56 klein calls. Outputs `gen/{set_id}__Q0.jpg`,
`gen/{set_id}__Q3.jpg`. Scored on the V2 ternary, one reviewer.

**Cases to read first:** the pairs whose reference carries a known re-pose cost —
`g013` (bare feet), `g012` (`Q3` extra foot), `scarlett` (`Q0` trousers vs `Q3` dress),
`p030` (arms up) — and the v3.1 hard pairs `g011`/`p019` (exposed skin) and `zendaya`
(white on white).

### 8.1 Results — 56 klein edits, 0 failures, no black frames. Reviewed by eye, unscored

**Headline: at the output, `Q3` is indistinguishable from `BC` and `MQ` on 24 of 28
pairs.** The same edit, given a klein-made reference instead of a Qwen-made one, produces
the same try-on. On the four pairs that differ:

| pair | `Q0` | `Q3` | `BC` | `MQ` | reading |
|---|---|---|---|---|---|
| `p008 + scarlett` | **trousers** | **dress, slit kept** | trousers | dress | the reference defect propagates straight through the edit: `Q0`'s jumpsuit becomes a jumpsuit on the person, `Q3`'s dress a dress. **The hold sentence pays at the output.** `BC` — the raw photograph, side-on — also came out as trousers |
| `p001 + p029` | backpack transferred | backpack transferred | backpack transferred | no backpack | **accessories in the reference come through the edit.** `MQ` is the only arm without the bag, because Qwen dropped it at extraction (v3.1 link 1). Neither the head swap nor the hold sentence removes a bag; nothing in the prompt asks to |
| `p018 + g009` | bag strap transferred | bag strap transferred | bag strap transferred | none | same |
| `p003 + emma_watson` | blazer over the person's own dress | blazer + a dark skirt | blazer over the dress | blazer + black skirt | a waist-up reference leaves the lower body to the edit; the four arms resolve it differently, none wrongly |

**The known reference defects did not propagate where the person supplies the part:**
`g013`'s bare mannequin feet (`p021` is seated, her own shoes are kept), `g012`'s third
foot (`p020` stands side-on, hem clean). They propagate where the *garment* carries the
defect: `scarlett`'s hem.

**The v3.1 hard pairs are unchanged:** `p019 + g011` cooks on all four arms — the
exposed-skin pairing defect of v3.1 §3c.31 is not a reference property and no reference
fixes it; `p010 + zendaya` (white on white) is fine on all four.

### 8.2 What this settles

1. **One model, two calls is at parity with the v3.1 locked arm at the output, by eye,
   on this fold.** Qwen can leave the deploy path.
2. **The reference decides the output's garment structure** — a dress in, a dress out;
   trousers in, trousers out; a bag in, a bag out. Every difference between arms traces
   to the reference, none to the edit. This is v3.0's finding, confirmed on a
   regenerated-head reference.
3. **Accessory carry-over is the one place `MQ` is ahead**, and it is ahead by an accident
   of Qwen's extraction, not by design. Whether the klein head swap should also drop
   bags is a product decision (v3.1 link 2 said the same); if yes, it is a sentence in
   call 1, and rule 1 says it must be concrete (*"if they are carrying a bag, the bag is
   gone"*), not enumerated.
4. `Q3` over `Q0`: one pair decided, none reversed. The hold sentence stays.

### 8.2b Reviewer's note on §8.1 (2026-08-29)

**Most of `Q3` is good.** One pair called out: **`p021 + g013`** — extra legs/feet in the
output. On the crop: the seated wearer (knees apart, sneakers) receives the dress as
**wide trousers**, and the feet region mixes the wearer's sneakers with the reference's
bare mannequin feet — `MQ`'s output on the same pair shows a sandal beside the sneakers.
Reviewer's hypothesis: the feet in the reference are a fidelity hazard; proposal: a `Q`
series with the reference **cut off at the ankles**, or any cheaper way of removing feet
from the reference. Discussed before any run; see §9 when opened.

### 8.3 What this cannot claim

Unscored — read by eye against the incumbents, one reviewer, one seed, 28 pairs. No
ternary tier assigned. The parity claim is "no visible difference on 24/28", not a number.

## 9. Phase 5 — feet out of the reference, set-up written before the run (2026-08-29)

**Reviewer's decision:** footwear is too much to carry; have klein ignore it or cut it
off. **Probe first** on the two references with known foot defects — `g013` (bare feet,
seated wearer `p021`) and `g012` (third foot, wearer `p020`) — then the fold.

**Where the cut sits.** "After" = a CPU cut on the finished `Q3` reference (head swap and
re-pose done), before the edit. "Before" = the cut on the A4 crop, so the framing reader
sees no ankles, the clause never names feet, and klein never regenerates them.

| arm | where | how | cost |
|---|---|---|---|
| `R1 ankle-after` | after | `Q3` reference cut at `min(ankle_y) − 3%` from the pose reader | CPU only |
| `R2 hem-after` | after | as `R1`, but if the lowest non-white row *above* the ankles (the hem, on a full-length garment) is higher than the ankle line, cut there — so the cut never runs through a hem | CPU only |
| `R3 ankle-before` | before | A4 crop cut at the ankles → klein (`M1` + `PERSON_CLAUSE` on the new read + hold sentence) → re-crop | 1 klein call per ref |
| `R4 prompt` | in the prompt | `Q3`'s prompt + *"The frame ends at the ankles; the feet are outside it."* on the uncut A4 crop | 1 klein call per ref |

Each reference then goes through the edit on its own pair. **What counts:** does the
doubled-feet region on `p021 + g013` go away; does the cut edge come back as a hard line
in the output (v3.0's boundary copy); does `R4` — which names feet to exclude them —
render them (rule 1).

Runner `v3/build/run_v33_feet.py`; outputs `refs/{g}__p5_{arm}.jpg`, `gen/{set_id}__{arm}.jpg`;
prompts `_v33_p5_prompts.json`; page `v3/report/v33_phase5.html`.

### 9.1 Probe results — `g013`, `g012`; 4 reference calls, 10 edits, 0 failures

**Reader note.** The pose reader found **no ankles on the finished `Q3` reference** for
`g013` (a mannequin-headed, re-posed frame) — the cut fell back to the ankle ratio
measured on the A4 crop, scaled. On `g012` it read the reference directly. `R3`'s cut
crop read as `waist_up` (knees present but under confidence), so its clause said "cut off
below the hip"; klein kept the full dress regardless.

| arm | reference | `p021 + g013` output | `p020 + g012` output |
|---|---|---|---|
| `Q3` (control) | feet in | trousers, sneakers | dress |
| `R1 ankle-after` | feet gone, cut just above the hem's lowest edge | **indistinguishable from `Q3`** | indistinguishable |
| `R2 hem-after` | identical to `R1` — on both references the hem sits below the ankle line, so the hem rule never fired | indistinguishable | indistinguishable |
| `R3 ankle-before` | klein on the cut crop: full dress, no feet, extent kept despite the `waist_up` clause | indistinguishable | indistinguishable |
| `R4 prompt` | **feet rendered anyway** — *"the feet are outside it"* named them | indistinguishable | indistinguishable |

**Reading.**
1. **The reference's feet are not what the output's feet come from.** With the feet cut
   out of the reference by three different routes, `p021`'s output is the same: her own
   sneakers, and the dress as trousers over her spread knees. The "four legs" on that
   pair are two wide trouser legs plus two shoes — **the seated pose, on the person's
   side**, which no reference edit reaches (the same person-side mechanism as §8.1's
   `scarlett` note, inverted).
2. **No boundary artefact.** The ankle cut did *not* come back as a hard line in the
   output (v3.0's boundary copy did not fire here) — so cutting feet is *safe*, just not
   *useful* on these two.
3. **`R4` is rule 1 again**: naming the feet to exclude them rendered them.
4. Footwear transfer, where wanted, would be lost by `R1`–`R3`; where the wearer's own
   shoes dominate, as here, the reference's feet were never used.

**Decision:** phase 5 is **not** extended to the fold. Feet stay in the reference; the
`p021` case is reclassified as a **person-pose** case (seated, knees apart) alongside
`p019`'s exposed skin — pairing properties the reference cannot fix.

### 9.2 Reviewer's decision on feet, and a research note on the seated case (2026-08-29)

**Decision.** Removing the feet from the reference is adopted as a general measure — it
is safe (§9.1: no boundary line came back), it costs a 36 ms pose read plus a crop, and
it removes footwear as a variable the pipeline would otherwise have to carry. `R1
ankle-after` goes into the version; where the reader finds no ankles on the re-posed
frame it falls back to the ankle ratio measured on the A4 crop (§9.1, `g013`).

**The question left open:** why does a *seated* wearer come back with extra legs? What
follows is research against the evidence on disk and the mechanism already documented in
[INVESTIGATION.md §3.1](../INVESTIGATION.md#31-image-2-is-not-conditioning-it-is-clean-tokens-in-the-same-attention-sequence),
labelled per [SCHEMA.md §4](../SCHEMA.md#4-provenance-for-external-work).

**What is actually in the frames.** Of the four seated wearers in the fold, three are
fine: `p022 + g014` (legs extended, dress), `p023 + g015` (side-on on a stool, dress),
`p024 + g018` (suit). The one that fails, `p021 + g013`, is **frontal, knees wide apart,
in jeans, in a wire chair**. On its outputs, read at full size: `Q3`, `BC` and **every
§9.1 cut variant** render **three fabric tubes** — her left leg, her right leg, and the
dress's centre panel hanging between the knees, shaped like the legs on either side of
it. Her feet stay two (two socks, two sneakers). `MQ` additionally adds **a sandal beside
her sneakers** — a third foot. So there are two separate defects on one pair, and the
"third leg" is fabric, not a limb.

**Verified:** the §9.1 edits were fed the cut references (`g013` R1/R2 at 512×1328
against the 512×1632 `Q3`; every output timestamped after its reference). The third tube
survives the feet cut, which is the stronger form of the finding below: it does not come
from the reference.

**Cause 1 — the dress becomes trousers: the person's layout, not the reference.**

- **[documented]** Image 1 and image 2 are tokens in one attention sequence, with a
  positional bias toward same-coordinate pairs (§3.1). The target's layout is set from
  image 1 at the early, low-frequency steps (§3.3).
- **[inferred, well-supported]** `p021`'s image 1 contains two clearly separated leg
  silhouettes in jeans with a gap between them, and the edit prompt says *keep the body
  and pose exactly*. The strongest low-frequency structure below the waist is therefore
  two tubes and a gap. The model does put dress fabric into the gap — the dress *would*
  hang there — but the only vertical structure it has to shape it by is the leg on either
  side, so the centre panel comes out as a third tube. The reference is standing with a
  straight hem, so its rows map onto her shins and say nothing about how fabric spans
  two knees.
- **[documented, indirect]** This is the person-side twin of the FitDiT / TryOnDiffusion
  finding already cited in §3.2: an agnostic that follows the wearer's contours makes
  the model *fill the contours*. Here there is no agnostic at all — the jeans are still
  in image 1 — so the contour it fills is the jeans'.
- **[speculative]** A training prior compounds it: frontal, seated, knees apart, wide
  fabric on each leg is the canonical wide-leg-trouser pose; a maxi dress on a wearer
  seated knees-apart needs a fabric bridge between the knees that is rarer in
  training data and requires cloth reasoning the model may not do at 4 steps.

**Why the other three seated cases pass:** legs extended (`p022`) and side-on (`p023`)
present one silhouette below the waist, not two; `p024` receives trousers, which *want*
two tubes.

**Cause 2 — the extra foot on `MQ`: reference row-copy at the feet row.**

- **[inferred]** `MQ`'s reference (Qwen's mannequin) wears sandals at a row that, after
  the `cap_pixels` resize, lands near her feet row in image 1; the position-privileged
  channel of §3.1 copies the sandal in beside her sneakers. Our `Q3` reference has bare,
  low-contrast mannequin feet at that row and does not do it — which is consistent with
  §9.1 finding that cutting our feet changed nothing: **there was little to copy.** It is
  also why the reviewer's feet decision is right in general: a *salient* foot in the
  reference (a sandal, a boot) at the wrong row is a copy hazard, and the cut removes it
  before it can be one.

**What would address cause 1, in order of cost.**

1. **Detect and flag** — the pose reader already gives hips and knees on image 1; knee
   separation over hip width, with hip–knee angle, identifies "seated, knees apart" in
   36 ms. Same shape as the exposed-skin detector v3.1 §3c.31 asked for: a *pairing*
   flag, not a fix. Cheapest, and honest.
2. **A person-side agnostic for the legs** — mask the region below the waist in image 1
   so there is no jeans contour to fill. This is the Krea2 mask → crop → edit → stitch
   pattern in `references/REFERENCES.md`, applied to the garment region. It reintroduces
   the boundary problem V2 spent its time on, on the person side.
3. **A call-2 prompt sentence** — untested; rule 1 says a sentence that names the knees
   or the gap will render something there. Lowest expectation.

Not run. Recorded for the next phase; the case is a **pairing** property (wearer pose ×
garment type), like `p019`'s exposed skin, and belongs in the same detector.

## 10. Phase 6 — a body-count sentence in call 2, set-up written before the run (2026-08-29)

**Reviewer's proposal:** put a sentence in the *edit* prompt — *do not add body parts*,
or similar — and see whether the third tube on `p021 + g013` goes. This is the first
variation of call 2 in all of V3 (v3.1 SOLUTION §6 item 5 named it the largest untouched
surface). Rule 1 predicts the negative form names limbs and may render them; the
positive forms are the control on that.

**Held fixed:** the `Q3` reference (`refs/{g}__p3_Q3_garment.jpg`, uncut — the ankle cut
exists only for the two probe references and §9.1 showed it changes nothing here),
image 1 the person, seed 46. Only the edit prompt varies. `E0` is the existing `Q3`
output.

| arm | edit prompt = `EDIT_PROMPT` + | form |
|---|---|---|
| `E0` | nothing — *"Dress the person in image 1 in the clothing shown in image 2. Keep the person's face, identity, body and the background exactly as they are."* | control |
| `E1` | *"Do not add any body parts."* | the reviewer's negative |
| `E2` | *"The person has exactly two legs and two feet."* | positive count |
| `E3` | *"The person's body, limbs and feet are exactly as in image 1 — nothing added, nothing removed."* | positive, grounded in image 1 |
| `E4` | *"The clothing drapes over the body as one garment; the body underneath is unchanged."* | garment-side positive |

**Pairs.** `p021 + g013` (the case), and three where `Q3` was clean, to see what the
sentence costs elsewhere: `p022 + g014` (seated, legs extended), `p008 + scarlett`
(the dress the hold sentence saved), `p003 + emma_watson` (waist-up reference, lower
body invented by the edit). 4 × 4 = 16 edits. Runner `v3/build/run_v33_edit2.py`;
outputs `gen/{set_id}__E{n}.jpg`; page `v3/report/v33_phase6.html`.

### 10.1 Results — 16 edits, 0 failures

| arm | `p021 + g013` (the case) | the three clean pairs |
|---|---|---|
| `E0` control | three tubes | clean |
| `E1` *"Do not add any body parts."* | centre panel fainter, still there — **not fixed**; two feet | no visible change on any of the three |
| `E2` *"exactly two legs and two feet"* | two tubes (culottes) — but **the whole person is re-rendered**: pose, braids, shoes changed | **identity and pose drift on all three** — `scarlett`'s wearer re-framed and the bag gone, `p022`'s legs and feet re-drawn, `emma_watson`'s blazer became a full-length coat |
| **`E3`** *"body, limbs and feet exactly as in image 1 — nothing added, nothing removed"* | **passes** — read at full size: the fabric spans both knees as one continuous width, no centre column; two legs, two feet, chair intact. (First recorded as "no change" from the contact sheet; corrected on the reviewer's reading, 2026-08-29) | **no change on any of the three** |
| `E4` *"drapes over the body as one garment; the body underneath is unchanged"* | centre panel reduced, fabric reads more as one piece; two legs still tube the dress — **partial** | `emma_watson`: lower body resolved as her own burgundy skirt instead of an invented dark one — different, not wrong; other two unchanged |

**Reading.**
1. **Naming a count re-renders the body.** `E2` is the only sentence that removed the
   third tube, and it did so by regenerating the person — the cost v3.1 §4.2 predicted
   for any constraint that competes with identity. Rejected.
2. **The negative form does nothing much either way** (`E1`), like `P3` in phase 2: the
   parts it names are present, so there is no empty slot to fill, and nothing to remove
   that the layout did not already put there.
3. **Grounding in image 1 (`E3`) is the one that works, and it works without touching
   the person.** It is v3.1 rule 2 — *tell the model what is there* — applied to call 2:
   the sentence names nothing to add or remove, it states the body as given, and the
   fabric is then draped over that body rather than shaped by its silhouette.
4. **The garment-side sentence (`E4`) is the only one that moves the fabric rather than
   the body**, and it moves it partway. It also changes how a waist-up reference's lower
   body is resolved (`emma_watson`), which is a second effect to price before adoption.

**Decision:** `E3` is the candidate — the first change to the edit prompt since V2. It
is validated fold-wide (§10.2) before adoption; `E4` is kept as the fallback. The
pairing flag (§9.2) remains worth having for the cases wording does not reach.

### 10.2 `E3` on all 28 — 24 further edits, 0 failures

`E0` (the V2 edit prompt) beside `E3`, same `Q3` reference, same seed, every pair of the
fold. **Indistinguishable on 27 of 28; `p021 + g013` fixed.** No pair is worse under
`E3`: identity, background, garment and accessories match `E0` on every other pair
(`p011`'s coat shades a little differently; `p018`'s ground shadow shifts — neither a
defect). The waist-up `emma_watson` pair, which `E4` had changed, is unchanged under `E3`.

**Adopted.** The edit prompt of record becomes:

> *Dress the person in image 1 in the clothing shown in image 2. Keep the person's face,
> identity, body and the background exactly as they are. The person's body, limbs and
> feet are exactly as in image 1 — nothing added, nothing removed.*

The first change to call 2 in V3, and it is v3.1 rule 2 verbatim: tell the model what
is there.

## 11. Phase 7 — arms in partial crops, set-up written before the run (2026-08-29)

**The case.** `p030`: arms raised over the head, `chest_up` on the crop. Under the
version's prompt the arms stay raised and the head is rendered beneath them (§6.4 item 5);
§7.2's probe showed *"Arms down, relaxed at the sides"* appended to the prompt fixes it.

**The change.** `PERSON_CLAUSE` is a table, so the fix is a row edit, not an appended
sentence: `chest_up` becomes *"…faces the camera squarely, shoulders level, **arms down,
relaxed at the sides**. The photograph shows them from the head to the chest only…"*.
`waist_up` already carries *"arms relaxed at the sides"*; `full_body` and `knee_up` too.
So the only reference whose prompt changes is `p030` — every other reference's prompt is
byte-identical to phase 3's and is not re-run.

**Run.** `p030` reference regenerated from the new table (`refs/p030__p7_Q3.jpg`), then
through the edit with the `E3` prompt on its pair `p002 + p030`, beside the existing
`Q3` reference and its `E3` output. 1 klein reference call, 1 edit. Runner
`v3/build/run_v33_arms.py`; page `v3/report/v33_phase7.html`.

### 11.1 Result — 1 reference call, 1 edit, 0 failures

| | old `chest_up` row | new row (*arms down, relaxed at the sides*) |
|---|---|---|
| `p030` reference | arms raised over the head, head rendered beneath them | **arms down, clean bust, head clear**; framing held at chest-up (the top of the jeans shows, as the person's did) |
| `p002 + p030` output, `E3` | white turtleneck, wearer's own pose | **identical** — the wearer supplies his own arms, so the reference's arms never reached the output on this pair |

**Reading.** The row edit does what the §7.2 probe did, as a table entry rather than an
appended sentence — which is the form v3.1 established for pose wording: one read, one
row, never two sentences about the same fact. At the output it is neutral on this pair,
as every reference-pose change has been where the wearer's own pose dominates (§8.1,
§9.1). It matters for the reference's quality and for any pair where the edit *does*
lean on the reference's arms (a sleeveless or open-sided garment); none such is in the
fold for `chest_up`.

**Adopted.** `PERSON_CLAUSE["chest_up"]` carries the arms phrase; every row now does.
`p030` is the only reference whose prompt changed; the other 27 are untouched.

## 12. Phase 8 — the complete version on the fold (2026-08-29)

**Why.** `Q3` approved; `E3` approved; the ankle cut and the arms row adopted — but the
four had never been run *together* through the edit on ordinary pairs. The reviewer's
concern is unintended consequences on the normal cases. The check: the complete version
on all 28, beside the `E3` outputs already on disk, which differ only by the ankle cut
(and the arms row on `p030`).

**The version as run.** `refs/{g}__V.jpg` = the `Q3` reference (`p030`: the phase-7
arms-row one) with the ankle cut; `gen/{set_id}__V.jpg` = the `E3` edit from it. 28
cuts, 28 edits, 0 failures. Record `_v33_version.json`; runner
`v3/build/run_v33_version.py`; page `v3/report/v33_version.html`.

The cut fired on 20 references; on the 8 partial crops (`p029`, `emma_watson`,
`queen_latifah`, `g015`, `g018`, `g027`, `g029`, `g030`) the reader found no ankles and
nothing was cut — correct, there are none.

### 12.1 Result — indistinguishable on 27 of 28; one intended difference

| pair | `E3`, no cut | `V`, the version | reading |
|---|---|---|---|
| `p025 + g024` | the reference's cream shoes transferred | **the wearer's own black boots kept** | the cut doing what it was adopted for: footwear is no longer carried by the reference |
| the other 27 | — | **indistinguishable** — identity, background, garment, accessories, feet all as `E3` | no side effect |

`p021 + g013` stays fixed (two legs, `E3`); `p008 + scarlett` stays a dress; `p019 + g011`
still cooks (pairing defect, all arms, all phases). The `p002 + p030` output is identical
from the arms-row reference (§11.1).

**Reviewer's approval:** `Q3` and `E3` approved; the version is the one in
[SOLUTION.md](SOLUTION.md). Unscored.

*Aside, not part of the check:* six additional pairings (fold garments on other people
from the 200-pair matrix) were run through the version earlier the same day and are on
disk as `gen/{set_id}__P8E3.jpg` with `_v33_p8.json`; they were not reviewed for this
section and make no claim here.

## 13. The iron-man run — data on disk, unscored (2026-08-30)

**Run** `v33_ironman_run_20260830_0548` — the locked version (`V`) against `BC`, self-hosted
`black-forest-labs/FLUX.2-klein-4B` (bf16) on an **NVIDIA A100-SXM4-40GB** in Colab, over the
**200-pair matrix** (`v3/testsets/v3_full_matrix.csv`), **seeds 46, 47, 48**. Bundle
`v33_ironman_bundle.zip` @ `v3.3-lock`; runner `v3/colab/lib/run_ironman.py`; notebook
`v3/colab/v33_ironman.ipynb`. Unpacked to `v3/runs/ironman/20260830_0548/` (gitignored);
page `v3/report/v33_ironman.html` (blinded; key `key.csv` beside the run).

| | |
|---|---|
| outputs | **1,200** — 200 pairs × 2 arms × 3 seeds; **0 black frames**; 17 distinct output sizes, each the person's |
| references | 56 `V` (head swap → re-crop → ankle cut), 56 `BC` (bald → A4 crop) |
| klein calls | **1,312** — 656 per arm — at **2.04 s per call** (mean; `edit/V` 2.04, `edit/BC` 2.16, `ref/V` 0.96, `bald/BC` 1.70) |
| model load | 251.6 s, once (from the Drive HF cache) |
| wall time | **57.6 min** end to end, including load and 112 crops |
| A4 crop | **6.8–7.4 s per crop** — BiRefNet ran on the host CPU, not the GPU (`onnxruntime-gpu` did not expose `CUDAExecutionProvider` on this runtime); 112 crops ≈ 13 min of the wall time. On the GPU this would be seconds |
| cost | **CAD 0.66** measured — 57.6 min at CAD 0.689/h (5.3 CU/h × CAD 0.13/CU); the notebook's placeholder USD 1.20/h gave USD 1.15 and is kept in `cost.json` under `as_run` |
| fal-equivalent | USD 19.68 at $0.015/call — the self-hosted run is **~30× cheaper per call** |
| per output | CAD 0.0005 per pair-arm-seed |

**What this run is.** Evidence for the scoring that locks the version: a blinded page of
400 A/B cells per seed, the key held beside the run. **No verdicts are recorded here.**
The reviewer scores on the V2 ternary; the numbers go in a §14 when they exist.

**One observation, not a score.** The version's call 1 is cheaper than the incumbent's:
a `V` reference costs 0.96 s + 0.04 s of CPU where a `BC` reference costs 1.70 s + a
second crop (7.4 s on this CPU) — the head swap on the already-cropped frame is a smaller
edit than the bald pass on the raw one.
