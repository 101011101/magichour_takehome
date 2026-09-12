# v3.8 — SOLUTION

**Locked 2026-09-10.** The architecture, and why each stage is there. Per
[SCHEMA.md](../SCHEMA.md) this document carries the solution and links to the evidence rather
than restating it: the argument is in [EXPERIMENT.md](EXPERIMENT.md), the cases and numbers in
[RESULTS.md](RESULTS.md).

---

## 1. The architecture

```
garment photograph ──► klein bald pass                              CALL 1
                         BALD_PROMPT, the wearer's hair removed
                         a small in-distribution edit - the only
                         generative step that touches the source
                              │
                              ▼
                       V2 cropper, head subtracted                  NO MODEL
                         BiRefNet_lite matte x human-parser classes
                         cranium → white, subject bbox on white
                         DETERMINISTIC and SUBTRACTIVE: it can only
                         remove, so the garment pixels that leave
                         this stage are the photograph's
                              │
                              ▼
                       THE REFERENCE (image 2)
                              │
person photograph ────────────┴──► klein edit — ER                  CALL 2
                                     "Replace the clothing in image 1
                                      with the clothing in image 2.
                                      Keep the person's face, identity,
                                      body and the background exactly
                                      as they are."
                                     canvas: area 2²⁰, aspect kept,
                                     each side floored to 32
                                              │
                                              ▼
                                        TRY-ON (~1 MP)
```

**Two model calls, which is the production budget**, and both are to the same model. Call 1 is
per **garment** and amortises across every customer who tries it; call 2 is per **try-on**.

The single change v3.8 makes to the incumbent is the verb in call 2's first sentence. Nothing
else in the diagram is new.

## 2. Why each stage is there

| stage | why it exists | what happens without it |
|---|---|---|
| **bald pass** | the wearer's hair is the one thing a matte cannot separate from a collar; a small edit to the *head* removes it without touching the garment | hair over the shoulders is matted as garment and transferred onto the target ([v2 PHEAD](../../v2/v2.2/RESULTS.md), 63%/21% against `BC`'s 74%/5%) |
| **V2 cropper, head subtracted** | identity removal that **cannot invent**. A matte multiplies; it has no capacity to add a placket, change a hem or drop a piece | every generative alternative pays the regeneration tax: the v3.4 lock fails **9.2%** against this stage's **4.8%** on the same 600 cells ([v3.5 §4](../v3.5/RESULTS.md)) |
| **call 2, `ER`** | *replace…with* names the removal as well as the putting-on; *dress…in* names only the second half | the wearer's own clothing survives underneath the new garment — the class `ER` repairs on **32%** of the incumbent's failures ([RESULTS §3](RESULTS.md)) |
| **the hold clause** | *keep the face, identity, body and background* — tested by deletion, not assumed | `ER2` drops it and breaks **15 cells `ER` keeps clean against 2 the other way** ([EXPERIMENT link 8](EXPERIMENT.md)) |
| **1 MP canvas** | the distilled schedule branches at 4,300 tokens; 2²⁰ px = 4,096 keeps every call on the schedule the model was trained for | above the branch the model is on a schedule it was not distilled for ([v3.4 SOLUTION](../v3.4/SOLUTION.md)) |

## 3. The prompts, as sent

```
BALD_PROMPT   Make this person completely bald. Remove all hair from the head and any
              hair falling over the shoulders, chest or back, and show the scalp. Keep
              the clothing, the body, the pose and the background exactly as they are.

ER            Replace the clothing in image 1 with the clothing in image 2. Keep the
              person's face, identity, body and the background exactly as they are.
```

`v3lib.BALD_PROMPT` unchanged from V2; `ER` is `v3lib.EDIT_PROMPT` with its first verb
rewritten. Both are two sentences. **Nothing longer survived testing** — see
[EXPERIMENT links 3, 4, 8](EXPERIMENT.md).

## 4. What must be held fixed

These are load-bearing. Each has a measurement behind it, not a preference.

| | rule | why |
|---|---|---|
| **canvas** | ≤ 1 MP (2²⁰ px = 4,096 tokens) on **every** klein call | a **cliff**, not a dial: `compute_empirical_mu` branches at 4,300 tokens ([v3.4](../v3.4/SOLUTION.md)) |
| **call-1 canvas** | the crop's own size, capped 1 MP, **never upscaled**, sides floored to 16 | inflated inputs lose framing (v3.4 links F, G) |
| **call-2 canvas** | area 1024², aspect preserved, up **or** down, sides floored to 32 | fal's rule, reproduced by not passing `image_size`; measured off fal 20/20 |
| **upscaling** | never inside a klein call | rendering above its conditioning makes klein **invent structure** — the p004 placket at ×2.67 ([v3.4 §7.1](../v3.4/RESULTS.md)) |
| **sampler** | 4 steps, `guidance_scale` 0.0, bfloat16 | the distilled schedule |
| **seed** | `torch.Generator("cpu")` | a CUDA generator does not reproduce |
| **weights** | `black-forest-labs/FLUX.2-klein-4B`, revision pinned, **no LoRAs** | unpinned `from_pretrained` lets a future revision change outputs silently; LoRAs change them materially and no number here transfers to a LoRA'd stack |
| **host** | self-hosted; fal and the A100 are **not** interchangeable | same prompt, seed and canvas rule, different failures ([EXPERIMENT link 1](EXPERIMENT.md)) |

`Photoroom/FLUX.2-klein-4b-fp8-diffusers/transformer_bf16` is an acceptable substitute for the
transformer specifically — measured, no outcome changes on 74 cells — but its repo carries a
transformer and nothing else, so the text encoder, VAE, scheduler and tokenizer must still come
from BFL. See [RESULTS §10](RESULTS.md#10-the-transformer-swap-2026-09-10).

> **Post-lock note — 2026-09-11 (Ray).** Added after the lock; nothing above it is changed.
> **Production uses the Photoroom `transformer_bf16`**
> (`Photoroom/FLUX.2-klein-4b-fp8-diffusers` @ `408c457f3589e17a1be1dae5bf0dcaf09cd4985f`),
> with the text encoder, VAE, scheduler and tokenizer from
> `black-forest-labs/FLUX.2-klein-4B` @ `e7b7dc27f91deacad38e78976d1f2b499d76a294`. BFL's own
> transformer is kept for one purpose only: parity against the archive, which was made on it
> ([BUILD §3.3, §7.3 T2](BUILD.md)). The production rate on the Photoroom transformer comes
> from the package's 600-cell sweep (BUILD T4).

## 5. What it costs

| | |
|---|---|
| call 2 | 2.28 s median on an A100 |
| a 600-cell arm | CAD 0.273 self-hosted — USD 9.00 for the same calls on fal |
| **per 1000 finished images**, references already built | **CAD 0.45** — USD 15.00 on fal |
| per 1000 including reference build, at this fold's ratio | CAD 0.54 (GPU crops) / 0.78 (CPU crops) |

`ER` costs the same as the incumbent to three decimal places. The verb is free.

## 6. What it does not fix

Stated so it is not discovered later as a surprise.

- **Two thirds of the remaining failures are reference-side.** On 34 of the incumbent's 50
  failures `ER` has the same defect. The fault is upstream of call 2 — the crop, the pair, the
  photograph — and no wording reaches it.
- **Crossed arms.** A matte cannot know folded arms are not part of the garment's shape, so
  call 2 receives a jacket with arms baked into its silhouette and duplicates them. The fix —
  unfolding them in call 1 — is a full-frame regeneration, which costs more than the defect.
- **The wearer's own accessories.** Handbags and worn-under shorts persist under every
  reference arm identically. Person-side, untouched by anything in v3.8.
- **`BC` cannot re-pose**, and this fold does not punish it: the 200 pairs are mostly
  front-facing wearers. A catalogue of awkward source photographs would move the number.
- **The reference is not scaled to the canvas.** It arrives at 0.42 MP mean against a 1 MP
  output. `VEi` SRs its reference for this reason and the dwarfism fix is real — but the same
  step carries a measured hands and cleanliness cost (v3.4 §9.1), and it has never been tested
  on a matte-derived reference. **A trade to be priced, not a fix.**

## 7. What the evidence recommends next

**A seed retry, not a prompt.** Both arms were run at three seeds, so the record prices it:
given a cell fails, another seed of the same pair passes **72%** of the time on `ER`, which
takes roughly **6.2% → 1.7%** for about 6% more calls — only rejected images are redrawn.

Its missing piece is a **rejector**. The v3.8 VLM judge is a first attempt and is not one: its
artifact flag fires on 45% of cells a human passed. Its limb flag (14.8× lift) and phasing
(2.7×) are the signals to build on, and it must be measured against the blind human marks
before it is trusted to spend calls.

Until that exists, the retry figures are a property of the model, not a shipped number.
