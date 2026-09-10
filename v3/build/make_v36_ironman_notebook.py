"""Write `v3/colab/v36_ironman_er.ipynb` — the iron-man run for `ER`, on an A100.

Generated rather than hand-edited so the cells stay diffable.

  python3 v3/build/make_v36_ironman_notebook.py
"""
import json
import os

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(REPO, "v3", "colab", "v36_ironman_er.ipynb")
BRANCH = "v3.3-lock"

MD = """# Iron man — the `ER` arm

`ER` is `BC` with **one word changed in call 2**. Call 1 is `BC`'s, untouched: the klein
bald pass, then the V2 cropper subtracts the head. This notebook does not run it — the 56
references come off Drive exactly as `BC` shipped them, so the two arms are the same
pipeline up to the last call.

| | call 2 prompt |
|---|---|
| `BC` | *Dress the person in image 1 in the clothing shown in image 2.* Keep the person's face, identity, body and the background exactly as they are. |
| `ER` | ***Replace the clothing in image 1 with*** *the clothing in image 2.* Keep the person's face, identity, body and the background exactly as they are. |

**The set is not sampled.** It is the whole iron-man-2 matrix — 200 pairs × seeds 46/47/48,
**600 cells**, the same 600 `BC` was counted on in the blind sweep that gave it 29 failures
(4.8%). A rate for `ER` is comparable to that one only if it is the same cells, the same
reference, the same canvas, the same eye and the same page, so nothing here is filtered and
no cell is skipped for being easy.

Needs on Drive: the klein cache, `v34_ironman2_*.zip` (inputs) and `v34_ironman2_bc_*.zip`
(the `BC` references). Runtime → **A100**, then **Run all**. 600 edits, ~25 min, ~CAD 0.3.
"""

CELLS = [
    ("markdown", MD),
    ("code", '''# 1 · settings
A100_USD_PER_HOUR = 0.689     # CAD/h at 5.3 CU/h x CAD 0.13/CU; edit if your rate differs
ARMS = ("ER",)
MATRIX = "v36_ironman_er.csv"  # 600 cells: the iron-man-2 matrix x seeds 46/47/48
DRIVE_PROJECT_DIR = "Side projects and shi"
'''),
    ("code", '''# 2 · the stack. Call 2 only - no cropper, no BiRefNet, no parser, so none of the
#     onnxruntime trouble the call-1 notebooks have to work around.
!pip -q install -U diffusers transformers accelerate sentencepiece protobuf opencv-python-headless
import os, sys, torch
print('gpu:', torch.cuda.get_device_name(0))
assert 'A100' in torch.cuda.get_device_name(0), 'Runtime -> Change runtime type -> A100'
'''),
    ("code", f'''# 3 · the bundle. klein_local.py and v3lib.py are the repo's own, byte for byte, so the
#     model call here is the model call of record.
!cd /content && rm -rf v36 && wget -q -O v36.zip https://github.com/101011101/magichour_takehome/raw/{BRANCH}/v36_bundle.zip && unzip -qo v36.zip -d v36
%cd /content/v36
sys.path.insert(0, 'lib')
for f in ('lib/klein_local.py', 'lib/v3lib.py', 'lib/run_v36.py', MATRIX):
    assert os.path.exists(f), f'bundle incomplete: {{f}} - is the latest v36_bundle.zip pushed to {BRANCH}?'
import csv
rows = list(csv.DictReader(open(MATRIX)))
print(len(rows), 'cells,', len({{r['set_id'] for r in rows}}), 'pairs,',
      sorted({{r['seed'] for r in rows}}), 'seeds')
'''),
    ("code", '''# 4 · Drive: the klein cache, the inputs, and BC's references. Nothing is recomputed -
#     ER differs from BC in the call-2 prompt and in nothing else, so it has to be given
#     BC's own references rather than fresh ones.
import glob, zipfile, shutil
from google.colab import drive
drive.mount('/content/drive')
MYDRIVE = '/content/drive/MyDrive'; BASE = os.path.join(MYDRIVE, DRIVE_PROJECT_DIR)
assert os.path.isdir(BASE), f'Drive project dir not found: {BASE}'
KLEIN = 'models--black-forest-labs--FLUX.2-klein-4B'
cands = [os.path.join(MYDRIVE, 'hf_cache'), os.path.join(BASE, 'tryon_models', 'hf_cache'),
         os.path.join(BASE, 'hf_cache')]
found = [c for c in cands if os.path.isdir(os.path.join(c, 'hub', KLEIN))]
os.environ['HF_HOME'] = found[0] if found else cands[0]
os.makedirs(os.environ['HF_HOME'], exist_ok=True)
print('HF_HOME', os.environ['HF_HOME'], '(klein cached)' if found else '(no cache - downloads ~13 GB once)')

def newest(pat):
    hits = sorted(glob.glob(os.path.join(BASE, 'v3_runs', pat)))
    assert hits, f'not on Drive: v3_runs/{pat}'
    return hits[-1]

want_people = {f"inputs/{r['person']}.jpg" for r in rows}
want_refs   = {f"refs/{r['garment']}__BC.jpg" for r in rows}
for pat, want in (('v34_ironman2_2*.zip', want_people), ('v34_ironman2_bc_*.zip', want_refs)):
    z = newest(pat)
    with zipfile.ZipFile(z) as zz:
        missing = want - set(zz.namelist())
        assert not missing, f'{os.path.basename(z)} is missing {len(missing)}, e.g. {sorted(missing)[:3]}'
        for n in sorted(want):
            zz.extract(n, 'run')
    print(f'{os.path.basename(z)}: {len(want)} files')
'''),
    ("code", '''# 5 · load klein once, timed
import klein_local as K
K.load(); K.info()
'''),
    ("code", '''# 6 · the prompt, printed as it will be sent, and one cell before the other 599
import run_v36 as V, numpy as np, cv2
from PIL import Image
from IPython.display import display
print('ER:', V.PROMPT['ER'])

sub = 'probe_set.csv'
with open(sub, 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerow(rows[0])
V.main(sub, arms=ARMS, gpu_usd_per_hour=A100_USD_PER_HOUR)

def side(paths, h=430):
    ims = [cv2.imread(p) for p in paths if os.path.exists(p)]
    fit = [cv2.resize(i, (max(1, int(i.shape[1] * h / i.shape[0])), h)) for i in ims]
    w = max(f.shape[1] for f in fit)
    return Image.fromarray(cv2.cvtColor(np.hstack(
        [np.pad(f, ((0, 0), (0, w - f.shape[1]), (0, 0)), constant_values=255) for f in fit]),
        cv2.COLOR_BGR2RGB))

r0 = rows[0]
print(r0['set_id'], 'seed', r0['seed'], '- person, BC reference, ER')
display(side([f"run/inputs/{r0['person']}.jpg", f"run/refs/{r0['garment']}__BC.jpg",
              f"run/gen/{r0['set_id']}__ER__s{r0['seed']}.jpg"]))
'''),
    ("code", '''# 7 · the 600 edits (resumable - rerun after any disconnect and it skips what is on disk)
import json
V.main(MATRIX, arms=ARMS, gpu_usd_per_hour=A100_USD_PER_HOUR)
print(json.dumps(json.load(open('run/meta/cost_v36.json')), indent=1))
'''),
    ("code", '''# 8 · every cell landed?
made = len(glob.glob('run/gen/*__ER__*.jpg'))
print(f'ER {made}/{len(rows)} cells')
assert made == len(rows), 'incomplete - rerun cell 7, it resumes'
missing = [r for r in rows if not os.path.exists(f"run/gen/{r['set_id']}__ER__s{r['seed']}.jpg")]
assert not missing, missing[:3]
print('complete: 200 pairs x 3 seeds, the same 600 cells BC was counted on')
'''),
    ("code", '''# 9 · zip to Drive
import time
name = f"v36_ironman_er_{time.strftime('%Y%m%d_%H%M')}"
with zipfile.ZipFile(f'/content/{name}.zip', 'w', zipfile.ZIP_DEFLATED) as z:
    for f in os.listdir('run/gen'):    z.write('run/gen/' + f,    'gen/' + f)
    for f in os.listdir('run/refs'):   z.write('run/refs/' + f,   'refs/' + f)
    for f in os.listdir('run/inputs'): z.write('run/inputs/' + f, 'inputs/' + f)
    for f in os.listdir('run/meta'):   z.write('run/meta/' + f,   'meta/' + f)
    z.write(MATRIX, MATRIX)
with zipfile.ZipFile(f'/content/{name}.zip') as z:
    assert z.testzip() is None, 'the zip is corrupt - do not trust it'
    print(len(z.namelist()), 'files')
os.makedirs(os.path.join(BASE, 'v3_runs'), exist_ok=True)
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
    nb = {"cells": cells, "metadata": {
        "accelerator": "GPU",
        "colab": {"provenance": [], "gpuType": "A100"},
        "kernelspec": {"display_name": "Python 3", "name": "python3"},
        "language_info": {"name": "python"}},
        "nbformat": 4, "nbformat_minor": 0}
    json.dump(nb, open(OUT, "w"), indent=1)
    print(f"{os.path.relpath(OUT, REPO)}  ({len(cells)} cells)")


if __name__ == "__main__":
    main()
