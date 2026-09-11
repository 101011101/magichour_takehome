"""Write `v3/colab/v36_er2.ipynb` — ER's first sentence alone, on the failing cells.

Generated rather than hand-edited so the cells stay diffable.

  python3 v3/build/make_v36_er2_notebook.py
"""
import json
import os

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(REPO, "v3", "colab", "v36_er2.ipynb")
BRANCH = "v3.3-lock"

MD = """# `ER2` — the replace sentence, with nothing after it

Every call-2 prompt since V2 has carried a **hold clause**: *Keep the person's face,
identity, body and the background exactly as they are.* `ER2` drops it and sends the first
sentence alone:

> Replace the clothing in image 1 with the clothing in image 2.

The question is what that clause was buying. Two outcomes are worth having:

- **It was dead weight.** The shorter prompt does the same thing, and a 4-step distilled
  model is known to drift as prompts grow — so the shortest correct prompt is the one to
  ship.
- **It was load-bearing.** Identity, pose or background move without it, which prices the
  clause and closes the question for good.

**The set is only what currently fails** — `v36_er2_set.csv`, the union of BC's pass-2
failures (50) and the ER sweep's (18), **53 cells**. That is a diagnostic, not a rate:
selected on failure, so nothing here transfers to the fold. What it can show is whether the
shorter prompt reaches failures the longer one does not, and whether it breaks identity.

Call 1 does not run. Same references, same canvas, same seeds as every other v3.6 arm.
Runtime → **A100**, then **Run all**. 53 edits, ~3 min, ~CAD 0.1 (most of it model load).
"""

CELLS = [
    ("markdown", MD),
    ("code", '''# 1 · settings
A100_USD_PER_HOUR = 0.689
ARMS = ("ER2",)
MATRIX = "v36_er2_set.csv"     # 53 cells: every cell failing under BC pass 2 or the ER sweep
DRIVE_PROJECT_DIR = "Side projects and shi"
'''),
    ("code", '''# 2 · the stack. Call 2 only - no cropper, no parser, no mediapipe.
!pip -q install -U diffusers transformers accelerate sentencepiece protobuf opencv-python-headless
import os, sys, torch
print('gpu:', torch.cuda.get_device_name(0))
assert 'A100' in torch.cuda.get_device_name(0), 'Runtime -> Change runtime type -> A100'
'''),
    ("code", f'''# 3 · the bundle
!cd /content && rm -rf v36 && wget -q -O v36.zip https://github.com/101011101/magichour_takehome/raw/{BRANCH}/v36_bundle.zip && unzip -qo v36.zip -d v36
%cd /content/v36
sys.path.insert(0, 'lib')
import csv
for f in ('lib/klein_local.py', 'lib/v3lib.py', 'lib/run_v36.py', MATRIX):
    assert os.path.exists(f), f'bundle incomplete: {{f}} - is the latest v36_bundle.zip pushed to {BRANCH}?'
rows = list(csv.DictReader(open(MATRIX)))
print(len(rows), 'cells:', sum(r['bc2'] == 'fail' for r in rows), 'fail under BC,',
      sum(r['er'] == 'fail' for r in rows), 'under ER')
'''),
    ("code", '''# 4 · Drive: klein, the inputs, BC's references. Nothing is recomputed.
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
        assert not missing, f'{os.path.basename(z)} is missing {len(missing)}'
        for n in sorted(want): zz.extract(n, 'run')
    print(f'{os.path.basename(z)}: {len(want)} files')

# the ER cells for the same rows, off Drive, so the page can show ER beside ER2
prev = sorted(glob.glob(os.path.join(BASE, 'v3_runs', 'v36_ironman_er_*.zip')))
if prev:
    want_er = {f"gen/{r['set_id']}__ER__s{r['seed']}.jpg" for r in rows}
    with zipfile.ZipFile(prev[-1]) as zz:
        for n in sorted(want_er & set(zz.namelist())): zz.extract(n, 'run')
    print(f'{os.path.basename(prev[-1])}: {len(glob.glob("run/gen/*__ER__*.jpg"))} ER cells')
'''),
    ("code", '''# 5 · load klein once, timed
import klein_local as K
K.load(); K.info()
'''),
    ("code", '''# 6 · the two prompts, as they will be sent
import run_v36 as V
print('ER :', V.PROMPT['ER'])
print()
print('ER2:', V.PROMPT['ER2'])
'''),
    ("code", '''# 7 · the run (resumable)
import json
V.main(MATRIX, arms=ARMS, gpu_usd_per_hour=A100_USD_PER_HOUR)
print(json.dumps(json.load(open('run/meta/cost_v36.json')), indent=1))
'''),
    ("code", '''# 8 · every cell landed, and a first look at the risk this arm carries: without the
#     hold clause, does the face or the background move? Six cells, ER beside ER2.
import numpy as np, cv2
from PIL import Image
from IPython.display import display
made = len(glob.glob('run/gen/*__ER2__*.jpg'))
print(f'ER2 {made}/{len(rows)} cells')
assert made == len(rows), 'incomplete - rerun cell 7, it resumes'

def side(paths, h=380):
    ims = [cv2.imread(p) for p in paths if os.path.exists(p)]
    fit = [cv2.resize(i, (max(1, int(i.shape[1] * h / i.shape[0])), h)) for i in ims]
    w = max(f.shape[1] for f in fit)
    return Image.fromarray(cv2.cvtColor(np.hstack(
        [np.pad(f, ((0, 0), (0, w - f.shape[1]), (0, 0)), constant_values=255) for f in fit]),
        cv2.COLOR_BGR2RGB))

for r in rows[:6]:
    sid, s = r['set_id'], r['seed']
    print(sid, 'seed', s, '- person, reference, ER, ER2')
    display(side([f"run/inputs/{r['person']}.jpg", f"run/refs/{r['garment']}__BC.jpg",
                  f'run/gen/{sid}__ER__s{s}.jpg', f'run/gen/{sid}__ER2__s{s}.jpg']))
'''),
    ("code", '''# 9 · zip to Drive
import time
name = f"v36_er2_{time.strftime('%Y%m%d_%H%M')}"
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
             "source": src.rstrip("\\n").splitlines(keepends=True)}
        if kind == "code":
            c["execution_count"] = None
            c["outputs"] = []
        cells.append(c)
    nb = {"cells": cells, "metadata": {
        "accelerator": "GPU", "colab": {"provenance": [], "gpuType": "A100"},
        "kernelspec": {"display_name": "Python 3", "name": "python3"},
        "language_info": {"name": "python"}},
        "nbformat": 4, "nbformat_minor": 0}
    json.dump(nb, open(OUT, "w"), indent=1)
    print(f"{os.path.relpath(OUT, REPO)}  ({len(cells)} cells)")


if __name__ == "__main__":
    main()
