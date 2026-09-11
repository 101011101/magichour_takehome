# v3.5 — RESULTS

Per-case detail, numbers and methodology for [EXPERIMENT.md](EXPERIMENT.md), per
[SCHEMA.md](../SCHEMA.md).

## 1. Link A — the four call-1 arms on 56 garments (2026-09-08)

**Run.** `v3/build/run_v35_refs.py`, **224 klein calls** on
`fal-ai/flux-2/klein/4b/distilled/edit`, seed 46, **$3.36**, 6.1 min wall (1.9 s/call
median). Outputs `v3/runs/v35/linkA/refs/{g}__{M0,M1,M2,G1}.jpg`; cost and per-call wall
time in `meta/run.json` + `meta/timings.csv`; every prompt as sent in `meta/prompts.csv`.
Crops, framing reads and the A100 `VEi` references are reused from
`v3/runs/v34/ironman2/` — link A paid for klein calls and nothing else. Page:
`v3/report/v35_linkA.html` (56 garments × 7 columns, unblinded).

**Derived arms.** `M1c`/`M0c` — the same references with the head subtracted by the V2
cropper (`phase3_variants.masks(cranium=True)`, the exact call
`v3/build/ironman_bc_crop.py` makes for `BC`) — `v3/build/run_v35_headcrop.py`. **No model
call**; ~90 s/image on this laptop's CPU, so 112 images ≈ 2.7 h, running at the time of
writing. The mechanism is verified on the arms-crossed blazer: `M1c` comes back front-on,
arms down, **headless, with the collar and lapels still photographic** — klein re-drew the
pose, the cropper removed the head, and nothing re-drew the garment after that.

### 1.1 What the arms do — first read (2026-09-08)

The reviewer's pass over the full page is pending. Read so far: the 4-garment smoke set
plus 18 garments sampled across the fold (`dualuse_lp_*`, `g015`–`g030`, `p015`–`p020`).
Four things it shows, stated as claims the full pass must confirm or kill:

1. **The mannequin sentence is not what does the re-posing.** `M1` — the turn sentence
   alone, no mannequin — turns the wearer front-on as reliably as the lock does on every
   garment read: profile shots (`p017`, `p018`), a walking side-on figure (`p016`),
   arms-crossed (`p019`, the blazer), and the **backview dress**
   (`dualuse_scarlett_johansson_black_dress_backview_night`), which comes back facing
   forward with the garment's front visible. That last case is the class
   [v3.4 SOLUTION §4](../v3.4/SOLUTION.md) carried open as **F3 / a source-image problem no
   renderer fixes**. On this evidence the re-pose reaches it; whether the *garment* it
   turns around is the right garment is a separate question, and the one link B has to
   answer.
2. **`M0`, `M1` and `M2` are the same garment.** Across the sample the three arms are hard
   to tell apart on the clothing itself, which is what makes the pair `M1`/`M2` a clean
   read on the mannequin sentence: it costs nothing and it buys identity removal, nothing
   else. **One exception, and it runs against the lock:** on `p020` (long tunic over
   trousers) the lock's own `VEi` reference and `M0` both come back in **shorts** — the
   trousers dropped — while `M1` and `M2` keep the full tunic and trousers. A single cell
   at one seed, not a result; flagged for the reviewer's pass because it is the F3
   dropped-piece failure appearing on the *control* and not on the new arms.
3. **`M1` keeps the wearer's head — including headwear.** By construction: the face
   survives (`p015` keeps its kufi cap, the kimono set keeps its beret, `p017` its
   glasses) where every mannequin arm removes them. That is not a defect of `M1`, it is
   the reason `M1c` exists — but it does mean **`M1` must never be handed to call 2 with
   the head on**, or call 2 has a second face to borrow from.
4. **`G1` — the clothing alone — restructures the garment.** It returns a clean
   e-commerce flat every time, and it is the only arm that fails the garment test
   outright, in two ways seen repeatedly: **length changes** (the arms-crossed blazer
   returns as a full-length coat; `p017`'s shirt as a shirt-dress; `p018`'s waistcoat +
   shirt as a **sleeveless dress**; `g030`'s sequin shirt lengthened) and **dropped
   pieces** (trousers gone on `p015`, `p017`, `g018`, `g030`; the white tee gone under
   `g029`'s blazer). Removing the wearer removes the constraint that held the garment's
   shape — the same mechanism as v3.4's placket, arrived at from the other side.

**Reading.** The experiment's target shape survives link A: the re-pose does not need the
mannequin, so the head can come off with a crop instead of being replaced by a generator.
`G1` is the arm to drop unless link B finds it a job. Nothing here is a verdict on call 2
— every claim above is about the reference, at one seed, on fal.

### 1.2 The head crops, complete (2026-09-08)

**Run.** `v3/build/run_v35_headcrop.py M1 M0` — 112 crops, `M1c` and `M0c` for all 56
garments. **No model call**; median 82 s an image, which is BiRefNet on an eight-year-old
CPU rather than the method. `phase3_variants.masks(cranium=True)` — the V2 cropper's own
head subtraction, the exact call `BC` makes — and **the human parser fired on all 112**
(`cranium_used=True` in `meta/headcrop.json`), so nothing fell back to the pose ellipse.

**The mannequin head crops more cleanly than a real one.** This is the finding the pair
`M0c`/`M1c` exists to produce, and it runs against the arm this investigation set out to
favour. On `g029` (the houndstooth blazer) `M0c` comes back with a clean neckline and
`M1c` carries a ragged white notch through the left shoulder where long hair met the
lapel; the plaid overcoat shows a milder version of the same at the collar on both arms.
The mechanism is not mysterious — a mannequin head is a smooth convex shape with a
hair-free boundary, which is the easy case for a matte, where a real head with hair over a
collar is the hard one, and the parser's boundary error lands **on the garment**.

**And the crop inherits whatever call 1 did.** `p020` is the case: the lock's prompt drops
the tunic's trousers and renders shorts, so `M0c` is a headless figure in shorts, while
`M1` keeps the full tunic and `M1c` keeps it too. Removing the head cannot repair a piece
call 1 never drew — the two failures are independent, and an arm has to win both.

**What this changes for link C.** It gives `VEic` a real argument the design did not
anticipate: the mannequin sentence costs a call-1 draw that sometimes loses a piece, but
it buys a head that is *easier to cut off cleanly*. `M1qc` is the cheaper reference and the
riskier crop. That is exactly the trade the 31-pair run has to price, and it is why both
arms are in it rather than one.

## 2. Link B — the head-cropped reference through call 2 (probe, 2026-09-08)

**Run.** `v3/build/run_v35_edits.py`, **15 klein calls** on fal, seed 46, **$0.22**,
8.2 min (SR on this laptop's CPU dominates; the klein calls are 3–5 s each). Five pairs ×
three arms (`BC`, `M0`, `M1c`). Outputs `v3/runs/v35/linkB/gen/`; the references as call 2
saw them (SR'd to ~1 MP) in `v3/runs/v35/linkB/refs_sr/`. Page: `v3/report/v35_linkB.html`.

**The set.** All five are **seed-stable `VEi` failures** — `g004+g005`, `g005+g009`,
`g005+p002`, `g027+g029`, `g027+p011`, five of the eight pairs in
`v3/testsets/v35_failures.csv` that the reviewer marked FAIL at every seed in iron man 2.
They were picked because their references were the ones already head-cropped when the probe
ran, not for their outcome; the other three are queued.

**Cell by cell.**

| pair | `BC` | `M0` | `M1c` |
|---|---|---|---|
| `g005+g009` cream knit + trousers | **shorts** — trousers dropped | **shorts** — trousers dropped | **full-length trousers** — the only correct one |
| `g027+p011` yellow chef top | short sleeves, print bleeds through | long sleeves, print bleeds | long sleeves, print bleeds |
| `g027+g029` houndstooth blazer | blazer over the wearer's own tee | cleanest of the three | correct pieces, a white shoulder artifact |
| `g005+p002` black tee + jeans | wearer's shorts survive | wearer's shorts survive | wearer's shorts survive |
| `g004+g005` UA tee + shorts | handbag survives | handbag survives | handbag survives |

**Reading.** Two things, and they point in different directions.

1. **The head crop reaches a failure the mannequin reference does not.** On `g005+g009`
   the dropped-trousers failure is present in the incumbent *and* in the lock's own prompt,
   and absent in `M1c`. That is the F3 dropped-piece class, and it is the second time in
   this investigation that the explicit turn sentence has held a piece the lock lost (the
   first was `p020`'s tunic at link A, on the reference itself). One cell each; two cells
   is a signal to run the set, not a result.
2. **No reference change touches F1.** On `g005+p002` and `g004+g005` the wearer's own
   shorts and handbag survive under all three arms identically. v3.4 called F1 a
   person-side failure; this probe is consistent with that and gives no reason to reopen
   it from the reference side.

**Not claimed.** One seed, five pairs, chosen for readiness. No blinding, no judge, no
control set — a failure-selected probe cannot say what any of this costs on the 163 pairs
that already work. The full 31-pair × 3-seed run is link B proper; the fold is link C.

### 2.1 One call re-poses *and* balds (2026-09-08)

**Run.** `v3/build/run_v35_bald_probe.py`, **10 klein calls** on fal, seed 46, **$0.15**.
Five garments × two arms; the `M0` mannequin column is link A's, same backend and seed, so
it costs nothing and is paired. Outputs `v3/runs/v35/bald_probe/refs/`; page
`v3/report/v35_bald.html`.

**The set, and why these five.** Ranked by **garment lost to hair removal** — the alpha-area
difference between V2's own two crops of the same photograph, `c32_no_face_keep_hair` minus
`c3_no_face` (`v2/runs/crop_screen`). That is the quantity V2's `hair_threshold = 0.14`
gates `BC_klein` on, so it is the fold's own definition of "long hair" rather than a new
one. Four of the five are over the threshold:

| garment | hair share | `M1q` (re-pose only) | `M1qb` (+ bald) |
|---|---|---|---|
| `p021` | 0.195 | braids down the chest, **on the sweater** | bald, sweater clean |
| `dualuse_woman_top_denim_skirt_nonceleb` | 0.170 | hair over both shoulders and the top | bald, clean |
| `p023` | 0.169 | large afro, mostly clear of the garment | bald |
| `dualuse_zendaya_white_blazer_skirt` | 0.144 | curls across the **white blazer lapels** | bald, lapels clean |
| `p012` | 0.140 | hair over the cardigan shoulders | bald, clean |

**The clause**, lifted from `v3lib.BALD_PROMPT` so the wording is the record's rather than a
new invention (its third sentence dropped, because `KEEP` and `PERSON_CLAUSE` already say
it): *"The person is completely bald: remove all hair from the head and any hair falling
over the shoulders, chest or back, and show the scalp."*

**Result.** One call does both jobs on all five: still front-on, arms down, framing kept,
garment unchanged, and the hair off the garment. It leaves the wearer's *face* — bald, not
featureless — which does not matter, because the head is cropped afterwards.

**What it settles.** `M1q` without the bald clause is not a shippable arm: on a long-haired
wearer it bakes hair into the reference that no downstream stage removes. Link C therefore
runs `M1qb` and does not run `M1q` — the bald version covers that case and is the only
functional form.

**Not claimed.** Five garments, one seed, references only. Whether the bald clause costs
anything on the *garment* across the fold is a link C question, and the arm carries it
there.

## 3. Link C — the run (2026-09-10)

**Run.** `v3/colab/v35_a100.ipynb` on an A100, one session: **645 klein calls, 36.8 min,
$0.42** at CAD 0.689/h. 51 pairs × 4 new arms × 3 seeds = **612 edits**, plus 33 `M1qb`
references; `VEi` and `BC` cells and the lock's pre-SR references came off Drive rather
than being redrawn, which is what kept it to 645 calls instead of ~1,000. Outputs
`v3/runs/v35/linkC/`; page `v3/report/v35_linkC.html` (918 cells, six arms).

**Integrity of the run**, from its own meta rather than by assertion:

| check | result |
|---|---|
| cells per arm | 153/153 on all six — `VEi`, `BC`, `VEic`, `M1qbc`, `VEica`, `M1qbca` |
| human parser fired | **33/33 garments**, both bases — no fallbacks, unlike the link A pass where the backview dress fell through all three head-finding routes |
| ankle cut applied | 23/33 (`VEica`), 24/33 (`M1qbca`); a **no-op on the rest** — no ankles in frame, so the `a` arms differ from their twins on ~two thirds of cells only |
| call-2 prompt | `E3`, byte-identical to the v3.3 lock, including "nothing added, nothing removed" |
| per stage | edit 3.09 s · ref 0.95 s · SR 0.18 s · head crop 15.8 s (CPU, threaded) |

Crops ran on **CPU by choice**: every reference of record, including the `BC` refs this
comparison is measured against, was made with CPU ONNX inference, so CPU crops are
numerically identical to the archive and cell 7's validation cannot drift. The GPU path
works (cell 3 probes for an onnxruntime whose CUDA provider actually loads) and is ~6×
faster, but it would put the crops on a different numeric footing from the baseline.

## 4. Why `BC` may simply be better — the regeneration tax

**The count that raises it.** `BC_klein` marked in one pass over all 600 iron-man-2 cells
(`v3/report/bc_count.html` → `v3/testsets/bc_count.csv`, 2026-09-10): **29 failures, 4.8%**,
19 pairs, 2 seed-stable. The `VEi` record on the same 600 cells is **55, 9.2%**, 31 pairs,
8 seed-stable. Joined per cell:

| | VEi CLEAN | VEi MID | VEi FAIL |
|---|---|---|---|
| **BC ok** | 467 | 61 | **43** |
| **BC FAIL** | 8 | 9 | 12 |

43 cells where the lock fails and the incumbent does not, against 17 the other way.

**The mechanism this points at.** `BC` and every `V`-family arm differ on one axis that has
nothing to do with prompts: **whether a generative model ever re-draws the garment.**

- `BC`'s bald pass edits the *head*; the garment is then isolated by a **deterministic
  matte**, which can only remove. Its garment pixels are the photograph's, end to end.
- Every `V`-family arm — `V`, `VEi`, `VEic`, `M1qbc` — asks klein to re-draw the whole
  frame in call 1, because a head swap and a re-pose are full-frame edits. **The garment
  that reaches call 2 is a rendering of the garment, not the garment.**

A distilled 4-step model re-drawing a garment does not copy it. It resamples it, and the
resampling loses exactly what call 2 most needs: weave, print registration, seam and hem
placement, the count of pieces. The loss is not uniform noise — it is *structured
invention*, which is worse, because call 2 has no way to tell an invented placket from a
real one and will faithfully transfer the invention onto the wearer. So a defect introduced
in call 1 is not merely carried into call 2, it is **amplified** by it: call 2 treats the
degraded reference as ground truth.

**Evidence already in the tree, all of it consistent with this and none of it collected to
prove it:**

| observation | where |
|---|---|
| klein asked to render above its conditioning **invents structure** — the p004 placket appears at ×2.67 generation-upscale | [v3.4 RESULTS §7.1](../v3.4/RESULTS.md) |
| "render at evidence scale… generate small, upscale the *finished* image algorithmically" — a rule adopted precisely because generative rendering degrades garments | [v3.4 SOLUTION §5](../v3.4/SOLUTION.md), rule 2 |
| the garment criterion is **statistically identical across every 1 MP arm** (2.5–2.7 of 5): the whole canvas arc bought identity, scene and realism, and **bought nothing on the garment** | [v3.4 SOLUTION §6](../v3.4/SOLUTION.md) |
| `G1`, the most aggressive regeneration (wearer removed entirely), is the **only arm that fails the garment test outright** — length changes and dropped pieces | [§1.1](#11-what-the-arms-do--first-read-2026-09-08) |
| `p020`: the lock's own call 1 **drops the tunic's trousers** and renders shorts; the crop then inherits it | [§1.2](#12-the-head-crops-complete-2026-09-08) |
| `g005+g009`: `VEi` and `VEic` drop the reference's trousers, `BC` and `M1qbc` do not | [§2](#2-link-b--the-head-cropped-reference-through-call-2-probe-2026-09-08), §3 |

The head crop cannot address any of this. It changes **how identity is removed**, which is
downstream of the re-draw; the garment has already been resampled by the time it is cropped.
That is why `VEic` tracks `VEi` on the garment failures rather than repairing them.

**What this does not yet establish, and must before it is believed.**

1. **The two rates were not measured the same way.** `VEi`'s 9.2% came from a
   judge-then-audit protocol; `BC`'s 4.8% from a single fresh sweep on a purpose-built page.
   A stricter or more lenient day accounts for some unknown share of the gap. The fix is
   already built and running: `v3/report/vei_count.html` is the identical page for `VEi`,
   so the same eye can produce both numbers under one protocol. **No conclusion here should
   be drawn until that pass is exported.**
2. **`BC` cannot re-pose, and the fold does not punish it for that.** The 200-pair matrix is
   mostly front-facing wearers, where re-posing buys nothing and only costs a re-draw. On a
   backview or extreme-pose source `BC` has no move at all — v3.4 called that a source-image
   problem no renderer fixes, and [§1.1](#11-what-the-arms-do--first-read-2026-09-08) showed
   the re-pose arm turning the backview dress to front. So the honest question is not "is
   `BC` better" but **"does the re-pose buy back more than the re-draw costs, and on what
   share of a real catalogue?"** A fold with more awkward source photographs would move this
   number, possibly a long way.
3. **A hybrid is untested and is what the mechanism actually recommends.** If the re-draw is
   the tax, the arm to build is one that pays it **only when the pose requires it** —
   v3.4's `F3` line, "re-pose only when the pose reader says the wearer is not neutral;
   otherwise ship the garment pixels untouched". That is a router, not a new prompt, and
   nothing in v3.5 has tested it.
