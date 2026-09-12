"""Write `v3/colab/v311_a100.ipynb` - the garment-type selector, two ways of building it.

  python3 v3/build/make_v311_notebook.py
"""
import json
import os

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(REPO, "v3", "colab", "v311_a100.ipynb")
BRANCH = "v3.3-lock"

MD = """# v3.11 — choosing the garment type: upper, lower, or the whole outfit

**Runbo, verbatim:** *"You didn't include a feature that allows users to choose the garment type,
right, like if the user uploads a full body image but just wants to swap like the top."*

So the outcome being asked for is **person-side**: a full-body photograph goes in with
`REGION=upper`, the top is swapped, and the person's own trousers are still their own trousers
afterwards. The reference is only the means — and there are two ways to build it, so this run
puts them side by side.

| arm | how the reference is built |
|---|---|
| **A — crop only** | call 1 is `BALD_PROMPT` **byte for byte**; the band is cut on the **mask**, before the bbox |
| **B — modify call 1** | call 1 *also* replaces the half you did not select with a plain white garment, then the same band |

B's idea is that a uniform, unpatterned region is an easier thing for the matte and the parser to
cut against, so the reference comes out cleaner. **B departs from the call-1 prompt of record**,
so no v3.8/v3.10 number transfers to it; A is the control precisely because its call 1 is
untouched. Call 2 is `ER`, byte for byte, in both arms — the only variable is how the reference
was built.

`full` has nothing unselected to neutralise, so B's call 1 would be A's: it is generated once,
under A.

**The band.** The hip line is the mean of Pose landmarks 23/24, counting only hips that are
confident *and* inside the frame. No pose, no in-frame hip, or a band keeping under 2% of the
subject **falls back to `full` and records why** — never a guessed fraction of the frame. It fills
a stub: `garment_crop.SELECT_REGION` and `region_band` have sat unimplemented since V2.

**The set is cells that already work** — every pair is marked clean in the v3.10 count, and every
person reads `full_body` on the framing read, which is Runbo's case. A failure here is therefore
attributable to the selector rather than to a pair that was already broken.

**What to look for**, per try-on: did the selected half get swapped, and **did the unselected half
survive untouched**. The second question decides whether a selector is a crop change or a much
larger piece of work.

Nothing is needed on Drive: the photos come from the repo and the weights from Hugging Face.
Runtime → **A100**, then **Run all**.
≈78 calls, ≈8 min, ≈CAD 0.09.
"""

CELLS = [
    ("markdown", MD),
    ("code", '''# 1 · settings
import csv, glob, json, os, shutil, time, zipfile
A100_CAD_PER_HOUR = 0.689
MATRIX = "v311_set.csv"
PLAN = (("A", "full"), ("A", "upper"), ("A", "lower"), ("B", "upper"), ("B", "lower"))
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
!cd /content && rm -rf v311 && wget -q -O v311.zip https://github.com/101011101/magichour_takehome/raw/{BRANCH}/v311_bundle.zip && unzip -qo v311.zip -d v311
%cd /content/v311
import torch, cv2, onnxruntime as ort
sys.path.insert(0, 'lib')
for f in ('lib/klein_local.py', 'lib/v3lib.py', 'lib/run_v36.py', 'lib/run_v311.py',
          'lib/ironman_bc_crop.py', 'lib/garment_crop.py', 'lib/phase3_variants.py', MATRIX):
    assert os.path.exists(f), f'bundle incomplete: {{f}} - is v311_bundle.zip pushed to {BRANCH}?'
assert hasattr(cv2, 'ximgproc'), 'plain opencv shadowed opencv-contrib - Runtime > Restart, run from cell 1'
assert 'A100' in torch.cuda.get_device_name(0), 'Runtime > Change runtime type > A100'
print(torch.cuda.get_device_name(0), '| onnxruntime', ort.__version__, ort.get_available_providers())
'''),
    ("code", '''# 4 · the photos, straight from the repo - every pair here is one the v3.10 count marked clean
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
# the originals, not the 340px report copies: canonical test-set directories only
DIRS = ('test_set1/people', 'test_set1/garments', 'test_set2/people', 'test_set2/clothes',
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
print(f'{len(rows)} cells · {len({r["garment"] for r in rows})} garments · '
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
    ("code", '''# 6 · the crops on CUDA, the two call-1 prompts as they will be sent, and the hip read
import run_v311 as V
import garment_crop as GC, phase3_variants as P
GC._biref(); P._parser()
for name, sess in (('BiRefNet', GC._STATE['biref']), ('SCHP', P._HP['m'])):
    assert sess.get_providers()[0] == 'CUDAExecutionProvider', f'{name} fell back to CPU'
    print(f'{name:9s} {sess.get_providers()[0]}')
import v3lib as L
print('\\ncall 1, arm A (the prompt of record):\\n ', L.BALD_PROMPT)
for region, p in V.BALD_NEUTRAL.items():
    print(f'\\ncall 1, arm B, REGION={region} (neutralises the other half):\\n  {p}')
print()
for g in sorted({r['garment'] for r in rows}):
    im = V.normalise(cv2.imread(f'run/inputs/{g}.jpg'))
    y, why = V.hip_line(im)
    print(f'  {g[:48]:48s} hip_y={"-" if y is None else round(y, 1)}'
          f'{"" if y is None else f" ({y / im.shape[0]:.2f} of height)"}{"  " + why if why else ""}')
'''),
    ("code", '''# 7 · one garment end to end before paying for the rest
V.main(MATRIX, plan=PLAN, gpu_usd_per_hour=A100_CAD_PER_HOUR, limit=1)
'''),
    ("code", '''# 8 · the run (resumable - rerun after a disconnect and it skips what is on disk)
import json
V.main(MATRIX, plan=PLAN, gpu_usd_per_hour=A100_CAD_PER_HOUR)
print(json.dumps(json.load(open('run/meta/cost_v311.json')), indent=1))
'''),
    ("code", '''# 9 · what landed, and which references fell back
meta = json.load(open('run/meta/v311_meta.json'))
want = len(rows) * len(PLAN)
have = len(glob.glob('run/gen/*.jpg'))
print(f'{have}/{want} try-ons · {len(glob.glob("run/refs/*__bald_*.jpg"))} bald frames · '
      f'{len(glob.glob("run/refs/*_upper.jpg")) + len(glob.glob("run/refs/*_lower.jpg")) + len(glob.glob("run/refs/*_full.jpg"))} references')
assert have == want, 'incomplete - rerun cell 8, it resumes'
for g, v in meta['garments'].items():
    fell = {k: i['fallback'] for k, i in v.items() if i.get('fallback')}
    kept = {k: i.get('kept_fraction') for k, i in v.items() if i.get('kept_fraction') is not None}
    print(f'  {g[:44]:44s} hip={v.get("A_full", {}).get("hip_y")} kept={kept}'
          + (f' FELL BACK {fell}' if fell else ''))
'''),
    ("code", '''# 10 · zip, download, then release the GPU
TERMINATE_WHEN_DONE = True  #@param {type:"boolean"}
DOWNLOAD_GRACE_SECONDS = 120  #@param {type:"integer"}

import shutil, time
name = f"v311_a100_{time.strftime('%Y%m%d_%H%M')}"
zip_path = f'/content/{name}.zip'
with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as z:
    for sub in ('gen', 'refs', 'in1mp', 'meta'):
        for f in os.listdir(f'run/{sub}'): z.write(f'run/{sub}/{f}', f'{sub}/{f}')
    z.write(MATRIX, MATRIX)
with zipfile.ZipFile(zip_path) as z:
    assert z.testzip() is None, 'the zip is corrupt'
    names = z.namelist()
    for need in ('meta/v311_meta.json', 'meta/cost_v311.json'):
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
