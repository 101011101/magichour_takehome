# v3.5 — EXPERIMENT

**Status: OPEN, opened 2026-09-08. Link A run (references, 56 garments × 4 arms, fal, seed 46); links B–C staged.** One question:

> **What does call 1 actually have to do to the reference — and can the head come off
> instead of being replaced?**

v3.4 locked `VEi`: call 1 takes the A4 crop and *replaces the head with a mannequin head*
while re-posing the wearer to face forward, then the finished small reference is SR'd to
~1 MP ([v3.4 SOLUTION](../v3.4/SOLUTION.md)). The mannequin is doing two jobs at once, and
the lock never separated them: it removes the reference's identity so call 2 cannot borrow
it, and it is baked into the same call that does the re-pose. The incumbent `BC` removes
identity a third way — it cuts the head off with the V2 cropper and never asks a model for
a head at all — and BC's references keep the garment pixels the generator never re-drew.

So: **VEi's re-pose, BC's head removal.** That is the target shape of v3.5, and it is only
reachable if the re-pose survives without the mannequin sentence. Post-synthesis
conclusions only, per [SCHEMA.md](../SCHEMA.md).

## The three things asked of call 1, separated

| | what call 1 is asked | identity removed by | garment redrawn |
|---|---|---|---|
| `M0` | mannequin head **+** re-pose (the lock's `Q3`, verbatim) | the model | yes |
| `M1` | re-pose only — turn front-on, neutral | **nothing** (the face survives) | yes |
| `M2` | mannequin head **+** the same explicit turn sentence as `M1` | the model | yes |
| `G1` | return the clothing alone, no wearer | the person is gone | yes |
| `M1c` | `M1`, head cut off afterwards — **derived, no model call** | **a crop** | yes |
| `M0c` | `M0`, mannequin head cut off afterwards — derived, no model call | crop + model | yes |

`M1`/`M2` differ by exactly one sentence, so what the mannequin instruction costs and buys
is readable off that pair. `M0` is the incumbent re-run on the same backend, because a fal
draw and an A100 draw are not comparable ([v3.4 SOLUTION §5](../v3.4/SOLUTION.md), rule 4).
`M1c`/`M0c` cost nothing — they are a crop of an image already paid for — which is why the
head-crop idea can be tested at all without a second sweep.

## The chain

### A — can klein re-pose without being told to build a mannequin? *(run 2026-09-08)*

**How.** All 56 garments of the iron-man 2 matrix, four call-1 arms, one klein call each,
seed 46, on fal (`fal-ai/flux-2/klein/4b/distilled/edit`). The A4 crops and the per-garment
framing are **reused from the iron-man 2 run on disk** — nothing recomputed, no BiRefNet,
no MediaPipe, no GPU. The call-1 canvas is pinned to the v3.3/v3.4 rule (the crop's own
size, capped 1 MP, floor 16) through fal's `image_size`, which the v3.4 probe measured as
honoured exactly ([probe c20](../../../v3/runs/v34/probe_fal/PROBE.md)); left unset, fal
renders call 1 at ~1 MP, which is arm `VE`, not `VEi`. Runner:
`v3/build/run_v35_refs.py`. Outputs: `v3/runs/v35/linkA/`. 224 calls, $3.36.

**Result.** 224 calls, $3.36, 6.1 min. **The mannequin sentence is not what re-poses the
wearer** — `M1`, the turn sentence alone, turns every profile, walking and arms-crossed
case front-on, the backview dress included, and its garment is not distinguishable from
the lock's. `M1` keeps the wearer's head by construction, which is what `M1c` is for; the
head-subtraction mechanism is verified on it. `G1`, the clothing alone, is the one arm
that fails the garment test — it changes length and drops pieces, because removing the
wearer removes the constraint that held the garment's shape. First read only, one seed;
→ [RESULTS §1](RESULTS.md#1-link-a--the-four-call-1-arms-on-56-garments-2026-09-08).

**Next.** Whichever arms hold the garment: the derived head crop, then call 2.

### B — the head crop, and what call 2 does with it *(staged)*

**How.** The head-subtracted references through call 2, **on the 31 pairs the lock actually
failed** — `v3/testsets/v35_failures.csv`, built from the reviewer's own per-cell verdict of
iron man 2 (`v34_im2_truth.json`), 8 of them seed-stable. Call 2 is the lock's, unchanged;
the reference is the only variable. Runner: `v3/build/run_v35_edits.py`; page
`v3/report/v35_linkB.html`.

**Result (probe, 5 seed-stable pairs, seed 46, `BC`/`M0`/`M1c`, 15 calls, $0.22).** The head
crop is competitive and wins outright once: on `g005+g009` both `BC` and `M0` drop the
reference's trousers and render shorts, and **`M1c` is the only arm that produces the
full-length cream trousers**. Elsewhere it is level with `M0` and ahead of `BC` on sleeve
length, with an occasional shoulder artifact of its own. **No arm fixes the F1 class** — on
`g005+p002` and `g004+g005` the wearer's own shorts and handbag survive under all three,
which is the person-side failure v3.4 named and no reference change can reach.
→ [RESULTS §2](RESULTS.md#2-link-b--the-head-cropped-reference-through-call-2-probe-2026-09-08).

### C — the fold *(staged)*

Only if B holds: the 200-pair matrix, three seeds, blinded, against the v3.4 lock.

## What is carried in from v3.4

`F3` (the regenerated reference drifts) and the backview/extreme-pose class are the classes
this chain is aimed at — v3.4 called the latter a source-image problem no renderer fixes.
`M1`'s explicit turn is the first arm that tests that claim directly. `F1`, `F2`, `F4` and
`F5` are untouched here; select-from-N remains v4 scope.
