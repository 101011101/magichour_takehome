[web / aie]: build klein virtual try-on (ER) script

Colab:
[ADD LINK — notebook is built at vp/tryon_er.ipynb, not yet uploaded]

GPU:
A100 40GB. Every number below was measured on an A100-SXM4-40GB with the whole pipeline resident and no offload. Both the generative model and the two ONNX models in garment preparation run on the GPU.
Weights on the GPU are ~16.5GB before activations. Peak VRAM [ADD — never run on a GPU from this repo], so plan on 40GB until it is measured; a 24GB card previously needed CPU offload, which changes timings.
A different GPU type produces different pixels for the same seed, so its failure rate has to be re-measured before these numbers are quoted for it.

Model:
FLUX.2 [klein] 4B, run twice per try-on. Five weights, all pinned by revision:
- Transformer: Photoroom/FLUX.2-klein-4b-fp8-diffusers @408c457f3589e17a1be1dae5bf0dcaf09cd4985f, subfolder transformer_bf16 (3.88B params, 7.75GB bf16)
- Text encoder (Qwen3-4B), VAE, tokenizer, scheduler, configs: black-forest-labs/FLUX.2-klein-4B @e7b7dc27f91deacad38e78976d1f2b499d76a294 (~8.04GB + 0.17GB)
- Garment preparation, none of them generative: BiRefNet_lite (onnx-community/BiRefNet_lite-ONNX, 44.6M params), SCHP human parser (basso4/humanparsing @4fd18f98561bae00b5c24342c92307b4780b2a8d, 66.7M params), MediaPipe Selfie Multiclass, MediaPipe Pose Landmarker lite
Total download ~16.5GB. Take transformer_bf16 only from Photoroom, and skip BFL's transformer/ and its single-file flux-2-klein-4b.safetensors.
No LoRAs. The three in the models/loras folder (RebelReal4B, RealSkin4B, ConsistenceEdit4B) must not be loaded — every measurement here is on a stack without them, and none of it transfers to a LoRA'd stack.

Modes:
- Virtual try-on: a photo of a person and a photo of a garment in, the person wearing that garment out
Not text-to-image, and not general image editing. The prompts are fixed and not exposed.

Inputs:
- Person image — required. Sets the output's aspect ratio and resolution
- Garment image — required. A photo of the garment being worn by someone
- Seed — optional integer. Random when blank, and always returned
- MAX_RES — optional integer, caps the longer side of the output. Blank is the default and gives the full ~1MP canvas, which is also the maximum
- No prompt, no width, no height: the prompts are fixed inside the script, and the dimensions come from the person image
- Each image may be supplied as a local path or an http(s) URL; the script prompts for an upload when the field is blank
- REFERENCE_IMAGE and OUTPUT_IMAGE set where the prepared garment and the finished try-on are written
Handling the product should do before calling: decode with EXIF orientation applied; flatten PNG transparency onto white; reject or warn on person photos below ~0.5MP, since the output is always ~1MP and a smaller input is being scaled up beyond anything tested.

Outputs:
- Try-on image, ~1MP, in the person image's aspect ratio
- The seed used, needed to reproduce the image or to redraw it
- The prepared garment reference, an intermediate image — written to disk at REFERENCE_IMAGE and cached under /content/cache, keyed by a hash of the garment image plus a pipeline version; cache it, see Notes

Generation time (A100), per request:
- Try-on: 2.28s median. The garment is already prepared, so this is the whole per-request cost
- Model load at process start: 354-532s from a network-backed cache; [ADD — load time from local disk not measured]. Load once and keep the process warm

Garment preparation (once per garment, cached, off the request path):
- Bald pass: 1.48s median
- Crop, BiRefNet and the parser on GPU: [ADD — GPU crop time not yet measured]
- A garment is prepared once and reused by every user who tries it on, so this does not appear in per-request latency

Resolution:
1MP (1,048,576 px) is the maximum, in general and in every aspect ratio. The output takes the person photo's aspect ratio at ~1MP, each side a multiple of 32. What 1MP comes to:
- 1:1 -> 1024x1024
- 3:4 -> 864x1152, and 4:3 -> 1152x864
- 2:3 -> 832x1248, and 3:2 -> 1248x832
- 9:16 -> 768x1344, and 16:9 -> 1344x768
The ceiling is a hard limit, not a tuning choice. Above 1MP the model crosses an internal threshold and runs on a sampling schedule it was not trained for, so quality falls off. It cannot render 1080p or 2K. If a larger deliverable is needed, generate at 1MP and upscale the finished image afterwards.
MAX_RES can only lower the output. Blank, the default, is the full ~1MP canvas above. A value caps the longer side, rounding down to a multiple of 32; a value at or above that canvas's own longer side (1344 at most) changes nothing. Examples for a 3:4 person photo: 864x1152 by default, 768x1024 at MAX_RES 1024, 576x768 at MAX_RES 768. Below 1MP is untested for quality.

Cost:
- ~CAD 0.45 of A100 time per 1,000 try-ons, garments already prepared
- ~CAD 0.54 per 1,000 with garment preparation amortised in, at the test set's ratio of 93 new garments per 1,000 try-ons
- [ADD CREDITS]

Notes:
- Two calls, and only one of them is per request. Preparing a garment (bald pass, then the crop) is per garment and its result is identical for every user; the try-on is per request. Cache the prepared garment keyed by a hash of the garment image plus a pipeline version string, so a pipeline change invalidates it instead of silently mixing old and new references. It does not expire otherwise.
- Redraw contract: when a user marks a result as failed, run the try-on again with the same person image, the same cached garment and a new seed that has not been used for that pair. Do not re-prepare the garment. About 72% of failed images come back clean on a new seed; the failures that survive every seed are faults in the garment reference, which a new seed cannot fix.
- There is no automatic quality check. The user pressing "fail" is the only signal that a result was bad, so the redraw has to be user-triggered.
- Expected first-draw failure rate is roughly 3-6%, where a failure is a human calling the image unusable — most often the person's original clothing still showing through the new garment, or a limb or hand defect. The range is a marking range from one reviewer over 200 garment/person pairs, mostly front-facing. After one redraw the rate lands near 1.7%.
- Determinism: the same person image, garment reference, seed, weights, library versions and GPU type give a byte-identical image. Log the seed with every request so any customer result can be reproduced for support.
- Garment photos should show the garment being worn by a person. Flat-lay, product and mannequin photos are untested on this path. When the garment photo has no findable head the pipeline falls back to a cruder head estimate; log which route fired so those garments can be reviewed.
- Must not be changed, each is load-bearing: both prompts, 4 sampling steps, guidance 0.0, bfloat16, a CPU random generator for the seed, the fixed seed 46 used when preparing a garment, batch size 1, the pinned model revisions, and the 1MP ceiling.
- The two ONNX models in garment preparation must be verified to be on CUDA at startup. The GPU provider can fail to load and fall back silently, which runs several times slower; the script raises instead of continuing.
- [ADD: AI Image Generator, AI Image Editor, a standalone try-on product, or a combination]
- [ADD: whether the existing klein script's loader is reused — its canvas and sampling defaults differ from this one and must not be inherited]
