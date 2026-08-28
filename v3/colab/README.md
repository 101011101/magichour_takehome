# v3.1 full run — Colab bundle

Self-contained. No repo, no Drive, no cached state: the notebook downloads its own
weights and everything else is in here.

```
v31_full_run.ipynb   the notebook — run cells in order
matrix.csv           200 pairs, every image used 3–4 times on each side
testset/             56 on-model photographs + manifest.csv
lib/v3lib.py         the pipeline: readers, crop, prompts, fal client
lib/run_all.py       resumable orchestrator
```

## The three arms

| arm | reference built by | calls |
|---|---|---|
| `BC` | klein makes the wearer bald → CPU crop | 2 |
| `QX` | Qwen regenerates the garment isolated on white | 2 |
| `MQ` | CPU crop → Qwen regenerates it as a **mannequin** — **this is v3.1** | 2 |

## What makes MQ different

Its extraction prompt is **assembled per pair** from two CPU reads:

- the **person's** face → median Lab → one of ten named tone steps → a colour word
- the **garment crop's** pose → which joints are in frame → a framing category
- the category selects the **extent and pose clauses together** from one table

That last point is the fix worth knowing about: those two clauses were once written
separately and contradicted each other — *"feet together"* told the model feet were in
frame while the extent clause said to cut above them, and the pose clause won. One
lookup, one rule: **never name a body part the crop excludes.**

## Cost, before you start

600 klein edits + ~56 bald + ~256 Qwen extractions. At the measured klein price of
$0.015 that is **~$9.84 of klein**; the **Qwen price is not recorded anywhere in this
project** — check the dashboard first.

MQ needs one extraction *per pair* rather than per reference, because the colour word
depends on who is being dressed. 200 Qwen calls instead of 56. That is the price of the
colour reader and it is worth knowing before it is spent.

**The run is resumable.** Every stage skips what is already on disk, so an exhausted
balance costs a restart and nothing else. That has happened five times at smaller scale.

## Models — it looks for a cache before downloading

Three weights are needed: **BiRefNet_lite 224 MB**, Selfie Multiclass 16 MB, Pose
Landmarker 6 MB. Cell 3 searches, in order:

```
$V3_MODEL_DIR   ./models   /content/models
/content/drive/MyDrive/v3_models   /content/drive/MyDrive/models
/content/drive/MyDrive/tryon_v2_runs/models   ~/.cache/v3_models
```

**A file only counts if it is the right size.** Existence is not enough: an interrupted
download leaves a file that passes `os.path.exists` and then fails somewhere much less
obvious, so each is checked against its expected byte count and refetched if wrong.

Set `PERSIST` in cell 3 to a Drive path and the downloads are copied there, so the
224 MB fetch happens **once ever** rather than once per runtime.

## Run it

1. Upload this zip to `/content`
2. Runtime → Change runtime type → **GPU** (BiRefNet is ~49 s/image on CPU, milliseconds on GPU)
3. Run the cells in order. **Cell 5 does one pair first** — check `run/gen/` has three
   images before letting cell 6 spend on 200.

## What comes back

`run/inputs` normalised sources and A4 crops · `run/refs` the three reference kinds ·
`run/gen` `{set_id}__{BC,QX,MQ}.jpg` · `run/meta` every prompt as sent, plus the colour
and framing read for every pair, so a bad output traces to a bad read.

**Scoring is not included.** The zip is evidence, not a verdict.
