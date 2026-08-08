# Execution Conventions — Virtual Try-On Colab

Working agreement: planning docs live in this repo (VS Code); the notebook itself is
built and executed in Google Colab via the Colab MCP server; a snapshot of the
notebook is copied back into this repo on request and at delivery.

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
- [x] fal endpoint IDs confirmed (Aug 2026):
  - Qwen 2511 baseline: `fal-ai/qwen-image-edit-2511`
  - FLUX.2 klein 4B edit: `fal-ai/flux-2/klein/4b/distilled/edit` (multi-reference; ~$0.014/image)
  - Ideogram Character V3 edit: `fal-ai/ideogram/character/edit` (⚠️ schema wants character ref + mask — needs its own arg branch)
  - Krea 2: dropped — API takes only one content image (see NOTES.md)
- [ ] Per-endpoint argument schemas (cell 5 currently sends one generic `prompt` + `image_urls` shape)
- [ ] Pick LLM judge (vision-capable) and wire scoring prompt to rubric
