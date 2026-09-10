"""Write `v3/colab/v36_editprompts.ipynb` — the v3.6 call-2 prompt run, on an A100.

The notebook is generated rather than hand-edited so the cells stay diffable.

  python3 v3/build/make_v36_notebook.py
"""
import json
import os

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(REPO, "v3", "colab", "v36_editprompts.ipynb")
BRANCH = "v3.3-lock"

MD = f"""# v3.6 — call 2's prompt, on both sides of `BC`'s record

`BC` = the incumbent: klein bald pass → V2 cropper subtracts the head → klein edit. This
notebook **does not run call 1 at all**. Every arm is handed the two images the shipped
`BC` cell was handed — the person, and `refs/{{garment}}__BC.jpg` off Drive — on `BC`'s own
call-2 canvas. The only thing that varies is the prompt.

| arm | prompt | made here |
|---|---|---|
| `E0` | the shipped prompt, unchanged since V2 | no — the archive **is** this arm, and the verdicts were made on it |
| `ER` | E0's verb rewritten: *replace the clothing*, not *dress the person* | yes |
| `EFR` | `ER` + the no-blend paragraph | yes |
| `EX` | the maximal prompt: removal, layering, piece count, limb count, framing | yes |

**The set is both sides of the record** — `v36_editset.csv`, 150 cells: the **29 the
reviewer marked FAIL** for `BC` and **121 it left unmarked**, sampled with a fixed seed
from the other 571. A prompt tested only on failures cannot be adopted: the 29 say what a
longer prompt buys, the 121 say what it costs, and the second number is the one that
decides. Every cell already carries a `BC` verdict, so both numbers land on the same
protocol.

Needs on Drive: the klein HF cache, session 1's inputs (`v34_ironman2_*.zip`) and the BC
arm (`v34_ironman2_bc_*.zip`). Runtime → **A100**, then **Run all**. 450 edits, ~25 min,
~CAD 0.3.
"""

CELLS = [
    ("markdown", MD),
    ("code", '''# 1 · settings
A100_USD_PER_HOUR = 0.689     # CAD/h at 5.3 CU/h x CAD 0.13/CU; edit if your rate differs
ARMS = ("ER", "EFR", "EX")    # E0 is the archive, not a call
MATRIX = "v36_editset.csv"    # 150 cells: 29 BC failures + 121 BC passes
DRIVE_PROJECT_DIR = "Side projects and shi"
'''),
    ("code", '''# 2 · the stack. No cropper, no BiRefNet, no parser, no mediapipe - this run is call 2
#     only, so the onnxruntime problem the other notebooks fight simply is not here.
!pip -q install -U diffusers transformers accelerate sentencepiece protobuf opencv-python-headless
import os, sys, torch
print('gpu:', torch.cuda.get_device_name(0))
assert 'A100' in torch.cuda.get_device_name(0), 'Runtime -> Change runtime type -> A100'
'''),
    ("code", f'''# 3 · the bundle: three library files and the set. klein_local.py and v3lib.py are the
#     repo's own, byte for byte, so the model call here is the model call of record.
!cd /content && rm -rf v36 && wget -q -O v36.zip https://github.com/101011101/magichour_takehome/raw/{BRANCH}/v36_bundle.zip && unzip -qo v36.zip -d v36
%cd /content/v36
sys.path.insert(0, 'lib')
for f in ('lib/klein_local.py', 'lib/v3lib.py', 'lib/run_v36.py', MATRIX):
    assert os.path.exists(f), f'bundle incomplete: {{f}} - is v36_bundle.zip pushed to {BRANCH}?'
import csv
rows = list(csv.DictReader(open(MATRIX)))
print(len(rows), 'cells:', sum(r['bc'] == 'fail' for r in rows), 'BC failures +',
      sum(r['bc'] == 'ok' for r in rows), 'BC passes')
'''),
    ("code", '''# 4 · Drive: the klein cache, session 1's inputs, and the BC arm. Nothing is recomputed -
#     the references and the E0 archive are the records this run is measured against, and
#     redrawing them would break the pairing with the reviewer's verdicts.
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

want_people   = {f"inputs/{r['person']}.jpg" for r in rows}
want_refs     = {f"refs/{r['garment']}__BC.jpg" for r in rows}
want_archive  = {f"gen/{r['set_id']}__BC__s{r['seed']}.jpg" for r in rows}
os.makedirs('run/gen', exist_ok=True)
for pat, want in ((\'v34_ironman2_2*.zip\', want_people),
                  (\'v34_ironman2_bc_*.zip\', want_refs | want_archive)):
    z = newest(pat)
    with zipfile.ZipFile(z) as zz:
        have = set(zz.namelist())
        missing = want - have
        assert not missing, f'{os.path.basename(z)} is missing {len(missing)}, e.g. {sorted(missing)[:3]}'
        for n in sorted(want):
            zz.extract(n, 'run')
    print(f'{os.path.basename(z)}: {len(want)} files')

# the archive, renamed in place as arm E0 - the control, not a call
for r in rows:
    src = f"run/gen/{r['set_id']}__BC__s{r['seed']}.jpg"
    shutil.copy(src, src.replace('__BC__', '__E0__'))
print('E0 (archive):', len(glob.glob('run/gen/*__E0__*.jpg')), 'cells')
'''),
    ("code", '''# 5 · load klein once, timed
import klein_local as K
K.load(); K.info()
'''),
    ("code", '''# 6 · one cell through all three prompts, before paying for the set. The cell is a
#     seed-stable BC failure, so a prompt that reaches anything should show it here.
import numpy as np, cv2
from PIL import Image
from IPython.display import display
import run_v36 as V

probe = [r for r in rows if r['bc'] == 'fail'][0]
for a in ARMS: print(f'{a}: {V.PROMPT[a]}\\n')

sub = 'probe_set.csv'
with open(sub, 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(probe)); w.writeheader(); w.writerow(probe)
V.main(sub, arms=ARMS, gpu_usd_per_hour=A100_USD_PER_HOUR)

def row(paths, h=430):
    ims = [cv2.imread(p) for p in paths if os.path.exists(p)]
    fit = [cv2.resize(i, (max(1, int(i.shape[1] * h / i.shape[0])), h)) for i in ims]
    w = max(f.shape[1] for f in fit)
    return Image.fromarray(cv2.cvtColor(np.hstack(
        [np.pad(f, ((0, 0), (0, w - f.shape[1]), (0, 0)), constant_values=255) for f in fit]),
        cv2.COLOR_BGR2RGB))

sid, s = probe['set_id'], probe['seed']
print(sid, 'seed', s, '- person, BC reference, E0 (archive),', ', '.join(ARMS))
display(row([f"run/inputs/{probe['person']}.jpg", f"run/refs/{probe['garment']}__BC.jpg",
             f'run/gen/{sid}__E0__s{s}.jpg'] + [f'run/gen/{sid}__{a}__s{s}.jpg' for a in ARMS]))
'''),
    ("code", '''# 7 · the run (resumable - rerun after any disconnect and it skips what is on disk)
import json
import run_v36 as V
V.main(MATRIX, arms=ARMS, gpu_usd_per_hour=A100_USD_PER_HOUR)
print(json.dumps(json.load(open('run/meta/cost_v36.json')), indent=1))
'''),
    ("code", '''# 8 · every cell landed?
short = []
for a in ('E0',) + ARMS:
    n = len(glob.glob(f'run/gen/*__{a}__*.jpg'))
    print(f'  {a:4s} {n}/{len(rows)} cells')
    if n < len(rows): short.append(a)
assert not short, f'incomplete arms: {short} - rerun cell 7, it resumes'
print(f'\\ncomplete: {len(rows) * (len(ARMS) + 1)} cells, {len(ARMS) + 1} arms, one seed each')
'''),
    ("code", '''# 9 · zip outputs, the references they were made from, and meta to Drive
import time
name = f"v36_editprompts_{time.strftime('%Y%m%d_%H%M')}"
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
