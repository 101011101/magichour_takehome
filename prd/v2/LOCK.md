# V2 — locked

**Frozen 2026-08-23 at `v2.0.0`.** No further work lands in V2. What is here is
complete, measured, and implemented as an installable package. V3 starts from a
different premise and is tracked separately in [`prd/v3/`](../v3/README.md).

This document says exactly what is frozen, what is *known to be wrong inside it*, and
why the freeze happened rather than a fix.

---

## 1. Why V2 is frozen rather than finished

V2 answered its own question and then answered a second one it did not ask.

The question it set out to answer — *can an open-weights stack match the closed V1
cascade?* — is answered yes. The pipeline is **31 perfect / 7 ok / 0 fail over 38
sets** at 2.158 generations, every model under a commercial licence, nothing closed in
the deploy path.

The second answer is the reason for the freeze. Measured against the harness, the
**strongest single arm alone** — flat BC_klein, two calls, no router, no gate, no
VLM — is **28 / 6 / 4 at 2.000 generations**. The harness buys **four failures**
for 0.158 generations and the entire routing, gating and escalation surface.

Four failures out of 38 is a real purchase and the harness is the better system. It is
also, at this scale, most of the complexity for a small share of the quality: the
**garment crop** is worth roughly twenty points of perfection (uncropped baseline is
53% perfect / 34% fail), and everything built on top of it is worth four sets. A
production service weighs those differently than an experiment does, and the call was
made to weigh them differently.

So V2 is kept whole as the record of what was measured, and V3 rebuilds on the part
that carried the weight.

## 2. What is frozen

| | where |
|---|---|
| **Assembly spec** | [ARCHITECTURE.md](ARCHITECTURE.md) — standalone, no history |
| **Every decision, with photo evidence** | [DECISIONS.md](DECISIONS.md) |
| **Working code** | [`v2/pipeline/`](../../v2/pipeline/README.md) — `pip install -e v2/` |
| **Numbers, recomputed from data** | `v2/pipeline/tests/test_published_numbers.py` |
| **Edge cases** | [EDGE_CASE_INDEX.md](EDGE_CASE_INDEX.md) |
| **Parity status** | [PARITY.md](PARITY.md) |
| **Report** | `v2/report/` — simple, deep, failures |

The package is **29 tests, no GPU, no API key**. Three of them are regressions for
bugs that each cost a run, and the rest lock the published numbers to the CSV so a
documented claim cannot drift from its evidence.

## 3. Known wrong at the moment of freeze

Frozen does not mean correct. These are recorded rather than fixed, because fixing
them inside V2 would mean re-measuring a system that is being replaced.

1. **The router's cut-point is set too high.** Shipped at 0.14; the sweep in
   [ARCHITECTURE §9.2](ARCHITECTURE.md) shows 0.05–0.09 gives **29/6/3 at 1.55
   generations** against 0.14's 28/5/5 at 1.26 and always-BC's 28/6/4 at 2.00. At 0.08
   the router is strictly better than the strongest single arm *and* 22% cheaper. It
   is left at 0.14 because 0.08 is picked by reading the same 38 sets it is scored on,
   and the held-out recomputation over all 48 references was never run. **`config.py`
   ships 0.14; `--hair-threshold` overrides it.**
2. **The oracle over PHEAD+BC is 29/6/3, and 0.08 already reaches it.** No better
   router exists. The remaining three failures need a different arm.
3. **VLM-A is measured at 4-bit and hedges** — 331 of 570 verdicts were `OK`, which is
   what caps recall at 51%. Binary forced choice and fp16 are both untried.
4. **The named-region branch has no evidence at all.** Nothing in the test set carries
   one. It is reasoning, not measurement.
5. **n = 38, one reviewer, one seed, unblinded.**
6. **Self-hosted parity is partial.** The stack runs end to end on downloaded weights
   ([PARITY.md](PARITY.md)), but not every number in the documents was re-measured
   there. SeedVR2 in particular was never self-hosted — it needs apex, flash-attn and
   an H100-class card.
7. **AuraFace runs on CPU at 16.9s** and dominates request latency whenever it is
   invoked. Moving it to GPU is owed and was never done.

## 4. What V3 inherits, and what it drops

**Carried forward — this is where the quality is:**

- The **garment crop**, and the CPU mask stack that produces it (BiRefNet_lite, SCHP
  ATR, MediaPipe Selfie Multiclass, MediaPipe Pose). ~1.9s, no GPU, no API, all
  commercially licensed. Uncropped is 53% perfect / 34% fail; cropped is 74% / 11%.
  Nothing else in the project moved the number this far.
- **BC_klein** as the single path: klein makes the reference person bald, the same
  cropper runs on the bald frame, klein does the edit. Two calls.
- **Escalate mechanism, never seed.** Failure is a property of the garment.
- **The 1 MP normalisation.** fal silently normalises to ~832×1248; generating at
  3.45 MP self-hosted cost 32% detail and 128s against 39s.
- **klein 4B distilled at 4 steps, guidance 1.0.** The 9B sibling is non-commercial.

**Dropped:**

- **The router.** Worth one perfect and one fail at its best cut-point, and it is a
  second code path to maintain. Its measurement stands; its complexity does not pay
  at production scale.
- **The VLM gate.** Only reachable to trigger QX, which is also dropped.
- **QX as an arm.** Its *anti-artefact behaviour* is the part worth having — QX
  regenerates rather than subtracts, which is why it has no shared failure mode with
  the other two and why it rescued 11 of PHEAD's 13 hard cases. V3 rolls that property
  into the single path rather than keeping it as an escalation target.
- **The realism pass.** Off by default already; V3 does not upscale.
- **The deterministic quality gate as a scorer.** AUC 0.506. Already a negative result.

## 5. Reading order for someone new

1. [ARCHITECTURE.md](ARCHITECTURE.md) — what it is, no argument
2. [`v2/pipeline/README.md`](../../v2/pipeline/README.md) — how to run it
3. [DECISIONS.md](DECISIONS.md) — why, with the photographs
4. This file — what is wrong with it
5. [`prd/v3/README.md`](../v3/README.md) — what happens next
