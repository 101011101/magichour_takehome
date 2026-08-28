# v3 — working directory

Code, evidence bundles and report pages for V3. The brief lives in
[`prd/v3/README.md`](../prd/v3/README.md); nothing here restates it.

Layout follows `v1/` and `v2/`:

| | |
|---|---|
| `artefacts/` | Evidence bundles. One folder per case, inputs and intermediates and outputs copied in with canonical names, plus `manifest.json` carrying provenance and metrics |
| `build/` | Scripts that produce the pages and the test matrices. Deterministic, no API calls, safe to re-run |
| `testsets/` | Generated evaluation matrices of record. One CSV per investigation; the `TEST.md` that documents it renders from here |
| `report/` | Generated HTML. Never hand-edited — edit the builder |

## What is here

**`artefacts/`** — the four sets where BC_klein failed and QX rescued it, assembled
from `v2/runs/`. Every file records where it came from. Analysis:
[`prd/v3/v3.0/`](../prd/v3/v3.0/EXPERIMENT.md).

**`report/artefacts.html`** — side-by-side of the reference chain and the four arms
for each case, with the defect region magnified. Built by
`build/artefact_page.py`; images are copied into `report/img/` so the page is
self-contained.

```
python3 v3/artefacts/build_bundle.py     # assemble the bundle from v2/runs
python3 v3/build/artefact_page.py        # rebuild the page from the bundle
python3 v3/build/make_matrix.py          # regenerate the v3.0 evaluation matrix
```
