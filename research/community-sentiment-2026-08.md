# Community Sentiment Addendum — Open Image Gen/Edit + VTO (Aug 14, 2026)

Practitioner-forum companion to `open-weights-model-catalog.md`: what people actually
run and say on r/StableDiffusion, r/comfyui, Civitai comment threads, HF discussions,
HN, and ComfyUI GitHub. Two research sweeps, 2026-08-14. Reddit recovered via the
Arctic Shift archive API (direct fetch blocked); Civitai comments via rendering proxy.
Scores are snapshot values; single-post opinions and rumors flagged as such.

---

## 1. Landscape shifts the catalog didn't have (last ~8 weeks)

- **Krea 2 went open-weights (Jun 23, 2026)** — 12–13B, Raw + Turbo variants
  (HN 415 pts; HF krea/Krea-2-Raw ~101k DL). This reverses the V1-era "Krea 2 is
  API-only" verdict at the weights level (the "no edit endpoint" disqualification was
  about the hosted API). **License caveat: $1M revenue cap + mandatory content
  filters** — HN consensus "open-weights, not open-source." For Magic Hour the revenue
  cap likely disqualifies the deploy path — verify the exact license text before any bet.
- **Krea 2 "Identity Edit" LoRA v1.2** (community author conradlocke, ~Aug 10):
  the biggest editing story of August (826-pt thread + 428-pt before/afters);
  commenters rate its character consistency "better than qwen and klein." Known
  faults from the same thread: color shift input→output "100% of the time", breaks
  above ~1K, can't change camera angle, slow (~2 min/MP on a 5060 Ti). Directly
  relevant to the identity-degradation problem — evaluate even if only as a
  technique/teacher, given the base license.
- **Qwen-Image 2 & 3 are closed-weights** — community treats 2511/2512 as the end of
  the open Qwen line and is optimizing what exists (ByteShape compact 2512 GGUFs,
  PAI Fun-ControlNet-Union-2602). Confirms the catalog's "plan on 2511 as terminal."
- **FLUX 3 announced Jul 23–24** — one multimodal model; API-only preview; "FLUX-3-Dev"
  open weights promised but NOT shipped (571-pt HN thread; "local soon pls" threads).
  Rumor/pending — but it may reshuffle everything if dev weights drop.
- **Microsoft Mage-Flow** (4B T2I + Edit, MIT, native 2K): shipped Jun 15, then pulled;
  community-mirrored at Comfy-Org/Mage-Flow on HF. Quality issues at 2K reported
  pre-removal. Unconfirmed rumor of a re-release with a new text encoder.
- **Z-Image-Edit is vaporware** — Tongyi-MAI org ships only Z-Image (base, Jan 2026)
  and Z-Image-Turbo (940k DL — the most-deployed open T2I); the "when will
  Z-Image-Edit" HF discussion has sat unanswered for months.
- **Kroma v0.2** (lodestones/Chroma lineage, Aug 9, MIT): full finetune of Krea 2;
  cautiously positive but rough (SD1-level fine detail, garbled INT8 outputs).
- **Boogu-Image-0.1** family (Jun 16, Apache-2.0, Base/Turbo/Edit/Edit-Turbo):
  modest buzz, **astroturfing accusations on the subreddit** — treat adoption
  numbers skeptically.
- Niche: Anima-2.9B (anime, trending #1 on HF, hobby license); Ideogram 4.0 open
  release (9.3B, Jun 3) as the typography reference; NVIDIA Qwen-Image-Flash 4-step
  distill; MiniMax H3 (video) is eating the subreddit's attention share.
- Quant/runtime meta shifted: INT8 ConvRot + hybrid "GGUF Q8_CR" formats, NVFP4 for
  50-series, ComfyUI `--enable-dynamic-vram` (headline feature and top complaint
  generator of August).

## 2. Top open EDITOR — contested three-way

No single winner; the representative thread ("Is Klein Edit still the best we have
for image editing?", 72 pts) top comment: *"Klein is best. Unless you use Qwen — then
chances are Qwen is best."*

| Model | Community verdict | Echoed complaints |
|---|---|---|
| FLUX.2 Klein 9B Edit | Default "best" answer; speed, sharpness, photorealism | Color-preservation drift in edits; character-swap quality loss; censorship (uncensored text-encoder swaps trending); **9B is NC** |
| Qwen-Image-Edit-2511 | Adoption king + LoRA platform (2509+2511+GGUF+Lightning ≈ 1.1M monthly DL combined) | Plastic/AI-ish skin esp. with Lightning; prompt-following and text-rendering regressions vs 2509 (HF discussions); 20B heavy |
| Krea 2 + Identity Edit LoRA | Surging challenger, best identity consistency per commenters | Color shift, ≤1K only, no angle changes, slow, base license revenue cap |

- FLUX.2-dev (32B): acknowledged quality ceiling, minority choice (VRAM, license, i2i
  ignoring the reference per HF threads).
- Cross-model consensus on identity drift: "preserve the face" prompting fails —
  the accepted fix is **masking + SAM3 compositing nodes**, not prompts (62-pt thread).
  Matches the catalog's paste-back doctrine.
- Second tier reality-check: **FireRed-Image-Edit** — 1.0 launch hot (257 pts), but
  **1.1 landed flat** and one sweep describes it as a Qwen-Edit finetune (conflicts
  with the tech-report "from a T2I base" framing — verify base lineage if it matters
  for LoRA compatibility); adoption modest (7k DL). **JoyAI-Image-Edit**: "Why isn't
  JoyAI getting any love?" — adoption never materialized despite native ComfyUI;
  JD's buzz moved to video. **LongCat-Image-Edit**: largely bypassed; "official
  workflow gives unsatisfactory results" (Apr 2026). **VIBE**: dead in discussion.
  **HiDream-O1**: big launch, then "showcase doesn't match reality" pushback — mixed.

## 3. Try-on / clothing transfer — practitioner state of play

**The center of gravity split.** Kingroka's Qwen LoRA is no longer the sole standard;
the Aug-2026 picture is (a) Qwen-2511 native editing + LoRAs, (b) FLUX.2 Klein 9B
edit workflows, (c) dual-base LoRAs covering both.

- **fal/flux-klein-9b-virtual-tryon-lora** — the current community favorite by thread
  energy (674 pts / 76 comments; 4.4k monthly DL). Praised over IDM-VTON/OutfitAnyone
  for pose preservation at non-frontal angles and fabric drape. Skepticism in-thread:
  top comment jokes results look similar *without* the LoRA; fal-ad accusations.
  Community loudly demands a **4B version** (9B NC). Note: an in-thread claim that
  "klein license blocks commercial VTO" conflates the tiers — 4B Apache, 9B NC.
- **Klein 4B, no LoRA at all**, handles odd poses surprisingly well (90-pt thread) —
  cheap arm to test.
- **kingroka "Clothes Try On"** (Civitai 1940532): still the most-downloaded VTO asset
  (11.3k DL, overwhelmingly positive) but **frozen at v1.0 (Sep 2025), no successor**
  (his 2026 output is Klein/Z-Image LoRAs, nothing clothing-related; a Patreon-only
  experimental build likely dates to Sep 2025 — unconfirmed). Works on 2511 per
  comments; known weak: pattern transfer, shoes/hats.
- **"Attach Outfit & Try On [Qwen & Klein]"** (Civitai 2367983, updated Jun 18, 2026):
  the notable dual-base newcomer; "works fine with 2511" per comments; Klein-9B
  version is its most-downloaded; **explicitly non-commercial LoRA license**.
- **Semichka "Outfit Transfer Helper"** (Civitai 2111450): formalized 3-step
  extract→transfer pipeline, **commercial use allowed**; footwear rarely transfers.
- **FASHN VTON v1.5**: warm release reception ("first commercially usable open-source
  VTON") but modest uptake (repo 286★; the ComfyUI node `drphero/ComfyUI-FASHN-VTON`
  has 10★). **Zero complaints found about 576×864**; the real friction is the
  **NVIDIA-NC-licensed SegFormer human parser** — FASHN's official reply: parser is
  optional in maskless mode and replaceable. A July 2026 user's "can I use this in my
  SaaS" posts were mod-removed unanswered. Known "faint aura" artifact from
  background restoration (officially acknowledged).
- **BS-VTON** (Klein-9B person-to-person LoRA, Apr 2026): author deleted the HF repo —
  dead/unavailable; 4B attempt had artifacts and a lost checkpoint.
- **OrthoTryOn** (LongCat base, Apache, code+LoRA+dataset released): ~zero traction
  yet (16★) — first try-on artifact on a LongCat base, watch.
- **WearWow** (Jul 22 paper): still paper-only, no weights. **OmniTry**: adoption
  capped by 28GB VRAM. **No try-on LoRAs exist yet for FireRed/JoyAI/HiDream-O1 bases**
  (Chinese-community coverage thin — caveat).
- Wedding-dress thread (r/comfyui, Jul 30, freshest real-workflow consensus):
  **Qwen-2511 at 1024² for the try-on pass → Klein 9B at 2048² as refiner/face-fixer/
  upscaler**; "lace details always get mushy" → accepted answer: **preserve original
  garment pixels, generate only the person/scene, composite and retouch**.

## 4. Failure-mode practice (what people actually do)

- **Identity/face drift:** 2511's headline improvement (community-confirmed; most 2509
  LoRAs drop in unchanged); Klein 9B itself used as the face fixer at 2K; FaceDetailer
  + consistency LoRAs; per-identity likeness LoRA on 2511 for production characters;
  SAM3 masking + compositing over prompting. Krea 2 Identity Edit is the new
  wildcard. (ReActor/inswapper remains NC — community routes around it.)
- **Logo/text/detail loss:** no model-side fix trusted; paste-back of original garment
  pixels is the accepted answer; kingroka's own docs recommend SeedVR2 after ("fine
  details will be lost"); Klein cited as better than Qwen at detail retention
  (2 independent comments).
- **Worn-garment source:** two-step try-off → try-on via kingroka Outfit Extractor
  (10k DL) or Outfit Transfer Helper; single-shot person-to-person remains unsolved
  in open weights (BS-VTON dead).
- **Accessories/shoes/hats:** consistently broken across every open stack.
- **SeedVR2**: still the default open upscaler despite memory gripes.

## 5. Deltas vs `open-weights-model-catalog.md`

1. **Krea 2 open-weights release** is new — catalog written under the "Krea = API-only"
   assumption. Add as an arm candidate *for evaluation*; license (revenue cap) likely
   blocks the deploy path.
2. Community adoption inverts some catalog rankings: **FireRed/JoyAI/LongCat have
   near-zero practitioner traction** despite strong specs — expect to be on our own
   for workflows/LoRAs there. (Benchmarks earned them the eval slot anyway.)
3. The catalog's klein-4B-first stance is directionally confirmed but community
   quality signal concentrates on **9B** (NC); the 4B-vs-9B quality gap on try-on is
   exactly the experiment the community hasn't run — high-information for us.
4. FASHN v1.5's resolution cap worried us; the field reports don't mention it —
   the parser license and the "faint aura" artifact are the real issues.
5. FLUX 3 dev weights, if they ship open, reshuffle everything — track.

Primary threads/sources cited inline; full source lists in the two agent reports
(session transcripts, 2026-08-14).
