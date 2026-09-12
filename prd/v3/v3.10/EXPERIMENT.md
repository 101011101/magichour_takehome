# v3.10 — EXPERIMENT

**Status: OPEN.** Built 2026-09-12, not yet run. One question: **does call 2 have to scale the
person photo up to 1 MP?** The matrix is [TEST.md](TEST.md); results, when the run lands, go to
`RESULTS.md`.

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

### 1 — Is the shipped canvas rule's upscale paying for itself on cells that already work? **← built, not yet run**

**How.** All 600 cells of the iron-man-2 matrix, two arms differing only in call 2's canvas —
`SCALE` (area 2²⁰, up or down, floor 32) against `NOSCALE` (the photo's own size under a 1 MP
bound, floor 32, never upscaled) — one reference per garment, shared by both arms and taken
from the archive unchanged. 1,056 generations, ≈43 min, ≈CAD 0.50. Marked blind in one
shuffled stream with the prior verdict hidden, so a single bar covers both groups and the
split is applied afterwards. → [TEST.md](TEST.md)

**What would count.** `NOSCALE` ships if it does **not** cost on the 420 passing cells — the
bar v3.8 set for `ER` — and keeps its advantage on the 36 failing ones. If v3.9's clean-cell
reversal holds up at this size, the shipped rule stays and v3.9's headline is filed as a
failure-set artefact. A third outcome is live: both arms indistinguishable on passing cells and
`NOSCALE` ahead on failing ones, which would make the upscale dead weight and its removal worth
**~17% of call-2 latency** (1.92 s against 2.31 s, measured in v3.9).

---

*No conclusion yet: the run has not been made.*
