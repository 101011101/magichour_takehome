# V2 handoff — read this first

**Purpose.** Open a new chat, say *"read `prd/v2/HANDOFF.md`"*, and be up to speed.
Everything below is either the state of play or a pointer to it. Written 2026-08-20.

**Who/what.** Ray is building V2 of a virtual try-on system for deployment into Magic
Hour company code. Hard constraint: **open weights only in the deployed path.** fal is
used as a serving substrate for those same open checkpoints during iteration; final
numbers are owed on downloaded weights.

---

## 1. Where the project is right now

**v2.2 (attention and failure) is one component from done.**

| workstream | status |
|---|---|
| v2.0 arm selection | complete — klein 4B distilled chosen |
| v2.1 realism / auxiliary | complete, parked — SeedVR2 `noise_scale=0` chosen |
| **v2.2.1** garment reference cropping | **complete**, three phases |
| **v2.2.2** person crop + composite | **closed as obsolete** — addressed by v2.2.1 |
| **v2.2.3** failure gate + routing | **in progress — the last piece of v2.2** |
| v2.3 artifacts | not started |
| v2.4 auxiliary cleanup | not started |

### The finding the whole program now rests on

**The descent hypothesis.** klein descends toward a correct solution it can already
produce; the attention deficit is what chips away at it. The model is not short of
capability — competing content in the garment reference is what stops it going all the
way. **Therefore the manner of removing the deficit is free to vary**, and that
interchangeability is where V3's cost work lives.

Recorded verbatim (including the status note Ray sent to Runbo) in
`prd/v2/RESEARCH_LOG.md`, entry 2026-08-19.

### The three arms that solve it

| arm | what it is | perfect / fail (38 sets) | cost |
|---|---|---|---|
| **BC_klein** | klein makes the person bald → deterministic crop | 74% / 5% | 1 extra generation |
| **QX_qwen_p1** | Qwen-Image-Edit-2511 asked to return only the clothing | 58% / 8% | 1 extra generation |
| **PHEAD** | human-parser head removal, no generative step | 63% / 21% | **free** |
| *baseline* `control` | C3.1 as it originally shipped | 53% / 34% | free |

**BC_klein + QX = 100% usable across all 38 sets, with five failures between them and
zero overlap.** Subtraction cannot recover what it never saw; regeneration cannot
reproduce what it never captured — different failure causes, so they rescue each
other.

---

## 2. What to read, in order

**Start here — the three reference documents, written 2026-08-21:**

| document | what it is |
|---|---|
| **[ARCHITECTURE.md](ARCHITECTURE.md)** | **standalone assembly spec** — what to build and how, no history. Component table with licences, the three arms decomposed, the two VLM checks, build order, and a *what not to build* section |
| **[DECISIONS.md](DECISIONS.md)** | every sub-version as question → architecture → result → verdict → how to redo it. All scrapped arms with the measurement that killed them, and the withdrawn-claims ledger |
| **[TODO.md](TODO.md)** | what is left, ordered, with the blocking/iteration split |

**Then, for the working detail:**


1. **`prd/v2/v2.2/RESULTS.md`** — the substance. Attention Modulation Test, the three
   arms and their failure modes, the union model, the cost analysis, the router probe.
2. **`prd/v2/v2.2/EXPERIMENT.md` §2c and §2d** — why each experiment was designed the
   way it was, and the v2.2.3 architecture.
3. **`prd/v2/v2.2/PLAN.md`** — execution shape and current statuses.
4. **`prd/v2/RESEARCH_LOG.md`** — dated, append-only, the reasoning as it happened.
5. **`prd/v2/results_summary/V2.2_RESULTS.md`** — program-level summary and checkpoint.

Conventions: `execution_conventions.md` at repo root. Parking lot for unscheduled
ideas: `prd/v2/V2.x_DIRECTIONS.md`.

---

## 3. The open task — v2.2.3

Two halves of one component:

| half | runs | job |
|---|---|---|
| **Gate** | after generation | score a frame, accept or **escalate to a different arm** |
| **Router** | before generation | predict which arm to start with — **deferred** |

**Critical design correction:** the gate must **escalate mechanism, never reseed.**
Failure is a property of the *garment* — a damaged reference failed on all three
people it was paired with — so retrying the same arm reproduces it. The original
v2.2.3 spec assumed retry-with-fresh-seed; that design is dead.

**Cascade order: PHEAD → QX → BC_klein** (1.421 units/request) beats PHEAD → BC → QX
(1.526). QX rescues precisely PHEAD's failure mode, so it converts more on the first
escalation even though BC_klein is the stronger arm alone.

**The router is deferred on arithmetic**: it must be ≥79% accurate to beat simply
cascading, and the candidate sits at ~75% — which is itself optimistic, being fitted
and evaluated on the same 22 garments.

### RESOLVED — the deterministic gate does not work, and will not (2026-08-21)

Built at `v2/build/failure_gate.py`, graded over 456 outputs, then tested blind
against the reviewer on 114 cells (`v2/artifacts/v223_cheapest_usable.html`).

| | |
|---|---|
| **AUC, gate score vs Ray's usable call** | **0.506** — a coin flip |
| Mean gate score, usable (n=82) vs unusable (n=32) | 0.684 vs 0.674 |
| Best agreement at any threshold | 71.1% |
| Agreement from accepting every frame unchecked | **71.9%** |

**Identity ran and is excellent — at the wrong thing.** 100% precision at every
threshold 0.1–0.6, and it fires on **zero of PHEAD, BC_klein and QX**, reading 1.00
on all eight PHEAD failures. It only fires on `BALD_raw` and the D\*O arms, which keep
a head in the reference. The cascade arms remove the reference person, so identity
substitution is the one failure they cannot have.

**The control that makes it conclusive:** Ray's earlier AMT tier predicts his later
binary call at 95% / 44% / 0% across perfect / ok / fail. The target is stable; the
instrument is the problem. Charts: `prd/v2/v2.2/images/gate_vs_human.png`.

**Decisions taken.** The binary gate does not ship. Identity stays wired in as a free
100%-precision monitor, never a spend decision. The router stays deferred on a second
ground — it is only worth building on a gate that catches its mistakes. **QX moves to
slot 2**: of PHEAD's 13 unusable sets QX rescues 11, BC_klein 6 (both PHEAD and
BC_klein subtract and share a failure mode), 1.789 gen/request vs 2.053.

### THE HARNESS — settled and measured, 2026-08-22. v2.2 is closed.

Design: [`ARCHITECTURE.md`](ARCHITECTURE.md). Evidence:
[`v223_vlm_eval.html`](../../v2/artifacts/v223_vlm_eval.html),
`v2.2/images/harness_v223.png`.

```
user specified a garment region?  ──yes──►  QX
hair over garment >= ~14%?        ──yes──►  BC_klein  (2 gen)
                    |no
                    v
                 PHEAD  (1 gen)
                    |
   no-op / degenerate vs person input       ──┐
   identity < 0.90  (wrong person)          ──┤
   VLM-A  tryon != PERFECT                  ──┤
   VLM-A  garment == FAIL                   ──┴─► QX (+2 gen), take QX
                    |clean
                    v
                  ship  ──►  realism pass, conditional:
                              skip if already sharp (hf >= 2.5)
                              revert if identity < 0.90
```

**2.158 generations/request. 31 perfect / 7 ok / 0 fail over 38 sets.** Flat
BC_klein, the best single arm, is 2.000 for 28/6/4 — essentially the same cost, and
**nothing ships broken**. A cheaper gate (`garment == FAIL` + identity) gives 1.789
for 32/5/1; safe was chosen deliberately.

**The three things the VLM evaluation established:**

1. **Do not ask about artefacts.** That prompt returned `CLEAN` on all 114 outputs and
   never fired once. Our failures are not artefacts — they are competent photographs
   of the wrong thing.
2. **VLM-A must see the garment reference.** Only the prompt with a reference image
   beat the do-nothing baseline (70.2% vs 62.3%); every output-only formulation sat
   exactly on it. Counter-intuitively, adding the *person* image as well made it worse.
3. **No pairwise selection call.** 34% self-consistency under image swap; picked the
   already-failed arm 2 of 5 times. Always take QX.
4. **The VLM does not replace the free input-comparison checks.** Over 114 cells the
   VLM caught 26 failures they missed and they caught **1** the VLM missed — and that
   one was the only frame that shipped broken. Identity swaps and no-ops are coherent
   photographs of the wrong thing, so a semantic judge has nothing to find.

**Corrected twice, same direction.** The deterministic checks were first justified on
robustness alone (wrong: the no-op check catches `HD_p023`), then identity was written
off as useless on the cascade arms — **measured at threshold 0.5, which was the wrong
operating point.** At 0.90 it fires once in 114 cells, on the one frame that shipped
broken. Both corrections say the same thing: the checks are precise low-recall
detectors for the blind spot a semantic judge has by construction, and they cost
nothing.

**Caveat:** the model hedges (331 of 570 verdicts `OK`, only 49 `FAIL`), which caps
recall at 51%. Binary forced-choice prompts and fp16 instead of 4-bit are both untried.

### THE REALISM PASS — validated and made conditional, 2026-08-22

[`v2.4/RESULTS.md`](v2.4/RESULTS.md) ·
[`v223_realism_pass.html`](../../v2/artifacts/v223_realism_pass.html) (drag to wipe,
zoom to 12×). SeedVR2 ×2 at `noise_scale = 0` over the 38 frames the harness ships.
The resolution gain is clearly visible; run unconditionally it cost identity on **7 of
38 frames, worst 0.772** — inside the range that eliminated Z-Image Turbo in v2.1.

Gated on both sides: **skip if `hf_before >= 2.5`** (already sharp), **revert if
`identity_cos < 0.90`** (it damaged the face). 29 calls instead of 38, **no frame
below 0.90**, 1.110 of the 1.121 sharpening gain kept.

The trigger works because the frames that lose identity are the frames SeedVR2 *failed
to sharpen* — `corr(hf_ratio, identity) = +0.512`. The failure announces itself.

### NEXT — the end-to-end run

Run the **assembled** pipeline over the 38 sets, **including the SeedVR2 realism
pass**, against `qwen_2511` (the website baseline), flat klein, and flat BC_klein.
~$2–3 fal. Including SeedVR2 closes the long-owed "composite never validated end to
end" gap in the same pass. Then the report. See [`TODO.md`](TODO.md).

---

## 4. Working agreements that were learned the hard way

- **Everything is judged by eye.** Three separate times an instrument said the
  opposite of the truth: no-op outputs scored perfectly on identity; the bald-frame
  "garment lost" metric collapsed to ~0 by construction; furniture sat in every crop
  undetected. **Every stage of this pipeline has been debugged by looking, not by
  measuring.**
- **`node --check` the JS before shipping any review page**, and verify image paths
  resolve — both have broken pages more than once. A function-name collision
  (`paint`) silently killed every listener registered after it.
- **Check that a test set contains the failure mode it is meant to test.** The first
  Attention Modulation set excluded the worst hair-damage reference entirely, which
  flattered the baseline and produced a wrong recommendation.
- **Mean rank and win-counts are invalid** where the top band is a *tie*. Both were
  used once and withdrawn.
- Record negative results first; never delete a superseded conclusion, mark it.

---

## 5. Verify what exists

```bash
cd /Users/arviny/Downloads/Code/magichour_takehome
python3 v2/build/check_links.py           # every doc→artifact link resolves
ls v2/artifacts/v221_*.html               # the review pages
ls v2/runs/amt/gen | wc -l                # 456 generated outputs
```

### Review pages (open in a browser)

Paths are relative to the repo root so `check_links.py` can verify them — bare
backticked filenames were reported broken because the checker resolves non-relative
links against the repo root, not `v2/artifacts/`.

| page | what it is |
|---|---|
| [`v223_perfect_tier.html`](../../v2/artifacts/v223_perfect_tier.html) | **the live task** — three-tier marking, stop on perfect |
| [`v223_cheapest_usable.html`](../../v2/artifacts/v223_cheapest_usable.html) | superseded binary usable/not sheet; the gate-vs-reviewer evidence |
| [`v223_gate_simulation.html`](../../v2/artifacts/v223_gate_simulation.html) | gate threshold slider and cascade replay |
| [`v221_attention_mod.html`](../../v2/artifacts/v221_attention_mod.html) | the main v2.2.1 test — 38 sets × 10 arms, ⓘ cards, drag-ranking |
| [`v221_crop_tuning.html`](../../v2/artifacts/v221_crop_tuning.html) | arms ordered by result, pick a best replacement |
| [`v221_crop_tuning_phead.html`](../../v2/artifacts/v221_crop_tuning_phead.html) | PHEAD vs the arms it has to beat |
| [`v221_phase3_acc.html`](../../v2/artifacts/v221_phase3_acc.html), [`_crops`](../../v2/artifacts/v221_phase3_crops.html), [`_ac`](../../v2/artifacts/v221_phase3_ac.html), [`_bg`](../../v2/artifacts/v221_phase3_bg.html), [`_m`](../../v2/artifacts/v221_phase3_m.html) | phase-3 screens |

**Naming convention** (de facto, not previously written down): the filename prefix is
the workstream that *produced* the page — `v20_`, `v21_`, `v221_`, `v223_`. Three
harness pages were renamed from `v221_` to `v223_` on 2026-08-21.

### Human-labelled data (the ground truth everything is scored against)

| file | contents |
|---|---|
| `v221_attention_mod_rankings (1).csv` | 38 sets × 10 arms, tier = top/mid/out |
| `v221_phead_verdicts.csv` | PHEAD, perfect/ok/fail |
| `v221_review_annotations.csv` | phase-2 failure annotations, per-category |

**Reading rules for the rankings CSV, set by Ray:** `top` = **tied for first** (rank
within it is meaningless), `mid` = genuinely ranked, `out` = failed. An unmarked base
means the base passed; a base marked failed with a blank crop cell means that crop did
**not** solve it.

---

## 6. Moving to another computer

**Bring:**

- the whole repo **except** `v2/runs/` (it is ~1GB of generated images)
- from `v2/runs/`, keep only: `amt/` (108M — the generations everything is scored
  against), `crop_screen/crop_log.csv` (the source-path index every script reads), and
  `amt/_run.json`, `amt/_gate.json`, `amt/_refs.json`
- the three human-labelled CSVs at repo root
- `.env` (holds `FAL_KEY`) — **not** in git

**Do not bring** `v2/runs/.models/` (~610MB). All of it re-downloads on first use:
BiRefNet_lite, MediaPipe selfie + pose, SegFormer human parser (`mattmdjaga/segformer_b2_clothes`),
AuraFace. See `v2/runs/.models/PURGEABLE.md`.

**Recreate the environment:** `.venv` with `opencv-python`, `mediapipe`,
`onnxruntime`, `torch`, `transformers`, `scikit-image`, `insightface`, `open_clip`,
`fal_client`, `matplotlib`. Note the venv is Python 3.9 and several scripts are run as
`.venv/bin/python`, not bare `python3`.

**Costs so far:** ≈ $19.6 fal across the whole of V2, ≈ $9 of that in phase 3.

---

## 7. Owed regardless of what happens next

**The self-hosted parity run.** Every number in every document is a **fal** number,
and V2's entire premise is open weights in the deploy path. Nothing has been verified
on downloaded weights end to end. Of all outstanding work this is the one most likely
to matter in review — see `prd/v2/V2.x_DIRECTIONS.md` direction 6.

Also unverified: the licence and training-data terms of
`mattmdjaga/segformer_b2_clothes`, which the current head detection depends on.
