"""Write `v3/colab/v36_limbclause.ipynb` — the dynamic limb clause on call 2, on an A100.

Generated rather than hand-edited so the cells stay diffable.

  python3 v3/build/make_v36_limb_notebook.py
"""
import json
import os

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(REPO, "v3", "colab", "v36_limbclause.ipynb")
BRANCH = "v3.3-lock"

MD = """# v3.6 — the limb clause, dynamic against static

V2's dynamic prompting had one rule: **never name a body part the crop excludes.** Call 1
has obeyed it since v3.1 (`v3lib.FRAME_CLAUSE`, picked by a pose read). Call 2 never has.
This notebook tests it there, as a matched pair over `ER`:

| arm | call 2 |
|---|---|
| `ER` | the verb change alone — the incumbent for this comparison |
| `ERD` | `ER` + a limb clause **built per cell** from a MediaPipe Pose read of image 1: names hands only if the wrists are in frame, feet only if the ankles or foot-index are, and **says nothing at all** when neither is |
| `ERS` | `ER` + that clause **always**, whichever parts the photograph actually shows |

`ERS` is not a strawman, it is the control: it is the only thing that can say whether the
read is doing any work, or whether naming a limb is harmless and the machinery is dead
weight. On this set the two arms genuinely differ — **the feet are out of frame on 57 of
the 150 cells**, so `ERS` names feet on 38% of cells that have none, and `ERD` stays quiet.

**Why a pose read and not BiRefNet.** BiRefNet returns a matte — a silhouette with no part
labels — so it cannot answer "is a foot in frame". MediaPipe Pose already returns a
visibility *and* a coordinate per landmark, so the question is a read rather than a
boundary hunt. That is the same mechanism `v3lib.framing()` uses; wrists (15/16) and
foot-index (31/32) are read in `run_v36.py` rather than by widening `v3lib.JOINTS`, which
every arm of record depends on.

The set is `v36_editset.csv` — the 29 cells `BC` failed and 121 it passed, so a rescue and
a regression are both measurable. Runtime → **A100**, then **Run all**. 300 edits, ~13 min,
~CAD 0.15.
"""

CELLS = [
    ("markdown", MD),
    ("code", '''# 1 · settings
A100_USD_PER_HOUR = 0.689     # CAD/h at 5.3 CU/h x CAD 0.13/CU; edit if your rate differs
ARMS = ("ERD", "ERS")         # ER, EFR, EX and E0 come off Drive from the earlier session
MATRIX = "v36_editset.csv"    # 150 cells: 29 BC failures + 121 BC passes
DRIVE_PROJECT_DIR = "Side projects and shi"
'''),
    ("code", '''# 2 · the stack. mediapipe is here and nowhere else in v3.6: ERD needs the pose read.
#     Still no BiRefNet and no cropper, so the onnxruntime problem stays out of this run.
!pip -q install -U diffusers transformers accelerate sentencepiece protobuf mediapipe opencv-python-headless
import os, sys, torch
print('gpu:', torch.cuda.get_device_name(0))
assert 'A100' in torch.cuda.get_device_name(0), 'Runtime -> Change runtime type -> A100'
'''),
    ("code", f'''# 3 · the bundle
!cd /content && rm -rf v36 && wget -q -O v36.zip https://github.com/101011101/magichour_takehome/raw/{BRANCH}/v36_bundle.zip && unzip -qo v36.zip -d v36
%cd /content/v36
sys.path.insert(0, 'lib')
for f in ('lib/klein_local.py', 'lib/v3lib.py', 'lib/run_v36.py', MATRIX):
    assert os.path.exists(f), f'bundle incomplete: {{f}} - is the latest v36_bundle.zip pushed to {BRANCH}?'
import csv
rows = list(csv.DictReader(open(MATRIX)))
print(len(rows), 'cells:', sum(r['bc'] == 'fail' for r in rows), 'BC failures +',
      sum(r['bc'] == 'ok' for r in rows), 'BC passes')
'''),
    ("code", '''# 4 · Drive: the klein cache, the pose model, the inputs and BC's references - and the
#     earlier v3.6 session, so the finished set carries every arm and the page can show
#     them side by side. Nothing already made is remade.
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
os.environ['V3_MODEL_DIR'] = os.path.join(BASE, 'v3_models')   # the pose model persists here
for p in (os.environ['HF_HOME'], os.environ['V3_MODEL_DIR']): os.makedirs(p, exist_ok=True)
print('HF_HOME', os.environ['HF_HOME'], '(klein cached)' if found else '(no cache - downloads ~13 GB once)')

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
        assert not missing, f'{os.path.basename(z)} is missing {len(missing)}, e.g. {sorted(missing)[:3]}'
        for n in sorted(want): zz.extract(n, 'run')
    print(f'{os.path.basename(z)}: {len(want)} files')

prev = newest('v36_editprompts_*.zip', required=False)
if prev:
    with zipfile.ZipFile(prev) as zz:
        for n in zz.namelist():
            if n.startswith('gen/'): zz.extract(n, 'run')
    print(f'{os.path.basename(prev)}: {len(glob.glob("run/gen/*.jpg"))} cells already made')
else:
    print('no earlier v3.6 session on Drive - this run will carry ERD and ERS only')
'''),
    ("code", '''# 5 · load klein once, timed
import klein_local as K
K.load(); K.info()
'''),
    ("code", '''# 6 · what the read actually says, before any of it is sent. If the two arms do not
#     differ on a good share of cells, the dynamic machinery has nothing to prove.
import collections, cv2
import run_v36 as V, v3lib as L
paths = L.fetch_models(persist=os.environ['V3_MODEL_DIR'])
seen = {p: tuple(sorted(V.limbs(cv2.imread(f'run/inputs/{p}.jpg'), paths)))
        for p in sorted({r['person'] for r in rows})}
cells = collections.Counter(seen[r['person']] for r in rows)
for k, n in cells.most_common():
    print(f"  {str(k or '(neither)'):24s} {n:3d} cells   ->  {V.limb_clause(list(k)) or '(no clause - plain ER)'}"[:150])
diff = sum(n for k, n in cells.items() if set(k) != {'hands', 'feet'})
print(f'\\nERD and ERS differ on {diff}/{len(rows)} cells')
print('\\nERS every cell:', V.PROMPT['ERS'])
'''),
    ("code", '''# 7 · the run (resumable - rerun after any disconnect and it skips what is on disk)
import json
V.main(MATRIX, arms=ARMS, gpu_usd_per_hour=A100_USD_PER_HOUR)
print(json.dumps(json.load(open('run/meta/cost_v36.json')), indent=1))
'''),
    ("code", '''# 8 · every cell landed, and what each dynamic cell was actually sent
made = json.load(open('run/meta/prompts_v36.json'))
short = []
for a in ('E0', 'ER', 'EFR', 'EX') + ARMS:
    n = len(glob.glob(f'run/gen/*__{a}__*.jpg'))
    print(f'  {a:4s} {n}/{len(rows)} cells' + ('' if n == len(rows) else '   (not in this session)'))
    if a in ARMS and n < len(rows): short.append(a)
assert not short, f'incomplete arms: {short} - rerun cell 7, it resumes'
byclause = collections.Counter(tuple(v['in_frame']) for v in made.values())
print('\\nERD, what the read found per cell:', dict(byclause))
'''),
    ("code", '''# 9 · zip to Drive
import time
name = f"v36_limbclause_{time.strftime('%Y%m%d_%H%M')}"
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
