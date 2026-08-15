# V2 Extension Arms — open-weights candidates NOT on fal (deferred)

The V2 core eval runs five arms, all served on fal from the same open-weights
checkpoints (Qwen-Image-Edit-2511 baseline, FLUX.2 klein-4B, FASHN VTON v1.5,
FireRed-Image-Edit, Z-Image-Turbo refiner). The models below are open-weights and
catalog-vetted (`research/open-weights-model-catalog.md`) but have **no fal
endpoint**, so evaluating them means self-hosting from day one — deferred so the
core eval can iterate entirely on fal and switch to downloaded weights once, at
the parity stage, not per-arm.

## fal re-check, 2026-08-14

Two of these turned out to be servable on fal after all (promotion trigger 3):

- **HiDream-O1-Image** — `fal-ai/hidream-o1-image/edit` takes
  `reference_image_urls: list<string>` at $0.01/MP. **Promoted, run on Testset2,
  and eliminated** — see V2.0_RESULTS.md Run 3, finding 5.
- **JoyAI** — `fal-ai/joyai-image-edit` exists ($0.1/MP) but is the **single-image
  Edit**, not Edit-Plus; it has one `image_url`, so it cannot take person + garment.
  Testing Edit-Plus (1–5 refs, `JoyImageEditPlusPipeline` in diffusers main) still
  means self-hosting, or a stitched person+garment canvas through the single-image
  endpoint (a different, weaker experiment).
- Still no endpoint anywhere for OOTDiffusion, OrthoTryOn, LongCat-Image-Edit.
  Replicate carries IDM-VTON, but its CC-BY-NC-SA licence keeps it out of the
  deploy path — baseline value only.

## Extension candidates

| Arm | License | VRAM class | Why it might earn a slot |
|---|---|---|---|
| JoyAI-Image-Edit-Plus (JD) | Apache 2.0 | A100 (~24B pipeline) | Freshest multi-ref editor; e-commerce lineage; unproven on VTO |
| ~~HiDream-O1-Image(-Dev)~~ | MIT | FP8 ~10GB, T4 OK | **Eliminated 2026-08-14 on fal** — reframes the scene, no-ops on outerwear, identity substitution on 2/13 |
| OOTDiffusion | MIT (data provenance flag) | ~8–10GB, T4 OK | Dedicated VTO, big ecosystem; dated, identity drift |
| OrthoTryOn (LoRA on LongCat-Image-Edit) | Apache 2.0 | 24GB+ | Try-on + try-off + pose transfer in one adapter |
| LongCat-Image-Edit | Apache 2.0 | ~18GB offloaded | Single-image input only — needs stitched canvas; eclipsed by FireRed |
| Moebius (inpainter, support slot) | Apache 2.0 | tiny (0.22B) | FLUX-Fill-parity hole/background repair at >15× speed |

## Promotion triggers

Promote an extension arm into the eval only if:

1. the core five underperform on a specific axis it targets (e.g. identity →
   HiDream-O1's pixel-native path; worn-garment inputs → OrthoTryOn's try-off), or
2. a cheap qualitative screen (2–4 pairs, self-hosted on T4/A100) beats a core
   arm's outputs by eye, or
3. a fal endpoint appears for it (re-check before any promotion — fal adds
   open-weights models frequently; FireRed appeared within weeks of release).

Promotion cost: one arm-registry entry in the harness + a self-hosted inference
cell; the eval pipeline itself is arm-agnostic.

## Explicitly out (license-blocked for deploy, kept as eval baselines only)

IDM-VTON, FitDiT, CatVTON/FastFit, everything on FLUX.1-dev/Kontext/Fill bases
(OmniTry, RefTon, FitVTON, DreamO, ACE++...), klein-9B. See catalog §1.2/§2.3.
