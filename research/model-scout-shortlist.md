# VTO Harness Scouting Synthesis — Aug 7, 2026

Judge notes on evidence quality: three independent leaderboard/benchmark systems recur across agents — **arena.ai image-edit** (28.8M votes, Aug 7 2026), **artificialanalysis (AA) editing** (Jul 2026), and the **TStars-VTON** family of evals, which exists in **two incompatible rubrics** (Tstars-Tryon 1.0 paper, arXiv 2604.19748, where Seedream5 Lite = 9.30 / GPT-Image-2 = 9.20; and the Oxygen-TryOn re-eval, arXiv 2607.21694, where the same models score 8.77 / 8.34). All cross-model comparisons below stay within one rubric. Two agents' conflicts (Seedream Pro, Hunyuan hosting, pruna) are resolved by source quality as noted inline.

---

## 1. Shortlist — add to harness (ranked)

### 1. GPT Image 2 (`gpt-image-2`, pin snapshot `gpt-image-2-2026-04-21`) — OpenAI `/v1/images/edits`
- **Access:** OpenAI Images API (`POST /v1/images/edits`), openai SDK from Colab. May require one-time API Organization Verification; Tier 1 = 5 images/min.
- **Two-image:** Yes — up to 16 input images per edit call; person + garment + instruction is the intended pattern. Optional mask (inpainting) enables a masked-garment variant.
- **Cost:** token-priced ($8/1M image-input, $30/1M output; Batch −50%). ≈ **$0.04–0.05/img at `quality=medium`**, ~$0.17–0.21 high, ~$0.005 low.
- **Knobs:** `n`, `quality` (low/medium/high/auto), `size` (presets + custom: edges ×16, max edge 3840px, 0.65–8.3MP, ≤3:1 — can match input aspect exactly), `mask`, `stream`/`partial_images`, `moderation` (auto/low), `output_format`/`compression`. `input_fidelity` locked to high. **No seed, negative prompt, guidance, or steps.**
- **Evidence:** The only new general editor with direct try-on benchmark data: TStars paper rubric **9.20/10 single-item** vs SOTA specialist 9.372 (human GSB: specialist wins only 41.9% / 42.6% tie / 15.5% loss). Arena image-edit **#1, Elo 1463±4**. Garment Fidelity dimension still trails specialists (specialist 8.833 vs commercial editors in the 7–8 band).
- **Integration:** run `quality=medium`, size matched to person image, n=1; archive outputs (no seed). Also directly answers the stakeholder ChatGPT question (Section 4).

### 2. Qwen-Image-3 Edit (`alibaba/qwen-image-3/edit` on fal, live Jul 21 2026)
- **Access:** fal hosted API only (no open weights — 2511 remains the newest open Qwen editor). Trivial via fal queue API; OpenAPI schema verified.
- **Two-image:** Yes — required `image_urls` (1–3, **order matters**: person = image 1, garment = image 2).
- **Cost:** **$0.04/img** at 1K, $0.075 at 2K.
- **Knobs:** best of any new candidate — **seed**, **negative_prompt**, num_images, image_size, `enable_prompt_expansion` (turn OFF for reproducibility), safety toggle.
- **Evidence:** No direct try-on benchmark yet — promoted on lineage, not marketing: it is the direct API successor of the baseline family (2511 → qwen-image-max Jan → qwen-image-2/pro Mar → 3 Jul), where 2511 is the open cloth-consistency leader. The single most plausible baseline-beater; a same-family A/B against Qwen-2511 is the cheapest high-information experiment available.
- **Integration:** existing fal client; disable prompt expansion; fix seed.

### 3. Google `virtual-try-on-001` (Vertex AI `recontext_image`)
- **Access:** Vertex AI only (GCP creds, google-genai SDK); Google ships an official Colab notebook. Occasional 429s reported.
- **Two-image:** Yes, **typed slots** — `person_image` + `product_images` (one garment per request; composite for multi-garment). No person-to-person transfer mode.
- **Cost:** ~**$0.02–0.04/img** (community-measured; official price not on the fetched pricing page — verify in console). Cheapest dedicated arm, undercutting FLUX VTO v2 and FASHN.
- **Knobs:** `number_of_images` (1–4), `safety_filter_level` (down to BLOCK_NONE), **`add_watermark` toggle** (SynthID can be disabled — unique among Google models), output mime. Possible seed/baseSteps unconfirmed — check `RecontextImageConfig` in SDK.
- **Evidence:** Community head-to-head (suzuki-shoten.dev metafit part 3): **exact garment color preserved where Nano Banana shifted red→pink**; best-in-test on flat-background product/flatlay inputs; handles shoes/accessories. Known weakness: pose pulled toward source. Real third-party comparative evidence, unlike most candidates.
- **Integration:** route flatlay/product-shot garments here. Caveats: Vertex VTO endpoint retirement flagged for **Jan 20, 2027**; a newer `virtual-try-on-preview-08-04` exists (see one-cells).

### 4. Amazon Nova Canvas `VIRTUAL_TRY_ON` (`amazon.nova-canvas-v1:0`, Bedrock)
- **Access:** Bedrock InvokeModel (us-east-1 / ap-northeast-1 / eu-west-1), boto3 from Colab, base64 JSON body.
- **Two-image:** Yes — `sourceImage` (person) + `referenceImage` (garment: flatlay, on-body, or multi-product) + optional mask; auto garment masking via `maskType=GARMENT` + `garmentClass`.
- **Cost:** **$0.04–0.08/img** by resolution/quality.
- **Knobs:** richest of any hosted dedicated VTO — **seed, cfgScale, numberOfImages (≤5)**, garmentClass (UPPER/LOWER/FOOTWEAR/FULL_BODY), preserveFace/Hands/Pose, garmentStyling (sleeve/tuck/outer-layer), **mergeStyle BALANCED/SEAMLESS/DETAILED**, returnMask; output to 4.19MP.
- **Evidence:** No third-party benchmark (flagged honestly) — promoted on *structural* properties, not marketing: BALANCED mode guarantees non-masked pixels are **pixel-identical to source** (background/identity preservation by construction, which the judge criteria reward), and DETAILED mode does a tight-crop hi-res inpaint explicitly to improve **logos/text** — the exact FASHN-adjacent fidelity axis. Only knob-rich seeded dedicated arm available.
- **Integration:** AWS creds are the only friction; commercially clean.

### 5. fal `flux-klein-9b-virtual-tryon-lora` on `fal-ai/flux-2/klein/9b/base/edit/lora`
- **Access:** open weights (HF, Apache-2.0, diffusers/ComfyUI) or fal LoRA-by-URL endpoint; Colab A100 feasible locally.
- **Two-image:** Yes — 3 ordered refs (person, top, bottom) with a fixed `TRYON ...` prompt template; single-garment via top-only prompting (trained on top+bottom tuples).
- **Cost:** fal $0.02/MP in+out ≈ **$0.06–0.08/img**; free locally.
- **Knobs:** full set — **seed, guidance (5), steps (28), negative prompt**, num_images, size, per-LoRA scale.
- **Evidence:** Vendor demos + 4,738 HF downloads only — but the promotion logic is benchmark-anchored: **VTEdit-Bench (ECCV 2026) puts FLUX.2-klein at 3.96 on Shop2Model, the best universal editor and above Qwen-2511 (3.64)**, so a first-party try-on LoRA on the top-benched open base is the best-motivated open/seeded specialization available, and it upgrades an existing harness family for near-zero integration cost.
- **Integration:** existing fal client or existing klein arm locally; watch LoRA/base version match.

---

## 2. One-cell experiments (priority order)

1. **Seedream 5.0 Pro Edit** (`bytedance/seedream/v5/pro/edit` fal, ~$0.072 for person+garment at 1K; Replicate $0.045/1K, $0.09/2K) — arena edit #4 (Elo 1393) argues upgrade over the Lite arm, **but** official BytePlus docs show Lite beats Pro on edit-relevant specs (14 vs 10 refs, 3K vs 2K, edit-marketed variant, streaming/sequential) and **neither exposes a seed** (only seedream-3-0-t2i does). A/B vs Lite before any promotion; conflict between agents resolved toward the official-docs agent.
2. **Nano Banana Pro** (`gemini-3-pro-image`, ~$0.134/img 1K–2K, Batch −50%) — **best proprietary garment/item fidelity on the Oxygen re-eval (8.65 single-item, 8.50 multi-item)** but overall 8.04 < Lite's 8.77 due to **worst background preservation (7.88)** — measured whole-image drift. No seed (autoregressive), IMAGE_SAFETY refusals on sportswear/swimwear, mandatory SynthID. Test as a logo/text-heavy-garment specialist with pinned aspect/size, ≥1000px person inputs, explicit preserve-face/pose/background instruction.
3. **kingroka "Clothes Try On" Qwen-Edit LoRA** (Civitai 1940532; 11.2k downloads, 626 thumbs-up; commercial image use allowed) — strongest community-validated try-on LoRA, stitched single-image workflow (garment left, person right), strength 1.5. Trained on **original** Qwen-Image-Edit, not 2511 — verify cross-version behavior on fal's 2511 LoRA endpoint ($0.035/MP) or run on the original checkpoint before trusting it.
4. **prunaai/p-image-try-on** (Replicate, **$0.015 + $0.008/extra garment** — cheapest commercial VTO found) — seed, turbo, `preserve_input_size`, up to 11 garments, experimental pose reference. Undisclosed base model, unstated license, zero independent benchmarks: one cell for the cost floor and multi-garment probing (agents split add vs one-cell; strictness says one-cell).
5. **Google `virtual-try-on-preview-08-04`** — near-free A/B against -001; release notes claim shoe/body-shape/product-fidelity gains and lower latency; confirm it actually postdates -001.
6. **Wan 2.7 Image Pro** (Replicate, **$0.03/img**, seed 0–2^31, ≤9 refs, num_outputs 1–4) — best knob profile of the Chinese sweep, zero try-on evidence.
7. **Nano Banana 2** (`gemini-3.1-flash-image`, ~$0.045–0.067/img) — arena 1385 ≈ Pro at half the cost, unique `thinking_level` knob; no try-on data at all.
8. **Kling Image O3** (fal, **$0.028/img**, @Image refs + face-control `elements`) — cheap identity-preservation probe; mid-pack edit Elo (AA 1212).
9. **grok-imagine-image-quality edit** (fal/xAI, $0.05 + ~$0.01/input, 3 refs) — arena #6 (1390) but no seed, no try-on evidence.
10. **Reve 2.1 Remix** (fal, `<frame>` multi-image syntax) — AA editing #1 (1260) but no seed and **unverified ~$0.20/img** — confirm price before batching.
11. **OmniTry v1** (HF, Apache-2.0, ~28GB VRAM, fits Colab A100) — only commercially-licensed open-weights VTON; use as open control arm and for accessories/"try on anything"; won't beat FASHN on garments.
12. **Alibaba aitryon-plus** (DashScope, ~$0.072/img, top+bottom simultaneous, explicit logo-accuracy claims) — only if the China-Beijing API-key hurdle is acceptable; no seed, 24h result expiry.
13. **Vidu Q2 reference-to-image** ($0.04/1080p, **seed exposed**, 7 refs, 4K) — cheapest seeded multi-ref editor; video-company consistency model, no try-on evidence.
14. Lower priority: **"Attach Outfit & Try On" LoRA** (true two-image on both Qwen-2509 and klein bases, but Civitai license grants no commercial image rights), **fal image-apps-v2/virtual-try-on** ($0.04, 4K claim, undisclosed base), **HiDream-O1-Image** (MIT, 8B, multi-reference — but scene-regenerating personalization, zero edit benchmarks).

---

## 3. Rejects worth naming

- **MAI-Image-2.5 / 2.5-Pro** (Microsoft, arena #3) — edit endpoints accept exactly **one** input image (schema-verified); structurally incompatible with person+garment.
- **muse-image** (Meta, arena #2, Elo 1405) — no public API anywhere; re-check if Meta ships one.
- **Oxygen-TryOn** (JD.com, arXiv 2607.21694) — claimed SOTA **9.36 single-item vs 8.77 next-best** on the Oxygen re-eval rubric, but no code/weights/API; **watch item**, and its re-eval protocol is reusable for our scoring.
- **HunyuanImage 3.0 Instruct** — a fal-hosted edit endpoint with 3 refs, seed+guidance does exist (~$0.09; OpenAPI-verified, overriding the agent that couldn't reach fal), but AA edit Elo 1222 sits below the baseline family and weights need 8x80GB; territorial license restrictions.
- **ChatGPT-the-product / `chatgpt-image-latest`** — not scriptable (ToS), no knobs, session drift, and its serving config benchmarks *below* raw gpt-image-2 (1390 vs 1463). See Section 4.
- **Kling Kolors Virtual Try-On** — API still v1/v1.5 (Jan 2025); "Kolors 2.1" try-on is web-app-only marketing (n.b. the source of that claim is a Magic Hour blog post); the dedicated endpoint has vanished from current Kling API doc navigation — likely retired.
- **LongCat-Image-Edit(-Turbo)** — most-adopted new open editor (22k downloads) but strictly single-image; benchmarks exclude 2511.
- **Voost** (SIGGRAPH Asia 2025) — no downloadable weights, CC BY-NC-SA, demo only.
- **WearWow** (arXiv 2607.19923, native-2K multi-garment claims) — paper only, no artifact; watch.
- **Pixelcut VTO** — $0.10/img, zero knobs, zero quality evidence; dominated by FASHN.
- **Luma UNI 1.1 Max** — costs more than FASHN Max, bottom of new-entrant Elo pack, thinnest knob set.
- **MiniMax image-01, GLM-Image/CogView-4** — cannot accept a garment reference at all.
- **Emu3.5, OmniGen2, Step1X-Edit-v1p2, UMO/USO/ACE++/BAGEL/Lumina** — 2025-generation cohort, all below the klein/2511 arms; no 2026 successors; ACE++ carries FLUX.1-dev NC license.
- **Nano Banana 2 Lite / gemini-2.5-flash-image (legacy)** — dominated within their own family.
- **TryOn-API.com** — aggregator middleman; adds nothing over direct integrations.
- **Decart Lucy 2.1 VTON** — realtime-webcam video only; no static output mode.
- **Replicate IDM-VTON** — 2024-era, CC BY-NC-SA, called production-unsuitable on license grounds.
- **xocialize klein-4B try-on LoRA** — 273 training tuples, mandatory clothing-agnostic masking preprocessing, self-admitted artifacts; dominated by fal's klein-9B LoRA.

---

## 4. ChatGPT / GPT Image 2 verdict

**Yes — add GPT Image 2 (API, medium quality, pinned snapshot) as a harness arm. Do not use ChatGPT-the-product.**

**Why it earns a slot:** it is arena's #1 image editor (Elo 1463±4, clear of everything else) and near-ties a commercial SOTA try-on specialist on overall single-item quality (TStars paper rubric: 9.20 vs Tstars 9.372; human GSB 41.9/42.6/15.5) at ~$0.05/img medium. It is also literally the model behind ChatGPT, so running it under controlled conditions is the direct, defensible answer to "how does our work differ from ChatGPT."

**Exact API surface:** `POST /v1/images/edits`, `model=gpt-image-2` (pin `gpt-image-2-2026-04-21`); up to 16 input images (file/file_id/base64); optional `mask`; `n`; `quality` low/medium/high/auto; `size` presets or custom (edges ×16, ≤3840px edge, 0.65–8.3MP, ≤3:1 aspect); `input_fidelity` locked high; `stream`+`partial_images` 0–3; `moderation` auto/low; `output_format` png/jpeg/webp + compression. **No seed, negative prompt, guidance, or steps anywhere in the API.**

**Cost:** $8/1M image-input + $30/1M output tokens; per image ≈ $0.005 low / **$0.04–0.05 medium** / $0.17–0.21 high; Batch API −50%. Tier-1 rate limit 5 images/min; possible one-time org identity verification before GPT Image access.

**Try-on-relevant failure modes:** garment-detail gap vs specialists (Garment Fidelity: specialist 8.833 vs general editors 7–8 band); brand-logo reproduction documented "hit-or-miss"; noise/grid artifacts specifically when editing from uploaded reference images (community megathread, Apr 2026), amplifying across sequential edits; expect multi-garment collapse like other general editors (Qwen-2511 drops 8.121→6.441 with multiple items); 3+ min latency at high quality; mandatory C2PA + SynthID watermark on every output (since May 2026, detector at openai.com/research/verify); zero run-to-run determinism.

**Stakeholder differentiation (API arm vs ChatGPT product):** ChatGPT offers no seed/quality/size/mask controls, undisclosed daily caps, session-state drift (near-identical repeats within a session, noise accumulation across generations), chat-history contamination, ToS prohibition on automation — and its serving config (`chatgpt-image-latest-high-fidelity`) measures **below** the raw API model on arena (1390 vs 1463). Our harness runs the same underlying model with pinned snapshot, controlled inputs, batch reproducibility, and side-by-side scoring against dedicated try-on specialists that beat it on garment fidelity.

---

## 5. Corrections to prior conclusions

1. **The Qwen family did move — just not in open weights.** No Qwen-Image-Edit-2512 exists (HF-verified; Qwen-Image-2512 is a T2I base, Qwen-Image-Bench is a benchmark). But the API-only **Qwen-Image-3 Edit** (fal, Jul 21 2026) is the family's real successor; treating Qwen-2511 as the family frontier is now wrong.
2. **FLUX.2-klein already beats Qwen-2511 on the one public try-on benchmark.** VTEdit-Bench (ECCV 2026) Shop2Model: klein 3.96 > Qwen-2511 3.64 > FLUX.2 3.36. If the harness assumes Qwen-2511 is the strongest general-editor arm for try-on, that ordering needs re-checking. VTEdit-Bench contains **no** Seedream/Hunyuan/Kling/Wan/Vidu entries.
3. **TStars numbers exist in two rubrics — do not mix.** Paper rubric: Lite 9.30, GPT-Image-2 9.20, specialist 9.372. Oxygen re-eval rubric: Lite 8.77 (matching our prior 8.77), GPT-Image-2 8.34, Nano Banana Pro 8.04, FLUX.2-dev 7.76, Qwen-Image-Edit 6.10, Oxygen-TryOn (claimed) 9.36.
4. **Seedream 5.0 Pro exists above Lite, but is not a straightforward upgrade:** it takes fewer refs (10 vs 14), lower max res (2K vs 3K), and **no Seedream 5.0 tier exposes a seed** on the official API (seed is seedream-3-0-t2i only).
5. **Nano Banana naming:** NB Pro = `gemini-3-pro-image`; NB 2 = `gemini-3.1-flash-image`; no "Nano Banana 3" / Gemini-3.5-image exists. Gemini image refs are untyped ordered images, no seed on any Gemini image model.
6. **Kling try-on regression:** no API version beyond kolors-VTO v1.5, and the endpoint has disappeared from current Kling API doc navigation — likely retired. "Kling Kolors 2.1" try-on (per a Magic Hour blog post) is web-app-only, not an API model.
7. **FASHN and BFL are current:** FASHN's only change since v1.6 is a Fast mode on tryon-max (Jul 2, 2026, costs unchanged); BFL has shipped nothing since Apr 2026 (FLUX.2 [max] hosted tier, AA Elo 1201, is the only family member above klein not in the harness).
8. **Google Vertex VTO endpoint retirement is scheduled Jan 20, 2027**, and a `virtual-try-on-preview-08-04` successor exists — plan the -001 arm accordingly.
9. **All OpenAI images since May 2026 carry C2PA + SynthID**; conversely Vertex `virtual-try-on-001` is the rare model where watermarking can be disabled.
10. **Methodology caveat:** every agent's WebSearch budget was exhausted; findings came from direct fetches of leaderboards, OpenAPI schemas, HF/Civitai APIs, and vendor docs. One agent could not reach fal at all — its "not on fal" negatives were overridden where another agent had schema-level proof. Unverified numbers to confirm before wiring: Reve pricing (~$0.20), virtual-try-on-001 official price and possible seed field, GPT Image org-verification status.

---

## Sources

**Leaderboards / benchmarks**
- https://arena.ai/leaderboard/image-edit
- https://artificialanalysis.ai/image/leaderboard/editing
- https://github.com/Hiuyee124/VTEdit-Bench (ECCV 2026)
- https://arxiv.org/abs/2604.19748 (Tstars-Tryon 1.0)
- https://arxiv.org/html/2607.21694v1 (Oxygen-TryOn + TStars re-eval)

**Shortlist endpoints**
- https://developers.openai.com/api/docs/api-reference/images/createEdit (+ pricing, gpt-image-2 model page, rate-limits)
- https://fal.ai/api/openapi/queue/openapi.json?endpoint_id=alibaba/qwen-image-3/edit
- https://raw.githubusercontent.com/GoogleCloudPlatform/generative-ai/main/vision/getting-started/virtual_try_on.ipynb
- https://docs.aws.amazon.com/nova/latest/userguide/image-gen-vto.html
- https://huggingface.co/fal/flux-klein-9b-virtual-tryon-lora + https://fal.ai/models/fal-ai/flux-2/klein/9b/base/edit/lora

**One-cell candidates**
- https://fal.ai/api/openapi/queue/openapi.json?endpoint_id=bytedance/seedream/v5/pro/edit + https://docs.byteplus.com/en/docs/ModelArk/1541523
- https://ai.google.dev/gemini-api/docs/image-generation + /pricing
- https://civitai.com/models/1940532 (kingroka LoRA); https://civitai.com/models/2367983
- https://replicate.com/prunaai/p-image-try-on/llms.txt; https://replicate.com/wan-video/wan-2.7-image-pro/llms.txt
- https://www.alibabacloud.com/help/en/model-studio/aitryon-plus-api; https://platform.vidu.com/docs/reference-to-image
- https://github.com/Kunbyte-AI/OmniTry; https://docs.x.ai/docs/guides/image-generations

**Failure modes / community evidence**
- https://community.openai.com/t/collection-of-gpt-image-generator-2-0-issues-bugs-and-work-around-tips-check-first-post/1379535
- https://suzuki-shoten.dev/blog/metafit-genai-part2/ and /metafit-genai-part3/
- https://lumalabs.ai/learning-center/articles/gpt-image-2-complete-guide

**Status checks / corrections**
- https://huggingface.co/api/models?author=Qwen (no 2512); https://fashn.ai/changelog; https://docs.cloud.google.com/vertex-ai/docs/release-notes
- https://kling.ai/document-api/guides/capability-map/image; https://innvesti.com/reports/best-virtual-try-on-apis-developers-2026/
- https://magichour.ai/blog/kling-kolors-21-for-ai-virtual-try-on (app-only "2.1" claim source)
