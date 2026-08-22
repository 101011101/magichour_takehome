# Edge-Case Index — where every marked failure lives

Assembled 2026-08-22 to support the progression report: base klein → cropping iterations → qx (Qwen extraction) / upgraded crops → composite harness. Every entry names the pair ID, what went wrong (in the source's words where possible), and the exact evidence path. All paths relative to the repo root unless absolute.

Report narrative in one line: the composite idea started as *repair the output after the fact* (`composite_v2ow`), moved to *repair the input before it is cut* (PRE beats AC), and landed as a cost-ordered cascade — **31 perfect / 7 ok / 0 fail at 2.158 gen/request** vs flat BC_klein's 28/6/4 at 2.000.

---

## 0. Master evidence map

| Kind | Where |
|---|---|
| HTML report pages | `v2/artifacts/` — `index.html` is the hub (stale: lists no phase-3 or v223 pages) |
| Annotation CSVs (human verdicts) | repo root: `v221_review_annotations.csv`, `v221_phead_verdicts.csv`, `v221_attention_mod_rankings (1).csv`, `v221_cheapest_usable_picks.csv`, `v223_perfect_tier_picks.csv`, `v223_vlm_eval.csv`, `v223_vlm_pairwise.csv` |
| Metric CSVs | `v2/runs/`: `cv_metrics.csv`, `vlm_judgments.csv`, `v221_review_noop.csv`, `aux_metrics.csv`, `aux_vlm.csv`; `v2/runs/ts2/`: `ts2_vlm.csv`, `ts2_cv_metrics.csv`, `matrix.csv` |
| Result images | `v2/runs/ts2/outputs/`, `v2/runs/combo/`, `v2/runs/v221/`, `v2/runs/crop_screen/`, `v2/runs/phase3/`, `v2/runs/acab/`, `v2/runs/acc/`, `v2/runs/amt/` + `v2/runs/amt/gen/`, `v2/runs/fashn/`, `v2/runs/realism/`, `v2/runs/triage_*/`, `v2/runs/grid_composite_v2ow_*/` |
| Prose of record | `prd/v2/v2.2/RESULTS.md`, `prd/v2/v2.2/EXPERIMENT.md`, `prd/v2/DECISIONS.md`, `prd/v2/ARCHITECTURE.md`, `prd/v2/RESEARCH_LOG.md`, `prd/v2/results_summary/` |
| Figures already made | `prd/v2/v2.2/images/`: `amt_outcomes.png`, `amt_per_reference.png`, `gate_vs_human.png`, `harness_v223.png`, `v221_edge_before_after_beige_coat.png`, `v221_c3_no_face_example.jpg`, `v221_c4_clothes_only_example.jpg` |

---

## 1. Stage: base klein (v2.0 — uncropped `fal-ai/flux-2/klein/4b/distilled/edit`)

Headline number for the report: **20 of 33 sets failed (61%)** in human review — wrong clothes 12, wrong person 11, wrong background 11, duplication 5, no transfer 3, artefacts 6. Source: `prd/v2/v2.2/RESULTS.md` §"What the uncropped baseline got wrong"; raw flags in `v221_review_annotations.csv`; viewer `v2/artifacts/v221_review.html`.

### Worst individual cases

| Case | Failure | Evidence |
|---|---|---|
| **Solid black frame** — `p005xg023` seed 47 | VLM: "Generated result is essentially black/blank" (1/1/1/1/5/1); API reported `"ok": true`, nothing caught it. ~6% flake rate claim | image `v2/runs/triage_klein_4b_edit_p005xg023_s47/result.png`; `run_config.json` same dir; `v2/runs/cv_metrics.csv` row `triage,klein_4b_edit,1,p005xg023` (bg_psnr 1.78, identity_cos empty); `v2/runs/vlm_judgments.csv` same key |
| **`ts2_12` collapse** (man_black_suit + hugh_jackman grey suit, duo_swap) | Only row with 4 defect flags at once: wrong person + wrong clothes + duplication + wrong bg. VLM: "replaces the original studio scene with the garment reference background and leaves the reference person visibly behind the subject" — scene 1, bg_psnr 6.67 dB. "The worst klein output on record" | image `v2/runs/ts2/outputs/klein_4b_edit__ts2_12.png`; `v221_review_annotations.csv` row `ts2_12`; `v2/runs/ts2/ts2_vlm.csv` + `ts2_cv_metrics.csv`; page `v2/artifacts/v20_klein_variant.html` (bottom set, `class='fail'`); base-variant contrast `klein_4b_base_edit__ts2_12.png` (+2.00 fidelity) |
| **`ts2_11` no-transfer** (emma_watson + man_black_suit) | Garment ignored entirely; **VLM scored it 4/5** — the flagship instrument miss. no-op SSIM 0.9319 | image `v2/runs/ts2/outputs/klein_4b_edit__ts2_11.png`; `v221_review_annotations.csv` (`base_nontransfer=1`); `v2/runs/v221_review_noop.csv` |
| **Identity import (failure mode F1)** — worst: `p015 wears p007`, margin **−0.933** (identity vs base 0.032, vs source 0.965) | klein rendered the *source* person's face. Uncropped control: **25 of 83** combos wrong-person vs 3 cropped; mean margin +0.316 vs +0.718 | page `v2/artifacts/v221_duo_transfer.html`; images `v2/runs/combo/p015__wears__p007__base.png`, `dualuse_man_black_suit_studio_nonceleb__wears__dualuse_woman_top_denim_skirt_nonceleb__base.png` (−0.908), `p011__wears__p003__base.png` (−0.850), `p015__wears__p002__base.png` (−0.849) — cropped counterparts in same dir without `__base` |
| **Artefact pairs** `ts2_07`, `ts2_09`, `ts2_10` (lookbook coats) | Leg warping, reference-outfit bleed: "extra reference outfit elements appear". ts2_07 and ts2_10 solved by **no** crop variant | images `v2/runs/ts2/outputs/klein_4b_edit__ts2_{07,09,10}.png`; flags in `v221_review_annotations.csv` |
| **`composite_v2ow` gate failures** — `p006xg006` (0.454), `p010xg001` (0.447) | Face paste-back skipped: `garment_overlaps_head` ×3, retries exhausted; `p013xg004` skipped for `no_face_in_person`. Hoods/high collars defeat the paste-back — 5 of 12 pairs | `v2/runs/grid_composite_v2ow_p006xg006_s149/` and `..._p010xg001_s155/` (`run_config.json` + `result.png`); `v2/build/composite_cells.py` header; superseded per `v2/artifacts/index.html` |

### Instrument failures at this stage (report these — they justify human review)
- `wrong_person = 0.00` across all 38 v2.0 outputs was **the wrong reading**; human review later found 4 of 7 duo pairs failed, 3 missed by both instruments, one scoring above the run mean — `prd/v2/v2.0/RESULTS.md` §"What v2.0 got wrong".
- "`garment_sim` rewards a plausible garment, not the reference garment" — 0.78 + VLM 4/5 on a no-transfer.
- 22 of 165 review outputs were no-ops that score perfectly on identity — `v2/runs/v221_review_noop.csv` (worst: `p009+p014` c2 0.946, `ts2_04` identical across all variants at 0.9199).

Other arms' worst cases (context for the arm choice): FireRed garment 2.00 (`v2/runs/triage_firered_edit_*`); HiDream only arm to substitute the person (`ts2_08`, `ts2_11`, identity_cos 0.05/0.10, `v2/runs/ts2/ts2_cv_metrics.csv`); FASHN hard error "Failed to detect body pose" on `ts2_08` (row absent from ts2 CSVs).

---

## 2. Stage: cropping iterations (v2.2.1 — the bad crops before the good one)

### 2a. Discarded segmenter iterations (crop v0/v1)
Table of record: `prd/v2/DECISIONS.md` §3 and `v2/build/garment_crop.py` header. All quotes verbatim:

| Iteration | Failure |
|---|---|
| Skin-colour heuristic (YCrCb/HSV) | "tore a wedge out of a beige coat on a dark-skinned model, and read a brown plaid overcoat as skin and destroyed it. A bias failure, not a threshold failure" |
| MediaPipe Selfie Multiclass alone | "a staircase by construction" — 256×256 binary upsampled ~6×; soft-alpha fraction exactly 0.00%; jag 0.427 on the beige coat |
| Intersective composition | "notched 6 px blocks out of the peacoat's outline" |
| Category bands (shoulders-to-hips) | "dragged the jeans into the navy peacoat crop" |
| Trimap+matting on subject matte | "white speckles punched ~15 px into a dark navy sleeve" |

Fix: BiRefNet_lite @1024² raw soft alpha + subtractive composition → jag **0.427 → 0.048**. Before/after figure already exists: `prd/v2/v2.2/images/v221_edge_before_after_beige_coat.png`.

### 2b. C1–C4 variant ladder failures (33 sets, human-judged)
Solve rates on the 20 baseline failures: **C3.1 75%, C4 75% (conditional), C2 45%, C3.2 45%**. Note: an earlier "94–96%" figure is **withdrawn** (`prd/v2/DECISIONS.md`) — do not quote it.

| Case | Failure | Evidence |
|---|---|---|
| `dualuse_man_black_suit_studio_nonceleb+dualuse_woman_top_denim_skirt_nonceleb` — **the set no crop arm solved** | C3.1: jagged hair cut read as garment; C3.2 "failed at identity and changed the gender — interpreted the white space as cloth" (reviewer note verbatim in CSV) | `v221_review_annotations.csv` (all `solved_*` = no); outputs `v2/runs/v221/{c31_no_face,c32_keep_hair,...}__*.png`; crops `v2/runs/crop_screen/` |
| `p018+p014` — **white garment on white background** | "white tshirt seems tobe ignroed … same colro as the backgroudn" — sole basis of the later-dropped BG workstream | `v221_review_annotations.csv` note; no-op SSIM 0.9352 in `v2/runs/v221_review_noop.csv` |
| `p018+p016` — skin-tone leak | "skin color mismatch in c2-3"; only C4 solved it | `v221_review_annotations.csv` |
| `p016` — the one hard crop failure | `crop_log.csv` `failed=True`, mask 1.4% of frame; page verdict "FAILED — fell back; do not send" | `v2/runs/crop_screen/crop_log.csv`; page `v2/artifacts/v221_crop_screen.html` |
| `p004`, `p022` — collar over-cut | "head removal takes the collar on several worn references (p004, p022 clearest)" | `v2/runs/crop_screen/p004__c3_no_face.jpg`, `p022__c3_no_face.jpg`; `prd/v2/RESEARCH_LOG.md` 2026-08-15 |
| C4 hand-occlusion holes | "hands crossing a garment punch holes through it" — why C4 wasn't shipped despite 75% | `v2/runs/crop_screen/*__c4_clothes_only.jpg`; example figure `prd/v2/v2.2/images/v221_c4_clothes_only_example.jpg` |
| Furniture in the matte — `p023` stool, `p021` chair | "BiRefNet's subject matte counted a stool … as subject — and therefore so did every crop produced up to that point." Found by eye, never fixed (still a known defect in `prd/v2/ARCHITECTURE.md`) | `v2/artifacts/v221_phase3_acc.html`; crops in `v2/runs/crop_screen/` |

### 2c. The hair-damage cohort (what C3.1 costs)
`hair_over_garment = area(C3.2) − area(C3.1)`. Top of table: **p021 19.53%**, `dualuse_woman_top_denim_skirt_nonceleb` 16.97%, p023 16.92%, zendaya_white_blazer 14.41%, p012 13.98%, p019 13.52%, p028 11.92%, p030 11.46%, scarlett 9.84%, p016 9.75%, p009 7.22%. Key finding: "the damage is open, not enclosed — framing this as an inpainting problem is a category error." Source: `prd/v2/v2.2/RESULTS.md` §"Hair-removal damage"; per-ref fringe images `v2/runs/phase3/{ref}__FRINGE.jpg`, control `{ref}__AC0.jpg`.

### 2d. Failed crop-repair iterations (each is a report-worthy dead end)
- **OC5 over-crop (area target)** — "solved radius inversely related to the defect": p016 (worst fringe 4.69%) solved at 5 px, p023 (0.29%) needed 60 px. `v2/artifacts/v221_phase3_crops.html`; images `v2/runs/phase3/{ref}__OC5.jpg`.
- **Eight head-detection heuristics** — each traded one reference for another: no neck found on p021/p019; face band cost p028 10 pts, p030 17 pts; chin cut swept raised arms (36% of subject); pose ellipse missed p016's scalp (ears 9 px apart); clothes guard protected 19.5% of p019's head. "The signature of a heuristic at its ceiling." `prd/v2/DECISIONS.md` §3.5, `prd/v2/v2.2/EXPERIMENT.md`. Replaced by SegFormer-B2/ATR parser (+5.0 pts vs +0.8–1.2).
- **PCROP** — dropped the body with the garment classes, "the same over-crop C4 had"; page `v2/artifacts/v221_crop_tuning_pcrop.html` is a dead orphan (`prd/v2/TODO.md`).
- **Bald-frame head cut v1** — `head = HAIR + FACE` finds no hair on a bald frame: removal fell 17.6% → 8.6%, "the cranium survived the cut."
- **PRE (repair-before-crop) — the fix that worked**: p021 head-cut 19.5% → **0.0%** (PRE2 klein bald / PRE3 qwen bald); counter-case **p019** where PRE3 made fringe worse (0.12% → 1.21%). Page `v2/artifacts/v221_phase3_crops.html`; numbers `v2/runs/phase3/_pre_notes.json`; raw-frame guard images `{ref}__PRE{1,2,3}raw.jpg`.

### 2e. PHEAD verdicts (the upgraded deterministic crop)
`v221_phead_verdicts.csv` — 38 rows: 24 perfect / 6 ok / **8 fail**. Fails: `dualuse_man_black_suit...+...woman_top_denim_skirt`, `p018+p016`, `HD_p021`, `HD_p023`, `HD_p021+dualuse_hugh_jackman_grey_suit_outdoor`, `HD_p021+p009`, `HD_p023+p019`, `HD_dualuse_zendaya_white_blazer_skirt+p017`. **5 of 6 high-damage fails involve p021 or p023** — the two worst-hair references and the two with furniture in the matte. Page `v2/artifacts/v221_crop_tuning_phead.html`; outputs `v2/runs/amt/gen/{set}__PHEAD.jpg`.

---

## 3. Stage: qx (Qwen extraction) and who needs the upgraded crop

qx = `QX_qwen_p1`: Qwen-Image-Edit-2511 *regenerates* the garment on white (AC-A). Built-in risk, verbatim from `v2/build/extraction_drift.py`: "it can return a beautiful crop of the wrong clothes" — and both instruments reward that.

### 3a. Extraction drift (qx's own edge cases)
Drift table of record: `prd/v2/v2.2/EXPERIMENT.md` §AC-A; per-reference verdicts rendered in `v2/artifacts/v221_phase3_acab.html`; images `v2/runs/acab/{ref}__QX_qwen_p1.jpg` vs `{ref}__CTRL.jpg`.
- "Every arm drifts on almost every reference." Qwen arms return ~half the control's edge detail; hue drift 21–30° on every arm. "No extraction arm currently returns the same garment."
- Worst recolour: **p009 hue 88°**. Worst texture loss: **p030 pattern ×0.23**. Clean: p019, p028 only.
- **Qwen-Image-Edit-Plus dropped** (ΔL to 99, hue 67.6°); **ghost-mannequin prompt p3** read as "make it pale and simple" (ΔL 48–99).
- Deliberate trap for the report: the reviewer *preferred* the qwen crops by eye while they lost half the pattern — "cleanest-looking" and "most faithful" pull apart.

### 3b. Who needed the upgraded crop (the AMT split — 38 sets × 10 arms)
Data: `v221_attention_mod_rankings (1).csv`; page `v2/artifacts/v221_attention_mod.html`; prose `prd/v2/v2.2/RESULTS.md` §AMT. Best/failed rates, low-damage → HIGH-damage:

| arm | best | failed |
|---|---|---|
| control (basic C3.1) | 75% → **28%** | 10% → **61%** |
| BC_klein (upgraded) | 80% → 67% | 0% → 11% |
| QX_qwen_p1 (qx) | 55% → 61% | **15% → 0%** |
| BALD_raw (no crop) | 15% → 22% | 85% → 61% |

- **Fine with the basic crop**: the 20 low-damage sets — control cut in only 2 of 20. qx is at its *worst* here; its only three cut/fail sets are all low-damage: **`p017+p002`** (the single human `fail` for qx in the whole 38-set eval — VLM said CLEAN), **`p026+p004`**, **`p009+p014`**.
- **Needed the upgrade**: the 18 `HD_` sets (garments p021, p023, zendaya, p019, p028, p009 × 3 people each). Control collapses; every bald-based arm holds; **qx never fails a high-damage set (0/18)**.
- Failure is a property of the **garment**, not the pairing: p021 CUT×3, p028 CUT×3, p009 CUT×3; but non-monotonic in damage % (p009 at 7.2% fails, zendaya at 14.4% is fine) — the "trigger on damage number" rule is dead.
- **Test-set defect to disclose**: the first 20-pair AMT set held only 5 of 11 damage refs and "p021 — the worst at 19.53% — was never tested at all", which flattered the baseline. Mean-rank and win-count statistics are **withdrawn** (top band is a tie).

### 3c. qx as the escalation arm
qx: 20 perfect / 17 ok / **1 fail** — lowest ceiling, highest floor → last in the cascade "to route around AI artefacts, not to produce the best frame." BC_klein's only two failures (`HD_p023`, `HD_p023+p019`) are both rescued by qx. Evidence: `v223_perfect_tier_picks.csv`; `prd/v2/ARCHITECTURE.md` §2; chart code `v2/build/harness_chart.py`.

---

## 4. Stage: composite harness (v2.2.3 — shipped) and what remains

Shipped shape (`v2/pipeline/harness.py`): hair router (`hair_over_garment ≥ 0.14` → BC_klein, else PHEAD) → input comparison (noop, **identity < 0.90**, degenerate) → VLM gate (tryon≠PERFECT, garment==FAIL) → escalate to QX → optional SeedVR2 ×2 noise 0. Result over 38 sets: **2.158 gen/request, 31 perfect / 7 ok / 0 fail** vs flat BC_klein 2.000 for 28/6/4. Per-set record: `v2/runs/realism/_realism.json`.

**Corrected 2026-08-22:** the earlier shipped rule omitted the identity check and shipped 1 failure. See the table below.

### Remaining edge cases (the honest end of the report)

| Case | Status | Evidence |
|---|---|---|
| **`HD_p028+dualuse_navy_peacoat_onmodel`** — **now fixed**, was the 1 shipped fail | Router chose PHEAD at hair 11.9% (just under the 14% cut) and the VLM gate did not fire — **all five prompts passed it**, including `transfer`, which saw the person photo. The person was substituted entirely: input is a man with short auburn hair, output a woman with long dark hair. `chk_identity = 0.755` caught it; the rule did not consult identity. **Adding `identity < 0.90` closes it.** Second near-miss `p018+p016` at 9.7% hair | `v2/runs/realism/_realism.json`, `v223_vlm_eval.csv`, `v223_perfect_tier_picks.csv` |
| 4 sets with **no perfect arm**: `dualuse_lp_beige_long_coat...+scarlett`, `dualuse_lp_floral_kimono_set+p008`, `HD_p019+p009` (all ok/ok/ok), `HD_p023+p019` (fail/fail/ok — only qx tolerable) | Ceiling of the current cascade | `v223_perfect_tier_picks.csv` |
| `dualuse_man_black_suit...+...woman_top_denim_skirt` | The historically unsolvable set still lands non-perfect | `v2/runs/realism/_realism.json` |
| **Deterministic gate is a coin flip as a SCORER** — AUC 0.506; background sub-check inverted (0.379). ~~identity "100% precise and useless"~~ **withdrawn 2026-08-22**: that was measured at threshold 0.5; at 0.90 identity catches the one shipped failure | No deterministic *score* ships; `noop` and `identity` ship as escalation triggers | `v2/artifacts/v223_gate_simulation.html`; `v2/runs/amt/_gate.json`; figure `prd/v2/v2.2/images/gate_vs_human.png`; known hole stated in `v2/build/failure_gate.py` header |
| **VLM `artefact` prompt never fired** — CLEAN on all 114 incl. every fail: "our failures are not artefacts — they are competent photographs of the wrong thing." Only the `garment` prompt (sees the reference) works: 70.2%, 53% fail-catch | Gate is VLM `garment` + `tryon` **plus** noop and identity | `v2/artifacts/v223_vlm_eval.html`; `v223_vlm_eval.csv` |
| **Pairwise VLM dropped** — 34% self-consistency under image swap (reads position, not content); picked the already-failed arm 2 of 5 escalations | | `v223_vlm_pairwise.csv` |
| Furniture in subject matte (p021/p023) | Known defect, unfixed | `prd/v2/ARCHITECTURE.md` §known defects |
| Parity gap — every number is a fal number; nothing reproduced on downloaded weights | Standing program risk | `prd/v2/DECISIONS.md`; `v2/artifacts/v20_coverage.html`; `v2/artifacts/index.html` |
| v2.1 side-finding: Z-Image destroys identity even on real photos (AuraFace 0.72; id_preserve down to 0.20 at s035 on p003xg011) — `artifact_fix` = 3.00 in 14/14 batches, "no global realism pass has ever repaired an artifact" | Founding premise of v2.3 (not yet run) | `v2/runs/aux_metrics.csv`, `v2/runs/aux_vlm.csv`; `prd/v2/v2.1/RESULTS.md` |

---

## 5. Suggested before/after picks for the report (progression money shots)

1. **Attention deficit solved by cropping** — `ts2_12`: base klein disaster (4 simultaneous defects) → solved by every crop variant. `v2/runs/ts2/outputs/klein_4b_edit__ts2_12.png` vs `v2/runs/v221/c31_no_face__ts2_12.png`.
2. **Identity import solved by cropping** — `p015 wears p007` margin −0.933 → cropped counterpart positive. `v2/runs/combo/p015__wears__p007__base.png` vs `v2/runs/combo/p015__wears__p007.png` (page `v221_duo_transfer.html` renders both).
3. **Crop edge quality** — beige coat jag 0.427 → 0.048: ready-made figure `prd/v2/v2.2/images/v221_edge_before_after_beige_coat.png`.
4. **Hair damage solved by PRE/bald** — p021: head cut 19.5% + fringe 2.66% → 0.0/0.00. `v2/runs/phase3/p021__AC0.jpg` → `p021__PRE2.jpg` (+ `__FRINGE.jpg` to show the defect).
5. **Basic crop vs upgraded on a hard garment** — `HD_p023`: control/PHEAD fail (gate 0.148 on BC_klein) → **QX rescue perfect**. `v2/runs/amt/gen/HD_p023__{control,PHEAD,BC_klein,QX_qwen_p1}.jpg`.
6. **qx drift as the counter-example** — p030 pattern ×0.23 or p009 hue 88°: `v2/runs/acab/p030__QX_qwen_p1.jpg` vs `p030__CTRL.jpg` — why qx is the escalation, not the default.
7. **The residual** — `HD_p028+dualuse_navy_peacoat_onmodel` shipped fail: `v2/runs/realism/HD_p028+dualuse_navy_peacoat_onmodel__after.png`; and `p018+p014` white-on-white, still only solved by C4.
8. **Final composite** — figure `prd/v2/v2.2/images/harness_v223.png` + the 30/7/1 vs 28/6/4 table from `prd/v2/ARCHITECTURE.md` §2.

---

## 6. Numbers to avoid quoting (withdrawn or wrong in-source)

- "94–96% solve rate across all four crop variants" — withdrawn (blank cells miscounted); correct is 75% for C3.1.
- AMT mean rank and win-count — withdrawn (top band is a tie); use tied-first and failure rates.
- PRE "garment lost 19.5% → 0.02%" metric — withdrawn by construction (bald frames score ~0 regardless).
- "nothing beats what already ships" (control) — withdrawn after the HD cohort was added.
- klein triage mean: `v20_triage_v1set.html` shows 0.584 (dragged by the black frame) while `v2/NOTES.md` and `prd/v2/v2.0/RESULTS.md` quote 0.778 — reconcile before quoting either.
- `wrong_person = 0.00` from v2.0 metrics — the reading was wrong; cite the human census instead.
