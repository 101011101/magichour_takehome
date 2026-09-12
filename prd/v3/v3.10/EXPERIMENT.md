# v3.10 — EXPERIMENT

**Status: CONCLUDED 2026-09-12. It yielded a change to the shipped pipeline: production stops
upscaling.** One question: **does call 2 have to scale the person photo up to 1 MP?** The
matrix is [TEST.md](TEST.md); the cases, numbers and methodology are
[RESULTS.md](RESULTS.md).

Post-synthesis conclusions only, per [SCHEMA.md](../SCHEMA.md).

---

## Why this exists, when v3.9 just asked it

[v3.9](../v3.9/EXPERIMENT.md) put `NOSCALE` — the same pipeline with the upscale removed —
against the shipped rule on 93 cells and came back **22 : 8** with 37 ties, two-sided exact
**p = 0.016**. On its face that is a result. Three things in the same marks say it cannot be
adopted on that evidence:

1. **It is a failure-set result.** Split by the cell's prior blind verdict, `NOSCALE` wins
   **20 : 3** on cells that were already failing and loses **2 : 5** on cells that already
   passed. The sign reverses.
2. **v3.8's own adoption rule forbids exactly this.** `EFR` and `EX` were refused for being
   tested where they could only help; what decided `ER` was the 121 passing cells it did not
   break ([v3.8 EXPERIMENT link 2](../v3.8/EXPERIMENT.md)). v3.9 had **31** passing cells.
3. **The effect runs backwards to its own mechanism.** If upscaling is what hurts, the harm
   should be worst where the upscale is largest. It is the opposite: `NOSCALE` wins 11 : 3
   where its canvas is 0.8 of the baseline's and only 2 : 1 where it is 0.6.

So the honest reading of v3.9 is: *something* is there on hard cells, and the cost on ordinary
cells is unmeasured. This run measures the cost.

## What this run adds that v3.9 could not

The **547 cells of the fold that both blind sweeps passed** — 420 of them comparable once the
no-ops are removed, against v3.9's 32.

| | v3.9 | v3.10 |
|---|---|---|
| cards on cells that already failed | 36 | **the same 36** |
| cards on cells that already passed | 32 | **420** (388 of them new) |

The failure side is therefore not re-asked so much as **replicated on a different reference**:
v3.9 rebuilt its references under the 1 MP bound, this run hands both arms iron man 2's
archived `__BC.jpg` untouched. Same cells, different inputs, independent draw.

## The chain

### 1 — Is the shipped canvas rule's upscale paying for itself on cells that already work? **← run 2026-09-12; the pre-registered test could not be evaluated as written**

**How.** All 600 cells of the iron-man-2 matrix, two arms differing only in call 2's canvas —
`SCALE` (area 2²⁰, up or down, floor 32) against `NOSCALE` (the photo's own size under a 1 MP
bound, floor 32, never upscaled) — one reference per garment, shared by both arms and taken
from the archive unchanged. 1,056 generations, 38.3 min, CAD 0.44. Counted, not compared: 912
cards in one shuffled stream, one image each, arm and prior verdict hidden, all marked in one
sitting. → [RESULTS §1–§3](RESULTS.md)

**Result, fold-wide.** `SCALE` **18 / 456 = 3.95%**, `NOSCALE` **12 / 456 = 2.63%**. Paired,
**17 rescues against 11 breaks**, McNemar exact **p = 0.345**. The 456 cells are the whole fold
minus the no-ops, so this carries no selection: the point estimate favours `NOSCALE` and the
sample cannot resolve a gap that size. Six net cells decide it.

**The pre-registered criterion turned out to be unanswerable.** This document said `NOSCALE`
ships if it does not cost on the 420 passing cells. It reads 3 : 10 against `NOSCALE` there
(p = 0.092) — but **that split is confounded and cannot be read as a cost**: the groups were
defined by blind sweeps made on archive outputs produced under `SCALE`, so each arm regresses
toward its own record, flattering `SCALE` on the cells it passed and punishing it on the cells
it failed. The bar was written assuming the subgroup would be readable. It is not.
→ [RESULTS §4](RESULTS.md)

**An earlier reading of this run made exactly that mistake**, treating the clean-cell column as
a measured cost and recommending the shipped rule stand. It was corrected the same day. The
correction is recorded rather than quietly fixed, because the failure mode — conditioning on a
prior measurement produced by one of the arms — is the kind that recurs.

### 2 — Is anything about the two arms clean of that confound? **← yes, and it favours `NOSCALE`**

**How.** Failure clustering by pair, computed from the marks alone, which never touch the prior
labels. → [RESULTS §5](RESULTS.md)

**Result.** `NOSCALE` has **no pair failing at every seed**; `SCALE` has **two**
(`g004+g005`, `g013+p006`). `SCALE`'s 18 failures sit on 11 pairs at 1, 2 and 3 seeds apiece;
`NOSCALE`'s 12 sit on 11 pairs, ten of them once. Under the shipped retry policy a failure with
no seed-stable pair behind it is one a fresh seed can reach, so `NOSCALE`'s residue after a
retry is smaller than its rate suggests, and `SCALE`'s is floored by two pairs no seed repairs.

### 3 — What does the canvas cost in time? **← measured, and it is the firmest number here**

**Result.** Call 2 means **2.377 s** under `SCALE` against **1.903 s** under `NOSCALE` —
**19.9% faster**, from the run's own `meta/cost_v310.json`. It is a property of rendering
fewer tokens and owes nothing to the marking.

---

## Conclusion

*Reached; concluded 2026-09-12.* **Production stops upscaling** (Ray's decision, on this
evidence).

What the decision rests on, stated exactly:

- **No fold-wide evidence of harm.** Over the whole fold minus no-ops, `NOSCALE` has the lower
  count — 12 against 18 — and the paired split is 17 : 11.
- **A ~20% latency saving** on the only per-request call, measured rather than marked.
- **Less seed-stable failure**, which is the one comparison the prior-label confound cannot
  reach, and which makes the shipped retry policy work better.

What it does **not** rest on, and should never be quoted as though it does:

- **Statistical significance.** p = 0.345. This is a directional result plus a speed benefit,
  not a demonstrated quality win.
- **The subgroup split.** Both columns are confounded ([RESULTS §4](RESULTS.md)). The
  0.71% against 2.38% on passing cells is not a measured cost, and neither is the 41.67%
  against 5.56% on failing ones a measured gain.
- **A second opinion.** One reviewer throughout, whose bar has moved 1.72× between sittings on
  these cells.

**What would strengthen it:** a second eye over the same 912 cards, or a fresh sample marked
with no prior labels in play. Either would cost a sitting and no GPU time; neither has been
done, and until one is, the honest form of this conclusion is *no harm found, a real speed
saving, adopted on that basis*.

**What it changes.** Call 2's canvas in the deployed path: the person photo's own size under a
hard ≤2²⁰ px bound, each side floored to 32, never upscaled; `MAX_RES` lowers it further. The
1 MP ceiling is untouched and still load-bearing — the schedule branch at 4,300 tokens is why
the bound exists ([v3.8 BUILD §4](../v3.8/BUILD.md)). The archive was made under the old rule,
so the byte-parity acceptance test compares against outputs that will now differ by design.

**What it does not change.** Everything else: both prompts, the reference build, 4 steps,
guidance 0.0, bfloat16, the CPU generator, call 1's seed and canvas, the retry policy.
