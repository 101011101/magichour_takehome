# PROD — open questions

Each question states what the record already says, where that evidence is, and what would
close it. A closed question moves to the ledger in [`TODO.md`](TODO.md) with its evidence.

---

## Q1. Call 2 scales image 1 up or down to 1 MP — is that the right play?

**Raised by Ray, 2026-09-11.**

**What the record says.** The rule is fal's canvas: scale the person photo to area 2²⁰ px,
aspect kept, up or down, sides floored to 32 (`klein_local._size_fal`). It was adopted in
v3.4 link D. The two halves of the rule rest on different evidence:

- **Down is required.** `compute_empirical_mu` branches at 4,300 tokens; above it the
  distilled model runs a schedule its 4 steps were not trained for. Under the previous rule
  (≤1.15 MP, never upscaled) **38 of 200** iron-man call-2 outputs crossed the branch, and
  those pairs had a failing cell **21%** of the time against **14%** below it — suggestive,
  n = 38. Code-verified in both diffusers and BFL.
  → `prd/v3/v3.4/RESULTS.md` §4.2
- **Up was adopted to match fal's token count.** The old rule rendered most people on
  2,300–4,000 tokens where fal renders ~4,000 every time. The supporting evidence is
  indirect: a blind judge gave fal a small identity/scene edge (+0.16 / +0.17, confidence
  intervals touching zero) and no garment edge.
  → `prd/v3/v3.4/RESULTS.md` §4.2, §4.4
- **Link D measured the rule** on the V-arm failure set: parity or better against the fal
  benchmark on **85 of 93** cells. One regression — the `g027+p003` dwarfism — was
  diagnosed as a framing-retention failure that the old canvas has too. That pair is the
  fold's only ×1.3 upscale.
  → `prd/v3/v3.4/RESULTS.md` §5, §6
- **For `BC` and `ER` the rule was never compared with anything.** Iron man 2 put `BC` on it
  by the fairness rule (the canvas is a property of call 2, not of the arm), and `ER`
  inherited it.
  → `prd/v3/v3.4/SOLUTION.md` §3b, §5

**Why 1.15 MP, and not 1 MP.** The 1.15 MP figure was never argued for. It first appears as
`MAXPIX = 1_150_000` in the V3.0 runner (commit `7c1e520`, 2026-08-27) with no comment, and
every later V3 run inherited it (`v3lib.MAXPIX`). The intent on record is a **~1 MP
normalisation to match fal**, after V2 found that generating at 3.45 MP self-hosted "cost 32%
detail and took 128s against 39s" while fal silently normalises to ~832×1248
(`prd/v3/README.md` §6). **[inferred]** 1.15 reads as "about 1 MP, with headroom"; at the time
nobody knew klein's schedule has a cliff. v3.4 found it from source: fal's canvas is exactly
area 2²⁰, and 1.15 MP admits up to ~4,492 tokens — over `compute_empirical_mu`'s 4,300-token
branch — so it was **retired as a canvas limit** ("1.15 MP was 5% over the cliff",
`prd/v3/v3.4/SOLUTION.md` §5 rule 1; `prd/v3/v3.4/RESULTS.md` §4.2). It survives only as the
input pre-bound in `v3lib.normalise`; no klein canvas exceeds 2²⁰ px.

**So:** no finding says the rule is wrong. The "down" half is load-bearing; the "up" half
has never been isolated, and never on `ER`.

**MEASURED 2026-09-12 — v3.9, and it did not close the question.**
`SCALE` against `NOSCALE` (own size, never upscaled), everything bounded to 1 MP, 68 cells,
blind and paired. **`NOSCALE` won 22 : 8 on 30 discordant cells, two-sided exact p = 0.016** —
the shipped rule lost. But the result lives almost entirely in the failure group: `fail`
**20 : 3** (p = 0.0005), `clean` **2 : 5** the other way. v3.8's adoption rule requires a win
on `fail` *without* a loss on `clean`, and the clean side is unresolved rather than won. The
effect is also not ordered by how much upscaling a cell had — weakest where the upscale is
largest, the opposite of the mechanism it needs.
→ `prd/v3/v3.9/RESULTS.md` §3, `prd/v3/v3.9/EXPERIMENT.md` link 1

**Free finding:** not upscaling is **~17% faster per try-on** (1.92 s against 2.31 s), being
the arithmetic of a 0.70× canvas.

**Still open, and what would close it.** The set is **57% failures by construction** against
the fold's ~6%, judged by one reviewer, on a page that equalises display width — which removes
pixel count as a cue but not softness as an appearance. The same paired comparison
**fold-wide over all 200 pairs**, ideally with a second reviewer on the discordant cells, is
what would license changing the shipped rule. Until then the rule of record stands.

**Why 1.15 MP, and not 1 MP** — see the paragraph above; that half is settled.

**Interacts with Q3.**

---

## Q2. One crop or two? — **(a) CLOSED 2026-09-12, (b) still open**

**Raised by Ray, 2026-09-11**, and clarified by him on 2026-09-12: *"when I say double crop I
mean crop the person + clothes then run through the bald pipeline"* — reading (a).

**(a) ANSWERED: no difference. The second crop is not adopted.** `CROP2` (A4 crop → bald pass
on the crop → the same head-subtracting crop) against the single-crop baseline, 93 cells,
blind and paired: **84 same, 3 : 6 discordant, p = 0.51**, and **not one of the 40 clean cells
moved**. Reference sizes bear out the prior — 0.392 MP mean for one crop against 0.391 MP for
two. The one thing it buys is a **1.9× faster bald pass** (0.85 s against 1.61 s), a cost
saving on the cached per-garment half, available later on its own merits.
→ `prd/v3/v3.9/RESULTS.md` §4, `prd/v3/v3.9/EXPERIMENT.md` link 2

**The original (a) framing, for the record** — BiRefNet crop → bald pass → head-subtracting crop.
The record never did this: the bald pass always runs on the uncropped, normalised photo
(`run_ironman.py:249`), and the one crop comes after it. The nearest arm, `BCA4`
(bald → A4 crop, head kept), answers a different question (`prd/v3/v3.3/RESULTS.md` §13–14).
**[inferred]** A pre-crop would likely change little: the call-1 canvas is never upscaled,
so a tighter crop gives klein fewer tokens rather than more detail, and the reference's
garment pixels come from the post-bald crop either way. Untested.

**(b) One reference per garment, or a fresh one per request.** Every number of record uses
one reference per garment (call 1 at seed 46), with only call 2's seed varying. On 34 of
`BC`'s 50 failures `ER` had the same defect — reference-side — and 1 pair failed at every
seed (`prd/v3/v3.8/RESULTS.md` §3, §6). Whether a different bald seed rescues those is
unmeasured.
**Test:** rebuild the references of the 14 pairs `ER` failed at seeds 47 and 48, re-run
call 2, and mark them paired. Minutes on an A100. If it rescues, "re-prepare the garment"
becomes a second-level redraw.

---

## Q3. Runbo's max-resolution setting against the 1 MP rule

**Raised by Runbo's brief, 2026-09-11** ([`TODO.md`](TODO.md)). He asks for a setting that
caps the larger of height and width. The company's existing klein ticket uses `MAX_RES` the
same way, with 1080p or 2K as the maximum ([`TICKET_TEMPLATE.md`](TICKET_TEMPLATE.md)).

**The constraint.** `ER`'s canvas is an *area* rule, and it cannot exceed 2²⁰ px without
crossing the schedule branch (Q1). So a max-resolution setting can only **lower** the
output:

- canvas = the 1 MP rule; then, if its longer side exceeds `MAX_RES`, scale down to it
  (floor 32). `MAX_RES = None` → the rule of record.
- Example: a 3:4 photo renders at 864×1152; `MAX_RES = 1024` gives 768×1024 (0.75 MP) —
  below the measured canvas, in the regime the old rule ran in. Quality there is untested
  on `ER`.
- Values above the rule's own longer side — at most 1344, for 9:16 — have no effect.

**The ticket must say the maximum is ~1 MP, not 1080p.** If 1080p output is a product
requirement, the path consistent with the record is to generate at 1 MP and upscale the
finished image algorithmically (realesr-general-x4v3 is in the repo) — untested for
try-on.

**Decision needed:** Ray and Runbo — the setting's semantics, its default, and whether
output upscaling is wanted.

---

## Q4. BiRefNet and the parser on the GPU — **partly answered; parity still open**

**Settled 2026-09-12 (Ray, Colab A100).** BiRefNet_lite does run on the GPU, and the wheel
is the whole trick: the newest `onnxruntime-gpu` failed the probe at the `dlopen` step, and
**`onnxruntime-gpu==1.22.0`** was the first whose CUDA provider actually loaded. With it,
`providers` reported `['CUDAExecutionProvider', 'CPUExecutionProvider']` and a
1×3×1024×1024 input ran in **0.139 s against 7.798 s on CPU — 56×** (warm; GPU averaged
over three runs, CPU over one). Both production notebooks now try `==1.22.0` first and keep
the descending walk as a fallback.
→ `prd/v3/v3.8/BUILD.md` §5; `vp/tryon_er.ipynb` §1; `vp/gpu_check.ipynb` §3

**It also settles what the v3.9 crops were.** That run's `headcrop` median of 16.8 s sits
next to v3.5's 15.8 s CPU figure while BiRefNet on GPU is 0.139 s — so the v3.9 inquiry
crops ran **on CPU**, as suspected.
→ `prd/v3/v3.9/RESULTS.md` §6

**What is still open, and it is the part that gates production:**

1. **The SCHP parser is untimed on GPU.** Only BiRefNet was measured.
2. **The end-to-end crop on GPU is unmeasured.** `head_subtract` is not one ONNX call —
   MediaPipe Selfie and Pose stay on CPU by design, and `refine_band`'s guided filter is
   OpenCV on CPU. None of the 56× carries over to the crop as a whole, so the ticket's crop
   time stays a placeholder.
3. **Crop parity is unproven.** Every reference of record was built with **CPU** ONNX, and
   GPU crops have still never been compared with them. **Closes with** BUILD §7.3 **T1**
   (per-reference MAD ≤ 4.0, shapes within 8 px). If it fails, crops stay on CPU: they run
   once per garment and are cached, so they are off the try-on's latency path.
→ `prd/v3/v3.8/BUILD.md` §5, §7.3; `prd/v3/v3.5/RESULTS.md` §3; `prd/v3/v3.4/RESULTS.md` §10

**The re-run must write its verdict to a file.** The 2026-09-12 attempt inside
`vp/inquiry_confirmation.ipynb` printed to the notebook and the session was released, so
the bundle carries no provider record, no timing and no parity number. It is cheap — a few
crops, no generation.

## Q5. Peak VRAM, and which GPUs

Never measured. Weights are ~16.5 GB resident. The company's klein ticket reports 18.3 GB
on G4 for its klein script; this pipeline adds a second conditioning image and ~0.5 GB of
ONNX. Can it partition the way that ticket describes? A different GPU class is also a
different draw, so its rates need their own sweep.
**Closes with** T3 on the target GPU, then T4 on it.

## Q6. What is handed over, and what else gets built

Runbo's brief and the three example tickets suggest the handoff is **a clean Colab plus a
Linear ticket**, with engineering building the product around it. If so, Docker, serving,
the reference cache and the redraw API belong to them, and the ticket has to carry
everything they need: weights, revisions, the cache, the seed, timings. If we own the
backend, the work adds a container (CUDA 12 base, pinned wheels, a matched
`onnxruntime-gpu`), weights on local disk, a reference store, the request/redraw API, seed
logging and a warm-up. **[CONFIRM with Runbo.]**
→ `prd/v3/v3.8/BUILD.md` §6, §7.2

## Q7. Which garment photos does the product accept? — **ANSWERED 2026-09-12**

All 56 garments the system was measured on are photographs of the garment **being worn**
(`v3/colab/matrix.csv`). Flat-lay, product and mannequin photos were untested on this path —
the cropper has a product route, but `ER`'s head-subtracting path does not use it.

**Product shots work.** 10 product-only garments (flat-lay and ghost-mannequin) × 3 people ×
2 seeds, production path against the v3.0 no-bald product route: **59 of 60 cards marked
same**, the single discordant card favouring production. The pipeline does not break on a
garment photograph with no person in it.
→ `prd/v3/v3.9/RESULTS.md` §5, `prd/v3/v3.9/EXPERIMENT.md` link 3

**With a caveat that is a cost question, not a quality one.** The head-finder fired on **10 of
10** photographs containing no person, the bald pass changed **2.7–7.7%** of pixels (mean
5.4%) on garments with no hair, and the references came out taller on 8 of 10 and whiter on
10 of 10 than the no-bald route. `ER` has no branch on garment kind; v3.0 did, and skipped
balding product shots because "there is no head". So every product garment currently pays a
generative call it does not need, and takes an invention risk a reviewer could not see on
this sample.

**Open decision, for the product:** restore v3.0's branch — route a garment photograph with
no person around the bald pass — trading a saved call per product garment against a
classifier that must be right. The marks force nothing; the metrics make it free money if the
classifier is reliable. Sample is 10 garments, all clean studio imagery, one reviewer.

## Q8. The existing klein script — reuse it?

The company already has a klein script (`aie: build flux klein script`). Its canvas
(`MAX_RES` on the longer side) and its defaults may differ from `ER`'s rules; reusing its
loader is fine, but reusing its canvas or call defaults changes outputs
(`prd/v3/v3.8/BUILD.md` §0.3, §4).

**Magic Hour's model list, checked against `ER` (2026-09-11).**

| MH file | `ER` |
|---|---|
| `FLUX.2-klein-4b-fp8-diffusers/transformer_bf16/diffusion_pytorch_model.safetensors` @ `408c457f` | **same** — the production transformer |
| `FLUX.2-klein-4B/text_encoder/model-0000{1,2}-of-00002.safetensors` @ `e7b7dc27` | **same** |
| `FLUX.2-klein-4B/vae/diffusion_pytorch_model.safetensors` @ `e7b7dc27` | **same** |
| `FLUX.2-klein-4B/scheduler/*`, `tokenizer/*` @ `e7b7dc27` | **same** |
| `loras/RebelReal4B.safetensors`, `RealSkin4B.safetensors`, `ConsistenceEdit4B.safetensors` | **not used.** `ER` runs with no LoRAs (BUILD §4 rule 7): each changes outputs materially, and no v3.8 number transfers to a LoRA'd stack. If MH's loader attaches them by default, the try-on path must load klein without them |
| — | **missing from MH's list:** `model_index.json`, `transformer_bf16/config.json`, `text_encoder/config.json`, `generation_config.json`, `model.safetensors.index.json`, and the four crop models (BiRefNet_lite, SCHP parser, MediaPipe Selfie Multiclass, MediaPipe Pose) — BUILD §3.1–3.2 |

**Still open:** whether the existing script attaches those LoRAs by default, and whether its
canvas and call defaults can be bypassed for the try-on path.

## Q9. Library versions of record

Never recorded — every notebook ran `pip install -U`. **Closes with** T2: byte-identical
call-2 outputs mean the pinned set is the set of record.

## Q10. Carried from v3.8, not blocking

- **SR on the reference** — it enters call 2 at 0.40 MP; the evidence's recommended next
  arm (`prd/v3/v3.8/BUILD.md` §9).
- **`ER` has not been swept against the strict bar** — its rate is a range with a floor
  (`prd/v3/v3.8/RESULTS.md` §3).
- **The fold is mostly front-facing** (`prd/v3/v3.8/SOLUTION.md` §6).
