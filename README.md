# Virtual Try-On — Magic Hour Take-Home

Person image + garment image → the person wearing that garment, better than the
website's Qwen 2511 baseline. Prompt and context: [TASK.md](TASK.md).

## Layout

| Path | What it is |
|---|---|
| [v1/](v1/) | Shipped V1 pilot: 7-arm hosted-API bake-off, eval harness, final report. Entry point: [v1/README.md](v1/README.md) |
| [v2/](v2/) | In progress: open-weights-only rebuild. Notes: [v2/NOTES.md](v2/NOTES.md) |
| [prd/](prd/) | Product docs — [OUTLINE.md](prd/OUTLINE.md) (global), `v1/`, `v2/` |
| [test_set/](test_set/) | Curated 30 people + 30 garments, shared across versions ([TESTSET_PLAN.md](TESTSET_PLAN.md)) |
| [research/](research/) | Model scouting, accuracy research, open-weights catalog |
| [references/](references/) | Reference notebooks (Krea 2 identity edit, Ideogram) + synthesis |
| [execution_conventions.md](execution_conventions.md) | Working conventions for this repo |

## Status

- **V1** shipped 2026-08-08 — seedream5_lite → qwen_image3 cascade beat the qwen_2511
  baseline on every judging system on held-out pairs. Full report in [v1/](v1/).
- **V2** pivots to open weights only (no hosted APIs); primary goal is output quality
  with identity preservation.
