# v3.9 — EXPERIMENT

**Status: open — set up 2026-09-11, amended the same day, not yet run.** Two questions the
shipped pipeline (`ER`, [v3.8](../v3.8/SOLUTION.md)) inherited rather than tested, raised by
Ray while specifying production ([`prd/PROD/OPEN_QUESTIONS.md`](../../PROD/OPEN_QUESTIONS.md)
Q1 and Q2(a)). The matrix is [TEST.md](TEST.md); `RESULTS.md` is written when the marks exist.

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

### 1 — Does call 2 need to scale the person *up* to 1 MP? **← set up**

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

**Result.** Pending.

### 2 — Does cropping before the bald pass as well change anything? **← set up**

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

**Result.** Pending.

---

## What decides each question

For each arm, the paired marks split into *arm better*, *baseline better*, *same*, *both bad*,
per group. **An arm is adopted only if it wins on the fail group without losing on the clean
group** — the clean group is the one that decides whether a change ships, as in v3.8. A result
of mostly *same* closes the question in favour of what ships.

A second reading comes free on question 1: the marks join to each cell's canvas area, so "does
the upscale matter" can be read against *how much* upscaling the cell had.

## Conclusion

Not reached.
