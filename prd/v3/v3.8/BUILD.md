# v3.8 — BUILD

**Written 2026-09-10.** How to build, deploy and accept the v3.8 system (`ER`). The
companion to [SOLUTION.md](SOLUTION.md): that document says *what* the architecture is and
*why*; this one says *how*, with every weight, revision, setting and test pinned, so the
system can be stood up without re-reading the investigation. Evidence is cited, not
restated ([SCHEMA §3](../SCHEMA.md)).

**Authority.** Where this document and prose anywhere else disagree, the code of record
wins, and this document names the file. The code of record for `ER` is:

| stage | file |
|---|---|
| normalise, prompts, BiRefNet/MediaPipe loaders | `v3/colab/lib/v3lib.py` |
| klein load, canvas rules, the call | `v3/colab/lib/klein_local.py` |
| bald pass (call 1) | `v3/colab/lib/run_ironman.py` lines 245–251 |
| head subtraction | `v3/build/ironman_bc_crop.py` → `v2/build/phase3_variants.py` `masks(cranium=True)` → `v2/build/garment_crop.py` |
| call 2 (`ER`) | `v3/colab/lib/run_v36.py` (`ER`, `main`) |

---

## 0. Corrections this document makes

Four statements elsewhere are wrong against the code. SOLUTION is locked and not amended;
the corrections live here.

1. **The cropper is not "no model".** SOLUTION §1 labels it `NO MODEL`. It is **no
   generative model**: it runs four non-generative networks — BiRefNet_lite, MediaPipe
   Selfie Multiclass, the SCHP human parser, and MediaPipe Pose (neck line, and fallback
   head ellipse). What SOLUTION means, and what is true, is that it can only *remove*
   pixels, never draw them.
2. **Call 1's canvas is not "the crop's own size".** That wording is `VEi`'s, whose call 1
   took the A4 crop. In `ER` call 1 is the bald pass on the **normalised garment
   photograph**, uncropped (`run_ironman.py:249`): canvas = that photo's size, capped at
   2²⁰ px, never upscaled, sides floored to 16 (`klein_local._size`, `canvas="v33"`).
3. **"Reproduced by not passing `image_size`" is a fal statement.** Self-hosted, the call-2
   canvas **must be passed explicitly** as `height`/`width` from `klein_local._size_fal`.
   The diffusers default is a *different* rule: `Flux2KleinPipeline` takes image 1's size
   capped at 1024² (down only) and floored to 16 (`pipeline_flux2_klein.py` v0.40.0, lines
   770–784). It would not scale small photos up and floors to 16, not 32 — a different
   canvas from every number of record.
4. **"Never upscale inside a klein call" is a call-1 rule.** The p004 placket is a call-1
   finding. Call 2's canvas rule scales image 1 **up or down** to 2²⁰ px by design (v3.4
   link D). On this fold, person photos are 0.58–1.10 MP (2²⁰), so call 2 upscales by at
   most ×1.32 linear; below that range it is unmeasured — see the input guard in §6.

---

## 1. The pipeline, stage by stage

```
GARMENT PHOTO                                                  once per garment, cached
  │ S0 normalise        ≤1,150,000 px, INTER_AREA          v3lib.normalise
  │                     → JPEG q95 round trip (part of the measured path)
  ▼
  S1 CALL 1 — bald      klein, BALD_PROMPT, seed 46         run_ironman.py:249
  │                     canvas: own size, ≤2²⁰, never up, /16   klein_local._size
  │                     → resized back to S0 size, INTER_AREA  → JPEG q95
  ▼
  S2 head subtraction   BiRefNet matte × Selfie labels × SCHP head   ironman_bc_crop.crop_bc
  │                     → head removed → subject bbox (+3%) → flattened on white 255
  │                     → JPEG q95                           = THE REFERENCE
  ▼
PERSON PHOTO ─ S0 normalise → JPEG q95 ─┐                      once per try-on
                                        ▼
  S3 CALL 2 — ER        klein, ER prompt, images [person, reference], seed per request
                        canvas: person's aspect at area 2²⁰, up or down, /32   klein_local._size_fal
                        4 steps · guidance 0.0 · bf16 · torch.Generator("cpu")
                        ▼
                        TRY-ON (~1 MP)
```

**S0 — normalise.** `v3lib.normalise`: if `h·w > 1,150,000`, resize by area to that
bound with `INTER_AREA`; otherwise untouched. This is a pre-bound only; no klein canvas
exceeds 2²⁰ regardless. The record writes and re-reads every normalised image as **JPEG
quality 95** (`run_ironman.py:200`); keep that round trip for parity.

**S1 — call 1, the bald pass.** `klein_local.edit([garment], BALD_PROMPT, seed=46,
canvas="v33")`, then `cv2.resize` back to the normalised photo's size with `INTER_AREA`
and JPEG q95 (`run_ironman.py:249–251`). A small, in-distribution edit of the *head*: it
exists because hair over a collar or shoulders cannot be separated from the garment by a
matte (SOLUTION §2).

**S2 — head subtraction.** `ironman_bc_crop.crop_bc(bald_bgr, stem)`:

1. **Subject** — BiRefNet_lite at 1024×1024 (ImageNet normalisation, sigmoid, cubic
   resize back), specks dropped (`garment_crop.biref_matte`, `drop_specks`).
2. **Class labels** — MediaPipe Selfie Multiclass at 256×256; hair+face, face, body
   channels refined in a trimap band with a guided filter
   (`garment_crop.refine_band` — needs `cv2.ximgproc`, i.e. `opencv-contrib`).
3. **Head** — the SCHP ATR parser at 512×512 supplies head shape; MediaPipe Pose's neck
   line bounds its extent; only the component containing the nose is kept; Selfie's
   clothes class vetoes collar pixels (`HEAD_CLOTHES_GUARD=1`, default)
   (`phase3_variants.parser_classes`).
   Fallbacks, in order, if the parser finds nothing: Pose head ellipse
   (`head_from_pose`), then a face-anchored cranium band (`with_cranium`). The route taken
   is returned as `cranium_used`.
4. `noface = subject × (1 − head)` → bbox of `subject > 0.5` with a 3% pad of the longer
   side (`garment_crop.bbox_of`) → `flatten(crop, noface, 255)` → JPEG q95
   (`garment_crop.write_rgb`).

**S3 — call 2, `ER`.** `klein_local.edit([person, reference], ER, seed, canvas="fal")`.
Image order is `[person, reference]` — image 1 is the person, and image 1 defines the
canvas. `Flux2KleinPipeline` feeds each conditioning image at its native size unless it
exceeds 1024² area (then it is scaled down to it), floored to 16 (`pipeline_flux2_klein.py`
v0.40.0 lines 770–779). So the reference enters at **0.40 MP mean (2²⁰; 0.42 decimal),
median 0.37, min 0.08, max 0.84** — measured on the 56 references of
`v3/runs/v36/ironman_er/refs/`.

---

## 2. The prompts, byte for byte

```python
BALD_PROMPT = ("Make this person completely bald. Remove all hair from the head and any "
               "hair falling over the shoulders, chest or back, and show the scalp. "
               "Keep the clothing, the body, the pose and the background exactly as "
               "they are.")

ER = ("Replace the clothing in image 1 with the clothing in image 2. Keep the person's "
      "face, identity, body and the background exactly as they are.")
```

Import them from `v3lib.BALD_PROMPT` and `run_v36.ER`, or copy with a test asserting
equality. A 4-step distilled model drifts as a prompt grows (EXPERIMENT links 3, 4); a
changed character is an untested arm.

---

## 3. The models

### 3.1 Inventory

| model | source · revision | file · bytes | params | license | device |
|---|---|---|---|---|---|
| **klein transformer** (**production**) | `Photoroom/FLUX.2-klein-4b-fp8-diffusers` @ `408c457f3589e17a1be1dae5bf0dcaf09cd4985f` | `transformer_bf16/diffusion_pytorch_model.safetensors` · 7,751,109,744 | **3.88B** | card: `other` → BFL's LICENSE (see §3.3) | GPU, bf16 |
| klein transformer (the one the archive was made on) | `black-forest-labs/FLUX.2-klein-4B` @ `e7b7dc27f91deacad38e78976d1f2b499d76a294` | `transformer/diffusion_pytorch_model.safetensors` · 7,751,109,744 | 3.88B (3,875,544,576) | Apache-2.0 | GPU, bf16 — parity test T2 only |
| **text encoder** (Qwen3-4B) | BFL @ `e7b7dc27` | `text_encoder/model-0000{1,2}-of-00002.safetensors` · 4,967,215,360 + 3,077,766,632 | **≈4.0B** | Apache-2.0 | GPU, bf16 |
| **VAE** | BFL @ `e7b7dc27` | `vae/diffusion_pytorch_model.safetensors` · 168,120,878 | — | Apache-2.0 | GPU |
| tokenizer, scheduler, configs | BFL @ `e7b7dc27` | `tokenizer/*`, `scheduler/*`, `*/config.json`, `text_encoder/model.safetensors.index.json`, `model_index.json` | — | Apache-2.0 | — |
| **BiRefNet_lite** (Swin-T) | `onnx-community/BiRefNet_lite-ONNX` `onnx/model.onnx` | `BiRefNet_lite.onnx` · 224,005,088 · sha256 `5600024376f572a557870a5eb0afb1e5961636bef4e1e22132025467d0f03333` | **44.6M** (44,622,290), fp32, input 1×3×1024×1024 | MIT | GPU (§5) |
| **SCHP ATR parser** (ResNet-101) | `basso4/humanparsing` @ `4fd18f98561bae00b5c24342c92307b4780b2a8d` | `parsing_atr.onnx` · 266,859,305 · sha256 `04c7d1d070d0e0ae943d86b18cb5aaaea9e278d97462e9cfb270cbbe4cd977f4` | **66.7M** (66,665,636), input 1×3×512×512 | MIT upstream (Peike Li) | GPU (§5) |
| MediaPipe Selfie Multiclass | Google `selfie_multiclass_256x256/float32/latest` | 16,371,837 · sha256 `c6748b1253a99067ef71f7e26ca71096cd449baefa8f101900ea23016507e0e0` | small | Apache-2.0 | CPU |
| MediaPipe Pose Landmarker lite | Google `pose_landmarker_lite/float16/1` | 5,777,746 · sha256 `59929e1d1ee95287735ddd833b19cf4ac46d29bc7afddbbf6753c459690d574a` | small | Apache-2.0 | CPU |

Byte counts and klein parameter counts are from the Hugging Face API at the pinned
revisions; ONNX parameter counts are summed over each graph's initializers; hashes are of
the copies in `models/` and `v2/runs/.models/`. **Verify every file by sha256 at startup**:
the MediaPipe URLs say `latest`, which is not a pin.

**Resident on the GPU:** ≈ 7.75 + 8.04 + 0.17 GB (klein, bf16) + 0.49 GB (two ONNX
graphs) ≈ **16.5 GB of weights**, before activations. Nothing is offloaded on the record's
A100-SXM4-40GB.

### 3.2 What to download, and what not to

From BFL, **exclude** `flux-2-klein-4b.safetensors` (a 7.75 GB single-file duplicate of the
transformer for ComfyUI) and the three sample `.jpg`s. From Photoroom, take
`transformer_bf16/` only — **not** `transformer_fp8_static/` (4.07 GB torchao, untested)
and not `grid.png`. With the Photoroom transformer, also skip BFL's `transformer/`.
Total ≈ 16.5 GB either way.

A `models/` folder holding only the Photoroom transformer and the two text-encoder shards
is **incomplete**: it also needs BFL's `vae/`, `tokenizer/`, `scheduler/`,
`text_encoder/config.json`, `text_encoder/generation_config.json`,
`text_encoder/model.safetensors.index.json`, `model_index.json`, and
`transformer_bf16/config.json`, plus the four non-generative models above.

### 3.3 The transformer choice

**Production uses the Photoroom `transformer_bf16`** (decided by Ray, 2026-09-11, on
v3.8's evidence). It is a dequantised fp8 round trip of BFL's transformer — same class,
config and tensor layout, 16 of 18 large matrices perturbed at ~2.2% median relative
error — and on 74 cells with a known `ER` verdict it changed **no outcome**: median pixel
difference 1.88/255, worst 9.08, flat across the both-clean, repaired and failed groups;
timing 2.31 s vs 2.28 s ([RESULTS §10](RESULTS.md#10-the-transformer-swap-2026-09-10), EXPERIMENT link 11; set
`v3/colab/v36_fp8_set.csv`, run `v3/runs/v36/fp8/`, page `v3/report/v36_fp8.html`).

BFL's transformer stays in this document for one job: **T2**, the byte-parity test, which
compares the package against an archive that was made on it. The production rate on the
Photoroom transformer comes from **T4**, which runs on it anyway.

The text encoder, VAE, tokenizer and scheduler always come from BFL — the Photoroom repo
carries a transformer and nothing else. Its card declares `license: other`, named
`flux-2-klein-4b-agreement`, linking to BFL's `LICENSE.md`, which at `e7b7dc27` is the
Apache License 2.0; the label goes to whoever signs off licenses, as a note.

There is **no VRAM saving** from it: `transformer_bf16` is byte-for-byte the same size as
BFL's.

---

## 4. What must be held fixed

Load-bearing, each with a measurement behind it. A deployment that breaks one is a new
arm, and no number in v3.8 describes it.

| # | rule | code | why |
|---|---|---|---|
| 1 | every klein canvas ≤ 2²⁰ px (4,096 tokens) | `_size`, `_size_fal` | `compute_empirical_mu` branches at 4,300 tokens (`pipeline_flux2_klein.py:67`); above it the model runs a schedule it was not distilled for. 1.15 MP admits ~4,492 — why v3.4 capped it ([v3.4 SOLUTION §2](../v3.4/SOLUTION.md)) |
| 2 | call 1: the normalised photo's own size, ≤ 2²⁰, never upscaled, sides floored to 16 | `klein_local._size` | inflated call-1 inputs lose framing; rendering above evidence invents structure (v3.4 links E–G; p004 placket at ×2.67) |
| 3 | call 2: image 1 scaled to area 2²⁰, aspect kept, up **or** down, sides floored to 32 — **passed explicitly** | `klein_local._size_fal` | the canvas every `ER` number was made on; measured off fal 20/20 ([v3.4 SOLUTION §2](../v3.4/SOLUTION.md)); the diffusers default differs (§0.3) |
| 4 | no generative upscale of the reference | — | a finished image may be scaled algorithmically; klein may not render above its conditioning |
| 5 | 4 steps, `guidance_scale=0.0`, `torch.bfloat16` | `klein_local.STEPS/GUIDANCE`, `load()` | the distilled operating point. Guidance is inert either way (`is_distilled: true`, no guidance embed; CFG only runs for `>1` on non-distilled) — keep 0.0 so the call is byte-identical to the record's |
| 6 | seed through `torch.Generator("cpu").manual_seed(seed)` | `klein_local.edit` | a CUDA generator's stream differs; seeds would not reproduce |
| 7 | no LoRAs, no adapters, no attention processors swapped | — | any of them changes outputs materially; no number here transfers |
| 8 | revisions pinned: BFL `e7b7dc27…`, Photoroom `408c457f…`, SCHP `4fd18f98…` | `from_pretrained(..., revision=)` | unpinned `main` can change outputs silently |
| 9 | self-hosted; never compare with fal | — | same prompt, seed and canvas rule gave different failures on fal ([EXPERIMENT link 1](EXPERIMENT.md)) |
| 10 | prompts byte-identical (§2); images in the order `[person, reference]` | `run_v36.ER` | the prompt was the only variable in v3.8; image 1 defines the canvas |
| 11 | JPEG q95 round trip on the normalised inputs, the bald frame and the reference | `run_ironman.py:200, 251`, `garment_crop.write_rgb` | part of the measured path; skipping it changes inputs by a few levels per pixel and breaks byte parity (T2) |
| 12 | call 1 at seed **46** | `run_ironman.py:249` (`seeds[0]`) | every reference of record was built at the run's first seed; the seed lottery was measured on call 2 only |
| 13 | batch size 1, one pipeline per GPU | — | batching changes kernels; never measured |
| 14 | the parser is SCHP (`PARSER` unset or `schp`) | `phase3_variants.PARSER` | the SegFormer parser is **non-commercial** (NVLabs licence §3.3) — never deploy `PARSER=segformer` |

---

## 5. BiRefNet and the parser on the GPU

**Yes, and BiRefNet on the GPU is now measured rather than inherited.** On a Colab A100
(Ray, 2026-09-12) with `onnxruntime-gpu==1.22.0`, BiRefNet_lite runs a 1×3×1024×1024 input
in **0.139 s on CUDA against 7.798 s on CPU — 56×** (warmed up, GPU averaged over three
runs, CPU over one). The `~6×` figure this document used to carry came from
[v3.5 RESULTS §3](../v3.5/RESULTS.md) and is superseded for BiRefNet.

**What that measurement does not cover, and it is most of the crop.** It is BiRefNet alone
on a synthetic tensor. The SCHP parser is not timed, and neither is the rest of
`head_subtract` — MediaPipe Selfie and Pose stay on CPU by design, and `refine_band`'s
guided filter is OpenCV on CPU. So the **end-to-end crop time on GPU is still unmeasured**,
and no share of the 56× transfers to it. The CPU figures of record stand until a GPU crop
is timed: 15.8 s per garment on a Colab host (v3.5 RESULTS §3), 16.3 s in the v3.9 inquiry
run, 200–1,000 s per frame on the local laptop
([v3.4 RESULTS §10.1](../v3.4/RESULTS.md)).

Three things make "on the GPU" true rather than assumed:

1. **It is opt-in.** `garment_crop.ort_providers()` returns CPU unless `V2_ORT_GPU=1`, on
   purpose: every V2 number was CPU. Set it. The same function gives the CUDA provider a
   memory-polite arena (`kSameAsRequested`, capped cuDNN workspace) because BiRefNet
   allocates ~800 MB of intermediates while sharing the card with klein;
   `V2_ORT_GPU_MEM_MB` caps it further.
2. **`onnxruntime-gpu` fails silently, and the pin is `==1.22.0`.** The newest wheel is
   built for CUDA 13; with a CUDA 12 torch it *registers* `CUDAExecutionProvider`, fails to
   `dlopen` it when a session is created, and falls back to CPU with no error.
   `get_available_providers()` cannot detect this — only loading the provider library can.
   Confirmed again on 2026-09-12: the newest wheel's probe died at the `dlopen` step and
   **`onnxruntime-gpu==1.22.0` was the first that loaded**, which is the known-good pin on
   Colab's current CUDA and what `vp/tryon_er.ipynb` and `vp/gpu_check.ipynb` now try
   first (each keeps the descending walk as a fallback, since the pin is a fact about a
   runtime and not about the model). The v3.3 iron man's A4 crops ran 6.8–7.4 s each on an
   A100 for exactly this reason ([v3.3 RESULTS](../v3.3/RESULTS.md), cost table), and the
   v3.9 inquiry run's 16.3 s head crop is the same failure: it was a CPU crop on an A100.
   **Never** install the CPU `onnxruntime` wheel alongside it — they cannot coexist.
3. **Assert at startup and fail closed.** After the first session is created:

   ```python
   import garment_crop as G, phase3_variants as P
   G._biref(); P._parser()
   assert G._STATE["biref"].get_providers()[0] == "CUDAExecutionProvider", "BiRefNet fell back to CPU"
   assert P._HP["m"].get_providers()[0] == "CUDAExecutionProvider", "SCHP fell back to CPU"
   ```

**The numeric footing is the one open question.** Every reference of record was made with
**CPU** ONNX. The iron-man-2 `BC` references — the ones every `ER` number stands on — were
cropped on the Colab host's CPU and checked against the 33 the local run made: **median
MAD 0.00, max 2.34** ([v3.4 RESULTS §10](../v3.4/RESULTS.md)). **GPU crops have never
been compared to them** — the v3.9 inquiry run did not close this either, because its crops
ran on CPU. Acceptance test T1 does that. If GPU crops fail it, keep the
cropper on CPU: it runs once per garment and is cached, so it is off the try-on's
latency path.

---

## 6. The service

### 6.1 Two operations

**`build_reference(garment_image) → reference`** — once per garment, cached.
S0 → S1 → S2. Cache key: sha256 of the normalised garment bytes **plus** a pipeline
version string (revisions + prompt hash + library pins), so a pipeline change invalidates
the cache rather than silently mixing references. Store alongside it: `cranium_used`,
which head route fired (parser / pose / band), sizes, per-stage seconds.

**`try_on(person_image, reference, seed=None) → (image, seed)`** — per request.
S0 on the person → S3. Returns the seed it used.

### 6.2 The seed policy

- **Call 1 is fixed at seed 46.** The reference is a garment asset, not a draw: it is
  built once, cached, and identical for every customer. That is also how the record was
  made — one reference per garment at seed 46, with seeds 46/47/48 varying call 2 only.
- **Call 2 draws a fresh seed per request**: `seed = secrets.randbelow(2**31)`. Log it
  with the request. With the same reference, person, seed, weights, library pins and GPU
  class, the output is **byte-identical** (the determinism control,
  [RESULTS §5](RESULTS.md)) — so any customer image can be reproduced exactly for
  support or audit.
- **A retry redraws call 2 only, at a new seed** never used for that pair. It never
  rebuilds the reference: the failures a seed cannot fix are reference-side, and a
  different bald draw is an untested arm.
- **The rejector is the user.** v3.8 ships no automatic rejector: the VLM judge is not
  good enough to spend calls on ([RESULTS §7](RESULTS.md) — its artifact flag fires on 45%
  of passes). The retry is triggered by the customer's "fail" button. An automatic
  rejector is a new component with its own validation against the blind marks.

**What the numbers are, under this policy** ([RESULTS §3, §6](RESULTS.md)):

| | value | basis |
|---|---|---|
| first-draw failure rate | **3.00% – ≥6.17%** | lenient sweep (§2) to strict-bar floor (§3); a range with a floor, not a point |
| a failed cell passes at another seed | **72%** (26/36) | §6 |
| failure rate after one retry | **1.71%** | the deployed report's figure: 6.17% (strict floor) × 28% (a retry meets another failed seed, from `ER`'s one sweep). On the lenient footing, 0.83% |
| pairs failing at every seed | 1 of 200 (0.5%) | the reference-side floor no seed reaches |
| extra call-2s the policy costs | ≈ the rejection rate, 3–6% | only rejected images are redrawn |

Under a user-triggered retry, the customer sees the first-draw rate; the post-retry figure
is what they end up with after pressing the button.

### 6.3 Input handling

- **Decode with `cv2.imread(..., IMREAD_COLOR)`** (or `cv2.imdecode`), as the record did:
  it applies EXIF orientation and returns 3-channel BGR for grayscale input. If a service
  layer decodes with PIL instead, apply `ImageOps.exif_transpose` first.
- **PNG with alpha:** flatten onto white before S0. `IMREAD_COLOR` drops alpha and keeps
  whatever colour sits under it — often black. Product decision; not measured.
- **Minimum person size.** The fold's normalised person photos are 0.58–1.10 MP (2²⁰);
  call 2 upscales at most ×1.32 on it. Photos far below that are rendered at 1 MP from
  thin evidence — unmeasured. Flag or reject below ~0.5 MP until a run says otherwise
  **[inferred]** from the fold's range, not measured.
- **Garment photos with no findable head** (back views, crops, flat lays): the parser and
  Pose fall through to the cranium band or to nothing. `cranium_used` records it; log it,
  and treat a garment whose head route failed as a candidate for review.

### 6.4 Hardware

- **Of record: A100-SXM4-40GB**, whole pipeline resident, no offload
  (`v3/runs/v34/ironman2_bc/meta/run.json`).
- **Peak VRAM has never been measured.** Weights are ~16.5 GB; activations at 1 MP with
  two conditioning images add to it. T3 measures it. V2 ran klein on a 24 GB L4 only with
  CPU offload (`prd/v2/TODO.md`), so plan on **≥40 GB**, or measure before choosing
  24 GB.
- **A different GPU class is a different draw.** Kernels differ, so bytes will not match
  the archive. The *outcome* equivalence of another GPU is unmeasured, like the Photoroom
  swap was until it was tested — run T4 on the target class before quoting v3.8's rates
  for it.
- Cold load: 354–532 s from a Drive-backed HF cache ([RESULTS §8](RESULTS.md),
  `ironman2_bc/meta/run.json`). Serve from local NVMe and keep the process warm.

### 6.5 Cost and latency

Per try-on (reference cached): call 2, **2.28 s median** on the A100 ([RESULTS §8](RESULTS.md)),
**CAD 0.45 per 1,000 images**. Per new garment: bald pass **1.48 s median**
(`v3/runs/v34/ironman2/meta/timings.csv`) + head crop (15.8 s CPU; ~6× less on GPU).
Including reference builds at this fold's ratio: CAD 0.54 (GPU crops) / 0.78 (CPU crops)
per 1,000.

---

## 7. Build it, then accept it

### 7.1 Environment

- Python 3.11+; CUDA 12.x torch; one `onnxruntime-gpu` matched to it (§5); `diffusers`
  with `Flux2KleinPipeline` (v0.40.0 carries it); `transformers`, `accelerate`,
  `sentencepiece`, `protobuf`, `mediapipe`, `huggingface_hub`; and
  **`opencv-contrib-python-headless` as the only OpenCV** — `mediapipe` can pull in plain
  `opencv`, which lacks `cv2.ximgproc` and breaks `refine_band`. Install it last and assert
  `hasattr(cv2.ximgproc, "guidedFilter")`.
- **The library versions of record were never recorded.** Every notebook ran
  `pip install -U` at run time (e.g. `v3/colab/v36_ironman_er.ipynb` cell 2), so the
  record used whatever PyPI served on 2026-09-10. Pin a set, `pip freeze` it into the
  image, and let **T2** decide whether that set reproduces the archive: byte-identical
  means it is the set of record.

### 7.2 Package layout

Vendor, do not rewrite — the BCA4 lesson was a cropper "reimplemented" into something
else ([v3.4 RESULTS §10](../v3.4/RESULTS.md)). Refactor only after T1/T2 pass, and re-run
them after.

```
tryon_er/
  weights.py    snapshot_download at pinned revisions with allow_patterns; sha256 check of
                every file in §3.1; refuse to start on a mismatch
  klein.py      klein_local.py: load(), _size, _size_fal, edit() - verbatim
  crop.py       garment_crop.py + phase3_variants.py, only what masks(cranium=True) reaches,
                with three changes: model paths injected (no repo-relative paths); the
                biref_matte DISK CACHE REMOVED (it is keyed by filename stem and checks only
                shape - a new image with an old stem gets the old matte); PARSER pinned to
                "schp"
  pipeline.py   build_reference(), try_on(); the JPEG q95 round trips; the seed policy
  prompts.py    BALD_PROMPT, ER - with a test asserting equality to v3lib / run_v36
```

Loading klein, with either transformer:

```python
import torch
from huggingface_hub import snapshot_download
from diffusers import Flux2KleinPipeline, Flux2Transformer2DModel

BFL, BFL_REV = "black-forest-labs/FLUX.2-klein-4B", "e7b7dc27f91deacad38e78976d1f2b499d76a294"
PR, PR_REV = "Photoroom/FLUX.2-klein-4b-fp8-diffusers", "408c457f3589e17a1be1dae5bf0dcaf09cd4985f"
BASE = ["model_index.json", "scheduler/*", "text_encoder/*", "tokenizer/*", "vae/*"]

def load(photoroom=True):
    bfl = snapshot_download(BFL, revision=BFL_REV,
                            allow_patterns=BASE + ([] if photoroom else ["transformer/*"]))
    kw = {}
    if photoroom:
        pr = snapshot_download(PR, revision=PR_REV, allow_patterns=["transformer_bf16/*"])
        kw["transformer"] = Flux2Transformer2DModel.from_pretrained(
            pr, subfolder="transformer_bf16", torch_dtype=torch.bfloat16)
    return Flux2KleinPipeline.from_pretrained(bfl, torch_dtype=torch.bfloat16, **kw).to("cuda")
```

Then call exactly as `klein_local.edit` does: `height, width` from the canvas rule,
`num_inference_steps=4`, `guidance_scale=0.0`, `generator=torch.Generator("cpu").manual_seed(seed)`.
Do **not** copy the Photoroom card's example call (`height=1024, width=1024`,
`guidance_scale=1.0`): fixed 1024² is not the canvas rule.

### 7.3 Acceptance tests

Cheap because the pipeline is deterministic. Inputs are the archive:
`v34_ironman2_20260906_0904.zip` (inputs, bald frames), `v3/runs/v34/ironman2_bc/refs/`,
`v3/runs/v36/ironman_er/` (the 600 `ER` outputs), matrix `v3/colab/v36_ironman_er.csv`.

| test | what | passes when | cost |
|---|---|---|---|
| **T0** environment | sha256 of every weight; revisions; both ONNX providers are CUDA; `cv2.ximgproc` present; `pip freeze` and GPU name written to the image | all true | seconds |
| **T1** reference parity | rebuild the 56 `BC` references from the archived bald frames; compare with `ironman2_bc/refs/*__BC.jpg`. Once with crops on CPU, once on GPU. Then rebuild the bald frames from the inputs at seed 46 and compare with the archive | shapes within 8 px, per-reference MAD ≤ 4.0 — the gate `v3/colab/v34_bc.ipynb` cell 6 used; the CPU run should land near the 0.00 / 2.34 of record | minutes |
| **T2** call-2 parity | the archived inputs + references, seeds 46/47/48, `ER`, BFL transformer, on an A100 → compare with `v3/runs/v36/ironman_er/gen/` | **byte-identical**. If not, the library set differs from the record's: note which, and T4 becomes mandatory | ~25 min, ~CAD 0.3 for all 600; 30 cells for a first read |
| **T3** resources | peak VRAM (`torch.cuda.max_memory_allocated` + `nvidia-smi` for the ONNX arena), per-stage latency, cold load | numbers recorded; chooses the GPU class | minutes |
| **T4** end to end | raw photos → package → all 600 cells; mark only the cells whose output differs perceptibly from the archive, blind to which is which, on the counting page | no outcome worse than the archive beyond the seed noise of RESULTS §6. **Required** for the Photoroom transformer, for a new GPU class, or when T2 is not byte-identical | ~25 min, ~CAD 0.3, plus marking |
| **T5** edge inputs | tiny, huge, extreme aspect, PNG with alpha, grayscale, EXIF-rotated, back view, garment with no head in frame | no crash; guards fire; `cranium_used` and the head route logged | minutes |

T1 + T2 prove the package **is** `ER`. T4 is what licenses a change of transformer or
hardware.

---

## 8. What is deliberately not in the build

| not built | why | evidence |
|---|---|---|
| a VLM or any automatic rejector | no instrument yet separates failures from passes well enough to spend calls on | [RESULTS §7](RESULTS.md) |
| an SR pass on the reference | untested on a matte-derived reference; carries a measured hands/cleanliness cost on `VEi` — see §9 | [v3.4 RESULTS §9.1](../v3.4/RESULTS.md) |
| an ankle cut | neutral on every failure class; footwear follows the reference | [v3.4 SOLUTION §2](../v3.4/SOLUTION.md) |
| a framing read / pose clause in call 2 | naming an absent limb draws it — ×12 invented feet | [EXPERIMENT link 4](EXPERIMENT.md) |
| the A4 crop, a mannequin or re-pose call 1 | every generative pass over the garment pays the regeneration tax | [v3.5 RESULTS §4](../v3.5/RESULTS.md), [v3.7](../v3.7/EXPERIMENT.md) |
| Qwen, fal, LoRAs, `transformer_fp8_static` | outside the one-model self-hosted constraint, or untested | §4 |

---

## 9. Open, and not blocking

- **The reference is not scaled to the canvas** (0.40 MP mean into a 1 MP call). v3.4
  link H found the reference's ~1 MP token footprint in call 2 is what fixes dwarfism, and
  `VEi` SRs its reference for that reason; `ER` inherits `BC`'s no-SR path. An SR pass on
  the finished reference (`run_ironman.to_1mp_sr`, realesr-general-x4v3, 1.2M params, no
  extra klein call) is the one untested change the evidence recommends, and it aims at the
  reference-side floor where 68% of what remains lives. It is a new arm: it needs its own
  600-cell run and paired marking before it enters this build (SOLUTION §6 calls it a
  trade to be priced).
- **`ER` has not been swept against the strict bar**, so its rate is a range with a floor
  ([RESULTS §3](RESULTS.md)).
- **The fold is mostly front-facing wearers.** A catalogue of awkward source photographs
  would move the number (SOLUTION §6).
- **The library versions of record are unknown** until T2 fixes them.
- **The Photoroom card's license label** (§3.3).
