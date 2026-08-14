# Deterministic editing components — practical quality assessment (Aug 2026)

Scope: the deterministic pieces proposed in `prd/v2/` — the garment re-cropper
(`POTENTIAL_FEATURES.md` #1) and the item-grouping / semantic-decomposition stack
inside the intention-aware fidelity guardrail (`INTENTION_AWARE_FIDELITY.md`
steps 1–3). Question answered: how good are these off-the-shelf, today, and where
do they break.

## 1. Garment re-cropping (segment → white-fill → tight crop)

**Verdict: effectively solved for product-style garment photos; the guaranteed
fallback chain in the PRD is still the right design for worn-garment inputs.**

- On flat-lay / ghost-mannequin / on-white garment photos, this is a trivial
  salient-object case. **BiRefNet** (MIT incl. weights) produces a soft alpha
  good enough that the tight crop is just the alpha bounding box. ~0.5–1 s per
  1024px image on a T4; `BiRefNet_lite` or InSPyReNet (MIT) for CPU/MPS.
  RMBG-2.0 is CC-BY-NC (BRIA paid for commercial) *and* is itself a BiRefNet
  derivative — no reason to touch it. BEN2 (MIT base, 94.6M params, ~378MB) is
  the lighter A/B candidate, arguably better on hair, but the open checkpoint is
  the vendor's second-best model.
- On a **worn** garment (extract the shirt off a person), saliency models grab
  the whole person — a parser/cloth-seg model is required (see §2). This is the
  case that needs the PRD's fallback tiers.
- **Evidence the crop+white-fill helps** is converging vendor guidance rather
  than a controlled ablation: Alibaba Aidge VTO ("best try-on effect with
  flat-laid images on a white background"), Google apparel try-on merchant specs
  (clean white/grey background, ≥1024px), FASHN (use a cutout instead of a worn
  photo "because worn photos cause the AI to confuse the original model's body
  with the garment"; their API exposes `garment_photo_type` and does its own
  preprocessing), Astria (flat-lay required), and Qwen-Edit practitioner guidance
  (tightly cropped references). Consistent with our own
  `image-accuracy-research.md` finding (VTEdit Model2Model: ~1.1 vs >3.5 on
  shop images). The ablation the PRD demands remains ours to run — no published
  one exists.

## 2. Item grouping / semantic scene decomposition

**Verdict: person-level separation is solved; part-level parsing became solved
*and* commercially usable in April 2026 (Sapiens2); hands and hair boundaries
remain the shaky parts and need the confidence gates the PRD already specifies.**

### Person matte
- **BiRefNet family** is the open leader: true soft alpha (matting variants),
  best-in-class hair/thin structures, MIT. `BiRefNet_HR-matting` (2048²) for
  high-res inputs. Failure modes: multi-person photos matte *all* salient people
  (it is saliency, not instance segmentation — gate with a detector or SAM box
  prompt if multi-person inputs are possible); low-contrast scenes degrade it.
- SAM 2.1/3 output **binary** masks — wrong tool for the matte itself, right
  tool for picking one instance among several.

### Part-level parsing (face / hair / hands / skin / torso)
- **Sapiens2 (Meta, Apr 2026) is the headline change**: 29-class body-part seg
  with first-class hand classes, 0.4B–5B checkpoints, 1024×768 native, matting
  model added May 2026 — and the Sapiens2 License has **no non-commercial
  clause** (Llama-style AUP: no surveillance/biometrics/deepfakes). Sapiens 1
  was CC-BY-NC; that blocker is gone. Needs Python ≥3.12 / PyTorch ≥2.7;
  CUDA-first (treat as T4/cloud, not MPS). fp16 on T4 verified by third parties
  for Sapiens-1-class sizes.
- **SCHP (MIT)** is what the try-on ecosystem actually ships (verified:
  IDM-VTON, CatVTON AutoMasker, OOTDiffusion ONNX, Leffa) — proven adequate,
  but 473px coarse edges and **no hand class at all** (hands melt into "arm";
  structural, not tunable). It is the floor, not the ceiling.
- **License landmines confirmed**: every popular SegFormer fine-tune —
  mattmdjaga/segformer_b2_clothes *and* the purpose-built FASHN Human Parser —
  inherits the NVIDIA Source Code License (non-commercial). Fine as dev-time
  reference/judge; never in the deploy path.

### Worn-garment zone mask
- **levindabhi U2Net cloth-seg (MIT)**: upper/lower/full-body cloth, coarse but
  license-clean, <1 s anywhere — right granularity for the expected-edit prior,
  and a cheap second opinion against Sapiens2's Upper_Clothing class.
- **SAM 3** (commercial-permitted SAM License): text-prompt "shirt"/"dress"
  returns all instances; a benchmark found it specifically strong on clothing
  boundaries, but ~1 s/image and 8–12GB fp16 — fallback/QA tier, not per-image
  primary. Grounded-SAM-2 (all-Apache) is the license-cleanest alternative; its
  text→box stage is the weak link on garment classes.

### Solved vs shaky (parsing)
- Solved (trust blindly): person/background matte; face region; torso-garment
  region on clean single-person photos; upper/lower clothing split.
- Shaky (gate + fallback, exactly as the PRD prescribes): **hands** (fingers
  over garment, crossed/occluded — breaks every parser; use MediaPipe hand
  landmarks (Apache) as an independent agreement gate); **hair fine boundaries**
  (parsers give blobby hair — route hair through a matting alpha, not the seg
  mask); the sleeve/hem garment-skin boundary (precisely the pixels VTO edits);
  layered clothing (jacket-over-shirt oscillates between classes).

## 3. Registration + change detection (guardrail steps 1 and 3)

**Verdict: the drift problem is real and documented; registration is cheap and
reliable with the right transform constraint; the "item grouping" change-detection
stage has direct published precedent (training-free, CVPR 2025).**

### Registration (original vs diffusion-edited twin)
- The Qwen-Image-Edit pixel-shift/zoom drift is an **open acknowledged issue**
  (QwenLM/Qwen-Image #229), persists through 2511, and the community workaround
  is pad→edit→crop-back→detail-transfer. The transform is essentially a global
  **similarity** (tx, ty, scale, tiny rotation) — constraining the model to that
  family stabilizes everything.
- Recommended cascade (all with computable confidence for the PRD's fallback
  gates): phase correlation at ~512px for coarse scale+shift (ms, CPU) → pyramid
  ECC (`MOTION_AFFINE`/Euclidean on blurred grayscale; the ECC correlation
  coefficient is the confidence signal) → if low, EfficientLoFTR (Apache,
  ~2.7× faster than LoFTR) or LightGlue+**DISK/ALIKED** + RANSAC similarity
  (inlier count/ratio = confidence). Avoid LightGlue+SuperPoint (SuperPoint
  weights are MagicLeap non-commercial) and DUSt3R/MASt3R (CC-BY-NC, overkill).
- ECC caveat: a large legitimately-changed region (the new garment) pollutes the
  objective — hence the coarse seed, the blur, and validating recovered scale
  (e.g. within [0.9, 1.1]) rather than trusting the score alone.

### Change detection + region formation
- Pixel metrics alone (delta-E, SSIM) are known-bad on re-rendered pairs —
  everything differs slightly, the map saturates. The robust recipe is a
  **low-res semantic change map** (DINOv2 or SAM-encoder patch-cosine
  differences) deciding *which* regions changed, intersected with a
  full-resolution photometric map (Lab delta-E) deciding *precise boundaries*,
  with an **adaptive** (skewness-based) threshold rather than a fixed one.
- Direct prior art for the grouping stage: **GeSCF (CVPR 2025)** — training-free
  scene change detection: coarse-align pair → correlate SAM-encoder key facets →
  adaptive threshold → use **SAM mask proposals as the region unit** (geometric
  intersection + semantic similarity matching). +19.2% over trained methods.
  Also AnyChange (NeurIPS 2024): per-mask SAM-embedding cosine across the pair.
  One SAM encoder pass per image serves both the diff features and the grouping
  proposals. Connected components on a thresholded diff = fragile pre-filter;
  SLIC = cheapest CPU boundary snap; SAM masks = what the literature converged
  on (a garment becomes 1–2 masks, not 50 blobs).
- Post-hoc paste-back precedent: A1111/ComfyUI inpaint compositing (paste
  masked generated region onto the original) is the de-facto standard — our
  guardrail is that operation with the mask *inferred* plus registration.
  Differential Diffusion (per-pixel change map), DiffEdit (auto-derives the edit
  mask), PixPerfect (2025, pixel-space post-edit refinement) are the research
  ancestors. Nobody has packaged the automatic aligned-diff-mask version — that
  is the gap the guardrail fills. PIE-Bench's background-preservation protocol
  (PSNR/LPIPS/SSIM outside the mask + DINO structure distance) is the ready-made
  scoring method for the raw-vs-guarded ablation.

## Bottom line

| Component | Status | Pick (commercial, T4) |
|---|---|---|
| Garment crop (product photo) | Solved | BiRefNet alpha bbox + white fill |
| Garment crop (worn photo) | Needs parser + fallback tiers | Sapiens2 / U2Net cloth-seg ∩ BiRefNet matte |
| Person matte | Solved | BiRefNet(-HR-matting) or Sapiens2 matting |
| Part parsing incl. hands | Solved as of Apr 2026 | Sapiens2 0.4B/1B (hands still gated via MediaPipe agreement) |
| Registration | Solved with similarity constraint | phase-corr → ECC → EfficientLoFTR fallback |
| Change map | Solid recipe, needs tuning | SAM/DINOv2 patch-cosine × Lab delta-E, adaptive threshold |
| Region grouping | Published precedent | GeSCF-style SAM mask proposals |
| Composite/paste-back | Industry standard | A1111-style composite + feather |

Estimated added latency for the full guardrail on a T4: ~1–2 s per image
(matting + parsing + one SAM encoder pass + registration are each sub-second).

Timing figures for T4/Apple Silicon are extrapolations from published V100/A100
numbers and community reports, not vendor benchmarks. Source URLs are in the
underlying agent reports; key ones: github.com/ZhengPeng7/BiRefNet ·
github.com/facebookresearch/sapiens2 · github.com/QwenLM/Qwen-Image/issues/229 ·
arxiv.org/html/2409.06214v3 (GeSCF) · arxiv.org/abs/2402.01188 (AnyChange) ·
github.com/NVlabs/SegFormer/blob/master/LICENSE ·
docs.aidc-ai.com (Aidge VTO input spec) · fashn.ai/blog (garment input guidance).
