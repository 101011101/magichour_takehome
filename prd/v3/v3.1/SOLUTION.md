# v3.1 — SOLUTION

**Locked 2026-08-28.** The architecture this investigation yielded, and why each stage is
there. Per [SCHEMA.md](../SCHEMA.md) this document carries the solution and links to the
evidence rather than restating it: the argument is in [EXPERIMENT.md](EXPERIMENT.md), the
cases and numbers in [RESULTS.md](RESULTS.md).

---

## 1. The architecture

```
person photograph ──┬─────────────────────────────────────────────────────────┐
                    │                                                          │
                    └─► MediaPipe Selfie Multiclass                            │
                          FACE mask → median L*a*b* → nearest ladder step       │
                          → COLOUR WORD                            149 ms      │
                                                                                │
garment photograph ─┬─► BiRefNet_lite @1024²                                    │
                    │     subject matte → bbox + white ground, HEAD KEPT        │
                    │     → THE CROP                                            │
                    │                                                           │
                    └─► MediaPipe Pose (on the crop)                            │
                          joints in frame → FRAMING CATEGORY          36 ms     │
                          → FRAME_CLAUSE[category] → EXTENT + POSE              │
                                        │                                       │
        PREFIX + <colour word> + SUFFIX + <extent + pose clause>                │
                                        │                                       │
                 Qwen-Image-Edit-2511 ──┴──► MANNEQUIN REFERENCE      CALL 1    │
                                        │                                       │
                          FLUX.2 klein ─┴───────────────────────────────────────┘
                                        └──► TRY-ON                   CALL 2
```

**Two model calls, which is the production budget.** Everything left of call 1 is CPU and
runs in under 200 ms except the matte.

## 2. Why each stage is there

| stage | why it exists | what happens without it |
|---|---|---|
| **the crop** | the reference is what the edit attends to; a raw photograph spends the token budget on a room | subject fill as low as 17%, and a landscape frame produces **two mannequins** ([§3c.12](RESULTS.md#3c12-aspect-ratio-causes-the-duplication-and-padding-fixes-it)) |
| **head kept** | the hair is context for how the garment sits | removing it loses that context and scores worse than keeping it ([§3c.19](RESULTS.md#3c19-the-crop-quality-ladder-measured-cost-and-no-middle-rung)) |
| **BiRefNet, not the 256² map** | the cheap matte does not round the silhouette, it **removes garment** | a segmentation error, worse than the edge defect V2 rejected it for |
| **colour word** | a white form under a pale garment is a low-amplitude boundary — the mechanism that made `HD_p023` return its input | the garment loses its outline ([§3c.28](RESULTS.md#3c28-the-colour-word-does-not-only-set-colour-it-decides-what-kind-of-object-is-rendered)) |
| **"skin"-bound colour** | a bare chromatic adjective applies to the whole picture | `"tan"` turned a white shirt into a **tan polo** ([§3c.3](RESULTS.md#3c3-a-chromatic-mannequin-colour-bleeds-into-the-garment-p72-fails)) |
| **framing category** | a whole-body instruction against a waist-up photograph is satisfied by inventing legs | trousers appear under a portrait ([§3b.2](RESULTS.md#3b2-the-mannequin-invents-garments-the-photograph-does-not-contain)) |
| **one table for extent + pose** | two sentences about the same fact disagreed, and the pose one won | a waist-up crop reopened to full length ([§3c.30](RESULTS.md#3c30-a-pose-word-fixes-the-stride-and-quietly-overrides-the-extent-clause)) |

## 3. The rules that generalise

Four findings that outlive this architecture and should govern any prompt written in V3.

1. **The model does exactly what the words permit.** `"the garment"` permitted one
   garment; `"bag, belt, hat"` permitted invention; `"tan"` permitted a tan picture;
   `"light brown skin"` permitted a **person**, and people have strides. Every prompt
   failure here was a permission wider than the intent.
2. **Tell the model what is there; do not tell it what to omit.** An instruction grounded
   in the image works. An enumeration of what to include gets produced whether or not it
   exists.
3. **Never name a body part the crop excludes.** The rule that makes dynamic prompting
   consistent, and the reason the pose clause changes with the category.
4. **Compound prompts are paid for in fidelity, not compliance** — which is the axis a
   try-on is judged on ([INVESTIGATION.md §4.2](../INVESTIGATION.md#42-compound-instructions-cost-fidelity-not-compliance-and-that-is-our-result)).

## 4. Cost

| | |
|---|---|
| model calls | **2** — one extraction, one edit |
| CPU per pair | ~190 ms of readers, plus one matte per garment reference |
| the matte | **~49 s on a 4-core CPU, milliseconds on a GPU.** The deployment target runs klein and therefore has one ([§3c.20](RESULTS.md#3c20-the-99-seconds-is-a-laptop-artefact-and-v2s-19-s-figure-is-wrong)) |
| extraction cardinality | **per pair, not per reference** — the colour word depends on who is being dressed |

That last line is the architecture's one real cost. QX extracts once per garment; MQ
extracts once per *pairing*. At 200 pairs over 56 references that is 200 Qwen calls
instead of 56.

## 5. What is locked, and what the evidence actually covers

**Locked:** the stages above, the ten-step tone ladder, `FRAME_CLAUSE`, the A4 crop, and
both prompts.

**The scored evidence does not cover the locked configuration.** The 28-pair comparison —
**MQ 92% perfect against BC 79% and QX 58%** — was produced **before dynamic prompting
existed**, by a variant with no pose clause. Rule 1 of the schema says a number appears in
exactly one place and is cited everywhere else; this is that number's caveat and it
travels with it.

Two further limits on that comparison, both stated in
[§3c.22](RESULTS.md#3c22-what-this-comparison-can-and-cannot-claim):

- **It is confounded.** MQ ran on the crop, BC and QX ran raw — two differences at once,
  so a win belongs to the arm and not to the mannequin prompt.
- **Head-to-head, MQ beats BC on 3 pairs and loses on 2, with 19 ties.** The 13-point rate
  gap rests on a net of one pair. Against QX the margin is real: 9 better, 1 worse.

**MQ has no `ok` verdicts at all** — it is right or it is broken, where BC degrades through
five `ok`s and never fails. **BC's floor is higher; MQ's ceiling is higher.** That is a
production tradeoff, not a ranking.

## 6. Known defects carried into the lock

Locked does not mean correct.

**0. It uses two models, and V3's constraint is one.** The brief is explicit — *"One base
model on the server: FLUX.2 klein 4B distilled. Nothing else loaded"* — and states the
central problem as getting the regeneration property *"inside two klein calls, on one
model"* ([README §2, §4](../README.md)). **This architecture uses Qwen-Image-Edit-2511 for
call 1 and klein for call 2.** Resident weights are ~55 GB + ~16 GB against ~16 GB for
klein alone: an H100-80 or two A100-40s per worker, or a 40 GB model load on every
request.

**So the architecture below is locked as a measured design, not as a deployable one.**

The obvious repair has never been tried: **klein with the mannequin prompt.** V2 measured
klein as an extractor, but with the old `p1` "isolated on white" wording and before any of
v3.1's work — and on those numbers klein is **better than Qwen on hue (21.3° against
28.6°) and far better on texture retention (×1.01 against ×0.51)**, worse only on
lightness, which is the axis the colour word now controls
([v3.0/RESULTS §4.2](../v3.0/RESULTS.md#42-klein-as-an-extractor-is-already-measured)).
That is a promising starting point sitting unused. **8 references, ~$0.24, and it decides
whether v3.1 ships as one model or two.**

1. **The tone ladder is not calibrated to what the model renders.** `dark beige skin` came
   back **23 L\* points darker** than its own swatch, and not uniformly — so no offset
   fixes it ([§3c.25](RESULTS.md#3c25-p019s-colour-the-read-is-right-and-the-render-is-not)).
2. **A half-lit face defeats the median.** L\* spanning 20 to 72 gives a median that
   represents neither mode.
3. **`g011`'s texture merge is parked.** The defect fires whenever the target garment
   **exposes a region the source photograph covered** — it is a property of the *pairing*,
   and **nothing in the pipeline detects it** ([§3c.31](RESULTS.md#3c31-g011s-cooked-texture-it-is-neither-the-person-nor-the-prompt)).
4. **Accessories drop inconsistently**, by decision.
5. **Call 2 has never been varied.** Every prompt experiment was on call 1; the klein edit
   prompt is unchanged since V2 and is the largest untouched surface left.
6. **n = 28, one seed, one reviewer, unblinded.**

## 7. Where the implementation is

| | |
|---|---|
| pipeline, self-contained | `v3/colab/lib/v3lib.py` |
| orchestrator, resumable | `v3/colab/lib/run_all.py` |
| Colab notebook | `v3/colab/v31_full_run.ipynb` |
| 200-pair matrix | `v3/testsets/v3_full_matrix.csv` |
| bundle | `v3_colab_bundle.zip` |
| repo-side runners | `v3/build/run_mq.py` — **still uses the pre-dynamic clause; the Colab library is the current one** |
