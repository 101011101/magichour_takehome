# fal `fal-ai/flux-2/klein/4b/distilled/edit` — empirical probe (2026-08-31)

28 calls (budget 40). Everything here is measured on this endpoint today; nothing is taken
from fal docs. Scripts: `probe.py` (calls, saves raw bytes + decoded PNG + response JSON per
call under `out/`), `analyze.py` (diffs, side-by-sides under `sbs/`, full table in `analysis.txt`).

## Fixed call arguments (every call unless a row says otherwise)

```
endpoint  fal-ai/flux-2/klein/4b/distilled/edit          (fal_client.subscribe, with_logs=False)
prompt    E3 from v3/colab/lib/run_ironman.py:
          "Dress the person in image 1 in the clothing shown in image 2. Keep the person's face,
           identity, body and the background exactly as they are. The person's body, limbs and
           feet are exactly as in image 1 - nothing added, nothing removed."
seed      46
image_urls  [P, R] as PNG data-URIs via L.b64 (cv2.imencode .png)
P  = v3/runs/ironman/20260830_0548/inputs/p001.jpg        682x1024, 0.698 MP  (image 1, person)
R  = v3/runs/v34/linkA/refs/p002__Vnc.jpg                 557x1666, 0.928 MP  (image 2, garment ref)
     (the prompt's suggested refs/p002__V.jpg is only 265x684 = 0.18 MP; the Vnc cut is ~1 MP, as the
      question asks for)
no num_inference_steps / guidance / output_format / image_size passed unless stated.
```

Resized variants (`inputs/*.png`, aspect preserved, INTER_AREA down / INTER_CUBIC up):
P05 577x866 (0.500 MP) · P11 856x1285 (1.100 MP) · P25 1290x1937 (2.499 MP) · Pq7 1001x1503 (1.505 MP)
R025 289x865 (0.250 MP) · R2 818x2446 (2.001 MP) · R3 1001x2996 (2.999 MP)
Pa0635 = P[:,16:666] 650x1024 · Pa0758 = P[62:962,:] 682x900 · Pwide = P transposed 1024x682.

Metrics: MAD = mean |a-b| over all 8-bit BGR values; px>16 = % of pixels whose max channel
difference exceeds 16; PSNR in dB. Response always contains `seed: 46`, `has_nsfw_concepts`,
`timings.inference` 0.8-1.7 s.

## Call table

| call | image_urls | extra args | output | bytes | notes |
|---|---|---|---|---|---|
| c01_base | [P, R] | – | 832x1248 png | 1165855 | reference output |
| c02_p05 | [P05, R] | – | 832x1248 png | | |
| c03_p25 | [P25, R] | – | 832x1248 png | | |
| c04_p11 | [P11, R] | – | 832x1248 png | | |
| c05_r025 | [P, R025] | – | 832x1248 png | | |
| c06_r3 | [P, R3] | – | 832x1248 png | | |
| c07_repeat | [P, R] | – | 832x1248 png | 1165855 | = c01 |
| c08_steps8 | [P, R] | num_inference_steps=8 | 832x1248 png | | inference 1.67 s (vs 0.94) |
| c09_steps4 | [P, R] | num_inference_steps=4 | 832x1248 png | 1165855 | = c01 |
| c10_swap | [R, P] | – | 576x1760 png | | |
| c11_dup | [P, R, R] | – | 832x1248 png | | |
| c12_jpeg | [P jpg q95, R jpg q95] data-URIs | – | 832x1248 png | | |
| c13_url | [P, R] uploaded PNG files (fal_client.upload_file) | – | 832x1248 png | 1165855 | = c01 |
| c14_q7 | [Pq7, R] | – | 832x1248 png | | |
| c15_r2 | [P, R2] | – | 832x1248 png | | |
| c16_png | [P, R] | output_format="png" | 832x1248 png | 1166148 | differs from c01 (see Q3) |
| c17_a0635 | [Pa0635, R] | – | 800x1280 png | | |
| c18_a0758 | [Pa0758, R] | – | 864x1152 png | | |
| c19_wide | [Pwide, R] | – | 1248x832 png | | |
| c20_imgsize | [P, R] | image_size={"width":672,"height":1024} | 672x1024 png | | accepted, honoured exactly |
| c21_repeat2 | [P, R] | – | 832x1248 png | 1165855 | = c01 |
| c22_png2 | [P, R] | output_format="png" | 832x1248 png | 1165855 | = c01 |
| c23_jpegout | [P, R] | output_format="jpeg" | 832x1248 jpg | 369385 | |
| c24_repeat3 | [P, R] | – | 832x1248 png | 1165855 | = c01 |
| c25_dup2 | [P, R, R] | – | 832x1248 png | | = c11 |
| c26_r025b | [P, R025] | – | 832x1248 png | | differs from c05 |
| c27_p05b | [P05, R] | – | 832x1248 png | | = c02 |
| c28_jpeg2 | [P jpg, R jpg] | – | 832x1248 png | | = c12 |

## Q3 first: determinism and the noise floor (needed to read every other number)

| pair (identical arguments) | MAD | px!=0 | px>16 | PSNR |
|---|---|---|---|---|
| c01 vs c07 | 0.000 | 0.00 % | 0 % | inf |
| c01 vs c21 | 0.000 | 0 | 0 | inf |
| c01 vs c24 | 0.000 | 0 | 0 | inf |
| c01 vs c09 (explicit steps=4) | 0.000 | 0 | 0 | inf |
| c01 vs c13 (uploaded URL instead of data-URI) | 0.000 | 0 | 0 | inf |
| c01 vs c22 (output_format=png) | 0.000 | 0 | 0 | inf |
| c11 vs c25 (dup ref) | 0.000 | 0 | 0 | inf |
| c02 vs c27 (P05) | 0.000 | 0 | 0 | inf |
| c12 vs c28 (jpeg inputs) | 0.000 | 0 | 0 | inf |
| **c16 vs c22** (output_format=png, twice) | **0.350** | 44.2 % | 0.25 % | 40.2 dB |
| **c05 vs c26** (R025, twice) | **0.406** | 50.9 % | 0.23 % | 39.2 dB |

- Pixels: 9 of 11 identical-argument pairs are pixel-identical (MAD exactly 0). 2 of 11 differ by
  MAD 0.35-0.41 / PSNR ~40 dB, i.e. the endpoint is **usually but not always** pixel-deterministic
  for a fixed seed (most likely a different worker/GPU or kernel selection; not measurable from
  outside). **Noise floor for this probe: MAD ≈ 0.4, px>16 ≈ 0.25 %, PSNR ≈ 40 dB.** Any
  difference at or below that cannot be attributed to the input change.
- Bytes: **never byte-identical**. Every PNG carries a 13,031-byte `caBX` (C2PA content-credentials)
  chunk right after IHDR; the pixel-identical pairs differ only inside that chunk (c01 vs c07: 325
  differing bytes, offsets 121-13075, all inside caBX; IDAT identical). So "same sha256" is the wrong
  test for this endpoint; compare decoded pixels.
- The floor is not visually nothing: in the feet crop (`sbs/feet_crops.jpg`) a lace-like artefact
  on the left ankle is present in c01/c07/c03/c14/c15/c26 and absent in c16/c02/c04/c05/c06/c11/c12,
  with feet-region MAD 1.5-2.5. Small semantic details flip at the noise floor.

## Q1 Output size (image 1 at 0.70 / 0.50 / 1.10 / 2.50 MP)

| image 1 | output | out MP | MAD vs c01 (px>16) |
|---|---|---|---|
| P 682x1024 (0.698 MP) | 832x1248 | 1.038 | – |
| P05 577x866 (0.500 MP) | 832x1248 | 1.038 | 0.612 (0.43 %) — deterministic (c02=c27) |
| P11 856x1285 (1.100 MP) | 832x1248 | 1.038 | 0.460 (0.33 %) |
| P25 1290x1937 (2.499 MP) | 832x1248 | 1.038 | 0.435 (0.28 %) |
| Pq7 1001x1503 (1.505 MP) | 832x1248 | 1.038 | 0.450 (0.38 %) |
| Pwide 1024x682 | 1248x832 | 1.038 | (transposed) |

Answer: the output is **not** image 1's size, not a rounding of it, and not a cap. fal
**re-samples image 1 to a fixed ~1.04 MP canvas** at (nearly) its aspect ratio, whether image 1 is
0.5 MP (upscaled ×1.44 in each axis) or 2.5 MP (downscaled). A 0.70 MP input comes back at
1.04 MP, i.e. fal upsamples our normal inputs. Side-by-side: `sbs/q1q7_image1_size.jpg`.

Local rule (klein_local._size): k = min(1, sqrt(1.15 MP / (h·w))); side = floor(side·k / 16)·16
→ 682x1024 stays 672x1024 (0.69 MP). Same input, fal 832x1248 vs local 672x1024: **different latent
grid (52x78 vs 42x64 latent-pixels), so the two can never produce the same image at the same seed.**

**image_size is accepted (c20):** `image_size={"width":672,"height":1024}` returned exactly
672x1024. So fal can be told to render at the local grid; whether that makes fal match the local
output was not tested (would need the local pipeline in the loop).

## Q7 Aspect / rounding rule (six data points)

| input | in aspect | output | out aspect | Δ aspect |
|---|---|---|---|---|
| 682x1024 | 0.6660 | 832x1248 | 0.6667 | +0.10 % |
| 1001x1503 | 0.6660 | 832x1248 | 0.6667 | +0.10 % |
| 650x1024 | 0.6348 | 800x1280 | 0.6250 | −1.54 % |
| 682x900 | 0.7578 | 864x1152 | 0.7500 | −1.03 % |
| 557x1666 (swap) | 0.3343 | 576x1760 | 0.3273 | −2.11 % |
| 1024x682 | 1.5015 | 1248x832 | 1.5000 | −0.10 % |

All six are reproduced exactly by: **scale to area 1024² = 1,048,576 px preserving aspect, then
floor each side to a multiple of 32** (e.g. 650x1024: k=1.2549 → 815.7x1285.0 → 800x1280;
682x900: k=1.3070 → 891.4x1176.3 → 864x1152; 557x1666: k=1.0630 → 592.1x1771 → 576x1760).
Multiples of 16 do not fit (650x1024 would give 816, observed 800); area targets outside
[1.037, 1.090] MP do not fit. So fal uses **/32 floor at ~1.05 MP**; local uses **/16 floor at
≤1.15 MP with no upscaling**. Both floor, so both shave up to 31 (fal) / 15 (local) pixels off one
side: aspect error up to ~2 % on tall images.

Stretch vs crop: at ≤2 % aspect change the crop-vs-squash test (top-35 % MAD of output against
the input resized either way) cannot separate the two (1.79 vs 1.72, 3.41 vs 3.43); visually
(`sbs/q7_aspect_rule.jpg`) the person is not perceptibly stretched in any of the six. A non-multiple
of-16 width (682, 650, 1001) is handled the same way as any other width — no special case.

## Q2 Reference-size sensitivity

| pair | MAD | px!=0 | px>16 | PSNR |
|---|---|---|---|---|
| (a) R 0.93 MP vs (b) R025 0.25 MP: c01 vs c05 | 0.527 | 62.6 % | 0.33 % | 39.1 |
| (a) vs (b) second run: c01 vs c26 | 0.455 | 57.1 % | 0.29 % | 40.3 |
| (a) vs R2 2.0 MP: c01 vs c15 | 0.415 | 55.8 % | 0.24 % | 40.9 |
| (a) vs (c) R3 3.0 MP: c01 vs c06 | 0.377 | 47.6 % | 0.25 % | 40.7 |
| R2 vs R3: c15 vs c06 | 0.371 | 46.0 % | 0.26 % | 39.8 |

(a) and (c) are **not identical** (MAD 0.377), but the difference is at the measured
non-determinism floor (0.35-0.41), and so is (a) vs (b) (0.46-0.53) and 2 MP vs 3 MP (0.37). The
*expected* signature of a reference actually used at 0.25 MP vs 3 MP (12× fewer tokens) is a
change far larger than the floor — for scale, steps 4→8 gives MAD 3.7 and one duplicated
reference gives 1.25. Reference size from 0.25 MP to 3 MP therefore has **no effect beyond
noise**; the reference is re-sampled to a fixed size inside fal before use. The exact cap value
cannot be read from these numbers (identity was never reached because the endpoint itself is
not always pixel-deterministic). Side-by-side: `sbs/q2_reference_size.jpg`.

## Q4 Steps

| pair | MAD | px!=0 | px>16 | PSNR | inference time |
|---|---|---|---|---|---|
| default vs num_inference_steps=4: c01 vs c09 | 0.000 | 0 % | 0 % | inf | 0.94 s / 0.94 s |
| steps 4 vs 8: c01 vs c08 | 3.723 | 99.8 % | 1.01 % | 30.0 | 0.94 s / 1.67 s |
| input P vs c01 (how much the edit changes the image at all) | 14.71 | 100 % | 18.9 % | 19.8 | |
| input P vs c08 | 11.79 | 100 % | 10.0 % | 20.3 | |

Default **is 4 steps** (pixel-identical to explicit 4, and ~1.8× slower at 8). 8 steps gives a
visibly different but not better image (`sbs/q3q4_determinism_steps.jpg`); it sits closer to the
input (MAD 11.8 vs 14.7 from P).

## Q5 Image order / count

- **Swap [R, P]** (c10): output 576x1760 — the canvas follows image 1 (the garment ref). Content
  (`sbs/q5_order_count.jpg`): the woman from P appears (identity taken from image 2, not the
  mannequin from image 1) wearing P's own oversized tee, with R's black jeans and sneakers, on P's
  grey studio background. So the result is a mix, not the clean "person becomes the garment" —
  the model treats the human photo as the identity source regardless of position, but layout /
  size follow image 1.
- **Duplicate reference [P, R, R]** (c11, c25): MAD 1.254 vs c01, 84.8 % pixels, px>16 1.16 %,
  PSNR 30.5 — 3× the noise floor and reproducible (c11 = c25 exactly). Visible change: a wrist-watch
  from R appears on the left wrist, feet-region MAD 3.42, the lace artefact disappears. So the
  second copy of R is **not** deduplicated; it is fed as an additional conditioning image with its
  own position and does change the result.

## Q6 Input encoding

| pair | MAD | px!=0 | px>16 | PSNR |
|---|---|---|---|---|
| PNG data-URI vs JPEG q95 data-URI: c01 vs c12 (=c28) | 0.435 | 52.7 % | 0.32 % | 39.6 |
| PNG data-URI vs uploaded PNG file URL: c01 vs c13 | 0.000 | 0 % | 0 % | inf |
| default output vs output_format="png": c01 vs c22 | 0.000 | 0 | 0 | inf |
| default output vs output_format="jpeg" (decoded): c01 vs c23 | 0.828 | 90.3 % | 0.04 % | 45.9 |

JPEG-q95 inputs give an output that is reproducible (c12 = c28) but differs from the PNG-input
output by MAD 0.435 — the same magnitude as the endpoint's own non-determinism, so JPEG q95
encoding of the inputs is **harmless at the level this test can resolve**. Transport (data-URI vs
uploaded file) is irrelevant. The default output format is PNG (with C2PA chunk); asking for JPEG
costs MAD 0.83 of pure compression noise (px>16 0.04 %).

## Differences from our local pipeline that are now MEASURED (not assumed)

1. **Output canvas.** fal renders at ~1.05 MP (area 1024², sides floored to /32) whatever
   image 1's size, upscaling a 0.70 MP input to 832x1248; local renders at min(native, 1.15 MP)
   floored to /16 (672x1024 for the same input). Different latent grid → same seed cannot give
   the same image. fal accepts `image_size` and honours it exactly (672x1024 returned).
2. **Default steps = 4** on fal (pixel-identical to explicit 4; 8 steps changes MAD 3.7).
3. **Not always pixel-deterministic.** 2 of 11 identical-argument repeats differed (MAD 0.35-0.41,
   PSNR ~40 dB); no run is ever byte-identical because of a per-response C2PA `caBX` chunk. A local
   run with a fixed generator is deterministic on one GPU; equality checks must be pixel-level
   with a ~0.4 MAD tolerance.
4. **Reference size does not matter** on fal from 0.25 to 3 MP (all diffs ≤ floor); fal
   re-samples image 2 to a fixed size internally. The local path passes the PIL image to diffusers
   at whatever size it is given (not measured here — see unknowns).
5. **Duplicate references are not collapsed**: [P, R, R] ≠ [P, R] (MAD 1.25, deterministic).
6. **Image-1 position controls the canvas, not the identity**: swapped order gives image 1's
   size with the human from image 2.
7. **JPEG-q95 inputs, data-URI vs upload, and output_format=png all change nothing beyond the
   noise floor**; output_format=jpeg adds MAD 0.83 of compression noise.

## Still unknown

- The exact reference cap value (only "0.25-3 MP all equivalent within noise" is measured).
- Whether fal with `image_size` = local grid + same seed reproduces the local diffusers output
  (needs a local run with the same inputs; not in this probe's scope).
- What causes the occasional non-determinism (different worker / GPU / kernel autotune) — not
  observable from the API.
- Whether fal's resampling filter for image 1 (bicubic vs area vs Lanczos) matches PIL's; only
  the size rule is measured.
- Guidance scale default on fal (not probed; the distilled model may ignore it).
- Crop vs squash at the ≤2 % aspect change: the test cannot resolve it; no visible stretch.
