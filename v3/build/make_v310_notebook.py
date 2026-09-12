"""Write `v3/colab/v310_a100.ipynb` - the no-upscale canvas against the shipped one, on the
whole fold, call 2 only.

  python3 v3/build/make_v310_notebook.py
"""
import json
import os

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(REPO, "v3", "colab", "v310_a100.ipynb")
BRANCH = "v3.3-lock"

MD = """# v3.10 — the canvas without the upscale, on the whole fold

One question, on all 600 cells of the iron-man-2 matrix: **does call 2 need to scale the person
photo up to 1 MP?**

| arm | call-2 canvas |
|---|---|
| `SCALE` | **the rule of record**: area 2²⁰, aspect kept, **up** or down, floor 32 |
| `NOSCALE` | **the candidate**: the photo's own size under a 1 MP bound, floor 32, never upscaled |

**Why again, after v3.9.** v3.9 measured this on 93 cells and got `NOSCALE` 22 : `SCALE` 8
(p=0.016) — but the win was almost entirely on cells that were already failing (20:3), it
**reversed** on the 31 that already passed (2:5), and it was *weakest* where the upscale was
largest, which is backwards for the mechanism it would need. v3.8's own adoption rule is that
an arm tested on failures cannot be adopted on failures; what decides it is the cost on passing
cells. There are **547** of those here.

**One variable.** Every cell of both arms is handed the **archived** `refs/{g}__BC.jpg` of iron
man 2, unchanged — no bald pass and no crop runs in this notebook, which is also what makes
1,056 generations affordable. Person photos are bounded to 2²⁰ px for **both** arms, so the only
difference is whether a photo under 1 MP is scaled up to it.

**Not poolable with v3.9**, which rebuilt its references under the 1 MP bound. Both runs are
internally consistent; their marks must not be merged.

**Everything runs on the production transformer** — `Photoroom/FLUX.2-klein-4b-fp8-diffusers`
`transformer_bf16` @ `408c457f`, with BFL's text encoder, VAE, scheduler and tokenizer @
`e7b7dc27`.

**144 of the 600 cells are no-ops** — the person photo is already at the bound, so both rules
give the same canvas and there is nothing to compare. They are not generated.

Needs on Drive under `v3_runs/`: `v34_ironman2_*.zip` and `v34_ironman2_bc_*.zip`.
Runtime → **A100**, then **Run all**. ≈1,056 calls, ≈43 min, ≈CAD 0.50.
"""

CELLS = [
    ("markdown", MD),
    ("code", '''# 1 · settings
A100_CAD_PER_HOUR = 0.689
MATRIX = "v310_set.csv"
ARMS = ("SCALE", "NOSCALE")
DRIVE_PROJECT_DIR = "Side projects and shi"
BFL_REPO, BFL_REV = "black-forest-labs/FLUX.2-klein-4B", "e7b7dc27f91deacad38e78976d1f2b499d76a294"
PR_REPO, PR_REV = "Photoroom/FLUX.2-klein-4b-fp8-diffusers", "408c457f3589e17a1be1dae5bf0dcaf09cd4985f"
PR_SUB = "transformer_bf16"
'''),
    ("code", '''# 2 · Drive and the klein cache
import os
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
print('HF_HOME', os.environ['HF_HOME'], '(klein cached)' if found else '(klein downloads)')
'''),
    ("code", f'''# 3 · install and the bundle. Call 2 only - no cropper, so no onnxruntime, no mediapipe
!pip -q install -U diffusers transformers accelerate sentencepiece protobuf opencv-python-headless
!cd /content && rm -rf v310 && wget -q -O v310.zip https://github.com/101011101/magichour_takehome/raw/{BRANCH}/v310_bundle.zip && unzip -qo v310.zip -d v310
%cd /content/v310
import sys, torch, cv2
sys.path.insert(0, 'lib')
for f in ('lib/klein_local.py', 'lib/v3lib.py', 'lib/run_v36.py', 'lib/run_v310.py', MATRIX):
    assert os.path.exists(f), f'bundle incomplete: {{f}} - is v310_bundle.zip pushed to {BRANCH}?'
assert 'A100' in torch.cuda.get_device_name(0), 'Runtime > Change runtime type > A100'
print(torch.cuda.get_device_name(0))
'''),
    ("code", '''# 4 · the inputs of record off Drive: the person photos, and iron man 2's BC references
#     exactly as they are - this run never rebuilds a reference
import csv, glob, zipfile
rows = list(csv.DictReader(open(MATRIX)))
persons = sorted({r['person'] for r in rows}); garments = sorted({r['garment'] for r in rows})

def pick(pat, exclude=None):
    zs = [z for z in sorted(glob.glob(os.path.join(BASE, 'v3_runs', pat)))
          if not (exclude and exclude in os.path.basename(z))]
    assert zs, f'no {pat} on Drive under v3_runs/'
    return zs[-1]

# '_bc_' sorts after the digits, so a bare v34_ironman2_*.zip glob would resolve to the BC zip
want = {pick('v34_ironman2_*.zip', exclude='_bc_'): {f'inputs/{p}.jpg' for p in persons},
        pick('v34_ironman2_bc_*.zip'): {f'refs/{g}__BC.jpg' for g in garments}}
for zp, names in want.items():
    with zipfile.ZipFile(zp) as z:
        missing = names - set(z.namelist())
        assert not missing, f'{os.path.basename(zp)} is missing {sorted(missing)[:3]}'
        z.extractall('run', members=sorted(names))
    print(f'{os.path.basename(zp)}: {len(names)} files')
noop = sum(r['noscale_noop'] == '1' for r in rows)
print(f'{len(rows)} cells · {len(persons)} persons · {len(garments)} references · '
      f'{noop} no-ops · {2 * len(rows) - noop} generations expected')
'''),
    ("code", '''# 5 · weights at pinned revisions; klein with Photoroom's transformer in BFL's place
from huggingface_hub import snapshot_download
import klein_local as K
bfl = snapshot_download(BFL_REPO, revision=BFL_REV,
                        ignore_patterns=['flux-2-klein-4b.safetensors', '*.jpg'])
pr = snapshot_download(PR_REPO, revision=PR_REV, allow_patterns=[f'{PR_SUB}/*'])
assert bfl.rstrip('/').endswith(BFL_REV) and pr.rstrip('/').endswith(PR_REV), (bfl, pr)
K.load(repo=bfl, transformer=(pr, PR_SUB))
print(K.info())
assert K.info().get('transformer', '').startswith(pr), 'the transformer swap did not take'
'''),
    ("code", '''# 6 · one cell end to end before paying for the fold
import run_v310 as V
V.main(MATRIX, arms=ARMS, gpu_usd_per_hour=A100_CAD_PER_HOUR, limit=1)
'''),
    ("code", '''# 7 · the run (resumable - rerun after a disconnect and it skips what is on disk)
import json
V.main(MATRIX, arms=ARMS, gpu_usd_per_hour=A100_CAD_PER_HOUR)
print(json.dumps(json.load(open('run/meta/cost_v310.json')), indent=1))
'''),
    ("code", '''# 8 · every cell landed, and the canvases are what the set said they would be
meta = json.load(open('run/meta/v310_meta.json'))
noop = sum(1 for c in meta['cells'].values() if c.get('NOSCALE_noop'))
want = {'SCALE': len(rows), 'NOSCALE': len(rows) - noop}
short = []
for a in ARMS:
    n = len(glob.glob(f'run/gen/*__{a}__*.jpg'))
    print(f'  {a:8s} {n}/{want[a]} cells')
    if n < want[a]: short.append(a)
assert not short, f'incomplete: {short} - rerun cell 7, it resumes'
bad = [k for k, c in meta['cells'].items()
       if 'NOSCALE' in c and 'SCALE' in c and c['NOSCALE'] != c['SCALE'] and c.get('NOSCALE_noop')]
assert not bad, f'no-op flag disagrees with the canvases: {bad[:3]}'
prior = {}
for r in rows:
    if r['noscale_noop'] != '1': prior[r['prior']] = prior.get(r['prior'], 0) + 1
print(f'  no-ops {noop} · cards to mark {sum(prior.values())} {prior}')
'''),
    ("code", '''# 9 · zip, download, then release the GPU - verified before anything is deleted
TERMINATE_WHEN_DONE = True  #@param {type:"boolean"}
DOWNLOAD_GRACE_SECONDS = 180  #@param {type:"integer"}

import shutil, time
name = f"v310_a100_{time.strftime('%Y%m%d_%H%M')}"
zip_path = f'/content/{name}.zip'
with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as z:
    for f in os.listdir('run/gen'):   z.write('run/gen/' + f, 'gen/' + f)
    for f in os.listdir('run/refs'):  z.write('run/refs/' + f, 'refs/' + f)
    for f in os.listdir('run/in1mp'): z.write('run/in1mp/' + f, 'in1mp/' + f)
    for f in os.listdir('run/meta'):  z.write('run/meta/' + f, 'meta/' + f)
    z.write(MATRIX, MATRIX)
with zipfile.ZipFile(zip_path) as z:
    assert z.testzip() is None, 'the zip is corrupt'
    names = z.namelist()
    for need in ('meta/v310_meta.json', 'meta/cost_v310.json', 'meta/timings_v310.csv'):
        assert need in names, f'missing {need}'
size_mb = os.path.getsize(zip_path) / 1e6
drive_copy = None
try:
    os.makedirs(os.path.join(BASE, 'v3_runs'), exist_ok=True)
    drive_copy = os.path.join(BASE, 'v3_runs', f'{name}.zip')
    shutil.copy(zip_path, drive_copy)
except Exception as e:
    print(f'Drive copy failed ({e}); the browser download is the only copy')
print(f'{name}.zip · {len(names)} files · {size_mb:.1f} MB')
if drive_copy: print(f'Drive  {drive_copy}')
print(f'Local  {zip_path}')

from google.colab import files
downloaded = False
try:
    files.download(zip_path)
    downloaded = True
except Exception as e:
    print(f'download failed ({e}) - take it from Drive or /content')
if downloaded:
    print(f'downloading; waiting {DOWNLOAD_GRACE_SECONDS}s before the runtime is released')
    time.sleep(DOWNLOAD_GRACE_SECONDS)
if TERMINATE_WHEN_DONE and (downloaded or drive_copy):
    from google.colab import runtime
    print('releasing the GPU')
    runtime.unassign()
else:
    print('runtime kept - nothing was saved off this machine')
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
