# V2 — virtual try-on, assembly specification

**This document is standalone.** It is what to build and how, with no history and no
argument. Why each choice was made, and what was tried and discarded, is in
[DECISIONS.md](DECISIONS.md). What is left to do is in [TODO.md](TODO.md).

Written 2026-08-21. Target: implementation in Magic Hour company code.

---

## 1. Scope and the hard constraint

Given a **person photo** and a **garment reference** (which is usually itself a photo
of a different person wearing the garment), produce a photograph of the person wearing
that garment.

**Open weights only in the deployed path.** Every model below is a downloadable
checkpoint under a commercial-use licence. fal is used as a *serving substrate* for
those same checkpoints during iteration; it is never a model source, and no closed
model may enter the pipeline. Two consequences that are easy to get wrong:

- FLUX.2 klein **4B** is the usable size. The 9B sibling is non-commercial.
- FASHN **v1.5** is the open release. fal's `v1.6` endpoint is FASHN's closed
  commercial model — the endpoint string must never be bumped.

**One licence is unresolved and blocks deploy:** `mattmdjaga/segformer_b2_clothes`,
the human parser. See §9.

---

## 2. The pipeline

```
  person photo  +  garment reference
                        │
        ┌───────────────┴────────────────┐
        │  1. REFERENCE PREPROCESSING    │   free, CPU
        │     subject matte + parse      │
        └───────────────┬────────────────┘
                        │
        ┌───────────────┴────────────────┐
        │  2. ROUTER                     │   free — reads §1's output
        └───────────────┬────────────────┘
                        │
    user named a region?├──yes──────────────────────────────► QX arm      (2 gen)
                        │
   hair over garment    ├──yes──────────────────────────────► BC_klein arm (2 gen)
        ≥ 14% ?         │
                        └──no───────────────────────────────► PHEAD arm   (1 gen)
                                                                   │
                        ┌──────────────────────────────────────────┘
                        ▼
        ┌────────────────────────────────┐
        │  3. CRASH GUARD                │   free, CPU — deterministic
        │  4. VLM-A: "is this broken?"   │   ~$0.0003
        └───────────────┬────────────────┘
                        │
              fires ────┴──► QX arm (+2 gen) ──► VLM-B picks between the two
                        │                                    │
                       clean                                 │
                        └────────────────┬───────────────────┘
                                         ▼
        ┌────────────────────────────────────────┐
        │  5. REALISM PASS — SeedVR2 noise_scale=0│   ~$0.005
        └────────────────┬───────────────────────┘
                         ▼
                      OUTPUT
```

**Measured: 1.526 generations per request. 32 perfect / 6 ok / 0 fail over 38 sets.**
The comparison that matters is flat BC_klein — the strongest single arm — at 2.000
generations for 28 perfect / 6 ok / **4 fail**. The harness is cheaper *and* ships
nothing broken. **The zero is the result, not the perfect count.**

---

## 3. Component reference

| # | component | checkpoint | licence | where | cost |
|---|---|---|---|---|---|
| 1 | subject matte | **BiRefNet_lite**, 1024², 224MB ONNX | MIT | CPU | free |
| 1 | human parser | **`mattmdjaga/segformer_b2_clothes`** (SegFormer-B2 / ATR, 18 classes) | **UNVERIFIED** | CPU | free |
| 1 | pose | **MediaPipe Pose Landmarker lite**, 5.8MB | Apache-2.0 | CPU | free |
| 3 | editing base | **FLUX.2 klein 4B distilled** | commercial-OK (9B is not) | GPU | ~$0.015 / gen |
| 3 | extractor | **Qwen-Image-Edit-2511** | Apache-2.0 | GPU | ~$0.015 / gen |
| 4 | artefact judge | **Qwen2.5-VL-7B** (candidate — see §9) | Apache-2.0 | GPU | ~$0.0003 / call |
| 5 | realism | **SeedVR2** ×2 upscale, `noise_scale = 0` | Apache-2.0 | GPU | ~$0.005 |

Alternate VLMs, licence-first: Pixtral-12B (Apache-2.0), InternVL3-8B, Kimi-VL-A3B
(MIT), Ovis2 (Apache-2.0). **Do not use** Llama 3.2 Vision (its licence excludes
EU-domiciled entities) or Gemma 3 (use restrictions). Verify every licence against the
model card before shipping — these change.

Generation is billed per call; klein is the unit of cost throughout this document
(1 unit ≈ $0.015). A VLM call is **0.02 units**. Hold that ratio in mind reading §6.

---

## 4. Stage 1 — reference preprocessing

Everything in this stage runs on CPU and costs nothing. It produces the masks all three
arms consume and the single feature the router reads.

```
garment reference
  → BiRefNet_lite at 1024²      → subject alpha (soft, 8-bit)
  → SegFormer-B2 / ATR          → 18 part classes
  → MediaPipe Pose Landmarker   → body landmarks
```

Class grouping used throughout:

```python
ATR = {"head":    (1, 2, 3, 11),                    # hat, hair, sunglasses, face
       "garment": (4, 5, 6, 7, 8, 9, 10, 16, 17),
       "skin":    (12, 13, 14, 15)}                 # arms and legs
```

**Composition is subtractive, never intersective.** Take BiRefNet's alpha as the
silhouette and subtract class regions from it. Intersecting the alpha with a class mask
notches holes in garment outlines, because the two disagree at boundaries.

**The head region needs all three models, not just the parser.** ATR's `face` class
bleeds down the torso on bald or short-haired subjects. The rule that works:

1. take `head` classes from the parser for shape,
2. bound the region vertically using pose landmarks so it cannot run down the body,
3. keep only the connected component containing the nose.

Step 3 is what stops raised arms and background objects being swept in.

**Known defect, unfixed:** BiRefNet's subject matte includes furniture in contact with
the person — a stool on `p023`, a chair on `p021` — and therefore so does every crop.
It has not caused a measured failure. Watch for it; do not assume the matte is the
person.

### The router feature

```
hair_over_garment = (area(C3.2) − area(C3.1)) / area(C3.2)
```

where `C3.1` removes hair **and** face and `C3.2` removes face only. This is the pixel
area that hair removal takes out of the garment crop — not a proxy for it, the thing
itself. It is a free byproduct of masks this stage already computes.

It predicts *"PHEAD will not be perfect"* at **AUC 0.862**. Threshold **14%**; quality
is flat from 12% to 16%, so it is not a knife-edge.

---

## 5. Stage 2 — the three arms

The arms are pipelines, not models. Each ends in the same klein call; they differ in
what garment reference they hand it.

### PHEAD — 1 generation, the default

```
reference → [stage 1 masks] → subtract head → white ground → klein edit
```

No generative preprocessing. The whole arm is mask arithmetic plus one klein call.

### BC_klein — 2 generations, for high-hair references

```
reference → klein: "Make this person completely bald..."      ← generation 1
          → [stage 1 masks] applied to the bald frame
          → subtract head → white ground
          → klein edit                                         ← generation 2
```

Generating a bald frame first means hair removal has less to remove, so the crop takes
away less garment. It is the same subtraction as PHEAD, applied to an easier input.

### QX — 2 generations, the escalation target

```
reference → Qwen-Image-Edit-2511: return only the clothing      ← generation 1
          → klein edit                                          ← generation 2
```

### Why the order is what it is

| arm | perfect | ok | fail | mechanism |
|---|---|---|---|---|
| PHEAD | 23 (61%) | 5 | 10 | subtract |
| BC_klein | **28 (74%)** | 6 | 4 | subtract |
| QX | 20 (53%) | 17 | **1** | **regenerate** |

**PHEAD and BC_klein both subtract; QX regenerates.** That single fact drives three
design decisions:

1. **QX is last, and is the escalation target.** It has the lowest ceiling and by far
   the lowest floor — one failure in 38. It is a safety net, not a quality arm.
   Escalating to BC_klein instead gives 29 / 6 / **3** against QX's 32 / 6 / **0**.
   QX is the only arm that converts failures into non-failures.
2. **BC_klein is reached by the router, not by escalation.** Subtraction cannot recover
   what the crop never saw, so when PHEAD fails, BC_klein tends to fail the same way —
   it rescues only 6 of PHEAD's 13 hard cases against QX's 11.
3. **Never generate a third candidate.** Adding the un-chosen subtractive arm on
   escalation costs +0.21 generations per request for **zero** quality gain. On the 5
   escalated sets it is itself `fail` on 3. It is paying to re-run what just broke.

---

## 6. Stages 3–4 — the failure path

### Crash guard (free, deterministic)

Global standard deviation, Laplacian variance, unique-colour count, and an SSIM
no-op check against the person input. **This catches crashes only** — a black frame, a
truncated response, an unchanged input. It is justified by production robustness, not
by measured quality value: on the 114-cell test set it catches 1–2 of 32 bad frames
while wrongly rejecting 2–4 good ones, because that set contains no crashes.

**Do not extend it into a quality judge.** See §8.

### VLM-A — the artefact screen

Runs on **every** request, on the first arm's output. Asks one narrow question:
*"Does this image contain rendering artefacts, anatomical impossibilities, or obvious
generation errors?"* Binary answer.

**Ask this, not "is this good".** A VLM scored 4/5 on an output that transferred no
garment at all — absolute quality judgement is a question VLMs fail. "Is it broken" is
visual and much easier.

### VLM-B — the selection call

Fires only on escalation (~26% of requests). Forced choice between the first arm's
output and QX's: *"Which of these two is the better try-on result?"* Both candidates
are in hand, which is the form of question a VLM handles best.

On current data this is **insurance rather than value** — QX is at least as good as
the first arm on all 5 escalated sets, so "always take QX" gives the same answer. Keep
it anyway; QX does fail once in 38, and the call costs 0.02 units.

### The economics — why a VLM at all

| | cost |
|---|---|
| one VLM call | **$0.0003** |
| one generation | $0.015 |
| one *wasted* escalation | **$0.030** |

A VLM check is **0.02 generation-equivalents**, roughly 1% of pipeline cost. Since a
wrong escalation costs 2 generations, **the VLM can be wrong 100 times for every time
it saves a generation and still break even.** You are not buying accuracy; you are
buying a cheap opinion, and almost any opinion beats none.

This is why a VLM works here and did not in earlier analysis: earlier costing assumed a
closed frontier API. A self-hosted 7–8B open model is 20–50× cheaper, and is open
weights, which the deploy path requires anyway.

**Trigger scope is a tunable.** Firing only on hard failures gives 32 / 6 / 0 at
1.526 generations. Firing on anything less than perfect gives 34 / 4 / 0 at 1.789.
**Start with failures only** — it removes every failure, which is the headline, and
asks the easier question.

---

## 7. Stage 5 — realism

**SeedVR2, ×2 upscale, `noise_scale = 0`.** Note `0`, not fal's default `0.1`: the
default is measurably worse on both fidelity (4.88 vs 5.00) and identity (0.892 vs
0.943).

SeedVR2 accepts **no text input**. It restores; it does not repair artefacts and it
does not remove gloss.

---

## 8. What not to build

Each of these was built or costed and rejected on measurement. They will look like good
ideas again.

| Do not build | Why |
|---|---|
| **A deterministic quality gate** | Measured **AUC 0.506** against the reviewer over 114 blind cells. Best threshold agreed on 71.1% of cells; accepting every frame unchecked agrees on 71.9%. Not a calibration problem — pixel statistics cannot see semantic failure |
| **Retry with a fresh seed** | Failure is a property of the **garment**, not the roll: a damaged reference failed on all three people it was paired with. A retry reproduces it. Escalate mechanism, never reseed |
| **A third candidate on escalation** | +0.21 gen/request, zero quality gain. Shares the failure mode that just fired |
| **An off-the-shelf AI-artefact detector** | They answer *"was this generated?"* — 100% of these frames were. Such a detector fires on everything and discriminates nothing |
| **A VLM router for hair** | The deterministic measure *is* the quantity, not a proxy. A perfect router would save 0.053 gen/request; a VLM router costs 0.020. Ceiling ≈ 2% |
| **Z-Image Turbo, anywhere** | Fails the damage-floor test at every strength — restructures faces on **real photographs that needed no repair**. AuraFace drops to 0.72 on a real photo |
| **A whole-image artefact pass** | The VLM `artifact_fix` criterion scored **exactly 3.00 — no change — in 14 of 14 config-batches** |
| **A grey mannequin form, or a non-white ground** | Both built, neither ever triggered. The pale-garment case rests on one observed reference |
| **A closed-model VLM or editor** | Deploy constraint, and cost |

---

## 9. What is unproven

State these wherever the numbers above are quoted.

1. **VLM-A is unbuilt.** Every number in §2 assumes it fires correctly. Cost is
   settled; capability is not measured. Validating it needs GPU time and no fal
   spend — 456 outputs and 114 absolute tiers are on disk.
2. **The 14% threshold is fitted** on these 38 sets. AUC 0.862 is the honest figure;
   the cut-point needs recomputing over all 48 references, held out.
3. **The user-specification branch has no evidence at all.** Nothing in the test set
   carries one. QX's single-failure profile makes it a safe default; that is reasoning.
4. **The human parser's licence is unverified**, and head detection depends on it. It
   is fine for measurement and **not cleared for the deploy path**.
5. **n = 38, one reviewer, one seed, unblinded.**
6. **Every number in this document is a fal number.** Nothing has been verified on
   downloaded weights end to end. This is the largest outstanding gap.

---

## 10. Build order

Each step is independently verifiable, so a failure localises. **Production rule,
applied at every stage: a stage that cannot do its job passes its input through
unchanged. No stage may ever emit a broken image.**

| # | build | verify against |
|---|---|---|
| 1 | Stage 1 masks — BiRefNet, parser, pose, the head rule | crops by eye on the known-hard references: `p021`, `p028`, `p016`, `p009`, `p023` |
| 2 | `hair_over_garment` | reproduces AUC 0.862 against the labelled tiers |
| 3 | PHEAD arm end to end | 23 / 5 / 10 on the 38 sets |
| 4 | BC_klein and QX arms | 28 / 6 / 4 and 20 / 17 / 1 |
| 5 | Router | routes 10 of 38 to BC_klein at 14% |
| 6 | Crash guard | fires on a deliberately blacked frame; fires on a no-op |
| 7 | **VLM-A** — the unbuilt piece | separates broken from clean on the 114 tiers, beating AUC 0.57 by a wide margin |
| 8 | VLM-B, escalation wiring | 1.526 gen/request, 32 / 6 / 0 |
| 9 | SeedVR2 pass | identity cosine does not drop; `noise_scale` is `0` |
| 10 | **Self-hosted parity** | every number above, on downloaded weights |

**Judge by eye at every step.** Three separate times in this project an instrument said
the opposite of the truth: no-op outputs scored perfectly on identity; a "garment lost"
metric collapsed to zero by construction; furniture sat in every crop undetected. The
pipeline was debugged by looking, not by measuring.
