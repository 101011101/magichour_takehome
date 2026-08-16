# results_summary — program level

Cross-workstream state: what is decided, on what evidence, and what those
decisions are conditional on. Detail stays in the workstreams.

| Doc | What it holds |
|---|---|
| [CONDITIONS.md](CONDITIONS.md) | The setup half — constraints, model pool and why each model is in it, test sets, what each evaluation layer measures. **No verdicts** |
| [V2.0_RESULTS.md](V2.0_RESULTS.md) | The arm screen: status board, three run tables, per-arm eliminations. Superseded as a scoreboard, kept as the evidence record |
| [V2.1_RESULTS.md](V2.1_RESULTS.md) | **Editing base decided — klein 4B distilled** (2026-08-14), plus the distilled-vs-base head-to-head and the auxiliary two-batch confirmation |
| [V2.2_RESULTS.md](V2.2_RESULTS.md) | **Cropping the garment reference works** — adopted into the editing path (2026-08-15) |
| [V2.1.1_RESULTS.md](V2.1.1_RESULTS.md) | klein parity on downloaded weights — **scrapped as a workstream**; the run definition and the standing risk are kept because the gate is still owed |

## How these are numbered

Two levels share the same numbers, deliberately:

| | Doc | Scope |
|---|---|---|
| **Program** | `results_summary/V2.N_RESULTS.md` | The decision and what it changes for everything downstream. Written when workstream N closes |
| **Workstream** | `v2.N/RESULTS.md` | The full per-run, per-set detail behind it |

`V2.2_RESULTS.md` → `../v2.2/RESULTS.md` is the clearest instance of the pair.
A program doc never restates the workstream's tables; it links to them.

**One exception, and it is a historical accident rather than a rule.**
`V2.1_RESULTS.md`'s headline decision — klein 4B as the editing base — is
**v2.0's result, not v2.1's**. It carries a V2.1 number because that is when it
was written down; the v2.1 workstream is image realism, and it took klein as
given. The evidence behind that decision is `V2.0_RESULTS.md` and
[../v2.0/](../v2.0/). If you are looking for how the editing base was chosen,
start at [../v2.0/README.md](../v2.0/README.md).

## Reading order

1. [CONDITIONS.md](CONDITIONS.md) — what is being tested and why
2. The `V2.N_RESULTS.md` files in order — each says what it supersedes or extends
3. The workstream `RESULTS.md` for detail on any one of them
4. [../RESEARCH_LOG.md](../RESEARCH_LOG.md) for the dated record of how the
   conclusions were arrived at, with observation kept separate from inference

## Standing conditions on every number here

1. **Parity rule outstanding** — every figure comes from fal-hosted endpoints;
   nothing has been reproduced on downloaded weights.
2. **Sample sizes are small** — 4 to 33 depending on the run. Directional
   evidence plus product judgement.
3. **Cross-kind comparison is invalid** — duo garment scores are inflated
   relative to product (CONDITIONS.md §3).
4. **The instruments have known blind spots** — a non-transfer scores 0.78 on
   garment similarity, and a no-op scores perfectly on identity preservation.
   Human review is the verdict from v2.2 onward.
