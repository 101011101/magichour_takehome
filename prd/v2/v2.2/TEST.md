# v2.2 Test — ablation design, metrics, gates, cost

Reuses `v2/build/ts2_harness.py` (matrix, arms, prompts, `wrong_person`) and the
metric definitions in [SCORING_CRITERIA.md](../SCORING_CRITERIA.md). Nothing new
is defined here that already exists there.


## TODO — simplify this document

**This test design is overcomplicated for where v2.2 actually is** (noted
2026-08-15). It was written against the earlier five-component scope and still
carries: a four-config matrix, three seeds, 156 outputs, and columns for the
predicted-warp metric and quick VLM check that are now out of scope
(../V2.x_DIRECTIONS.md).

What it should become, per EXPERIMENT.md section 4:

- **Three configs** — `base`, `v221`, `v222` — not four.
- **Testset2, all 13 pairs** (already correct below; the V1 set stays excluded).
- **Human review as the primary judge**, deterministic metrics and the VLM
  rubric as supporting evidence, no pre-registered numeric gates.
- Drop the warp-metric and quick-VLM columns.
- 2.2.3 verdicts recorded, retry not fired.

Left as-is for now; simplify before the run.

## 1. Test set and pair kinds

`Testset2/`, all 13 pairs, unchanged matrix from `ts2_harness.MATRIX`.

| kind | n | Role in v2.2 |
|---|---|---|
| `product` | 6 | non-inferiority control for H1b — the cropper must not cost anything on the case that already works |
| `duo_lookbook` | 4 | on-model reference; primary H1 signal |
| `duo_swap` | 3 | whole-person reference, klein's weakest kind (fidelity 3.89); the sharpest H1 signal |

`test_set/` (V1, 1024px) is not used: it is too soft for identity metrics and has
no duo kind, which is the whole point of this workstream. Cross-set and
cross-kind score comparisons remain invalid (CONDITIONS.md §3) — every table is
read within a kind.

## 2. Arms and configs

One arm under test: `klein_4b_edit`. `fashn_v15` and `qwen_2511` are **not
re-run**; their v2.1 numbers are quoted as reference lines only.

| Config | Generated? | Crop | Restore | Reseed | Source |
|---|---|---|---|---|---|
| `base` | yes | off | off | off | new seeds + the 13 existing v2.1 outputs at seed 46 |
| `crop` | yes | on | off | off | new |
| `restore` | no — derived | off | on | off | `restore_protected` applied to `base` outputs |
| `crop_restore` | no — derived | on | on | on | `restore_protected` applied to `crop` outputs |

Seeds `46, 47, 48`, identical across configs, so every comparison is paired at
the `(pair, seed)` level rather than a difference of independent means. Seed 46
`base` outputs already exist on disk and are reused rather than re-paid.

Reseed is only exercised in `crop_restore`; because it fires only on a degenerate
frame, it changes neither the paired design nor the cost materially. `base`
deliberately records degenerate frames without replacing them — that is the only
way to observe the natural failure rate at all.

## 3. Metrics

### Deterministic (free, local, all 156 outputs)

| Metric | Source | Used for |
|---|---|---|
| `garment_sim` | `metrics_v2` FashionSigLIP, duo refs via `_torso_crop` | H1a, H1b, H4b |
| `identity_cos` | `metrics_v2` AuraFace | H4a |
| `bg_psnr` | `metrics_v2` background PSNR | H2, H4a |
| `pose_err` | `metrics_v2` landmark displacement | H2 |
| `score` | anchored composite, garment x2, `CV_ANCHORS` unchanged | summary only |
| `warp_ssim`, `warp_lpips`, `match_rate`, `color_hist_dist` | new `metrics_warp` | H5, F4 |
| `guard_severity`, `reason_codes`, `seeds_tried` | new `output_guard` | H3 |
| `crop_tier`, `crop_conf`, `mask_area_frac` | new `garment_prep` | H1 diagnosis |
| `restored_frac`, `registration_conf` | new `restore_protected` | H4 diagnosis |

Anchors are **not** recalibrated for v2.2 — changing anchors mid-workstream would
make the ablation incomparable to v2.1.

### VLM (paid, blind gpt-5.5, seed 46 only, 52 judgments)

Existing `ts2_harness` rubric, unchanged schema: `garment`, `identity`, `scene`,
`clean`, `hands`, `realism`, `wrong_person`, `note`; fidelity = mean(garment,
identity, scene), realism = mean(clean, hands, realism). Judging is blind to
config as well as to arm — configs are shuffled and unlabelled in the request.
`judge_all`'s existing cache key extends to `(arm, config, id, seed)` so nothing
is ever re-judged.

Seeds 47 and 48 are scored deterministically only. The VLM is the authority for
realism and the garment score; the extra seeds exist for paired deterministic
power and for failure counting, where they are free.

### Quick VLM check (paid, cheap, all 156 outputs)

Coarse pass/fail: garment present, person intact, gross artifact. Reported
against `output_guard` verdicts as an agreement table; disagreements go to human
review. Eval only.

### Human review

Mandatory for two things the metrics cannot settle: garment truncation in cropped
references (H1 "done when: zero truncations"), and confirmation of any
predicted-warp lookalike case (H5).

## 4. Gates

| Gate | Condition | Consequence |
|---|---|---|
| G1 | H1a met, H1b and H1c hold | cropper defaults **on** in the deployed config |
| G2 | Any `wrong_person` > 0 in any config | that config is rejected outright |
| G3 | H3 false-positive rate > 0 on good outputs | detector thresholds re-tuned before any deployment |
| G4 | H4a met, H4b and H4c hold | restore defaults **on**; otherwise it stays flagged off |
| G5 | Cropper tier-3 pass-through > 20% of references | segmentation backend is inadequate — swap backend before judging H1 |
| G6 | \|rho\| < 0.3 for H5 | warp metric is diagnostic-only, excluded from every gate |
| G7 | H4c `clean` regression beyond bar | seam handling handed to v2.3; restore stays flagged off until then |

## 5. Sample size and what it can support

| Comparison | Paired units | Honest reading |
|---|---|---|
| Deterministic, all pairs | 39 (13 x 3 seeds) | directional; report per-pair deltas and a sign test, not just means |
| Deterministic, duo pairs | 21 (7 x 3) | directional only |
| VLM, all pairs | 13 | directional only; a 0.30 bar on a 1-5 integer scale is one notch on ~40% of pairs |
| VLM, duo pairs | 7 | weakest link in the design; must be stated wherever H1 is quoted |
| Natural degenerate frames | ~2 expected at 6% over 39 `base` runs | descriptive count, never a rate estimate |
| Injected degenerate frames | 20 synthetic | sufficient for the detector's recall bar |

This is the same sample-size caveat carried in V2.1_RESULTS.md §"Open caveats",
and it does not go away because the workstream changed. Results are product
judgement plus directional evidence.

The parity rule also still applies: every number will come from fal-hosted
open-weights endpoints and is directional until the winning configuration is
re-run on downloaded klein weights.

## 6. Files and flags to add

| File | Status | Contents |
|---|---|---|
| `v2/build/garment_prep.py` | new | `prepare_garment_reference`, `CropperConfig`, `GarmentRef`, tier logic |
| `v2/build/output_guard.py` | new | `check_output`, `generate_with_retry`, `GuardConfig`, injected-frame fixtures |
| `v2/build/restore_protected.py` | new | `restore_protected`, `RestoreConfig`, register/decompose/diff/composite |
| `v2/build/metrics_warp.py` | new | `warp_fidelity` + checkerboard overlay writer |
| `v2/build/ts2_harness.py` | edit | `CONFIGS` table; hooks into `generate`/`score_all`/`judge_all`; new output naming and sidecar fields |
| `v2/build/make_v22_page.py` | new | builds `v2/artifacts/v22_accuracy.html` from the run CSVs |

New harness flags:

```text
--configs base,crop,restore,crop_restore    # default: all
--seeds 46,47,48                            # default: 46
--crop / --no-crop                          # per-run override of the config table
--restore / --no-restore
--retry                                     # enable reseed on degenerate output
--warp                                      # compute predicted-warp metrics (free)
--quickvlm                                  # paid, eval-only gross-failure check
--inject-failures                           # offline detector validation, no network
```

New outputs: `v2/runs/ts2/ts2_cv_metrics.csv` gains `config`, `seed`, and the
crop/guard/restore/warp columns; `ts2_vlm.csv` gains `config`, `seed`;
`ts2_guard.csv` and `ts2_crop_tiers.csv` are written alongside.

## 7. Cost estimate

fal `klein_4b_edit` at `est_usd` 0.015 per generation (harness value).

| Item | Count | Unit | Subtotal |
|---|---|---|---|
| `base` generations (39 total, 13 already on disk at seed 46) | 26 | $0.015 | $0.39 |
| `crop` generations | 39 | $0.015 | $0.59 |
| Reseeds (~6% of 39, up to 2 attempts) | ~5 | $0.015 | $0.08 |
| `restore` / `crop_restore` | 0 | derived post-hoc | $0.00 |
| **Generation total** | | | **~$1.06** |
| VLM judging, seed 46, 4 configs x 13 pairs, 3 images each | 52 | ~$0.02 est. | ~$1.04 |
| Quick VLM check, all outputs, 1 image, short prompt | 156 | ~$0.004 est. | ~$0.62 |
| **Judging total** | | | **~$1.66** |
| **Grand total** | | | **~$2.7** |

Generation sits well under the harness's existing `BUDGET_USD = 4.00` ceiling.
The two judging unit prices are estimates, not observed invoice figures — they
should be checked against one run before the full batch. Deterministic scoring,
the warp metric, and detector validation are free and local.

**Nothing in this document has been run.** No paid step executes without explicit
approval.
