# v3.4 — TEST

**Status: written 2026-08-31, before any v3.4 run.**

## The failure set

`v3/testsets/v34_failures.csv` — **31 pairs**, every pair of the 200-pair iron-man matrix
on which the locked v3.3 version had at least one failing cell under the reviewer's rule
(BC klein better, or both failed, and not nudged acceptable;
[v3.3 RESULTS §14.5–14.6](../v3.3/RESULTS.md#145-second-export-0245-with-nudges-and-the-failure-taxonomy)).
Generated from `v33_ironman_votes_bca4.csv` + `key.csv` by the script in this commit; not
typed. Each row carries the failure class (`F1`–`F4`), whether the failure is seed-stable
(4 are), and the three per-seed verdicts.

| class | pairs | what it is |
|---|---|---|
| F1 | 9 | the wearer's own clothing survives where the new garment exposes it |
| F2 | 8 | skirt / dress rendered as trousers on a male or legs-apart wearer |
| F3 | 12 | the regenerated reference drifts (colour, dropped pieces, hem) |
| F4 | 2 | exposed-skin pairing |

The set is **selected on failure**, so a rate measured on it does not transfer to the
fold; its purpose is to show whether a change reaches the failures at all. Anything that
looks like a fix here is then run on the full matrix before it is believed.

## The control set

`v3/testsets/v34_controls.csv` — **30 pairs** drawn with a fixed seed (34) from the 163
pairs on which v3.3 had no failing cell at any seed. Unselected on failure, so a failure
rate measured on it *does* transfer; its job is to catch what a change costs. Carries the
three A100 verdicts per pair.

## The A100 run of record for v3.4

`v3/colab/v34_a100.ipynb` — **the v3.4 version** (arm `V34`: no ankle cut, call 2 on fal's
1024²/floor-32 canvas), the failure set, **seeds 49/50/51** — the link-C seeds, so `Vnc` vs
`V34` is a paired comparison with the canvas as the only variable. Reuses the iron-man
inputs and A4 crops from Drive. Self-hosted klein 4B distilled. Link C (`Vnc`, both
matrices, the same seeds) was run from an earlier version of this notebook.

## Held fixed

Everything in the v3.3 lock except the ankle cut (removed for every v3.4 arm at the
reviewer's decision; link A showed it neutral on the failures): A4 crop, head swap,
`PERSON_CLAUSE`, hold sentence, `E3`; seeds 46/47/48 on fal, 49/50/51 on the A100, self-hosted klein 4B distilled on an A100, the same normalised inputs
and crops as the iron-man run (the arm reuses its `run/` directory).

## Review

Unblinded — the point is to see the failure — v3.3 output beside the arm's output for
every cell of the set, with the reviewer's original verdict.
