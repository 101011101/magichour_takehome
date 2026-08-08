# V1 — the $10 Pilot (what is actually being built)

Version doc for the build in flight. Scope decisions live here; [OUTLINE.md](OUTLINE.md)
holds the full program; `execution_conventions.md` holds where truth lives and how
docs work.

## Scope of V1

- **All fal arms, one notebook, $10 ceiling.** Triage (arms × 4 pairs × 1 gen) →
  grid (survivors × 12 pairs × 1 gen) → reserve (best-of-2 on top 2).
- **Judging is HUMAN in V1.** Ray scores outputs by eye in a dedicated, clearly
  marked notebook section (§8) that writes `judgments.csv`. The VLM-judge code
  ships in V1 (§9) but is **written-not-run** — judge model gets picked later
  (candidates below), flipped on by setting one config value.
- **Deterministic CV metrics (face cosine, pose diff, PSNR) are deferred** to a
  later version — stubbed section, not blocking the pilot.
- **Tuning/Key deferred** (Phase 3, per OUTLINE.md). Interim Key = leaderboard
  winner at defaults.

## Arms in V1

All verified against live fal.ai /api schema pages (2026-08-08, scout agent):

| Arm | Endpoint | ~$/img | Gotcha |
|---|---|---|---|
| Qwen 2511 (baseline) | `fal-ai/qwen-image-edit-2511` | 0.03/MP | — |
| FLUX.2 klein 4B edit | `fal-ai/flux-2/klein/4b/distilled/edit` | 0.015 | max 4 ref images |
| FLUX VTO **v1** | `fal-ai/flux-pro/v1/vto` | 0.048 | **v2 is NOT on fal** (BFL direct API only); person ≤1MP / garment ≤0.5MP recommended — harness auto-downscales |
| FASHN v1.6 (quality) | `fal-ai/fashn/tryon/v1.6` | 0.075 | no prompt param; fixed 864×1296 output |
| Qwen-Image-3 Edit | `alibaba/qwen-image-3/edit` | 0.04 | **prompt-expansion ON by default** — harness disables it for fairness |
| klein try-on LoRA | `fal-ai/flux-2-lora-gallery/virtual-tryon` | ~0.04 (per-second billing) | prompt needs `TRYON` trigger word |
| Seedream 5.0 Lite | `fal-ai/bytedance/seedream/v5/lite/edit` | 0.035 | **no seed input** — this arm is not reproducible |
| ~~Ideogram Character V3~~ | — | — | ❌ cut (single content slot, verified in NOTES.md) |
| ~~Krea 2~~ | — | — | ❌ cut (single content slot, verified in NOTES.md) |

## Notebook section map (the deliverable's shape)

| § | Cell(s) | Paid? | Who runs it |
|---|---|---|---|
| 0 | Title, version, budget tracker | – | auto |
| 1 | Settings — knobs: enabled arms, pair set, seed, run flags | – | Ray edits |
| 2 | Setup — pip, `FAL_KEY` from Colab Secrets, clone repo (test set) | – | Run all |
| 3 | Test set — load `pairs.csv`, select triage-4 / grid-12 subsets | – | Run all |
| 4 | Preflight — key check, arms listed, **cost estimate printout** | – | Run all |
| 5 | Harness — arm registry, `try_on()`, upload helper, run packages | – | Run all |
| 6 | **Triage run** (`RUN_TRIAGE=True`) then **Grid run** (`RUN_GRID=True`) | 💰 | Ray flips flag |
| 7 | Comparison grids — thumbnails, rows=pairs × cols=arms | – | Run all |
| **8** | **🔴 HUMAN JUDGING — Ray's station.** Blank scoring sheet auto-generated; score 1–5 × 4 criteria per output; saves `judgments.csv` | – | **Ray, by eye** |
| 9 | VLM judge — full code, `JUDGE_MODEL = None` (off). Schema-validated, self-correct retries | (💰 later) | nobody in V1 |
| 10 | Leaderboard — aggregates human (and later VLM) scores vs baseline | – | Run all |
| 11 | Verdict card + actual spend vs $10 | – | Run all |

## Judge-model candidates (pick later, one-line config change)

| Candidate | Why | Rough cost / 84 judgments |
|---|---|---|
| **Gemini 2.5 Flash-Lite** (recommended) | Cheapest capable vision model; generous free tier may make judging $0 | ~$0.10–0.30 |
| Claude Haiku 4.5 | Strong vision, cheap, easy JSON compliance | ~$0.50–1.00 |
| GPT-5 mini | Comparable; third opinion if judges disagree | ~$0.50–1.00 |

## Conventions honored (from the references)

Per-run packages (`run_config.json` + `metrics.json` + result PNG) to Drive;
seeds fixed per pair; `globals().get` knob fallbacks; thumbnails only in cell
outputs (MCP stall gotcha); paid cells gated behind explicit flags so "Run all"
never spends money by accident.
