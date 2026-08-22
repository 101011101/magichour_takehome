# V2 — what was tried, what was kept, and why

**Companion to [ARCHITECTURE.md](ARCHITECTURE.md)**, which says what to build. This
document says why, and what was discarded to get there. Every sub-version is written
the same way: **the question · the architecture as built · the result · the verdict ·
how to redo it.** Numbers are cited to the document that measured them.

Negative results are recorded first-class. A superseded conclusion is marked, never
deleted — several of the most expensive lessons here are corrections.

Written 2026-08-21. Spend to date ≈ $19.6 fal + ~$3.3 judging.

---

## 0. V1, and why V2 exists

**Question.** Can a hosted-model cascade beat the Qwen-2511 baseline currently on the
Magic Hour website?

**Architecture.** `seedream5_lite` edit → `qwen_image3` realism refine. Selected by
human review, corroborated by a blind frontier-VLM judge at the grid stage.

**Result.** Best arm on 18 held-out pairs — VLM overall **4.22** (clean 4.06, realism
4.11, garment 4.00) against the baseline's 3.81. Recorded tension: on the deterministic
composite the holdout was still topped by pixel-compositing arms (flux_vto 0.642,
fashn_v16 0.632), and FASHN was the preservation champion at identity cosine 0.974 and
background PSNR 29.2 dB.
Evidence: `v1/artifacts/final_report_v2.html`, `FINAL_REPORT.pdf`, `v1/gallery/`.

**Verdict — dead, for two independent reasons.**

1. **Seedream is closed-weights.** V2's deploy path is open weights only, so the V1
   winner is unusable regardless of how well it scored.
2. **Identity degradation** carried over as an unresolved regression.

**Redo.** Nothing to redo; V1 stands as the baseline V2 must beat. The one thing worth
carrying forward is its *method*: blind human review as the primary judge, with
deterministic metrics used only for elimination.

---

## 1. v2.0 — choosing the editing base

**Question.** Which open-weights editor should everything else be built on?

**Architecture.** Three runs: triage on the V1 test set (4 arms × 4 pairs), an
auxiliary screen, and Testset2 (4 arms × 13 pairs, 51/52 generations succeeded). Judged
by deterministic metrics plus a blind VLM.
Cost ≈ $3.5 fal + $2.3 judging. *Documents were reconstructed after the runs and are
labelled as not a pre-registration.*

**Result.**

| arm | the hypothesis it represented | outcome |
|---|---|---|
| **FLUX.2 klein 4B distilled** | a strong *general* editor with no weak axis beats a specialist | fidelity **4.41**, realism 4.03, garment **4.08**, identity 4.46, id cos 0.903, `wrong_person` 0.00 → **CHOSEN** |
| FASHN VTON v1.5 | pixel-space, no VAE round-trip → best identity | best preservation (id cos **0.971**, bg **27.5 dB**) but worst garment (**3.33**) |
| Qwen-Image-Edit-2511 | the shipped baseline | fidelity 4.28, garment 3.77 — beaten by both leaders |
| FireRed-Image-Edit v1.1 | explicit **identity-consistency loss** in training | **VLM garment 2.00** |
| HiDream-O1-Image | pixel-native / no-VAE, same argument as FASHN | realism **4.08** (best on the board), but id cos 0.626, bg 14.1 dB, `wrong_person` **0.15** |
| FLUX.2 klein 4B **base** | do base checkpoints beat distilled siblings? | fidelity ties **exactly** (4.410) but garment 3.54 vs 4.08 |

Evidence: `v20_arms_ts2.html`, `v20_klein_variant.html`, `v20_coverage.html`,
`v20_triage_v1set.html`.

**Verdict.**

- **klein 4B distilled chosen.** No weak axis; the specialist hypothesis lost.
- **FireRed scrapped** — *"the identity-consistency-loss hypothesis did not survive
  contact with the task."* Garment 2.00 is a failure to transfer at all.
- **HiDream-O1 scrapped** on three counts: it re-renders the frame rather than editing
  it; it no-ops on outerwear (garment 1/5 on three of four `duo_lookbook` coats); and it
  was **the only arm to substitute the reference's person** (`ts2_08`, `ts2_11`, identity
  cosine 0.05 and 0.10). Its single win — realism — sends it to v2.4's bucket, not to
  the deploy path.
- **klein base not chosen** — ties on fidelity, loses on the ×2-weighted garment
  objective, judged clearly worse by eye, and costs roughly an order of magnitude more
  compute (28 steps at guidance 5 versus ~4 steps at CFG 0).
- **klein 9B ineligible** — non-commercial licence. 4B is the only usable size.
- **FASHN retained as a documented fallback**, not an arm: it is the right answer if the
  objective ever becomes strict preservation, but it carries a hard availability risk —
  its in-pipeline pose detection **errors the whole call**, on 1 of 13 pairs.
- **JoyAI / OOTDiffusion / OrthoTryOn deferred, not dropped** — no fal endpoint.
  `fal-ai/joyai-image-edit` exists but is the single-image Edit with one `image_url`, so
  it cannot take a person and a garment.
- **IDM-VTON, FitDiT, CatVTON, OmniTry, RefTon, DreamO, ACE++** — licence-blocked for
  deploy; usable as eval baselines only.

**The mistake v2.0 made, recorded first-class.** `wrong_person = 0.00 across all 38
outputs` was read as *"the model-to-model collapse did not happen."* Human review later
found failures on **4 of 7 duo pairs** — three of them missed by the deterministic
metrics *and* by the VLM, one scoring above the run mean. Two named instrument
failures: `garment_sim` is an embedding cosine, so a non-transfer still scores **0.78**;
and a no-op scores *perfectly* on identity. **Consequence: human review became the
primary judge from v2.2 onward, and remains so.**

**Redo.** Same shape, but: hold out a set for reporting rather than selecting and
reporting on the same 13 pairs; blind and double-rate the review; and run the
distilled-versus-base comparison at matched resolution with matched prompting — the
base ran with a preservation-only negative prompt the distilled model cannot accept, so
that comparison is still owed.

---

## 2. v2.1 — realism and fidelity preservation

**Question.** Can an auxiliary pass make klein's output look less generated without
damaging what klein got right?

**Architecture.** Two screens. **Screen 1**: 6 configs × 4 FASHN outputs, gate at VLM
fidelity ≥ 4.5 (24 generations ≈ $0.64). **Screen 2**, built after screen 1's design
flaw was found: 4 configs × 5 subjects × 2 batches — one batch of klein outputs and one
of **real photographs as a control** (40 generations ≈ $1.40 + ~$1.00 judging).

**Result** (screen 2, the one that counts):

| batch | config | realism | fidelity | id cos |
|---|---|---|---|---|
| klein | **seedvr2_x2_noise0** | **4.15** | 4.90 | **0.943** |
| klein | seedvr2_x2_noise01 *(fal default)* | 4.10 | 5.00 | 0.892 |
| klein | seedvr2_then_zimage | 4.05 | 4.90 | 0.702 |
| klein | zimage_s025 | 4.00 | 4.80 | 0.613 |
| **real photos** | **seedvr2_x2_noise0** | 4.05 | 5.00 | **0.937** |
| real photos | zimage_s025 | 3.90 | 4.90 | 0.721 |

Evidence: `v21_aux_screen.html`, `v21_aux_batches.html`.

**Verdict.**

- **SeedVR2 ×2 at `noise_scale = 0` chosen.** Wins both batches on realism *and*
  identity. Beats fal's default `0.1` on fidelity (5.00 vs 4.88) and identity (0.943 vs
  0.892) — the default is not the right setting.
- **Z-Image Turbo rejected at every strength.** It fails the damage-floor test: it
  restructures faces **on real photographs that needed no repair**, dropping AuraFace to
  **0.72** on a real photo and 0.61 on klein outputs. This is the single most useful
  thing the real-photo control bought.
- **Stacking (SeedVR2 → Z-Image) rejected** — worse on every axis than SeedVR2 alone,
  and costs identity (0.702 vs 0.943).
- **Artefact repair in this stage: settled as impossible.** The VLM `artifact_fix`
  criterion scored **exactly 3.00 — meaning no change — for every configuration across
  two rounds and 14 config-batches.** This became the founding premise of v2.3.
- **`hf_ratio` refuted as an over-sharpening signal** — same model and settings give
  1.20 on real photos and 1.68 on generated ones, so it restores in proportion to input
  softness. It is a review trigger, never an auto-fail.

**Screen 1's design flaw, and why screen 2 exists.** Every BEFORE image in screen 1 was
already AI-generated, so the screen could not distinguish *repair* from *damage*: a
config that restructured faces looked the same as one that fixed them. Adding a
real-photo control was the fix, and it is what killed Z-Image.

**Parked honestly, not closed.** *Gloss is not actually solved.* The workstream is named
for reducing gloss and plastic skin, but the winning mechanism is **restoration** — it
does not de-gloss. The model that does de-gloss destroys identity. Queued and unrun:
Real-ESRGAN and AuraSR-v2 as a zero-drift floor; **Z-Image Base + PAI Fun tile-ControlNet
+ UltraReal LoRA** (self-host only, the highest-priority gloss candidate); face-scoped
GFPGAN / RestoreFormer++ / PMRF; frequency-separation detail transfer.

**Redo.** Include a real-photo control from the first screen, not the second. Include a
deliberate breaking-point arm (`zimage_s035` played that role and earned its place).

---

## 3. v2.2.1 — cropping the garment reference

**Question.** A garment reference usually contains a *person*. Does that cause the
model to attend to the wrong thing, and does removing them fix it?

### 3.1 Phase 1 — building the cropper (free, CPU, 48 references)

**Architecture, as finally built.** BiRefNet_lite at 1024² supplies a soft subject
alpha; MediaPipe is demoted to semantic labels only; composition is **subtractive**.

**What was tried and discarded getting there:**

| discarded | why |
|---|---|
| MediaPipe Selfie Multiclass as the sole segmenter | 256×256 thresholded and upsampled ~6×. Fractional-alpha fraction was **exactly 0.00%** across 13 references — *a binary label upsampled 6× cannot produce a smooth edge* |
| YCrCb/HSV skin-colour heuristic | tore a wedge out of a beige coat on a dark-skinned model, and read a brown plaid overcoat as skin and destroyed it. **A bias failure, not a threshold failure — no parameter value fixes it.** Retained only as a fallback route |
| Intersective composition (`subject × clothes_class`) | notched 6 px blocks out of the peacoat outline |
| Shoulders-to-hips / hips-down category bands | deleted; dissolved a hem bug by construction |
| Trimap + guided-filter matting over BiRefNet | made results **worse** — white speckles ~15 px into a peacoat sleeve |
| 3-worker parallelism | slower, not faster: free RAM ~16 MB, onnxruntime paging, CPU down to ~35% |

Measured improvement: edge jaggedness on the beige coat **0.427 → 0.048**, soft-alpha
fraction 0% → 0.8%. Two references get *worse* on the jag metric (black suit, kimono) —
those are not regressions, the metric penalises true structure.
Evidence: `v221_crop_screen.html`, `images/v221_edge_before_after_beige_coat.png`.

### 3.2 Phase 2 — the crop variants against klein (33 sets, human review)

**Architecture.** Five arms per set: uncropped baseline plus four crop variants,
one variable, seed 46.

| variant | definition | solved |
|---|---|---|
| C1 `bbox` | whole-subject crop, background untouched | control |
| C2 `bbox_nobg` | background white, **wearer kept** | 9 / 20 (45%) |
| **C3.1 `no_face`** | background white, **hair and face removed**, body skin kept | **15 / 20 (75%)** |
| C3.2 `no_face_keep_hair` | background white, face only removed, hair kept | 9 / 20 (45%) |
| C4 `clothes_only` | every clothing class; skin and face removed | 15 / 20 (75%), conditional |

**Result.** The uncropped baseline failed **20 of 33 sets (61%)**. Baseline failure
categories: wrong clothes 36%, wrong person 33%, wrong background 33%, duplication 15%,
no transfer 9%. **Those three leading categories occurring at near-identical rates is
the signature of one cause, not three** — the model attending to the whole reference
rather than the garment in it.

Evidence: `v221_review.html` (the primary judgement), `v221_klein_trial.html`,
`v221_duo_transfer.html`, `images/v221_c3_no_face_example.jpg`,
`images/v221_c4_clothes_only_example.jpg`.

**Verdict.** C3.1 shipped as the default. C2 and C3.2 dropped as not competitive —
C3.2 in particular *"interpreted the white space as cloth instead of white space,"*
failing at identity and changing the gender. C4 not shipped because it works **only
where the cut boundary is clean**: hands crossing a garment punch holes through it.

**⚠ Withdrawn statistic.** An earlier table read **94–96% solve rate across all four
variants** and concluded the rate could not distinguish them. That was an artifact of
treating blank annotation cells as *unjudged* rather than as *not solved*. **The 94%
figure is withdrawn**; the correct figure is 75% for C3.1.

**Three residual mechanisms**, named from specific sets:

1. **Jagged cut edges are read as garment** — `man_black_suit + woman_top_denim_skirt`,
   the one set no arm solved. klein renders a ragged white notch as white cloth.
2. **A white background collides with a white garment** — `p018 + p014`. A white t-shirt
   was ignored entirely because it matched the ground.
3. **Body similarity helps, difference hurts** — `p018 + p016`, observed as a
   skin-colour mismatch.

### 3.3 The hair-damage cohort — the specific references everything is tested against

Measured as `C3.2 − C3.1`, the region hair removal takes out of the garment:

| reference | garment lost | enclosed | open | roughness C3.2 → C3.1 |
|---|---|---|---|---|
| **p021** | **19.53%** | 0.00% | 19.52% | **3.0 → 6.2 — doubles** |
| **p028** | 11.92% | 0.00% | 11.91% | 1.9 → 1.9 |
| **p016** | 9.75% | 1.51% | 7.99% | 8.6 → 7.2 |
| **p009** | 7.22% | 0.00% | 7.20% | 3.8 → 2.4 |

**The damage is *open*, not enclosed** — 19.52 of p021's 19.53 points. An enclosed hole
is surrounded by known fabric and inpainting is well-posed; an open notch has garment on
one side and background on the other, so filling it means extending the silhouette
outward with nothing constraining where the garment should end. **Framing this as an
inpainting problem is a category error**, and that single observation killed the
synthetic test bed (§3.4). Only **p021** actually gets jagged.

Use these five references — plus **p023**, the pre-registered worst case for head
removal — as the standing hard set for any change to stage 1.

### 3.4 Phase 3 — M (mannequin), BG (ground), AC (auto-complete)

Three components, each gated on a free artifact before anything was bought.

**M — mannequin. Scrapped entirely.** M1 flat mid-grey fill, M2 shaded grey (LAB, a/b
zeroed, L compressed to [116, 196]) — the expected winner. Both built and working;
**neither was ever klein-tested.** They were to be built only if the AC trials showed
failure or needed compensation for reduced attention. They did not: **the trigger
condition was never met.** An M3 blur tier and a featureless grey head form were cut to
keep the arm count honest. M4 face-smear-only was shelved and later **revived as AC-C**,
on the argument that eight failed head-removal iterations justified testing it properly.
Evidence: `v221_phase3_m.html`.

**BG — ground selection. Parked.** BG1 white control, BG2 flat `#F1F1F1`, BG3 adaptive
neutral ramp, BG4 ramp + radial falloff + contact shadow, BG5 white + contact shadow
only. The detector fires on 14 of 48 references and **every firing reference picks the
ramp floor `#C8C8C8`** — so *"the adaptive ramp collapses to a binary choice in
practice."* Dropped because **the pale-garment problem BG was built for rests on one
observed instance (`p018+p014`), and that reference was never in the klein test set.**
BG5 is the most promising if it is ever revisited.

*The checkerboard idea was dropped by argument, not data*: models have learned
checkerboard ⇄ transparency as something to **draw**, making it a leakage risk rather
than an erasure instruction.

*The BG detector was rebuilt once.* Version 1 took median luminance in a band inside the
garment boundary; on `p014` — the one documented failure — it reads median L\* 57 and
ranks the reference **13th of 48**, firing at no plausible threshold, while **22% of
that garment is near-white**. Replaced by pale **area share**, firing at 15%: p014 fires
at 22.0%, a flat white tee at 99.6%. **The lesson generalises: for "is any of this
white", measure area share, not central tendency.**
Evidence: `v221_phase3_bg.html`.

**AC — auto-complete, AC0–AC9.** A ladder of repair mechanisms, free arms first so the
licence questions might never need answering: AC0 control, AC1 algebra
(`B = (I − αF)/(1 − α)`), AC2 Telea/Navier-Stokes, AC3 FSR, AC4 PatchMatch (never
built), AC5 MI-GAN, AC6 LaMa, AC7.1–.3 generative repair (klein / Qwen inpaint / Z-Image
inpaint), AC8.1–.2 generative *crop*, AC9 SeedVR2 post-pass.

AC1 is instructive: **100% of fringe pixels fall inside its α window and it still
undercorrects**, because it assumes a single *global* hair colour — dark hair on dark
fabric leaves the rim.

Scrapped inside AC:

| scrapped | why |
|---|---|
| **SUPIR** | its licence *"does not grant any rights to the weights, biases, or architecture."* Widely described as open-source; **not open weights** |
| **Virtual try-off family** — TryOffDiff (SSPL), TryOffAnyone, CatVTON (CC BY-NC-SA) | commercially locked. The Apache amodal-completion alternative needs LISA-13B + SD2 + Grounded-SAM — neither light nor licence-clean |
| **Synthetic punched-hole test bed** | *"It tests a defect we do not have."* A punched hole is enclosed; our damage is an open boundary notch. **Ground truth is not worth having if it is truth about the wrong question** |
| **OC5** (over-crop by 5% area) | solved radii came out **inversely related** to the defect: p016 at 4.69% fringe needed 5 px, p023 at 0.29% needed **60 px**. A defect in the definition, not in the result |
| **Qwen-Image-Edit-Plus** | worst arm on every axis measured — ΔL 23–99 against 2511's 10.7. Run abandoned incomplete; not worth completing |
| **Ghost-mannequin prompt p3** | ΔL **48** on 2511, **99** on Plus — read as *"make it pale and simple"* rather than *"keep the drape."* Moved to the parking lot, not deleted |
| AC5 MI-GAN / AC6 LaMa | clean Apache/MIT **code**, but Places2-trained checkpoints whose data terms say non-commercial. Unresolved; avoided by the free arms winning |

Evidence: `v221_phase3_ac.html`, `v221_phase3_acc.html`, `v221_phase3_crops.html`,
`v221_phase3_acab.html`.

### 3.5 Eight head-detection iterations, and what replaced them

Removing the head from a **bald** frame broke every geometric rule tried, because
`head = HAIR + FACE` and there is no hair: head removal fell from 17.6% to **8.6%**,
leaving half the skull.

| iteration | failed on |
|---|---|
| narrowest-silhouette neck | found no neck at all on p021, p019 |
| face-anchored band | cost p028 10 points and p030 17 points of clothes |
| "cut above the chin" | swept in a blob 36% of the subject, 60% clothes-class — raised arms |
| pose ellipse | p016's ears are **9 px apart**; a 54 px ellipse missed the scalp |
| silhouette sizing | p028 lost 8.6 points |
| neck-length cap | p028 −3.2, p030 −1.7 |
| clothes guard | **19.5% of p019's head region classified as clothes** and therefore protected, leaving the crown |

**Seven iterations, each trading one reference for another — the signature of a
heuristic at its ceiling.** Replaced by the **SegFormer-B2 / ATR human parser** bounded
by pose and reduced to the nose-connected component: head removal **+5.0 points** mean,
against +0.8–1.2 for the best geometric rule.

**A defect found by eye, not by instrument.** BiRefNet's subject matte counted a stool
on `p023` and a chair on `p021` as subject — *and therefore so did every crop produced
up to that point.* This was the **third** time an instrument missed something the eye
caught.

### 3.6 The Attention Modulation Test — the phase that decided the arms

**Architecture.** 38 sets × 10 arms, klein 4B distilled, seed 46, one variable: the
garment reference. Arms: `control` (C3.1), `BC_klein`, `QX_qwen_p1`, `BALD_raw`, and six
face-destruction arms — blur / twirl / pixelate, each on the original frame (`/O`) and
on the bald frame (`/B`). Ranked by drag-ordering with an explicit tied-first band.

**Result** (final, all 38 sets, perfect / fail): **BC_klein 74% / 5% · D3B 68% / 5% ·
PHEAD 63% / 21% · QX 58% / 8% · control 53% / 34%.**
Evidence: `v221_attention_mod.html`, `v221_crop_tuning.html`,
`v221_crop_tuning_phead.html`, `images/amt_outcomes.png`,
`images/amt_per_reference.png`.

**Verdict and drops.**

- **`BALD_raw` dropped** — 85% cut, zero wins. *The crop earns its place.*
- **`control` (C3.1) dropped as a standalone ship.** On high-damage references it goes
  from 75% best to **28%**, and from 10% failed to **61%**. The earlier conclusion that
  *"nothing beats what already ships"* is **withdrawn**.
- **The `/O` disfiguration arms dropped** — identity leaks; they are the only arms on
  which the identity check ever fires.
- **BC_klein + D3B pairing dropped** — 13 points *below* an independence model. Both are
  bald-based subtraction, so they share a failure mode.

**Two statistics withdrawn.** *Mean rank* and *win-count* were both computed and both
are invalid: the top band is a **tie**, so order within it is meaningless.

**⚠ The test set excluded its own failure mode.** The first 20-pair AMT set contained
only 5 of the 11 damage references, and **p021 — the worst at 19.53% — was never tested
at all.** That flattered the baseline and produced a wrong recommendation. Fixed by
adding 6 + 12 pairs. **Always check that a test set contains the failure mode it is
meant to test.**

**A conditional trigger on the damage number was withdrawn** — it does not separate the
cases, and is non-monotonic: `p009` at 7.2% loss fails on all three people it is paired
with, while `zendaya` at 14.4% is fine.

### 3.7 The governing finding — the descent hypothesis

klein descends toward a correct solution **it can already produce**; the attention
deficit is what chips away at it. The model is not short of capability — competing
content in the garment reference is what stops it going all the way.

**Therefore the *manner* of removing the deficit is free to vary.** That
interchangeability is where the cost work lives: if attention rather than capability is
the bottleneck, a cheaper base model with a clean reference may match a larger one with
a poor reference.

### 3.8 FASHN cross-check

**Question.** Does our cropping help a purpose-built try-on model, or is it solving a
problem FASHN does not have? Arms `FA_base` (raw on-model photo), `FA_c31` (our crop),
`FA_pre3` (Qwen bald frame); 20 klein-failure pairs, v1.5 pinned.

**Result: base ≈ c31** — FASHN's internal segmentation already handles worn references,
so cropping is redundant *for it*. The attention deficit is a property of general-purpose
editors, not of try-on models. Evidence: `v221_phase3_fashn.html`.

---

## 4. v2.2.2 — person crop and composite. Closed as obsolete.

**Question it was built for.** Protect the **background** by cropping the person out so
the model never sees it, then compositing back.

**Verdict: closed, addressed by v2.2.1.** It is only worth building if background damage
is its own failure mode. It is not — it is a symptom of the same attention deficit.

| | |
|---|---|
| Sets with wrong background on the uncropped baseline | 11 of 33 |
| …co-occurring with **wrong person** | **9 of 11 (82%)** |
| …background wrong **on its own** | **1 of 11 (9%)** — `p009+p018` |
| **P(wrong background \| wrong person)** | **82%** |
| **P(wrong background \| person was correct)** | **9%** |

**A nine-fold difference.** Background damage is almost never independent; it appears
when the model is already confused about which person it is looking at.

**What remains unproven, and why it does not change the decision.** The AMT rankings were
holistic — one verdict per output, no per-axis columns — so background was never scored
on its own axis. The claim rests on co-occurrence structure plus the absence of failures
downstream. Cheap residual check if ever wanted: `bg_psnr` outside a dilated person mask
on the AMT outputs, which are already on disk.

**Reopen only if** background damage reappears in the v2.3 artefact review, or a product
requirement makes background fidelity explicit. `p009+p018` is the pattern to watch.

---

## 5. v2.2.3 — the failure gate, and why it died

**Question.** Can a deterministic, CPU-only check decide whether a generated frame is
usable, so the pipeline can escalate only when needed?

**Architecture as built.** Five checks, each returning a margin in [0, 1] — `degenerate`
(global std, Laplacian variance, unique colours), `noop` (SSIM against the person input),
`people` (duplicate-subject detection), `identity` (AuraFace cosine), `background`. The
composite is the **weakest** check, not the average, so one hard failure sinks a frame.
Run over all 456 AMT outputs.

**Result — near-random.**

| human label | gate score (mean) |
|---|---|
| perfect | 0.677 |
| ok | **0.757** ← higher than perfect |
| fail | 0.584 |

Then tested blind against the reviewer on 114 cells:

| | |
|---|---|
| Mean score, cells marked **usable** (n=82) | 0.684 |
| Mean score, cells marked **unusable** (n=32) | 0.674 |
| **AUC** | **0.506** |
| Best agreement at any threshold | 71.1% |
| **Agreement from accepting every frame unchecked** | **71.9%** |

Evidence: `images/gate_vs_human.png`, `v223_gate_simulation.html`,
`v223_cheapest_usable.html`.

**The one check that works, and how far it goes.** `identity` separates at +0.216 and
is **100% precise** at every threshold from 0.1 to 0.6 — it has never once flagged a
frame the reviewer liked. It fires most on `BALD_raw` (12/38) and the `/O`
disfiguration arms, which keep a head in the garment reference.

> **Corrected 2026-08-22.** The original text here read *"fires on zero of PHEAD,
> BC_klein and QX… the only check with signal is blind to every case the cascade needs
> caught."* **That was measured at threshold 0.5, which is the wrong operating point,
> and the conclusion was wrong.** At **0.90** identity fires exactly once across the
> 114 cascade cells — on `HD_p028+navy_peacoat`, where the person was substituted
> entirely, and which was **the only frame the shipped harness got wrong**. It is now
> part of the escalation rule. Rare, precise, and not dead. The error was found by a
> spot-check of one image, not by any of the statistics.

*It had also never actually run until 2026-08-21* — AuraFace was silently disabled by a
path mismatch (the HF snapshot puts its ONNX files at the snapshot root; insightface
expects `<root>/models/<name>/`), so it tried to fetch a non-existent `auraface.zip` and
fell back to no model, scoring a constant 1.0.

**The control that makes this conclusive.** The same reviewer labelled the same outputs
twice, in different sessions under different questions. The earlier AMT tier predicts the
later binary call at **95% / 44% / 0%** across perfect / ok / fail — perfectly ordered.
**The target is stable and reproducible; the instrument is the problem.**

**Verdict.**

- **The deterministic gate does not ship as a quality judge.** This is not a calibration
  problem. Pixel statistics cannot see semantic failure, and all 456 outputs are valid
  photographs — the failures are *wrong garment, wrong identity, repainted scene*.
- **Two of its five checks ship as detectors.** The composite score does not, but
  `noop` and `identity` do, as escalation triggers. Over 114 cells the VLM caught 26
  failures they missed and they caught **1** the VLM missed — and that one was the only
  frame that shipped broken. A no-op and an identity swap are both *coherent
  photographs of the wrong thing*, so a semantic judge has nothing to find; only a
  numeric comparison against the input reveals them. They cost nothing.
- **Recall is the wrong metric for a free check.** 7% against the VLM's 65% is not an
  argument for dropping something that runs on CPU and makes no API call.
- **The reseed design is dead.** Failure is a property of the **garment**, not the roll:
  a damaged reference failed on all three people it was paired with. Escalate mechanism,
  never seed.

**A deterministic AI-artefact check is not available even in principle.** Published
detectors answer *"was this generated?"* — and 100% of these frames were, so such a
detector fires on everything and discriminates nothing. The question needed is *"is this
generated image **wrong**"*, a different axis. The one genuine exception worth building
is anatomical plausibility (MediaPipe Hands finger counting, impossible pose landmarks),
as a free pre-filter ahead of the VLM.

---

## 6. v2.2.3 — the harness that replaced it

**Question.** If the output cannot be judged deterministically, can the *input* be?

**Result: yes.** `hair_over_garment` = `C3.2 − C3.1` predicts *"PHEAD will not be
perfect"* at **AUC 0.862**, against 0.38–0.57 for every check that reads the output. It
is free, already computed, and is not a proxy — it is the pixel area hair removal takes
out.

**Routing turned out to be the half that works and the gate the half that does not** —
the reverse of the "gate first, routing second" assumption v2.2.3 was built on. A router
reads the input, where a physically-meaningful measurement exists.

**The absolute re-mark.** All 38 sets were re-marked **perfect / ok / fail** in absolute
terms, because the earlier binary sheet conflated *ship it* with *acceptable*.
Evidence: `v223_perfect_tier.html` → `v223_perfect_tier_picks.csv`,
`images/harness_v223.png`.

| arm | perfect | ok | fail |
|---|---|---|---|
| PHEAD | 23 (61%) | 5 | 10 |
| BC_klein | **28 (74%)** | 6 | 4 |
| QX | 20 (53%) | 17 | **1** |

**QX's shape is the finding.** Lowest ceiling, by far the lowest floor. The binary sheet
had scored it 71% "usable" and hidden that most of those were merely *ok*. It is a
safety net, not a quality arm — which is exactly why it is last.

| design | gen/req | perfect | ok | fail |
|---|---|---|---|---|
| flat BC_klein, no harness | 2.000 | 28 | 6 | **4** |
| first arm only, no escalation | 1.263 | 28 | 5 | 5 |
| **router → arm → QX on failure** | **1.526** | **32** | 6 | **0** |
| escalating on *not perfect* rather than failure | 1.789 | 34 | 4 | 0 |
| full 3-step cascade PHEAD → BC → QX | 2.053 | 34 | 4 | 0 |

**⚠ The AMT tier is retired as the label of record.** AMT `perfect` meant **tied for
first among ten arms** — a relative ranking, and an arm can top a weak field without
being shippable. It agrees with the absolute pass on 81% of cells, so conclusions built
on it were directionally right and quantitatively loose.

**Three recommendations reversed by the absolute re-mark**, recorded because the pattern
matters:

1. **Route high-hair references to BC_klein, not QX.** The earlier call came from the
   binary marks, where QX's 17 *ok*s counted as wins. On absolute marks BC_klein takes 5
   of the high-hair PHEAD failures to perfect against QX's 4.
2. **Two candidates on escalation, never three.** The un-chosen subtractive arm is
   itself `fail` on 3 of the 5 escalated sets.
3. **A VLM is affordable after all.** The earlier ruling priced a *closed frontier* API.
   A self-hosted 7–8B open model costs ~$0.0003 against ~$0.015 per generation, and
   since a wasted escalation costs 2 generations, **it can be wrong 100 times per save
   and still break even.**

**The four-feature router was dropped** (torso lean, frontality, garment share, landmark
visibility, z-summed): ~75% precision against a 79% break-even, fitted and evaluated on
the same 22 garments. Garment class count and entropy as unusualness proxies **pointed
the wrong way** — both *lower* on weak cases.

---

## 7. Withdrawn claims and corrections

Kept together because they are the expensive lessons.

| withdrawn | replaced by |
|---|---|
| "~94–96% solve rate across all four crop variants" | 75% for C3.1; blank cells were *not solved*, not *unjudged* |
| Mean rank and win-count in the AMT | nothing — invalid where the top band is a tie |
| The PRE "garment lost" metric on bald frames | nothing — `C3.2 − C3.1` collapses to ~0 by construction on a bald frame, so **every** bald frame scores ~0 regardless of quality |
| A conditional trigger on the damage number | non-monotonic; p009 at 7.2% fails, zendaya at 14.4% is fine |
| "Nothing beats what already ships" (control) | control collapses on damaged references, 75% → 28% best |
| `wrong_person = 0.00` read as "no collapse" | human review found failures on 4 of 7 duo pairs |
| `hf_ratio` as an over-sharpening signal | it tracks input softness; review trigger only |
| The AMT tier as label of record | the absolute perfect/ok/fail pass |
| "A VLM costs about what a generation costs" | true of closed APIs; a self-hosted 8B is 20–50× cheaper |
| BG detector v1 (median border luminance) | pale **area share** |

**The working agreement that produced all of these: judge by eye.** Three separate times
an instrument said the opposite of the truth — no-op outputs scored perfectly on
identity; the bald-frame "garment lost" metric collapsed by construction; furniture sat
in every crop undetected. Every stage of this pipeline was debugged by looking.

---

## 8. v2.3 and v2.4 — scope as planned

**v2.3 — artefact reduction.** Design complete, nothing run; all its numbers are
hypotheses. Founding premise: whole-image realism passes cannot repair artefacts
(`artifact_fix` = exactly 3.00 in 14/14 config-batches), so v2.3 builds a **detect →
localize → repair → verify** loop operating on regions. Five-class taxonomy: A1
anatomical/hands, A2 seam/compositing, A3 garment physics (*declared unsolved*), A4
duplication, A5 texture. Repair mechanisms ranked weakest-sufficient-first: restore
original pixels → hand detailer at denoise ≤ 0.3 → klein local crop → EliGen → LaMa →
Z-Image inpaint (*deprioritized on our own evidence*). Rejected before running:
FLUX.1-Fill-dev (non-commercial), any retrained model (no training in V2).
Stop rule, pre-registered: *if region-targeted repair also fails, artefacts must be
attacked at the editing stage rather than repaired at all.*

**May now be partly answered by v2.2.3** — if VLM-A plus QX escalation removes artefacts,
v2.3's question is smaller than it was. Decide after the harness trials.

**v2.4 — auxiliary realism, revisited.** Deferred by decision. Candidates: **Z-Image Base
+ PAI Fun tile-ControlNet + UltraReal LoRA** (highest priority, self-host only),
Real-ESRGAN / AuraSR-v2 as a zero-drift floor, **HiDream-O1 re-screened in the realism
bucket** (its one v2.0 win), face-scoped restorers. Open question worth keeping: should
the auxiliary stage be **conditional** on a measured realism deficit rather than always
on?

**v2.1.1 (parity) is not a workstream** — parity is a release gate, not an
information-generating experiment.

---

## 9. Owed, regardless of what happens next

1. **The self-hosted parity run.** Every number in every V2 document is a **fal** number
   and V2's premise is open weights in the deploy path. Nothing has been verified on
   downloaded weights end to end. Of all outstanding work this is the one most likely to
   matter in review.
2. **`mattmdjaga/segformer_b2_clothes` licence and training-data terms.** Head detection
   depends on it. Fine for measurement; **not cleared for deploy.**
3. **AC5 MI-GAN / AC6 LaMa** — Places2 checkpoint terms, if those arms are ever revived.
4. **The klein distilled-versus-base isolation run** — the base ran with a
   preservation-only negative prompt the distilled model cannot accept.
5. **Methodology debt**, recorded 2026-08-15 and still open: variant selection and
   reporting use the same pairs, with no held-out split; review is unblinded and
   single-rater; every claim is about klein specifically and untested on a second editor.
