# v3.5 — TEST

**Status: written 2026-09-08, with link A.**

## The set

The **56 garments** of the iron-man 2 matrix (`v3/colab/matrix.csv`, 200 pairs over 56
garments and 56 persons). Link A is a *reference* experiment: call 1 runs once per garment,
not once per pair, so the garment axis is the whole set and the person axis does not enter
until link B.

Framing mix, as read by MediaPipe in the iron-man 2 run and reused verbatim:
32 `full_body` · 18 `waist_up` · 4 `knee_up` · 2 `chest_up`.

The set is **not** selected on failure, so what link A shows transfers to the fold. It
carries the hard cases the v3.4 chain named: the backview dress
(`dualuse_scarlett_johansson_black_dress_backview_night`, class F3), the arms-crossed
blazer (`dualuse_emma_watson_black_blazer_armscrossed`), and `g027`, the garment whose
framing the canvas arc was built around.

## Assets reused, not rebuilt

| asset | where | why it is reusable |
|---|---|---|
| normalised inputs, 56+56 | `v3/runs/v34/ironman2/inputs/` | ingestion is unchanged from v3.4 |
| A4 crops, 56 | `v3/runs/v34/ironman2/inputs/*__A4.jpg` | the crop stage is not a v3.5 variable |
| per-garment framing | `v3/runs/v34/ironman2/meta/prompts.json` | MediaPipe read of the same crops |
| `VEi` references, 56 | `v3/runs/v34/ironman2/refs/*__VEi*.jpg` | the A100 lock's own output — **reference only, not the control**: it is a different backend |
| `BC` references, 56 | `v3/runs/v34/ironman2/refs/*__BC.jpg` | the incumbent's head-subtracted crops, for the link-B comparison |

So link A pays for klein calls and nothing else.

## The arms

| arm | call 1 | calls |
|---|---|---|
| `M0` | `SWAP + KEEP + PERSON_CLAUSE + HOLD` — the v3.4 `Q3`, verbatim | 1 |
| `M1` | `TURN + KEEP + FRAME + HOLD` — no mannequin sentence | 1 |
| `M2` | `SWAP + TURN + KEEP + FRAME + HOLD` | 1 |
| `G1` | `GARMENT` — the clothing alone on white | 1 |
| `M1c`, `M0c` | derived: `M1`/`M0` cut at the shoulder line | 0 |

`FRAME` is the framing half of `PERSON_CLAUSE` with the re-pose half removed — `M1`/`M2`
carry their own turn sentence and must not be told to change the pose twice. Every prompt
string is written to `v3/runs/v35/linkA/meta/run.json`; the runner imports `SWAP`, `KEEP`,
`HOLD` and `PERSON_CLAUSE` from `v3/colab/lib/run_ironman.py` rather than copying them, so
the control cannot drift from the lock.

## Held fixed

Seed 46. One klein call per reference. The A4 crop, the normalisation, the white-margin
re-crop after call 1, and the call-1 canvas rule — all as the v3.4 lock. No SR in link A:
the SR pass is identical across arms and belongs to call 2, so it would only add cost to a
comparison it cannot change.

## Backend

**fal**, `fal-ai/flux-2/klein/4b/distilled/edit`, $0.015/call — the same weights as the
deploy path, on someone else's GPU. Link A is a prompt experiment, and every arm in it is
drawn by the same backend at the same seed, so the comparison is paired and internally
valid. **Any number that goes into a lock is re-measured on the downloaded weights** — fal
priors have failed to transfer to the A100 twice ([v3.4 links F→G](../v3.4/EXPERIMENT.md)).

## Review

Unblinded contact sheets, crop beside all four arms per garment, at
`v3/report/v35_linkA.html`. The question at link A is not "which is prettier" but three
readable facts per cell: did the wearer turn front-on, did the garment survive unchanged,
and is the head gone.
