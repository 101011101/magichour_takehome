# v3.3 — SOLUTION

**Locked 2026-08-30.** Approved by the reviewer (`Q3`, `E3`, the ankle cut, the arms row),
run whole on the 28-pair run-B fold with no side effect
([RESULTS §12](RESULTS.md#12-phase-8--the-complete-version-on-the-fold-2026-08-29)), and at
parity with v3.1's locked arm at the output by eye
([RESULTS §8.1](RESULTS.md#81-results--56-klein-edits-0-failures-no-black-frames-reviewed-by-eye-unscored)).
Per [SCHEMA.md](../SCHEMA.md) this document carries the architecture and links to the
evidence; the argument is in [EXPERIMENT.md](EXPERIMENT.md), the cases in
[RESULTS.md](RESULTS.md). **Unscored** — the next step is the scored comparison in §7.

**The locked version in one line:** `A4 crop → klein head swap (neck up) + dynamic
pose+framing clause + garment-hold sentence + mannequin head colour → bbox re-crop →
ankle cut → klein edit`.

Two decisions taken 2026-08-29 and binding on every run from phase 2 onward:

1. **The A4 crop is applied first, before any klein call.** Every phase-1 klein arm
   edited the full frame and cropped after; that is withdrawn as a procedure
   ([RESULTS §5.5 item 2](RESULTS.md#55-reviewers-notes-on-45-recorded-2026-08-29)).
2. **Pose + framing — the dynamic `PERSON_CLAUSE` — is the arm going forward.** The
   constant-pose sentence is dropped.

**The experiment template for phase 2** is the version *without* the colour word:
`A4 crop → head swap + PERSON_CLAUSE[framing] → bbox re-crop`. The colour word is in the
version but is held out of phase 2 so that pose and region variants are read against one
prompt.

## 1. The architecture

```
person photograph ──► MediaPipe Selfie Multiclass → FACE median L*a*b* → ladder step
                        → HEAD COLOUR WORD                                   149 ms
                                                                                 │
garment photograph ─┬─► BiRefNet_lite @1024² → subject on white, head kept       │
                    │     → THE A4 CROP                                          │
                    │                                                            │
                    └─► MediaPipe Pose on the crop → FRAMING CATEGORY     36 ms  │
                          → PERSON_CLAUSE[category]  (pose + extent, one table)  │
                                        │                                        │
        HEAD SWAP + <colour word> + KEEP + PERSON_CLAUSE[category]               │
                                        │                                        │
                 FLUX.2 klein 4b distilled edit ──► HEAD-SWAPPED, RE-POSED       │
                                        │           PHOTOGRAPH            CALL 1 │
                          pose bbox re-crop + ANKLE CUT (40 ms) → THE REFERENCE  │
                                        │                                        │
                 FLUX.2 klein ──────────┴──────────────────────────────────────────┘
                                        └──► TRY-ON                      CALL 2
```

**One model, two calls.** Qwen leaves the deploy path. Everything left of call 1 is the
v3.1 CPU stack unchanged.

## 2. Every stage, and the evidence for it

| stage | what | status | evidence |
|---|---|---|---|
| A4 crop | BiRefNet_lite 1024², white ground, **head kept**, bbox + 4% | **inherited from v3.1, locked** | [v3.1 SOLUTION §2](../v3.1/SOLUTION.md) |
| tone reader → colour word | face median L\*a\*b\* → ten-step ladder | inherited; **now colours the head, not a mannequin body** | [RESULTS §5.1](RESULTS.md#51-result--112-klein-calls-0-failures-reviewed-on-the-raw-frames-crops-following) `MH_col` 28/28 |
| framing reader → `PERSON_CLAUSE` | pose + extent from one table, never naming a part the crop excludes | **passed** 28/28 extent; the constant-pose control failed 8/9 partial crops | [RESULTS §5.1](RESULTS.md#51-result--112-klein-calls-0-failures-reviewed-on-the-raw-frames-crops-following) |
| call 1: head swap | klein replaces the head **from the neck up** with a featureless mannequin head, everything else kept | **passed** 28/28; `M1` wording adopted in phase 2 | [RESULTS §4](RESULTS.md#4-link-13--reviewers-verdict-on-13-and-the-head-swap-arm) |
| call 1: + re-pose | the `PERSON_CLAUSE` pose sentence **+ the garment-hold sentence** | **passed** on 28; hold sentence removes the dress→trousers split (phase 3) | [RESULTS §5](RESULTS.md#5-link-14--can-klein-pose-the-person-inside-the-head-swap-edit) |
| call 1: + head colour | `"<tone> mannequin head"` | **passed** 28/28, added to the version; to be revisited after §4 items 1–3 | [RESULTS §5.5](RESULTS.md#55-reviewers-notes-on-45-recorded-2026-08-29) |
| ankle cut | pose reader on the re-posed frame → cut at `min(ankle_y) − 3%`; fallback: the A4 crop's ankle ratio | **adopted** 2026-08-29 (reviewer); null on the probe, safe, removes footwear as a variable | [RESULTS §9.1–9.2](RESULTS.md#91-probe-results--g013-g012-4-reference-calls-10-edits-0-failures) |
| crop order | **A4 crop → klein → bbox re-crop** | **binding; run in phase 2** — `P0` 28/28 extent, no duplication | [RESULTS §5.6](RESULTS.md#56-the-crop-order-question-settled-for-the-next-phase) |
| call 2: the edit | klein, `EDIT_PROMPT` **+ the `E3` sentence** (§3b), seed 46 | **run**; `Q3` indistinguishable from `BC`/`MQ` on 24/28; `E3` = V2 prompt on 27/28 and fixes the 28th | [RESULTS §8.1](RESULTS.md#81-results--56-klein-edits-0-failures-no-black-frames-reviewed-by-eye-unscored) |

## 3. The call-1 prompt

```
Replace this person's head, from the neck up, with a smooth, featureless <colour>
mannequin head of the same size, in the same position and facing the same way - no
face, no hair. Keep the clothing, the body, the hands and the background exactly as
they are.
+ PERSON_CLAUSE[framing]
+ " The clothing stays exactly the same through the change of pose - the same pieces,
   the same shape, the same length."
```

The last sentence is phase 3's `Q3` ([RESULTS §7.1](RESULTS.md#71-results--107-klein-calls--2-re-seeds-seed-47-gal_gadot-q1-scarlett-q4-107-re-crops)):
it holds a dress as a dress through the re-pose and names no garment type — the version
that did put skirts on men.

*"from the neck up"* is phase 2's `M1` — accepted by the reviewer as the head-swap
sentence ([RESULTS §6.4](RESULTS.md#64-reviewers-notes-on-phase-2-2026-08-29)). The neck
is part of the replaced region.

`PERSON_CLAUSE` (from `v3/build/run_v33_pose.py`):

| category | clause |
|---|---|
| `full_body` | Change the pose: the person stands upright in a neutral pose, facing forward, arms relaxed at the sides, feet together. The photograph shows them from head to feet; keep that framing. |
| `knee_up` | … legs together. The photograph shows them from the head to the knee only; keep exactly that framing, cut off below the knee. |
| `waist_up` | Change the pose: the person stands upright and square to the camera, shoulders level, arms relaxed at the sides. The photograph shows them from the head to the hip only; keep exactly that framing, cut off below the hip. |
| `chest_up` | Change the pose: the person faces the camera squarely, shoulders level, **arms down, relaxed at the sides**. The photograph shows them from the head to the chest only; keep exactly that framing, cut off below the chest. *(arms phrase added in phase 7)* |

### 3b. The call-2 prompt

```
Dress the person in image 1 in the clothing shown in image 2. Keep the person's face,
identity, body and the background exactly as they are. The person's body, limbs and
feet are exactly as in image 1 - nothing added, nothing removed.
```

The last sentence is phase 6's `E3` — the first change to call 2 in V3.

## 4. The inquiries that built it, and what is carried open

Items 1–4 as the reviewer raised them ([RESULTS §5.5](RESULTS.md#55-reviewers-notes-on-45-recorded-2026-08-29)); the rest added as they arose.

**Closed, in the version**

1. ~~**Leg and foot control**~~ — negative ([RESULTS §6.3](RESULTS.md#63-results--206-klein-calls--3-reruns-206-re-crops-reviewed-on-the-crops)):
   crop-first already straightens the feet; no added sentence helps, and the hip sentence
   on `waist_up` invents legs. `PERSON_CLAUSE` unchanged.
2. ~~**Crop-first**~~ — done; `P0` is the baseline.
3. ~~**Head-swap region**~~ — **`M1` "from the neck up"** is the sentence; the neck blends
   with the head and the reviewer accepts it. "Face only" renders a face.
4. ~~**Pose wording**~~ — the garment-neutral hold sentence (`Q3`) is in the prompt; leg
   and foot words do nothing; naming garment types invents them.
5. ~~**Call 2**~~ — run, parity ([RESULTS §8.1](RESULTS.md#81-results--56-klein-edits-0-failures-no-black-frames-reviewed-by-eye-unscored)).
6. ~~**Feet in the reference**~~ — probed null, adopted as a general measure ([RESULTS §9.2](RESULTS.md#92-reviewers-decision-on-feet-and-a-research-note-on-the-seated-case-2026-08-29));
   `R1 ankle-after` is in the version.
7. ~~**Call-2 wording**~~ — **`E3` approved by the reviewer 2026-08-29** ([RESULTS §10.2](RESULTS.md#102-e3-on-all-28--24-further-edits-0-failures)):
   indistinguishable from the V2 prompt on 27/28, fixes `p021`. Prompt of record in §3b.

8. ~~**Arms in partial crops**~~ — **adopted** ([RESULTS §11.1](RESULTS.md#111-result--1-reference-call-1-edit-0-failures)):
   the `chest_up` row gains *"arms down, relaxed at the sides"*; every row now carries an
   arms phrase. `p030`'s reference fixed; output neutral.

**Carried into the lock, open**

9. **Head colour** — in the version, working 28/28 at the reference; its effect at the
   output has not been isolated (call 2 ran without it). Revisit only if scoring says to.
10. **Accessory carry-over** — bags in the reference are worn in the output; `MQ` avoids
    this only because Qwen dropped them. **Product decision**, not an experiment; if
    "drop", one concrete sentence in call 1.
11. **Footwear regenerated by the re-pose** (`g013`) — moot at the reference now that
    the ankle cut removes feet; unmeasured at the output.
12. **Scoring** — the parity claim is by eye, one seed, one reviewer. A ternary pass over
    the version (`gen/{set_id}__V.jpg`) against `BC`/`MQ` is what would change this
    document's status to locked.

## 4b. Where the version's outputs are

| | |
|---|---|
| references | `v3/runs/v3.0b/refs/{garment}__V.jpg` |
| outputs | `v3/runs/v3.0b/gen/{set_id}__V.jpg` |
| page | `v3/report/v33_version.html` |
| runner | `v3/build/run_v33_version.py` (composes the phase runners; the prompt of record is §3 + §3b) |

## 5. Rules that generalise out of v3.3

Added to v3.1's four ([v3.1 SOLUTION §3](../v3.1/SOLUTION.md#3-the-rules-that-generalise)).

5. **Ask an editor for an edit.** klein could not regenerate a mannequin or an isolated
   garment to Qwen's standard; asked to replace the head and re-pose — a local edit with
   everything else held — it produced a reference the try-on edit cannot tell from Qwen's.
6. **A negation fills its slot only if the slot is empty.** "No hand, no leg, no face"
   rendered a grey body where the parts were absent (`k6`); "no turned feet" and "do not
   add body parts" did nothing where the parts were present (`P3`, `E1`).
7. **Naming a garment type fills that slot too** — "a skirt stays a skirt" put skirts on
   three men; the garment-neutral hold sentence did not.
8. **The reference decides the garment's structure at the output; the person decides
   the pose.** A dress in, a dress out; a bag in, a bag out. Feet, arms and a seated
   wearer's legs come from image 1, and only call 2 can reach them.
9. **Tell the model what is there — in call 2 as well.** The one edit-prompt sentence
   that worked states the body as given and names nothing to add or remove.

## 6. Known limits carried into the lock

- Everything is one seed, one reviewer, by eye, on the 28-reference run-B fold.
- A re-pose re-renders the garment wherever a limb moves — seen as bare feet on `g013`
  and a jumpsuit on `scarlett`; `MH` without the pose clause is pixel-faithful by
  construction and remains the fallback.
- Seed 46 returned a black frame on 3 of 206 phase-2 cells; seed 47 rendered them. A
  production path needs a black-frame check and a re-seed.
- Exposed skin on arms, hands and legs is kept — a real photograph of the wearer, not a
  mannequin. Whether the edit reconciles it against the target person is unmeasured.
- The tone ladder's calibration defect ([v3.1 SOLUTION §6](../v3.1/SOLUTION.md#6-known-defects-carried-into-the-lock)) is inherited.


## 7. Next: the iron-man test

The version is locked on one reviewer's eye over 28 pairs at one seed. What locks it as
a *result* is a scored comparison against everything on disk, under the protocol V2 and
v3.1 used and this investigation did not:

| | |
|---|---|
| arms | the version (`gen/{set_id}__V.jpg`) against `BC`, `MQ`, `QX`, `PH`, `PH2` — all already in `v3/runs/v3.0b/gen/` for the same 28 pairs |
| then | the 200-pair matrix (`v3/testsets/v3_full_matrix.csv`) through the Colab bundle, the version beside `BC`/`MQ`, on a GPU so the matte is milliseconds |
| protocol | the V2 ternary (`perfect` / `ok` / `fail`) with a band tag on every non-perfect; **blinded** — arm names hidden, order shuffled; more than one seed on the version |
| what would unlock the accessory question | a count of pairs where a reference-borne bag is worn in the output, per arm |
| what would unlock the head-colour question | the version with and without the colour word, scored, not eyed |
| where it runs | **Colab, A100, self-hosted klein** (`black-forest-labs/FLUX.2-klein-4B`, `Flux2KleinPipeline`, weights from the Drive HF cache) — the plan's rule that final numbers come from downloaded weights |
| the bundle | `v33_ironman_bundle.zip` = `v3/colab/v33_ironman.ipynb` + `lib/{v3lib,klein_local,run_ironman}.py` + the 200-pair matrix + testset; `v3/colab/README_ironman.md` |
| what comes back | one zip: inputs, references, `gen/{set_id}__{V,BC}__s{seed}.jpg`, and `meta/` with every prompt, **`timings.csv` (every stage and call timed) and `cost.json`** (klein calls, seconds per call, wall time, USD at the hourly rate set in the notebook, fal-equivalent at $0.015/call) |
| then locally | `python3 v3/build/ironman_page.py <zip>` → `v3/report/v33_ironman.html`, **blinded** (A/B per pair, order shuffled, key in `v3/runs/ironman/<stamp>/key.csv`), timing and cost tables at the top |
| scale | 200 pairs × 2 arms × 3 seeds ≈ 1,312 klein calls; low single-digit seconds each on an A100 — well under an hour of generation |

Nothing in the version changes for this test. It is measurement.
