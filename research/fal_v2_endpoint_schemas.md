# fal.ai V2 Endpoint Schemas (verified live 2026-08-14)

Source: fal model `/api` and `/llms.txt` pages, blog.fal.ai, FireRedTeam GitHub/HuggingFace.
All prices are fal list prices at verification time.

---

## 1. fal-ai/qwen-image-edit-2511

Status: live, unchanged from V1 usage.

Required:
- `prompt` (string) — edit instruction
- `image_urls` (list[string])

Optional (defaults):
- `negative_prompt` ("")
- `num_images` (1, range 1-4)
- `num_inference_steps` (28, range 1-50)
- `guidance_scale` (4.5, range 1-20)
- `seed` (int; echoed in output, same seed + same prompt reproduces across same model version)
- `image_size` (defaults to input image dimensions)
- `output_format` ("png"; jpeg/png/webp)
- `enable_safety_checker` (true; disabling requires account authorization, unauthorized requests always checked)
- `acceleration` ("regular"; none/regular/high)
- `sync_mode` (false)

Output: `images[]` (url/width/height/content_type), `seed`, `prompt`, `has_nsfw_concepts[]`, `timings`.

Price: $0.03 per output megapixel.

Gotchas: flagged-unsafe images come back black. Leave `acceleration` at "regular" or pin to "none" if determinism drift is observed across runs.

---

## 2. fal-ai/flux-2/klein/4b/distilled/edit

Status: live.

Required:
- `prompt` (string)
- `image_urls` (list[string]) — maximum 4 images

Optional (defaults):
- `seed` (int)
- `num_inference_steps` (4, range 4-8)
- `image_size` (defaults to input image size)
- `num_images` (1, range 1-4)
- `enable_safety_checker` (true; same authorization rule, unsafe -> black image)
- `output_format` ("png"; jpeg/png/webp)
- `sync_mode` (false)

Output: `images[]`, `prompt`, `seed`, `has_nsfw_concepts[]`, `timings`.

Price: $0.014 first megapixel + $0.001 each additional MP. Input images free.

Gotchas: distilled 4-step model — very cheap/fast, expect quality ceiling. No negative_prompt, no guidance_scale exposed. 2-reference input (person + garment) is well within the 4-image cap.

---

## 3. FASHN try-on — ENDPOINT ID CHANGED

Status: the bare id `fal-ai/fashn/tryon` now returns 404 (both `/api` and `/llms.txt`).
The model lives only at versioned ids:

- `fal-ai/fashn/tryon/v1.6` — latest (use this)
- `fal-ai/fashn/tryon/v1.5` — still live, "proven stability" tier

Note: the fal blog post on v1.5 is historical; v1.6 is the current top version. Both $0.075/generation.

### fal-ai/fashn/tryon/v1.6 schema

Required:
- `model_image` (string; URL or base64) — person
- `garment_image` (string; URL or base64) — garment

Optional (defaults):
- `category` ("auto"; tops/bottoms/one-pieces/auto)
- `mode` (performance/balanced/quality)
- `garment_photo_type` ("auto"; auto/model/flat-lay)
- `seed` (int, reproducible)
- `num_samples` (1, range 1-4)
- `output_format` ("png" or "jpeg")
- `moderation_level` (none/permissive/conservative)
- `segmentation_free` (true; set false to revert to legacy human-parsing pipeline)
- `sync_mode` (false)

Output resolution: fixed 864x1296. Price: $0.075 per generation.

### Diff vs V1-era usage

| Aspect | V1-era | Now |
|---|---|---|
| Endpoint id | `fal-ai/fashn/tryon` (unversioned alias worked) | alias 404s; must call `fal-ai/fashn/tryon/v1.6` |
| Person/garment fields | `model_image` / `garment_image` | unchanged |
| `category` | tops/bottoms/one-pieces | unchanged, default "auto" |
| Resolution | 864x1296 | unchanged (1MP upgrade announced but not shipped) |
| Price | ~$0.075/img | unchanged |
| New knobs | — | `segmentation_free` (default true), `garment_photo_type`, `moderation_level` |

Only breaking change is the endpoint id. Any V1 harness code pointing at the bare id must be updated.

---

## 4. FireRed Image Edit (v1.0 and v1.1)

### fal-ai/firered-image-edit (v1.0)

Required:
- `prompt` (string; English and Chinese)
- `image_urls` (list[string]) — multi-image references explicitly supported ("virtual try-on and style transfer")

Optional (defaults):
- `num_inference_steps` (30, range 2-50)
- `guidance_scale` (4, range 1-10)
- `num_images` (1, range 1-4)
- `seed` (int, reproducible)
- `negative_prompt` ("")
- `image_size` (defaults to input dimensions)
- `output_format` ("png"; also jpeg)
- `enable_safety_checker` (true; authorization rule, unsafe -> black)
- `acceleration` ("regular"; none/regular/high)
- `sync_mode` (false)

Price: $0.0325 per output megapixel, rounded up to nearest MP.

### fal-ai/firered-image-edit-v1.1

Status: live. Schema identical to v1.0 (same required/optional args, same defaults, same $0.0325/MP price). v1.1 release notes: optimized portrait consistency, multi-element fusion, stylized text reference, portrait makeup effects.

### Open-weights verdict: v1.1 IS OPEN — use v1.1

- GitHub (FireRedTeam/FireRed-Image-Edit) README: "The code and the weights of FireRed-Image-Edit are licensed under Apache 2.0."
- Timeline: 2026-02-14 released FireRed-Image-Edit-1.0 weights; 2026-03-03 released FireRed-Image-Edit-1.1.
- HuggingFace `FireRedTeam/FireRed-Image-Edit-1.1`: license tag apache-2.0, safetensors weight files present, 20B params BF16, loads via Diffusers `QwenImageEditPlusPipeline` (Qwen-Image-Edit architecture).
- A 1.0-Distilled (Lightning) variant also exists for faster local inference; no 1.1 distilled seen.

Conclusion: v1.1 weights are open under Apache 2.0, so the V2 open-weights constraint is satisfied by the v1.1 endpoint. Use `fal-ai/firered-image-edit-v1.1`; v1.0 fallback not needed.

Gotcha: 20B model — local deployment footprint is Qwen-Image-Edit-class, not small.

---

## 5. fal-ai/z-image/turbo/image-to-image

Status: live.

Required:
- `prompt` (string)
- `image_url` (string) — single image, not a list

Optional (defaults):
- `strength` (0.6, float) — img2img conditioning strength (denoise amount); this is the param name, not "denoise"
- `num_inference_steps` (8, range 1-8)
- `seed` (int, reproducible per model version)
- `num_images` (1, range 1-4)
- `image_size` ("auto")
- `enable_safety_checker` (true; authorization rule)
- `enable_prompt_expansion` (false) — adds $0.0025/request if enabled; keep OFF for determinism
- `output_format` ("png"; jpeg/png/webp)
- `acceleration` ("regular"; none/regular/high)
- `sync_mode` (false)

Output: `images[]`, `seed`, `prompt`, `has_nsfw_concepts[]`, `timings`.

Price: $0.005 per megapixel (+ $0.0025 if prompt expansion enabled).

Gotchas: as a refiner keep `strength` low (~0.2-0.4) or it will repaint garment detail; `enable_prompt_expansion` must stay false (nondeterministic rewriting + surcharge); max 8 steps.

---

## V2 arm registry implications

Harness interface: `args(person_url, garment_url, seed) -> dict`. All arms fix `num_images=1`, pass `seed`, and keep safety checker at default (cannot disable without account authorization anyway). PROMPT_VTON = the shared try-on instruction ("Dress the person in the first image in the garment from the second image..." per V1 conventions).

```python
# Arm 1: qwen2511
endpoint = "fal-ai/qwen-image-edit-2511"
args = {
    "prompt": PROMPT_VTON,
    "image_urls": [person_url, garment_url],
    "seed": seed,
    "num_images": 1,
    "negative_prompt": NEG_PROMPT,          # optional, "" if unused
    "acceleration": "none",                  # determinism-conservative
}

# Arm 2: flux2-klein
endpoint = "fal-ai/flux-2/klein/4b/distilled/edit"
args = {
    "prompt": PROMPT_VTON,
    "image_urls": [person_url, garment_url],
    "seed": seed,
    "num_images": 1,
}   # no negative_prompt / guidance_scale on this endpoint

# Arm 3: fashn (id changed — versioned path required)
endpoint = "fal-ai/fashn/tryon/v1.6"
args = {
    "model_image": person_url,
    "garment_image": garment_url,
    "category": "auto",                      # or per-pair override
    "mode": "quality",
    "seed": seed,
    "num_samples": 1,
    "output_format": "png",
}   # output fixed at 864x1296

# Arm 4: firered v1.1 (open weights confirmed, Apache 2.0)
endpoint = "fal-ai/firered-image-edit-v1.1"
args = {
    "prompt": PROMPT_VTON,
    "image_urls": [person_url, garment_url],
    "seed": seed,
    "num_images": 1,
    "negative_prompt": NEG_PROMPT,
    "acceleration": "none",
}

# Refiner: z-image turbo (input is an arm's output image, not person/garment)
endpoint = "fal-ai/z-image/turbo/image-to-image"
args = {
    "prompt": PROMPT_REFINE,
    "image_url": stage1_output_url,          # single URL, not a list
    "strength": 0.3,                         # tune 0.2-0.4; higher repaints garment
    "seed": seed,
    "num_images": 1,
    "enable_prompt_expansion": False,
    "acceleration": "none",
}
```

Cost note per pair at ~1MP output: qwen2511 $0.03, flux2-klein $0.014, fashn $0.075, firered $0.0325, z-image refine $0.005.
