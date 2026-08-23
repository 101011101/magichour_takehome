# V2 — Virtual Try-On, open weights only

> **FROZEN 2026-08-23 at `v2.0.0`.** No further work lands in V2. What is frozen,
> what is known wrong inside it, and why the freeze happened rather than a fix:
> **[LOCK.md](LOCK.md)**. The working code is an installable package at
> [`v2/pipeline/`](../../v2/pipeline/README.md). The next version is
> [`prd/v3/`](../v3/README.md).

V2 was built toward deployment in Magic Hour company code. The deployed
path must be self-hostable open weights; fal endpoints are used for iteration
only. Full constraints: [results_summary/CONDITIONS.md](results_summary/CONDITIONS.md).

**Result: 31 perfect / 7 ok / 0 fail over 38 sets at 2.158 generations per request**,
every model commercially licensed. The strongest single arm alone is 28 / 6 / 4 at
2.000 — which is why V3 restarts from that arm rather than from this assembly.

## Layout

| Path | What it holds |
|---|---|
| [results_summary/](results_summary/) | **Program level.** `CONDITIONS.md` (what is tested, on what data, why) and the versioned rolling scoreboards `V2.0_RESULTS.md`, `V2.1_RESULTS.md`, `V2.2_RESULTS.md` (decisions and cross-workstream state). Its [README](results_summary/README.md) explains how the two levels of numbering relate |
| [SCORING_CRITERIA.md](SCORING_CRITERIA.md) | The two model buckets, the fidelity/realism axes, deterministic and VLM schemas, gates |
| [EXTENSION_ARMS.md](EXTENSION_ARMS.md) | Open-weights arms with no hosted endpoint — deferred, with promotion triggers |
| [RESEARCH_LOG.md](RESEARCH_LOG.md) | **Dated, append-only record** of what was done, seen and concluded each day, with observation kept separate from inference |
| [ARCHITECTURE.md](ARCHITECTURE.md) | **The assembly spec.** Standalone: what to build and how, no history, no argument |
| [DECISIONS.md](DECISIONS.md) | Why each choice was made, with the photographs |
| [LOCK.md](LOCK.md) | **What is frozen, and what is known wrong inside it** |
| [ideas/](ideas/) | Proposals not yet committed to a workstream |
| [v2.0/](v2.0/) | **Workstream — choosing the editing base.** Status: closed, klein 4B distilled decided 2026-08-14. Documents reconstructed after the runs, and labelled as such |
| [v2.1/](v2.1/) | **Workstream — image realism and gloss.** Status: conditional pass, parked |
| [v2.2/](v2.2/) | **Workstream — accuracy, failures, attention.** Status: v2.2.1 complete (cropping validated); v2.2.2 and v2.2.3 not started |
| [v2.3/](v2.3/) | **Workstream — artifacts.** Status: PRD |
| [v2.4/](v2.4/) | **Workstream — auxiliary realism, revisited.** Status: deferred by decision; README only |

Evidence lives outside `prd/`: interactive comparison pages in `v2/artifacts/`
(start at `v2/artifacts/index.html`), images/CSVs/run packages in `v2/runs/`, harnesses in
`v2/build/`.

## Workstream document schema

Every `v2.x/` directory carries the same five documents, in this order of use:

| Doc | Answers | Written |
|---|---|---|
| `README.md` | What is this workstream, what is its status | At creation |
| `EXPERIMENT.md` | What are the goals, what is being tested, what are we looking for — as falsifiable hypotheses with success criteria | Before any run |
| `PLAN.md` | The architecture and product design: where each piece sits in the pipeline, interfaces, gates, fallbacks, build order | Before any run |
| `TEST.md` | What the tests will be: test set and pair kinds, arms/configs, metrics and gates, ablation design, sample size, cost | Before any run |
| `RESULTS.md` | What was found, with the leaderboards, and links to the page in `v2/artifacts/` | After each run |

Rule of thumb: `EXPERIMENT` states the question, `PLAN` states the build,
`TEST` states the measurement, `RESULTS` states the answer. A finding that
changes program direction is promoted into `results_summary/`.

## Current state

- **Editing base: FLUX.2 klein 4B _distilled_** (`.../4b/distilled/edit`, decided 2026-08-14) — best fidelity,
  realism and garment transfer. Accepted downsides: occasional AI artifacts,
  occasional generation failure, weaker attention with multiple identities.
- **Auxiliary realism: `seedvr2_x2_noise0`** — confirmed on a control batch.
- **Composite target: klein 4B → SeedVR2**, not yet validated end to end.
- **Garment reference cropping adopted** (v2.2.1, C3.1 `no_face`): the
  uncropped baseline failed 61% of reviewed sets; C3.1 solved **75%** of those.
  *(An earlier "~94%" figure is withdrawn — it counted unjudged annotation cells
  as solved.)* See [results_summary/V2.2_RESULTS.md](results_summary/V2.2_RESULTS.md).
- **v2.2.3 harness settled**: router → PHEAD|BC_klein → QX on failure, **1.526
  generations/request, 32 perfect / 6 ok / 0 fail** over 38 sets. Assembly spec in
  [ARCHITECTURE.md](ARCHITECTURE.md), rationale in [DECISIONS.md](DECISIONS.md),
  remaining work in [TODO.md](TODO.md).

The three workstreams map onto the three accepted downsides of the chosen base:
v2.1 realism (parked, conditional), v2.2 accuracy/failures/attention, v2.3
artifacts. v2.4 revisits the auxiliary slot and is deferred behind all of them.

**v2.1.1** (klein parity on downloaded weights) is **scrapped as a workstream** —
parity is a release gate, not an experiment; it runs at the end. The notebook
cells are built and parked in §14
([results_summary/V2.1.1_RESULTS.md](results_summary/V2.1.1_RESULTS.md)).
