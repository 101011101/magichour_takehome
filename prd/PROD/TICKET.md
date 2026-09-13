<!-- SNAPSHOT, 2026-09-12. The live ticket is Ray's Google Doc; this file is the copy it was
     written from and is not edited in place any more. Changes since are in
     TICKET_AMENDMENTS.md, pastable section by section. -->

[web / aie]: build klein virtual try-on (ER) script

Colab:
https://colab.research.google.com/github/101011101/magichour_takehome/blob/v3.3-lock/vp/tryon_er.ipynb

GPU:
A100 40GB, everything resident, no offload. Weights are ~16.5GB before activations; peak VRAM [ADD — not yet measured], so plan on 40GB. A 24GB card previously needed CPU offload, which changes the timings below.
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
- Person image — required. Sets the output's aspect ratio and its resolution
- Garment image — required. A photo of the garment, worn by someone or shot on its own
- Seed — optional integer. Random when blank, and always returned
- No prompt, no width, no height, no resolution setting: the prompts are fixed inside the script and the dimensions come from the person photo
- Each image may be supplied as a local path or an http(s) URL
Handling the product should do before calling: decode with EXIF orientation applied, and flatten PNG transparency onto white. The script refuses person photos below ~0.5MP, and a small photo yields a small output rather than being stretched, so set whatever minimum the product wants above that floor.

Outputs:
- Try-on image, at the person photo's own resolution capped at 1MP, in its aspect ratio — see Resolution
- The seed used, needed to reproduce the image or to redraw it
- The prepared garment reference, an intermediate image, written to disk and cached — see Notes

Generation time (A100), per request:
- Try-on: ~1.9s. The garment is already prepared, so this is the whole per-request cost
- Model load at process start: 354-532s from a network-backed cache; [ADD — load time from local disk not measured]. Load once and keep the process warm

Garment preparation (once per garment, cached, off the request path):
- Bald pass: 1.48s median
- Crop: 0.58s median on an A100, with BiRefNet and the human parser on CUDA and MediaPipe and an OpenCV filter on CPU, where they stay by design. The same crop on the same machine with the ONNX models on CPU takes 8.14s, so the GPU is worth 14x here
- So a new garment costs ~2.1s to prepare. End to end, the first try-on of a garment nobody has used yet is ~4.0s (2.1s preparation + 1.9s try-on); every try-on of that garment afterwards is ~1.9s
- The GPU path needs onnxruntime-gpu==1.22.0 on a CUDA 12 runtime. Newer builds advertise CUDA, fail to load it, and fall back to CPU silently
- A garment is prepared once and reused by everyone who tries it on, so this never appears in per-request latency
- Every figure above is warm. The first call after the model loads pays CUDA warm-up: measured once on a fresh A100 runtime it was 3.5s for the bald pass, 2.9s for the crop and 2.9s for the try-on, settling to the numbers above afterwards. Send a throwaway request after startup if first-user latency matters

Resolution:
The output is the person photo's own size, capped at 1MP (1,048,576 px), each side rounded down to a multiple of 32. The script never enlarges a photo; it only bounds one larger than 1MP. Worked examples:
- 4000x3000, a 12MP phone photo -> 1152x864
- 3000x4000, the same photo held portrait -> 864x1152
- 1920x1080 -> 1344x768, and 1080x1920 -> 768x1344
- 1024x1024 -> 1024x1024
- 900x1200 -> 864x1152
- 700x900 -> 672x896
- 768x704 -> 768x704
So any large photo lands at ~1MP whatever its shape, and a small one comes back at its own size rather than inflated.
1MP is the ceiling because klein is optimised for ~1MP: above it the model crosses an internal threshold and runs on a sampling schedule it was not distilled for, and quality falls off. It cannot render 1080p or 2K at generation time, and there is no setting to raise or lower the output — if the product needs a consistent deliverable size, upscale the finished image after generation.

Cost:
A100 at ~USD 0.50/hour (CAD 0.689 at 1 CAD = 0.7214 USD, 12 Sep 2026).
- ~USD 0.26 per 1,000 try-ons, garments already prepared
- ~USD 0.29 per 1,000 with garment preparation amortised in, at the test set's ratio of 93 new garments per 1,000 try-ons
- [ADD CREDITS]

Notes:
- Two calls, and only one of them is per request. Preparing a garment (bald pass, then the crop) is per garment and its result is identical for every user; the try-on is per request. Cache the prepared garment keyed by a hash of the garment image plus a pipeline version string, so a pipeline change invalidates it instead of silently mixing old and new references. It does not expire otherwise.
- Every garment goes through both steps. There is no branch and no detection — a flat-lay is prepared exactly like a worn photo.
- Redraw contract: when a user marks a result as failed, run the try-on again with the same person image, the same cached garment and a new seed that has not been used for that pair. Do not re-prepare the garment. About 72% of failed images come back clean on a new seed; the failures that survive every seed are faults in the garment reference, which a new seed cannot fix.
- There is no automatic quality check. The user pressing "fail" is the only signal that a result was bad, so the redraw has to be user-triggered.
- Expected first-draw failure rate is roughly 3-6%, a failure being a human calling the image unusable — most often the person's original clothing showing through the new garment, or a limb or hand defect. A separate count over the whole fold put the shipped configuration at 2.6%. Both are one reviewer; they come from different instruments and should not be averaged.
- Determinism: the same person image, garment reference, seed, weights, library versions and GPU type give a byte-identical image. Log the seed with every request so any customer result can be reproduced for support.
- Garment photos work both ways. Most of the measurement is on garments worn by a person, and that is the best-supported input. Product shots — flat-lay and ghost-mannequin — were tested separately on 10 garments and came out indistinguishable from a route that skips the person-side step, so they are usable.
- Product shots do cost more than they need to. The pipeline still runs its person-side step on them, repainting a few percent of the garment for no visible benefit. Skipping it for product garments would save one model call each; quality did not depend on it either way.
- Log which head route the garment preparation used. It is recorded per garment and is the signal for reviewing odd inputs.
- Already set correctly in the script, and not tunable when porting it to the backend: both prompts, 4 sampling steps, guidance 0.0, bfloat16, a CPU random generator for the seed, the fixed seed 46 used when preparing a garment, batch size 1, the pinned model revisions, and the 1MP ceiling. Each was measured; changing any of them invalidates the numbers in this ticket.
- The two ONNX models in garment preparation must be verified to be on CUDA at startup. The GPU provider can fail to load and fall back silently, which runs several times slower; the script raises instead of continuing.
- Ships in: a standalone try-on product.
- [ADD: whether the existing klein script's loader is reused — its canvas and sampling defaults differ from this one and must not be inherited]
