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

**What would close it.** `ER` on the old canvas (cap 2²⁰, never upscale, floor 16) over the
600 iron-man cells, marked paired against the archive — only the cells whose canvas
actually differs, which is most of the fold, since the person photos are 0.58–1.10 MP.
~25 min, ~CAD 0.3, plus marking.

**Interacts with Q3.**

---

## Q2. One crop or two?

**Raised by Ray, 2026-09-11.** Two readings; neither has data. **[CONFIRM which is meant.]**

**(a) Crop before call 1 as well** — BiRefNet crop → bald pass → head-subtracting crop.
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

## Q4. BiRefNet and the parser on the GPU — do the crops match?

Every reference of record was made with **CPU** ONNX. The GPU path works and is ~6×
faster, but GPU crops have never been compared with the references `ER` was measured on.
**Closes with** BUILD §7.3 **T1** (per-reference MAD ≤ 4.0). If it fails, crops stay on CPU:
they run once per garment and are cached.
→ `prd/v3/v3.8/BUILD.md` §5; `prd/v3/v3.5/RESULTS.md` §3; `prd/v3/v3.4/RESULTS.md` §10

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

## Q7. Which garment photos does the product accept?

All 56 garments the system was measured on are photographs of the garment **being worn**
(`v3/colab/matrix.csv`). Flat-lay, product and mannequin photos are untested on this path —
the cropper has a product route, but `ER`'s head-subtracting path does not use it.

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
