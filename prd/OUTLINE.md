# PRD — Virtual Try-On Colab (Magic Hour take-home)

**Goal (from [TASK.md](../TASK.md)):** a Colab that takes a person image + outfit
image → person wearing that outfit, and demonstrably beats the website's
Qwen 2511 on a shared test set.

**Shape of the build:** model harness → test data → eval harness → evaluate →
tune → freeze the key → final deliverable. Mirrors the internal Krea2 notebook's
structure (knobs → run → quality gates → run package) — see
[references/REFERENCES.md](../references/REFERENCES.md).

---

## 1 · Model harness

A single switchable interface so every model runs identically:

```
try_on(person_img, outfit_img, model_cfg) -> result_img
```

### Phase 1 — the 7-arm all-fal harness

One API key, one client (`fal_client.subscribe(endpoint, {image_urls/person+garment, seed, ...})`),
~zero marginal integration cost per arm — the whole harness is one wrapper
function plus a per-arm config dict.

| # | Arm | Role |
|---|---|---|
| 1 | **Qwen 2511** | The baseline; mandatory |
| 2 | **FLUX VTO v2** | Default dedicated try-on arm |
| 3 | **FASHN v1.6** (quality mode) | Pattern/logo specialist |
| 4 | **FLUX.2 klein 9B base/edit** | General editor that beats Qwen on VTEdit-Bench |
| 5 | **Qwen-Image-3 Edit** | The baseline's own successor — cheapest "did the family already beat itself?" experiment |
| 6 | **klein try-on LoRA** | Near-free variant of #4 |
| 7 | **Seedream 5.0 Lite** | Best-benchmarked hosted general editor |

**Budget: $10 pilot first.** All 7 arms, 12 pairs, best-of-1 (~84 images):
smoke tests $0.80 → main grid $3.80 → VLM judging $1.50 → failure buffer $0.90 →
$3.00 reserve for best-of-2 on the top 2 arms. Output: a directional leaderboard
that picks the top 2 arms and reveals real per-arm pricing. Full grid
(best-of-4 × 100 pairs ≈ **$120–180**, Ray's estimate at ~4–6¢/image over 2,800
images) is deferred until the pilot says which arms deserve it.

**Excluded — documented:** Krea 2 (API takes one content image; physically
can't do try-on — see NOTES.md). Ideogram (text-to-image as used in the
reference; poor fit — justify exclusion in the memo).

### Phase 2 — one non-fal integration: GPT Image 2

The only arm worth a separate key: ~10 lines via the `openai` SDK, and
strategically load-bearing — arena's #1 editor and the direct answer to
"doesn't ChatGPT already do this?"

Harness details (patterns from the Krea2 reference): config-dict per arm,
per-run output package (`result.png` + `run_config.json` + `metrics.json`).

## 2 · Test data

- **N ≈ 10–16 person/outfit pairs**, fixed, versioned in the repo/Drive.
- Mix: flat-lay garments + on-model garments; simple + busy backgrounds;
  varied poses, body types, skin tones; at least 2 garments with logos/text
  (the classic failure case).
- **Split: ~1/3 dev (for tuning) / ~2/3 held-out (for reported numbers).**
  Never tune on held-out.

## 3 · Evaluation harness  *(built BEFORE tuning — evaluation first, guardrails second)*

Deterministic metrics (extends Magic Hour's own `identity_cosine` /
`body_preserve_psnr` gate pattern):

| Metric | Checks | Method |
|---|---|---|
| **Garment fidelity** ⭐ | The outfit actually transferred (print/color/cut) | Embedding similarity, garment region ↔ reference garment; the one metric the user's draft was missing — without it "change nothing" scores perfectly |
| Identity preservation | Same face/person | Face-embedding cosine (input vs output) |
| Skeletal consistency | Same pose | Pose keypoint diff (before vs after) |
| Background/scene drift | Untouched pixels stayed untouched | PSNR/diff outside garment region |
| AI marks / artifacts | Hands, seams, plastic skin, garble | VLM judge (deterministic CV is weak here) + resolution/EXIF sanity checks |

Plus: side-by-side grids per test pair, and a blind VLM-judge rubric score
(1–5 per criterion) as the perceptual complement.

## 4 · Evaluate (round 1, default settings)

All models × all pairs at sane defaults → metric table + grids.
Output: leaderboard vs the Qwen 2511 baseline; identify each model's failure
modes (this drives what to tune).

## 5 · Tune → the Key  *(DEFERRED — Phase 3, after the harness + eval ship)*

Phases 1–2 run all arms at sane defaults. Tuning is a follow-on phase, not
part of the initial deliverable:

- Tune only the top 1–2 arms from the leaderboard, only on the **dev split**,
  guided by the eval metrics (not vibes).
- Knobs: instruction prompt wording, steps/guidance, resolution, seed policy,
  mask/guardrail on-vs-off (measure whether guardrails help or hurt — per NOTES.md).
- **The Key** = the frozen winning configuration: model ID + endpoint + prompt
  template + all knob values + preprocessing choices, serialized as a config
  block (JSON/dict) in the notebook. Same artifact as the Krea2 reference's
  §1 knobs + `run_config.json` — "same key + same inputs ⇒ same output."
- Re-run the **held-out split** with the Key for the reported final numbers.
- Until Phase 3 runs, the interim Key is simply the leaderboard winner at
  default settings.

## 6 · Deliverables

1. **The Colab notebook** — sections mirroring the Krea2 house style:
   §1 Key/knobs → §2 Setup → §3 Upload pair → §4 Run (any model) →
   §5 Eval harness → §6 Comparison grids + leaderboard → §7 Verdict card.
2. **Proof of work** — round-1 + tuned results, metric tables, grids, and the
   dev/held-out methodology.
3. **The final implementation + Key** — `try_on()` locked to the winning model
   with the frozen config; one-click path: upload two images → result.
4. **The memo** — why the winner beats Qwen 2511 (numbers + examples), why
   Krea 2 was cut, what to ship / productionize next.

## Inspiration ledger — patterns taken from the reference notebooks

### From Krea2 Identity Edit

| Pattern | Verdict | Phase |
|---|---|---|
| Quality gates with named thresholds | ✅ Core of our eval harness | 1 |
| Run packages (`run_config.json` + `metrics.json` per run) | ✅ Essential at 8 arms × 100 pairs scale | 1 |
| Preflight cell | ✅ Adapted: API keys valid, fal reachable, person-detect / garment-detect on inputs | 1 |
| Stakeholder eval card | ✅ Becomes the leaderboard/verdict card | 1 |
| `globals().get(knob, default)` stale-session resilience | ✅ Notebook hygiene | 1 |
| Mask→crop→edit→stitch | ⚠️ Reshaped: **post-hoc stitch** — segment garment region, paste original pixels back elsewhere; deterministically guarantees background/identity. A guardrail experiment, measured by our own eval | 3 |
| Warm model cache | ❌ Irrelevant for hosted APIs (revisit only if running FASHN weights locally) | — |

### From MagicHourOptimize

| Pattern | Verdict | Phase |
|---|---|---|
| Validate/self-correct loop | ✅ Reshaped for the **VLM judge**: force verdicts into a JSON schema, validate, feed errors back for retry — one malformed judge response must not corrupt the leaderboard. Most transferable piece of the notebook | 1 |
| Prompt-enhancement ("enhance loop") | ⚠️ Deferred as a **tuning knob**: VLM describes the garment in detail, description injected into the edit instruction. Only helps prompt-taking arms (klein edit, Qwen-Image-3, Seedream, GPT Image 2) — dedicated try-on arms take no prompt. Classic "does machinery help or hurt?" question → answer with the eval: `static template` vs `VLM-enhanced` per arm | 3 |
| Latency/cost accounting | ✅ Light version: per-arm latency + $/image recorded in `metrics.json` — "beats Qwen by X pts at Y¢/image and Z s" is a stronger memo argument than quality alone | 1 |
| VRAM handoff, bbox-composition schema, transformer forward-hook profiling | ❌ Local-model / Ideogram-specific | — |

## Non-goals

- No training/fine-tuning; no app/API/deployment; no exhaustive model zoo —
  judgment about which models fit is itself the work.

## Open items

- Compute/API card from Runbo (references run local-GPU; dedicated try-on
  candidates are hosted APIs — likely need both).
- Confirm exact Qwen 2511 settings used by the website for a fair baseline.
- Access to `headswap_V2` repo if reusing its ComfyUI scaffolding locally.
