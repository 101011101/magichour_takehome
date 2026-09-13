"""Generate v3/colab/v314_consolidate.ipynb - the consolidation inquiry.

Drive-free: photos from the repo, weights from Hugging Face at pinned revisions.

  python3 v3/build/make_v314_notebook.py
"""
import json
import os

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(REPO, "v3", "colab", "v314_consolidate.ipynb")
RAW = "https://raw.githubusercontent.com/101011101/magichour_takehome/v3.3-lock"
ZIP = "https://github.com/101011101/magichour_takehome/raw/v3.3-lock/v314_bundle.zip"

CELLS = [
    ("markdown", """# v3.14 — can any of the four small models be consolidated?

Runbo asked whether the vision models can be folded together or into klein. **Into klein is
closed**: v3.5 measured that letting the generative model re-render the garment costs
fidelity — 9.2% against 4.8% on the same 600 cells — and that finding is what the current
design rests on. What is open is whether the four small models can be reduced among
themselves.

**The criterion is Runbo's own:** *"we don't want to reduce quality. We just want robustness
and simplicity and as much determinism as we can."* So this run is not scored on cost or
latency — these stages run once per garment and are cached. It is scored on:

1. **Quality is a veto.** A candidate that removes a model but moves a reference for the
   worse is a rejection.
2. **Fewer branches beats fewer models.** The thing that can go wrong is the number of ways
   a garment can be handled, not the number of weights on disk.
3. **Determinism is already true in-process** — the four vision models have no seed and no
   sampling, and v3.8 measured byte-identical outputs on 86 cells sent identical inputs.
   What varies is *which branch an image takes*, which is data-dependent. A route that fires
   on 3% of garments is the likeliest place for an unnoticed bug.

**"Keep what we have" is a permitted answer**, and section 8 says so plainly if that is what
the numbers show.

| candidate | what it removes | what it costs |
|---|---|---|
| **A** — drop Selfie Multiclass, keep the SCHP parser | one model, the collar guard, the selfie union | the fallback chain loses its inputs — see §7 |
| **B** — take the waist from the parser, not Pose | the hip read (Pose stays for the neck line) | a dress has no waist to find |

Runtime → **A100**, then **Run all**. The bald frames are regenerated here because the
archive lived on a Drive that has been cleared."""),

    ("code", """# 1 · settings
import csv, glob, json, os, shutil, subprocess, sys, time, zipfile

RAW = "%s"
BUNDLE = "%s"
MATRIX = "v314_set.csv"
A100_CAD_PER_HOUR = 0.689
BALD_SEED = 46
GENERATE_TRYONS = 6  #@param {type:"integer"}
""" % (RAW, ZIP)),

    ("code", """# 2 · install, with the onnxruntime-gpu whose CUDA provider actually loads
!pip -q install -U diffusers transformers accelerate sentencepiece protobuf mediapipe opencv-contrib-python-headless
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
os.environ['V2_ORT_GPU'] = '1'
!cd /content && rm -rf v314 && wget -q -O v314.zip $BUNDLE && unzip -qo v314.zip -d v314
%cd /content/v314
import torch, cv2, onnxruntime as ort
sys.path.insert(0, 'lib')
for _m in ('run_v314', 'v3lib', 'klein_local', 'garment_crop', 'phase3_variants', 'ironman_bc_crop'):
    sys.modules.pop(_m, None)
assert hasattr(cv2, 'ximgproc'), 'plain opencv shadowed opencv-contrib - Restart, run from cell 1'
gpu = torch.cuda.get_device_name(0)
if 'A100' not in gpu:
    print(f'{gpu} - not the A100 the record was made on. Both arms still run on this one\n'
          '  machine, so the comparison holds; only absolute numbers are not comparable\n'
          '  to the archive.')
print(torch.cuda.get_device_name(0), '| onnxruntime', ort.__version__)"""),

    ("code", """# 3 · the photos, straight from the repo
import urllib.request
rows = list(csv.DictReader(open(MATRIX)))
os.makedirs('run/inputs', exist_ok=True)
for r in rows:
    dst = f"run/inputs/{r['stem']}.jpg"
    if os.path.exists(dst):
        continue
    urllib.request.urlretrieve(f"{RAW}/{r['path']}", '/content/_dl')
    im = cv2.imread('/content/_dl', cv2.IMREAD_COLOR)
    assert im is not None, f"unreadable: {r['path']}"
    cv2.imwrite(dst, im, [cv2.IMWRITE_JPEG_QUALITY, 95])
worn = [r for r in rows if r['kind'] == 'worn']
product = [r for r in rows if r['kind'] == 'product']
print(f"{len(rows)} garments: {len(worn)} worn, {len(product)} product")"""),

    ("code", """# 4 · weights at pinned revisions, and the crop models on CUDA
import hashlib
MODELS = 'v2/runs/.models'
os.makedirs(MODELS, exist_ok=True)
os.environ['HF_HOME'] = os.path.abspath(f'{MODELS}/hf')
CROP_FILES = {
    'BiRefNet_lite.onnx': ('https://huggingface.co/onnx-community/BiRefNet_lite-ONNX/resolve/'
        'de15b22ba131738a16dff04aab8bdf8dc32e3ac1/onnx/model.onnx',
        '5600024376f572a557870a5eb0afb1e5961636bef4e1e22132025467d0f03333'),
    'selfie_multiclass_256x256.tflite': ('https://storage.googleapis.com/mediapipe-models/'
        'image_segmenter/selfie_multiclass_256x256/float32/latest/selfie_multiclass_256x256.tflite',
        'c6748b1253a99067ef71f7e26ca71096cd449baefa8f101900ea23016507e0e0'),
    'pose_landmarker_lite.task': ('https://storage.googleapis.com/mediapipe-models/'
        'pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task',
        '59929e1d1ee95287735ddd833b19cf4ac46d29bc7afddbbf6753c459690d574a'),
}
def sha256(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 24), b''):
            h.update(b)
    return h.hexdigest()
for name, (url, want) in CROP_FILES.items():
    p = os.path.join(MODELS, name)
    if not os.path.exists(p) or sha256(p) != want:
        urllib.request.urlretrieve(url, p)
        got = sha256(p)
        assert got == want, f'{name}: sha256 {got} != {want}'
    print(f'  {name}: ok')
import garment_crop as GC, phase3_variants as P, run_v314 as V
GC._biref(); P._parser()
for nm, s in (('BiRefNet', GC._STATE['biref']), ('SCHP', P._HP['m'])):
    assert s.get_providers()[0] == 'CUDAExecutionProvider', f'{nm} fell back to CPU'
    print(f'  {nm} {s.get_providers()[0]}')"""),

    ("code", """# 5 · klein, and the bald frames the crop actually runs on
import klein_local as K, v3lib as L
K.load()
t0 = time.time()
os.makedirs('run/bald', exist_ok=True)
for r in worn:
    dst = f"run/bald/{r['stem']}.jpg"
    if os.path.exists(dst):
        continue
    raw = L.normalise(cv2.imread(f"run/inputs/{r['stem']}.jpg"))
    im, _ = K.edit([raw], L.BALD_PROMPT, BALD_SEED, canvas='v33')
    im = cv2.resize(im, (raw.shape[1], raw.shape[0]), interpolation=cv2.INTER_AREA)
    cv2.imwrite(dst, im, [cv2.IMWRITE_JPEG_QUALITY, 95])
print(f'{len(worn)} bald frames in {(time.time() - t0) / 60:.1f} min')"""),

    ("code", """# 6 · both candidates, measured
worn_paths = {r['stem']: f"run/bald/{r['stem']}.jpg" for r in worn}
product_paths = {r['stem']: f"run/inputs/{r['stem']}.jpg" for r in product}
rec = V.main(worn_paths, product_paths, out='run')
A = {k: v for k, v in rec['A'].items() if 'mad' in v}
print(f"CANDIDATE A - reference movement, parser-only vs today ({len(A)} garments)")
for k, v in sorted(A.items(), key=lambda kv: -kv[1]['mad'])[:10]:
    print(f"  {k[:34]:34s} MAD {v['mad']:6.2f}  max {v['max']:3d}  changed {v['changed_pct']:6.2f}%"
          f"  head px {v['head_px_today']} -> {v['head_px_only']}")
skipped = [k for k, v in rec['A'].items() if 'skipped' in v]
if skipped:
    print(f"  not comparable (parser did not fire): {skipped}")"""),

    ("code", """# 7 · candidate B, and the branch inventory
B = rec['B']
wb = {k: v for k, v in B.items() if v['kind'] == 'worn'}
pb = {k: v for k, v in B.items() if v['kind'] == 'product'}
both = {k: v for k, v in wb.items() if v['diff'] is not None}
import statistics as st
print(f"CANDIDATE B - waist from the parser vs hip from Pose")
print(f"  worn    {len(wb):3d}: parser waist {sum(v['waist'] is not None for v in wb.values()):3d}"
      f"  pose hip {sum(v['hip'] is not None for v in wb.values()):3d}")
if both:
    ds = sorted(v['diff'] for v in both.values())
    print(f"    both fired on {len(both)}: median |diff| {st.median(ds):.3f} of height,"
          f" p90 {ds[int(.9 * (len(ds) - 1))]:.3f}, max {max(ds):.3f}")
    for k, v in sorted(both.items(), key=lambda kv: -kv[1]['diff'])[:5]:
        print(f"      {k[:30]:30s} waist {v['waist']:.2f} vs hip {v['hip']:.2f}  ({v['waist_why']})")
print(f"  product {len(pb):3d}: parser invents a waist on"
      f" {sum(v['waist'] is not None for v in pb.values()):3d},"
      f" pose invents a hip on {sum(v['hip'] is not None for v in pb.values()):3d}")
for k, v in pb.items():
    if v['waist'] is not None:
        print(f"      parser invents: {k} at {v['waist']:.2f} ({v['waist_why']})")
reasons = {}
for v in wb.values():
    reasons[v['waist_why']] = reasons.get(v['waist_why'], 0) + 1
print(f"  parser waist reasons on worn photos: {reasons}")
json.dump(rec, open('run/meta/v314_meta.json', 'w'), indent=1)"""),

    ("code", """# 8 · cost, and the zip
gpu_s = (len(worn) * 1.7)
json.dump({'worn': len(worn), 'product': len(product), 'klein_calls': len(worn),
           'approx_gpu_seconds': round(gpu_s, 1),
           'approx_cad': round(gpu_s / 3600 * A100_CAD_PER_HOUR, 4),
           'klein': K.info(), 'python': sys.version.split()[0]},
          open('run/meta/cost_v314.json', 'w'), indent=1)
print(json.dumps(json.load(open('run/meta/cost_v314.json')), indent=1))

TERMINATE_WHEN_DONE = True  #@param {type:"boolean"}
DOWNLOAD_GRACE_SECONDS = 90  #@param {type:"integer"}
name = f"v314_a100_{time.strftime('%Y%m%d_%H%M')}"
zip_path = f'/content/{name}.zip'
with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as z:
    for sub in ('refs', 'meta', 'bald', 'inputs'):
        if os.path.isdir(f'run/{sub}'):
            for f in os.listdir(f'run/{sub}'):
                z.write(f'run/{sub}/{f}', f'{sub}/{f}')
    z.write(MATRIX, MATRIX)
with zipfile.ZipFile(zip_path) as z:
    assert z.testzip() is None, 'the zip is corrupt'
    assert 'meta/v314_meta.json' in z.namelist(), 'missing meta'
    n = len(z.namelist())
print(f'{name}.zip · {n} files · {os.path.getsize(zip_path) / 1e6:.1f} MB')
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
    print('releasing the GPU'); runtime.unassign()
else:
    print('runtime kept')"""),
]


def main():
    nb = {"cells": [], "metadata": {"accelerator": "GPU",
                                    "colab": {"provenance": []},
                                    "kernelspec": {"display_name": "Python 3", "name": "python3"},
                                    "language_info": {"name": "python"}},
          "nbformat": 4, "nbformat_minor": 0}
    for kind, src in CELLS:
        cell = {"cell_type": kind, "metadata": {},
                "source": src.splitlines(keepends=True)}
        if kind == "code":
            cell["execution_count"] = None
            cell["outputs"] = []
        nb["cells"].append(cell)
    json.dump(nb, open(OUT, "w"), indent=1)
    print(f"{OUT}  ({len(nb['cells'])} cells)")


if __name__ == "__main__":
    main()
