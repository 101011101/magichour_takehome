# PROD — skeletal structure

The shape of the production system and of the production Colab, at the level a ticket is
written from. Every stage, setting and number has its detail in
[`prd/v3/v3.8/BUILD.md`](../v3/v3.8/BUILD.md); section numbers below point there.

## 1. The system

```
                 ┌──────────── PREPARE GARMENT ─────────────┐   once per garment, cached
garment photo ──►│ normalise → klein bald pass (seed 46)     │
                 │ → head-subtracting crop → reference       │──► reference (cache)
                 └───────────────────────────────────────────┘          │
                                                                        ▼
                 ┌──────────────── TRY ON ───────────────────┐   once per request
person photo ───►│ normalise → klein edit (ER), random seed  │──► try-on image + seed
                 └───────────────────────────────────────────┘
                                   ▲
                                   └── user presses FAIL → same inputs, new seed (call 2 only)
```

Two klein calls per garment-and-person, one model. The first is shared by every user who
tries that garment on; the second is the only per-request cost.

## 2. The parts

| part | model | runs on | per | state |
|---|---|---|---|---|
| normalise | — (OpenCV, ≤1.15 MP) | CPU | image | none |
| bald pass — call 1 | FLUX.2 klein 4B | GPU | garment | none |
| head-subtracting crop | BiRefNet_lite · SCHP parser · MediaPipe Selfie · MediaPipe Pose | GPU (ONNX) · CPU (MediaPipe) | garment | none |
| band cut (a region) | MediaPipe Pose (hips) | CPU | garment × region | none |
| reference cache | — | storage | garment **× region × route** | **yes** — the one piece of state |
| try-on — call 2 | FLUX.2 klein 4B | GPU | request | none |
| redraw | — | — | failed request | the seeds already used for the pair |

klein = Photoroom `transformer_bf16` + BFL text encoder, VAE, tokenizer, scheduler
([BUILD §3](../v3/v3.8/BUILD.md)).

## 3. The contract

```
prepare_garment(garment_image, region)              -> reference, info{requested, region,
                                                        fallback, head_route, route,
                                                        route_why, seconds}
try_on(person_image, reference, seed=None, region)  -> image, seed
```

- `person_image` is image 1: it sets the output's aspect ratio **and its size** — since
  2026-09-12 the output *is* the person photo's own size, bounded to 1 MP, floored to 32,
  never upscaled ([BUILD §6.1b](../v3/v3.8/BUILD.md)).
- `garment_image` is a photograph of the garment. Worn by a person is the best-supported
  input — every garment the system was measured on is one (`v3/colab/matrix.csv`, 56
  garments). A product shot with nobody in it is detected and takes a shorter route: the
  **person gate** skips the bald pass and the head-subtracting crop, and forces `full`
  ([BUILD §6.1d](../v3/v3.8/BUILD.md)). The gate is a **head** check — Selfie Multiclass
  FACE + HAIR, at least 500 px — and it makes no error either way: 56 of 56 worn
  photographs, 0 of 17 person-free ones. The threshold sits in a 9.2× gap (worn floor 1,849
  px, person-free ceiling 202).
- `region` is `full`, `upper` or `lower` — the garment type the user asked to swap. It
  changes **both** the reference (the mask is cut at the hip line) and call 2's prompt, which
  names the half. A full-body photo with `upper` should come back with the person's own
  trousers.
- **Pass `info["region"]` to `try_on`, not the region you asked for.** The band falls back to
  `full` — recording which rule fired — when no pose or no in-frame hip is found, when the band
  keeps under **15%** of the garment, or when the reference it would send has a side under
  **64 px** (klein's own input floor). A product shot is forced to `full` by the person gate.
  The prompt has to follow the reference. `info["requested"]` always keeps what the user asked
  for, on both routes ([BUILD §6.1c](../v3/v3.8/BUILD.md)).
- `seed` omitted → drawn at random and returned. Same inputs + same seed → the same image,
  on the same GPU class and library versions.
- Redraw = `try_on` again with a seed not yet used for that pair. The reference is not
  rebuilt.

## 4. Exposed and fixed

| exposed to the product | fixed inside the script |
|---|---|
| person image | all three prompts ([BUILD §2](../v3/v3.8/BUILD.md)) |
| garment image | 4 steps · guidance 0.0 · bfloat16 · CPU generator |
| **region** — `full`, `upper`, `lower` | call-1 seed 46 |
| seed (optional) | the hip line, and the fallback to `full` |
| **max resolution** — caps the longer side, default 1536 | |
| | canvas rule: the person's own size, ≤1 MP, floor 32, **never upscaled** ([BUILD §4 rule 3](../v3/v3.8/BUILD.md)) |
| | no LoRAs, pinned revisions |

## 5. The production Colab

Runbo's layout: like with like, no test code, no comments. One section per kind of code.

| § | section | contents |
|---|---|---|
| 1 | Install | one pip cell: pinned `diffusers`, `transformers`, `accelerate`, `mediapipe`, `onnxruntime-gpu` (matched to torch's CUDA), `opencv-contrib-python-headless` last |
| 2 | Downloads | every weight in one place, at pinned revisions: BFL klein parts, Photoroom transformer, BiRefNet, SCHP, the two MediaPipe files |
| 3 | Inputs | `PERSON_IMAGE`, `GARMENT_IMAGE`, `SEED` — every user setting, nothing else |
| 4 | Load | klein on the GPU; the ONNX sessions on CUDA, asserted |
| 5 | Pipeline | normalise, the canvas rule, the bald pass, the crop, the try-on — functions only |
| 6 | Run | `prepare_garment`, then `try_on`; times each |
| 7 | Output | the image, the seed, the timings |

**Built:** [`vp/tryon_er.ipynb`](../../vp/tryon_er.ipynb). The crop code is **inline** in §5 —
the notebook is self-contained, with no fetch of repo files — vendored from the code of record
with comments, the disk cache and repo paths removed ([`vp/README.md`](../../vp/README.md)).

## 6. Not in the system

No VLM, no automatic rejector, no SR, no ankle cut, no pose clause, no fal
([BUILD §8](../v3/v3.8/BUILD.md)).
