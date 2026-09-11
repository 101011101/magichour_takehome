# v3.7 — RESULTS

Per-case detail, numbers and methodology for [EXPERIMENT.md](EXPERIMENT.md), per
[SCHEMA.md](../SCHEMA.md).

## 1. The run (2026-09-10)

**Call 1.** `v3/colab/lib/run_v37.py`, **102 klein calls** on
`fal-ai/flux-2/klein/4b/distilled/edit`, seed 46, 51 pairs × 2 wordings, ~6 min wall.
Outputs `v3/runs/v37/run/refs/{sid}__{BCp,BCp2}_raw.jpg`.

**Crop + call 2.** The V2 cropper (`ironman_bc_crop.crop_bc`) on an 8-pair subset —
14 crops, 97 s each on the laptop CPU — then **16 klein calls**. Outputs
`refs/{sid}__{arm}.jpg` and `gen/{sid}__{arm}__s46.jpg`.

**The crop stage is serial, and that is a finding rather than a default.** It was first
written on three threads on the reasoning that BiRefNet and the human parser are both
onnxruntime and release the GIL. They do; but `phase3_variants.masks` also calls MediaPipe's
`ImageSegmenter`, and one segmenter is not safe for concurrent `segment()` calls. Three
workers sharing it completed **zero crops in 26 minutes**, against ~97 s each serially. The
reason is recorded in `run_v37.py` at the stage so it is not re-attempted.

**Total $1.77.** Prompts as sent, per-stage timings and the cost breakdown in
`v3/runs/v37/run/meta/run_v37.json`. Page: `v3/report/v37.html` — 51 pairs × 3 arms,
`BC`'s reference and cell on every card, unblinded.

`BC`'s side is reused from `v35_linkC_20260910_0513.zip`, not recomputed.

## 2. Verdict

**Negative on all three arms of the claim.** Over 51 pairs, from
`v3/runs/v37/run/meta/pose_metrics.json`:

| | `BCp` | `BCp2` |
|---|---|---|
| source pose kept — balded, otherwise untouched | **30** | **29** |
| collapsed onto image 2 — the target's photo, re-dressed | **18** | **19** |
| genuinely re-posed toward the target | **1** | **1** |
| no landmark read — the detector finds nobody in the call-1 frame | 2 | 2 |
| | 51 | 51 |

The buckets are assignments, not thresholds: `base` says which input the output resembles
globally, and for the ones based on image 1, `d_source` vs `d_target` says which pose it is
nearer. The unreadable pairs are their own row rather than folded into "kept" — see
§6.

The two wordings differ by one pair. Whatever is happening is the model's, not the
sentence's — H4 in [EXPERIMENT §1](EXPERIMENT.md#1--does-the-pose-come-across-and-does-anything-else-come-with-it)
confirmed, and it is the only hypothesis that survived.

**The one that worked** is `p028+g015`: a black slip dress on a plain studio model, target
arms raised overhead. The output is the slip dress, arms raised overhead, in its own studio
— image 1's garment, image 1's scene, image 2's pose. The capability is not strictly
absent. It is not reachable by asking.

## 3. Method — and why `shift` alone would have misled

Landmarks from `v3lib._poser` (pose_landmarker_lite), the pipeline's own detector.
Coordinates are translated to the mid-hip and scaled by the shoulder-to-hip length, and
compared only over the landmarks confidently visible in **all four** images (garment photo,
target, and both wordings' call-1 output), so a waist-up target cannot flatter or punish a
full-body source. `v3/build/v37_pose_metrics.py`.

    shift = d(out, source) / (d(out, source) + d(out, target))

**Two corrections were needed before this number meant anything, and both are why the page
shows images beside it.** A third, the mis-bucketing of the unreadable pairs, is in §7.

1. **The ratio is undefined when the two poses are alike.** Where `d(source, target)` is
   small the ratio divides one small number by another and returns noise. Only **17 of 48**
   pairs clear `d_src_tgt >= 0.35`. Median `shift` over those: **0.13** (`BCp`), **0.15**
   (`BCp2`) — call 1 returns the source pose essentially untouched.
2. **A high `shift` is usually the failure, not the success.** When klein returns the
   target's own photograph, the output *is* in the target's pose, and `shift` goes to ~0.95
   for a total failure of the arm. `p001+p024` scores 0.956; `p010+p023`, 0.923. So `base`
   is recorded beside it — which input the output resembles globally, by mean absolute
   difference of a contrast-normalised 128×128 grey thumbnail. Of the 4 `BCp` pairs that
   land near the target, **3 got there by collapsing**.

The headline table in §2 therefore uses no threshold at all: `base` says which input the
output came from, `d_source` vs `d_target` says which pose it is nearer, and both are
defined on every pair the detector reads.

## 4. What the two failure classes look like

They look nothing alike, and a reader who only sees one class will draw the wrong
conclusion from the page. Fraction of pixels differing from the garment photo by more than
25 levels, `BCp` call 1:

`px_changed` — the fraction of the garment photo's pixels the call moved by more than 25
levels, `v37_pose_metrics.px_changed`, recorded per pair in `pose_metrics.json`. It needs no
landmarks, so it is defined on all 51. Across the two classes it separates them almost
completely:

| class | median `px_changed`, `BCp` | `BCp2` |
|---|---|---|
| source pose kept | **8.9%** | 10.2% |
| collapsed onto image 2 | **90.5%** | 92.3% |

An order of magnitude, with no overlap in the middle. Named cases, the two ends and the
one that is neither:

| pair | changed | what happened |
|---|---|---|
| `dualuse_man_black_suit_studio_nonceleb+g011` | 1.8% | hair only |
| `dualuse_emma_watson_black_blazer_armscrossed+…scarlett…backview` | 4.7% | hair only — the back-view dress stays back-view against a waist-up, arms-crossed, studio target |
| `dualuse_gal_gadot_blue_dress_redcarpet+…woman_top_denim_skirt` | 20.2% | pose unchanged, **garment leaked**: the park photo comes back wearing the target's blue dress. The one class `px_changed` alone would misfile |
| `dualuse_navy_peacoat_onmodel+g030` | 58.1% | collapsed |
| `dualuse_lp_plaid_overcoat_brown_suit+g029` | 89.5% | collapsed |
| `dualuse_hugh_jackman_grey_suit_outdoor+…zendaya_white_blazer_skirt` | 98.2% | collapsed — Zendaya's outfit on Hugh Jackman, in his own scene |

"I can't see a difference" is the correct reading of the first group and the wrong one for
the last three.

**Framing (H2) does not come across either.** The output's framing class equals the
target's on **8 of 17** separable pairs — and on the collapsed pairs it matches for the
wrong reason, because the output is the target's photograph. The classifier is not made
redundant by handing klein the photo.

## 5. Where the failure records live

- `v3/runs/v37/run/meta/pose_metrics.json` — per pair, per wording: `d_source`, `d_target`,
  `d_src_tgt`, `separable`, `shift`, `base`, `d_thumb_source`, `d_thumb_target`,
  `px_changed`, `framing_reached`; rebuilt by `python3 v3/build/v37_pose_metrics.py`
- `v3/runs/v37/run/meta/run_v37.json` — prompts as sent, timings, cost, crop record
- `v3/report/v37.html` — every reference frame and every cell, `BC` alongside; the vote
  widget exports human marks as `v37_votes.csv`

The 18 collapses are the population for the one-call observation carried in
[EXPERIMENT.md](EXPERIMENT.md#conclusion). They are recorded, not pursued.

## 6. Withdrawn numbers

Per [SCHEMA §3.3](../SCHEMA.md#3-rules-that-hold-across-all-of-them), struck rather than
deleted. Both were reported in-session before this document was written; neither ever
appeared in a committed document.

- ~~"4 of 17 pairs collapsed onto image 2"~~ — the count restricted to the 17 pairs whose
  poses are far enough apart to compute `shift`. It understated the failure by a factor of
  four: `base` needs no such restriction and is defined on every pair. **Corrected: 18 of
  51** (§2).
- ~~"32 pairs kept the source pose"~~ — the page computed that bucket by subtraction
  (`n − collapsed − re-posed`), which silently absorbed the 2 pairs the pose detector cannot
  read. **Corrected: 30, with the 2 unreadable as their own row** (§2). The page builder was
  changed to assign the bucket rather than subtract it.

## 7. Limits of this run

Stated so the verdict is not read as stronger than it is.

- **One seed.** Per [TEST §3](TEST.md#3-seeds); a capability that needs seed search is not
  one the deploy path can use, but this run does not measure seed stability.
- **Call 2 on 8 pairs of 51.** The verdict rests on call 1, where the arm's only change is.
- **`base` is a heuristic.** A thumbnail difference, not ground truth. It agreed with the
  eye on every case checked by hand, and the page shows the images so it can be overruled.
- **31 of 48 pairs cannot judge `shift`.** Their poses are too alike. They are counted in
  the §2 table, which does not need the ratio, and excluded from the median.
- **2 pairs have no landmark read at all** — the detector finds nobody in their call-1
  frame, so they are in no pose bucket. They are 4% of the fold and cannot change the
  verdict in either direction.
- **`px_changed` cannot tell a leak from a no-op on its own.** A garment leak with the pose
  untouched sits at 20%, between the two modes. It is a separator for the two large classes,
  not a classifier.
- **No human pass.** The §2 split is instrument output. The page carries the vote widget
  for a human pass; none has been run, and none is needed to fail the arm.
