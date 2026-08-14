# Open-Weights Model Catalog — Virtual Try-On V2 Scout (Aug 13, 2026)

Scope: every open-weights (self-hostable) model remotely relevant to the V2 deploy path
(person image + garment image → person wearing garment; open weights only, commercial
deployment in Magic Hour company code). Compiled from three parallel research sweeps
verified against live GitHub/HF/Civitai/arXiv pages on 2026-08-13. Complements the
V1-era API-focused `model-scout-shortlist.md`.

Per-model structure: what it is → good at → weak at → input conditions → output
conditions → open-weights details (license / VRAM / integration) → anything special.

---

## 0. Cross-cutting license traps (read first — these disqualify more "open" models than quality does)

1. **FLUX.1 trap.** FLUX.1-dev / Fill-dev / Kontext-dev / Krea-dev, FLUX.2-dev (32B),
   and FLUX.2-klein-**9B** are all BFL **Non-Commercial** (v1.1, Jun 2025, also pulled
   the commercial-outputs clause). Every LoRA/ControlNet/finetune on them inherits it:
   IDM-VTON-flux forks, CatVTON-FLUX, OmniTry, RefTon, Any2AnyTryon, FitVTON, DreamO,
   DreamOmni2, ACE++, UNO, catvton-flux. Only Apache FLUX models: **FLUX.1-schnell**
   and **FLUX.2-klein-4B**.
2. **InsightFace trap.** Code MIT, but all pretrained packs (buffalo_l, antelopev2,
   inswapper_128, SCRFD) are research-only; commercial license is sold separately.
   This poisons InstantID, PuLID, IP-Adapter FaceID, EcomID, InfiniteYou regardless of
   the adapter's own Apache tag. Clean escape: **AuraFace-v1** (Apache ArcFace clone).
3. **Training-data provenance.** Almost all academic VTO models (incl. MIT-licensed
   OOTDiffusion and Leffa) trained on VITON-HD / DressCode — research-only datasets.
   Weights license may read MIT; provenance still needs legal review for production.
4. **The Qwen-Image stack is Apache 2.0 end-to-end** — base, Edit-2509/2511,
   InstantX ControlNets, DiffSynth blockwise CNs, PAI Fun union CNs. This is where
   2026 VTO community activity actually lives.
5. Smaller traps: NTU S-Lab license = NC (CodeFormer, StableSR, ResShift, InvSR);
   OpenPose CMU ~$25K/yr; DensePose weights CC-BY-NC + bit-rotted; RMBG-2.0 (BRIA
   paid); Ultralytics YOLO AGPL; 4x-UltraSharp CC-BY-NC-SA; SegFormer fashion parsers
   (mattmdjaga, FASHN parser) inherit NVIDIA non-commercial source license; SUPIR/HYPIR
   NC addendum; Sapiens v1 CC-BY-NC (Sapiens2 is commercial-OK); no-license repos
   (PiSA-SR, Harmonizer, GPEN, OSDFace) = all rights reserved.

---

## 1. Dedicated virtual try-on models

### 1.1 Commercially clean — production-plausible

#### FASHN VTON v1.5 ⭐ (the standout 2026 release)
- Links: github.com/fashn-AI/fashn-vton-1.5 · hf.co/fashn-ai/fashn-vton-1.5 (Jan 27, 2026)
- **What it is:** 972M-param pixel-space MMDiT (no VAE), 8 double + 16 single stream
  blocks. FASHN (the commercial VTO vendor — our V1 fashn_v16 arm) open-sourced their v1.5.
- **Good at:** maskless (no parsing/DensePose in inference path); preserves tattoos,
  body characteristics, cultural garments; segmentation-free mode stops old-garment
  silhouette leakage; ~5s on H100; proprietary training data → clean provenance;
  pixel-space design directly targets identity degradation (no VAE round-trip).
- **Weak at:** fixed 576×864 output (sub-1K); imperfect body-shape preservation
  (synthetic data); transition artifacts on drastic garment-type swaps; paper unpublished.
- **Inputs:** person RGB + garment RGB + category (`tops`/`bottoms`/`one-pieces`);
  garment flatlay or on-model; DWPose auto-extracted in-pipeline.
- **Outputs:** 576×864 full re-render (pixel space), seeded/deterministic.
- **Weights:** **Apache 2.0 incl. deps (DWPose/YOLOX)**; ~2GB bf16, **~8GB VRAM → T4 OK**
  (Turing falls back fp32); reference PyTorch repo; no official diffusers/ComfyUI yet.
- **Special:** the only modern, dedicated, Apache-licensed VTO with a clean data story.
  Note: our V1 eval already showed fashn_v16 (API) as the identity/background champion;
  this is the self-hostable cousin. No training code.

#### OOTDiffusion
- Links: github.com/levihsu/OOTDiffusion · hf.co/levihsu/OOTDiffusion
- **What it is:** SD1.5 latent diffusion + "outfitting fusion" (garment UNet features
  fused into denoising UNet self-attention). Half-body (VITON-HD) + full-body (DressCode) ckpts.
- **Good at:** solid mid-tier 768×1024; light VRAM; big community, ComfyUI nodes; MIT.
- **Weak at:** face/identity drift; logo/text warping; below IDM-VTON/FitDiT on garment
  detail; unmaintained since 2024; Linux-only tested.
- **Inputs:** person + garment flatlay + category (0 upper / 1 lower / 2 dress);
  bundled human parsing + OpenPose run automatically.
- **Outputs:** 768×1024 masked-region re-render (inpainting style), seeded.
- **Weights:** **MIT** (VITON-HD/DressCode provenance flag); ~8–10GB VRAM → T4 OK.
- **Special:** no training code; ONNX parsing option.

#### JCo-MVTON (Alibaba DAMO)
- Links: github.com/damo-cv/JCo-MVTON · hf.co/Damo-vision/JCo-MVTON (Aug 2025)
- **What it is:** MM-DiT with co-attention branches for garment/person — a full
  finetune of FLUX.1-dev.
- **Good at:** mask-free; claimed FID 8.1 paired VITON-HD; 1024×1024; upper/lower/dress ckpts.
- **Weak at:** in-the-wild generalization and fine garment-attribute control (own admission);
  FLUX-scale heavy.
- **Inputs:** person + garment + text prompt; no masks/densepose.
- **Outputs:** 1024×1024 full re-render, seeded.
- **Weights:** tagged Apache-2.0 **but FLUX.1-dev derivative — BFL NC base arguably
  attaches; legal review required**. A100-40GB class; no T4; diffusers-based, no ComfyUI.
- **Special:** one of the few full-finetune (not LoRA) FLUX try-ons with released weights.

#### OrthoTryOn (ECCV 2026)
- Links: github.com/NJU-PCALab/OrthoTryOn (Jun 2026); LoRA + dataset on HF
- **What it is:** Orthogonal-subspace-projection LoRA on **LongCat-Image-Edit** doing
  try-on / try-off / pose transfer in one adapter, + Fisher-guided negative guidance.
- **Good at:** three tasks without interference; modern editing-model base; Apache 2.0.
- **Weak at:** background preservation needs an optional refinement step; validated only
  on VITON-HD/DeepFashion; brand-new, tiny ecosystem.
- **Inputs:** person + skeleton map (MMPose HRNet-W48) + garment image or description +
  editing instruction (they generate instructions with Qwen2.5-VL-7B). Pose-map
  preprocessing required; no densepose/mask.
- **Outputs:** editing-model re-render at LongCat defaults, seeded.
- **Weights:** **Apache 2.0** LoRA; LongCat-Image-Edit base Apache (verify current terms);
  large DiT → 24GB+, not T4.
- **Special:** training annotations released; "one adapter, three tasks" fits a product
  that also wants try-off.

#### DreamFit (ByteDance, AAAI 2025) — adjacent, not strict try-on
- Links: github.com/bytedance/DreamFit · hf.co/bytedance-research/Dreamfit
- **What it is:** garment-centric human **generation** (83.4M "Anything-Dressing
  Encoder" + LoRA) for FLUX and SD1.5 — generates a new person wearing the garment.
- **Good at:** garment fidelity from a single flatlay; pose-controlled generation; Apache 2.0.
- **Weak at:** does not preserve identity by default (new humans); the true try-on mode
  needs "keep image" masks whose generation code was never open-sourced.
- **Inputs:** garment + text; optional pose image; try-on mode needs person + keep-mask.
- **Outputs:** full generation ~1MP, seeded.
- **Weights:** **Apache 2.0**; SD1.5 variant T4-OK; FLUX variant 24GB+ **and NC base (flag)**.
- **Special:** useful for AI-model fashion shots, not user try-on.

### 1.2 Strong quality, license-blocked (evaluation baselines only)

#### IDM-VTON (ECCV 2024) — still the SDXL-era reference
- Links: github.com/yisol/IDM-VTON (~4.6k★) · hf.co/yisol/IDM-VTON
- **What it is:** SDXL-inpainting TryonNet + parallel GarmentNet (second SDXL UNet) +
  IP-Adapter for high-level garment semantics.
- **Good at:** best garment detail/text/logo fidelity of the open SDXL generation;
  robust in-the-wild with customization; the perennial quality pick in third-party
  comparisons; VTEdit-Bench best specialist on Shop2Model (3.60, FID 7.40).
- **Weak at:** heavy preprocessing (agnostic mask + DensePose + OpenPose/parsing);
  masked re-render can shift skin/hands; slow dual-UNet; dated vs 2026 DiTs.
- **Inputs:** person + garment flatlay + agnostic mask + DensePose + parsing
  (auto-runnable but heavy); 768×1024; upper/lower/dress.
- **Outputs:** 768×1024; inpaints masked region (unmasked pixels preserved by
  construction), seeded.
- **Weights:** **CC BY-NC-SA 4.0 — commercial blocked.** ~16–24GB fp16 (T4 borderline
  with offload); diffusers-based; popular ComfyUI node.
- **Special:** training code released; the Replicate/fal forks carry the same NC problem.

#### FitDiT (Tencent)
- Links: github.com/BoyuanJiang/FitDiT · HF gated · official ComfyUI repo
- **What it is:** SD3-class MMDiT, two-stage: mask prediction → garment synthesis, with
  garment-texture priors.
- **Good at:** highest-resolution academic VTO (**1152×1536**); best-in-class stripes/
  logos/text retention; interactive mask adjustment; official ComfyUI.
- **Weak at:** mask-based (stage-1 mask gates results); gated weights; heavy.
- **Inputs:** person + garment; auto try-on-area mask (editable); pose internal;
  upper/lower/dress.
- **Outputs:** up to 1152×1536 masked re-render, seeded.
- **Weights:** **CC BY-NC-SA 4.0, gated; commercial = Tencent Cloud paid API.** ~24GB
  bf16; aggressive offload ~10–12GB (slow) → T4 only barely.
- **Special:** the usual "best quality if the license didn't block you" answer.

#### CatVTON lineage (Zheng Chong)
- **CatVTON** (ICLR 2025; github.com/Zheng-Chong/CatVTON): SD1.5-inpainting
  concatenation try-on, 899M total / 49.57M trainable, no garment encoder.
  Good: **<8GB VRAM at 1024×768** (best efficiency/quality ratio, T4-friendly);
  built-in AutoMasker (SCHP+DensePose); ComfyUI nodes. Weak: SD1.5 faces/hands;
  mask-based. **CC BY-NC-SA 4.0.** Training code released.
- **CatVTON-FLUX:** official 37.4M LoRA for FLUX.1-Fill-dev — NC twice over.
- **CatV2TON:** DiT image+video try-on, 256/512 ckpts, CC BY-NC-SA; video is its point.
- **FastFit:** SD1.5-inpainting **multi-reference** try-on (tops+bottoms+shoes+bags at
  once, reference KV caching). The only open model that survives multi-garment
  (VTEdit MultiShop2Model 2.90, above klein 2.68). **Custom FastFit NC license**
  (commercial via LavieAI deal).

#### Leffa
- Links: github.com/franciszzj/Leffa · hf.co/franciszzj/Leffa
- **What it is:** diffusion try-on baseline + flow-field-in-attention regularization
  loss forcing target queries to attend to the right garment reference keys.
- **Good at:** fine texture fidelity with fewer detail distortions; ~6s/img A100 fp16;
  VITON-HD + DressCode ckpts; also pose transfer.
- **Weak at:** SCHP + DensePose preprocessing pipeline; 768×1024 cap; wild backgrounds.
- **Inputs:** person + garment + auto agnostic mask (SCHP) + DensePose; upper/lower/dress.
- **Outputs:** 768×1024 masked re-render, seeded.
- **Weights:** **MIT on the HF repo** (rare here) — **but VITON-HD/DressCode training
  data; provenance review before commercial use.** 24GB comfortable; T4 with offload.
- **Special:** the loss is model-agnostic — a candidate technique to retrain on clean data.

#### OmniTry (NeurIPS 2025)
- Links: github.com/Kunbyte-AI/OmniTry · weights on HF (Aug 2025)
- **What it is:** LoRA on FLUX.1-Fill-dev; unified mask-free try-on for **12 wearable
  classes** (garments + jewelry, glasses, hats, bags, watches, shoes, ties).
- **Good at:** accessories — essentially the only open model doing earrings/watches/bags
  well; mask-free localization; strong identity/background retention.
- **Weak at:** 28GB+ bf16 (A100 territory); garment-only quality slightly behind
  dedicated clothes models; no official ComfyUI.
- **Inputs:** person + object image, nothing else.
- **Outputs:** ~1MP full re-render, seeded.
- **Weights:** LoRA Apache 2.0, **FLUX.1-Fill-dev base = BFL NC → commercial blocked.**
- **Special:** OmniTry-Bench released; the mask-free transfer-from-unpaired-data
  training recipe is documented.

#### Any2AnyTryon (ICCV 2025)
- FLUX.1-dev unified try-on / try-off / model generation via prompt templates
  (`<MODEL>…<GARMENT>…<TARGET>…`); LAION-Garment dataset released. Mask-free mode;
  repaint mode needs AutoMasker; images cropped to ×16. **No explicit license +
  FLUX.1-dev NC base → treat as NC.** 24GB+ with group offloading.

#### RefTon (Qihoo 360, CVPR 2026)
- LoRA on FLUX.1-Kontext-dev; conditions on an optional **reference photo of the
  garment worn by another person** — boosts drape/realism in the e-commerce case where
  on-model shots exist. Up to 1024×768. **No license + Kontext NC base → NC.** Young repo.

#### FitVTON (Jun 2026) — garment-fit control
- Dual-LoRA on FLUX.1-Kontext: one LoRA controls fit geometry from structured text
  (loose/tight/length over 16 body prototypes), one does transfer; GarmentCodeVTON
  (78K simulated triplets) + FittingEffect3K benchmark released.
- The only open model addressing "how it fits" rather than "what it looks like".
- **Mixed licenses (MIT + NVIDIA NVSCL NC + SMPL-X) + Kontext NC base → NC overall.**
- Special: the GarmentCode + cloth-sim synthetic data pipeline is itself valuable.

#### Legacy / niche NC checkpoints (brief)
- **StableVITON** (CVPR 2024): SD1.5 PbE + zero-init cross-attn; full VITON-HD
  preprocessing stack; CC BY-NC-SA; T4-runnable; superseded by PromptDresser.
- **PromptDresser** (ICCV 2025): frozen SDXL dual-UNet + LLM prompts + prompt-aware
  masks for wearing-style control (tucked/open); assume NC.
- **HR-VITON** (ECCV 2022): GAN two-stage, 1024×768, sub-second — only relevant for
  GAN-speed throughput; CC BY-NC.
- **VITON-HD** (CVPR 2021): the original; CC BY-NC; historic.
- **MV-VTON:** multi-view try-on (front+back garment → any view); CC BY-NC-SA; masks/warp needed.
- **ITA-MDT** (CVPR 2025): masked diffusion transformer, lightweight; ckpts re-uploaded
  Oct 2025 after a wrong-weights upload (gotcha); license unlisted → research-only.
- **SIFT-VTON** (ICPR 2026): StableVITON + SIFT-correspondence supervision; 384×512;
  CC BY-NC-SA.
- **Mobile-VTON** (CVPR 2026): IP-Adapter on-device try-on; needs densepose; CC BY-NC-SA.
- **OmniVTON** (ICCV 2025): training-free steering of stock SD inpainting; heaviest
  preprocessing of all; pipeline code itself CC BY-NC.
- **IMAGDressing-v1:** SD1.5 "virtual dressing" (generates a model, not user try-on);
  weights research-only.
- **Kolors Virtual Try-On (Kwai):** demo Space only — **try-on weights never released**
  (Kolors issue #152). Not self-hostable.

### 1.3 Try-off models (garment extraction — preprocessing for the worn-garment case)

Every generator collapses when the garment reference is worn by another person
(VTEdit Model2Model: best universal 2.06; Qwen 1.17; klein 1.03). Try-off converts
worn photos to pseudo-packshots first.
- **fal/virtual-tryoff-lora** (HF): **Apache 2.0 on FLUX.2-klein-9B** — note the 9B base
  is NC, so for commercial use retrain the recipe on klein-4B. TRYOFF prompt →
  product-on-white; 300 pairs / 10k steps (a demonstrator).
- **kingroka Outfit Extractor** (Civitai 1940557, Qwen Edit LoRA): "extract the outfit
  onto a white background", strength 1.75–2. Apache-base stack.
- **TryOffDiff** (+ MGT multi-garment): SD1.4 + SigLIP; **SSPL license — effectively NC.**
- **cat-tryoff-flux:** FLUX.1-Fill finetune, ≥40GB VRAM, NC base.
- Maintained index: github.com/rizavelioglu/awesome-virtual-try-off.

### 1.4 Watch list — paper/demo only, no weights (as of 2026-08-13)
- **Voost** (NXN Labs, SIGGRAPH Asia 2025): bidirectional try-on/try-off DiT; HF Space
  demo only, repo CC BY-NC-SA, zero public models; commercial = contact NXN.
- **WearWow** (arXiv 2607.19923, Jul 2026): native 2K multi-garment mask-free try-on +
  promised WearWow-2K dataset — current SOTA-on-paper, no artifact anywhere yet.
- **BooW-VTON** (MIT repo): mask-free in-the-wild; training code/demo "coming soon",
  no HF weights — effectively unreleased.
- **Oxygen-TryOn** (JD, arXiv 2607.21694): claimed 9.36 single-item SOTA; no artifact;
  its re-eval protocol remains reusable for our scoring.
- Paper-only 2025–26: Tstars-Tryon 1.0, DiT-VTON, OmniDiT, LPH-VTON, DirectTryOn,
  FEAT, One-Model-For-All, PROMO; PG-VTON (CVPR 2026) repo essentially empty;
  DiffuseFit (MIT code, no weights, heavy preprocessing); SPM-Diff (weight release
  unconfirmed — verify before planning around it).
- Closed industrial: Google TryOnDiffusion, Alibaba OutfitAnyone / Wear-Any-Way,
  Kling/Kolors VTO, FASHN's own v2+ API models.

---

## 2. General instruction editors (multi-reference, open weights)

### Benchmark anchor — VTEdit-Bench (arXiv 2603.11734, v2 Jun 29 2026; verified from the PDF)
24,220 pairs; GPT-4o rubric 0–5 on model/cloth/quality consistency; overall = min of
the three. Key numbers:
- **Shop2Model overall:** klein **3.96** > Qwen-2511 3.64 > IDM-VTON 3.60 > CatVTON 3.39 >
  FLUX.2 3.36 > FastFit 3.08. Qwen-2511 has the **best cloth consistency of all 15
  models (4.77)** but weak identity (4.23); klein is balanced (4.61/4.68/4.48).
- **Shop2MultiView:** klein 3.99 > FLUX.2 3.38 > IDM 2.73 > Qwen 2.46.
- **Shop2MultiModel (multi-person):** klein 3.56 > FLUX.2 3.02 > Qwen 2.14.
- **Model2Model (worn-garment transfer):** everyone fails — CatVTON 2.25 > FLUX.2 2.06 >>
  Qwen 1.17 (identity collapse 1.60), klein 1.03 (cloth collapse 2.17).
- **MultiShop2Model (multi-garment):** FastFit 2.90 > klein 2.68 > FLUX.2 2.25 >>
  Qwen 0.34, DreamO 0.01.
- Caveat: paper doesn't say which klein size was tested (likely 9B) — reproduce S2M
  with 4B before betting the deploy path on the Apache variant.
- Other 2026 evals: OpenVTON-Bench (arXiv 2601.22725), Dress-ED (arXiv 2603.22607 —
  146k-quadruplet dataset + code, a finetuning resource), VTBench.

### 2.1 Primary candidates (license-clean)

#### Qwen-Image-Edit-2511
- Links: hf.co/Qwen/Qwen-Image-Edit-2511 · github.com/QwenLM/Qwen-Image · GGUF builds
- **What it is:** 20B MMDiT + Qwen2.5-VL conditioning (`QwenImageEditPlusPipeline`).
  Current V1 arm and family baseline.
- **Good at:** best cloth consistency of any model on VTEdit (4.77); strong multi-image
  fusion; 2511 merged popular community LoRAs, improved drift/character consistency vs
  2509; top text rendering (CN+EN); richest try-on LoRA ecosystem.
- **Weak at:** **identity drift is its documented weakness** (4.23 S2M; 1.60 M2M) — the
  exact V1 regression we're fixing; multi-garment collapse (0.34); residual zoom/crop
  drift across edits.
- **Inputs:** 1–3 images as a list (order matters; person first, garment second, index
  the prompt "Picture 1/Picture 2"); negative prompt; true CFG; ~1MP sweet spot;
  natively accepts depth/edge/keypoint condition images as extra inputs.
- **Outputs:** full re-render (no native mask channel), seed-deterministic, ~1024px class.
- **Weights:** **Apache 2.0.** ~40GB bf16 → A100-40GB with offload; fp8/GGUF Q4–Q8 run
  in 12–24GB; T4 only with aggressive quant (minutes/img). Full diffusers + ComfyUI.
- **Special:** Lightning 4–8-step distills; LoRA training trivial (ai-toolkit/ostris);
  the de-facto open finetuning base for VTO. **Family status verified: no open editor
  newer than 2511 — Qwen-Image-2.0 (Feb 2026) is API-only; weight requests unanswered
  through May 2026. Plan on 2511 as the terminal open release.**

#### FLUX.2 [klein] 4B / 9B (BFL, Jan 15 2026)
- Links: bfl.ai blog · hf.co/black-forest-labs/FLUX.2-klein-4B (+9b-fp8, base variants)
- **What it is:** rectified-flow transformers distilled from FLUX.2 32B; distilled and
  **undistilled "base"** checkpoints at 4B and 9B; unified T2I + multi-reference editing.
- **Good at:** **#1 open model on VTEdit shop-based try-on**; balanced identity+garment
  +quality (no weak dimension); sub-0.5s at 4 steps; multi-person scenes.
- **Weak at:** Model2Model collapse (can't lift garments off worn photos); text
  rendering below Qwen; distilled variants have low seed diversity and dead
  steps/guidance knobs; prompt-phrasing sensitivity.
- **Inputs:** multi-reference (practically 1–4) + prompt; ~1MP.
- **Outputs:** full re-render; distilled = fixed ~4 steps CFG 0; base variants have
  true CFG + negative prompts; seeded.
- **Weights:** **4B = Apache 2.0; 9B = BFL Non-Commercial** (treat as unusable in the
  deploy path). 4B ≈ 13GB bf16 → **T4 feasible at fp8, easy A100**; FP8 −40% VRAM/1.6×
  speed, NVFP4 −55%/2.7×. Diffusers `Flux2KleinPipeline` + ComfyUI day-one.
- **Special:** klein-4B-**base** (undistilled) is the obvious commercial LoRA-training
  target; fal's try-on/try-off LoRA recipes port to it.

#### FireRed-Image-Edit-1.0 (Xiaohongshu, Feb 14 2026) ⭐ new
- Links: github.com/FireRedTeam/FireRed-Image-Edit · HF + GGUF · arXiv 2602.13344
- **What it is:** 20B diffusion editing foundation model.
- **Good at:** **current open-source SOTA on general edit benchmarks** (GEdit-EN 7.94,
  above Qwen-Edit; ImgEdit 4.56); trained with a **differentiable identity-consistency
  loss** + DPO; README explicitly lists virtual try-on / multi-element fusion as
  capabilities; bilingual.
- **Weak at:** no third-party VTO eval yet (missed VTEdit's cutoff by 2 days); young
  ecosystem.
- **Inputs:** instruction + image(s), multi-image supported.
- **Outputs:** full re-render, diffusers pipeline, seeded.
- **Weights:** **Apache 2.0.** 20B → same math as Qwen (A100-40GB quantized; GGUF for
  16–24GB). Diffusers; ComfyUI via community.
- **Special:** the identity-consistency objective targets exactly the failure that
  kills Qwen-2511 on VTO — **highest-value new head-to-head to run.**

#### JoyAI-Image-Edit / Edit-Plus (JD.com, Apr/Jun 2026) — new
- Links: github.com/jd-opensource/JoyAI-Image
- **What it is:** 8B MLLM + 16B MMDiT unified model; **Edit-Plus (Jun 23 2026) adds
  multi-image composition** — the VTO input shape.
- **Good at:** spatial editing, long text rendering, multi-view; e-commerce heritage
  (JD retail data lineage plausible).
- **Weak at:** no public benchmark table; unproven identity preservation.
- **Inputs:** 1 image (Edit) or multiple (Edit-Plus) + instruction.
- **Outputs:** full re-render; diffusers ≥0.34.
- **Weights:** **Apache 2.0.** ~24B pipeline → A100-40GB class, not T4. Native ComfyUI
  since Jul 17, 2026.
- **Special:** freshest multi-ref editor available; worth a qualitative screen.

#### LongCat-Image-Edit (Meituan, Dec 2025)
- ~6B-class DiT editor; character-level text encoding; claimed SOTA-among-open at
  release; **~18GB VRAM with offload** (light for its class; borderline T4).
- **Weak at:** **single-image input only** → VTO needs a stitched person+garment canvas;
  eclipsed by FireRed within ~10 weeks; no official ComfyUI.
- **Weights:** **Apache 2.0**; diffusers `LongCatImageEditPipeline`.
- **Special:** the base OrthoTryOn builds on.

#### FLUX.2 [dev] (32B) — teacher/eval only
- Best cross-task robustness on VTEdit (avg rank 2.2; best on multi-view/multi-person);
  up to 10 refs, 4MP. Cloth consistency 4.09 (loses fine garment detail vs Qwen).
- **BFL Non-Commercial** → offline eval/teacher only. ~64GB bf16; official 4-bit ~18–20GB;
  A100-40GB at 4-bit.

### 2.2 Usable with caveats

- **FLUX.1 Kontext [dev]** (12B, Jun 2025): iterative editing with good identity
  persistence; most-LoRA'd editing base after Qwen; single-reference natively (stitch
  hacks for two); GGUF/nunchaku ~8GB. **NC license (v1.1 also pulled commercial
  outputs) — avoid production.** No Kontext 2 — FLUX.2/klein is the successor.
- **DreamOmni2** (CVPR 2026 Highlight): edit+gen LoRAs + VLM on Kontext-dev for
  reference-driven edits; **poor at whole-garment try-on** (VTEdit S2M FID 27.4);
  NC base.
- **OmniGen2** (BAAI, ~7B: Qwen2.5-VL-3B + 4B decoder): flexible multi-image
  conditioning, easy hardware (~17GB, offload lower; T4-marginal); **Apache 2.0**;
  mid-pack-to-weak on VTO (S2M FID 34.0). Pairs with the UMO LoRA for an all-Apache
  multi-identity stack. No OmniGen3 as of Aug 2026.
- **Step1X-Edit v1p2** (StepFun, Nov 2025): ~19B, thinking–editing–**reflection** loop
  that reviews outputs and corrects unintended changes (interesting for identity-drift
  mitigation); Apache 2.0; ~42GB fp16 / ~24GB quant; single-image oriented; slow.
  (Step Image Edit 2, Apr 2026: API-only — no HF weights found.)
- **BAGEL** (ByteDance-Seed, 7B-active MoT): unified understanding+editing; Apache 2.0;
  now behind Qwen/FLUX.2/FireRed; 40GB+ recommended. No BAGEL-2 (Seed's newer image
  work went closed into Seedream/Seededit).
- **Emu3.5 / Emu3.5-Image** (BAAI, 34B autoregressive): Apache 2.0 but ~90GB weights →
  multi-A100/H100 only; slow AR decoding; no VTO evidence. Not practical.
- **HiDream-E1.1** (17B sparse DiT, MIT, 24GB, ComfyUI): decent general editor,
  single-image, never a VTO standout.
- **HiDream-O1-Image** (May 8 2026) — dark horse: **8B pixel-native unified transformer,
  no VAE, no external text encoders**; T2I + instruction editing + **multi-reference
  subject-driven personalization with skeleton/layout conditioning** to 2048².
  **MIT license.** Full ~20GB; **O1-Image-Dev distilled FP8 ~10GB → T4-feasible.**
  DiffSynth-Studio support. No third-party try-on eval yet.
- **VIBE-Image-Edit** (SberAI, Jan 2026): 2B Qwen3-VL guide + 1.6B Sana decoder; 2K
  output in ~4s on H100; tiny/cheap; single-image; small decoder limits garment texture.

### 2.3 Marginal / legacy / license-dead (named so nobody re-scouts them)

- **UNO** (weights CC BY-NC + FLUX base; VTEdit S2M FID 32.8 — weak anyway).
- **USO** (style-oriented; FLUX.1-dev base → NC in practice).
- **UMO** (CVPR 2026): RL multi-identity-consistency LoRA for UNO **or OmniGen2** —
  the OmniGen2 path is all-Apache; an ingredient, not a VTO model.
- **DreamO** (Apache code+weights, explicit ID + Try-On tasks, ComfyUI native,
  8GB nunchaku — but FLUX.1-dev base blocks commercial self-hosting; and VTEdit
  overall 1.62, multi-garment 0.01).
- **UniWorld V1** (Apache, ~12B): S2M FID 38.7 — not competitive.
- **ACE++** (ali-vilab, FLUX.1-Fill-dev LoRAs, mask-guided local editing): MIT-labeled
  but NC base; legacy, no ACE-2.
- **Lumina-DiMOO** (8B discrete diffusion-LLM, Apache 2.0): research-interesting,
  no VTO evidence. Other Lumina models are T2I/AR-gen — irrelevant.
- **AnyDoor / Paint-by-Example:** 2022–23 exemplar-pasters; unclear/RAIL licenses,
  mask-required, lose garment detail badly; historical only.
- **HunyuanImage 3.0 / Instruct** (80B MoE): Tencent Community License **excludes EU/UK/
  South Korea + >100M MAU clause**; 3×80GB recommended (4-bit ~48–56GB). Not practical,
  license-risky. Completeness only.
- **Kolors / "Kolors 2":** Kolors 2 does not exist as an open release; Kolors is 2024
  SDXL-arch T2I with a registration requirement; not an editor.
- **SD3.5 + edit adapters:** never materialized; no official edit/inpaint adapter;
  not a candidate.
- **MAI/muse/LongCat single-image cuts, Seedream, GPT-Image, Gemini:** closed — out of
  scope for V2 (see V1 shortlist for those).

---

## 3. Try-on LoRAs on Apache bases (the 2026 mainstream recipe)

- **kingroka "Clothes Try On (Clothing Transfer)"** — Civitai 1940532 (+ workflow
  1941790 + Outfit Extractor 1940557), Qwen-Image-Edit base.
  Input = single stitched canvas: garment flatlay on white LEFT, person RIGHT; prompt
  "put the clothes on the left onto the person on the right"; strength 1.25–1.75.
  Wide body-type adherence; huge adoption; commercial image use allowed; fp8 + 4–8-step
  lightning ComfyUI template. Weak: complex patterns; shoes/hats/accessories
  inconsistent. Trained on original Qwen-Image-Edit → verify behavior on 2511.
- **"Attach Outfit & Try On [Qwen & Klein]"** — Civitai 2367983; variants for Qwen Edit
  2509 AND FLUX.2 klein 4B/9B; two separate images (person + product-on-white), trigger
  "attach the outfit in Image 2 to the person in Image 1"; 43.4k downloads.
  **License contradiction on the page ("Apache 2.0" + "non-commercial use only") —
  treat as NC**; 537 fully synthetic training images.
- **FoxBaze/Try_On_Qwen_Edit_Lora_Alpha** (HF, Apache 2.0): multi-garment layout
  (subject top, garments along bottom), gendered prompt, 832×1248; struggles ≥5
  garments; ostris ai-toolkit trained.
- **Outfit Transfer Helper** — Civitai 2111450, companion LoRA for cleaner transfers.
- **fal/flux-klein-9b-virtual-tryon-lora** (HF, Apache 2.0 LoRA): 3-image conditioning
  (person + top + bottom → one output), "TRYON …" prompt template; trained only 2000
  steps on fal trainer — a demonstrator. 9B base is NC → **for commercial use, re-train
  the recipe on klein-4B-base** (training repo example: LightCooling/flux2-vton-lora).
- Takeaway: the center of gravity moved from bespoke dual-UNet VTO architectures to
  **LoRAs on general Apache editors** — maskless, preprocessing-free, retrainable on
  our own data with ai-toolkit-class tooling.

---

## 4. Supporting pipeline models

### 4.1 Identity preservation / restore (the V1 regression fix)

Generation-time adapters:
- **InstantID** (SDXL): stable ID lock, but SDXL-only, abandoned Jul 2024, and
  **checkpoints research-only + antelopev2 → NC.**
- **PuLID / PuLID-FLUX:** best classic open face fidelity; "lossless" insertion keeps
  edits intact; **Apache code/weights but InsightFace encoder + FLUX-dev base → NC**;
  near-clean path = SDXL-PuLID + AuraFace encoder swap; stalled since 2025.
- **InfiniteYou** (ByteDance InfuseNet): SOTA-class similarity; **CC BY-NC + FLUX base —
  dead end**; ~43GB bf16.
- **PhotoMaker V2** (TencentARC): **Apache 2.0 weights — the clean classic**; SDXL;
  1–4 refs; lower raw similarity than InstantID/PuLID; V1's CLIP path avoids
  InsightFace (audit which extraction path you compile); T4-fine.
- **IP-Adapter FaceID family:** ~100MB adapters, T4-trivial, but cards say "research
  purposes only"; the non-FaceID CLIP IP-Adapters are Apache but weaker at identity.
- **ConsistentID** (MIT, TPAMI 2026, InsightFace inside), **EcomID** (antelopev2 trap),
  **UniPortrait** (research-grade), **WithAnyone** (ICLR 2026, new SOTA-class on FLUX —
  academic/NC, benchmark only).
- **Key gap: no InstantID/PuLID-style zero-shot face adapter exists for Qwen-Image as
  of mid-2026** — only ControlNets and per-person LoRAs. Qwen-2511 itself shipping
  better face consistency is part of the answer.

Face swap as post-edit identity restore (highest-leverage category):
- **inswapper_128** (InsightFace): de-facto one-shot swapper; 128px (needs restore
  pass); **NC — InsightFace sells commercial licenses directly** (the one negotiated
  license with outsized impact).
- **FaceFusion** (29.6k★, active Aug 2026): ships its own **HyperSwap 1a/1b/1c 256px**
  models with better occlusion handling; code OpenRAIL-AS (commercial OK with behavior
  restrictions); **HyperSwap is the commercial-plausible swap path to evaluate.**
- **ReActor** (ComfyUI, GPL-3.0 + inswapper → NC in practice); **ReSwapper** (AGPL,
  quality below inswapper); SimSwap/HifiFace dead.

Face restoration:
- **GFPGAN v1.3/1.4** — **Apache 2.0**, default commercial-safe restorer; blend 0.3–0.5
  (over-smooths at full strength); CPU/T4 trivial.
- **CodeFormer** — better on severe degradation, **S-Lab NC — blocked.**
- **RestoreFormer++** — **Apache 2.0**, quality between the two.
- **DiffBIR (face mode)** — Apache 2.0, strong on heavy degradation, multi-step,
  ~12–16GB, T4 with tiling.
- **PMRF** (ICLR 2025, MIT) — posterior-mean rectified flow, notably identity-faithful:
  right objective for "restore without changing who it is".
- No-license/NC: GPEN, OSDFace, InvSR — skip.

Identity embeddings (metric + conditioning):
- **ArcFace/buffalo_l/antelopev2:** standard 512-d cosine metric — **packs NC**;
  tolerated for internal eval, never shipped.
- **AuraFace-v1 (fal):** **Apache 2.0** ArcFace clone (99.65% LFW), drop-in
  insightface-compatible ONNX — **production identity metric + gate.**
- **AdaFace:** better on low-quality faces, weights NC — internal scoring only.

License-clean identity-restore stack (no negotiated licenses):
edit (2511/FireRed) → deterministic face paste-back where garment doesn't intersect
head → differential-diffusion seam blend → GFPGAN/RestoreFormer++/PMRF only if face
structurally altered → **AuraFace cosine gate + auto-retry (best-of-N)**. With one
negotiated license (InsightFace or FaceFusion HyperSwap): add a swap-restore step —
the single highest-impact identity lock known in production VTO.

### 4.2 Pose / structure control

- **Qwen ecosystem (Apache end-to-end — matches the editor):**
  - Edit-2509/2511 **natively accepts pose/depth/edge condition images as inputs** —
    feed a DWPose skeleton render + "keep the pose from the skeleton". Zero extra
    weights; first thing to A/B.
  - **InstantX/Qwen-Image-ControlNet-Union** (Apache, 2B, canny/softedge/depth/pose,
    1328² training): the standard "lock body, edit garment" tool; diffusers + native
    ComfyUI; A100-40GB with offload/fp8.
  - **DiffSynth blockwise ControlNets** (Apache, lightweight, **training scripts
    published** — the train-your-own-garment-CN path) + unified control LoRA.
  - **alibaba-pai Fun-Controlnet-Union** for Qwen-Image-2512 (Apache, Jan 2026).
- **Z-Image-Turbo** (6B, Apache) + PAI Fun-CN-Union 2.1 (Apache, 1.9GB lite, 8-step):
  **the T4-viable pose-controlled generator of 2026** — cheap pose-locked refiner stage.
- FLUX CNs (Shakker Union-Pro-2.0 etc.): best FLUX pose control but NC base — skip.
- SDXL: **xinsir controlnet-union-sdxl / openpose-sdxl** (Apache 2.0, T4-comfortable).
- Keypoint extractors: **DWPose (Apache, default — 133 whole-body kps, OpenPose-format
  renders, <1GB)**; **RTMPose/RTMW via rtmlib** (Apache, accuracy pick, avoids mmcv);
  **ViTPose++** (Apache, accuracy ceiling, needs a detector); **Sapiens2 pose** (Apr
  2026, 308 kps, commercial-OK license); avoid OpenPose (CMU $25K/yr), Ultralytics
  (AGPL), MediaPipe (33 pts — too sparse).
- Depth: **Depth Anything V2 Small** (Apache) or **Depth Anything 3 MONO-LARGE**
  (Apache, current SOTA, T4-fine); Marigold (Apache, slow, offline); DepthPro (research-only).
- **DensePose is effectively dead in 2026:** archived, detectron2 bit-rot, weights
  CC-BY-NC/ambiguous. Replace with Sapiens2 seg/normals or DWPose+parsing; the
  Qwen-Edit lineage doesn't need a dense prior at all.
- Softedge: **TEED** (MIT, 58K params) for garment edges; PiDiNet has a research-only
  rider inside its "MIT" license — audit ComfyUI aux packs.

### 4.3 Human parsing & garment segmentation / masking

- **SAM 3 / 3.1** (Meta, Nov 2025 / Mar 2026): **text-promptable concept segmentation**
  ("dress", "person wearing red shirt") returning all instances; ~0.9B; HF
  `Sam3Model`; custom SAM license, **commercial permitted**. **The 2026 default for
  garment-prompted masks.** SAM 2.1 (Apache) for point/box prompts.
- **Grounded-SAM-2 / Grounding DINO** (Apache end-to-end): the Apache-only alternative,
  slightly worse/slower. GDINO 1.5+/DINO-X are API-only.
- **SCHP** (MIT): still the de-facto standard inside try-on repos; ATR ckpt = the
  fashion one (Upper-clothes/Skirt/Pants/Dress/Face/Arms); frozen ~2020 (use
  forks/ONNX); 473px coarse edges; T4-trivial.
- **Sapiens2** (Meta, Apr 2026): 0.1B–5B; 29-class body-part seg, 308-kp pose,
  normals, matting (May 2026); 1024×768 native; **commercial-OK license**
  (bans surveillance/deepfakes); 0.8–1B on T4. **Best commercial-safe replacement for
  the DensePose+SCHP stack**; ComfyUI integration still thin.
- License-trapped parsers: **mattmdjaga/segformer_b2_clothes** and the **FASHN Human
  Parser** (SegFormer-B4, purpose-built for VTO masking, hands separated) both inherit
  the **NVIDIA non-commercial source license** — widely missed. Sapiens v1 CC-BY-NC.
- Cutouts: **BiRefNet** (MIT incl. weights, HR 2048² variant, excellent hair — default
  person/garment cutout); **BEN2** (MIT, 94.6M, claims to beat RMBG-2.0);
  InSPyReNet (MIT); MODNet (Apache, portrait-only). Avoid RMBG-2.0 (BRIA paid);
  U2Net cloth-seg archived May 2026 (legacy).
- What VTO repos actually do (verified from source): CatVTON/Leffa AutoMasker =
  DensePose + SCHP-ATR + SCHP-LIP → garment region per category → **convex hull over
  garment+arms → dilate + Gaussian smooth → subtract face/hair/hands protection AFTER
  dilation**. Agnostic masks must over-cover the old garment (any leaked pixel
  reconstructs it); 15–30px dilation at 768–1024px.
- **Commercial-safe 2026 mask stack:** SAM 3 garment region (∪ SCHP-ATR) → hull with
  arms → dilate → subtract Sapiens2/SCHP-LIP protection. Drop DensePose entirely.

### 4.4 Inpainting / compositing (paste-back & repair)

- **FLUX.1-Fill-dev:** still the open fill-quality reference — **NC, blocked.**
  **No FLUX.2 Fill model exists** as of Aug 2026; klein inpainting = crop/stitch recipes.
- **Qwen inpainting stack (all Apache):** InstantX **Qwen-Image-ControlNet-Inpainting**
  (2B, 1328², `QwenImageControlNetInpaintPipeline`, native ComfyUI ≥0.3.59; works with
  base Qwen-Image; describe the target image, not instructions); DiffSynth
  **Blockwise-CN-Inpaint** (+ training scripts); DiffSynth **EliGen** (entity-level
  regional attention — "edit garment region only, freeze face/hands"); Edit-2511
  crop→edit→composite recipes.
- **Z-Image-Turbo** (6B, Apache, 16GB, 8-step): diffusers `ZImageInpaintPipeline`
  (latent blend, soft masks) — cheapest permissive diffusion repair pass. Z-Image-Edit
  still unreleased.
- **SDXL-inpainting-0.1** (OpenRAIL++): genuinely T4-friendly; the standard cheap
  "composite → soft mask → 0.3–0.5 denoise seam repair".
- **BrushNet** (better background preservation, SD-class, license mostly-Apache with
  third-party carve-outs); **PowerPaint v2** (MIT/Apache on RealisticVision, task
  tokens, T4-fine, served via IOPaint); **xinsir Union ProMax** (Apache, inpaint+tile
  with any SDXL ckpt).
- **Moebius** (ECCV 2026, Jun 2026): **0.22B** linear-attention inpainter claiming
  FLUX-Fill parity at >15× speed; **Apache 2.0**. Mask-fill only (not text-guided) —
  can't generate a garment, but the 2026 upgrade for background/hole repair. New — validate.
- **LanPaint** (GPL-3.0, fine server-side): training-free Langevin masked sampling with
  any model incl. Qwen — much better mask coherence than naive latent blending, at
  2–5× sampling cost.
- Fast non-diffusion fill: **LaMa** (Apache, CPU-capable, via IOPaint) — the workhorse
  for "old garment longer than new → fill background"; MI-GAN (MIT, mobile); MAT (NC).
- Harmonization/QC: **libcom** (Apache, pip): PCTNet harmonization, shadow gen, color
  transfer, **BargainNet harmony score as an automatic QC gate on composites**;
  INR-Harmonization (Apache); `cv2.seamlessClone` Poisson baseline. Harmonizer
  (ZHKKKe) has no license file — do not deploy.
- Soft-mask paste-back recipe (no extra weights): composite original face/hands/bg
  hard-alpha → GrowMask + Gaussian 16–48px feather seam band → **Differential
  Diffusion** (ComfyUI core) at denoise 0.3–0.5 → Inpaint-Crop/Stitch at crop-native
  res → optional 0.1–0.2 denoise full-frame pass to re-unify grain. diffusers
  equivalent: soft `mask_image` + `strength`.

### 4.5 Refinement / realism passes & upscalers

- License scoreboard — blocked: SUPIR, HYPIR (SupPixel commercial clause), StableSR/
  ResShift/InvSR (S-Lab), PiSA-SR (no license), 4x-UltraSharp v1+v2 (CC-BY-NC-SA),
  all FLUX-dev realism LoRAs. Clean: Real-ESRGAN (BSD-3), AuraSR-v2 (Apache),
  SwinIR/HAT/DAT/ATD (Apache), SeedVR2 (Apache), DiffBIR v2/SeeSR/OSEDiff (Apache),
  Z-Image-Turbo (Apache), RealVisXL V5/Juggernaut (OpenRAIL++/check RunDiffusion terms),
  TSD-SR (Stability Community License, free <$1M revenue).
- **SeedVR2** (ByteDance, ICLR 2026, 3B/7B): one-step DiT restoration; community
  consensus SOTA open generative upscaler of 2026, **Apache 2.0**; 3B fp16 ~18GB+,
  FP8 12–24GB, GGUF to 6–12GB; verify it doesn't regularize small logos.
- **Real-ESRGAN** (BSD-3): zero-risk fidelity pass — will not change garment print or
  identity; `realesr-general-x4v3` has a denoise knob; <2GB, runs anywhere.
- **AuraSR-v2** (Apache, GigaGAN-style 4x, ~618M, fast on T4): middle ground — crisper
  than ESRGAN without diffusion hallucination; occasional tile seams.
- **OSEDiff** (Apache): cheap one-step SR, T4-friendly.
- img2img realism refiners: **Z-Image-Turbo @ ~0.2 denoise** (2026 sleeper: Apache,
  sub-second, praised for natural non-plastic skin — best quality-per-VRAM Apache
  pass); Qwen-Edit-2511 "enhance realism, keep garment identical" (needs paste-back
  after); **RealVisXL V5 / Juggernaut @ 0.15–0.25 denoise + CN-Tile** (the T4-class
  de-plastic pass; ≥0.3 denoise measurably drifts identity/prints).
- Detail workflows: **Ultimate SD Upscale** (GPL, internal use fine) per-tile at
  0.15–0.25 denoise — large tiles or repeating garment patterns desync;
  Impact Pack FaceDetailer **warning: default denoise replaces the face** — ≤0.3 with
  the person's own crop, or skip faces.
- **Detail transfer / frequency separation (the garment-fidelity insurance):**
  kijai IC-Light `DetailTransfer` (Apache — blend original high-frequency garment
  detail onto the refined image, maskable); spacepxl Image-Filters (MIT — frequency
  separate/combine, color match); wavelet color fix (license-clean reimplementations
  in KJNodes/Image-Filters). Recommended composite: refine → wavelet color fix vs
  original → garment-mask paste-back of original high frequencies → seam blend.

### 4.6 Eval / metric models (brief — harness exists; upgrades only)

- **Garment similarity: Marqo-FashionSigLIP (Apache 2.0)** — +57% MRR over FashionCLIP
  on fashion retrieval; drop-in cosine-embedding swap. This is the Phase-2
  `garment_sim` fix the README already calls for (better than generic CLIP).
- **DINOv2** (Apache, ungated) for the standard DINO garment-fidelity metric;
  DINOv3 is commercial-OK but gated + Meta-IP friction — not worth it for a scalar.
- **Identity metric: AuraFace** (Apache) shipped; ArcFace/AdaFace internal-eval only.
- **Preference/aesthetic:** HPSv3 (MIT, Qwen2-VL-7B backbone, ~20GB) if adding an axis.
- **Open VLM judge:** **Qwen3-VL** (2B–32B dense + 30B-A3B MoE, Apache 2.0) —
  Qwen3-VL-8B as pairwise judge (~20GB bf16); InternVL3.5-8B (Apache) alternative;
  GLM-4.5V (MIT, but ~4×80GB).

---

## 5. Shortlist & pipeline synthesis (Magic Hour V2 lens)

License-clean AND VTO-credible generator arms, ranked by current evidence:

| # | Arm | License | VRAM class | Why |
|---|---|---|---|---|
| 1 | **FLUX.2 klein-4B (+ retrained try-on LoRA on klein-4B-base)** | Apache 2.0 | ~13GB, T4 fp8 / easy A100 | VTEdit shop→model leader (verify 4B reproduces the likely-9B score); sub-second |
| 2 | **Qwen-Image-Edit-2511 + kingroka-style LoRA** | Apache 2.0 | fp8/GGUF 12–24GB, A100 comfortable | Best garment fidelity anywhere; richest LoRA/tooling ecosystem; identity drift must be fixed downstream |
| 3 | **FASHN VTON v1.5** | Apache 2.0 | ~8GB, T4 OK | Only clean dedicated VTO; pixel-space; maskless; 576×864 cap is the tradeoff |
| 4 | **FireRed-Image-Edit-1.0** | Apache 2.0 | like Qwen | Edit-bench SOTA + identity-consistency training objective; unbenchmarked on VTO — run it |
| 5 | **JoyAI-Image-Edit-Plus** | Apache 2.0 | A100 class | Newest multi-ref editor, e-commerce lineage; qualitative screen |
| 6 | **HiDream-O1-Image(-Dev)** | MIT | FP8 ~10GB, T4 OK | Pixel-native, skeleton conditioning, multi-ref; dark horse |

Excluded from the deploy path by license (kept as eval baselines): FLUX.2-dev,
klein-9B, Kontext-dev + everything on them (DreamOmni2, ACE++, UNO/DreamO, OmniTry,
RefTon, catvton-flux), IDM-VTON, FitDiT, CatVTON/FastFit, HunyuanImage 3.0 (territory),
InsightFace packs, CodeFormer, SUPIR/HYPIR.

Universal failure modes to design around (VTEdit-verified): identity drift under
garment influence (worst in Qwen — our V1 regression is the general case); garment
extraction from worn photos (everyone fails → route through try-off first); multi-
garment composition (everyone fails except FastFit-style specialists → composite to
one canvas or chain edits); fine texture/small logo loss vs specialists (→ frequency-
separation detail transfer + crop-and-stitch); multi-person one-of-two dressing errors.

Reference license-clean pipeline (slots + picks):

| Slot | Primary | Runner-up |
|---|---|---|
| Try-off (worn garments) | kingroka Outfit Extractor (Qwen) | retrained klein-4B TRYOFF LoRA |
| Generator | klein-4B or Qwen-2511 (+LoRA) | FASHN v1.5 / FireRed |
| Pose lock | native 2511 condition image + DWPose | InstantX Qwen CN-Union pose |
| Garment mask | SAM 3 text-prompt ∪ SCHP-ATR → hull → dilate → subtract protection | Grounded-SAM-2 (all-Apache) |
| Cutouts | BiRefNet-HR (MIT) | BEN2 / SAM 3 |
| Identity restore | face paste-back + differential-diffusion seam + GFPGAN/PMRF if altered; AuraFace gate + retry | negotiated: InsightFace inswapper or FaceFusion HyperSwap |
| Background fill | LaMa | Moebius |
| Harmonize + QC | libcom PCTNet + BargainNet score | Poisson baseline |
| Realism pass | Z-Image-Turbo img2img @ ~0.2 | RealVisXL V5 + tile upscale |
| Fidelity insurance | frequency-separation detail transfer + wavelet color fix | — |
| Upscale | Real-ESRGAN (zero drift) | SeedVR2-3B FP8 (then re-run detail transfer) |
| Eval upgrades | Marqo-FashionSigLIP · DINOv2 · AuraFace · Qwen3-VL-8B judge | HPSv3 |

Biggest 2026 shifts vs the 2024 canon: (1) FASHN v1.5 is the first serious Apache
dedicated VTO; (2) gravity moved from bespoke dual-UNet architectures to LoRAs on
general Apache editors (maskless, no preprocessing); (3) DensePose/parsing pipelines
now mark a model as legacy; (4) Voost and WearWow are the strongest papers still
withholding weights; (5) identity restoration remains the part with the fewest fully
open options — the one place a negotiated license (InsightFace/HyperSwap) buys real quality.

---

Sources: consolidated from three research sweeps (2026-08-13); primary references —
VTEdit-Bench arXiv:2603.11734 · fashn-ai/fashn-vton-1.5 · Qwen/Qwen-Image-Edit-2511 ·
black-forest-labs/FLUX.2-klein-4B · FireRedTeam/FireRed-Image-Edit ·
jd-opensource/JoyAI-Image · HiDream-ai/HiDream-O1-Image · Kunbyte-AI/OmniTry ·
Zheng-Chong/Awesome-Try-On-Models · rizavelioglu/awesome-virtual-try-off ·
civitai.com/models/1940532 · fal/flux-klein-9b-virtual-tryon-lora ·
facebookresearch/sam3 · facebookresearch/sapiens2 · InstantX Qwen ControlNets ·
ByteDance-Seed/SeedVR · fal/AuraFace-v1 · Marqo/marqo-fashionSigLIP; per-model
GitHub/HF/Civitai pages linked inline in the agent reports (session transcripts).
