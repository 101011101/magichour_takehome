# v2.2 Plan — architecture and product design

Where each mitigation sits, what it exposes, how it fails safely, and the order
to build it in. Production constraint throughout: **anything in the deployed path
is open-weights, runs self-hosted, and must never hand the model a broken input
or hand the user a broken output.** Every stage below is either deterministic
CPU code or an open-weights segmentation model, and every stage has a
pass-through tier.

## 1. Pipeline position

```text
person image ─────────────────────────────────────────────┐
                                                          │
garment reference ──► [A] garment_prep  ──► cropped ref ───┤
                       (pre-processing)                   │
                                                          ▼
                                            klein 4B edit (open weights)
                                                          │
                                                    candidate
                                                          │
                                      [B] output_guard ───┤ degenerate? ──► reseed (<= 2)
                                       (post-generation)  │                    │
                                                          │◄───────────────────┘
                                                          ▼
                              [C] restore_protected  ──► final image
                               (post-generation, accept/restore only)
                                                          │
                                    ┌─────────────────────┴───────────────┐
                                    ▼                                     ▼
                      [D] predicted-warp metric              [E] quick VLM check
                            (eval only)                          (eval only)
```

| Stage | Path | Bucket | Open weights |
|---|---|---|---|
| [A] `garment_prep` | production | pre-processing | segmentation only; numpy/PIL otherwise |
| [B] `output_guard` | production | post-generation | none — pure CPU statistics |
| [C] `restore_protected` | production | post-generation | person matte + human parsing |
| [D] predicted warp | eval only | measurement | DINOv2/LoFTR features, local |
| [E] quick VLM check | eval only | measurement | gpt-5.5, never deployed |

[D] and [E] are evaluation instruments by construction (POTENTIAL_FEATURES §2, §3)
and must not acquire a production caller.

## 2. [A] Garment reference cropper — BUILT (see RESULTS.md)

Implemented as `v2/build/garment_crop.py`. Deterministic pre-processing of the
garment reference: segment the subject, fill the background white, crop to the
whole-subject bounding box with a safety margin, and optionally remove the head
or all skin. Rationale as argued in
[POTENTIAL_FEATURES.md](../ideas/POTENTIAL_FEATURES.md) §1 — multi-image editors
spread attention roughly uniformly over reference tokens, so a white,
tightly-cropped reference spends those tokens on the garment instead of on a room
and a stranger's face.

### As-built architecture (2026-08-15)

Two models with a strict division of labour:

| Stage | Model | Role |
|---|---|---|
| Subject alpha | **BiRefNet_lite**, 224MB ONNX, MIT, run at 1024x1024 on onnxruntime | Owns the **outer boundary**. Produces true soft alpha (0.6-1.1% fractional pixels) |
| Semantic labels | **MediaPipe Selfie Multiclass**, 447KB, 256x256 | Owns **interior class assignment** only — clothes / body-skin / face-skin / hair |
| Product route | Pure OpenCV — corner-patch background colour, edge-connected fill, Otsu retry | Flat-lay and ghost-mannequin references need no model |

Three architectural rules, each learned by measurement rather than assumed:

1. **Composition is subtractive, never intersective.** `subject x clothes_class`
   hands the outer boundary back to the 256x256 map and notches 6px blocks out of
   the silhouette. Build C3 = matte - head, C4 = C3 - body skin, so the
   high-resolution matte always owns the outline and the coarse map only ever
   operates on interior regions.
2. **No post-filter on the subject matte.** Trimap + guided-filter matting over
   the BiRefNet output made results worse — guided filtering transfers image
   structure into alpha, and dark fabric on a white ground is its worst case
   (white speckles ~15px into a navy sleeve). The raw matte is used as-is.
   Trimap refinement is confined to the internal clothes-vs-skin edge.
3. **Whole-body crop, no category band.** The shoulders-to-hips / hips-down prior
   is deleted; it caused the peacoat to drag in the jeans as a band artifact.
   Target-garment selection belongs to the prompt. `select_region` is stubbed and
   defaulted off for a future selectable version.

Variants are named **C1-C4** (C for crop) — C1 `bbox`, C2 `bbox_nobg`,
C3 `no_face`, C4 `clothes_only`. Model-facing outputs are explicitly
white-flattened RGB; alpha PNGs and SVG contours are inspection artifacts only.

**Deployment note.** BiRefNet is MIT with weights, so it is consistent with the
open-weights constraint, and adds ~224MB beside klein's ~13GB. On CPU the matte
costs 104-320s per reference and is cached; on GPU it is ~17 FPS at 1024x1024.
Garment crops are cacheable per catalog image rather than recomputed per request,
so the amortised production cost is close to zero. Process-level parallelism was
measured and made things **slower** on an 8GB machine (RAM exhaustion into mmap
paging); default is 1 worker.

### Interface

```python
# v2/build/garment_prep.py
@dataclass
class GarmentRef:
    image: PIL.Image.Image      # always valid, always RGB, never alpha
    tier: str                   # "segment_fill" | "bbox_crop" | "passthrough"
    confidence: float           # segmentation confidence, 0.0 when passthrough
    mask_area_frac: float       # dominant-component area / image area
    bbox: tuple[int, int, int, int] | None
    reason_codes: list[str]     # e.g. ["LOW_CONF", "MULTI_COMPONENT", "TINY_MASK"]

def prepare_garment_reference(
    image: PIL.Image.Image,
    duo: bool,                  # reference is a photo of a person (Testset2 kind)
    target: str | None,         # target garment phrase, for text-prompted seg
    cfg: CropperConfig,
) -> GarmentRef: ...
```

`duo` selects the segmentation route: a product shot needs foreground-vs-white
separation, a duo reference needs the garment lifted off a person and the
reference person's head removed — the single largest source of the second
identity in the prompt.

### Fallback chain (mandated order, POTENTIAL_FEATURES §1)

| Tier | Condition | Output |
|---|---|---|
| 1 `segment_fill` | segmentation confidence >= `min_conf` **and** dominant component >= `dominant_frac` of mask area **and** mask area within `[min_area_frac, max_area_frac]` | garment on white, cropped to bbox + margin |
| 2 `bbox_crop` | segmentation ran but failed a tier-1 condition | crop to mask bbox + margin, background left intact, no fill |
| 3 `passthrough` | segmentation errored, returned nothing, or produced a mask touching all four borders | the original image, unmodified |

Hard invariants, checked before return in every tier: output is RGB (never alpha
— model VAEs are 3-channel), min side >= `min_side_px`, aspect within
`[1/4, 4]`, and the crop box is inflated by `margin_frac` of the bbox diagonal so
sleeves and hems are never clipped. Any invariant failure demotes to the next
tier; a tier-3 failure is impossible by construction (it returns the input).
Deterministic for identical input — fixed model weights, fixed thresholds, no
sampling. `tier`, `confidence`, and `reason_codes` are logged per run and
persisted in the harness JSON sidecar.

### Segmentation backends — as built

| Route | Models | License | Used for |
|---|---|---|---|
| `product_opencv` | none — corner-patch background estimate, edge-connected fill, adaptive tolerance with Otsu retry | n/a | flat-lay, ghost mannequin (6 references, all clean) |
| `duo_biref_multiclass` | BiRefNet_lite (outline) + Selfie Multiclass (interior labels) | MIT / Apache | worn and person-source references (7 references, all usable) |
| `duo_heuristic` (fallback only) | YCrCb/HSV skin range | n/a | retained but **not trusted** |

The skin-colour heuristic is a fallback of last resort. It was built first and
measured: it tore a wedge out of the beige coat on a dark-skinned model and read
the brown plaid overcoat as skin entirely. That is a bias failure, not a
threshold failure, and no parameter value fixes it. SCHP and Sapiens were not
needed — the multiclass model plus a high-resolution matte covers the same
ground at a fraction of the download.

### Config knobs

```python
CropperConfig(
    enabled=True,
    min_conf=0.60,
    dominant_frac=0.70,        # largest connected component share of mask area
    min_area_frac=0.02,        # smaller mask => detection failure, demote
    max_area_frac=0.95,        # near-full-frame mask => no separation achieved
    margin_frac=0.06,          # of bbox diagonal
    fill=(255, 255, 255),
    min_side_px=256,
    max_side_px=1536,          # matches ts2_harness MAX_SIDE
    duo_drop_classes=("face", "hair", "head"),
    backend="auto",
)
```

## 3. [B] Degenerate-output detector and reseed

Cheapest mitigation, highest reliability payoff: klein's failure is a
near-constant frame, which is trivially separable from a photograph by pixel
statistics. No model, no network, no ambiguity.

```python
# v2/build/output_guard.py
@dataclass
class OutputVerdict:
    ok: bool
    severity: str               # "ok" | "suspect" | "degenerate"
    reason_codes: list[str]
    stats: dict                 # global_std, laplacian_var, unique_colors, mean_luma, face_found

def check_output(result: Image, person: Image, cfg: GuardConfig) -> OutputVerdict: ...

def generate_with_retry(
    call: Callable[[int], Image],   # arm invocation, takes a seed
    person: Image,
    cfg: GuardConfig,
) -> tuple[Image, OutputVerdict, list[int]]:   # image, final verdict, seeds tried
    ...
```

Checks, in evaluation order (all CPU, all thresholds frozen config):

| Check | Trips `degenerate` when | Note |
|---|---|---|
| global pixel std | `< std_min` | catches solid black/white/constant colour |
| Laplacian variance | `< lap_min` | catches flat and blur-out frames |
| unique-colour count (downsampled) | `< colors_min` | catches banded/posterized garbage |
| mean luminance | `< luma_min` or `> luma_max` **and** std low | black or blown frames |
| face present | person image has a face, result has none | catches wholesale scene loss |
| size/aspect | differs from person image beyond `aspect_tol` | catches endpoint reframing |
| `identity_cos` floor | `< id_floor` | `suspect` only — never auto-discards |

Only the first five can force a retry. `identity_cos` and aspect drift raise
`suspect`, which is logged and surfaced in the artifacts page but does not throw
away work — a strict identity floor would silently prefer conservative outputs
and re-open the FASHN-vs-klein trade the program already decided.

Retry policy: up to `max_retries=2` fresh seeds (`seed + 1`, `seed + 2`,
deterministic, never random). If all attempts are rejected, return the **best
attempt by `severity` then `laplacian_var`** together with a failing verdict —
the caller always receives an image, and the production surface decides whether
to show it or ask the user to retry. Never returns `None`. Cost of retries is
bounded and logged.

```python
GuardConfig(std_min=6.0, lap_min=15.0, colors_min=512,
            luma_min=6.0, luma_max=249.0, aspect_tol=0.05,
            id_floor=0.25, max_retries=2)
```

## 4. [C] Protected-region restore

The accuracy half of
[INTENTION_AWARE_FIDELITY.md](../ideas/INTENTION_AWARE_FIDELITY.md), scoped down
to the two decisions that serve accuracy: `accept` the garment edit, `restore`
protected content that was regenerated by accident. The `repair` class, the
uncertainty band, and the seam-harmonization pass are **v2.3** and are not built
here — the interface leaves room for them and nothing more.

```python
# v2/build/restore_protected.py
@dataclass
class RestoreResult:
    image: Image
    applied: bool
    restored_frac: dict[str, float]   # per group: share of that group's area restored
    registration_conf: float
    reason_codes: list[str]

def restore_protected(
    person: Image, candidate: Image, garment_ref: GarmentRef,
    cfg: RestoreConfig,
) -> RestoreResult: ...
```

Stages, reusing the guardrail doc's decomposition verbatim so the two documents
do not drift:

1. **Register + colour-normalize** the candidate to the person image (ECC or
   feature homography). Record `registration_conf`; below `min_reg_conf`, return
   the raw candidate.
2. **Decompose** the person image into semantic groups: person matte, parts
   (face, hair, hands, skin), garment zone (dilated), background.
3. **Diff** aligned pair in Lab + edge space; group changed pixels into
   components; split any component crossing a group boundary.
4. **Decide** per region: `restore` only when the region lies in a protected
   group, has low overlap with the dilated garment zone, and is not attached to
   the garment via the region graph. Everything else is `accept`. No region is
   ever restored inside the garment zone.
5. **Composite** with the gradient acceptance map, Gaussian-feathered at the
   transition band only (`feather_px`). No generative repair pass runs here.

Guard rails against the known laundering risk: if `restored_frac["background"]`
or the total restored area exceeds `max_restore_frac`, the stage returns the raw
candidate rather than a near-total paste-back — a stage that restores everything
would score beautifully on preservation and delete the product.

```python
RestoreConfig(
    enabled=True,
    groups=("face", "hands", "background"),   # hair and skin deliberately excluded for now
    garment_dilate_px=24,
    min_reg_conf=0.55,
    feather_px=6,
    max_restore_frac=0.35,
    color_normalize=True,
)
```

Note carried from the guardrail doc: global colour normalization can pull the new
garment away from the reference colour. High-acceptance regions are excluded from
the colour-matching estimate; if H4b fails, this is the first thing to check.

## 5. [D] Predicted-warp garment metric — eval only

```python
# v2/build/metrics_warp.py
def warp_fidelity(garment_ref: Image, result: Image, duo: bool,
                  cfg: WarpConfig) -> dict:
    """-> {match_rate, warp_ssim, warp_lpips, color_hist_dist, occluded_frac,
           reliability, overlay_path}"""
```

Segment the garment region in the result, match features between reference and
that region (DINOv2 patch features or LoFTR; SIFT for strongly textured
garments), fit a thin-plate spline to the correspondences, warp the reference,
and compare the overlay against the result region with SSIM/LPIPS plus colour
histogram distance. Occluded areas (crossed arms) are masked out of the score.
`reliability` is low when `match_rate` is low — solid-colour garments have few
features, so **the match rate is always reported next to the score** and a
low-reliability score never feeds a gate. A checkerboard overlay is persisted per
run for visual review.

## 6. [E] Quick VLM check — eval only

Coarse pass/fail per candidate: target garment present, person intact, gross
artifact absent. Same client and retry machinery as `ts2_harness.judge_all`, a
much shorter prompt, one image. Scope guard from POTENTIAL_FEATURES §2: evals
only, never the production path, never the fidelity judge — VLM judges are
insensitive to the localized damage v2.2 targets, so this filters gross failures
cheaply while the deterministic metrics carry the verdict. Its agreement with
`output_guard` is itself a reported number: disagreements are the interesting
rows.

## 7. Harness integration

`ts2_harness.py` keeps its matrix, arms, prompts, and `wrong_person` flag
unchanged. Added: a `CONFIGS` table of pre/post hooks and a seed list.

```python
CONFIGS = {
    "base":         {"crop": False, "restore": False, "retry": False},
    "crop":         {"crop": True,  "restore": False, "retry": False},
    "restore":      {"crop": False, "restore": True,  "retry": False},
    "crop_restore": {"crop": True,  "restore": True,  "retry": True},
}
```

Output naming moves from `{arm}__{id}.png` to `{arm}__{config}__{id}__s{seed}.png`;
existing v2.1 files are read as `(config="base", seed=46)` so no prior work is
re-paid for. The JSON sidecar gains `config`, `seed`, `crop_tier`,
`crop_reason_codes`, `guard_verdict`, `seeds_tried`, `restore_applied`,
`restored_frac`.

## 8. Build sequence (dependency order)

| # | Step | Depends on | Gate to proceed |
|---|---|---|---|
| 1 | `output_guard.check_output` + injected-frame test set | — | H3 detector bars met offline (free) |
| 2 | Harness config/seed plumbing, new naming, sidecar fields | 1 | existing v2.1 outputs still load and score |
| 3 | `garment_prep` tiers 1-3 + invariants + tier logging | 2 | 100% valid output on all 12 Testset2 references, zero truncations under manual review |
| 4 | `metrics_warp` + overlays | 2 | runs on v2.1 outputs already on disk; H5 correlation computed for free |
| 5 | Ablation generation: 2 *generated* configs (`base`, `crop`) x 13 pairs x 3 seeds; the two `restore` configs are derived post-hoc from these outputs | 3 | budget approval — this is the only paid step besides judging |
| 6 | `restore_protected` (register, decompose, diff, restore, composite) | 2 | applied post-hoc to step-5 `base` outputs first, so it costs nothing to iterate |
| 7 | Quick VLM check + VLM judging of the ablation | 5 | budget approval |
| 8 | `make_v22_page.py` -> `v2/artifacts/v22_accuracy.html`, RESULTS.md fill | 5, 6, 7 | — |

Step 6 sits after step 5 deliberately: `restore_protected` is a pure
post-generation function, so it can be developed and ablated against already-paid
outputs. Only the cropper needs new generations, because it changes the model's
input.
