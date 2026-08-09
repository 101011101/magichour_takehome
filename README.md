# Virtual Try-On — Model Comparison Pilot

[![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/101011101/magichour_takehome/blob/main/virtual_tryon.ipynb)

Person image + garment image → the person wearing that garment. Seven hosted
fal.ai arms compared against Magic Hour's **Qwen 2511** baseline under a $10
pilot budget, judged by three independent systems. The eval harness is the
product; the shipped implementation is one row in its results table.

## Setup

1. Clone the repo (or open the badge above — the notebook clones it for the test set).
2. Provide keys: `FAL_KEY` (generation) and `OPENAI_API_KEY` (VLM judge only) —
   in a local `.env` at the repo root, or as Colab Secrets.
3. **Run all** — every free cell executes: harness, test-set load, preflight cost
   estimate, deterministic judges, leaderboards over any cached results.
4. To spend, flip flags in §1 one stage at a time: `RUN_TRIAGE` (~$1.30) →
   `RUN_GRID` → `RUN_RESERVE` → `RUN_BENCHMARK` → `RUN_CASCADE`, plus
   `RUN_VLM_JUDGE` for the paid judge.

Paid stages never execute on "Run all" — every spending cell is gated behind an
explicit flag, and completed runs are cached as run packages so re-runs never
re-spend.

## Report

**Full report: [FINAL_REPORT.pdf](artifacts/FINAL_REPORT.pdf)** (renders on
GitHub — boards, narrative, and the complete three-way side-by-side gallery) ·
interactive version: [final_report_v2.html](artifacts/final_report_v2.html)
(sortable tables, lightbox; open locally after cloning).

**Verdict: the baseline (qwen_2511) was beaten by every judging system on
unseen data.** On the 18-pair held-out benchmark it finished last on the
deterministic composite and below both shipped models on the VLM board (human
review concurred).

**Headline finding:** on the 18 held-out pairs the shipped **cascade —
`seedream5_lite` edit → `qwen_image3` realism refine** (notebook §12b) —
**ranked #1 on the blind gpt-5.5 VLM board** (4.22 overall), taking
best-in-class on clean (4.06) and realism (4.11) and tied-best on garment
(4.00, shared with its stage-1 parent). It also edged its parent
`seedream5_lite` on the deterministic composite (0.522 vs 0.507) — the shipped
composite validated against its parent on data no selection decision ever
touched. `seedream5_lite` alone (§12a) remains the single-model option. The
cascade was originally selected by human review corroborated by the frontier
VLM on the grid stage, where it posted the joint-best garment score (4.00).

One honest tension stays on record: the **deterministic holdout board is still
topped by the pixel-compositing arms** — flux_vto_v1 (0.642) and fashn_v16
(0.632) — because pasting original pixels back maximizes preservation metrics,
while re-rendering trades pixel preservation for perceptual quality those
metrics cannot see. fashn_v16 remains the identity/background-preservation
champion (identity_cos 0.974, bg_psnr 29.2 dB) and the recommendation when
strict original-photo preservation is the requirement.

Scoring definitions used in every table below:

- **Deterministic composite** — each metric normalized to [0,1] against fixed
  absolute anchors, then weighted-averaged with `garment_sim` at weight 2 and
  the rest at 1: `garment_sim` 0.0→0.35, `identity_cos` 0.35→0.80,
  `pose_err` inverted 0.25→0.0, `bg_psnr` 12→32 dB.
- **VLM overall** — mean of six 1–5 rubric criteria: garment, identity, scene,
  clean, hands, realism. Editing axis = mean(garment, identity, scene);
  realism axis = mean(clean, hands, realism).

### Held-out benchmark — 18 unseen pairs (the reported numbers)

Deterministic composite (n = 18 per arm):

| Arm | Composite | garment_sim | identity_cos | pose_err | bg_psnr (dB) |
|---|---|---|---|---|---|
| flux_vto_v1 | **0.642** | 0.108 | 0.875 | 0.058 | 28.6 |
| fashn_v16 | 0.632 | 0.097 | 0.974 | 0.046 | 29.2 |
| seedream_qwen_refine (cascade) | 0.522 | 0.129 | 0.730 | 0.104 | 20.4 |
| seedream5_lite | 0.507 | 0.106 | 0.754 | 0.101 | 21.0 |
| qwen_2511 (baseline) | 0.385 | 0.077 | 0.855 | 0.241 | 16.2 |

VLM judge, gpt-5.5 blind (n = 18 per arm):

| Arm | Overall | Garment | Identity | Scene | Clean | Hands | Realism |
|---|---|---|---|---|---|---|---|
| seedream_qwen_refine (cascade) | **4.22** | **4.00** | 4.56 | 4.67 | **4.06** | 3.94 | **4.11** |
| seedream5_lite | 4.13 | **4.00** | 4.44 | 4.50 | 3.94 | 3.83 | 4.06 |
| flux_vto_v1 | 4.12 | 3.17 | 4.72 | 4.83 | 3.94 | 4.00 | 4.06 |
| qwen_2511 (baseline) | 3.81 | 3.39 | 3.94 | 4.33 | 3.72 | 3.78 | 3.72 |
| fashn_v16 | 3.60 | 2.72 | 4.44 | 4.50 | 3.33 | 3.17 | 3.44 |

### Grid stage — 12 pairs, survivors + baselines

Deterministic composite (n = 24 for arms with best-of-2 seeds; 12 for
klein_4b_edit, qwen_2511, the cascade, and magic_hour_api). Composites are
computed per output (anchored normalization, garment ×2) and averaged per arm:

| Arm | Composite | garment_sim | identity_cos | pose_err | bg_psnr (dB) |
|---|---|---|---|---|---|
| flux_vto_v1 | **0.677** | 0.122 | 0.872 | 0.025 | 28.6 |
| fashn_v16 | 0.666 | 0.127 | 0.980 | 0.034 | 28.5 |
| klein_4b_edit | 0.631 | 0.105 | 0.908 | 0.029 | 25.5 |
| seedream5_lite | 0.569 | 0.200 | 0.686 | 0.067 | 20.7 |
| magic_hour_api (website) | 0.557 | 0.145 | 0.647 | 0.034 | 25.9 |
| seedream_qwen_refine (cascade) | 0.507 | 0.142 | 0.660 | 0.073 | 20.6 |
| qwen_2511 (baseline) | 0.404 | 0.130 | 0.814 | 0.188 | 15.0 |

VLM judge, gpt-5.5 blind (same n as above):

| Arm | Overall | Garment | Identity | Scene | Clean | Hands | Realism | Editing axis | Realism axis |
|---|---|---|---|---|---|---|---|---|---|
| flux_vto_v1 | **4.18** | 3.25 | 4.79 | 4.96 | 4.00 | 4.04 | 4.04 | 4.33 | 4.03 |
| seedream_qwen_refine (cascade) | 4.14 | **4.00** | 4.42 | 4.50 | 4.00 | 3.92 | 4.00 | 4.31 | 3.97 |
| klein_4b_edit | 4.13 | 3.50 | 4.50 | 4.83 | 4.00 | 3.83 | 4.08 | 4.28 | 3.97 |
| seedream5_lite | 4.08 | **4.00** | 4.33 | 4.46 | 3.96 | 3.71 | 4.04 | 4.26 | 3.90 |
| magic_hour_api (website) | 3.92 | 3.25 | 4.17 | 4.67 | 3.83 | 3.75 | 3.83 | 4.03 | 3.81 |
| fashn_v16 | 3.89 | 3.50 | 4.54 | 4.75 | 3.46 | 3.42 | 3.67 | 4.26 | 3.51 |
| qwen_2511 (baseline) | 3.83 | 3.42 | 4.08 | 4.33 | 3.67 | 3.75 | 3.75 | 3.94 | 3.72 |

### Website baseline (Magic Hour production API)

The actual production output was added as a grid arm: `magic_hour_api`,
generated via the Magic Hour AI Clothes Changer API (`v1/ai_clothes_changer`)
on the same 12 grid pairs. It scored **0.557 deterministic / 3.92 VLM** —
meaningfully above raw qwen_2511 (0.404 / 3.83), confirming the website
wrapper adds real value over the raw model. Against our implementations: both
shipped models beat it on the VLM board (cascade 4.14, seedream5_lite 4.08 vs
3.92); on the deterministic composite seedream5_lite (0.569) is above it while
the cascade (0.507) sits below — the same pixel-preservation tension as
elsewhere (the website output keeps the background nearly intact,
bg_psnr 25.9 dB). Weak spots per the judges: the **lowest identity cosine of
any grid arm** (0.647 mean — a person-replacement occurred on one pair,
cosine 0.18) and garment accuracy of 3.25 on the VLM. Provenance: outputs
downloaded straight from the Magic Hour API, unmodified, native 384x576 —
see [`gallery/`](gallery/) and [`gallery/README.md`](gallery/README.md).

### Evidence

**Final report: [`artifacts/FINAL_REPORT.pdf`](artifacts/FINAL_REPORT.pdf)** —
renders directly on GitHub: approach narrative, all per-stage boards, and the
three-way side-by-side gallery (baseline vs seedream vs cascade) for every
pair. The same report as an interactive page (sortable tables, image lightbox,
stage tabs) is [`artifacts/final_report_v2.html`](artifacts/final_report_v2.html)
— GitHub shows HTML as source, so open it locally after cloning.

The rest of the committed evidence pack under [`artifacts/`](artifacts/):
`cv_metrics.csv`, `vlm_judgments.csv`, and the three stage grids
(`grid_triage.png`, `grid_main.png`, `grid_holdout.png`). The full working
evidence — every run package plus `runs/report.html` — lives in `runs/`,
which is gitignored; all reports are regenerated by re-running the free cells
over the cached run packages.

### Next steps / productionization

- **CLIP-embedding garment metric** to replace the color-histogram proxy —
  `garment_sim` is structure-blind today; this is the Phase-2 fix.
- **Dev/held-out split is already wired** for any future tuning: tune prompts,
  steps, or preprocessing on the grid pairs, report only on the 18 holdout
  pairs.
- **Best-of-N serving** — generate N candidates per request and let the
  deterministic scorer auto-pick the winner; cost scales linearly, quality
  doesn't, so N is a tunable dial.
- **Confirm the website's exact qwen_2511 settings** for a fully fair baseline
  (the pilot ran it at sane defaults).
- **Cost/latency**: the cascade is two API calls (~$0.08/run) vs ~$0.04 for
  single-model seedream5_lite — the quality margin should be weighed against
  the 2x cost and latency per request.

## Approach

Sources: [`NOTES.md`](NOTES.md) (final deliverable, frozen 2026-08-08),
[`prd/V1_PILOT.md`](prd/V1_PILOT.md), [`prd/OUTLINE.md`](prd/OUTLINE.md),
[`execution_conventions.md`](execution_conventions.md).

### Staged, budget-gated pipeline

| Stage | What runs | Gate |
|---|---|---|
| Triage | 7 arms × 4 pairs | `RUN_TRIAGE` |
| Elimination | automatic top-50% by deterministic composite, + baseline always advances (§6b) | free, reproducible on re-run |
| Grid | 5 arms × 12 pairs, best-of-2 seeds on the top arms for seed stability | `RUN_GRID` / `RUN_RESERVE` |
| Held-out benchmark | 18 pairs never touched by any selection decision | `RUN_BENCHMARK` |

The held-out split exists so the reported numbers cannot be an artifact of
tuning: no selection decision ever saw those 18 pairs.

### Three judging layers

1. **Deterministic CV harness** (free, local CPU) — garment color-histogram
   similarity, ArcFace identity cosine, MediaPipe pose keypoint diff,
   background PSNR outside the garment region. The pixel-preservation lens and
   the *elimination authority*: triage survival is decided here so a
   top-to-bottom re-run reproduces the same eliminations.
2. **Blind VLM judge** (gpt-5.5) — six-criterion rubric (garment, identity,
   scene, clean, hands, realism), arm identity hidden, responses forced into a
   JSON schema with validation and self-correcting retries so one malformed
   judgment cannot corrupt the leaderboard.
3. **Human review** — the supervising tiebreaker. §10 flags rank disagreements
   between the two automated judges (|Δrank| ≥ 2) for human eyes; the final
   model selection was made here, with the VLM as corroboration.

### Complementarity ("checkbox") axes → the cascade

The VLM criteria decompose into an **editing axis** (garment, identity, scene)
and a **realism axis** (clean, hands, realism). Arms strong on one axis and
weak on the other are cascade candidates: pair the best transfer specialist
with the best realism refiner. That derivation surfaced
`seedream5_lite → qwen_image3 refine`, which was then actually run and judged
(§6f) — joint-best garment score on the grid, and ultimately #1 on the VLM
board of the held-out benchmark. The symmetric suggestion (fashn → klein) was
never tested and deliberately does not ship.

### Key methodological decisions

- **`garment_sim` carries double weight** — garment transfer is the core
  product objective; without it, "change nothing" scores perfectly.
- **Fixed absolute anchors, not min–max across arms** — min–max over-rewarded
  compositing arms whose identity/background max out by construction (exact
  pixel paste) and crushed legitimate full re-renderers.
- **Identity saturates at 0.80 cosine** — beyond the ArcFace same-person
  region, extra cosine is pixel-copying credit, not identity fidelity.
- **Idempotent run packages** — every generation persists as
  `result.png` + `run_config.json`; completed work is reloaded (§5b), so
  re-runs never re-spend.
- **Paid cells behind explicit flags** — "Run all" is always free.

### Exclusions (documented, verified)

**Krea 2** and **Ideogram** — both named in the original prompt — physically
cannot do try-on: every endpoint of each takes exactly **one content image
slot** (verified against Krea's OpenAPI spec and all five Ideogram fal
endpoints plus the native API, including empirical probes). You cannot feed
them a person *and* a garment. Details and the weights-level Krea escape hatch
(a community LoRA, out of scope for v1) are in [`NOTES.md`](NOTES.md).

Known caveats: seedream accepts no seed input (outputs are stochastic);
`garment_sim` is a color-histogram proxy, structure-blind — the VLM covers
structure, and a CLIP-embedding upgrade is the Phase-2 fix.

## Schema

| Path | What / why |
|---|---|
| `virtual_tryon.ipynb` | The deliverable. §1 settings/knobs · §2 setup · §3 test set · §4 preflight + cost estimate · §5 harness (arm registry, `try_on()`, run packages; §5b cache reload; §5c deterministic judges) · §6 paid runs (a triage, b survivor selection, c grid, d best-of-2 reserve, e held-out benchmark, f cascade) · §7 comparison grids · §8 human judging station · §9 VLM judge · §10 leaderboards + judge agreement · §11 verdict card + spend · §12 final implementation and the Key (a single-model, b cascade, c `compare_vs_baseline()`). |
| `test_set/` | Curated evaluation data: 30 people + 30 garments with stratified quotas (skin tone, body size, gender, hand-over-torso poses). `pairs.csv` = 30 curated 1:1 pairs with difficulty tiers (4 easy / 14 medium / 12 hard) and per-pair rationale; `manifest.csv` = tags, sources, deviations. |
| `prd/V1_PILOT.md` | Version doc for this build: arms, prices, gotchas, elimination and scoring decisions, notebook section map. |
| `prd/OUTLINE.md` | The full program the pilot is a slice of: phases, budget math, inspiration ledger from the reference notebooks. |
| `NOTES.md` | Working notes and the frozen final-deliverable summary; the Krea 2 / Ideogram exclusion evidence. |
| `TESTSET_PLAN.md` | Stratification design the test set was curated against (scaled from 120+120 to 30+30 under the $10 budget). |
| `TASK.md` | The original take-home prompt and context. |
| `execution_conventions.md` | Where truth lives: Colab/MCP workflow, doc conventions, model-access table, open items. |
| `references/` | The two house-style reference notebooks (Krea2 identity edit, MagicHourOptimize) + `REFERENCES.md` synthesizing which patterns were adopted. |
| `research/` | Pre-build research: model scout shortlist (endpoint verification) and image-accuracy research. |
| `gallery/` | 12-pair 4-way comparison set, one row of six images per grid pair: person, garment, raw qwen_2511, Magic Hour website API output (raw PNG, 384x576), seedream, cascade — the visual side of the website-baseline comparison; see its README for the filename key. |
| `artifacts/` | Committed evidence pack: `cv_metrics.csv`, `vlm_judgments.csv`, three stage grid PNGs, `final_report_v2.html` — the numbers behind the Report section, reviewable without re-running anything. |
| `runs/` (gitignored) | Evidence outputs, regenerable. `cv_metrics.csv` = deterministic metrics per output; `vlm_judgments.csv` = VLM rubric scores + notes per output; `<stage>_<arm>_<pair>_s<seed>/` run packages (`result.png` + `run_config.json`) = the idempotency cache; `report.html` = every output with scores; `final_report.html` / `final_report_v2.html` = the final evidence pack; `executed_*.ipynb` = executed notebook snapshots per stage; `grid_*.png` = comparison grids. |
