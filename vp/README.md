# vp — production code

`vp/` is the production counterpart of `v1/`–`v3/`: code that ships, not code that
investigates. The prose — the ticket, the open questions, the ledger — lives in
[`prd/PROD/`](../prd/PROD/README.md); the build specification of record is
[`prd/v3/v3.8/BUILD.md`](../prd/v3/v3.8/BUILD.md).

| file | what |
|---|---|
| `tryon_er.ipynb` | the production Colab: the v3.8 `ER` virtual try-on, end to end — garment photo + person photo in, try-on image out |
| `gpu_check.ipynb` | the GPU check: proves BiRefNet and the SCHP parser really run on CUDA, times them against CPU, and runs the crop-parity gate (BUILD §7.3 **T1**) |
| `inquiry_confirmation.ipynb` | **Inquiry Confirmation**: every open inquiry in one run — the GPU question above, the call-2 upscale, the second crop, and garment-only references |

## The notebook

Seven sections, one kind of code each, per [`prd/PROD/SKELETON.md`](../prd/PROD/SKELETON.md) §5:

| § | section | what it does |
|---|---|---|
| 1 | Install | pinned `diffusers`, `transformers`, `accelerate`, `mediapipe`; the first `onnxruntime-gpu` build whose CUDA provider actually loads on the runtime; `opencv-contrib-python-headless` last |
| 2 | Downloads | every weight into `MODEL_ROOT`, in Magic Hour's layout, at pinned revisions — only files that are missing are fetched; the four crop models are sha256-checked every run |
| 3 | Inputs | `PERSON_IMAGE`, `GARMENT_IMAGE`, `OUTPUT_IMAGE`, `SEED`, `MAX_RES` |
| 4 | Load | klein (Photoroom transformer + BFL text encoder, VAE, tokenizer, scheduler) on the GPU; BiRefNet and the SCHP parser on CUDA — **stops with an error if either falls back to CPU**; MediaPipe Selfie and Pose on CPU |
| 5 | Pipeline | the functions: normalise, the two canvas rules, klein, the head-subtracting crop, `prepare_garment`, `try_on` |
| 6 | Run | prepares the garment, runs the try-on, writes `OUTPUT_IMAGE` |
| 7 | Output | the image, the seed, the head route, per-stage seconds |

Everything is inline. The crop is the code of record (`v2/build/garment_crop.py`,
`v2/build/phase3_variants.py`, `v3/build/ironman_bc_crop.py`) with the comments removed,
the filename-keyed disk cache removed, model paths injected, and the parser fixed to SCHP.

## How to run

1. Open `tryon_er.ipynb` in Colab on an **A100** runtime.
2. In §2 set `MODEL_ROOT` to the folder that holds `FLUX.2-klein-4B/` and
   `FLUX.2-klein-4b-fp8-diffusers/` (Magic Hour's `models/`). Leave it as is to download
   everything (~16.5 GB, once).
3. In §3 set the two image paths. `SEED = None` draws a random seed and prints it;
   `MAX_RES = None` keeps the 1 MP canvas.
4. Run all.

**Redraw:** set `SEED = None` (or any unused seed) and run §6–§7 again; the garment is
re-prepared in the Colab, where a product would reuse its cached reference.

## `MAX_RES`

`None` → the canvas of record: the person photo's aspect at area 2²⁰ px (~1 MP), sides
multiples of 32. A value caps the **longer side** of that canvas, scaling it down to fit
(multiples of 32). It never raises resolution: values at or above the canvas's own longer
side (at most 1344, for 9:16) change nothing. A 3:4 photo gives 864×1152 at `None`,
768×1024 at `MAX_RES = 1024`. Semantics are a proposal pending sign-off
([`prd/PROD/OPEN_QUESTIONS.md`](../prd/PROD/OPEN_QUESTIONS.md) Q3); below 1 MP is
untested on `ER`.

## Fixed on purpose

Both prompts, 4 steps, guidance 0.0, bfloat16, the CPU seed generator, call 1's seed 46,
no LoRAs — each is load-bearing ([BUILD §4](../prd/v3/v3.8/BUILD.md)). Magic Hour's
LoRA files are not loaded by this notebook.

## The GPU check

`gpu_check.ipynb` answers one question the production notebook asserts but has never
demonstrated on hardware: **do the two ONNX models actually run on the GPU, and do GPU
crops still reproduce the references of record?**

**Why it is needed.** The crops have always run on CPU, for three reasons that stack:

1. `v2/build/garment_crop.py` `ort_providers()` returns CPU unless `V2_ORT_GPU=1` — opt-in
   on purpose, because every V2 number was measured on a laptop with no GPU.
2. When the GPU *is* asked for, it can fail silently: the newest `onnxruntime-gpu` wheel is
   built against CUDA 13 while Colab's torch ships CUDA 12, so it registers
   `CUDAExecutionProvider`, fails to `dlopen` the provider library when a session is
   created, and falls back to CPU with no error. `get_available_providers()` cannot detect
   this — only loading the library can. The v3.3 iron man paid 6.8–7.4 s per crop on an
   A100 for exactly this (`prd/v3/v3.3/RESULTS.md`).
3. v3.5 then kept CPU **deliberately**, so new references stayed numerically identical to
   the CPU archive (`prd/v3/v3.5/RESULTS.md` §3).

**The fix is already in `tryon_er.ipynb`** and needed no amendment: §1 walks candidate
`onnxruntime-gpu` builds and keeps the first whose CUDA provider library actually loads,
and §4 builds both sessions with an explicit CUDA provider list and **raises** if either
reports anything but `CUDAExecutionProvider`. It never goes through `ort_providers()`, so
`V2_ORT_GPU` does not apply to it. `gpu_check.ipynb` is what proves that fix works on real
hardware, and it does use the repo modules, so it sets `V2_ORT_GPU` itself.

| § | section | what it does |
|---|---|---|
| 1 | Environment | torch's CUDA version, the installed `onnxruntime`, its providers, and — the point — whether the CUDA provider library *loads*, probed in a subprocess so nothing stale is imported into the kernel |
| 2 | Install | walks candidate `onnxruntime-gpu` builds, printing why each is rejected, and prints which one won |
| 3 | Downloads | the cropper modules (the `v3.3-lock` bundle) and, from Drive `v3_runs/`, the archived bald frames and the `BC` references of record |
| 4 | Load and assert | builds both sessions with `V2_ORT_GPU=1` and **raises** unless both report `CUDAExecutionProvider` |
| 5 | Timings | BiRefNet and the parser, GPU against CPU on the same frame, warmed up first, with the speed-up |
| 6 | Parity — **T1** | the full head-subtracting crop on the GPU over every archived bald frame, against the CPU references, on `v34_bc.ipynb`'s gate: shapes within 8 px, per-reference MAD ≤ 4.0 |
| 7 | Verdict | providers, timings, parity, and whether production should run crops on GPU |

**To run:** open it in Colab on an **A100**, set `DRIVE_PROJECT_DIR` in §1 if the Drive
folder differs, Run all. It needs `v34_ironman2_*.zip` and `v34_ironman2_bc_*.zip` under
Drive `v3_runs/`. The matte disk cache is cleared before §6 — it is keyed by filename and
would otherwise hand a GPU run the CPU mattes and pass trivially.

**What it settles that we do not already know:** whether a CUDA-loading wheel exists on the
runtime at all, the real GPU crop time (the ~6× is from v3.5 and is quoted nowhere as
measured on this stack), and **whether GPU crops are numerically safe** — the open question
in `prd/PROD/OPEN_QUESTIONS.md` Q4. If parity fails, production keeps crops on CPU: they
run once per garment and are cached, so they are off the try-on's latency path.

## Inquiry Confirmation

`inquiry_confirmation.ipynb` answers **four** open inquiries in one A100 session, so the
questions are settled against one another rather than one at a time.

| § | inquiry | how it is answered |
|---|---|---|
| 5–6 | **Do BiRefNet and the SCHP parser run on the GPU?** | measured in the run: providers asserted, GPU against CPU timings, and the T1 crop-parity gate against the CPU references of record |
| 7 | **Is the call-2 upscale necessary?** | `SCALE` (area 2²⁰, up or down) against `NOSCALE` (the photo's own size, never upscaled), everything bounded to ≤ 2²⁰ px — the v3.9 arms, run verbatim |
| 7 | **One crop or two?** | `CROP2` — the A4 crop first, *then* the bald pass, then the head-subtracting crop — against the same one-crop baseline |
| 8 | **Do product shots work?** | 10 flat-lay and ghost-mannequin garments × 3 people × 2 seeds, the full path (`PROD`) against one that **skips the bald pass** (`NOBALD`) |

**Sections 5 and 6 are the only ones the run itself decides.** The other three produce
images to judge: build the page with `python3 v3/build/inquiry_page.py` and mark it.

### Garment-only references — what the record already said

The production path balds **every** garment, because every garment it was measured on is
worn by someone (`v3/colab/matrix.csv`, 56 of 56). A flat-lay has no head to remove.

The v3.0 pipeline **branched on garment kind**: product references were never balded —
"there is no head" (`v3/build/run_v30.py`, and its `worn = [...]` filter). Run A paired 5
`clothesonly_*` product shots with 3 people each, 15 pairs, both `BC` and `QX` arms
(`v3/testsets/v30_matrix_a.csv`, outputs in `v3/runs/v3.0a/`). That evidence was never
marked — "run A complete and unmarked" (`prd/v3/v3.0/TEST.md`) — and run B excluded
product-only references deliberately, so **V3 has no verdict on them**, and the branch that
protected them no longer exists in `ER`.

The garments here are the 17 product-only entries of `test_set1/manifest.csv` — 10 chosen
across every category and both photo styles (7 flat-lay, 3 ghost mannequin), including the
`graphic_logo`, `graphic_text` and `fine_pattern` hard cases. They are pulled from the
`v3.3-lock` branch at run time, so nothing has to be uploaded.

Per garment the notebook records whether the parser found a head at all, how much of the
image the bald pass changed, and whether the crop returned something sane — then the page
asks the only question that matters: **does skipping the bald pass produce a better try-on?**

**To run:** Colab, A100, Run all. It needs `v34_ironman2_*.zip` and
`v34_ironman2_bc_*.zip` under Drive `v3_runs/`, and `v39_bundle.zip` pushed to
`v3.3-lock`. It writes one zip to Drive holding both runs; unpack it to
`v3/runs/inquiry/a100/`, then build the page and export to
`v3/testsets/inquiry_marks.csv`.

## Still to fill in

- A Colab link for the ticket once this is uploaded.
- Library pins are the PyPI versions current when `ER` was run (2026-09-10); acceptance
  test T2 confirms them against the archive.
- Never run on a GPU from this repo yet: peak VRAM and GPU crop time are unmeasured
  (T3).
