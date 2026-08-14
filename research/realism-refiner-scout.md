# Realism-Refiner Scout — Single-Image High-Fidelity Enhancement (Aug 14, 2026)

Use case: final "realism pass" over AI-generated try-on outputs (~1MP person+garment).
Hard gates: **pixel-strict face identity + garment prints/logos/text** (hallucinated
detail there is a dealbreaker), **commercial license**, same-res or 2–4x output both
acceptable. Companion to `open-weights-model-catalog.md` §4.5; this file supersedes
that section where they differ (licenses here were read first-hand from LICENSE
files/model cards; community sentiment via Arctic Shift Reddit archive, Civitai API).

Status checks verified: **no SeedVR3 exists** ("SeedVR2.5" = the ComfyUI node version);
Qwen-Image-Edit-2511 still the newest open Edit; Z-Image base shipped ~Jan 2026
(Apache); **Z-Image-Edit still unreleased**.

---

## 0. License matrix (verified first-hand)

Commercial-OK: SeedVR2 (3B/7B/7B-Sharp, Apache) · Z-Image + Turbo (Apache) ·
alibaba-pai Z-Image Fun-ControlNet-Union 2.1 incl. **Tile** (Apache) ·
Qwen-Image-Edit-2511 (Apache) · FLUX.2-klein-4B (Apache) · AuraSR-**v2** (Apache;
v1 is ambiguous `license: cc` — avoid) · ODTSR / OSEDiff / PiSA-SR / PASD / SeeSR /
DiffBIR (Apache repos; SD2.1-based carry OpenRAIL-M use restrictions) · Real-ESRGAN
(BSD-3) · SwinIR/HAT/DAT/DRCT/SPAN/PLKSR (Apache/MIT) · Phhofm OpenModelDB models
(CC-BY-4.0, attribution) · RealVisXL V5 (OpenRAIL++) · xinsir tile-sdxl (Apache) ·
GLM-Image (MIT).

Blocked: **Krea 2** (Community License v1, read in full: commercial only under $1M
company-wide TTM revenue incl. affiliates; grant revocable, 30-day termination for
convenience §9.2 — effectively out for company deployment) · FLUX.2-dev / klein-9B /
FLUX.1-dev / jasperai Flux upscaler CN / LucidFlux (BFL NC) · SUPIR / HYPIR (SupPixel
NC declaration) · StableSR/ResShift/InvSR (S-Lab NC) · 4x-UltraSharp(+V2) / Remacri /
NMKD (CC-BY-NC-SA — the classic deployment traps) · Tiled Diffusion nodes (contain
CC-BY-NC code) · ComfyUI-Impact-Subpack Ultralytics detectors (AGPL — use
MediaPipe/SAM instead) · ATD code repo has NO license file (use spandrel's MIT
reimplementation + CC-BY weights, after legal review).

---

## A. One/few-step generative restoration upscalers

### SeedVR2 3B/7B (ByteDance, ICLR 2026) — the 2026 community default
- github.com/ByteDance-Seed/SeedVR · node: numz/ComfyUI-SeedVR2_VideoUpscaler (2.7k★)
- One-step DiT restoration (adversarial post-training), arbitrary res, image+video;
  community 1.4B distill of 7B-Sharp appeared Jul 2026.
- **Good:** best community-proven identity preservation of any generative model in
  this survey — 2048→512→SeedVR2→2048 reported "IDENTICAL to the original"
  (r/SD, Aug 1 2026); Apr 2026 SUPIR-comparison: "sharper results, very faithful";
  "just works nearly every time". T4-viable (3B 12–16GB; 7B via GGUF/FP8/BlockSwap
  down to 8GB); ~2–10s/img; ComfyUI native + headless CLI.
- **Weak (directly relevant):** model card admits it "may oversharpen lighter
  degradations (e.g., 720p AIGC content)" — lightly-degraded AIGC is exactly our
  input class. 333-pt thread: "removes a LOT of detail… leaves them flat"; lip
  gloss/blush/fabric regularized away; "invents traits" reports tied to aggressive
  noise injection (consensus fix: noise injection 0); leathery skin if >2x per pass.
  No logo-mangling complaints found, but no positive proof either — bench on our
  prints. It restores/sharpens; it does NOT de-plastic skin much.
- Knobs: `resolution` (short edge — same-res pass possible), noise injection (keep 0).
  No steps/CFG (single step). No diffusers pipeline (plain PyTorch headless).

### ODTSR (RedMediaTech, CVPR 2026) — strongest on-paper fit, new
- github.com/RedMediaTech/ODTSR · HF double8fun/ODTSR
- One-step SR on **Qwen-Image 20B + LoRA**; explicitly claims strength on
  **text-in-image, fine textures, faces**; ships a **"Fidelity Weight" knob** —
  exactly our dial. Apache end-to-end.
- Weak: **min 40GB VRAM** (A100 only); near-zero community validation; no
  ComfyUI/diffusers. Bench-worthy on license + design alone.

### Cheap conservative fallbacks
- **PiSA-SR** (CVPR 2025, Apache, SD2.1 one-step): dual LoRAs, `lambda_pix` vs
  `lambda_sem` adjustable at inference — most explicit fidelity dial in the cheap
  class; T4-OK, sub-second/tile; weights only on GDrive/Baidu.
- **OSEDiff** (Apache): the original one-step Real-ISR distill; production-proven
  (OPPO phones); 0.1s/512 on A100; SD2.1 prior smooths rather than invents.
- PASD / SeeSR / DiffBIR v2: Apache but multi-step SD1.5/2.1-era, superseded
  (DiffBIR's README now redirects to the NC HYPIR). Legacy baselines.

### License-dead / skip
SUPIR (NC + community-dethroned: "obscenely slow… clearly dethroned by SeedVR2",
Apr 2026); HYPIR (NC; open SD2.1 variant lukewarm); StableSR/ResShift/InvSR (S-Lab);
LucidFlux (FLUX NC and README warns it hallucinates by design); ClearSR (no public
code). **Watch:** UniT (KAIST, text-aware restoration — most on-target research for
the logo constraint, no license yet); RCOD (AAAI'26, MIT, weights unreleased).

---

## B. Fidelity-first non-diffusion upscalers (deterministic anchors)

2026 consensus framing: "great at upscaling but not restoring really anything" — on
plastic input they preserve the plastic. Value = zero-drift anchor arms.

- **Real-ESRGAN** `realesr-general-x4v3` with `-dn 0.1–0.3` denoise knob (BSD-3):
  bulletproof fallback; known to airbrush skin; frozen since 2024; T4-trivial.
- **AuraSR-v2** (Apache): the only cat-B model that plausibly ADDS AI-render texture
  (GigaGAN repro built for AI images; "my go-to if I don't want denoising
  creativity"). 4x only, 256px tiles; amplifies input artifacts; crunchy eyes/teeth;
  occasional tile seams. Community recipe for same-res: 4x SR → 0.25x Lanczos → AuraSR.
- **Phhofm CC-BY-4.0 line** (OpenModelDB, spandrel-loadable/MIT):
  4xNomosWebPhoto-RealPLKSR (flagship photo/skin balance), 4xFaceUpDAT (face-trained),
  4xNomos8kHAT-L (max fidelity, slow), 4xRealWebPhoto_v4_dat2 (compressed inputs),
  Nomos8k SPAN (near-real-time). The permissive community lane; T4-OK.
- SwinIR/HAT/DAT/DRCT (Apache/MIT): battle-tested faithful; DAT2 = community
  quality/speed favorite; no 2026 arch displaced them.
- Traps: 4x-UltraSharp/V2, Remacri (CC-BY-NC-SA) — the most famous "realistic"
  checkpoints are NC.

---

## C. Low-denoise img2img realism refiners

### Z-Image / Z-Image-Turbo (Tongyi, 6B, Apache) — top realism candidate
- Turbo Nov 2025 (~5.7M DL via Comfy-Org mirror); base Jan 2026; alibaba-pai
  **Fun-ControlNet-Union 2.1 incl. dedicated TILE models** trained to 2048²
  (2601/2602 refreshes reduced bright-spot artifacts) — all Apache.
- Skin-realism consensus genuinely positive: "I love its skin texture"; "Z-Image
  Base generally does more realistic human skin"; refinement thread conclusion
  "I still prefer ZIT or Klein for that". Base > Turbo for skin; Turbo skews
  idealized, not plastic.
- **Killer feature: the only modern base with an Apache tile ControlNet** (Qwen and
  Klein have none as of Aug 2026). Reference inference via VideoX-Fun (Apache,
  headless-friendly); ComfyUI nodes exist.
- Config: i2i denoise 0.15–0.3 + tile CN; Turbo 8 steps; base ~22+3 two-stage.
  16GB fits (T4); GGUF/FP8 abundant; sub-second (Turbo) per 1MP.
- Canonical workflow "**ZiT Studio**" (r/comfyui, Dec 31 2025): Z-Image Turbo +
  Union 2.1 inpaint + Fun tile-CN tiled upscale + **SeedVR2 for the faithful
  upscale**; author's rule: "for a faithful upscale, use SeedVR2."

### Qwen-Image-Edit-2511 — identity-strong but the WRONG tool for this slot
Preserves identity/text well, but community reports its output finish is itself
plastic ("unusually smooth skin"; restoration attempts "plasticky skin, no detail").
It would add the look we're removing. Keep for targeted edits, not the realism pass.

### FLUX.2-klein-4B (Apache) — best anti-hallucination tiling mechanism, porting catch
The 2026 identity-anchored tiled refiners are Klein-based: hildegard refiner
(3 reference latents per tile — tile + neighbor map + whole-image thumbnail;
"a couple of ~2x passes beat one big jump"), Flux2Klein-Enhancer ("1:1 identity
pull"), KleinTiledUpscaler (per-tile histogram color match — **no license file**).
**Catch: all community tooling demos on klein-9B (NC)** — commercial use means
porting to 4B (same architecture, feasible, unproven). Headless:
DiffSynth-Studio/Template-KleinBase4B-Upscaler (Apache, Apr 2026, ~24GB quantized).

### SDXL tile-refine stack — superseded but cheapest fully-commercial
RealVisXL V5 (OpenRAIL++; no V6 coming) or Juggernaut (dev ended May 2025) +
xinsir tile CN (Apache) at denoise 0.15–0.3. T4-class; the best-understood
low-denoise identity behavior in existence.

### Krea 2 — great realism, gated license
Raw = finetuning base ("not recommended for inference"), Turbo usable; USDU tiling
artifacts reported ("skin cracks"); top realism workflow needs mandatory color
correction. License blocks company deployment (see §0).

### GLM-Image (Z.ai, Jan 2026) — MIT wildcard
9B AR + 7B diffusion decoder; editing + identity-preserving generation; best-in-class
text rendering. No refiner-workflow evidence yet; cheap bench slot on license alone.

### De-AI-ify LoRAs with real adoption (Civitai API-verified, commercial flags checked)
| LoRA | Bases | DL | Commercial |
|---|---|---|---|
| **Lenovo UltraReal** (Danrisi, 1662740) | Z-Image, Qwen, Klein-9B-base, Krea 2, Flux | 152k | Image+Rent+Sell ✓ |
| UltraReal Krea2/Klein9b (2462105) | Krea 2, Klein 9B | 31k | Image+Rent+Sell ✓ |
| Z-Image Radiant Realism Pro (2395852, "no wax effect") | Z-Image Turbo | 4.2k | Image+Rent+Sell ✓ |
| Jibify skin detailer (2346302, strength 0.4–0.7) | Z-Image Base | 2.7k | Image+RentCivit only |
| Amateur Photography (652699) | ZImage/Qwen/Flux | 83k | **no sell flag — avoid** |

"Smartphone Snapshot Photo Reality v13 OMEGA" is 2026's dominant realism LoRA but
targets klein-9B (NC base). Prompt-level finding (545-pt thread): camera-gear/film
vocabulary ("point-and-shoot film camera") beats "realistic/candid" tokens for
de-plasticizing Z-Image portraits.

---

## D. Protection wrapper (use around ANY refiner — the pixel-strict guarantee)

1. **Composite-back of protected regions** — the only true guarantee: face mask via
   MediaPipe/SAM (Apache — NOT Ultralytics/Impact-Subpack, AGPL) + OCR-derived
   logo/text masks (PaddleOCR/EasyOCR, Apache) → refine → feathered composite of
   ORIGINAL face/print pixels. Pro consensus on branded items: AI-native logo
   fidelity "not currently possible — composite the real product" (r/comfyui, Apr 2026).
2. **Differential Diffusion** (ComfyUI core node; also diffusers): per-pixel denoise
   map — 0.0 on face/logo feathered to ~0.3 on skin/fabric; kills binary-mask seams.
3. **Crop-and-stitch** (lquesada node, GPL-3): refine only the masked crop, leave the
   rest bit-identical — built because full-frame editors subtly shift untouched pixels.
4. **Wavelet color fix** (~50-line pure-python, replicated across SR repos): kills
   global color drift. **Frequency separation / Restore Detail** (spacepxl
   Image-Filters, MIT): keep refiner's new high-freq texture with original low-freq
   color/shape, or vice versa.
5. **Detail Daemon** (MIT, Flux/Z-Image): adds texture with zero composition change
   via sigma scheduling — documented to age faces ("adds pores/wrinkles
   indiscriminately") → mask away from faces.
6. **Grain in pixel space** (BetterFilmGrain, MIT) after the pipeline — "film grain"
   in a refiner prompt is a documented hallucination trigger.
7. Tiling: USDU (GPL) hallucinates per-tile >0.35 denoise without tile conditioning;
   Tiled Diffusion nodes contain CC-BY-NC code (red flag); the 2026 answer is
   Z-Image Fun tile CN (Apache), Klein reference-latent tiling, or skip diffusion
   tiling and let SeedVR2 do the resolution lift.

---

## Ranked shortlist

1. **SeedVR2-3B** — the fidelity/finish stage: best proven identity preservation,
   one step, T4-viable. Same-res or ≤2x per pass, noise injection 0. Risk:
   oversharpen/regularize on lightly-degraded AIGC; adds fidelity, not de-plastic.
2. **Z-Image Base i2i @ 0.15–0.30 + Fun tile CN + Lenovo UltraReal (or Radiant
   Realism Pro)** — the realism stage: only Apache-end-to-end stack with a real tile
   CN and consensus-best open skin texture; 16GB. Wrap with composite-back + wavelet
   color fix (non-negotiable).
3. **klein-4B tiled refine with reference-latent conditioning** (DiffSynth 4B
   upscaler template or hildegard-style port) + UltraReal-Klein LoRA — best
   anti-hallucination tiling mechanism; tooling targets NC 9B, budget porting time.
4. **ODTSR** — strongest on-paper match (fidelity knob, text/face claims, Qwen-20B
   prior); A100-only, unproven.
5. **Anchors:** 4xNomosWebPhoto-RealPLKSR / 4xFaceUpDAT (CC-BY) zero-drift 2–4x;
   AuraSR-v2 (Apache) texture-adding GAN; realesr-general-x4v3 (BSD-3) fallback.

Excluded on license despite quality: SUPIR, HYPIR, FLUX.2-dev, klein-9B, Krea 2,
LucidFlux, StableSR/ResShift/InvSR, UltraSharp/Remacri, Tiled-Diffusion, Ultralytics.
Excluded on behavior: Qwen-Edit-2511 as the realism pass (adds plastic skin).

## Recommended A/B test set

All arms share the protection wrapper: MediaPipe/SAM face mask + OCR logo mask →
feathered composite-back + wavelet color fix + BetterFilmGrain finish.

| Arm | Pipeline | HW | Tests |
|---|---|---|---|
| A1 control | 4xNomosWebPhoto-RealPLKSR 4x → Lanczos to target | T4 | zero-hallucination floor for identity metrics |
| A2 fidelity | SeedVR2-3B same-res or 2x, noise-inj 0 | T4 | does restoration alone kill the plastic look; does it touch logos |
| A3 primary | Z-Image Base i2i denoise 0.2 (sweep .15/.25/.30) + Fun tile CN + UltraReal @0.5 + differential-diffusion soft mask | T4/L4 | realism gain vs identity drift sweet spot |
| A4 speed | A3 with Z-Image-Turbo 8 steps + Radiant Realism Pro | T4 | Turbo idealization bias at production latency |
| A5 stretch | ODTSR fidelity-weight sweep (and/or klein-4B DiffSynth tiled refine) | A100 | whether 20B prior + fidelity knob beats A3 on fabric/text |

Metrics: ArcFace distance on pre-composite face crop; OCR exact-string match + LPIPS
on garment print crops; human/VLM realism rating on skin+fabric; seam/color-drift
check. Best-guess production shape: **A3 (realism) → A2 (SeedVR2 2x finish)** with A1
as regression anchor — the same "ZiT Studio" pattern the community converged on,
every component Apache/CC-BY/BSD.
