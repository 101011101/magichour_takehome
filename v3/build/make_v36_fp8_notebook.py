"""Write `v3/colab/v36_fp8.ipynb` — the same prompt on a different transformer.

  python3 v3/build/make_v36_fp8_notebook.py
"""
import json
import os

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(REPO, "v3", "colab", "v36_fp8.ipynb")
BRANCH = "v3.3-lock"

MD = """# `ERq` — Photoroom's transformer, everything else unchanged

Same prompt (`ER`), same references, same canvas, same seeds. **The only thing that changes
is which transformer weights are loaded.**

| component | where it comes from |
|---|---|
| **transformer** | **`Photoroom/FLUX.2-klein-4b-fp8-diffusers` → `transformer_bf16`** (7.22 GiB) |
| text encoder, VAE, scheduler, tokenizer | `black-forest-labs/FLUX.2-klein-4B`, unchanged |

Photoroom's repo carries **only** a transformer, so the rest of the pipeline is BFL's by
construction — any difference is attributable to those weights and nothing else.

**What the two files are.** Identical architecture config, identical class, identical tensor
shapes and offsets, identical file length. But **16 of 18 large weight matrices differ**, and
on those, 15–16% of Photoroom's weights have their low four mantissa bits zeroed against 6%
in BFL's — the signature of an fp8 → bf16 upcast. Median relative error ≈ 2.2% per weight.
Embeddings and norms are untouched, which is the usual fp8 pattern.

**The set is 74 cells with a known `ER` verdict**, so a difference lands somewhere meaningful:

| | cells | the question |
|---|---|---|
| `ER` failed | 18 | does the swap fail them too? |
| `ER` repaired over `BC` | 16 | does the swap keep the wins? |
| both arms clean | 40 | **does the swap break what works?** — the one that decides |

Runtime → **A100**, then **Run all**. 74 edits, ~4 min of generation; the transformer
download is the long pole the first time.
"""

CELLS = [
    ("markdown", MD),
    ("code", '''# 1 · settings
A100_USD_PER_HOUR = 0.689
ARMS = ("ERq",)                # ER's prompt, Photoroom's transformer
MATRIX = "v36_fp8_set.csv"
DRIVE_PROJECT_DIR = "Side projects and shi"
FP8_REPO, FP8_SUB = "Photoroom/FLUX.2-klein-4b-fp8-diffusers", "transformer_bf16"
'''),
    ("code", '''# 2 · the stack
!pip -q install -U diffusers transformers accelerate sentencepiece protobuf opencv-python-headless
import os, sys, torch
print('gpu:', torch.cuda.get_device_name(0))
assert 'A100' in torch.cuda.get_device_name(0), 'Runtime -> Change runtime type -> A100'
'''),
    ("code", f'''# 3 · the bundle
!cd /content && rm -rf v36 && wget -q -O v36.zip https://github.com/101011101/magichour_takehome/raw/{BRANCH}/v36_bundle.zip && unzip -qo v36.zip -d v36
%cd /content/v36
sys.path.insert(0, 'lib')
import csv, collections
for f in ('lib/klein_local.py', 'lib/v3lib.py', 'lib/run_v36.py', MATRIX):
    assert os.path.exists(f), f'bundle incomplete: {{f}} - is the latest v36_bundle.zip pushed to {BRANCH}?'
rows = list(csv.DictReader(open(MATRIX)))
print(len(rows), 'cells:', dict(collections.Counter(r['er_status'] for r in rows)))
'''),
    ("code", '''# 4 · Drive: the BFL cache stays - Photoroom ships a transformer and nothing else, so the
#     text encoder, VAE, scheduler and tokenizer still come from black-forest-labs.
import glob, zipfile, shutil
from google.colab import drive
drive.mount('/content/drive')
MYDRIVE = '/content/drive/MyDrive'; BASE = os.path.join(MYDRIVE, DRIVE_PROJECT_DIR)
assert os.path.isdir(BASE), f'Drive project dir not found: {BASE}'
KLEIN = 'models--black-forest-labs--FLUX.2-klein-4B'
cands = [os.path.join(MYDRIVE, 'hf_cache'), os.path.join(BASE, 'tryon_models', 'hf_cache'),
         os.path.join(BASE, 'hf_cache')]
found = [c for c in cands if os.path.isdir(os.path.join(c, 'hub', KLEIN))]
assert found, 'the BFL cache is required - Photoroom has no text encoder, VAE or tokenizer'
os.environ['HF_HOME'] = found[0]
print('HF_HOME', os.environ['HF_HOME'], '(BFL cached - do not delete it)')

def newest(pat, required=True):
    hits = sorted(glob.glob(os.path.join(BASE, 'v3_runs', pat)))
    assert hits or not required, f'not on Drive: v3_runs/{pat}'
    return hits[-1] if hits else None

want_people = {f"inputs/{r['person']}.jpg" for r in rows}
want_refs   = {f"refs/{r['garment']}__BC.jpg" for r in rows}
for pat, want in (('v34_ironman2_2*.zip', want_people), ('v34_ironman2_bc_*.zip', want_refs)):
    z = newest(pat)
    with zipfile.ZipFile(z) as zz:
        missing = want - set(zz.namelist())
        assert not missing, f'{os.path.basename(z)} is missing {len(missing)}'
        for n in sorted(want): zz.extract(n, 'run')
    print(f'{os.path.basename(z)}: {len(want)} files')

# the ER cells for these rows, so the page can put the two transformers side by side
prev = newest('v36_ironman_er_*.zip', required=False)
if prev:
    want_er = {f"gen/{r['set_id']}__ER__s{r['seed']}.jpg" for r in rows}
    with zipfile.ZipFile(prev) as zz:
        for n in sorted(want_er & set(zz.namelist())): zz.extract(n, 'run')
    print(f'{os.path.basename(prev)}: {len(glob.glob("run/gen/*__ER__*.jpg"))} ER cells')
'''),
    ("code", '''# 5 · the transformer, ~7.2 GiB, cached to Drive so this happens once
from huggingface_hub import snapshot_download
p = snapshot_download(FP8_REPO, allow_patterns=[f'{FP8_SUB}/*'])
print('transformer at', p)
!du -sh {p}
'''),
    ("code", '''# 6 · load the pipeline with that transformer in place of BFL's
import klein_local as K
K.load(transformer=(FP8_REPO, FP8_SUB))
print(K.info())
assert K.info().get('transformer'), 'the swap did not take - check cell 5'
'''),
    ("code", '''# 7 · the run (resumable)
import json
import run_v36 as V
print('prompt:', V.PROMPT['ERq'])
V.main(MATRIX, arms=ARMS, gpu_usd_per_hour=A100_USD_PER_HOUR)
print(json.dumps(json.load(open('run/meta/cost_v36.json')), indent=1))
'''),
    ("code", '''# 8 · landed, and a first look. If the weights were equivalent the two columns would be
#     identical; they will not be, because the sampling trajectory differs from step one.
#     What matters is whether the OUTCOME differs, not whether the pixels do.
import numpy as np, cv2, hashlib
from PIL import Image
from IPython.display import display
made = len(glob.glob('run/gen/*__ERq__*.jpg'))
print(f'ERq {made}/{len(rows)} cells')
assert made == len(rows), 'incomplete - rerun cell 7, it resumes'
h = lambda p: hashlib.md5(open(p, 'rb').read()).hexdigest()
pairs = [(r, f"run/gen/{r['set_id']}__ER__s{r['seed']}.jpg",
             f"run/gen/{r['set_id']}__ERq__s{r['seed']}.jpg") for r in rows]
both = [(r, a, b) for r, a, b in pairs if os.path.exists(a)]
ident = sum(1 for _, a, b in both if h(a) == h(b))
print(f'byte-identical to ER on {ident}/{len(both)} cells')

def side(paths, ht=380):
    ims = [cv2.imread(p) for p in paths if os.path.exists(p)]
    fit = [cv2.resize(i, (max(1, int(i.shape[1] * ht / i.shape[0])), ht)) for i in ims]
    w = max(f.shape[1] for f in fit)
    return Image.fromarray(cv2.cvtColor(np.hstack(
        [np.pad(f, ((0, 0), (0, w - f.shape[1]), (0, 0)), constant_values=255) for f in fit]),
        cv2.COLOR_BGR2RGB))

for r, a, b in [x for x in both if x[0]['er_status'] == 'both_clean'][:4]:
    print(r['set_id'], 's' + r['seed'], r['er_status'], '- person, reference, ER (BFL), ERq (Photoroom)')
    display(side([f"run/inputs/{r['person']}.jpg", f"run/refs/{r['garment']}__BC.jpg", a, b]))
'''),
    ("code", '''# 9 · zip to Drive
import time
name = f"v36_fp8_{time.strftime('%Y%m%d_%H%M')}"
with zipfile.ZipFile(f'/content/{name}.zip', 'w', zipfile.ZIP_DEFLATED) as z:
    for f in os.listdir('run/gen'):    z.write('run/gen/' + f,    'gen/' + f)
    for f in os.listdir('run/refs'):   z.write('run/refs/' + f,   'refs/' + f)
    for f in os.listdir('run/inputs'): z.write('run/inputs/' + f, 'inputs/' + f)
    for f in os.listdir('run/meta'):   z.write('run/meta/' + f,   'meta/' + f)
    z.write(MATRIX, MATRIX)
with zipfile.ZipFile(f'/content/{name}.zip') as z:
    assert z.testzip() is None, 'the zip is corrupt - do not trust it'
    print(len(z.namelist()), 'files')
shutil.copy(f'/content/{name}.zip', os.path.join(BASE, 'v3_runs', name + '.zip'))
print('->', os.path.join(BASE, 'v3_runs', name + '.zip'))
'''),
]


def main():
    cells = []
    for kind, src in CELLS:
        c = {"cell_type": kind, "metadata": {},
             "source": src.rstrip("\n").splitlines(keepends=True)}
        if kind == "code":
            c["execution_count"] = None
            c["outputs"] = []
        cells.append(c)
    json.dump({"cells": cells, "metadata": {
        "accelerator": "GPU", "colab": {"provenance": [], "gpuType": "A100"},
        "kernelspec": {"display_name": "Python 3", "name": "python3"},
        "language_info": {"name": "python"}},
        "nbformat": 4, "nbformat_minor": 0}, open(OUT, "w"), indent=1)
    print(f"{os.path.relpath(OUT, REPO)}  ({len(cells)} cells)")


if __name__ == "__main__":
    main()
