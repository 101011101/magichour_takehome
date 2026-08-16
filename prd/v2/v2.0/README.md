# v2.0 — Choosing the editing base

**Status: closed.** Decided 2026-08-14: **FLUX.2 klein 4B distilled** is the
editing base. The decision and its full reasoning are recorded program-level in
[../results_summary/V2.1_RESULTS.md](../results_summary/V2.1_RESULTS.md); the
evidence behind it is [../results_summary/V2.0_RESULTS.md](../results_summary/V2.0_RESULTS.md).

> **These documents were reconstructed on 2026-08-15, after the runs.** v2.0 was
> executed before the workstream document schema existed, so `EXPERIMENT.md`,
> `PLAN.md` and `TEST.md` here are written from the harness, the scoreboards and
> `CONDITIONS.md` rather than *before* the runs they describe. They are accurate
> as a record and are **not** a pre-registration. Nothing was rerun to produce
> them. Where a criterion was applied but never written down in advance, it says
> so.
>
> Every later workstream (v2.1 onward) has genuine pre-run documents.

**Owner:** Ray. **Ran:** 2026-08-13 to 2026-08-14. **Cost:** ≈ $3.5 fal +
$2.3 judging.

## What this workstream was

The first V2 question, and the one everything else is conditioned on: **of the
open-weights image editors that can do garment transfer at all, which one do we
build the product on?**

V1 shipped a Seedream 5 Lite → Qwen cascade. Seedream is closed-weights, so the
V1 winner is ineligible under the V2 constraint (deployed path must be
self-hostable open weights). The pipeline had to be rebuilt from a new base, and
nothing carried over except the test methodology.

| Doc | What it holds |
|---|---|
| [EXPERIMENT.md](EXPERIMENT.md) | The question, the hypotheses each candidate represented, and what would count as an answer |
| [PLAN.md](PLAN.md) | The two-bucket architecture, why editing and realism are separate stages, and the harness built to run the comparison |
| [TEST.md](TEST.md) | The three runs: triage on `test_set/`, the auxiliary screen, and the Testset2 arm comparison |
| [RESULTS.md](RESULTS.md) | What was found and what was decided, with pointers to the program scoreboards |

## Outcome in one line

Four editors were screened, two eliminated on evidence (FireRed on garment
transfer, HiDream on scene reframing and identity substitution), and the
FASHN-vs-klein contest was resolved in klein's favour on the ×2-weighted garment
objective — accepting three known klein downsides that became workstreams
[v2.1](../v2.1/), [v2.2](../v2.2/) and [v2.3](../v2.3/).

**How this fits:** program-level decisions and the cross-workstream scoreboard
live in [../results_summary/](../results_summary/). Scoring definitions are in
[../SCORING_CRITERIA.md](../SCORING_CRITERIA.md). The dated record of what was
done each day is [../RESEARCH_LOG.md](../RESEARCH_LOG.md).
