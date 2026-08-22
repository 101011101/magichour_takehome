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
        ┌────────────────────────────────────────────┐
        │  3. CRASH GUARD (no-op / degenerate)       │  free, CPU
        │  4. VLM-A, two prompts on one model:       │  ~$0.0006
        │       tryon   != PERFECT   ──┐             │
        │       garment == FAIL      ──┴─► escalate  │
        └───────────────┬────────────────────────────┘
                        │
              fires ────┴──► QX arm (+2 gen) ──► take QX unconditionally
                        │                                    │
                       clean                                 │
                        └────────────────┬───────────────────┘
                                         ▼
        ┌────────────────────────────────────────────┐
        │  5. REALISM PASS — conditional             │  ~$0.04, ~76% of requests
        │     skip if already sharp                  │
        │     revert if it damages the face          │
        └────────────────┬───────────────────────────┘
                         ▼
                      OUTPUT
```

**Measured end to end: 2.105 generations per request. 30 perfect / 7 ok / 1 fail
over 38 sets.** The comparison that matters is flat BC_klein — the strongest single
arm — at 2.000 generations for 28 perfect / 6 ok / **4 fail**. Same cost, a quarter
of the failures.

A cheaper configuration exists and is a legitimate choice: `garment == FAIL` alone
gives **1.737 generations, 31 / 5 / 2** — cheaper than BC_klein *and* better. The
safe configuration above trades +0.37 generations and one perfect for one fewer
shipped failure. That is a product judgement, not a data one; it is set to safe here
because a shipped failure is the worst outcome the system can produce.

| configuration | gen/req | perfect | ok | fail |
|---|---|---|---|---|
| flat BC_klein, no harness | 2.000 | 28 | 6 | 4 |
| harness, cheap gate | 1.737 | 31 | 5 | 2 |
| **harness, safe gate (shipped)** | **2.105** | **30** | 7 | **1** |
| *oracle gate, upper bound* | *1.789* | *34* | *4* | *0* |

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

### VLM-A — the escalation trigger

**Model: Qwen3-VL-8B-Instruct.** Two prompts, one model, one image pair each.
Escalate if **either** fires:

| prompt | sees | escalates when |
|---|---|---|
| `tryon` | the output | verdict is not `PERFECT` |
| `garment` | **garment reference + output** | verdict is `FAIL` |

**VLM-A must see the garment reference.** This is the single most important thing the
evaluation established, and it contradicts the original design. Measured over 114
human-tiered outputs, five prompt formulations:

| prompt | sees | fires | accuracy | catches `fail` |
|---|---|---|---|---|
| `artefact` | output | **0** | 62.3% | **0%** |
| `usable` | output | 4 | 62.3% | 13% |
| `tryon` | output | 2 | 62.3% | 7% |
| **`garment`** | **ref + output** | 35 | **70.2%** | **53%** |
| `transfer` | person + ref + output | 8 | 64.0% | 20% |
| *accept everything* | — | 0 | *62.3%* | 0% |

**Only `garment` beats the do-nothing baseline, and it is the only prompt with a
reference image.** Three of the five sit exactly on the baseline.

**Do not ask about artefacts.** The `artefact` prompt returned `CLEAN` on all 114
outputs — including every frame the reviewer marked `fail`. It never fired once. The
reason is structural and worth stating plainly: **these failures are not artefacts.**
They are competent photographs of the wrong thing — a plausible but different garment,
or the input returned unchanged. Nothing in the pixels looks broken.

**More context is not better.** `transfer`, which sees person *and* reference *and*
output, scored *below* `garment`. At 8B, three images appear to dilute attention. Two
is the working number.

### VLM-B — do not build it

A pairwise "which of these two is better" call was built and measured. **It agreed
with itself on only 34% of pairs when the two images were swapped** — worse than
chance, so it reads position rather than content. On the pairs that actually escalate
it chose the arm that had already failed 2 times in 5.

**Always take QX after an escalation.** That rule scores 5/5 on the same set.

A better mechanism exists if this is ever revisited: score each candidate
*independently* and compare the scores, which has no position to be biased by. It
reached 4/5 — better than pairwise, still worse than the trivial rule, on n = 5.

### The crash guard earns its place on evidence, not just robustness

The no-op check catches `HD_p023`, where the model returned the person essentially
unchanged. That output is a clean, plausible photograph, so **every output-only prompt
correctly calls it clean.** Only a comparison against the person input reveals it.

The deterministic checks and the VLM are therefore **complementary, not competing**:
the VLM catches incoherence it can see, the no-op check catches the coherent-but-wrong
case it cannot.

### The economics

| | cost |
|---|---|
| one VLM call | **$0.0003** (measured: $0.000124 on a hosted 8B) |
| one generation | $0.015 |
| one *wasted* escalation | **$0.030** |

Two prompts per request is **~0.04 generation-equivalents**, roughly 2% of pipeline
cost. Since a wrong escalation costs 2 generations, **the gate can be wrong 50 times
for every generation it saves and still break even.** Accuracy is not what is being
bought; a cheap opinion is.

**Serving:** one 24 GB GPU (L4 / A10G / 4090) at ~1–2 calls/sec covers 1M
requests/month with headroom, at roughly $300–600/month — about $0.0003 per call, which
is what the argument above assumes.

## 7. Stage 5 — realism, conditional

**SeedVR2, ×2 upscale, `noise_scale = 0`.** Note `0`, not fal's default `0.1`: the
default is measurably worse on both fidelity (4.88 vs 5.00) and identity (0.892 vs
0.943).

SeedVR2 accepts **no text input**. It restores and upscales; it does not repair
artefacts and it does not remove gloss.

**The resolution increase is a clear, visible improvement** — 832×1248 → 1664×2496 —
which is why the stage is in the pipeline. But run unconditionally it cost identity on
7 of 38 frames, with a worst case of **0.772**, inside the range that got Z-Image Turbo
eliminated in v2.1. So it is gated on both sides:

```
if hf_before(frame) >= 2.5:              # already sharp: nothing to restore
    skip
else:
    out = seedvr2(frame, factor=2, noise_scale=0)
    if identity_cos(out, frame) < 0.90:  # it damaged the face
        keep the original                # free, deterministic, CPU
    else:
        ship out
```

| policy | calls | mean identity | worst | below 0.90 | sharpening kept |
|---|---|---|---|---|---|
| always run | 38/38 | 0.933 | 0.772 | **7** | 1.121 |
| **skip-if-sharp + revert (shipped)** | **29/38** | **0.971** | **0.922** | **0** | **1.110** |

**24% fewer calls, no frame below 0.90 identity, and essentially all of the benefit.**

**Why a post-hoc check works.** The frames that lose identity are the frames SeedVR2
*failed to sharpen* — where `hf_ratio < 1.0`, mean identity is 0.891 against 0.941
elsewhere, and `corr(hf_ratio, identity) = +0.512`. One signal covers both problems:
when the pass works it is safe, and when it fails it announces itself.

**Revert, never retry.** SeedVR2 takes a seed but accepts no prompt, and the failure is
a property of the frame rather than the roll — the same reasoning that killed reseeding
at the escalation stage. Falling back to the original frame is the correct response.

Both checks are free: one high-frequency measure and one AuraFace cosine, both already
in the pipeline. Full detail and the policy comparison:
[v2.4/RESULTS.md](v2.4/RESULTS.md).

## 8. What not to build

Each of these was built or costed and rejected on measurement. They will look like good
ideas again.

| Do not build | Why |
|---|---|
| **A deterministic quality gate** | Measured **AUC 0.506** against the reviewer over 114 blind cells. Best threshold agreed on 71.1% of cells; accepting every frame unchecked agrees on 71.9%. Not a calibration problem — pixel statistics cannot see semantic failure |
| **Retry with a fresh seed** | Failure is a property of the **garment**, not the roll: a damaged reference failed on all three people it was paired with. A retry reproduces it. Escalate mechanism, never reseed |
| **A third candidate on escalation** | +0.21 gen/request, zero quality gain. Shares the failure mode that just fired |
| **An off-the-shelf AI-artefact detector** | They answer *"was this generated?"* — 100% of these frames were. Such a detector fires on everything and discriminates nothing |
| **A VLM asked about artefacts** | Measured: `CLEAN` on all 114 outputs, never fired. The failures are not artefacts |
| **A pairwise VLM selection call** | 34% self-consistency under image swap; picked the already-failed arm 2 of 5 times. Always take QX |
| **A VLM-A that sees only the output** | Every output-only prompt sat on the do-nothing baseline. It needs the garment reference |
| **A VLM router for hair** | The deterministic measure *is* the quantity, not a proxy. A perfect router would save 0.053 gen/request; a VLM router costs 0.020. Ceiling ≈ 2% |
| **Z-Image Turbo, anywhere** | Fails the damage-floor test at every strength — restructures faces on **real photographs that needed no repair**. AuraFace drops to 0.72 on a real photo |
| **A whole-image artefact pass** | The VLM `artifact_fix` criterion scored **exactly 3.00 — no change — in 14 of 14 config-batches** |
| **A grey mannequin form, or a non-white ground** | Both built, neither ever triggered. The pale-garment case rests on one observed reference |
| **A closed-model VLM or editor** | Deploy constraint, and cost |

---

## 9. What is unproven

State these wherever the numbers above are quoted.

1. **VLM-A is measured but at 4-bit, and the model hedges.** 331 of 570 verdicts were
   `OK`; only 49 were `FAIL`, which is what caps recall at 51%. Two untried levers,
   both plausibly worth several points: a **binary forced choice** with no middle
   option, and **fp16 instead of 4-bit**. Read the numbers as *Qwen3-VL-8B at 4-bit
   with these prompts*, not as a ceiling on open VLMs.
2. **The 14% threshold is fitted** on these 38 sets. AUC 0.862 is the honest figure;
   the cut-point needs recomputing over all 48 references, held out.
3. **The user-specification branch has no evidence at all.** Nothing in the test set
   carries one. QX's single-failure profile makes it a safe default; that is reasoning.
4. **The human parser's licence is unverified**, and head detection depends on it. It
   is fine for measurement and **not cleared for the deploy path**.
5. **The realism thresholds (2.5 and 0.90) are fitted** on 38 frames. The mechanism —
   `hf_ratio < 1` predicts identity damage — is the transferable part; the cut-points
   are not. The identity figure is also confounded by comparing a frame against a 2×
   upscale of itself, so some of the measured drop is resampling.
6. **n = 38, one reviewer, one seed, unblinded.**
7. **Every number in this document is a fal number.** Nothing has been verified on
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
| 7 | VLM-A, two prompts | reproduces 70.2% on `garment` against a 62.3% baseline |
| 8 | escalation wiring, always to QX | 2.105 gen/request, 30 / 7 / 1 |
| 9 | SeedVR2 pass, conditional | 29 of 38 frames run; no delivered frame below 0.90 identity; `noise_scale` is `0` |
| 10 | **Self-hosted parity** | every number above, on downloaded weights |

**Judge by eye at every step.** Three separate times in this project an instrument said
the opposite of the truth: no-op outputs scored perfectly on identity; a "garment lost"
metric collapsed to zero by construction; furniture sat in every crop undetected. The
pipeline was debugged by looking, not by measuring.
