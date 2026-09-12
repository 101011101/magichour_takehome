"""Write `v3/colab/v39_a100.ipynb` - the upscale half of call 2's canvas, and the second crop,
both under a hard 1 MP bound, on the production transformer.

  python3 v3/build/make_v39_notebook.py
"""
import json
import os

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(REPO, "v3", "colab", "v39_a100.ipynb")
BRANCH = "v3.3-lock"

MD = """# v3.9 — the upscale, and the second crop

Two questions the shipped pipeline (`ER`) never asked, each against a **fresh baseline** built
here on the same pipeline — so the only thing that differs between an arm and its baseline is
the arm.

| arm | reference | call-2 canvas |
|---|---|---|
| `SCALE` | bald pass on the photo → head-subtracting crop | **the rule of record**: area 2²⁰, aspect kept, **up** or down, floor 32 |
| `NOSCALE` | `SCALE`'s | **no upscale**: the photo's own size, floor 32 |
| `CROP2` | **A4 crop** → bald pass on the crop → head-subtracting crop | the rule of record |

**Everything is bounded to 1 MP.** Every photo is re-normalised to ≤ 2²⁰ px — not v3lib's
1,150,000 — and the A4 crops are recomputed from the bounded photos, so no image anywhere in
this run exceeds 1 MP. `NOSCALE` is therefore exactly *"≤ 1 MP and otherwise untouched"*, and
the two arms differ only in whether small photos are scaled **up** to 1 MP.

**Everything runs on the production transformer** — `Photoroom/FLUX.2-klein-4b-fp8-diffusers`
`transformer_bf16` @ `408c457f`, with BFL's text encoder, VAE, scheduler and tokenizer @
`e7b7dc27`.

**The set** (`v39_set.csv`): every cell either blind sweep failed, plus the 40 cells both
passed that the transformer probe already used. `NOSCALE` cells whose canvas equals the
baseline's are no-ops and are not generated.

**Crops run on CPU** — every reference of record was cropped on CPU ONNX, and cell 6 checks the
cropper reproduces them before it makes new ones.

Needs on Drive under `v3_runs/`: `v34_ironman2_*.zip`, `v34_ironman2_bc_*.zip`, and optionally
`v36_ironman_er_*.zip`. Runtime → **A100**, then **Run all**.
"""

CELLS = [
    ("markdown", MD),
    ("code", '''# 1 · settings
A100_CAD_PER_HOUR = 0.689
MATRIX = "v39_set.csv"
ARMS = ("SCALE", "NOSCALE", "CROP2")
CROP_WORKERS = 4
DRIVE_PROJECT_DIR = "Side projects and shi"
BFL_REPO, BFL_REV = "black-forest-labs/FLUX.2-klein-4B", "e7b7dc27f91deacad38e78976d1f2b499d76a294"
PR_REPO, PR_REV = "Photoroom/FLUX.2-klein-4b-fp8-diffusers", "408c457f3589e17a1be1dae5bf0dcaf09cd4985f"
PR_SUB = "transformer_bf16"
'''),
    ("code", '''# 2 · Drive and caches; the ONNX crops stay on CPU, the footing of every reference of record
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
os.environ['V3_MODEL_DIR'] = os.path.join(BASE, 'v3_models')
os.environ['V2_ORT_GPU'] = '0'
for d in (os.environ['HF_HOME'], os.environ['V3_MODEL_DIR']): os.makedirs(d, exist_ok=True)
print('HF_HOME     ', os.environ['HF_HOME'], '(klein cached)' if found else '(klein downloads)')
print('V3_MODEL_DIR', os.environ['V3_MODEL_DIR'])
'''),
    ("code", f'''# 3 · install (CPU onnxruntime only - the GPU wheel cannot coexist with it), then the bundle
!pip -q install -U diffusers transformers accelerate sentencepiece protobuf mediapipe opencv-contrib-python-headless
!pip -q uninstall -y onnxruntime onnxruntime-gpu >/dev/null 2>&1
!pip -q install onnxruntime
!cd /content && rm -rf v39 && wget -q -O v39.zip https://github.com/101011101/magichour_takehome/raw/{BRANCH}/v39_bundle.zip && unzip -qo v39.zip -d v39
%cd /content/v39
import sys, torch, cv2, onnxruntime as ort
sys.path.insert(0, 'lib')
for f in ('lib/klein_local.py', 'lib/v3lib.py', 'lib/run_v36.py', 'lib/run_v39.py',
          'lib/ironman_bc_crop.py', 'lib/garment_crop.py', 'lib/phase3_variants.py', MATRIX):
    assert os.path.exists(f), f'bundle incomplete: {{f}} - is v39_bundle.zip pushed to {BRANCH}?'
assert hasattr(cv2, 'ximgproc'), 'plain opencv shadowed opencv-contrib - Runtime > Restart, run from cell 1'
assert 'A100' in torch.cuda.get_device_name(0), 'Runtime > Change runtime type > A100'
print(torch.cuda.get_device_name(0), '| onnxruntime', ort.__version__, ort.get_available_providers())
'''),
    ("code", '''# 4 · the inputs of record, off Drive: the normalised photos (re-bounded to 1 MP in cell 7),
#     and the BFL bald frames and BC references that cell 6 checks the cropper against
import csv, glob, zipfile
rows = list(csv.DictReader(open(MATRIX)))
stems = {r['person'] for r in rows} | {r['garment'] for r in rows}
garments = sorted({r['garment'] for r in rows})

def pick(pat, exclude=None, required=True):
    zs = [z for z in sorted(glob.glob(os.path.join(BASE, 'v3_runs', pat)))
          if not (exclude and exclude in os.path.basename(z))]
    assert zs or not required, f'no {pat} on Drive under v3_runs/'
    return zs[-1] if zs else None

# '_bc_' sorts after the digits, so a bare v34_ironman2_*.zip glob would resolve to the BC zip
want = {pick('v34_ironman2_*.zip', exclude='_bc_'): {f'inputs/{s}.jpg' for s in stems},
        pick('v34_ironman2_bc_*.zip'):
            {f'refs/{g}__bald.jpg' for g in garments} | {f'refs/{g}__BC.jpg' for g in garments}}
for zp, names in want.items():
    with zipfile.ZipFile(zp) as z:
        missing = names - set(z.namelist())
        assert not missing, f'{os.path.basename(zp)} is missing {sorted(missing)[:3]}'
        z.extractall('run', members=sorted(names))
    print(f'{os.path.basename(zp)}: {len(names)} files')

er_zip = pick('v36_ironman_er_*.zip', required=False)
if er_zip:
    os.makedirs('run/archive', exist_ok=True)
    with zipfile.ZipFile(er_zip) as z:
        have = set(z.namelist())
        for r in rows:
            n = f"gen/{r['set_id']}__ER__s{r['seed']}.jpg"
            if n in have:
                open(f"run/archive/{os.path.basename(n)}", 'wb').write(z.read(n))
    print(f'{os.path.basename(er_zip)}: {len(os.listdir("run/archive"))} archived ER cells (BFL transformer, 1.15 MP inputs)')
print(f'{len(rows)} cells · {len(garments)} garments · '
      f'{sum(r["noscale_noop"] == "1" for r in rows)} NOSCALE no-ops expected')
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
    ("code", '''# 6 · the cropper on this machine reproduces the BC references of record from their own
#     bald frames, before it is trusted to make new ones (the v34_bc gate: MAD <= 4.0)
import numpy as np, garment_crop as GC
from ironman_bc_crop import crop_bc
bad = []
for g in garments[:5]:
    a = cv2.imread(f'run/refs/{g}__BC.jpg')
    b, _ = crop_bc(cv2.imread(f'run/refs/{g}__bald.jpg'), f'val_{g}')
    if abs(a.shape[0] - b.shape[0]) > 8 or abs(a.shape[1] - b.shape[1]) > 8:
        bad.append((g, f'shape {a.shape[:2]} vs {b.shape[:2]}')); continue
    mad = float(np.abs(a.astype(np.float32) - cv2.resize(b, (a.shape[1], a.shape[0])).astype(np.float32)).mean())
    print(f'  {g}: MAD {mad:.2f}')
    if mad > 4.0: bad.append((g, f'MAD {mad:.2f}'))
print('BiRefNet provider:', GC._STATE.get('biref_prov'))
assert not bad, f'the cropper does not reproduce the references of record here: {bad}'
'''),
    ("code", '''# 7 · one cell end to end before paying for the set (this also writes the 1 MP inputs
#     and the recomputed A4 crops, so the first call takes a few minutes)
import run_v39 as V
V.main(MATRIX, arms=ARMS, gpu_usd_per_hour=A100_CAD_PER_HOUR, crop_workers=CROP_WORKERS, limit=1)
'''),
    ("code", '''# 8 · the run (resumable - rerun after a disconnect and it skips what is on disk)
import json
V.main(MATRIX, arms=ARMS, gpu_usd_per_hour=A100_CAD_PER_HOUR, crop_workers=CROP_WORKERS)
print(json.dumps(json.load(open('run/meta/cost_v39.json')), indent=1))
'''),
    ("code", '''# 9 · every cell landed? the parser fired? and how far the fresh baseline sits from the archive
meta = json.load(open('run/meta/v39_meta.json'))
noop = sum(1 for c in meta['cells'].values() if c.get('NOSCALE_noop'))
want = {'SCALE': len(rows), 'NOSCALE': len(rows) - noop, 'CROP2': len(rows)}
short = []
for a in ARMS:
    n = len(glob.glob(f'run/gen/*__{a}__*.jpg'))
    print(f'  {a:8s} {n}/{want[a]} cells')
    if n < want[a]: short.append(a)
assert not short, f'incomplete: {short} - rerun cell 8, it resumes'
fell = sorted(f'{g}/{k}' for g, v in meta['garments'].items() for k, m in v.items() if not m['cranium_used'])
print('references where the parser did NOT fire:', fell or 'none')
# the archive differs in two ways at once - BFL's transformer and 1.15 MP inputs - so this is a
# sanity print, not a measurement, and cells whose canvas moved under the bound are skipped
mads = []
for r in rows:
    a, b = f"run/archive/{r['set_id']}__ER__s{r['seed']}.jpg", f"run/gen/{r['set_id']}__SCALE__s{r['seed']}.jpg"
    if os.path.exists(a) and os.path.exists(b):
        x, y = cv2.imread(a), cv2.imread(b)
        if x.shape == y.shape:
            mads.append(float(np.abs(x.astype(np.float32) - y.astype(np.float32)).mean()))
if mads:
    print(f'fresh SCALE vs archived ER, same canvas only: median MAD {np.median(mads):.2f}, '
          f'max {max(mads):.2f} over {len(mads)} of {len(rows)} cells')
'''),
    ("code", '''# 10 · zip to Drive - verified before it leaves the session
import shutil, time
name = f"v39_a100_{time.strftime('%Y%m%d_%H%M')}"
KEEP = ('__1crop.', '__2crop.', '__bald_1crop.', '__bald_2crop.')
with zipfile.ZipFile(f'/content/{name}.zip', 'w', zipfile.ZIP_DEFLATED) as z:
    for f in os.listdir('run/gen'):   z.write('run/gen/' + f, 'gen/' + f)
    for f in os.listdir('run/refs'):
        if any(k in f for k in KEEP): z.write('run/refs/' + f, 'refs/' + f)
    for f in os.listdir('run/in1mp'): z.write('run/in1mp/' + f, 'in1mp/' + f)
    for f in os.listdir('run/meta'):  z.write('run/meta/' + f, 'meta/' + f)
    z.write(MATRIX, MATRIX)
with zipfile.ZipFile(f'/content/{name}.zip') as z:
    assert z.testzip() is None, 'the zip is corrupt'
    names = z.namelist()
    for need in ('meta/v39_meta.json', 'meta/cost_v39.json', 'meta/timings_v39.csv'):
        assert need in names, f'missing {need}'
os.makedirs(os.path.join(BASE, 'v3_runs'), exist_ok=True)
shutil.copy(f'/content/{name}.zip', os.path.join(BASE, 'v3_runs', f'{name}.zip'))
print(f'{name}.zip · {len(names)} files -> Drive v3_runs/')
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
