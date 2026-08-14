# Reference Notebook Analysis

Synthesis of the two reference notebooks in this directory
(`Copy_of_krea2_identity_edit.ipynb`, `MagicHourOptimize.ipynb`).
Companion to [TASK.md](../TASK.md) and [NOTES.md](../v1/NOTES.md).

## The big surprise

**Neither reference notebook calls hosted APIs.** Both run models locally on the
Colab GPU with weights cached to Google Drive. "Give you a card" likely means
paying for Colab Pro / A100 compute, not API credits. This reshapes the plan:
the try-on notebook is likely expected to be a *self-hosted GPU pipeline*, in
the same style as these references.

---

## Notebook 1: `Copy_of_krea2_identity_edit.ipynb` (Krea 2 head swap)

**What it is:** Magic Hour internal production demo — deterministic head/face
swap. Body image (scene/pose/clothing) + face image (identity donor) → face
transferred onto body.

**How it runs:** Krea 2 via **ComfyUI, self-hosted on the Colab GPU** (~18 GB
weights cached on Drive; ~1–2 min/image on A100). Thin-notebook design — all
real logic lives in a cloned repo (`github.com/malihashar/headswap_V2`), the
notebook just wires knobs → helper functions.

**Core spatial strategy — mask → crop → edit → soft-stitch:**
detect and mask the head region, crop it, run the diffusion edit only on the
crop, soft-blend it back. Everything outside the mask stays pixel-perfect.
For try-on: mask the *garment region* instead.

**Quality gates (deterministic, automated!):**
- `identity_cosine` — face-embedding cosine similarity donor↔result, warn < 0.35
- `body_preserve_psnr` — PSNR outside the edited region, warn < 28.0 dB
- → Magic Hour already scores outputs deterministically. This validates the
  "EVALUATION FIRST" strategy in NOTES.md and gives us the exact metric shape
  to mirror: fidelity metric + out-of-region preservation metric.

**Key knobs/defaults:** `SEED=46, STEPS=8, CFG=1.0` (distilled/turbo sampler),
`OUTPUT_LONG_SIDE=1024`, `STITCH=True`.

**Reproducibility stack worth copying:** pinned repo commit, per-run package
(`result.png` + `run_config.json` + `metrics.json` + `timing.json`), warm model
cache in a notebook global, `globals().get(knob, default)` fallbacks so cells
survive stale sessions, preflight cell (GPU/models/inputs), stakeholder
"eval card" summary cell.

## Notebook 2: `MagicHourOptimize.ipynb` (Ideogram 4 + LLM prompt enhancer)

**What it is:** Text-to-image with a two-stage pipeline, plus heavy inference
speed profiling ("Optimize"). **No image inputs at all** — not a try-on or
editing notebook.

**How it runs:** entirely local on the Colab GPU, HF auth only:
1. **Qwen2.5-VL-7B** (transformers, bf16) rewrites a rough user request into a
   strict **Ideogram 4 JSON prompt** — a structured art-direction brief:
   description, style (photo XOR art_style), hex color palettes, and a
   composition section with per-element bboxes on a 1000×1000 canvas.
2. VRAM handoff (`del` + `empty_cache()`), then **Ideogram 4 FP8**
   (`ideogram-ai/ideogram-4-fp8`, custom pipeline from
   `github.com/sxiayuan/ideogram4-optimization`) renders the JSON prompt.
   `num_steps=12`, guidance 4.0 then 8.0×11, seed in filename.

**Star pattern — generate → validate → self-correct loop:** LLM output is
validated (jsonschema + key order + bbox sanity); on failure the exact error
plus the bad output are fed back for up to 3 correction attempts. Belt-and-
suspenders: the prompt instructs the format, a validator checks it, and a
reorder function guarantees it.

**Eval:** structural only (the prompt JSON), zero perceptual scoring of images.
Nothing to reuse on the eval side.

---

## What this means for the try-on build

| Ingredient | Take from |
|---|---|
| Notebook skeleton: knobs → setup → upload → preflight → run → results → eval card | Krea2 notebook |
| Mask→crop→edit→stitch (garment region instead of head) | Krea2 notebook |
| Deterministic quality gates (fidelity cosine + out-of-region PSNR) | Krea2 notebook |
| Reproducibility (seed, run packages, pinned commits, Drive weight cache) | Krea2 notebook |
| Ideogram 4 structured-JSON prompting + validate/self-correct loop | Optimize notebook |
| VRAM sequencing to fit multiple models in one session | Optimize notebook |
| Colab plumbing (Drive HF cache, GPU assert, HF login) | Optimize notebook |

**Gaps neither notebook fills (we must build):**
1. **Garment conditioning** — neither shows "outfit image in". Krea2 comes
   closest (two-image identity edit); need to establish how each candidate model
   accepts a garment reference (native multi-image vs. stitched canvas).
2. **The comparison harness** — neither compares models. We must add the
   multi-model `try_on()` interface + side-by-side grids + Qwen 2511 baseline.
3. **Perceptual eval** — extend Krea2's two gates with garment-fidelity scoring
   (embedding similarity on the garment region) and optional VLM-judge rubric.

**Open questions raised:**
- Is Ideogram 4 (text-to-image, bbox-composition) even a fit for try-on, which
  needs image *editing*? Its role may be limited or need a creative harness.
- Do we get access to the `headswap_V2` repo (private?) to reuse its ComfyUI
  Krea2 runtime for a garment-edit config?
- Confirm compute plan: A100 Colab (both references assume it) vs. hosted APIs.
