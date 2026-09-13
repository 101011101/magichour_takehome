# v3.15 — RESULTS

**Run 2026-09-13.** The shipped production notebook, driven end to end on a GPU with a region
set. Question and pass rules: [EXPERIMENT.md](EXPERIMENT.md), [TEST.md](TEST.md). Per case
records: `v3/runs/v315/a100/records.json` (zip `v315_prod_smoke_20260913_0630.zip`, gitignored
like every run); page `v3/report/v315.html`, built by `v3/build/v315_page.py`.

## 1. What was tested

| | |
|---|---|
| notebook under test | `vp/tryon_er.ipynb` at commit `62b837f` (`62b837f20659117a7f6cfd4a3434be5e30e6d817`) |
| its sha256 | `37f5236ae6aa01c2a8ccbb6aa63a3e5199961a03a7db9fcd7ab48c8d1754ca94` |
| how | its own Install, Downloads, Inputs, Load and Pipeline cells executed unmodified; its own `prepare_garment` and `try_on` called; a pass-through recorder on `klein` only |
| GPU | NVIDIA A100-SXM4-40GB |
| cases | 44 — 17 product shots × upper/lower, 5 worn garments × upper/lower |
| klein calls | 50 |

## 2. Result: 42 of 44

### 2.1 The person gate — 34 of 34

Every product shot, asked for `upper` and for `lower`, took the route the gate exists for:

| check | result |
|---|---|
| gate found no person | 34 / 34 |
| bald pass skipped | 34 / 34 |
| region forced to `full` | 34 / 34 |
| head pixels on these photos | max 233, against the 500 px threshold |

So the rule under test — the head gate decides who goes through the balding pipeline, and a
product shot never gets a region cut — holds on the shipped code.

### 2.2 The region band on worn garments — 8 of 10

| garment | region | band kept | reference | applied | call 2 | result |
|---|---|---|---|---|---|---|
| `g004` | lower | 58.1% | 373x553 | lower | `region` | **pass** |
| `g004` | upper | 41.9% | 321x338 | upper | `region` | **pass** |
| `g015` | lower | 61.7% | 296x595 | lower | `region` | **pass** |
| `g015` | upper | 38.3% | 277x380 | upper | `region` | **pass** |
| `g024` | lower | 60.4% | 326x550 | lower | `region` | **pass** |
| `g024` | upper | 39.6% | 239x354 | upper | `region` | **pass** |
| `g030` | lower | 2.3% (1 − upper) | **617×35** | lower (no fallback) | never sent | **FAIL — raised in call 2** |
| `g030` | upper | 97.7% | 826x872 | upper | `region` | **pass** |
| `p019` | lower | 10.8% (1 − upper) | **366×60** | lower (no fallback) | never sent | **FAIL — raised in call 2** |
| `p019` | upper | 89.2% | 467x474 | upper | `region` | **pass** |

## 3. The failure

Both failures are the same defect. Tracebacks are in `records.json`; the last frame is
`diffusers/pipelines/flux2/image_processor.py` `check_image_input`:

> `ValueError: Image too small: 617×35. Both dimensions must be at least 64px` (`g030`, lower)
> `ValueError: Image too small: 366×60. Both dimensions must be at least 64px` (`p019`, lower)

**Root cause.** The band's fallback fired only when the kept half was under **2% of the
garment's mask area**. On both garments the hip line sits low — their `upper` bands kept 97.7%
and 89.2% — so `lower` kept 2.3% and 10.8%. Both cleared 2%, the band was accepted, and its
bounding box was a thin strip that klein refuses. The guard measured area, never whether the
result is an image klein will take. These were the two cases chosen because they should fall
back; they crashed instead, which in production is a user asking for `lower` on a waist-up
photograph and getting an error.

**Fix, in `vp/tryon_er.ipynb` (2026-09-13).** The band falls back to `full`, each with its own
recorded reason, when it keeps under **15%** of the garment — every band that worked kept 38% or
more, the failures 2.3% and 10.8% — or when the reference it would send has a side under
**64 px**, klein's own floor, evaluated on the band's padded bounding box as call 2 receives it.
Also fixed: on a product shot `requested` was overwritten with `full`; it now keeps the region
the user asked for, including when the reference comes from the cache.

**Verified without a GPU.** The band decision was replayed through the notebook's own
`head_subtract`, from HEAD and from the fix, with the models stubbed and a synthetic mask set to
each garment's recorded kept fraction on its real normalised size. HEAD applies `lower` to `g030`
and `p019` on a sliver; the fix falls both back on the 15% rule. The other eight decisions are
unchanged. A band keeping 20% but 56 px tall falls back on the 64 px rule, and an `upper` sliver
falls back too.

**Not yet verified:** the GPU re-run against the fixed commit. The notebook resolves the commit
where `vp/tryon_er.ipynb` last changed, so a plain Run all tests the fix; expected 44/44.

## 4. Noted, not failures

- The three passing `lower` bands (58–62%) and all five `upper` bands produced references with
  no side under 239 px — well clear of 64 px.
- The worn set is five garments; the band thresholds rest on those plus v3.11's 30 references
  (kept 36–64%). A catalogue with many waist-up photographs would exercise the 15% rule far
  more often than this did.
