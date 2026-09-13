[web / aie]: build klein virtual try-on (ER) script
Colab:
https://colab.research.google.com/github/101011101/magichour_takehome/blob/v3.3-lock/vp/tryon_er.ipynb

GPU:
Prototyping was on A100 40GB but we can use the same one we use in prod for Flux 2 Klein (G4). Every timing and failure rate below was measured on the A100: expect G4 to be faster, and re-check the failure rate on it before quoting these figures, since a different GPU produces different pixels for the same seed.

Model:
FLUX.2 [klein] 4B, run at most twice per try-on (once for a product shot). Five weights, all pinned by revision:
- Transformer: Photoroom/FLUX.2-klein-4b-fp8-diffusers @408c457f3589e17a1be1dae5bf0dcaf09cd4985f, subfolder transformer_bf16 (3.88B params, 7.75GB bf16)
- Text encoder (Qwen3-4B), VAE, tokenizer, scheduler, configs: black-forest-labs/FLUX.2-klein-4B @e7b7dc27f91deacad38e78976d1f2b499d76a294 (~8.04GB + 0.17GB)
- Garment preparation, none of them generative: BiRefNet_lite (onnx-community/BiRefNet_lite-ONNX, 44.6M params), SCHP human parser (basso4/humanparsing @4fd18f98561bae00b5c24342c92307b4780b2a8d, 66.7M params), MediaPipe Selfie Multiclass, MediaPipe Pose Landmarker lite
Total download ~16.5GB. Take transformer_bf16 only from Photoroom, and skip BFL's transformer/ and its single-file flux-2-klein-4b.safetensors.
No LoRAs. The prod Flux 2 Klein setup loads three (RebelReal4B, RealSkin4B, ConsistenceEdit4B); this script must not — every measurement here is on a stack without them, and none of it transfers to a LoRA'd stack.

Inputs:
- Person image — required. Sets the output's aspect ratio and its resolution
- Garment image — required. A photo of the garment, worn by someone or shot on its own
- Region — optional, one of: full (default), upper, lower. full swaps the whole outfit. upper swaps what the person is wearing above the waist and leaves everything below it alone; lower is the mirror of that. It changes two things inside the script: the garment reference is cut at the person's hip line, and call 2 is sent a sentence naming the half. Nothing else about the request changes.
- Max resolution — optional integer, default 1536. Constrains the longer dimension of the output. The aspect ratio of the person photo is always preserved; this only ever lowers the result, never raises it, and it cannot lift the 1MP ceiling. Sides stay on a multiple of 32
- Seed — optional integer. Random when blank, and always returned; the redraw below depends on it
- Each image may be supplied as a local path or an http(s) URL
Handling the product should do before calling: decode with EXIF orientation applied, and flatten PNG transparency onto white. The script refuses person photos below ~0.5MP, and a small photo yields a small output rather than being stretched, so set whatever minimum the product wants above that floor.
Region only applies to garment photos with a person in them, and the script enforces that itself: it checks the garment photo for a person, and if there is none it treats the request as full and says so. A flat-lay sent as upper comes back as a whole-outfit swap rather than a bad cut. The UI can make the same check at upload time if it would rather grey the options out.

Outputs:
- Try-on image, at the person photo's own resolution capped at 1MP, in its aspect ratio — see Resolution
- The seed used, needed to reproduce the image or to redraw it
- The region requested and the region applied, with the reason whenever they differ

Generation time (A100):
- Try-on: ~1.9s, for any garment that has been used before
- The first try-on of a garment nobody has used yet: ~4.0s end to end (2.1s preparation + 1.9s try-on)
- A region request costs the same as a whole-outfit one
- Model load at process start: 6s from local disk with a warm cache, up to ~9 minutes from a network-backed cache. Load once and keep the process warm

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
1MP is the ceiling because klein is optimised for ~1MP: above it the model crosses an internal threshold and runs on a sampling schedule it was not distilled for, and quality falls off. It cannot render 1080p or 2K at generation time — if the product needs a consistent deliverable size, upscale the finished image after generation. Max resolution can only lower the output below this. The region does not change any of this: the output is the person photo's own size whichever region was requested; the region changes what is swapped inside the frame, not the frame.

Additional info for context - not needed to implement

Garment preparation process
- The script first checks whether the garment photo has a person in it, and that decides the route
- Worn photo: bald pass 1.48s median, then the crop 0.58s median on an A100, with BiRefNet and the human parser on CUDA and MediaPipe and an OpenCV filter on CPU, where they stay by design. The same crop with the ONNX models on CPU takes 8.14s, so the GPU is worth 14x here. ~2.1s in total
- Product shot (nobody in it): no bald pass and no head crop, only the background matte — one image-model call fewer
- If a garment is offered in more than one region, prepare them together: the bald pass does not depend on the region and one mask serves all three cuts, so all three references cost ~3.3s per garment against ~2.1s for full alone. Cutting them one at a time recomputes that mask each time and costs far more
- Cache the prepared reference under the garment, the region and the route. A garment prepared for full is not a reference for upper
- The GPU path needs onnxruntime-gpu==1.22.0 on a CUDA 12 runtime. Newer builds advertise CUDA, fail to load it, and fall back to CPU silently. This was verified on the A100; confirm the wheel loads its CUDA provider on G4 before relying on it
- A garment is prepared once and reused by everyone who tries it on, so this never appears in per-request latency
- Every figure above is warm. The first call after the model loads pays CUDA warm-up: measured once on a fresh A100 runtime it was 3.5s for the bald pass, 2.9s for the crop and 2.9s for the try-on, settling to the numbers above afterwards. Send a throwaway request after startup if first-user latency matters

Additional notes:
Two calls, and only one of them is per request. Preparing a garment is per garment and its result is identical for every user; the try-on is per request. Cache the prepared garment keyed by a hash of the garment image, the region, the route and a pipeline version string, so a pipeline change invalidates it instead of silently mixing old and new references. It does not expire otherwise.
The script tells worn photos from product shots itself, on the upload, before it generates anything. The check counts head pixels (face plus hair) with a segmentation model the crop already loads — no extra model and no language model. Measured over 56 worn garment photos and 17 flat-lay or ghost-mannequin ones, it made no error in either direction.
Verified end to end: the notebook linked above was run on an A100 over 44 cases — all 17 product shots and 5 worn garments, each at upper and lower — and every case behaved as designed.
Redraw contract: when a user marks a result as failed, run the try-on again with the same person image, the same cached garment and a new seed that has not been used for that pair. Do not re-prepare the garment. About 72% of failed images come back clean on a new seed; the failures that survive every seed are faults in the garment reference, which a new seed cannot fix.
There is no automatic quality check. The user pressing "fail" is the only signal that a result was bad, so the redraw has to be user-triggered.
Expected first-draw failure rate is roughly 3-6%, a failure being a human calling the image unusable — most often the person's original clothing showing through the new garment, or a limb or hand defect. A separate count over the whole fold put the shipped configuration at 2.6%. Both are one reviewer; they come from different instruments and should not be averaged.
Determinism: the same person image, garment reference, seed, weights, library versions and GPU type give a byte-identical image. Log the seed with every request so any customer result can be reproduced for support.
Garment photos work both ways. Most of the measurement is on garments worn by a person, and that is the best-supported input. Product shots — flat-lay and ghost-mannequin — were tested separately on 10 garments and came out indistinguishable from a route that skips the person-side step, so they are usable for whole-outfit requests. They are not suitable for upper or lower: there is no person in them to find a waist on.
Log which route the garment took, which head-finder fired, and any region fallback with its reason. They are recorded per garment and are the signal for reviewing odd inputs.
Already set correctly in the script, and not tunable when porting it to the backend: all four prompts (the bald pass, the whole-outfit call 2, and the upper and lower region variants of call 2), 4 sampling steps, guidance 0.0, bfloat16, a CPU random generator for the seed, the fixed seed 46 used when preparing a garment, batch size 1, the pinned model revisions, no LoRAs, and the 1MP ceiling. Each was measured; changing any of them invalidates the numbers in this ticket.
The two ONNX models in garment preparation must be verified to be on CUDA at startup. The GPU provider can fail to load and fall back silently, which runs several times slower; the script raises instead of continuing.
Ships in: a standalone try-on product.
What the region actually does: the garment reference is cut at the hip line, which comes from the pose detector's hip landmarks on the prepared garment frame, and call 2 is sent a sentence naming the half being replaced. Both are needed. Cutting the reference alone was tried and does not work — the model replaces the whole outfit anyway, because the instruction says to. The reference is not an instruction.
If the hip line cannot be found, if the requested half would keep less than 15% of the garment, or if the reference it would produce has a side under 64px (the image model's own minimum input), the request falls back to full and records which of those fired. It never guesses a cut at a fraction of the frame height. A waist-up photograph asked for lower is the case this protects: before this rule, two such requests crashed inside the image model instead of falling back.
Evidence level, and it is lower than the rest of this ticket: the selector was judged by eye on 12 cells at one seed by one reviewer, on pairs that already worked. It is a feasibility result, not a rate.
The failure rates quoted in this ticket (3-6%, and 2.6% fold-wide) describe whole-outfit requests. No rate has been measured for a region request, and those figures should not be quoted for one.

Examples of Input and Output:
https://drive.google.com/drive/folders/14cS44V7-vjrXM704R2o8jB_TEMK9bRfm?usp=sharing
