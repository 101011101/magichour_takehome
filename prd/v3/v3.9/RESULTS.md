# v3.9 — RESULTS

Per-case detail, numbers and methodology for the inquiry run, per [SCHEMA.md](../SCHEMA.md).
The decisions this evidence supports are not here; they belong in
[EXPERIMENT.md](EXPERIMENT.md).

**What was run, and where.** The matrix of [TEST.md](TEST.md) was executed inside
`vp/inquiry_confirmation.ipynb` rather than `v3/colab/v39_a100.ipynb` — the production
notebook Ray asked for, which carries the v3.9 arms **plus two further inquiries** raised
while specifying production (the ONNX crops on the GPU, and garment-only references). The
v3.9 arms, set, bound and canvases are exactly as TEST.md specifies; the additions are
recorded in §4 and §5 below. Marks therefore land in `v3/testsets/inquiry_marks.csv` and the
page is `v3/report/inquiry.html` (**221 cards**, not TEST.md's 161: the garment-only block
adds 60).

## 1. The run

**A100-SXM4-40GB, 2026-09-12.** 348 klein calls, 699.4 s of call time, **18.15 min wall,
CAD 0.208** at 0.689 CAD/h (USD 5.22 on fal). Model load 154.1 s from the Drive cache.
Outputs `v3/runs/inquiry/a100/`, bundle `inquiry_20260912_0620.zip`, meta
`v39/meta/{cost_v39,v39_meta,timings_v39}.json|csv` and `inquiry/meta/garment_only.json`.

**The transformer of record for this run is Photoroom's**, as
[v3.8](../v3.8/SOLUTION.md) locked for production: `cost_v39.json` records the resolved
snapshot paths — `Photoroom/FLUX.2-klein-4b-fp8-diffusers` `transformer_bf16` @ `408c457f…`
with `black-forest-labs/FLUX.2-klein-4B` @ `e7b7dc27…` for the rest, bfloat16.

**The bound held.** `input_bound_px` = 1,048,576. Every `SCALE` canvas lands at
**0.949–1.000 MP** across 10 distinct canvases; every generated `NOSCALE` canvas at
**0.562–0.812 MP** (mean 0.696). Nothing in the run exceeds 2²⁰ px.

| stage | n | median s | mean s |
|---|---|---|---|
| `a4_crop` (`CROP2` only) | 47 | 0.15 | 0.24 |
| `bald` — 1 crop (uncropped photo) | 47 | 1.61 | 1.73 |
| `bald` — 2 crop (on the A4 crop) | 47 | 0.85 | 0.90 |
| `headcrop` — 1 crop | 47 | **16.80** | 16.29 |
| `headcrop` — 2 crop | 47 | **16.60** | 16.25 |
| `edit` — `SCALE` | 93 | 2.31 | 2.39 |
| `edit` — `CROP2` | 93 | 2.31 | 2.39 |
| `edit` — `NOSCALE` | 68 | **1.92** | 1.93 |

Two readings fall out of the table before any mark is examined. **The bald pass is ~1.9×
faster on the A4 crop** (0.85 s against 1.61 s) — fewer tokens, as predicted. And
**`NOSCALE`'s edit is ~17% faster** (1.92 s against 2.31 s), which is the arithmetic of a
0.70× canvas and is the one advantage it has that needs no reviewer.

## 2. The instrument

`v3/build/inquiry_page.py` → `v3/report/inquiry.html`. One card per comparison: two outputs
side by side, **arm labels hidden, sides shuffled per card at a fixed seed**, the group
(`fail` / `clean`) hidden, image files hash-named so the page source does not name the arm.
One mark per card — *A better · same · B better · both bad*. Export carries the unblinding
key (`shown_A`, `shown_B`), the true canvas sizes (`wh_A`, `wh_B`) and the resolved verdict.

**220 of 221 cards were marked** in one sitting; the single blank is `p024+p025`@48 in the
upscale block, and it is excluded from every denominator below.

**The resolution tell, and its residue.** `NOSCALE`'s canvas is genuinely smaller, so both
sides are resampled to the same 460 px display width and the lightbox copies to that width
too. This removes pixel-count as a cue but **not resolution as an appearance**: a 0.70×
canvas resampled up to a common width is softer, and a reviewer may prefer or punish that
softness without being able to name it. Nothing short of not asking the question removes
this, and it bears directly on §3's headline — stated here rather than discovered later.

## 3. Question 1 — does call 2 need to scale the person *up* to 1 MP?

`SCALE` (the rule of record) against `NOSCALE` (own size, floor 32, never upscaled), same
reference, same seed, same cell. 68 cells; 25 of the 93 are no-ops where both rules give the
same canvas and `NOSCALE` was not generated.

| verdict | cells |
|---|---|
| `NOSCALE` better | **22** |
| `SCALE` better | 8 |
| same | 37 |

**30 discordant cells, 22 : 8 for `NOSCALE`, two-sided exact p = 0.016.** The shipped rule
loses.

**Split by group, which is where it stops being one result.**

| group | n | `NOSCALE` | `SCALE` | same | p |
|---|---|---|---|---|---|
| `fail` | 36 | **20** | 3 | 13 | **0.0005** |
| `clean` | 31 | 2 | **5** | 24 | 0.45 |

On the cells `ER` already fails, not upscaling is better by 20 : 3. On the cells `ER` already
passes, the direction **reverses** — 2 : 5 to `SCALE` — at a sample that cannot resolve it.
v3.8's adoption rule is that an arm ships only if it wins on `fail` **without losing** on
`clean`; on these numbers `NOSCALE` wins the first half decisively and the second half is
unresolved, not won.

**Against how much upscaling.** The marks join to each cell's canvas areas:

| `NOSCALE` / `SCALE` area | `NOSCALE` | `SCALE` | same | p |
|---|---|---|---|---|
| 0.6 | 2 | 1 | 1 | 1.00 |
| 0.7 | 9 | 4 | 27 | 0.27 |
| 0.8 | 11 | 3 | 9 | 0.057 |

The effect is **not** concentrated where the upscale is largest — if anything it is strongest
where the two canvases are closest (0.8), which is the opposite of what "the upscale harms"
predicts, and is the single most awkward number in this section. On n = 30 discordant cells
split three ways, none of these bins is individually significant; the split is reported
because it was specified in advance, not because it resolves anything.

**Clustering.** 16 of 47 pairs carry at least one `NOSCALE` win; only 2 pairs carry wins in
both directions. The wins are spread across pairs rather than driven by two or three cells.

**What this measurement cannot carry.**

1. **The set is enriched for failures by construction** — 53 `fail` + 40 `clean`, not a fold
   sample. The fold-wide rate is ~6% failures; here it is 57%. A result driven by the `fail`
   group therefore describes a minority of production traffic, and the headline 22 : 8 is a
   number about this set, not about the fold.
2. **One reviewer**, whose threshold moved 1.72× between two sittings in
   [v3.8 RESULTS §3](../v3.8/RESULTS.md). Every judgement here is paired inside one card,
   which is the instrument that survived that — but it is still one pair of eyes in one
   sitting.
3. **The softness residue of §2** is a live alternative explanation for a preference
   expressed on resampled images.
4. **The baseline is fresh, not the archive** (different transformer *and* a different input
   bound), so this compares two rules under one pipeline rather than against the record.

**What would license changing the shipped rule:** the same paired comparison **fold-wide** —
all 200 pairs, unenriched — so the `clean` side is measured at the size it actually matters,
ideally with a second reviewer on the discordant cells.

## 4. Question 2 — does cropping before the bald pass change anything?

`CROP2` (A4 crop → bald pass on the crop → the same head-subtracting crop) against `SCALE`,
all 93 cells, the same canvas on both sides so the crop is the only variable.

| verdict | cells |
|---|---|
| `CROP2` better | 3 |
| `SCALE` better | 6 |
| same | **84** |

**9 discordant cells of 93, p = 0.51.** And the split is cleaner than the total:

| group | n | `CROP2` | `SCALE` | same |
|---|---|---|---|---|
| `fail` | 53 | 3 | 6 | 44 |
| `clean` | 40 | **0** | **0** | **40** |

**Not one of the 40 clean cells moved at all.** Every discordant cell is in the failure
group, and there the direction mildly favours the single crop. The **[inferred]** prior in
[EXPERIMENT link 2](EXPERIMENT.md) — that a tighter crop gives klein fewer tokens rather than
more detail — survives; the reference sizes bear it out, at 0.392 MP mean for `1crop` against
0.391 MP for `2crop` across 47 garments.

The second crop is not free: it adds an A4 crop (0.15 s) and, more to the point, it is a
second pass over the same garment. The one thing it buys is a **1.9× faster bald pass**
(§1) — a cost saving on the cached, per-garment half of the pipeline, not a quality change.

## 5. Question 3 — garment-only references (product shots)

**Not in TEST.md.** Raised by Ray on 2026-09-12 after the record showed the v3.0 pipeline
*branched* on garment kind — product shots were never balded, "there is no head" — and that
`ER` has no such branch and balds everything
([`prd/PROD/OPEN_QUESTIONS.md`](../../PROD/OPEN_QUESTIONS.md) Q7).

**Set.** 10 product-only garments from `test_set1` (`g001`, `g002`, `g008`, `g010`, `g016`,
`g017`, `g021`, `g023`, `g026`, `g028` — flat-lay and ghost-mannequin), each against 3 fold
people at seeds 46/47 = **60 cards**.

**Arms.** `PROD` — the production path, bald pass then `crop_bc(cranium=True)`. `NOBALD` —
the v3.0 product route, `masks(cranium=False)` and the same subject-bbox flatten, no bald
pass at all.

| verdict | cells |
|---|---|
| `NOBALD` better | 0 |
| `PROD` better | 1 |
| same | **59** |

**59 of 60 same; p = 1.00.** The one discordant card is
`dualuse_hugh_jackman_grey_suit_outdoor+g023`@47, and it favours the production path.

**So the pipeline does not break on product shots** — which is itself the headline, because
nothing in V3 had established it. But the per-garment measurements say the bald pass is
doing real work to reach that non-result:

| garment | cranium fired | bald MAD | pixels changed >16 | `PROD` ref | `NOBALD` ref | `PROD` white | `NOBALD` white |
|---|---|---|---|---|---|---|---|
| g001 | yes | 3.98 | 3.3% | 722×767 | 718×615 | 0.599 | 0.441 |
| g002 | yes | 5.96 | 7.7% | 451×652 | 442×463 | 0.619 | 0.411 |
| g008 | yes | 5.22 | 3.9% | 589×714 | 581×568 | 0.470 | 0.309 |
| g010 | yes | 5.09 | 2.7% | 846×1024 | 843×1024 | 0.379 | 0.366 |
| g016 | yes | 4.32 | 4.7% | 642×764 | 633×645 | 0.576 | 0.477 |
| g017 | yes | 6.16 | 6.2% | 622×896 | 613×774 | 0.434 | 0.317 |
| g021 | yes | 4.28 | 7.4% | 327×807 | 319×680 | 0.372 | 0.232 |
| g023 | yes | 6.81 | 5.7% | 582×699 | 574×481 | 0.532 | 0.311 |
| g026 | yes | 6.42 | 6.7% | 1009×1024 | 1009×1024 | 0.379 | 0.366 |
| g028 | yes | 5.06 | 5.2% | 540×878 | 534×762 | 0.407 | 0.289 |

**The head-finder fired on 10 of 10 photographs that contain no person.** `cranium_used` is
true whenever the parser returns a head mask over ~40 px or a fallback produces one; it does
not record *which* route fired, so these numbers say a head-shaped region was found and
subtracted, not which model found it. That is a measurement gap in the instrument, not a
finding about the parser.

**The bald pass changed 2.7–7.7% of pixels** (mean 5.4%) at a >16/255 threshold — not JPEG
noise — with MAD 3.98–6.81 on garments that have no hair.

**And the reference geometry moves**: `PROD` references are taller than `NOBALD`'s on **8 of
10** and whiter on **10 of 10** — up to 767 px against 615 px on `g001`, and 0.532 white
against 0.311 on `g023`. The production path is producing a taller, emptier reference of the
same garment.

**What this is and is not.** As marked, it is a non-result: 59/60 same. What the metrics
describe is **wasted work and an invention surface** — a generative pass repainting ~5% of a
garment that needs no edit, on the per-garment (cached) half of the pipeline — not a quality
defect the reviewer could see. Both statements are true at once and neither is the other.

**What this cannot carry.** 10 garments, 3 people, 2 seeds, one reviewer; product shots that
are all clean studio imagery on white; and the reviewer marked 59 cards *same*, which is also
what an insufficiently discriminating instrument returns.

## 6. Question 4 — the ONNX crops on the GPU: **no evidence**

The inquiry notebook's §5 and §6 probe the `onnxruntime-gpu` provider, assert both sessions
report `CUDAExecutionProvider`, time GPU against CPU, and compare GPU crops against the CPU
references of record at MAD ≤ 4.0 (BUILD §7.3's T1). **None of it reached a file.** The
output was printed to the notebook and the session was released; the zip carries no provider
record, no timing and no parity number.

**The only trace is the timing table**, and it points the other way: `headcrop` ran at a
**median 16.8 s** (mean 16.29 s) per reference, against v3.5's measured **15.8 s on CPU** and
a GPU path that section reports as ~6× faster. On those numbers the crops in this run were
**on CPU**.

This inquiry is **unresolved**. It is not a pass, and the 16.8 s is evidence against, not
for. Re-running it costs a few crops and no generation.

## 7. Evidence paths

| what | where |
|---|---|
| marks (221 cards, 220 marked) | `v3/testsets/inquiry_marks.csv` |
| page and its builder | `v3/report/inquiry.html`, `v3/build/inquiry_page.py` |
| run outputs | `v3/runs/inquiry/a100/{v39,inquiry}/`, bundle `inquiry_20260912_0620.zip` |
| run facts, canvases, per-stage timings | `v39/meta/cost_v39.json`, `v39/meta/v39_meta.json`, `v39/meta/timings_v39.csv` |
| garment-only per-garment measurements | `inquiry/meta/garment_only.json` |
| the set | `v3/colab/v39_set.csv`, built by `v3/build/make_v39_set.py` |
| notebook | `vp/inquiry_confirmation.ipynb` |
