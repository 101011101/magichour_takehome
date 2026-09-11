# v3.5 — EXPERIMENT

**Status: OPEN, opened 2026-09-08.** Link A run (56 garments × 4 call-1 arms, fal); link B
run as a probe (5 pairs); the bald interlude run (5 longest-haired garments, fal); link C
run on the A100 2026-09-10 (51 pairs × 6 arms × 3 seeds, 918 cells). **The reviewer's pass
over link C is open**, and so is the `VEi` counting pass that the `BC` count must be set
against ([RESULTS §4](RESULTS.md#4-why-bc-may-simply-be-better--the-regeneration-tax)).
One question:

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
| `G1` | return the clothing alone, no wearer | the person is gone | yes — **and restructured; dropped at link A** |
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

### B — the head crop, and what call 2 does with it *(probe run 2026-09-08)*

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

### B2 — does one klein call re-pose *and* bald? *(run 2026-09-08)*

**Why it was asked.** `BC` bald-passes the raw photograph before it crops, because hair on
the shoulders and chest cannot be told from garment by any matte, and `VEi` gets that free —
the mannequin sentence takes the head and its hair together. A re-pose arm that keeps the
wearer's own head does neither, so cropping it leaves whatever hair spilled onto the
garment. The re-pose arm is therefore not shippable unless one call can do both.

**How.** The five garments with the most **garment lost to hair removal**, the quantity V2's
own `hair_threshold = 0.14` gates `BC_klein` on, measured off V2's crop pair
(`c32_no_face_keep_hair` minus `c3_no_face`, `v2/runs/crop_screen`); four of the five are
over that threshold. `M1q` against `M1q + a bald clause`, one klein call each, seed 46, fal.
Runner `v3/build/run_v35_bald_probe.py`; page `v3/report/v35_bald.html`.

**Result.** Yes, on all five — and the garment survives the added sentence.
→ [RESULTS §2.1](RESULTS.md#21-one-call-re-poses-and-balds-2026-09-08). `M1q` without the
bald clause was dropped as an arm on this basis; link C runs `M1qb`.

### C — VEi + head crop against re-pose + head crop, on the A100 *(run 2026-09-10)*

**Decided out of the chain: `G1` is not a candidate.** The clothing-alone path is dropped
on garment fidelity, not on cost or complexity — it returns a clean e-commerce flat and
then changes the garment: length changes (blazer → full-length coat, shirt → shirt-dress,
waistcoat + shirt → sleeveless dress) and dropped pieces (trousers gone on four of the
garments read, the tee gone under a blazer). Removing the wearer removes the constraint
that held the garment's shape, which is v3.4's placket mechanism arrived at from the other
side. It is not run again ([RESULTS §1.1](RESULTS.md#11-what-the-arms-do--first-read-2026-09-08)).

**What link C runs.** Two arms, differing by one sentence in call 1 and nothing else:

| arm | call 1 | head removed by | ankle cut |
|---|---|---|---|
| `VEic` | the lock's `Q3` — mannequin head **and** re-pose | a crop, after call 1 | no |
| `M1qc` | `Q3` **with the mannequin sentence deleted** — re-pose only | a crop, after call 1 | no |
| `VEica` · `M1qca` | as above | a crop | **yes** — v3.3's cut, reopened as its own variable |

plus `VEi` and `BC` unchanged as the two reference points, or the run cannot say whether
the crop helped. An arm name is read, not looked up: base + `c` head crop + `a` ankle cut.

**The set is the union of both failure records** — `v3/testsets/v35_linkC.csv`, 51 pairs:
20 the v3.4 lock failed, 20 v3.3 failed, 11 both. They overlap on only 11, so taking one
would miss half the hard pairs. There is **no per-cell record of a correctly built `BC`
failing** on this matrix — only the `VEi` arm was ever judged — so the v3.3 half's *both
arms failed* cells are the best BC coverage available without a fresh judging pass
([TEST.md](TEST.md)).

**The head crop is possible on both** — verified 2026-09-08, not assumed. It is the V2
cropper's own head subtraction (`phase3_variants.masks(cranium=True)` → `noface`, the exact
call `BC` makes), and it fires on a **mannequin** head as well as a real one: the human
parser returns `cranium_used=True` on the `M0` references and the head comes off at the
neck with the garment untouched. That it works on a featureless head is not luck — the
cranium path was built for `BC`'s *bald* frames, where the hair signal is absent by
construction, and it takes head **shape** from the parser and head **extent** from pose
landmarks, neither of which needs hair or a face.

**Order of operations, and why it is not the obvious one.** The crop goes **before** the
SR pass, not after: `call 1 → white-margin re-crop → head crop → SR to ~1 MP`. Cropping
after SR would take the reference back below 1 MP and break the one rule link H bought —
that what conditioning contributes is bounded by its **token footprint** in call 2
([v3.4 SOLUTION §5](../v3.4/SOLUTION.md), rule 3). A head-cropped reference is a smaller
image; it has to be re-floated to ~1 MP or the arm is testing two changes at once.

**Where it runs.** Colab, on the A100, end to end — including the crop. Every stage is
available there: BiRefNet and MediaPipe through `v3lib.fetch_models`, the human parser as
`basso4/humanparsing` `parsing_atr.onnx` off the HF hub, the pose landmarker from Google
storage, klein self-hosted, SR from the bundled `realesr-general-x4v3.pth`. On this laptop
the head crop is ~90 s an image, which is BiRefNet on an eight-year-old CPU, not the
method; on the A100 it is seconds.

**Result.** Run 2026-09-10: 645 klein calls, 36.8 min, $0.42; 918 cells over six arms,
the parser fired on 33/33 garments, the ankle cut a no-op on ~a third of references
([RESULTS §3](RESULTS.md#3-link-c--the-run-2026-09-10)). The reviewer's pass is open.

**What the run raises, ahead of that pass.** `BC_klein` counted over the same 600 iron-man-2
cells comes to **4.8%** against the lock's **9.2%**, and fails on 17 cells where the lock
does not against 43 the other way. The mechanism that would explain it is not about prompts:
`BC` never lets a generative model re-draw the garment, where every `V`-family arm does, and
a re-drawn garment reaches call 2 as a *rendering* of the garment — resampled, with
structured invention that call 2 then transfers faithfully onto the wearer. The head crop
cannot reach that, because it acts downstream of the re-draw. Stated, with its
counter-evidence and what would falsify it, in
[RESULTS §4](RESULTS.md#4-why-bc-may-simply-be-better--the-regeneration-tax) — **not
concluded**: the two rates were measured by different protocols, and the identical `VEi`
counting page exists so they can be measured by one.

## What is carried in from v3.4

`F3` (the regenerated reference drifts) and the backview/extreme-pose class are the classes
this chain is aimed at — v3.4 called the latter a source-image problem no renderer fixes.
`M1`'s explicit turn is the first arm that tests that claim directly. `F1`, `F2`, `F4` and
`F5` are untouched here; select-from-N remains v4 scope.
