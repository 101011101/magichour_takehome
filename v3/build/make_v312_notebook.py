"""Write `v3/colab/v312_flatlay.ipynb` - a region request on a photograph with no person in it.

  python3 v3/build/make_v312_notebook.py
"""
import json
import os

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(REPO, "v3", "colab", "v312_flatlay.ipynb")
BRANCH = "v3.3-lock"

MD = """# v3.12 — a region request on a garment photo with no person in it

**Runbo, reading the ticket:** *"So basically, this is saying that if the user uploads a flat lay
ghost mannequin 4 out of 10 times, it won't work in upper body and lower body mode?"*

The line he is reading comes from [v3.11 link 1](../../prd/v3/v3.11/EXPERIMENT.md): Pose reports a
hip on **6 of 10** flat-lay and ghost-mannequin photographs, which contain no person at all. That
number measures the **detector**, not the outcome, and no flat-lay has ever been run through
`upper` or `lower`. So the reading it invites — *the other 4 work* — has never been tested either
way. This run tests it.

What the two groups actually do, and why neither is the half the user asked for:

| what the detector does | what the request does | how it looks to a user |
|---|---|---|
| **reports a hip** (6 of 10 on record) | the band cuts at that row — on an image with no body in it | a **silent error**: nothing reports a problem |
| **reports nothing** (4 of 10) | the request falls back to `full` and records why | a **visible no-op**: the whole outfit is swapped |

The run is the shipping path, unchanged: `full` under `ER`, `upper`/`lower` under the
region-naming call 2, arm A. Nothing new is being tried — the point is to see what the shipped
thing does with an input the ticket tells the product not to send it.

**The picture that answers the question** is the hip line drawn on each photograph: it shows where
the cut lands, and on these images there is nothing anatomical for it to land on.

Nothing is needed on Drive: the photos come from the repo and the weights from Hugging Face.
Runtime → **A100**, then **Run all**.

| | klein calls | GPU time |
|---|---|---|
| 10 bald passes, 10 crops (one mask each, three regions off it), 60 edits | **70** | ≈2.5 min, ≈CAD 0.03 |

A fresh runtime also downloads ~16 GB of weights and loads the model before that.
"""

CELLS = [
    ("markdown", MD),
    ("code", '''# 1 · settings
import csv, glob, json, os, shutil, time, zipfile
A100_CAD_PER_HOUR = 0.689
MATRIX = "v312_set.csv"
# the shipping path only: full under ER, the halves under the region-named call 2
PLAN = (("A", "full", "S"), ("A", "upper", "R"), ("A", "lower", "R"))
DRIVE_PROJECT_DIR = "Side projects and shi"
BFL_REPO, BFL_REV = "black-forest-labs/FLUX.2-klein-4B", "e7b7dc27f91deacad38e78976d1f2b499d76a294"
PR_REPO, PR_REV = "Photoroom/FLUX.2-klein-4b-fp8-diffusers", "408c457f3589e17a1be1dae5bf0dcaf09cd4985f"
PR_SUB = "transformer_bf16"
'''),
    ("code", '''# 2 · the klein cache: Drive if a cache is already there, otherwise this runtime
import os
KLEIN = 'models--black-forest-labs--FLUX.2-klein-4B'
BASE = None
try:
    from google.colab import drive
    drive.mount('/content/drive')
    MYDRIVE = '/content/drive/MyDrive'
    cand = os.path.join(MYDRIVE, DRIVE_PROJECT_DIR)
    BASE = cand if os.path.isdir(cand) else None
    cands = [os.path.join(MYDRIVE, 'hf_cache')] + (
        [os.path.join(BASE, 'tryon_models', 'hf_cache'), os.path.join(BASE, 'hf_cache')] if BASE else [])
except Exception as e:
    print(f'Drive unavailable ({e}); everything stays on this runtime')
    cands = []
# only reuse a Drive cache that already holds klein - never write 16 GB of weights to Drive
found = [c for c in cands if os.path.isdir(os.path.join(c, 'hub', KLEIN))]
os.environ['HF_HOME'] = found[0] if found else '/content/hf_cache'
os.environ['V3_MODEL_DIR'] = os.path.join(BASE, 'v3_models') if BASE else '/content/v3_models'
for d in (os.environ['HF_HOME'], os.environ['V3_MODEL_DIR']): os.makedirs(d, exist_ok=True)
print('HF_HOME', os.environ['HF_HOME'], '(klein cached)' if found else '(klein downloads ~16 GB once)')
print('Drive  ', BASE or 'not used')
'''),
    ("code", f'''# 3 · install, with the onnxruntime-gpu whose CUDA provider actually loads, then the bundle
!pip -q install -U diffusers transformers accelerate sentencepiece protobuf mediapipe opencv-contrib-python-headless
!pip -q uninstall -y onnxruntime onnxruntime-gpu >/dev/null 2>&1
!pip -q install onnxruntime-gpu==1.22.0
import ctypes, glob, site, sys
dirs = sorted({{d for p in site.getsitepackages() for d in glob.glob(os.path.join(p, 'nvidia', '*', 'lib'))}})
os.environ['LD_LIBRARY_PATH'] = ':'.join(dirs + [os.environ.get('LD_LIBRARY_PATH', '')])
for d in dirs:
    for f in os.listdir(d):
        if '.so' in f and any(k in f for k in ('cudart', 'cublas', 'cudnn', 'cufft', 'curand')):
            try: ctypes.CDLL(os.path.join(d, f), mode=ctypes.RTLD_GLOBAL)
            except OSError: pass
os.environ['V2_ORT_GPU'] = '1'
!cd /content && rm -rf v312 && wget -q -O v312.zip https://github.com/101011101/magichour_takehome/raw/{BRANCH}/v312_bundle.zip && unzip -qo v312.zip -d v312
%cd /content/v312
import torch, cv2, onnxruntime as ort
sys.path.insert(0, 'lib')
# a rerun in a kernel that already imported these would keep the OLD module, whatever was
# just downloaded - so drop them and let the fresh bundle be imported
for _m in ('run_v312', 'run_v311', 'v3lib', 'klein_local', 'run_v36', 'ironman_bc_crop',
           'garment_crop', 'phase3_variants'):
    sys.modules.pop(_m, None)
for f in ('lib/klein_local.py', 'lib/v3lib.py', 'lib/run_v36.py', 'lib/run_v311.py',
          'lib/run_v312.py', 'lib/ironman_bc_crop.py', 'lib/garment_crop.py',
          'lib/phase3_variants.py', MATRIX):
    assert os.path.exists(f), f'bundle incomplete: {{f}} - is v312_bundle.zip pushed to {BRANCH}?'
assert hasattr(cv2, 'ximgproc'), 'plain opencv shadowed opencv-contrib - Runtime > Restart, run from cell 1'
assert 'A100' in torch.cuda.get_device_name(0), 'Runtime > Change runtime type > A100'
print(torch.cuda.get_device_name(0), '| onnxruntime', ort.__version__, ort.get_available_providers())
'''),
    ("code", '''# 4 · the photos, straight from the repo - ten product shots and two full-body people
import csv, urllib.request
import cv2
RAW = 'https://raw.githubusercontent.com/101011101/magichour_takehome/v3.3-lock'
rows = list(csv.DictReader(open(MATRIX)))
stems = sorted({r['person'] for r in rows} | {r['garment'] for r in rows})
if not os.path.exists('matrix.csv'):
    urllib.request.urlretrieve(f'{RAW}/v3/colab/matrix.csv', 'matrix.csv')
mx = list(csv.DictReader(open('matrix.csv')))
files = {r['person']: r['person_file'] for r in mx}
files.update({r['garment']: r['garment_file'] for r in mx})
# the ten product shots are garment-only and are not in the fold matrix, so they are named here
files.update({r['garment']: f"{r['garment']}.jpg" for r in rows if r['garment'] not in files})
DIRS = ('test_set1/garments', 'test_set1/people', 'test_set2/people', 'test_set2/clothes',
        'test_set3/people', 'test_set2/garments')
os.makedirs('run/inputs', exist_ok=True)
got = 0
for s in stems:
    dst = f'run/inputs/{s}.jpg'
    if os.path.exists(dst):
        got += 1; continue
    for d in DIRS:
        try:
            urllib.request.urlretrieve(f'{RAW}/{d}/{files[s]}', '/content/_dl')
        except Exception:
            continue
        im = cv2.imread('/content/_dl', cv2.IMREAD_COLOR)
        if im is None:
            continue
        cv2.imwrite(dst, im, [cv2.IMWRITE_JPEG_QUALITY, 95]); got += 1; break
    else:
        raise RuntimeError(f'{s} ({files[s]}) not found under any of {DIRS}')
print(f'{got} photos from the repo')
print(f'{len(rows)} cells · {len({r["garment"] for r in rows})} product garments · '
      f'{len({r["person"] for r in rows})} people · {len(rows) * len(PLAN)} try-ons')
'''),
    ("code", '''# 5 · weights at pinned revisions; klein with Photoroom's transformer in BFL's place
from huggingface_hub import snapshot_download
import klein_local as K
bfl = snapshot_download(BFL_REPO, revision=BFL_REV,
                        ignore_patterns=['flux-2-klein-4b.safetensors', '*.jpg'])
pr = snapshot_download(PR_REPO, revision=PR_REV, allow_patterns=[f'{PR_SUB}/*'])
K.load(repo=bfl, transformer=(pr, PR_SUB))
print(K.info())
assert K.info().get('transformer', '').startswith(pr), 'the transformer swap did not take'
'''),
    ("code", '''# 6 · the crops on CUDA, and the hip read on each product shot BEFORE anything is generated
import run_v312 as V
import run_v311 as V311
import garment_crop as GC, phase3_variants as P
GC._biref(); P._parser()
for name, sess in (('BiRefNet', GC._STATE['biref']), ('SCHP', P._HP['m'])):
    assert sess.get_providers()[0] == 'CUDAExecutionProvider', f'{name} fell back to CPU'
    print(f'{name:9s} {sess.get_providers()[0]}')
print('\\ncall 2, upper:\\n ', V311.call2('upper', 'R'))
print('\\ncall 2, lower:\\n ', V311.call2('lower', 'R'))
print('\\nthe hip read on the photographs themselves (no person is in any of them):')
hit = 0
for g in sorted({r['garment'] for r in rows}):
    im = V311.normalise(cv2.imread(f'run/inputs/{g}.jpg'))
    y, why = V311.hip_line(im)
    hit += y is not None
    print(f'  {g:6s} ' + (f'HIP REPORTED at {y / im.shape[0]:.2f} of height' if y is not None
                          else f'no hip: {why}'))
print(f'\\n{hit} of {len({r["garment"] for r in rows})} report a hip on a photograph with no person in it')
'''),
    ("code", '''# 7 · one garment end to end before paying for the rest
V.main(MATRIX, plan=PLAN, gpu_usd_per_hour=A100_CAD_PER_HOUR, limit=2)
'''),
    ("code", '''# 8 · the run (resumable - rerun after a disconnect and it skips what is on disk)
doc = V.main(MATRIX, plan=PLAN, gpu_usd_per_hour=A100_CAD_PER_HOUR)
print(json.dumps(json.load(open('run/meta/cost_v311.json')), indent=1))
'''),
    ("code", '''# 9 · the answer, per garment: what the detector said, and what the request did
want = len(rows) * len(PLAN)
have = len(glob.glob('run/gen/*.jpg'))
print(f'{have}/{want} try-ons · {len(glob.glob("run/hip/*__orig.jpg"))} hip overlays')
assert have == want, 'incomplete - rerun cell 8, it resumes'
for g, v in sorted(doc['garments'].items()):
    print(f'  {g:6s} {"HIP REPORTED" if v["hip_reported"] else "no hip      "} '
          f'upper={v["regions"]["upper"]["route"]:24s} lower={v["regions"]["lower"]["route"]}')
c = doc['counts']
print(f"\\n{c['cut_at_reported_hip']} cut at an invented row · {c['fell_back_to_full']} fell back "
      f"to the whole outfit · 0 returned the half that was asked for")
'''),
    ("code", '''# 10 · zip, download, then release the GPU
TERMINATE_WHEN_DONE = True  #@param {type:"boolean"}
DOWNLOAD_GRACE_SECONDS = 120  #@param {type:"integer"}

name = f"v312_a100_{time.strftime('%Y%m%d_%H%M')}"
zip_path = f'/content/{name}.zip'
with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as z:
    for sub in ('gen', 'refs', 'in1mp', 'hip', 'meta'):
        for f in os.listdir(f'run/{sub}'): z.write(f'run/{sub}/{f}', f'{sub}/{f}')
    z.write(MATRIX, MATRIX)
with zipfile.ZipFile(zip_path) as z:
    assert z.testzip() is None, 'the zip is corrupt'
    names = z.namelist()
    for need in ('meta/v312_flatlay.json', 'meta/cost_v311.json'):
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
