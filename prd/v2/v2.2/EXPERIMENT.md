# v2.2 Experiment — attention and failure

## 1. Goal

One question: **did the model make the correct change?** Not how pretty the
result is, not how realistic — whether the edit that was asked for is the edit
that happened. Three ways it fails, all in scope:

| # | Failure | What it looks like |
|---|---|---|
| **F1** | **Wrong person** | Content from the garment reference leaks in — the reference model's face, body or background appears in the output |
| **F2** | **Wrong clothes** | A plausible garment that is not the reference garment, or the reference garment rendered imprecisely |
| **F3** | **No change, or garbage** | The transformation is simply not made, or the frame is degenerate |

Realism, gloss, seams and artifacts are **not** in scope (v2.1 and v2.3). Region
restore and the predicted-warp metric were removed from this workstream on
2026-08-15 — see [../V2.x_DIRECTIONS.md](../V2.x_DIRECTIONS.md).

## 2. Approach

The premise: klein's attention is diluted across everything in the reference
images. It sees a garment *and* a stranger's face *and* a room, and spreads
attention roughly uniformly across all of it. Remove what is not the subject and
the attention lands where it should.

| | Scope | Mechanism |
|---|---|---|
| **2.2.1** | Crop the **garment** reference | Segment the clothes (and the body carrying them, where visible), place on white, crop tight with a safety margin |
| **2.2.2** | Crop **both** — garment and person | 2.2.1, plus: crop the person out, run the edit on that crop, composite the person back onto the original background |
| **2.2.3** | Failure catch | Deterministic gate that detects a failed generation |

**F1 is expected to be solved structurally by 2.2.1**, not by a detector.
Cropping the reference removes the reference person's head and background, so
there is nothing left to leak. klein already scored `wrong_person` 0.00 on all 13
pairs before any cropping; this should hold, and it is checked by eye rather than
gated.

## 2b. Observed baseline failures (traceability record)

**Observation.** Human review by eye of the **uncropped klein baseline** on
Testset2. Observer: Ray. Date: 2026-08-15. Method: visual inspection of the 13
base outputs, no metric consulted. Recorded verbatim below, separated from the
inference that follows it.

**Artifacts to verify against** — the exact files reviewed:

| pair | base output | inputs | viewer |
|---|---|---|---|
| ts2_09 | `v2/runs/ts2/outputs/klein_4b_edit__ts2_09.png` | person `dualuse_hugh_jackman_grey_suit_outdoor`, garment `dualuse_lp_plaid_overcoat_brown_suit` | `v2/artifacts/v221_klein_trial.html` |
| ts2_10 | `..._ts2_10.png` | person `dualuse_zendaya_white_blazer_skirt`, garment `dualuse_lp_floral_kimono_set` | same |
| ts2_11 | `..._ts2_11.png` | person `dualuse_emma_watson_black_blazer_armscrossed`, garment `dualuse_man_black_suit_studio_nonceleb` | same |
| ts2_12 | `..._ts2_12.png` | person `dualuse_man_black_suit_studio_nonceleb`, garment `dualuse_hugh_jackman_grey_suit_outdoor` | same |

**What was observed, as stated:**

| pair | kind | observed failure |
|---|---|---|
| ts2_09 | duo_lookbook | AI artefacts |
| ts2_10 | duo_lookbook | AI artefacts |
| ts2_11 | duo_swap | failed to transfer the clothes |
| ts2_12 | duo_swap | wrong individual, two people overlaid, wrong background |

**The distribution, which is a fact about the set, not a judgement:** all four are
duo pairs — the garment reference is a photograph of a person. **4 of 7 duo pairs
failed; 0 of 6 product pairs failed.**

### What the automated judges said about the same four

Recorded because it bears on how much weight the metrics can carry, and because a
future reader will otherwise assume the failures were caught.

| pair | det score | garment_sim | identity | bg_psnr | VLM garment | VLM scene | VLM clean | caught? |
|---|---|---|---|---|---|---|---|---|
| ts2_09 | 0.865 | 0.860 | 0.886 | 21.2 | 4 | 5 | 4 | **no** — scores *above* the 9-pair mean of 0.824 |
| ts2_10 | 0.725 | 0.799 | 0.871 | 18.9 | 4 | 5 | 4 | partially — low det, but VLM called it good |
| ts2_11 | 0.804 | 0.782 | 0.948 | 22.1 | **4** | 5 | 5 | **no** — VLM scored garment 4/5 on an output that transferred no garment |
| ts2_12 | 0.736 | 0.896 | 0.785 | **6.7** | 4 | **1** | 2 | **yes** — both judges flagged it |

**Three of the four human-identified failures were missed by the automated
judges**, and ts2_09 scored better than average. Only ts2_12, the most
catastrophic, was caught — by a collapsed `bg_psnr` (6.7 dB) and a VLM scene
score of 1.

This is the empirical basis for the decision in section 4 that **human review is
the primary judge** for this workstream. It also shows the specific blind spot:
`garment_sim` is an embedding cosine that rewards a plausible garment, so a
non-transfer that leaves the original clothing in place still scores 0.78, and
the VLM rewarded it 4/5. Neither instrument answers "is this the reference
garment", which is why the predicted-warp metric is parked as a direction rather
than deleted.

### Inference drawn from the observation

*This is interpretation, not observation.* The distribution supports the premise
in section 2: **a garment reference containing a person causes an attention
deficit.** The model is handed two people and must decide which identity to
keep, which background to keep, and which clothing is the subject — and on
ts2_12 it visibly failed all three at once.

The failures are also not uniformly "worse output". They are three distinct
symptoms — artefacts, no transfer, and identity/scene confusion — mapping onto
F1, F2 and F3. One competing person in a reference can produce any of the three.

**This is what the cropper is for**: remove the reference person's face and
background before the model sees them, rather than arguing the model out of it in
the prompt. These four pairs are the ones to check first in any v2.2.1 result.

## 2c. Phase 3 — reference conditioning (next)

Phase 2 established that cropping works and left **25% of baseline failures
unsolved by the best arm**. Phase 3 attacks that residual. It does not add a new
idea; it fixes three defects in how the crop is *presented* to the model, all of
which were named by the phase 2 reviewer rather than inferred.

Three components, run in this order because each one changes the conditions the
next is tested under:

| | Component | Arms | Attacks | Gate before klein |
|---|---|---|---|---|
| **M** | **Mannequin** — replace the wearer's visible skin with a neutral form | M1–M2 | mechanism 3 (body attributes leak) and mechanism 1 (C4's holes) | Ray eyeballs the crops |
| **BG** | **Ground selection** — white or a neutral alternative, chosen per reference by a detector | BG1–BG4 | mechanism 2 (pale garment on white ground) | Ray verifies the *detector's judgement*, not the outputs |
| **AC** | **Auto-complete** — put back garment area the head cut destroyed | AC0–AC8 | mechanism 1 (the gap read as white cloth) | Ray verifies it works; **no klein test until then** |

Order of execution is **M → BG → AC**: M changes how much work BG has to do, and
AC's learned arms are the only ones carrying a cost, so they run last.

### Why these three and not something else

The three phase-2 mechanisms are one problem seen from three sides: **the boundary
between garment and not-garment is what the model actually reads.** M replaces
what sits on the far side of that boundary, AC repairs the boundary where the
cropper broke it, BG makes the boundary visible when the colours collide. Nothing
here changes the model, the prompt, or the seed — phase 3 keeps phase 2's
single-variable discipline, and the variable is still the garment reference.

### M — mannequin (M1–M2)

**What is being tested.** Whether replacing the wearer with a neutral form beats
both keeping them (C2/C3, which leak body attributes) and deleting them (C4, which
leaves holes). The mannequin region is exactly `subject − clothes`, a mask
`process()` already computes, so both arms are pure mask arithmetic at zero cost.

| | Design | Rationale |
|---|---|---|
| **M1** | Flat mid-grey fill over `body` | The floor. Kills skin tone, tattoos, face — but flat fill has **no shading**, so an arm stops reading as a cylinder and drape becomes illegible. Bounds how much the *colour* alone buys, separately from the form |
| **M2** | **Shaded grey** — LAB, a/b zeroed, L compressed into [116, 196] | Keeps the shading that conveys 3D form; destroys hue and identity. Achromatic by construction, so no skin tone can survive. **Expected winner** |

**The design tension, stated because it sets the parameters.** Two failure risks
pull in opposite directions:

1. **The mannequin gets read as clothing.** Mitigated by keeping it smooth and
   matte — no texture, no fabric-like folds, no high-frequency detail. The
   mannequin should be the least cloth-like object in the frame. Wants **high**
   contrast against the garment.
2. **The mannequin attracts attention itself.** Mitigated by keeping it
   low-information — no face, no texture, smooth gradients only. Wants **low**
   contrast.

These cannot both be maximised, and the resolution is that they are contrasts
against *different things*: the mannequin should sit **close to the ground** so the
silhouette is quiet, while staying **separable from the garment** so it is not read
as cloth. A light grey body on a white ground satisfies both — and fails precisely
when the garment is also pale, which is component BG.

That interaction is why **M is sequenced before BG**: the mannequin partly solves
the pale-garment problem for free, since a white shirt on a grey body has a visible
boundary even when the ground behind it is white. How much ground work remains
cannot be known until M has run.

**Cut from an earlier draft, recorded so the decisions are not silently reversed:**
a blur tier (M2 + Gaussian), a face-smear-only arm, and a featureless grey head
form. All three were built and work; they are held back to keep the arm count
honest. Head-versus-no-head in particular is **deferred to a later phase and
decided on images**, not argued here.

### BG — ground selection (BG1–BG4)

**What is being tested.** Not "is grey better than white" in general — **is the
detector right about which reference needs which**. The ground stays white by
default and changes only when the garment cannot be separated from it. The
deliverable is the *decision rule*, and it is reviewed on its judgements before any
generation is bought.

| | Ground | Rationale |
|---|---|---|
| **BG1** | `#FFFFFF` | Control — what ships today |
| **BG2** | flat `#F1F1F1` | The documented shop-imagery **model-shot** spec. Our cropped duo references are model shots being flattened to the *packshot* spec |
| **BG3** | **Adaptive** — a neutral ramp value chosen per reference to clear ≥15 ΔL\* against the garment's border luminance | A brown garment keeps white; a white garment gets grey. Achromatic throughout, so the ground can never tint the garment and has no periodic structure to be read as weave |
| **BG4** | BG3 + radial falloff + contact shadow | Real packshot white is *photographed*: ~95% albedo, a contact shadow, a luminance falloff. Flat synthetic `#FFFFFF` is the degenerate case of it, and the falloff is exactly the separability cue that flatness deletes |
| **BG5** | **`#FFFFFF` + contact shadow, nothing else** | Isolates the shadow from the colour change. BG4 moves the ground colour *and* adds falloff *and* adds a shadow, so if it wins we cannot say which part did the work. Here the ground stays white — packshot convention untouched, no possibility of tinting the garment — but the garment sits **on** something instead of floating. The cue is created **locally at the silhouette**, which is where the model looks for the garment, and it works at any garment colour including white-on-white, with no global distribution shift |

**What the evidence does and does not support.** Background research found **no
study of reference-background colour for image-conditioned editing** — the white
convention is inherited from e-commerce, not measured, and IDM-VTON's README says
"white-out the background" without justification. "Low attention" is therefore a
*principle* here, not a finding: least information for the model to attend to means
no texture, no hue, no periodic structure, smooth gradients only. What the research
does supply concretely is the ramp values, the packshot-versus-model-shot
distinction, and the finding that flat `#FFFFFF` is out of distribution.

**The checkerboard is dropped.** Models have demonstrably learned checkerboard ⇄
transparency, but as something to **draw** — it is the canonical failure of
"transparent background" requests, where the grid is painted into RGB pixels. That
puts it in the model's output vocabulary as a high-prior renderable texture, which
is a leakage risk rather than an erasure instruction. Recorded consequence: the
reviewer's original suggestion is now answered by argument rather than by data.

**BG needs its own reference list**, selected by measurement across all 48
references. Measured on the hair-damage cohort BG3 selects white on all eleven —
correctly, since those are damaged references, not pale ones.

**The detector was rebuilt after failing its own test case (2026-08-17).** The first
version measured **median luminance in a band inside the garment boundary**. On the
one reference with a documented white-garment failure — `p014`, a white t-shirt over
dark trousers — that reads median L\* 57 and 10th percentile L\* 8, ranking it 13th
of 48 and firing at no plausible threshold. But **22% of that garment is
near-white**. The metric asked *"is the garment pale?"* when the failure is *"is
**part** of it pale?"* — one white region camouflages against a white ground no
matter what the rest of the outfit does, and any central statistic averages it away.

The measure is therefore an **area share**: the fraction of garment pixels within
ΔL\* of the ground, firing at **15%**. Under it `p014` fires at 22.0%, alongside the
flat tee (99.6%), the zendaya white blazer (63.8%) and p004 (57.6%). The 15% bar is
still a choice rather than a measurement, and the review page ranks all 48 by pale
share so it can be moved on evidence.

**The ramp collapses to binary in practice, which is a simplification worth taking.**
Every reference that fires selects the ramp *floor* (`#C8C8C8`); `#F1F1F1` and
`#D9D9D9` never clear the bar, because a garment pale enough to collide with white
is also pale enough to collide with a light grey. So "adaptive across a ramp" is
really "white, or one alternative ground". Recorded rather than acted on — if the
review confirms it, BG3 loses a parameter.

### AC — auto-complete (AC0–AC8)

**What is being tested.** Whether garment area destroyed by the head cut can be put
back well enough that the model stops reading the gap as white cloth — and, since
the methods span zero-cost arithmetic to a full diffusion model, **how far the free
options get before a model is needed at all.**

**The defect shape decides how to read the results.** Measured, the damage is
almost entirely **open** — connected to the background — rather than enclosed:
19.52 of p021's 19.53 points, and all of p009's and p028's. That is not the problem
inpainting is built for. An enclosed hole is ringed by known fabric and the fill is
well-posed; an open notch has garment on one side and background on the other, so
filling it means **extending the silhouette** with nothing constraining where the
garment should end. Two consequences, both recorded before the run so the result is
not rationalised afterwards:

- **Algebra is shape-agnostic.** Un-compositing is per-pixel — wherever hair was
  semi-transparent it recovers the garment underneath, enclosed or not.
- **The learned arms are being tested outside their design envelope.** If they
  underperform, that is evidence about the defect shape, not about inpainting.

| | Arm | Weights | Licence exposure |
|---|---|---|---|
| **AC0** | Unrepaired — control | — | none |
| **AC1** | **Algebra** — un-composite `B = (I − αF)/(1 − α)`, α from the hair probability | none | none |
| **AC2** | `cv2.inpaint` — Telea / Navier-Stokes | none | none |
| **AC3** | OpenCV `xphoto` **FSR** — Fourier-sparse block reconstruction | none | none |
| **AC4** | **Patch search** — OpenCV `xphoto` SHIFTMAP, patch-transform search | none | none |
| **AC5** | **MI-GAN** — mobile GAN, ICCV 2023 | small, ONNX | MIT code, **Places2 weights** |
| **AC6** | **LaMa** — FFC CNN, the standard hole-filler | ~51M | Apache-2.0 code, **Places2 weights** |
| **AC7.n** | **Generative repair** — *"complete the missing section, continue the existing pattern"*. `.1` klein, `.2` Qwen-Image-Edit **inpaint**, `.3` Z-Image Turbo **inpaint** | already shipped / Apache | none |
| **AC8.n** | **Generative crop** — raw image in, *"return just the clothes"*. `.1` klein, `.2` Qwen-Image-Edit-2511 | as above | none |
| **AC9** | **SeedVR2** post-pass over a crude fill | already selected | Apache-2.0 |

**AC8.n is a different kind of arm and is included deliberately.** Every other arm
repairs the deterministic cropper's output. AC8 **replaces the cropper**: raw image
in, garment out, one call. It is therefore the control that tells us whether the
whole deterministic stack — BiRefNet matte, MediaPipe class labels, subtractive
composition, M, BG and AC itself — earns its complexity. If a single prompted call
matches it, most of phase 3 stops being necessary, and that is worth knowing before
more is built on top of it.

The counterweight, stated so the comparison is read correctly: **a model can
hallucinate the garment.** It can shift a colour, alter a pattern, invent a collar
or a hem. The deterministic cropper physically cannot — it only ever removes
pixels, so whatever survives is real. That is the actual trade, and it is
measurable rather than arguable: score the returned garment against the original
garment region, not only against how clean the cutout looks. A beautiful crop of
the wrong garment is the failure mode to watch for, and it is exactly the failure
mode that `garment_sim` was already shown to miss in section 2b.

**Text is the one thing the pixels cannot supply.** AC7.n and AC8.n are the least
likely arms to win on small-gap filling, where copying beats generating, but a
prompt can assert something no neighbourhood statistic contains — "this is a
striped shirt, continue the stripes". Cheap to find out.

**Two prompt-guided options were ruled out.** SeedVR2 accepts **no text input** at
all (endpoint schema: `image_url`, `upscale_mode`, `upscale_factor`,
`target_resolution`, `seed`, `noise_scale`, `output_format`, `sync_mode`), so AC9
is image-only by necessity, not choice. **SUPIR** — the obvious text-guided
restoration model — is disqualified: its code is open-source but the licence states
explicitly that it "does not grant any rights to the weights, biases, or
architecture", which remain proprietary and non-commercial. Widely described as
open-source; not open weights.

**Why the ladder is ordered this way.** AC1–AC4 carry **no licence exposure at
all**, because there are no weights to license. The Places2 question — clean
Apache/MIT code, checkpoints trained on data whose terms say non-commercial —
attaches only to AC5 and AC6. If the free arms match them, the question never has
to be answered. Copy-based fill is also expected to *beat* the learned arms on
patterned fabric, since it copies a plaid where a 512-trained CNN approximates one.

**Two implementation constraints that shape AC7 and AC8.**

- **Neither takes a mask.** Flux.2 Klein's pipeline is txt2img/img2img only, with
  no mask input (diffusers #13005 is an open feature request), and SeedVR2 is a
  whole-image restoration pass. Both therefore run as *generate-then-composite*:
  the original pixels are hard-composited back outside the hole. This is mandatory,
  not optional — any latent round-trip degrades fine pattern **outside** the hole
  through the VAE, so without the composite the repair damages what it was not
  asked to touch.
- **AC8 is not an inpainter and is not being used as one.** SeedVR2 was v2.1's
  auxiliary leader (`seedvr2_x2_noise0`, Apache-2.0, one step) and it restores; it
  cannot invent garment where there is white. It is tested as a **second pass over
  a crude fill** — AC2 output refined — to see whether cheap-fill-plus-restore
  reaches the quality of an expensive fill. If it does, the pipeline gains nothing
  new: both components already ship.

**Why an imperfect fill is acceptable.** No ablation exists — VTON papers
concatenate a VAE-encoded garment latent and none study reference quality. The
argument is structural: a hole is **out of distribution** (no training garment
reference has one) while imperfect fabric is **in distribution**. The model needs to
understand *which garment this is*, not receive exact pixels. Explicit instruction
not to over-engineer the fill.

**What was ruled out, and why it is not revisited.** The fashion-specific models
that reconstruct an occluded garment by design — the virtual try-off family — are
commercially locked: TryOffDiff is **SSPL**, TryOffAnyone and CatVTON are **CC
BY-NC-SA 4.0**, and the Apache-licensed amodal-completion work depends on a
LISA-13B + SD2 + Grounded-SAM stack that is neither light nor licence-clean. This
is the norm in the space rather than bad luck. Generic infill loses little here:
continuing an existing pattern needs the neighbourhood's statistics, not garment
semantics.

#### The hair fringe, and the deliberate over-crop (2026-08-17)

**Observed by the reviewer, then measured.** The head cut leaves a residual hair
fringe *inside* the kept garment. It is present on every reference in the cohort and
it is **darker than the garment in every case**:

| ref | fringe, % of kept garment | fringe L\* | garment L\* |
|---|---|---|---|
| p016 | 4.69% | — | — |
| p021 | 2.66% | **24.9** | 46.0 |
| `woman_top_denim_skirt` | 1.92% | **13.2** | 25.8 |
| p028 | 1.52% | — | — |
| zendaya white blazer | 0.76% | **48.8** | 92.3 |
| p012 | 0.08% | 35.7 | 17.1 |

A dark rim tracing the cut line, on a white ground, is a strong local edge — the
same class of signal klein was already shown to read as garment in phase 2.

**The reviewer's hypothesis was that the fringe defeats the algebra. It does not,
quite.** 100% of fringe pixels fall inside the α ∈ (0.02, 0.90) window AC1 operates
on, so they are not being skipped. AC1 **undercorrects** them: un-compositing uses a
single *global* hair colour estimated from the opaque core, and where dark hair
meets dark fabric the correction is too small to erase the rim. Over-cropping is
therefore not a fix for something the algebra missed — it removes a problem the
algebra can only partly solve. Same conclusion, different mechanism, recorded
because the mechanism decides whether a better α estimate would also work.

**The trade being made.** Cut wider on purpose, then fill the gap back. This swaps
an **unknown contamination** for a **known, fillable gap** — and it is only a good
trade if AC works, which is precisely what the AC arms measure. It also composes
with the earlier finding that the damage is an *open boundary notch*: over-cropping
makes the notch bigger but cleaner, which is the shape a fill handles best.

**Definition problem, surfaced by the first run.** "Over-crop by 5%" was implemented
as *dilate the head mask until the extra garment removed equals 5% of garment area*,
with the radius solved per reference (a fixed radius means very different amounts on
a 500px and a 1500px image). The solved radii are **inversely related to the defect**:

| ref | fringe | solved radius |
|---|---|---|
| p016 | **4.69%** | **5px** |
| p021 | 2.66% | 7px |
| p030 | 0.78% | 9px |
| p012 | 0.08% | 40px |
| p023 | **0.29%** | **60px** |

p023 has the second-smallest fringe and receives the largest dilation; p016 has the
largest fringe and receives the smallest. An area target is driven by head-mask
perimeter, not by contamination, so it over-treats short-haired references and
under-treats the ones that actually need it. **This is recorded as a defect in the
definition, not in the result.** The alternative is a **fringe-targeted** dilation —
grow just past the measured contamination band — which would land near-constant at
roughly 10–15px and scale with the defect rather than against it. Both are on the
preview page; the choice is the reviewer's.

Preview: `v2/artifacts/v221_phase3_crops.html`. **The AC arms are not re-run until
this passes**, since the over-crop changes their input.

### PRE — repair before cropping (2026-08-17)

**A different architecture, not another AC arm.** Added after the reviewer asked
whether the hair could be dealt with *before* any calculation rather than patched
afterwards.

| | order of operations |
|---|---|
| **AC** | crop → damage exists → fill the damage |
| **PRE** | repair the **raw photo** → crop normally → **damage never exists** |

**Why PRE should win — stated before the run, so it is a prediction rather than a
rationalisation afterwards.** AC asks a model to fill a **white hole inside a crop**:
out of distribution (no training garment reference has a hole), no surrounding
context, and "white region adjacent to garment" is the exact failure this workstream
was created to fix. PRE asks for an edit on **a whole photograph of a person** —
in distribution, routine for these models — and leaves the entire body available as
context for what the garment under the hair looks like. The head cut afterwards then
has nothing to take, so the fringe is never created rather than being removed.

It also composes with the fringe finding above: over-cropping removes contamination
by taking *more* garment, whereas PRE removes the contamination's cause and takes
*less*.

| | Arm | Mechanism |
|---|---|---|
| **PRE0** | control — the current pipeline | |
| **PRE1** | **LaMa** fills the hair region in the raw frame, no prompt | Deterministic-ish; the whole body is context, unlike AC6 which fills a hole in a crop. Same weights, different position in the pipeline — so PRE1 vs AC6 isolates *where* the repair happens from *what* does it |
| **PRE2** | **klein**, prompted *"make this person completely bald"* | |
| **PRE3** | **Qwen-Image-Edit-2511**, same prompt | |

**All three then run the cropper unchanged**, so the only variable is the raw image
it receives. The measurement is direct and needs no judgement call: **how much
garment does the head cut take, and how much fringe survives**, before versus after.

**Why "make this person bald" and not "return just the clothes".** The prompt asks
for a *small, in-distribution* edit. Hair removal on a portrait is something these
models do routinely; a floating garment on white is an output shape they rarely
produce. The prompt also pins everything else explicitly — pose, body, background,
clothing unchanged — because the only thing being asked for is what lies *under* the
hair. AC8 keeps the original "return just the clothes" prompt so the two framings can
be compared rather than one silently replacing the other.

**Cost note.** PRE is slower than it looks: every repaired frame is a new image, so
BiRefNet must re-matte it (~200s each on CPU, versus a cache hit for the originals).
That is a measurement cost only — in production a garment reference is processed
once and cached per catalog image.

#### OCF — the fringe-targeted alternative to OC5

Added because OC5's area target proved inversely related to the defect (table above).
OCF dilates just past the **measured** contamination band — the 95th percentile of
the fringe's distance transform, plus a small margin — so the cut scales *with* the
defect instead of against it, and lands near-constant rather than swinging between
5px and 60px. Both are on the preview page; OC5 is retained rather than deleted so
the comparison is visible rather than asserted.

#### AC's justification and test set

The reviewer identified a hair-damage cohort by eye during phase 2 — **p009, p016,
p021, p028**. Measuring `C3.2 − C3.1` confirms all four and finds seven more at
comparable levels; the table is in [RESULTS.md](RESULTS.md), "Hair-removal damage".
**p021 loses 19.53% of the garment, `woman_top_denim_skirt` 16.97%.** Those eleven
references are AC's test set, with p021 (worst, and the only one whose silhouette
actually gets *rougher*) and `woman_top_denim_skirt` (garment source of the one set
no arm solved) as must-pass.

**The synthetic punched bed was built and then cut (2026-08-17).** It punched known
holes into intact fabric so the true pixels would be available to compare against —
attractive, because on real hair damage nobody knows what was underneath, so the
reviewer can only judge plausibility.

It was dropped because **it tests a defect we do not have.** A punched hole is
*enclosed* by fabric; our measured damage is an **open boundary notch** — 19.52 of
p021's 19.53 points. Scoring fills against a hole shape that never occurs in this
pipeline would reward the wrong behaviour, and having ground truth is not worth
having if it is truth about the wrong question. The generator is retained unused, in
case a genuine enclosed-hole case appears — C4's hand-overlap holes are the likely
candidate.

Consequence, accepted rather than worked around: **fill quality on the real cohort is
judged on plausibility, not correctness.** That is a real limit on what the AC
comparison can conclude, and it falls hardest on the learned arms, where a
convincing-but-wrong fill is the failure mode. It is a reason to prefer PRE, which
does not have to invent anything the photograph did not contain.

### FASHN cross-check (2026-08-18)

**This reopens a settled decision, deliberately and on request.** The scope note at
the top of [PLAN.md](PLAN.md) says v2.2 does not revisit the model choice, which was
made in [V2.1_RESULTS.md](../results_summary/V2.1_RESULTS.md). This arm revisits it
anyway, because the question it answers is cheap and phase 3 cannot answer it:
**is the cropper solving a problem that a purpose-built try-on model does not have?**

**Why FASHN cannot be a phase-3 arm.** It is a try-on model — person plus garment in,
dressed person out. It cannot produce a crop, a mannequin, a ground or a repair. fal
hosts only `tryon/v1.5` and `tryon/v1.6`; **there is no try-off endpoint**, so FASHN
also cannot serve as an AC8-style garment extractor. It can only replace klein at the
transfer step.

**Why it is nonetheless the sharpest available cross-check.** FASHN takes
`garment_photo_type` (flat-lay versus on-model) and `segmentation_free`, which means
it performs **its own garment segmentation internally**. A dedicated VTO model
expects a garment reference that may still be worn by someone — precisely the
condition that causes klein's attention deficit and that the whole cropper exists to
remove. So the comparison asks whether our preprocessing helps FASHN, is redundant
for it, or actively hurts.

| arm | garment reference given to FASHN | `garment_photo_type` |
|---|---|---|
| `FA_base` | the raw on-model photograph | `model` |
| `FA_c31` | our C3.1 crop | `flat-lay` |
| `FA_pre3` | the Qwen bald frame (where one exists) | `model` |

Run over **the 20 pairs whose klein baseline failed** — the same set that produced
the 75% / 45% arm split — so the numbers are directly comparable rather than
approximately so. Person image, seed (46) and mode (`quality`) are held fixed; the
only variable is the garment reference, matching phase 2's discipline.

**v1.5 is pinned.** fal's v1.6 is FASHN's **closed commercial model** and is
therefore outside the open-weights deploy path. The endpoint string must not be
bumped, and the runner carries that warning inline.

**Three outcomes and what each would mean**, written before the results so the
reading is not fitted afterwards:

| if | then |
|---|---|
| `FA_base` ≈ `FA_c31` | FASHN's internal segmentation already handles worn references, and cropping is **redundant for it**. That is an argument about FASHN, not against the cropper, since klein demonstrably needs the help |
| `FA_c31` > `FA_base` | the attention deficit is **not klein-specific**, and cropping is a general-purpose preprocessing win worth keeping whichever model ships |
| `FA_base` > `FA_c31` | our crops are **destroying information a VTO model uses** — drape, fit, how the garment hangs — which would be the strongest evidence yet for the mannequin (M) over pure subtraction |

**This arm does not by itself reopen the base-model choice.** FASHN is a
single-purpose try-on model; klein was chosen for editing breadth as well as
transfer quality, and one comparison on 20 adversarially-selected failure pairs
cannot overturn that. Treat it as a diagnostic on the *cropper*, not a leaderboard.

### AC phase 2 — AC-A extraction and AC-B bald+crop (2026-08-18)

**Both descend from the AC section and are not new ideas.** AC-A is AC8 (generative
crop) promoted from a one-shot probe to a pipeline; AC-B is PRE (repair before
cropping) with its blocking defect fixed. They are the two candidate ways of
producing a garment reference, and they will be judged against each other.

#### The defect that had to be fixed first, and the measurement it invalidated

The head mask is `HAIR + FACE`. On a **bald** frame no HAIR class fires, and
MediaPipe's FACE class covers the face rather than the skull — so **the cranium
survived the cut.** Measured across the cohort, head removal fell from **17.6% of
the subject on the original to 8.6% on the bald version**: roughly half the head
stayed in the crop. The reviewer saw this by eye before it was measured.

**This also invalidated the first PRE result.** "Garment lost" was computed as
`C3.2 − C3.1` — face-only-removed minus hair-and-face-removed. On a bald frame those
two masks are nearly identical, because there is no hair to separate them, so the
difference collapses to ~0 **by construction**. The reported 19.5% → 0.02% was not
measuring garment preservation; **every bald frame scores ~0 regardless of quality.**
This is a worse failure than the tautology anticipated in the PRE section: it was not
that a destructive edit would also score well, it is that the metric measured nothing
at all. The numbers are withdrawn. The visual evidence — the reviewer preferring
klein's bald frames — stands, and is now the only evidence.

Recorded as the second instance in this workstream of a metric rewarding a
degenerate case, after the no-op discovery in phase 2. Both were caught by eye.

**The fix.** A cranium region anchored to the **detected face** rather than to
silhouette geometry: everything in the subject above the face's lower edge, within
the face's x-range widened by a margin, unioned with the class mask. A first attempt
used the narrowest silhouette cross-section as a neck and was unreliable — it found
no neck at all on p021 and p019. The face-anchored version over-reached and cost
p028 10 points of clothes area and p030 17, so the skull region is now **intersected
with the complement of the clothes class**: a cranium is never clothing, which makes
garment loss impossible by construction rather than by threshold tuning. Residual
loss is now 1 reference of 11 (p030, ~5 points).

#### The two arms

| | AC-A extraction | AC-B bald → crop |
|---|---|---|
| what is regenerated | **the whole garment** | **only the hair** |
| garment pixels | synthesised | real, from the photograph |
| hallucination risk | **high** — nothing constrains it to the true garment | **low** — the crop can only remove, never invent |
| ceiling | potentially perfect | bounded by the segmenter |
| models | Qwen-Image-Edit-**2511** (Apache), Qwen-Image-Edit-**Plus**, klein 4B distilled, klein 4B base; three prompt variants on 2511 so model and prompt stay separable | klein-bald and Qwen-bald, both through the cranium-fixed cropper |

**On Qwen versions.** fal hosts `qwen-image-edit`, `-2509`, `-2511` and `-plus`;
there is no "3". **2511 is the newest numbered release**, explicitly the successor to
2509, and its stated gains — reduced identity drift, improved character consistency,
stronger geometric reasoning — are all directly relevant here. **"Plus" could not be
resolved by naming**: it was the community nickname for 2509, yet one source dates it
to early 2026. The fal schemas differ materially (50 inference steps and guidance 4,
versus 28 and 4.5), so they are genuinely different models rather than aliases, and
the question is settled empirically by running both on the same prompts and seed
rather than by trusting a version string. One implementation trap: `-plus` defaults
`image_size` to `square_hd`, which would squash a portrait reference and confound the
comparison — aspect is passed explicitly.

**They need different verdicts.** AC-B is judged on *is the crop clean, and is the
whole head gone.* AC-A is judged on ***is this the same garment*** — compared against
the control at zoom, on pattern and colour. Section 2b already established that
`garment_sim` and the VLM both reward a plausible garment over the correct one, so
neither instrument can catch an extraction that invented a collar.

#### Extraction drift — a triage signal, and what it says (2026-08-18)

AC-A's whole risk is that it regenerates the garment, and section 2b established
that neither instrument we have can catch a plausible-but-wrong result. So rather
than another embedding metric, `v2/build/extraction_drift.py` compares
**deliberately dumb statistics** of the garment pixels against the control crop:
median lightness and chroma shift in LAB, circular hue shift, and an edge-density
ratio as a pattern proxy. Gross recolouring and smoothed-away texture show up. A
changed collar or a moved seam does **not**, and cannot — that is what the reviewer's
eye is for. It ranks which references deserve the hardest look; it does not decide.

**A scale confound had to be fixed first.** Edge density rises with resolution, and
the control crops are ~376×897 while the extractions return at 672×1024 or larger,
so the first run was partly measuring image size. Both images are now rescaled to
the same garment height before any edge measurement. Colour statistics are scale-free
and were never affected. Corrected results:

| arm | mean abs ΔL | mean abs ΔC | mean Δhue | edge ratio | flagged |
|---|---|---|---|---|---|
| **klein base** | 21.8 | 8.5 | 21.3° | **1.01** | 9/11 |
| klein distilled | 27.3 | 5.9 | 26.7° | 0.80 | 10/11 |
| Qwen 2511 p2 | **10.7** | 6.8 | 29.7° | 0.61 | 9/11 |
| Qwen 2511 p1 | 11.7 | 5.8 | 28.6° | 0.51 | 9/11 |
| Qwen 2511 p3 (ghost) | 48.5 | 6.9 | 24.1° | 0.57 | 11/11 |
| Qwen Plus p1 | 23.0 | 20.7 | 30.0° | 0.44 | 3/4 |
| Qwen Plus p3 | 99.0 | 13.1 | 67.6° | 0.20 | 3/3 |

**Every arm drifts on almost every reference.** Three readings, all provisional
until the reviewer looks:

1. **Pattern loss is the dominant failure, not colour.** Every Qwen arm returns
   roughly half the edge detail of the control. **klein base is the only arm that
   preserves it** (ratio 1.01), and klein distilled is second. Whatever these models
   are doing, the Qwen family is smoothing fabric texture away.
2. **This directly contradicts the eye, and that is the point.** The reviewer
   preferred the Qwen crops on the earlier page. Qwen also has the *lowest* lightness
   drift, so its outputs look clean and correct — while losing half the pattern.
   "Cleanest-looking" and "most faithful" are pulling apart here, which is exactly
   the failure mode AC-A was flagged for before it ran.
3. **The ghost-mannequin prompt (p3) is the worst on both models.** ΔL of 48 on 2511
   and 99 on Plus: it is being read as *make it pale and simple*, not as *keep the
   drape*. The in-distribution argument for p3 does not survive contact.

**Hue drift of 21–30° is present on every arm including the klein ones**, which is
large enough to change a garment's apparent colour. No extraction arm currently
returns the same garment.

**Provisional consequence:** on this evidence AC-A is not ready to ship as a
reference pipeline, and AC-B — which regenerates only hair and keeps real garment
pixels — is the safer candidate by construction. Held as provisional rather than
concluded, because the drift check is triage and the reviewer has not yet looked.

#### Decisions out of the AC-A review (2026-08-18)

**Qwen-Image-Edit-Plus is dropped.** It is the worst arm on every axis measured:
mean lightness drift 23–99 versus 2511's 10.7, chroma drift 20.7 against 5.8, hue
drift up to 67.6°, and an edge ratio of 0.20 on the ghost prompt — four fifths of the
fabric detail gone. The run also stopped early when the fal balance was exhausted, so
it is incomplete (4 of 11 and 3 of 11), but nothing in the partial data suggests the
remaining references would rescue it. **2511 is the Qwen to use**, which is also the
newest numbered release. Not worth completing the run.

**The ghost-mannequin prompt (p3) moves out of AC and into the mannequin
subsection.** It is the wrong tool for extraction — ΔL of 48 on 2511 and 99 on Plus,
because "ghost mannequin" is being read as *make it pale and simple* rather than
*keep the drape*. But that is a statement about extraction, not about the idea: a
prompt that asks a model to supply a neutral body is a **mannequin** experiment, and
belongs with direction 12 where the same question is asked deterministically. Moved
rather than deleted, and it should be tested there against M1/M2 — if a model can
supply the mannequin, the deterministic one may never need building.

**Arms selected for the klein run: `QX_qwen_p1` (Qwen 2511, subtractive prompt) and
`BC_klein` (klein-bald → cranium-fixed crop).** One from each family, chosen by the
reviewer's eye. Note the tension recorded above: Qwen p1 is preferred visually while
returning about half the control's edge detail, so the klein run is partly a test of
whether that lost pattern actually matters downstream — the reference only has to
convey the garment, not reproduce it.

#### Head detection rebuilt — from heuristic to human parser (2026-08-18)

**Raised by the reviewer twice, and both challenges were right.** First that the
bald crop was leaving the head; then, when the fixes kept failing, that *"nothing
can crop a bald person"* did not sound right. It was not right. Four geometric
patches were spent on a region-shaping problem before asking whether a better
**signal** existed.

**The root error: the head was identified by appearance rather than by anatomy.**
The mask was `HAIR + FACE`, both from MediaPipe Selfie Multiclass — a lightweight
*selfie segmenter*, not a human parser, and never built to find a head. On a bald
frame no HAIR class fires and FACE covers the face rather than the skull, so **the
head signal disappeared along with the hair signal** and half the skull survived the
cut (head removal 17.6% of the subject → 8.6%).

**A wrong diagnosis on the way, recorded so it is not repeated.** p030 was blamed on
a mis-detected face — the FACE class sat at 52–73% of the frame while the silhouette
began at 20%, which looked conclusive. Pose landmarks then put the nose at y=663 and
the ears at y=650, **agreeing with the FACE class**. The detector was right. The real
cause was the *rule*: "cut everything above the chin" swept in a blob covering 36% of
the subject and 60% clothes-class — raised arms. A rule with no upper or lateral
bound breaks on any pose with something above the head.

**The general solution: separate anatomy from appearance.**

| | source | fires |
|---|---|---|
| **Skull** | pose landmarks — ellipse from ear separation | **always**, hair-independent |
| **Hair beyond the skull** | HAIR class | only when there is hair |

One rule covers every case: **bald** → ellipse alone; **short hair** → ellipse alone,
since short hair lies inside the skull; **long hair** → ellipse plus the HAIR class
for what spills onto the garment.

Three constraints, each measured rather than tuned:

1. **Sized from ear separation** — the skull width at ear level, with an
   ear→shoulder fallback for profile views where the ears collapse together.
2. **Clipped at the neck** — between the ear and shoulder landmarks, both detected.
   Without it the ellipse reached the chest (p019 −4.0 points, p028 −1.0).
3. **The clothes class is protected** — a head is never clothing, so a high collar
   or hood inside the ellipse survives. That is the correct outcome, and it took
   p019 from −3.3 to −0.1.

| | before | after |
|---|---|---|
| references losing garment area | 2 of 11 | **0 of 11** |
| p030 (the reference the reviewer named) | −3.4 pts | **−0.1 pts** |
| extra head removed, mean | — | **+0.8 pts** |

Pose fired on **22 of 22** crops; the old face-anchored band remains as a fallback
and was not needed. MediaPipe Pose Landmarker lite, **Apache-2.0, 5.8MB** — clean for
the deploy path.

**What this does not prove.** The numbers show no garment lost and more head removed.
They cannot show that the **whole skull is gone**, which is a visual check on the top
of each AC-B crop and remains the gate before klein.

#### The pose ellipse was also not enough — a human parser replaces it

The pose ellipse fixed the *anatomy* half but not the *boundary* half, and the
reviewer caught the residue: **p016 and p019 were still leaving the top of the
scalp.** Attempts to close that traded references against each other —

| change | effect |
|---|---|
| size from ear separation | p016 got a 54px-wide ellipse (its ear landmarks were **9px apart**); scalp missed |
| size from the silhouette instead | p016 and p019 fixed, but p028 lost 8.6 points of garment |
| cap the silhouette estimate by neck length | p028 −3.2, p030 −1.7 |
| clothes guard over the whole ellipse | 0 references lost garment, but on p019 **19.5% of the head region was classified as clothes** and was therefore protected, leaving the crown |

**Seven iterations, each trading one reference for another.** That is the signature
of a heuristic at its ceiling rather than a tuning problem: an ellipse has no notion
of "head" or "collar", so every knob moves both at once.

**The fix was a better model, not a better shape.** MediaPipe Selfie Multiclass —
used by the cropper throughout — is a lightweight *selfie background* segmenter with
six coarse classes at 256×256. It was never built to find a head. **SegFormer-B2
fine-tuned on ATR** gives 18 human-part classes, and is the class of model VTON
pipelines use to build agnostic masks. ATR's `Face` class covers the **head region**
rather than facial skin, which is precisely the property the bald case needs.

| | head removed, mean | worst references |
|---|---|---|
| class map + pose ellipse | +0.8 to +1.2 pts | p016 3.5% → 8.4% |
| **human parser** | **+5.0 pts** | **p016 3.5% → 11.9%, p023 10.6% → 23.4%** |

**All three roles now come from one model.** A first version took head from the
parser and left garment on MediaPipe; the "garment lost" figure then measured the
two models *disagreeing* — the parser calling a region head while the selfie map
called it clothes — and scored that disagreement as damage. Since the parser is the
better model on exactly that question, this was measuring the wrong thing. Head,
garment and skin now all come from ATR, so they are **disjoint by argmax** and head
can never overlap garment by construction.

**Licence: unverified.** `mattmdjaga/segformer_b2_clothes` needs its licence and its
training-data terms checked before this ships — the same Places2-style question that
applies to the AC5/AC6 inpainters. It is fine for measurement now; it is not cleared
for the deploy path.

**Superseded, retained as fallbacks in this order:** pose ellipse, then the
face-anchored band with its two patches. Neither fired on any reference once the
parser was available.

### AC-C — destroy the head instead of removing it (2026-08-18)

**A different idea, not another patch.** Eight iterations went into head *removal*
and every one traded precision in one place for damage in another. The reason is
structural: removal needs an exact boundary, and an error is expensive — a white
notch left where the cut was wrong gets read as garment. That is mechanism 1, the
single most damaging defect measured in this workstream.

But removal was never the goal. The goal is that **the model stops attending to a
competing identity**, and destruction achieves that without an exact boundary:

| | boundary precision needed | cost of an error |
|---|---|---|
| **Removal** | high | a white notch → read as cloth |
| **Destruction** | **low** | a little extra blurred skin → no identity, no garment, still a photograph |

That asymmetry is the whole argument. Over-covering costs almost nothing, so the
region can be generous and approximate — which is what our head detection is
reliably good at, and exactly what it has repeatedly failed to be precise about. It
also keeps the reference **in distribution**: a photograph of a person with a
blurred face is a normal image; a photograph with a hole cut in it is not.

#### Two bases

| | base | operation |
|---|---|---|
| **AC-C/O** | **original photo, hair intact** | destroy the **face** only — no balding step at all |
| **AC-C/B** | bald frame from AC-B | destroy the whole **head region** |

**The /O branch is the stronger candidate and is strictly cheaper**: no generative
call, fully deterministic, no licence question, no hallucination risk, milliseconds
to run. If it works, the entire bald pipeline becomes unnecessary.

It also has a direct measured precedent. **C3.2 was "keep the hair, remove the face"
and scored 45%**, and its recorded failure was *"interpreted the white space as
cloth"* — the hole left by cutting the face out. **AC-C/O is C3.2 with the face
destroyed in place rather than cut out**: the same information removed, no hole
created. It attacks C3.2's actual failure mode by construction rather than by tuning.

#### Arms

| | base | |
|---|---|---|
| D0-O | original | control — C3.1 as it ships |
| D1-O / D2-O / D3-O | original | blur / twirl / pixelate the **face** |
| D0-B | bald | control — the AC-B crop |
| D1-B / D2-B / D3-B | bald | blur / twirl / pixelate the **head region** |
| **D4-B** | bald | **the crop fix** — morphological opening to sever the neck at its constriction, keep the nose component, dilate back |

D4 runs alongside rather than instead, so removal and destruction are compared
directly instead of one displacing the other by assumption.

#### Risks and limits, recorded before the run

1. **A blurred head is still a head.** The model may attend to it as a person
   anyway, or reproduce the blur in the output. This is the arm's central
   assumption and it is untested.
2. **Blur may read as depth of field** (in-distribution, harmless) **or as an
   artefact** (out-of-distribution, harmful). Which of the two decides the arm.
3. **Twirl is definitely out of distribution.** Included because it destroys facial
   *structure* rather than only detail, but it is the likeliest to produce
   artefacts.
4. **The body still leaks in both branches.** The wearer's torso and arms remain, so
   the skin-tone mismatch recorded on `p018+p016` — mechanism 3 — is untouched.
   Destruction addresses identity in the face, not body attributes.
5. **D4 is not expected to succeed everywhere.** Opening only severs the neck if a
   kernel exists between neck width and head width. **p023 is the worst case**: a
   seated profile has a narrow head and a thick neck-to-chest connection, so any
   kernel large enough to cut may also erode the head. Stated in advance so a
   failure there reads as a predicted limit rather than a surprise.

**Relationship to M.** This revives **M4**, the face-smear-only arm built and shelved
to keep the arm count honest. It was shelved as a cheap partial; eight failed removal
iterations are the argument for testing it properly.

#### Recorded: the subject matte includes furniture

Visual inspection of a diagnostic montage (2026-08-18) showed **BiRefNet counting a
stool and a chair as subject** on p023 and p021 — and therefore in **every crop
produced so far**. A garment reference containing furniture is precisely the
attention-stealing distraction this workstream exists to remove, and it has been
present throughout, undetected, because no measurement looked for it.

Found only by rendering the masks and looking at them. This is the **third** instance
in this workstream of a defect that the instruments missed and the eye caught, after
the no-op outputs in phase 2 and the bald-frame metric collapse above. The pattern is
consistent enough to be worth stating as a rule: **every stage of this pipeline has
been debugged by looking, not by measuring.**

#### The klein run that follows

Gated on the reviewer approving both reference sets. Then, on the 20 failure pairs:

**All ten arms go to klein.** Every reference-production idea developed in phase 3
is tested against the same 20 failure pairs, rather than shortlisting on the
screening pages and risking a good arm being cut on a free artifact that does not
predict downstream behaviour.

| arm | garment reference | family |
|---|---|---|
| `control` | C3.1 as it ships today | baseline |
| **`QX_qwen_p1`** | Qwen 2511 extraction, subtractive prompt | AC-A |
| **`BC_klein`** | klein-bald → cranium-fixed crop | AC-B |
| **`BALD_raw`** | the bald frame with **no cropping at all** | AC-B control |
| **`D1hO`** | blur the face, **hair kept** | AC-C/O |
| **`D2O`** | twirl the face, hair kept | AC-C/O |
| **`D3O`** | pixelate the face, hair kept | AC-C/O |
| **`D1hB`** | blur the head, **bald** | AC-C/B |
| **`D2B`** | twirl the head, bald | AC-C/B |
| **`D3B`** | pixelate the head, bald | AC-C/B |

**Blur tier: HEAVY** (3 passes, 2× radius). The light tier was visibly insufficient
and the extreme tier risks reading as an artefact rather than as depth of field;
heavy is the middle, and the tier choice is itself part of what the run tests.

**A prerequisite before any paid call:** the AC-C variants existed only for the 11
damage-cohort *references*, while the klein pairs draw on 20 garment *sources*. The
pipeline is run over the missing sources first — free and local — so that every arm
covers every pair and the comparison is not silently unbalanced.

**This is the point of the phase.** Every arm here modulates what the model attends
to in the garment reference, by four different mechanisms: removing the person
(control, AC-A), removing only the head (AC-B), removing nothing but destroying
identity (AC-C), or removing nothing at all (`BALD_raw`). The question the run
answers is which mechanism klein actually responds to.

The fourth arm is the useful control: if a bald photograph works as well as a bald
photograph that has been cropped, the cropper is not earning its place in this
pipeline and the simplest thing ships.

### Outcome of the Attention Modulation Test

Run complete, ranked, and written up in [RESULTS.md](RESULTS.md). Headline: the crop
earns its place (`BALD_raw` cut 85% of the time), **pixelation is the strongest
destruction mechanism** because it removes attention while preserving context, and
**Qwen extraction is bimodal** — six wins and five bottom-two placements — so it
belongs in the harness as a conditional option rather than a fixed step.

**Opened by this run: pixelation modulation.** Cell size is a continuous dial between
full detail and flat block, so the quantity of attention removed becomes tunable
rather than binary.

**The descent hypothesis is what justifies whatever comes next.** With enough
attention available klein converges to essentially the same result regardless of
which arm produced the reference, so the failure is a **deficit, not an inability** —
and if the deficit is what matters, **the manner of removing it is free to vary**.
That interchangeability is a degree of freedom for **cost**, and it is the premise the
next phase should be designed against: find the cheapest mechanism that removes
enough attention, rather than the most thorough one. Full argument, evidence and the
tier-versus-rank caveat: [RESULTS.md](RESULTS.md), "The descent hypothesis".

**The next phase is not yet chosen.** Recorded here as the justification that will
shape it, not as a plan.

### Disposition of BG and M at the v2.2 checkpoint (2026-08-19)

**Both are dropped from v2.2 and moved to the parking lot.** The Attention
Modulation Test resolved the attention deficit with three arms that rescue each
other, so neither BG nor the mannequin is on the critical path any more.

| | verdict | why |
|---|---|---|
| **BG5** — white + contact shadow | **parked, most promising if revisited** | It restores the separability cue that flat `#FFFFFF` deletes, locally at the silhouette, with no global distribution shift. It was never klein-tested |
| **BG3** — adaptive neutral ground | **parked, likely unnecessary** | Its detector fires on 14 of 48 references, and every firing reference selects the ramp floor — the "adaptive ramp" collapses to a binary choice in practice |
| **M1 / M2** — mannequin | **dropped** | Built only if the AC trials showed failure or needed compensation for reduced attention. They did not: the trigger condition was never met |

The pale-garment problem BG was built for rests on **one observed instance**
(`p018+p014`), and that reference was never in the klein test set. That is not enough
to hold open a component.

### Superseded — the original pause note



**BG and the mannequin are suspended until the AC trials finish.** They address
smaller effects than the reference-production question AC-A and AC-B are settling,
and both would have to be re-run against whichever reference pipeline wins.

- **BG5 — white plus a contact shadow — is the most promising ground on current
  evidence.** It restores the separability cue that flat synthetic `#FFFFFF` deletes,
  does it **locally at the silhouette** where the model looks for the garment, keeps
  the packshot convention, and cannot tint anything. If it holds up, BG3's adaptive
  ramp becomes unnecessary — which would also dissolve the ramp-collapse oddity where
  every firing reference selects the floor value.
- **The mannequin is deferred and conditional.** It is built only if the AC trials
  show failure, or if the winning reference turns out to need compensation for
  reduced attention — the case where stripping the wearer removes so much drape and
  fit context that the model needs a neutral body to hang the garment on.

#### Judging and artifacts

**Everything in phase 3 is judged by eye.** Deterministic metrics are recorded where
they are free but no arm is selected on a number — the phase 2 record in section 2b
is the reason: three of four human-identified failures were missed by the
instruments, and one scored above average.

**One page per component**, because the three ask different questions and mixing
them makes the review harder rather than easier:

| page | question the reviewer is answering |
|---|---|
| `v2/artifacts/v221_phase3_m.html` | Does the mannequin read as a neutral form — not as clothing, and not as something worth attending to? |
| `v2/artifacts/v221_phase3_bg.html` | **Did the detector decide correctly?** Each reference shows the call and the margin that produced it, not only the image |
| `v2/artifacts/v221_phase3_ac.html` | Is the garment whole again, and on the synthetic bed, is it *right* as well as plausible? |

**Mask feathering is orthogonal to the AC arms and is tested separately.** Eroding
and feathering the head mask, and declining to cut thin hair strands, is free and
attacks the open-notch geometry directly rather than filling after the fact — the
measurement says the damage is a boundary defect, so not creating it beats repairing
it. It is a preprocessing switch that composes with every AC arm, so it is reported
as an on/off comparison rather than competing as an arm of its own.

#### The over-crop ledger — what each removal stage costs

Every C3/C4 variant pays, and not the same amount. Share of the C2 subject area
removed at each stage:

| stage | removes | range across 48 refs |
|---|---|---|
| **C2 → C3.2** | face only | 4.6 – 11.6% |
| **C3.2 → C3.1** | hair | 0 – 19.5% |
| **C3.1 → C4** | body skin | 1.5 – 40.2% |

**C3.2 is also over-cropped** — it keeps the hair but still pays 4.6–11.6% for face
removal. No variant is free.

#### Candidate over-cropping failures, and why the attribution mostly does not hold

Every set where the base failed and **C3.2 or C4 was not marked solved** (blank =
not solved), with the ledger for the garment source:

| set | failed arm | source | face% | hair% | skin% |
|---|---|---|---|---|---|
| `man_black_suit + woman_top_denim_skirt` | C3.2 + C4 | woman_top_denim_skirt | 6.71 | **15.83** | **36.41** |
| `p011 + p003` | C3.2 + C4 | p003 | 4.58 | 3.58 | 16.64 |
| `man_black_suit + scarlett` | C3.2 + C4 | scarlett | 7.30 | 9.12 | 26.96 |
| `p015 + p007` | C3.2 | p007 | 8.77 | 4.15 | 18.07 |
| `p015 + p002` | C3.2 | p002 | 7.52 | 1.78 | 12.23 |
| `beige_long_coat + scarlett` | C3.2 | scarlett | 7.30 | 9.12 | 26.96 |
| `navy_peacoat + p012` | C3.2 | p012 | 6.15 | **13.12** | 5.19 |
| `p018 + p016` | C3.2 | p016 | 7.35 | 9.03 | **40.15** |
| `p019 + p010` | C3.2 | p010 | 7.76 | 2.05 | 1.48 |
| `p007 + p030` | C3.2 | p030 | 11.55 | **10.13** | 5.84 |
| `p009 + p014` | C3.2 | p014 | 9.79 | 5.62 | 23.45 |
| `hugh_jackman + p007` | C4 | p007 | 8.77 | 4.15 | 18.07 |
| `p017 + p002` | C4 | p002 | 7.52 | 1.78 | 12.23 |

**Two reasons not to read this as proof of over-cropping**, recorded so the claim is
not made stronger than the data supports:

1. **C3.2 keeps the hair, so hair damage cannot be its failure mode.** Its only
   over-crop is face removal, which costs 4.6–11.6% roughly uniformly across all 48
   references, successes included. The reviewer's own note points the other way: on
   the universal failure, "C3.2 failed at identity and changed the gender —
   interpreted the white space as cloth." Retained hair plus a white notch is
   **under**-cropping.
2. **Three of the five C4 failures have a counterexample with the identical garment
   source** — same crop, same damage, opposite outcome:

   | source | solved | failed |
   |---|---|---|
   | p007 | `p015 + p007` | `hugh_jackman + p007` |
   | p002 | `p015 + p002` | `p017 + p002` |
   | scarlett | `beige_long_coat + scarlett` | `man_black_suit + scarlett` |

   Skin loss does not rank outcomes either: C4 **solved** p016 at 40.15% skin
   removal and **failed** p002 at 12.23%. The base person is involved, not the crop
   alone.

**An unexplained pattern worth flagging.** On p007 and p002 the arms invert
perfectly: where C4 solved, C3.2 failed, and vice versa. Two sources, both flipped.
That reads as the arms being **complementary rather than ranked**, which if it holds
would argue for selecting a variant per reference rather than shipping one. Two
instances concludes nothing; recorded so phase 3 checks it rather than rediscovers
it.

**What this means for AC.** Its justification rests on the *measured* cohort, not on
this failure list. The eleven damaged references are real and the damage is large;
whether that damage caused any particular downstream failure is **not established**,
so phase 3 scores the repair against the measurement rather than the annotation.

### Three test sets, deliberately different

Named separately because two of them previously had the same count and got
conflated:

| set | contents | used by |
|---|---|---|
| **Damage cohort** | 11 *references*, by measured garment loss to the head cut | M, AC |
| **Pale cohort** | *references* whose border luminance fails the ΔL\* margin against white | BG |
| **Synthetic bed** | intact garments with *known* holes punched in | AC2–AC6 scoring only |
| **Failure pairs** | 11 *pairs* from the phase 2 annotations | klein trials, after the gates pass |

**Gating.** Nothing reaches klein until its free artifact is reviewed, and the gate
asks a different question per component: for M and AC, *does the crop look right*;
for BG, *did the detector decide correctly*. BG's page therefore prints the call and
the margin that produced it, not only the image.

## 3. What 2.2.3 is

A deterministic, CPU-only gate that decides whether a generated frame is usable.
It produces a verdict and reason codes per output; when enabled, a rejected
output triggers a re-call of the model on a fresh deterministic seed.

F3 has two shapes and each needs its own check:

| Shape | Appearance | Detection |
|---|---|---|
| **Degenerate** | Solid black, constant colour, blur-out — not a photograph at all | Pixel statistics: global standard deviation, Laplacian variance, unique-colour count |
| **No-op** | A perfectly good photograph that is the *input*, unchanged | Compare output against the person input: high SSIM plus near-zero change inside the garment region |

A no-op is invisible to pixel statistics — nothing is wrong with the image, it is
just the wrong image. The two checks are independent and both are required.

## 4. How this is measured

**All v2.2 comparisons are against the v2.2 series itself** — base klein, 2.2.1,
2.2.2. No cross-arm comparison: FASHN, Qwen and HiDream numbers are not re-run
and are not targets here. The question is whether these mitigations improve *our
chosen base*, not whether a different model would have been better; that contest
closed in [V2.1_RESULTS.md](../results_summary/V2.1_RESULTS.md).

Three configurations, identical seeds, one arm (`klein_4b_edit`, distilled):

| config | garment crop | person crop + composite |
|---|---|---|
| `base` | off | off |
| `v221` | on | off |
| `v222` | on | on |

**Human review is the primary judge for now.** Ray reviews outputs side by side;
deterministic metrics and the VLM rubric are supporting evidence, not the
verdict. Numeric thresholds are deliberately not pre-registered — with 13 pairs
and an eye-led verdict, fake precision would be worse than none. Direction of
movement is what matters, and thresholds can be set once the first run shows the
spread.

### On 2.2.2's structural advantage

2.2.2 composites the original background back, so background and identity scores
improve **by construction**. This is a genuine product win, not a measurement
artifact: the paste-back ships with the product. It is also self-correcting — an
inaccurate crop-back shows up as seams, misregistration and a *worse* score, so
the metric penalises exactly the failure mode that matters.

One guard: garment fidelity is reported on its own axis, so a strong background
score can never mask a garment regression inside a weighted composite.

## 5. Open design decision

**Silhouette paste-back or box paste-back** for 2.2.2. Cutting the exact
silhouette clips or halos when the new garment is bulkier than the old one (a
puffer over a tee) and would require background inpainting for the revealed
strip. Cropping a generous box preserves everything outside it by construction
and gives the model room, at the cost of leaving the background *inside* the box
to the model. To be settled before build — see [PLAN.md](PLAN.md).
