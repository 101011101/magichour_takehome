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

### THE CURRENT BLOCKER — the gate does not work yet

Built at `v2/build/failure_gate.py`, graded over 456 outputs. **Result: near-random.**

| human label | gate score (mean) |
|---|---|
| perfect | 0.677 |
| ok | **0.757** ← higher than perfect |
| fail | 0.584 |

Per-check separation (perfect − fail): degenerate **−0.040**, noop −0.001, people
−0.021, identity **0.000 (never ran)**, background **+0.148**.

**Diagnosis: the gate targets failure modes our failures aren't.** Degenerate frames,
no-ops and duplicated people barely occur — all 456 outputs are valid photographs of
one person. The failures are *semantic*: wrong garment, wrong identity, repainted
scene. Pixel statistics cannot see those. Not a calibration problem.

**What is still worth trying, in order:**

1. **Re-run with the identity check.** It never ran — AuraFace failed to download
   during the session. **It has since completed: `v2/runs/.models/auraface`, 271MB.**
   Identity is the check most likely to work (compares against a *known* input, and
   "wrong person" was 33% of baseline failures). **This is the next thing to do.**
   Re-run the grader, then re-check the separation table.
2. **Background alone as a narrow pre-filter.** At threshold 0.3 it rejects 40 outputs
   at **70% precision against a 28% base rate** — real signal, but catches only 28 of
   119 failures. High precision, very low recall.
3. **If identity also fails to separate:** the honest conclusion is that a
   deterministic gate cannot do this job, the cascade should not ship, and the
   recommendation collapses to **use the best single arm** (BC_klein, flat 2 units).
   That is a legitimate v2.2.3 finding and better than shipping a gate that escalates
   on noise.

**A VLM gate is ruled out** on two independent grounds: §2b of EXPERIMENT.md measured
`garment_sim` at 0.78 and a VLM at 4/5 on an output that transferred *no garment*, so
it fails at the check that matters; and it costs about what a generation costs, so it
would spend the entire saving on the decision.

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

| page | what it is |
|---|---|
| `v221_attention_mod.html` | the main test — 38 sets × 10 arms, ⓘ cards, drag-ranking |
| `v221_crop_tuning.html` | arms ordered by result, pick a best replacement |
| `v221_crop_tuning_phead.html` | PHEAD vs the arms it has to beat |
| `v221_gate_simulation.html` | **the live task** — threshold slider, cascade replay, per-cell marking |
| `v221_phase3_acc.html`, `_acab`, `_crops`, `_fashn`, `_ac`, `_bg`, `_m` | phase-3 screens |

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
