# Notes — Virtual Try-On Eval

# ⚠️ EVALUATION FIRST, GUARDRAILS SECOND ⚠️

Use deterministic CV (pose, segmentation, embeddings) to **score** model outputs
before using it to **constrain** model inputs. Only add guardrails (masks, etc.)
where the metrics prove a model is drifting — adding machinery can make results worse.

## As post-processing (deterministic scoring out of the model)

- **Face-embedding distance** (input face vs. output face) → a number for identity preservation
- **Pose keypoint comparison** (skeleton before vs. after) → a number for pose consistency
- **Background diff** outside the clothing mask → a number for scene drift
- These make great eval metrics — objective, repeatable, no LLM-judge subjectivity —
  and complement the rubric scoring from before.

## Model considerations

- **Krea 2 cannot do try-on — via the API.** Verified against its OpenAPI spec: every endpoint
  takes exactly one content image (`image_url` + `strength`, img2img) plus style-only references —
  no second content slot, no mask. You physically can't feed it a person AND a garment.
  Ray's list has a wrong entry here — worth telling them.
  **But the Krea2 reference notebook proves a weights-level escape hatch exists:** it does
  two-image head swaps by self-hosting Krea 2 and patching it with a *community-trained LoRA*
  (`krea2_identity_edit_v1_2_r64.safetensors`) + custom ComfyUI nodes
  (`Krea2EditModelPatch` / `Krea2EditGroundedEncode`) that prepend two reference-latent token
  blocks to the sequence (image 1 = body scene, image 2 = identity face; per headswap_V2 source,
  which is public — repo also ships klein/qwen/kontext/omnigen2 pipelines). So two-image editing
  is *added trained weights*, not a native or promptable capability. A try-on analogue would mean
  training a garment-edit LoRA — real training data + GPU budget, out of scope for v1.
  This escape hatch does NOT transfer to Ideogram: its edit-capable weights are closed
  (only the FP8 *text-to-image* checkpoint is runnable), so there is nothing to patch.
- **Ideogram cannot do try-on either.** Verified all five fal.ai endpoints (character,
  character/edit, character/remix, v3/edit, v3/remix) plus Ideogram's native API: every one
  takes exactly one content image slot (`image_url`); character refs are identity-only (1 image
  max), `image_urls` are style-only. Empirically confirmed (2026-08-07): two images in
  `image_urls` on character/edit → pydantic "Field required" for singular `image_url`; a
  stitched-canvas probe on character/remix regenerated the collage, kept the person's original
  clothes, and mutated the garment. v3/edit's mask can only inpaint from *text*, so a specific
  garment can't be transferred faithfully. No workaround exists.
- **Flux 2 Klein** is real and open (4B is Apache-2.0/ungated; 9B is gated non-commercial),
  takes up to 4 reference images. BFL ships a purpose-built try-on endpoint,
  `/v1/flux-tools/vto-v2` (person + garment) — its internal schema name reveals it's Klein
  under the hood.
- **Dedicated try-on APIs** — a whole category not in the prompt:
  - **FASHN** (~$0.075; also open-sourced a 972M Apache-2.0 model that fits a T4)
  - **Google Vertex `virtual-try-on-001`** ($0.06; the only one with real mask control)
  - **Alibaba aitryon** (~$0.028; native top+bottom slots)

  These will almost certainly beat any general instruction-edit model on the average case.

## What the deliverable actually is

> **The eval harness is the product; the implementation is one row in its results table.**

One artifact, three stacked layers — value unevenly distributed:

1. **Implementation** — two images in, one out. ~30 lines for any API model. Smallest part.
   Delivering only this is the failure mode: a picture with no basis for "it's better."
2. **Comparison harness** — same N test pairs × K candidate models, cached, side by side.
   Turns "better than Qwen 2511" from a vibe into a statement. Stays useful forever —
   every future model release re-runs through it.
3. **Quality loop on a frozen model** — masking, compositing, seed search, prompting,
   preprocessing. Where the engineering judgment shows — and only possible because
   layer 2 tells you whether a change helped.

## Potential quality gates

- **Preprocess the inputs**: background-remove the garment, normalize to flat-lay,
  match aspect ratio to the model's native training resolution, upscale low-res inputs.
  Edit models degrade noticeably on aspect mismatch.
- **Best-of-N seed search + automatic scorer**: generate 4–8 seeds, auto-rank with
  DINOv2 garment-similarity + ArcFace identity metrics, return the winner.
  Real quality multiplier, pure orchestration — cost scales linearly, quality doesn't,
  so you tune N.
- **Prompt engineering (instruction-edit models)**: name what to *preserve*, not just
  what to change — "replace the shirt in image 1 with the garment in image 2, keeping
  the person's face, hair, pose, hands, and background completely unchanged."
  Explicitly referencing "image 1"/"image 2" matters when multiple refs are passed —
  BFL's own fashion prompting guide does exactly this.

## Final deliverable (frozen 2026-08-08)

**Approach in one paragraph:** seven hosted arms ran through a staged, budget-gated
pipeline — triage (7 arms x 4 pairs) → automatic top-50% elimination → grid
(5 arms x 12 pairs + best-of-2 seed stability) → held-out benchmark (18 pairs never
touched by any selection decision) — judged by three systems: a deterministic
evaluator harness (garment histogram, ArcFace identity cosine, MediaPipe pose diff,
background PSNR; weighted composite, garment x2, fixed absolute anchors), a blind
VLM judge (gpt-5.5, six-criterion rubric with schema-validated retries), and human
review as the supervising tiebreaker on flagged disagreements.

**What ships:**
1. **The Key — cascade implementation (default): seedream5_lite edit →
   qwen_image3 realism refine.** Chosen by human review corroborated by the frontier
   VLM — and subsequently validated on unseen data: on the 18 held-out pairs the
   cascade ranked #1 on the blind gpt-5.5 board (best garment, clean, and realism)
   and edged its stage-1 parent on the deterministic composite (0.522 vs 0.507),
   i.e. the refine pass measurably helps. The dedicated-pipeline arms
   (flux_vto_v1 0.642, fashn_v16 0.632 — within noise of each other) still top
   the deterministic holdout board via pixel-preservation metrics — decision
   and dissent both recorded.
2. **Single-model option: seedream5_lite** — top VLM board on the held-out set
   (4.19 overall), best garment fidelity on every judge that can see it.
3. **Baseline comparison module** — `compare_vs_baseline()` in notebook §12b runs
   cascade + seedream + Magic Hour baseline (qwen_2511) on the same inputs,
   side by side. The baseline lost to the shipped models on every judging system
   on unseen data.
4. **MVP eval harness** — model-agnostic registry + three-layer judging +
   per-stage boards + judge-agreement flags + complementarity ("checkbox") axes
   that surfaced the cascade pairing. Reusable for future bake-offs.
5. **Evidence pack** — `runs/final_report.html` (approach, boards, three-way
   side-by-side gallery), `runs/report.html` (every output with scores),
   cv_metrics.csv / vlm_judgments.csv, executed notebook snapshot.

**Notable caveats on record:** the deterministic harness is a work in progress —
reported table values carry human supervision (rankings validated, flagged
disagreements adjudicated by human review); seedream accepts no seed (outputs stochastic);
garment_sim is a color-histogram proxy (structure-blind — VLM covers structure;
CLIP-embedding upgrade is the Phase-2 fix); fashn_v16 is the pixel-preservation
champion (deterministic winner) and remains the recommendation when strict
original-photo preservation is the requirement; the fashn→klein cascade suggested
by raw axes-derivation was never tested and deliberately does not ship.

**Identity-restore experiments (2026-08-09, not shipped):** two composite variants
were attempted after the pilot — v2 (seedream output + full original photo through
qwen_image3 two-image edit) and v3 (same, with an auto-cropped face-only reference).
Human review found the restore inconsistent (v2 could pull original clothing back;
v3 fixed that structurally but face fidelity did not clearly beat the shipped blind
refine). The shipped composite remains v1. Run packages retained locally under
runs/grid_composite_v2_* / _v3_*.
