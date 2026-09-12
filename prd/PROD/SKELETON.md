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
| reference cache | — | storage | garment | **yes** — the one piece of state |
| try-on — call 2 | FLUX.2 klein 4B | GPU | request | none |
| redraw | — | — | failed request | the seeds already used for the pair |

klein = Photoroom `transformer_bf16` + BFL text encoder, VAE, tokenizer, scheduler
([BUILD §3](../v3/v3.8/BUILD.md)).

## 3. The contract

```
prepare_garment(garment_image)            -> reference, meta{cranium_used, head_route, seconds}
try_on(person_image, reference, seed=None) -> image, seed
```

- `person_image` is image 1: it sets the output's aspect ratio and size.
- `garment_image` is a photograph of the garment **being worn** — every garment the system
  was measured on is one (`v3/colab/matrix.csv`, 56 garments).
- `seed` omitted → drawn at random and returned. Same inputs + same seed → the same image,
  on the same GPU class and library versions.
- Redraw = `try_on` again with a seed not yet used for that pair. The reference is not
  rebuilt.

## 4. Exposed and fixed

| exposed to the product | fixed inside the script |
|---|---|
| person image | both prompts ([BUILD §2](../v3/v3.8/BUILD.md)) |
| garment image | 4 steps · guidance 0.0 · bfloat16 · CPU generator |
| seed (optional) | call-1 seed 46 |
| max resolution — **pending**, [OPEN Q3](OPEN_QUESTIONS.md) | canvas rule: ≤1 MP, never above ([BUILD §4](../v3/v3.8/BUILD.md)) |
| | no LoRAs, pinned revisions |

## 5. The production Colab

Runbo's layout: like with like, no test code, no comments. One section per kind of code.

| § | section | contents |
|---|---|---|
| 1 | Install | one pip cell: pinned `diffusers`, `transformers`, `accelerate`, `mediapipe`, `onnxruntime-gpu` (matched to torch's CUDA), `opencv-contrib-python-headless` last |
| 2 | Downloads | every weight in one place, at pinned revisions: BFL klein parts, Photoroom transformer, BiRefNet, SCHP, the two MediaPipe files |
| 3 | Inputs | `PERSON_IMAGE`, `GARMENT_IMAGE`, `SEED`, `MAX_RES` — every user setting, nothing else |
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
