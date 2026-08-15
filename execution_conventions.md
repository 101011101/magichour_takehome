# Deploy & Execution Conventions — Virtual Try-On

Working agreement: planning docs live in this repo (VS Code); the notebook itself is
built and executed in Google Colab via the Colab MCP server; a snapshot of the
notebook is copied back into this repo on request and at delivery.

## Dev → deploy convention

Code is written in VS Code (this repo). During development we temporarily call the
models via API (fal endpoints hosting open-weights models) because it is faster to
iterate — no weight downloads, no VRAM management. Once an arm wins, we switch to
properly downloaded open weights (diffusers on a Colab GPU) and re-test there; that
self-hosted path is what qualifies for deployment, and only its numbers count.

## V2 status & constraints (Aug 13 2026)

No longer a take-home — internship secured; this is being built toward **deployment
in Magic Hour company code** (see TASK.md). Ray builds; Runbo gave the prompt.

- **Deployed path: open weights only.** No proprietary hosted APIs (fal, Krea,
  Ideogram, seedream) in the final version — properly downloaded weights, self-hosted.
- **Testing exception:** remaining fal credits may be burned for experimentation,
  but only on endpoints hosting **open-weights models** (qwen-image-edit, flux
  klein, idm-vton, ...) so results stay portable to self-hosting.
- **Parity rule:** any number we claim for the final version must be reproduced on
  downloaded weights (diffusers on Colab A100), not fal — fal endpoints add their
  own preprocessing/defaults, so fal results are directional, not final.
- V1 winner (seedream→qwen cascade) is dead as-is: seedream is closed, fal-only.
  Known V1 regression to fix: identity degradation.
- The model/access table and fal registry below are V1-era; kept for reference.

## Drive layout & weight caching (Aug 14 2026)

Ray's Google account has 2TB storage. **Everything this project writes to Drive
lives inside `My Drive/Side projects and shi/`** — name confirmed against the
Drive API 2026-08-14: that *is* the full name, the trailing "…" was the UI
eliding nothing. `DRIVE_PROJECT_DIR` in notebook §1 already matches. Layout:

- `tryon_pilot_runs/` — V1 run packages (already there).
- `tryon_v2_runs/` — V2 run packages (per-run `run_config.json` + metrics + PNG),
  incl. `aux_selfhost/` for self-hosted outputs.
- `tryon_models/` — created 2026-08-14, everything weights-related lives under it.
- `tryon_models/hf_cache/` — Hugging Face cache. Notebook §13a mounts Drive and
  sets `HF_HOME` to this path, so any `from_pretrained()` / `hf_hub_download()`
  **downloads a model once into Drive on first use; every later session finds it
  in the cache and skips the download.** No custom sync scripts.
- Big checkpoints (~40GB class: Qwen-2511, FireRed) are copied Drive → VM local
  disk before loading (direct reads off the Drive mount are slow); klein-4B
  (~13GB) and small support models (BiRefNet, GFPGAN, AuraFace, …) load fine
  from cache.

## Test sets — what each one tests for (Aug 14 2026)

Two sets exist, and they answer different questions. Neither replaces the other:
`test_set/` is the breadth/demographics set, `Testset2/` is the difficulty and
resolution set. Always state which set a number came from — scores are not
comparable across sets.

### test_set/ — V1 set: human + garment-only, breadth-first

- **Shape:** 30 people + 30 garments, 30 curated 1:1 pairs (`pairs.csv`).
  Every garment reference is a **product shot** (flat-lay / ghost mannequin,
  no person in it). One pair kind only: **human + garment-only**.
- **Testing for: population coverage and fair comparison.** Stratified quotas
  (10/10/10 skin tone, 10/10/10 body size, 15/15 gender, 7 hand-over-torso)
  so a model cannot win by being good on one demographic. Difficulty is graded
  4 easy / 14 medium / 12 hard, with hard garments deliberately paired to hard
  poses.
- **Known limit:** everything was normalized to 1024px max side, which is
  **too soft for identity metrics** — face crops lose the detail AuraFace needs.
  This is what motivated Testset2.
- **Used by:** the V2 notebook (`v2/virtual_tryon.ipynb`) for triage → grid →
  holdout, and as the BEFORE set for the auxiliary screen.

### Testset2/ — V2 set: high resolution, garment-only AND garment+human

- **Shape:** 8 people + 12 garments, full-resolution originals (up to
  5152×7728; capped to 1536 on the long side only at upload). Mixed formats
  (jpg/webp/avif) normalized to JPEG by the harness. Includes two
  **`_nonceleb` controls** because celebrity faces may be memorized by the
  models and inflate identity scores.
- **Testing for: resolution-sensitive fidelity, and garment references that
  are themselves photos of people.** Three pair kinds (`v2/build/ts2_harness.py`
  matrix, 13 pairs):

| kind | n | garment reference is… | what it tests |
|---|---|---|---|
| `product` — **garment only** | 6 | flat-lay / ghost mannequin, no person | the normal shop→model case at high res: print, text, fine stripes, lower-body items, plus a back-view pose control |
| `duo_lookbook` — **garment + human** | 4 | an editorial on-model photo (a model wearing the look) | can the model lift a garment off another person (model2model) without importing that person |
| `duo_swap` — **garment + human** | 3 | a `people/` photo used as the garment source | pure clothes swapping: put what person B wears onto person A |

- **Why the duo kinds matter:** the benchmark literature has every open model
  collapsing here (VTEdit Model2Model: best 2.06, Qwen 1.17, klein 1.03), so
  the duo rows discriminate between arms while the product rows mostly do not.
  The specific failure they hunt is **identity substitution** — the result
  showing the reference's person instead of the input's — tracked by the
  `wrong_person` flag in the VLM schema.
- **Duo mechanics:** on-model references show a whole outfit, so each duo pair
  carries a **target-garment designation** ("the long beige coat") that goes
  into the prompt for prompt-based arms, and FASHN gets
  `garment_photo_type="model"` instead of `"flat-lay"`.
- **Scoring caveat:** for duo pairs the garment metric compares against a
  **torso crop of a real photo** (domain-matched to the output); for product
  pairs it compares against a **flat-lay** (domain gap). Duo garment scores are
  therefore inflated relative to product — compare arms *within* a kind, never
  scores *across* kinds.

### What each evaluation layer tests

- **Deterministic metrics** (free, local): garment similarity (FashionSigLIP),
  identity (AuraFace), pose displacement, background PSNR → fixed-anchor
  composite with garment ×2. Authoritative for elimination.
- **VLM judge** (gpt-5.5, blind): six 1–5 criteria bucketed into **fidelity**
  (garment, identity, scene) and **realism** (clean, hands, realism), plus
  `wrong_person`. Authoritative for realism, where deterministic metrics are weak.
- **Auxiliary screen** (`v2/build/aux_harness.py`): a different question
  entirely — single-image realism models scored against **their own input**
  ("did it change what it was given?"), gated on fidelity ≥ 4.5.
- Full criteria and bucket definitions: `prd/v2/SCORING_CRITERIA.md`; test
  conditions and model rationale: `prd/v2/results_summary/CONDITIONS.md`;
  rolling results: `prd/v2/results_summary/V2.0_RESULTS.md`.

## Goal

A Colab notebook that takes a person image + a garment image and produces the person
wearing that garment — beating the website's current Qwen 2511 output on a shared
test set. See PROMPT.md for the original request.

## Models & access (confirmed Aug 2026)

| Model | Access | Route in notebook |
|---|---|---|
| Qwen-Image-Edit-2511 (baseline) | Open weights + hosted | fal.ai hosted endpoint |
| Krea 2 (Medium/Large) | API-only | fal.ai (official partner) |
| Ideogram Character V3 (Edit) | API-only | fal.ai |
| FLUX.2 [klein] 4B (Apache 2.0) | Open weights (~13GB VRAM) + hosted | fal.ai primary; optional local T4 cell |

Single provider: **fal.ai** — one client, one API key (funded by Ray's card).
Optional zero-cost path: run FLUX.2 klein 4B locally on the Colab T4.

## Notebook outline

1. **Setup** — `pip install fal-client pillow`, API key entry (getpass, never printed).
2. **Inputs** — upload person + garment images, or use the bundled test pairs.
3. **Test set** — N≈6–10 person/garment pairs covering: full-body/half-body,
   plain/patterned garments, simple/busy backgrounds, varied poses & skin tones.
4. **Inference** — one function per model behind a common interface:
   `try_on(person_img, garment_img, model) -> result_img`. Run all 4 per pair.
5. **Comparison grid** — matplotlib grid: rows = test pairs, cols = models,
   Qwen 2511 first as baseline.
6. **Eval** — rubric scoring per output:
   - Garment fidelity (color, pattern, cut transferred faithfully)
   - Identity preservation (face, hair, body unchanged)
   - Pose & background consistency
   - Artifact-free (hands, seams, textures)
   Scored 1–5 by an LLM judge (vision model) + human-review cell; tally vs baseline.
7. **Verdict** — table of mean scores per model, wins/losses vs Qwen 2511.

## How Colab & the tooling work

A notebook has two separate parts: the **file** (`.ipynb` — JSON with code/markdown
cells) and the **kernel/runtime** (the machine that executes cells). Colab hosts both:
the file lives in Google Drive, and each session gets a temporary Google cloud VM
(free T4 GPU available). The VM is ephemeral — anything not saved out is lost when
the session ends; variables persist only within a running session, cells run top to
bottom.

Three ways to touch the same notebook:

- **Browser** (colab.research.google.com): the normal Colab UI; open the notebook
  from Drive, pick a GPU runtime (Runtime → Change runtime type → T4), Run all.
- **VS Code Colab extension** (installed): opens a notebook file in VS Code and
  connects it to a Colab cloud kernel (Select Kernel → Colab → Auto Connect), so
  cells run on Google's GPU while you edit locally. Your manual window into runs.
- **Colab MCP server** (connected in Claude Code): lets Claude create notebooks in
  Drive, write/reorder cells, execute them on the Colab runtime, and read outputs
  (stdout, errors, images). This is how the notebook gets built and iterated.
  Auth is Google OAuth (approved in browser on first connect), no API key.

Delivery: the final notebook is shared via a GitHub "Open in Colab" badge URL
(`https://colab.research.google.com/github/<user>/<repo>/blob/main/<file>.ipynb`),
which is how Ray's reference colabs work too.

## Workflow

1. Claude edits planning docs here → makes Colab MCP calls to write/run cells.
2. User watches the notebook live in their Colab account; can run cells via the
   VS Code Colab extension or browser.
3. On request / at the end: notebook snapshot committed here as `virtual_tryon.ipynb`
   with an Open-in-Colab badge in README.

## Open items

- [x] Colab MCP connected in Claude Code session — works (edit/run cells). Gotcha:
  MCP edits live only in the browser tab; **File ▸ Save after edits** or a tab
  reload silently discards them (happened once). Huge inline outputs (full-res
  matplotlib grids) can also stall the MCP connection — keep displays thumbnailed.
- [ ] fal.ai account + API key (Ray's card) → Colab Secrets as `FAL_KEY`
- [x] Assemble curated test pairs — `test_set/` (Aug 8): 30 people + 30 garments,
  stratified per TESTSET_PLAN.md (scaled from 120+120 under the $10 eval budget);
  quotas held: 10/10/10 skin tone, 10/10/10 body size, 15/15 gender, 7 hand-over-torso.
  `manifest.csv` = tags/sources/deviations; `pairs.csv` = 30 curated pairs
  (hard garment → hard pose; 4 easy / 14 medium / 12 hard).
- [ ] Swap notebook inputs from placeholder images (OOTDiffusion / IDM-VTON demo
  samples) to `test_set/` + `pairs.csv` — needs the repo on GitHub (or Drive upload)
  so the Colab runtime can fetch the images.
- [x] Drive project folder name confirmed via the Drive API (2026-08-14):
  `Side projects and shi` is the literal full name. `tryon_models/` created
  under it; `HF_HOME` → `tryon_models/hf_cache` in notebook §13a.
- [x] fal endpoint IDs + full argument schemas confirmed for all 7 arms
  (2026-08-08, live /api pages) — registry lives in the notebook §5; arm table
  with prices/gotchas in `prd/V1_PILOT.md`. Notables: FLUX VTO **v2 not on fal**
  (using `fal-ai/flux-pro/v1/vto`); Ideogram cut (see NOTES.md); Qwen-Image-3
  needs `enable_prompt_expansion=False`; Seedream has no seed param.
- [ ] Pick LLM judge (vision-capable) and wire scoring prompt to rubric
