# v3.9 — EXPERIMENT

**Status: concluded 2026-09-12 — two answers, one negative, one unresolved.** Two questions the
shipped pipeline (`ER`, [v3.8](../v3.8/SOLUTION.md)) inherited rather than tested, raised by
Ray while specifying production ([`prd/PROD/OPEN_QUESTIONS.md`](../../PROD/OPEN_QUESTIONS.md)
Q1 and Q2(a)) — and, added after the matrix was written, two more raised the same week: whether
product-only garment photographs survive the pipeline, and whether the ONNX crops run on the
GPU. The matrix is [TEST.md](TEST.md); cases, numbers and the failure modes of every
measurement are in [RESULTS.md](RESULTS.md).

**Run 2026-09-12** inside `vp/inquiry_confirmation.ipynb` — the production notebook, which
carries the v3.9 arms plus the two later inquiries. 348 klein calls, 18.15 min, CAD 0.208, on
an A100 and on the **Photoroom transformer** v3.8 locked for production. Marks
`v3/testsets/inquiry_marks.csv`; page `v3/report/inquiry.html`, 221 cards, 220 marked.

**Everything is bounded to 1 MP.** Ray's amendment: *"just have it so that it is hard limit of
<=1mp instead of 1.15 for this test and no upscaling vs upscaling."* Every photo in this run is
re-normalised to ≤ 2²⁰ px rather than v3lib's 1,150,000, and the A4 crops are recomputed from
the bounded photos, so nothing anywhere in the run exceeds 1 MP. The question left standing is
then exactly one thing: whether call 2 should scale a smaller photo **up** to 1 MP.

**Everything runs on the production transformer** — Photoroom's `transformer_bf16` with BFL's
text encoder, VAE, scheduler and tokenizer, both pinned — including a **fresh `SCALE`
baseline**. The baseline is rebuilt rather than read from the v3.8 archive for two reasons: the
archive is on BFL's transformer, and its inputs are 1.15 MP. Either alone would put a second
variable in every cell.

---

## The chain

### 1 — Does call 2 need to scale the person *up* to 1 MP? **← landed; significant, and not actionable**

**Why it is open.** `ER`'s call-2 canvas is fal's rule: area 2²⁰, aspect kept, up **or** down,
floor 32. The "down" half is load-bearing — the distilled schedule branches at 4,300 tokens
([v3.4 RESULTS §4.2](../v3.4/RESULTS.md)) — and the 1 MP bound here satisfies it by
construction. The "up" half was adopted to match fal's token count on the V arms (link D,
[§5](../v3.4/RESULTS.md)), has never been isolated, and was never tested on `BC` or `ER`: iron
man 2 put `BC` on it by the fairness rule and `ER` inherited it.

**How.** `SCALE` (the rule of record) against `NOSCALE` (the photo's own size, floor 32, never
upscaled) on the same cell, same reference, same seed, blind and paired. Under the 1 MP bound
`NOSCALE` never scales at all, so it is exactly *"≤ 1 MP and otherwise untouched"*. Cells where
the two rules give the same canvas are no-ops and are not generated. → [TEST.md](TEST.md)

**Prior from the record.** The old rule's small canvases rendered people on 2,300–4,000 tokens
where fal renders ~4,000; fal's blind-judge edge was identity/scene, not garment, and inside
seed noise ([v3.4 RESULTS §4.4](../v3.4/RESULTS.md)). Expect small differences, concentrated on
the smallest photos — `NOSCALE`'s canvas is 0.57–0.85 of `SCALE`'s in area on the cells where
they differ.

**Result. The shipped rule loses on the failure set, and the result does not generalise
past it.** 22 : 8 for `NOSCALE` on 30 discordant cells, two-sided exact **p = 0.016** — but
split by group it is `fail` **20 : 3** (p = 0.0005) and `clean` **2 : 5** the other way, at a
sample that cannot resolve the reversal. v3.8's rule is that an arm ships only if it wins on
`fail` *without losing* on `clean`; `NOSCALE` wins the first half and leaves the second
unresolved. The effect is also not ordered by how much upscaling a cell had — it is weakest
where the upscale is largest — which is the opposite of the mechanism it would need.
→ [RESULTS §3](RESULTS.md#3-question-1--does-call-2-need-to-scale-the-person-up-to-1-mp)

**What it costs to not upscale, free of any reviewer:** `NOSCALE`'s edit runs **1.92 s against
2.31 s**, ~17% faster, being the arithmetic of a 0.70× canvas.

**Next: the fold, unenriched.** This set is 57% failures by construction against ~6% in the
fold, so a result carried by the `fail` group describes a minority of production traffic. The
same paired comparison over all 200 pairs, ideally with a second reviewer on the discordant
cells, is what would license changing the shipped canvas rule. Until then the rule of record
stands.

### 2 — Does cropping before the bald pass as well change anything? **← landed, negative**

**Why it is open.** `ER` crops once: the bald pass runs on the uncropped normalised photo, and
the head-subtracting crop comes after it (`run_ironman.py:249`). Cropping first — a BiRefNet
subject crop, then the bald pass on the crop, then the same head-subtracting crop — has never
been run. The nearest arm, `BCA4`, keeps the head and answers a different question
([v3.3 RESULTS §13–14](../v3.3/RESULTS.md)).

**How.** `CROP2`: `v3lib.crop_a4` on the bounded photo → bald pass on the crop → the same
`crop_bc` → call 2 on `SCALE`'s canvas, so the crop is the only variable. Paired against
`SCALE`, blind, with both references on the card.

**Prior.** **[inferred]** Little change: the call-1 canvas is never upscaled, so a tighter crop
gives klein fewer tokens rather than more detail, and the reference's garment pixels come from
the post-bald crop either way. The one plausible lever is that klein sees less background and
less of the frame during the bald edit.

**Result. No difference, and the prior holds.** 84 of 93 cells marked *same*; 9 discordant,
3 : 6 mildly favouring the single crop, **p = 0.51**. **Not one of the 40 clean cells moved at
all** — every discordant cell is in the failure group. Reference sizes bear the prior out:
0.392 MP mean for one crop against 0.391 MP for two.
→ [RESULTS §4](RESULTS.md#4-question-2--does-cropping-before-the-bald-pass-change-anything)

**The question is closed.** The second crop is not adopted. It does buy a **1.9× faster bald
pass** (0.85 s against 1.61 s) — a saving on the cached per-garment half, available later as a
cost optimisation on its own merits, not as a quality change.

### 3 — Do garment-only photographs survive the pipeline? **← added 2026-09-12, landed**

**Why it was opened.** The record showed the v3.0 pipeline *branched* on garment kind —
product shots were never balded, "there is no head" — and that **`ER` has no such branch and
balds everything**. Every garment in the 200-pair fold is worn by a person, so nothing in V3
had ever established what the shipped path does with a flat-lay.

**How.** 10 product-only garments from `test_set1`, flat-lay and ghost-mannequin, against 3
fold people at two seeds: `PROD` (bald pass → head-subtracting crop) against `NOBALD` (the
v3.0 product route, no bald pass), 60 cards, blind and paired.

**Result. They survive: 59 of 60 marked *same*.** The one discordant card favours the
production path. Product shots are usable, which is the answer to the question as asked.
→ [RESULTS §5](RESULTS.md#5-question-3--garment-only-references-product-shots)

**But the pipeline is doing real work to reach that non-result.** The head-finder fired on
**10 of 10** photographs containing no person; the bald pass changed **2.7–7.7%** of pixels
(mean 5.4%, above a >16/255 threshold) on garments with no hair; and the resulting references
are taller on 8 of 10 and whiter on 10 of 10 than the no-bald route. That is **wasted compute
and an invention surface on the per-garment half of the pipeline**, not a quality defect a
reviewer could see. Both are true; neither is the other.

**Next, and it is a product decision rather than an experiment:** whether to restore v3.0's
branch — route a garment photograph with no person around the bald pass — trading a saved
call per product garment against a code path that must classify the input correctly. The
marks say nothing forces it; the metrics say it is free money if the classifier is reliable.

### 4 — Do the ONNX crops run on the GPU? **← added 2026-09-12, no evidence**

**How.** The notebook probes the `onnxruntime-gpu` provider, asserts both sessions report
`CUDAExecutionProvider`, times GPU against CPU, and checks GPU crops against the CPU
references of record at MAD ≤ 4.0.

**Result. Unresolved — nothing was saved.** The output printed to the notebook and the
session was released; the bundle carries no provider record, no timing and no parity number.
The only trace is the stage table, and it points the other way: `headcrop` ran at a **median
16.8 s**, against v3.5's **15.8 s on CPU** and a GPU path ~6× faster. On that evidence the
crops ran on CPU. → [RESULTS §6](RESULTS.md#6-question-4--the-onnx-crops-on-the-gpu-no-evidence)

**This is not a pass.** It is a re-run — cheap, since it is a few crops and no generation —
and it must write its verdict to a file.

---

## What decides each question

For each arm, the paired marks split into *arm better*, *baseline better*, *same*, *both bad*,
per group. **An arm is adopted only if it wins on the fail group without losing on the clean
group** — the clean group is the one that decides whether a change ships, as in v3.8. A result
of mostly *same* closes the question in favour of what ships.

A second reading comes free on question 1: the marks join to each cell's canvas area, so "does
the upscale matter" can be read against *how much* upscaling the cell had.

## Conclusion

*Reached 2026-09-12.* **Nothing in the shipped pipeline changes on this evidence, and two of
the four questions are closed.**

- **The canvas rule stands, under protest.** Not upscaling won 22 : 8 overall and 20 : 3 on
  the failure set — but lost 2 : 5 on the clean cells, on a set built 57% failures against the
  fold's ~6%, judged by one reviewer, on images a fixed display width makes softer rather than
  smaller. That is enough to make the rule an open question and not enough to change it. The
  fold-wide paired run is specified in link 1 and is the cheapest remaining lever on quality.
- **The second crop is closed, negative.** 84 of 93 *same*, zero movement on every clean cell.
- **Product-only garments work**, and the bald pass they get is measurable waste rather than
  measurable harm. Restoring v3.0's branch is a cost decision.
- **The GPU inquiry produced no evidence and must be re-run**, writing its verdict to disk.

**The honest shape of the headline.** The one statistically significant result here — 22 : 8,
p = 0.016 — is also the one this set is least able to support, because it lives almost
entirely in a failure group the set deliberately over-samples. v3.8's own lesson was that a
number which cannot survive its instrument is not a result; this section states the number and
declines to act on it, for the same reason.
