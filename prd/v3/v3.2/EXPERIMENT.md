# v3.2 — EXPERIMENT

**Status: concluded 2026-08-27 — negative, no solution.** One sub-investigation, one behaviour: **does running the klein edit
twice recover what PHEAD loses by skipping the bald pass?**

Post-synthesis conclusions only, per [SCHEMA.md](../SCHEMA.md). Cases, numbers and
method are in [RESULTS.md](RESULTS.md); the matrix is [TEST.md](TEST.md); shared ground
is [INVESTIGATION.md](../INVESTIGATION.md).

---

## Why this arm

The two-call budget is currently spent as *bald pass → edit*. [v3.0 link 3](../v3.0/EXPERIMENT.md#3-is-the-bald-pass-net-negative-where-hair-damage-is-low)
says the bald pass is at least sometimes net-negative: it re-renders the reference,
softens its edges, and the softened edge is what klein copies. PHEAD — the same cropper
on the *raw* reference, no generation — was in V2 the free arm that tracked BC_klein on
low hair damage and fell over on high damage (63% / 21% overall against BC's 74% / 5%,
`prd/v2/v2.2/RESULTS.md` §PHEAD).

That leaves one call unspent. v3.2 spends it on **the same edit again**: the pass-1
output goes back in as image 1, against the same raw crop, same prompt, same seed.
Nothing about the reference changes; the only thing the second pass sees differently is
a person who is already mostly wearing the garment.

Two things this could do, and they are distinguishable by eye:

1. **Complete the transfer.** Where pass 1 lands in *questionable attention* — right
   garment, half-resolved — a second pass starting from a target that already carries
   the garment's low-frequency layout has only fine detail left to move. That is the
   hope.
2. **Compound the copy.** Where pass 1 fell into *over-attention* — cut line as collar,
   hair fringe as hem — the second pass re-copies the same boundary onto a target that
   now agrees with it. Identity and background, protected only by the prompt, take a
   second round of drift. That is the risk, and the mechanism in
   [INVESTIGATION.md §3.1](../INVESTIGATION.md#31-image-2-is-not-conditioning-it-is-clean-tokens-in-the-same-attention-sequence)
   predicts it rather than the first.

And one thing it cannot do: a pass-1 *no-op* (failed attention, the output is the
input) hands pass 2 the identical problem. `p023`-class references are expected to
no-op twice.

## The chain

### 1 — What does the second pass change, and in which band?

**What is being investigated.** Over the 28-pair run-B fold, the three arms
**BC_klein** (bald → crop → edit), **PH** (raw crop → edit, one call) and **PH2** (PH
output → edit again, two calls), scored on the V2 ternary with a band tag on every
non-perfect. Hypotheses, stated so they can fail:

| # | hypothesis | what would confirm it |
|---|---|---|
| H1 | PH2 ≥ PH on every set — the second pass never makes a usable output unusable | zero PH `perfect`/`ok` that become PH2 `fail` |
| H2 | The second pass moves *questionable* to *perfect* and leaves *over-attention* where it is | PH→PH2 upgrades concentrated in the questionable band |
| H3 | Identity/background drift accumulates: PH2 loses on the person side what it gains on the garment side | PH2 marked down for the person where PH was not |
| H4 | PH2 matches BC_klein on low hair damage and still trails it on high | per-set ternary against `hair_frac` from `test_set3/manifest.csv` |

**How.** 28 PH edits + 28 PH2 edits, 56 klein calls, ~$0.84. Same fold, seed, prompt
and resolution as every other run-B arm, so BC and QX outputs already on disk are the
comparison. → [TEST.md](TEST.md). Evidence → [RESULTS.md](RESULTS.md).

**Result.** **Unusable across all 28 pairs.** PHEAD's issues persist through the second
pass and are not corrected by it: a copied cut boundary is copied again, a half-resolved
garment stays half-resolved, a no-op no-ops twice. The second call buys nothing, because
the reference — the thing that was wrong — is the same file both times, and pass 1's
output is a worse starting point than the original photo rather than a better one.
→ [RESULTS §2–3](RESULTS.md#2-verdict)

---

## Conclusion

**Negative. No solution; no `SOLUTION.md`.** Running the klein edit twice on a PHEAD
reference does not recover what skipping the bald pass loses. Defects in the reference
are persisted by a second pass, not repaired — the second call has to change the
*reference*, not re-run the edit. That closes "iterate the edit" as a way to spend call 2
and leaves the two candidates already on the table in
[v3.0](../v3.0/EXPERIMENT.md#conclusion): prepare the reference differently, or replace
it by regeneration.
