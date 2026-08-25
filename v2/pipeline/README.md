# `pipeline` — the V2 try-on harness

**V2 is frozen, 2026-08-23.** This package is `pipeline 1.0.0` — its first release,
implementing V2 whole: the v2.2.3 harness (router, gate, escalation) and v2.4's realism
pass. The `1.0.0` is a package version and has nothing to do with the `v2.0`..`v2.4`
workstream directories in `prd/v2/`.

This is a checkpoint, not the direction of travel.
V3 replaces it with a single two-call path; the reasoning is in
[`prd/v2/LOCK.md`](../../prd/v2/LOCK.md). Nothing here is deprecated — it is the
best-measured configuration the project produced, and it is preserved whole so it can
be read and re-measured rather than reconstructed from a report.

## Install

```bash
pip install -e v2/                # editable, from the repo root
pip install -e 'v2/[full,fal]'    # with the mask stack and the serving client
```

**Editable install only.** The package reaches three research modules in `v2/build/`
by path (`_research.py`): `failure_gate`, `phase3_variants`, `garment_crop`. They are
imported rather than reimplemented because every measured number in `prd/v2/` came out
of those exact files, and a second copy would drift from them silently. A wheel would
not carry them. Vendoring them is the right move when this lands in company code, and
is deliberately not done here.

## Use

```python
from pipeline import HarnessConfig, run

res = run("person.jpg", "garment.jpg")
print(res.arm, res.generations, res.image_path)
for line in res.trace:
    print(line)
```

```bash
tryon-v2 person.jpg garment.jpg -o out.png
tryon-v2 --route-only garment.jpg     # free, CPU, no API key — check this first
python -m pipeline person.jpg garment.jpg --json
```

`--route-only` is the one part of the pipeline that costs nothing and needs no
credentials, which makes it the right smoke test on a new machine.

## What it does

```
person + garment reference
   │
   1  preprocess       BiRefNet · SCHP ATR · MediaPipe · pose      free, CPU, ~1.9s
   2  route            hair_over_garment ≥ 0.14 ?                  free, ~1.5ms
   │                      no  → PHEAD      1 generation
   │                      yes → BC_klein   2 generations
   │                      named region → QX
   3  generate         FLUX.2 klein 4B distilled, 4 steps, guidance 1.0
   4  screen           degenerate · no-op · identity   free, CPU
   │                   VLM garment prompt              ~$0.0006
   │                      any fires → QX, taken unconditionally
   5  realism          off by default; SeedVR2 ×2, Lanczos fallback
   ▼
output
```

**2.158 generations per request · 31 perfect / 7 ok / 0 fail over 38 sets.** The
comparison that matters is flat BC_klein — the strongest single arm — at 2.000
generations for 28/6/**4**. Essentially the same cost, and nothing ships broken.

## Modules

| file | what it owns |
|---|---|
| `config.py` | every threshold, each with the measurement that set it |
| `harness.py` | `run`, `route`, the gate, the escalation |
| `masks.py` | stage 1 crops and the router feature |
| `checks.py` | the deterministic detectors (adapters over `failure_gate`) |
| `arms.py` | the three arms, including `build_reference` for unseen garments |
| `vlm.py` | the two escalation prompts, and why there are only two |
| `upscale.py` | the optional realism pass |
| `_research.py` | the single seam onto `v2/build/` |

## Three things that are easy to break by accident

1. **Escalation switches mechanism, never seed.** Failure is a property of the
   garment — a damaged reference failed on all three people it was paired with — so a
   retry on the same arm reproduces it.
2. **The two identity numbers are on different scales.** `checks.identity_margin` is a
   *normalised margin*; `upscale.identity_cos` is a *raw cosine*. Both are thresholded
   at 0.90 and they mean different things. Crossing them fired 6 false escalations in 8.
3. **A stage that cannot do its job passes its input through unchanged.** No stage may
   emit a broken image. `hair_over_garment` is the one deliberate exception: it raises,
   because 0.0 is a valid value and returning it on an error silently routes every
   request to the cheap arm.

## Tests

```bash
cd v2 && python -m pytest pipeline/tests -q     # 29 tests, no GPU, no API key
```

`test_harness_logic.py` covers the decisions; three of its cases are regressions for
bugs that each cost a run. `test_published_numbers.py` recomputes every arm tally and
router claim in `prd/v2/` from the review CSV, so a documented number cannot drift
from its evidence.
