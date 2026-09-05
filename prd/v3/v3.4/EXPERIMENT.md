# v3.4 — EXPERIMENT

**Status: open — links A–F run, G staged. F (2026-09-05, negative): Lanczos inputs lose the g027 framing 3/3 and the placket appears at every scale — call-1 regeneration, not scaling, is the drift channel. G = arm `VS` (SR inputs; fal priors: s50 "very good", first-ever `p019+gal_gadot` success) awaits its A100 run; then the canvas call and select-from-N (§0). Opened 2026-08-31.** One question:

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

## The test set

The **v3.3 failure set** — the 31 pairs on which v3.3 had a failing cell, with their
classes — is the matrix for every early link ([TEST.md](TEST.md)). It is selected on
failure, so it can show whether a change *reaches* the failures; only the full matrix can
say what it costs elsewhere.

## The chain

### A — Does removing the ankle cut change the failures? **← run on fal, negative**

**Why.** The reviewer's request. The cut was adopted as a general measure on a null probe
([v3.3 RESULTS §9.1](../v3.3/RESULTS.md#91-probe-results--g013-g012-4-reference-calls-10-edits-0-failures));
the iron-man losses include references whose footwear and lower pieces went missing
(`peacoat`'s boots, F3), and the cut is one of two things that could have removed them
(the re-pose is the other). This is the cheapest way to separate them.

**How.** Arm `Vnc` — the locked version with the ankle cut removed and nothing else
changed — on the 31 failure pairs at seeds 46/47/48, self-hosted, reusing the iron-man
inputs and crops. Notebook cell 10; `v3/colab/lib/run_ironman.py` arm `Vnc` (the uncut
reference is now also saved for `V`, as `{g}__V_uncut.jpg`). 31 references + 93 edits,
~5 min of A100.

**What counts.** Per cell, v3.3 (`V`) beside `Vnc`: did the cell's failure go, stay, or
change class. Footwear on the reference is the thing to look at first.

**Result. No.** Run on fal at the reviewer's request (22 references, 186 edits, three
seeds). `V` and `Vnc` share every pixel but the feet, and **every failure class is
identical between them** — the kimono sleeves, the skirt-as-trousers, the colour drift
are all upstream of the cut. The only visible difference is footwear on a few cells: with
the cut the wearer keeps their shoes, without it the reference's come along. The cut stays
in the lock; footwear is a product decision. → [RESULTS §1](RESULTS.md#1-link-a--the-ankle-cut-removed-on-the-failure-set-2026-08-31)

### B — Is fal more consistent than the self-hosted model? **← run on 30 controls, no**

**Why.** Link A's rescues on a failure-selected set could be a better sampler or a fresh
draw. Thirty clean control pairs (no failing cell at any seed on the A100), the same
version without the cut, on fal at three seeds.

**Result.** fal fails **~5% of the control cells** the A100 passed — the wearer's shorts
surviving under trousers, a dress hem showing under a slip dress — the same rate and the
same class (F1) as the A100 on the fold, on different cells. **fal is a different draw
of the same model, not a better one.** Reference preprocessing is not worth chasing on
this evidence. → [RESULTS §2](RESULTS.md#2-link-b--fal-on-30-clean-controls-is-fal-more-consistent-2026-08-31)

### C — A fresh A100 draw at new seeds, no ankle cut **← run, closes the question**

**How.** `v3/colab/v34_a100.ipynb`: failure set and controls, seeds 49/50/51, 219 calls
at 1.94 s, ~CAD 0.08.

**Result.** The A100 at new seeds does what fal did: rescues ~85% of the failure set,
leaves the same four seed-stable pairs failing (plus `p025 + zendaya`), and creates new
F1 leaks on ~5% of clean control cells. **Three draws agree: the failure rate is the model
sampled on hard pairs, not a backend or a seed.** → [RESULTS §3](RESULTS.md#3-link-c--the-a100-at-new-seeds-no-ankle-cut-failure-set--controls-2026-09-01)

### D — Does fal's call-2 canvas change the failures? **← run 2026-09-04; [RESULTS §5](RESULTS.md#5-the-v34-version-and-link-ds-set-up-2026-09-01)**

**Why.** The deep dive ([RESULTS §4](RESULTS.md#4-deep-dive--what-is-different-between-our-klein-and-fals-2026-09-01))
found the one code-level difference that survives reading both implementations: we size
call 2 to image 1 at ≤1.15 MP / floor 16 / no upscale; fal renders at area 1024² / floor
32 / up or down. Above 4,300 tokens the distilled model's sigma schedule switches (38 of
200 of our outputs crossed it); below, we render small persons on far fewer tokens than
fal. Everything else — guidance, steps, encoding, prompt length, position ids — is the
same on both paths.

**How.** The reviewer adopted the canvas into **the v3.4 version** (arm `V34` = no
ankle cut + fal's canvas on call 2; [RESULTS §5](RESULTS.md#5-the-v34-version-and-link-ds-set-up-2026-09-01)).
`v3/colab/v34_a100.ipynb` now runs exactly that: `V34` on the failure set at the link-C
seeds 49/50/51, so the canvas is the only variable against link C. ~3 min of A100.

**Result ([RESULTS §5](RESULTS.md#5-the-v34-version-and-link-ds-set-up-2026-09-01)).**
≥fal on 85/93 cells by the reviewer's three-way marks; 29/31 pairs pass at ≥1 seed. One
canvas-suspect regression, `g027+p003` (worse at all 3 seeds, proportion compression);
diagnosed in [RESULTS §6](RESULTS.md#6-the-g027p003-dwarfism-diagnosed-2026-09-04) as a
framing-retention failure on a waist-up person — the remaining difference vs fal is
**call 1's canvas** (fal's reference 0.91 MP, ours 0.24 MP). → link E.

### E — References at ~1 MP (call 1 on the fal canvas) **← the dwarfism follow-up**

Klein research (2026-09-04, sourced in §E-notes below) supports the reference side:
the diffusers pipeline **never upscales** a sub-1 MP reference (only downscales >1 MP
to 1 MP), a diffusers maintainer states references were likely **trained at 1 MP**, and
references share absolute (H,W) RoPE coordinates with the output canvas — a small
reference occupies a short corner of the grid, and FLUX.1 Kontext (same conditioning
paradigm) has a documented "big head / short legs" failure on cropped-input →
full-body-output cases. Arm: call 1 rendered on the fal canvas (references ≈1 MP, as
fal does), call 2 as `V34`. Failure set beside `V34` at 49/50/51. **Wired 2026-09-04:
arm `VE`** in `run_ironman.py` (`FAL_BOTH_ARMS`); `v3/colab/v34_a100.ipynb` runs it as
staged; page `v34_a100_page.py <dir> --arm VE` → `VE` · original · link-D `V34` · fal.
Prediction:
`g027+p003` recovers the waist-up framing; risk: reference regressions elsewhere, since
every scored run used ~0.5 MP-or-less references.

**Result ([RESULTS §7](RESULTS.md#7-link-e--references-at-1-mp-run-and-voted-2026-09-04)).**
Prediction confirmed — `g027+p003` to `VE` at all three seeds. Fold-wide the vote is
68 tie · 13 `V34` · 8 `VE` · 4 original: a targeted fix, not a general win. The canvas
fork (V34 base + VE in select-from-N, vs a conditional upscale, vs VE flat) is the
reviewer's call; recommendation recorded in §7.

**§E-notes — klein research of record (2026-09-04).** Settings: klein 4B is step- and
guidance-distilled to **4 steps**; the official CLI hard-fixes `steps=4, guidance=1.0`,
and the 4B checkpoint has **no guidance embed** (`use_guidance_embed: False`) — our
`guidance=0` vs `1` is bit-identical, not a knob. Schedule: `compute_empirical_mu`
counts **output tokens only** (reference tokens don't enter mu), confirming the §4
canvas reasoning. Teacher: size-distilled from the 32B FLUX.2 base; method undisclosed,
no tech report. Community (not measured here): steps 4→6–8 improves anatomy on the
distilled model; true CFG ≈1.2 with a negative helps limbs but needs bypassing the
`is_distilled` gate; fal's own klein try-on prompt template ends "The final image is a
full body shot." Sources: HF model card + BFL flux2 repo (`util.py`, `model.py`,
`sampling.py`), diffusers `pipeline_flux2_klein.py` + issue #13349, FLUX.1-Kontext-dev
discussion #23, fal klein guides, myaiforce.com anatomy post.

### F — All scaling algorithmic (arm `VA`) **← wired 2026-09-04; the decided rule**

**Why.** Link E's win came with a cost: klein's generation-upscale hallucinates garment
structure on small crops ([RESULTS §7.1](RESULTS.md#71-the-reference-hallucination-verified-2026-09-04)
— `p004`'s buttonless tee grows a two-button placket at ×2.67). The reviewer's rule:
**klein never scales** — every input is resized to ~1 MP by an algorithm (Lanczos up,
INTER_AREA down) *before* its call, so the render canvas always matches the
conditioning. Soft-but-faithful evidence at every grid position, no invented detail.

**How.** Arm `VA` in `run_ironman.py` (`ALGO_ARMS`, `to_1mp()`): the A4 crop is
pre-scaled before call 1, the person before call 2; both calls on the fal canvas rule
(which now ≈ the input's own size). `v3/colab/v34_a100.ipynb` runs it on the failure
set at 49/50/51 — cell-for-cell against `VE` (link E) and `V34` (link D). Page:
`v34_a100_page.py <dir> --arm VA` → `VA` · `VE` · `V34` · original · fal, winner vote
per row.

**What counts.** `g027+p003` (does the framing fix survive honest conditioning?),
`g029+p004` (does the hallucinated placket go?), and the 13 cells `V34` won off `VE`.

**Result. Negative on both counts** ([RESULTS §7.2 first reads](RESULTS.md#72-vs-on-the-marked-failures-fal-2026-09-05)
carry the diagnosis): the A100 loses the `g027+p003` framing 3/3 (the Lanczos-softened
person anchors worse than `VE`'s native one), and the placket appears at every scale —
call-1 regeneration, not scaling, is the drift channel. Lanczos retires; → link G.

### G — SR-scaled inputs (arm `VS`) **← wired 2026-09-05; the A100 run decides**

**Why.** The dilemma after F: blurry algorithmic inputs lose, klein's own upscale
hallucinates. A dedicated SR model (realesr-general-x4v3, 1.2M params, 4.9 MB, tens of
ms on the A100 — in the bundle) is the middle: sharp, structure-conservative,
algorithmic. fal-draw priors ([RESULTS §7.2](RESULTS.md#72-vs-on-the-marked-failures-fal-2026-09-05)):
the s50 cells read very good, and **the first-ever success on `p019+gal_gadot`** — no
passing cell in v3.3, links A–F, or fal's own draws before it.

**How.** Arm `VS` = `VA` with the upscaler swapped to SR (`to_1mp_sr`; the `sr` stage
is timed into `timings.csv`). `v3/colab/v34_a100.ipynb` runs it on the failure set at
49/50/51; page `v34_a100_page.py <dir> --arm VS` → `VS` · `VA` · `VE` · original · fal,
winner vote per row.

**Result.** *Pending.*

### 0 — Select-from-N **← next after D; cheapest, largest**

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

## What is decided

**No ankle cut in v3.4 — decided by the reviewer 2026-09-04, independent of the canvas
outcome.** This reverses the lock's product choice on footwear (link A: cut = wearer
keeps their shoes; no cut = the reference's shoes come along — v3.4 chooses the
latter). The cut stays in arm `V` for baseline comparability only. **The canvas rule is
NOT decided**: `V34` (call 2 at 1 MP) vs `VE` (both calls at 1 MP) awaits link E.

**Scaling is algorithmic — decided by the reviewer 2026-09-04, after §7.1.** Klein
never upscales: every input is resized to ~1 MP by an algorithm (Lanczos up,
INTER_AREA down) before its call, so the render canvas always matches the
conditioning. Raw photographs were already algorithmic-only (`normalise`: INTER_AREA
down to 1.15 MP, small images untouched); the generation-upscale in `VE`'s call 1 was
the only violation. Arm `VA` (link F) implements the rule; `VEi` (§7.1) is superseded.
