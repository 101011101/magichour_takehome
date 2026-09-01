# v3.4 — EXPERIMENT

**Status: opened 2026-08-31, nothing run.** One question:

> **What is left on the table after v3.3, and which side of the edit is it on?**

[v3.3](../v3.3/SOLUTION.md) put the deploy path on one model and, on 200 pairs × 3 seeds,
came out at least even with bald-plus-crop at the output: 77% ties, and 73% of the
decided cells to the version ([v3.3 RESULTS §14](../v3.3/RESULTS.md#14-iron-man-scores--the-version-against-bca4-2026-08-31)).
The failure taxonomy there ([§14.5](../v3.3/RESULTS.md#145-second-export-0245-with-nudges-and-the-failure-taxonomy))
is the brief for v3.4. Post-synthesis conclusions only, per [SCHEMA.md](../SCHEMA.md).

## What v3.3 leaves open, in order of size

| | class | side | what v3.4 would try |
|---|---|---|---|
| **F1** | the wearer's own clothing survives where the new garment exposes it (sleeves, trouser legs, shoes, bags) | **person, both arms** | a person-side garment-agnostic — mask the wearer's clothing in image 1 before the edit — or a call-2 sentence that names the wearer's clothing as *replaced* |
| **F2** | skirt / dress → trousers on a male or legs-apart wearer | **person, both arms** | detector first (pose reader: knee separation, hip–knee angle, plus the reference's garment type); then whether an agnostic below the waist lets the model drape instead of tube |
| **F3** | the regenerated reference drifts — colour, dropped pieces, restructured hem | **reference, V only** | **re-pose only when the pose reader says the wearer is not neutral**; otherwise ship `MH` (head swap, garment pixels untouched). Revisit the ankle cut where footwear is wanted |
| F4 | exposed-skin pairing | person, both | detector only — v3.1 §3c.31 stands |
| F5 | wearer's headwear / bags kept | by design | product decision, not an experiment |

**The finding that reorders this list** ([v3.3 RESULTS §14.6](../v3.3/RESULTS.md#146-are-the-failures-seed-stable-mostly-not)):
27 of the 31 failing pairs pass at another seed; only 4 fail at every seed. The failure
rate is mostly variance on hard pairs. That makes **select-from-N** the first thing to
try, and the person-side work the fix for the residue.

| | | |
|---|---|---|
| **F0** | the failing cell is a seed draw, not a pair property | **N seeds + a selector** — CV gate (does the wearer's original clothing survive where the reference does not cover? MediaPipe `CLOTHES` on image 1 vs the output) or the VLM as gate. Costs N× call 2 (2 s each self-hosted); the 2-call budget becomes 2 + (N−1) edits |

## The chain

### 0 — Select-from-N **← first, cheapest, largest**

On the 31 failing pairs and 30 clean controls: 3 seeds already on disk; the question is
only the selector. A CV gate that picks the right seed on the 27 rescuable pairs without
demoting the controls is worth more than every prompt experiment in v3.3 combined.

### 1 — Where does the tie mass come from? **← free**

Before spending: over the 459 tied cells, is the output *identical* between arms (the
edit ignored the reference difference) or *different and equally good*? A pixel/embedding
distance between the V and BCA4 outputs per tied cell, on disk, no calls. If most ties are
near-identical outputs, the reference is not where v3.4's money goes.

### 2 — F3: re-pose conditionally **← reference side**

Arm `V-cond`: `MH` when the pose reader calls the crop neutral (hips level, arms at the
sides, legs together), the v3.3 re-pose otherwise. Against `V` on the F3 pairs first,
then the fold. Expected: V's wins kept, the colour and the pieces back.

### 3 — F1: a person-side agnostic **← the big one**

Image 1 with the wearer's clothing masked (MediaPipe multiclass `CLOTHES`, dilated,
flattened to a neutral) before the edit, so there is no old sleeve to keep. The boundary
problem V2 spent its time on arrives on the person side; v3.0's finding that klein copies
cut boundaries is the risk, stated in advance. Against the F1 pairs first.

### 4 — F2: the detector, then the agnostic below the waist

*Not designed yet.* Depends on link 3.

## What is held

The v3.3 lock is not reopened: its prompts, crop, ankle cut and edit sentence are the
baseline every v3.4 arm is measured against, on the same 200-pair matrix, self-hosted,
blinded, three seeds.
