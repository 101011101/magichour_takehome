"""Write `v3/colab/v313_gate.ipynb` - which test decides whether a photo has a person in it.

  python3 v3/build/make_v313_notebook.py
"""
import json
import os

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(REPO, "v3", "colab", "v313_gate.ipynb")
BRANCH = "v3.3-lock"

MD = """# v3.13 — which test decides whether a garment photo has a person in it

The production pipeline is about to gate on this. If a garment photograph has no person in it,
there is no head to remove, and the bald pass **invents a wearer** — measured: the hip read fires
on 1 of 10 uploaded product shots but 6 of 10 of their bald frames. So the gate runs on the
upload, before call 1.

Ray's question: **should it look for a head rather than a face?** A face is small in a full-body
photograph, which is the input this system is built for, so a face test has the less margin of
the two. This run answers it with numbers.

Every candidate is built from a model the crop **already loads** — none adds a weight file:

| candidate | the test |
|---|---|
| **HEAD selfie** | Selfie Multiclass `FACE + HAIR` ≥ 500 px |
| **FACE selfie** | Selfie Multiclass `FACE` ≥ 500 px — `v3lib.tone`'s own test |
| **NOSE pose** | the Pose nose landmark at ≥ 0.5 visibility |
| **FACE or NOSE** | the gate as currently written: face, with the nose as tie-break |
| **HEAD parser** | SCHP ATR head classes as a share of everything it labels, ≥ 2% |
| **HEAD pose** | both ears and both shoulders confident — the skull ellipse's own precondition |

**The set is 73 distinct photographs**, ground truth from `test_set1/manifest.csv` rather than
anyone's eye: **56** with a person wearing the garment, **17** flat-lay or ghost-mannequin. The 13
on-model garments are a *subset* of the fold's 56 stems, so they are de-duplicated — adding the
lists naively counts them twice and reports 86.

**The two errors are not equal.** Calling a worn photograph *no person* sends a garment down a
path that never removes its wearer's head. Calling a flat-lay *person* only keeps today's
behaviour. The table below keeps them in separate columns for that reason.

No image is generated here — this is six detector passes over 73 photographs, seconds of compute.
Nothing is needed on Drive. Runtime → any GPU, then **Run all**.
"""

CELLS = [
    ("markdown", MD),
    ("code", '''# 1 · settings
import csv, glob, hashlib, json, os, shutil, sys, time, urllib.request, zipfile
SET = "v313_set.csv"
RAW = "https://raw.githubusercontent.com/101011101/magichour_takehome/''' + BRANCH + '''"
DRIVE_PROJECT_DIR = "Side projects and shi"
'''),
    ("code", '''# 2 · install, with the onnxruntime-gpu whose CUDA provider actually loads, then the bundle
!pip -q install -U mediapipe opencv-contrib-python-headless
!pip -q uninstall -y onnxruntime onnxruntime-gpu >/dev/null 2>&1
!pip -q install onnxruntime-gpu==1.22.0
import ctypes, site
dirs = sorted({d for p in site.getsitepackages() for d in glob.glob(os.path.join(p, 'nvidia', '*', 'lib'))})
os.environ['LD_LIBRARY_PATH'] = ':'.join(dirs + [os.environ.get('LD_LIBRARY_PATH', '')])
for d in dirs:
    for f in os.listdir(d):
        if '.so' in f and any(k in f for k in ('cudart', 'cublas', 'cudnn', 'cufft', 'curand')):
            try: ctypes.CDLL(os.path.join(d, f), mode=ctypes.RTLD_GLOBAL)
            except OSError: pass
!cd /content && rm -rf v313 && wget -q -O v313.zip https://github.com/101011101/magichour_takehome/raw/''' + BRANCH + '''/v313_bundle.zip && unzip -qo v313.zip -d v313
%cd /content/v313
sys.path.insert(0, 'lib')
for _m in ('run_v313',):
    sys.modules.pop(_m, None)
import cv2, onnxruntime as ort
assert os.path.exists(SET), 'bundle incomplete - is v313_bundle.zip pushed?'
print('onnxruntime', ort.__version__, ort.get_available_providers())
'''),
    ("code", '''# 3 · the models the crop already loads, at pinned revisions
MODELS = {
    'selfie_multiclass_256x256.tflite': (
        'https://storage.googleapis.com/mediapipe-models/image_segmenter/'
        'selfie_multiclass_256x256/float32/latest/selfie_multiclass_256x256.tflite',
        'c6748b1253a99067ef71f7e26ca71096cd449baefa8f101900ea23016507e0e0'),
    'pose_landmarker_lite.task': (
        'https://storage.googleapis.com/mediapipe-models/pose_landmarker/'
        'pose_landmarker_lite/float16/1/pose_landmarker_lite.task',
        '59929e1d1ee95287735ddd833b19cf4ac46d29bc7afddbbf6753c459690d574a'),
    'parsing_atr.onnx': (
        'https://huggingface.co/basso4/humanparsing/resolve/'
        '4fd18f98561bae00b5c24342c92307b4780b2a8d/parsing_atr.onnx',
        '04c7d1d070d0e0ae943d86b18cb5aaaea9e278d97462e9cfb270cbbe4cd977f4'),
}
os.makedirs('models', exist_ok=True)
for name, (url, want) in MODELS.items():
    p = os.path.join('models', name)
    if not os.path.exists(p):
        urllib.request.urlretrieve(url, p)
    got = hashlib.sha256(open(p, 'rb').read()).hexdigest()
    assert got == want, f'{name}: sha256 {got[:12]} != {want[:12]}'
    print(f'  {name:34s} {os.path.getsize(p)/1e6:7.1f} MB  sha256 ok')
'''),
    ("code", '''# 4 · the photographs, from the repo
rows = list(csv.DictReader(open(SET)))
os.makedirs('imgs', exist_ok=True)
for r in rows:
    dst = os.path.join('imgs', r['stem'] + '.jpg')
    if not os.path.exists(dst):
        urllib.request.urlretrieve(f"{RAW}/{r['path']}", '/content/_dl')
        im = cv2.imread('/content/_dl', cv2.IMREAD_COLOR)
        assert im is not None, f"unreadable: {r['path']}"
        cv2.imwrite(dst, im, [cv2.IMWRITE_JPEG_QUALITY, 95])
    r['file'] = dst
n_p = sum(1 for r in rows if r['truth'] == 'person')
print(f"{len(rows)} photographs: {n_p} with a person, {len(rows) - n_p} without")
'''),
    ("code", '''# 5 · one pass of each model over every photograph
from mediapipe.tasks import python as mpp
from mediapipe.tasks.python import vision
import run_v313 as V

seg = vision.ImageSegmenter.create_from_options(vision.ImageSegmenterOptions(
    base_options=mpp.BaseOptions(model_asset_path='models/selfie_multiclass_256x256.tflite'),
    running_mode=vision.RunningMode.IMAGE, output_confidence_masks=True))
pose = vision.PoseLandmarker.create_from_options(vision.PoseLandmarkerOptions(
    base_options=mpp.BaseOptions(model_asset_path='models/pose_landmarker_lite.task'),
    running_mode=vision.RunningMode.IMAGE))
schp = ort.InferenceSession('models/parsing_atr.onnx',
                            providers=[('CUDAExecutionProvider', {}), 'CPUExecutionProvider'])
print('SCHP on', schp.get_providers()[0])

t0 = time.time()
for i, r in enumerate(rows):
    r.update(V.measure(cv2.imread(r['file']), seg, pose, schp))
    if i % 20 == 0: print(f'  {i}/{len(rows)}', flush=True)
os.makedirs('meta', exist_ok=True)
json.dump(rows, open('meta/v313_measurements.json', 'w'), indent=1)
print(f'{len(rows)} photographs measured in {time.time() - t0:.0f}s')
'''),
    ("code", '''# 6 · every candidate, per photograph
table = V.score(rows)
print(f"{'photograph':46s} {'truth':10s} " + ' '.join(f'{n:>14s}' for n, _, _ in V.CANDIDATES))
for r in sorted(rows, key=lambda r: (r['truth'], r['stem'])):
    cells = []
    for name, fn, num in V.CANDIDATES:
        said = fn(r)
        ok = said == (r['truth'] == 'person')
        cells.append(f"{('T' if said else 'F') + ('' if ok else ' WRONG'):>14s}")
    print(f"{r['stem'][:45]:46s} {r['truth']:10s} " + ' '.join(cells))
'''),
    ("code", '''# 7 · the summary, and the number behind each verdict
print(f"{'candidate':16s} {'missed a worn photo':>20s} {'missed a flat-lay':>19s} {'wrong':>6s}")
for name, (worn, flat) in table.items():
    print(f'{name:16s} {len(worn):20d} {len(flat):19d} {len(worn) + len(flat):6d}')
    if worn: print(f'    worn, called no-person : {", ".join(worn)}')
    if flat: print(f'    flat-lay, called person: {", ".join(flat)}')

print('\\nseparation on the winning measurement (FACE + HAIR pixels):')
for t in ('person', 'no_person'):
    v = sorted(r['face_px'] + r['hair_px'] for r in rows if r['truth'] == t)
    print(f'  {t:10s} min {v[0]:>9,}  median {v[len(v)//2]:>9,}  max {v[-1]:>9,}')
'''),
    ("code", '''# 8 · zip the measurements, download, release the runtime
TERMINATE_WHEN_DONE = True  #@param {type:"boolean"}
DOWNLOAD_GRACE_SECONDS = 60  #@param {type:"integer"}

name = f"v313_gate_{time.strftime('%Y%m%d_%H%M')}"
zip_path = f'/content/{name}.zip'
with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as z:
    z.write('meta/v313_measurements.json', 'meta/v313_measurements.json')
    z.write(SET, SET)
with zipfile.ZipFile(zip_path) as z:
    assert z.testzip() is None, 'the zip is corrupt'
print(f'{name}.zip · {os.path.getsize(zip_path)/1e3:.0f} KB')

from google.colab import files
downloaded = False
try:
    files.download(zip_path); downloaded = True
except Exception as e:
    print(f'download failed ({e}) - take it from /content')
if downloaded:
    print(f'downloading; waiting {DOWNLOAD_GRACE_SECONDS}s')
    time.sleep(DOWNLOAD_GRACE_SECONDS)
if TERMINATE_WHEN_DONE and downloaded:
    from google.colab import runtime
    print('releasing the GPU')
    runtime.unassign()
else:
    print('runtime kept')
'''),
]


def main():
    cells = []
    for kind, src in CELLS:
        c = {"cell_type": kind, "metadata": {}, "source": src.rstrip().splitlines(keepends=True)}
        if kind == "code":
            c["outputs"], c["execution_count"] = [], None
        cells.append(c)
    json.dump({"cells": cells, "metadata": {
        "kernelspec": {"display_name": "Python 3", "name": "python3"},
        "language_info": {"name": "python"},
        "accelerator": "GPU", "colab": {"provenance": []}},
        "nbformat": 4, "nbformat_minor": 0}, open(OUT, "w"), indent=1)
    print(f"{os.path.relpath(OUT, REPO)}  ({len(cells)} cells)")


if __name__ == "__main__":
    main()
