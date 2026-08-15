# v2.1 — Image realism and gloss reduction

**Status: conditional pass, parked.** Every auxiliary configuration tested
cleared the fidelity gate, and `seedvr2_x2_noise0` leads on both realism and
identity preservation. The workstream is paused rather than closed because the
one thing it was named for — **gloss / plastic skin** — is not actually solved
by the current leader (see EXPERIMENT.md, open question 1).

This workstream covers the composition **klein 4B output → auxiliary realism
model**: taking the chosen editing base's output and making it read as a real
photograph, without touching what the editing model got right.

| Doc | What it holds |
|---|---|
| [EXPERIMENT.md](EXPERIMENT.md) | Goals, what was tested, what we were looking for, and what remains open |
| [PLAN.md](PLAN.md) | Where the auxiliary stage sits, its interfaces, gates and fallbacks |
| [TEST.md](TEST.md) | The two screens that were run: config sweep, then the two-batch control design |
| [RESULTS.md](RESULTS.md) | Findings, leaderboards, and links to the artifact pages |

**How this fits:** program-level decisions and the cross-workstream scoreboard
live in [../results_summary/](../results_summary/). Scoring definitions are in
[../SCORING_CRITERIA.md](../SCORING_CRITERIA.md). Sibling workstreams: **v2.2**
(accuracy, failures, attention) and **v2.3** (artifacts) — note that artifact
removal was proven *not* to be achievable from this workstream's mechanism.
