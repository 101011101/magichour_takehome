# Virtual Try-On — Model Comparison Pilot

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/101011101/magichour_takehome/blob/main/virtual_tryon.ipynb)

Person image + garment image → person wearing the garment, compared across 7
hosted arms vs the **Qwen 2511** baseline, under a $10 pilot budget.

- **Notebook:** [`virtual_tryon.ipynb`](virtual_tryon.ipynb) — open via the badge; needs `FAL_KEY` in Colab Secrets
- **What's being built & why:** [`prd/V1_PILOT.md`](prd/V1_PILOT.md) (version scope) · [`prd/OUTLINE.md`](prd/OUTLINE.md) (full program)
- **Task & background:** [`TASK.md`](TASK.md) · [`NOTES.md`](NOTES.md) · [`references/`](references/)
- **Test set:** [`test_set/`](test_set/) — 30 people × 30 garments, curated pairs in `pairs.csv`
- **How docs/truth work:** [`execution_conventions.md`](execution_conventions.md)

## Run flow

Run all (free cells only) → flip `RUN_TRIAGE=True` (~$1.30) → eyeball grids,
set `SURVIVORS` → flip `RUN_GRID=True` → **judge at §8** → leaderboard + verdict
at §10–11. Paid cells are flag-gated; nothing spends money on "Run all."
