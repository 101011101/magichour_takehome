# v3.3 iron-man run — Colab bundle

The locked v3.3 version against `BC` (v3.1's incumbent), **self-hosted klein on an A100**,
over the 200-pair matrix, at several seeds. One model, everything timed.

```
v33_ironman.ipynb    the notebook — run cells in order, Runtime → A100
matrix.csv           200 pairs (v3/testsets/v3_full_matrix.csv)
testset/             56 photographs + manifest.csv
lib/v3lib.py         v3.1's readers, crop, incumbent prompts
lib/klein_local.py   Flux2KleinPipeline, loaded once, timed per call
lib/run_ironman.py   the two arms, resumable, timings + cost
```

## The arms

| arm | reference | edit |
|---|---|---|
| `BC` | klein bald pass on the raw photo → A4 crop | V2 edit prompt |
| `V` | A4 crop → klein head swap (neck up) + `PERSON_CLAUSE[framing]` + hold sentence → re-crop → ankle cut | V2 edit prompt + the `E3` sentence |

Prompts of record: `prd/v3/v3.3/SOLUTION.md` §3 and §3b; they are also written into
`run/meta/run.json` so the zip is self-describing. `lib/run_ironman.py` carries them
verbatim (checked byte-equal against the phase-3/6/7 runners before the bundle was cut).

Two things to know about arm `V` here, both as in every scored v3.3 run:

- **no head-colour word** — SOLUTION §4 item 9 leaves it open; this run measures the
  version without it, so the two are separable later.
- **references are made once per garment at the first seed**; the seeds vary the edit.

Arm `BC` is v3.1's incumbent exactly: bald pass with V2's prompt, resized back, A4 crop,
V2's edit prompt without the `E3` sentence.

## Calls and time

Per seed: 200 edits per arm. Once: 56 `V` references, 56 `BC` bald passes, 56+56 crops.
At 3 seeds that is **~1,312 klein calls**. Klein 4B distilled is 4 steps at ≤1.15 MP —
expect low single-digit seconds per call on an A100, i.e. **well under an hour of
generation**. BiRefNet is milliseconds on the GPU.

## What the zip contains

```
run/inputs/     normalised photographs, A4 crops
run/refs/       {garment}__V.jpg, {garment}__BC.jpg
run/gen/        {set_id}__{V,BC}__s{seed}.jpg
run/meta/       prompts.json · run.json · timings.csv (every stage, every call) · cost.json
```

`cost.json`: klein calls, seconds per call, wall time, **USD at the hourly rate you set**,
and the fal-equivalent at $0.015/call for comparison.

## If the first cells disagree with this README

- `klein 4B distilled cached: False` in cell 2 → cell 4 downloads ~13 GB into the Drive
  cache once. Fine, just slower the first time.
- `onnxruntime providers` without `CUDAExecutionProvider` in cell 3 → BiRefNet falls
  back to CPU at ~50 s per crop (112 crops ≈ 90 min). Restart the runtime and re-run
  cell 3 before spending on that; if it persists, the A4 crops can be made once and the
  run resumed — they persist in `run/inputs/`.
- Weights are searched in `$V3_MODEL_DIR` (Drive `v3_models/`) first and copied there
  after a first download, so the 224 MB BiRefNet fetch happens once ever.

## Then, locally

```
python3 v3/build/ironman_page.py v33_ironman_run_<stamp>.zip
```

builds `v3/report/v33_ironman.html` — a **blinded** review page (arm names hidden, order
shuffled per pair, the key written to `v3/runs/ironman/<stamp>/key.csv`) with the
timing and cost tables at the top.
