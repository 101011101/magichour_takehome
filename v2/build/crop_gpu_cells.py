# GPU matte pre-pass for the v2.2.1 garment cropper.
# Generate the notebook with:
#   jupytext --to notebook --output ../crop_gpu.ipynb crop_gpu_cells.py
#
# Why this notebook exists: BiRefNet_lite costs ~75s per image on a laptop CPU
# and under a second on a T4. Only the network forward pass needs the GPU; every
# refinement stage in garment_crop.py is cheap and stays local.
#
# Runtime note (measured on Colab 2026-08-15): onnxruntime-gpu installs cleanly
# but exposes no CUDAExecutionProvider — a cuDNN version mismatch against the
# Colab image. Torch CUDA works, so this notebook loads the PyTorch BiRefNet_lite
# checkpoint instead of the ONNX export. Same weights, same preprocessing.
#
# Contract with the local pipeline: writes 8-bit grayscale PNGs named {stem}.png,
# sized to the source image's (h, w) AFTER the same resize the local pipeline
# applies, into v2/runs/.cache/matte/. garment_crop.biref_matte() reads exactly
# that and skips inference. The local cache validates on exact (h, w) — any
# divergence here means every matte is silently discarded on return.

# %% [markdown]
# # v2.2.1 — GPU matte pre-pass
#
# Computes BiRefNet subject mattes on a GPU runtime so the laptop never pays the
# ~75s/image CPU cost.
#
# **Before running: Runtime → Change runtime type → T4 GPU.**
#
# Then Run All. Produces `mattes.zip`; unzip into `v2/runs/.cache/matte/` locally
# and the crop pipeline re-runs in about 8 seconds with every matte cached.

# %%
#  1 · Runtime check --------------------------------------------------------
import subprocess
gpu = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total",
                      "--format=csv,noheader"],
                     capture_output=True, text=True).stdout.strip()
print(gpu or "NO GPU — Runtime > Change runtime type > T4, then Run All again")
assert gpu, "no GPU in this runtime"

# %%
#  2 · Dependencies ---------------------------------------------------------
# kornia and timm are imported by BiRefNet's remote modeling code; pillow-avif
# because one Testset2 reference is .avif, which OpenCV cannot decode.
# torch and transformers ship with Colab.
!pip install -q kornia timm opencv-python-headless pillow-avif-plugin

# %%
#  3 · Source images --------------------------------------------------------
# Every source is committed, so a shallow clone is the entire transfer.
#
# CRITICAL — the cap column. The local cache validates mattes on exact (h, w).
# test_set/ is read raw locally, so no resize here. Testset2 is read locally from
# PREPPED copies (max side 1536, per ts2_harness.prep) which are gitignored, so
# the same resize must happen here or every Testset2 matte is wasted work.
import os
REPO = "/content/tryon_repo"
if not os.path.exists(REPO):
    !git clone --depth 1 https://github.com/101011101/magichour_takehome.git {REPO}

SOURCES = [(f"{REPO}/test_set/people", None),     # 30 stratified people, read raw
           (f"{REPO}/Testset2/people", 1536),     # 8 high-res people
           (f"{REPO}/Testset2/clothes", 1536),    # 12 garment refs
           ("/content/extra", None)]              # anything uploaded by hand
EXTS = (".jpg", ".jpeg", ".png", ".webp", ".avif")

srcs = []
for d, cap in SOURCES:
    if not os.path.isdir(d):
        continue
    for f in sorted(os.listdir(d)):
        if f.lower().endswith(EXTS):
            srcs.append((os.path.join(d, f), cap))
print(f"{len(srcs)} source images")
for d, cap in SOURCES:
    n = sum(1 for p, _ in srcs if os.path.dirname(p) == d)
    if n:
        print(f"  {n:3d}  {os.path.basename(d):10s} cap={cap}")

# %%
#  4 · Model ----------------------------------------------------------------
# BiRefNet_lite, the same checkpoint the local pipeline uses via its ONNX export.
import torch
from transformers import AutoModelForImageSegmentation

model = AutoModelForImageSegmentation.from_pretrained(
    "ZhengPeng7/BiRefNet_lite", trust_remote_code=True).to("cuda").eval()
torch.set_float32_matmul_precision("high")
print("model on", next(model.parameters()).device)

# %%
#  5 · Matte pre-pass -------------------------------------------------------
# Mirrors garment_crop.biref_matte(): INTER_AREA to 1024, BGR->RGB, imagenet
# normalise, CHW, sigmoid, INTER_CUBIC back to source size, 8-bit PNG.
import time, numpy as np, cv2, PIL.Image
try:
    import pillow_avif  # noqa: F401  — registers the AVIF decoder with PIL
except ImportError:
    pass

BIREF_SIDE = 1024
MEAN = np.array([0.485, 0.456, 0.406], np.float32)
STD = np.array([0.229, 0.224, 0.225], np.float32)
OUT = "/content/matte"
os.makedirs(OUT, exist_ok=True)


def load_bgr(path, cap):
    """OpenCV first, PIL for what it cannot decode. `cap` replicates
    ts2_harness.prep — PIL thumbnail semantics, LANCZOS — so the matte matches
    the dimensions the local pipeline will ask for."""
    bgr = cv2.imread(path, cv2.IMREAD_COLOR)
    if bgr is None:
        bgr = cv2.cvtColor(np.asarray(PIL.Image.open(path).convert("RGB")),
                           cv2.COLOR_RGB2BGR)
    if cap and max(bgr.shape[:2]) > cap:
        im = PIL.Image.fromarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))
        im.thumbnail((cap, cap), PIL.Image.LANCZOS)
        bgr = cv2.cvtColor(np.asarray(im), cv2.COLOR_RGB2BGR)
    return bgr


t_all, done, skipped = time.time(), 0, []
for i, (path, cap) in enumerate(srcs, 1):
    stem = os.path.splitext(os.path.basename(path))[0]
    dst = os.path.join(OUT, f"{stem}.png")
    if os.path.exists(dst):
        continue
    try:
        bgr = load_bgr(path, cap)
    except Exception as e:
        skipped.append((stem, str(e)[:60]))
        print(f"  SKIP {stem}: {str(e)[:60]}")
        continue
    h, w = bgr.shape[:2]
    rgb = cv2.cvtColor(cv2.resize(bgr, (BIREF_SIDE, BIREF_SIDE),
                                  interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2RGB)
    x = ((rgb.astype(np.float32) / 255.0 - MEAN) / STD).transpose(2, 0, 1)[None]
    t = time.time()
    with torch.no_grad():
        p = model(torch.from_numpy(x).cuda())[-1].sigmoid().cpu().numpy()[0, 0]
    dt = time.time() - t
    p = np.clip(cv2.resize(p, (w, h), interpolation=cv2.INTER_CUBIC), 0.0, 1.0)
    cv2.imwrite(dst, (p * 255).astype(np.uint8))
    done += 1
    print(f"  {i:3d}/{len(srcs)}  {stem:34s} {w}x{h}  {dt:5.2f}s  "
          f"fg={float((p > 0.5).mean()):.3f}")
print(f"\n{done} mattes in {time.time() - t_all:.1f}s, {len(skipped)} skipped")

# %%
#  6 · Sanity check ---------------------------------------------------------
# A matte that is nearly all foreground or nearly all background is a failure,
# not a subject. This is the signal to read — it is what a major failure looks
# like before it reaches the crops.
import glob
from PIL import Image
rows = []
for f in sorted(glob.glob(f"{OUT}/*.png")):
    fg = float((np.asarray(Image.open(f)).astype(np.float32) / 255.0 > 0.5).mean())
    rows.append((os.path.basename(f)[:-4], fg))
bad = [r for r in rows if r[1] < 0.02 or r[1] > 0.95]
thin = [r for r in rows if 0.02 <= r[1] < 0.06]
print(f"{len(rows)} mattes | {len(bad)} suspicious | {len(thin)} very small subject")
for r in bad + thin:
    print(f"   {r[0]:40s} fg={r[1]:.3f}")

# %%
#  7 · Preview --------------------------------------------------------------
# Worst-first, so failures are on screen rather than buried.
import matplotlib.pyplot as plt
order = sorted(rows, key=lambda r: abs(r[1] - 0.3))[::-1][:8]
fig, ax = plt.subplots(2, len(order), figsize=(2.6 * len(order), 8))
for j, (stem, fg) in enumerate(order):
    src = next(((p, c) for p, c in srcs
                if os.path.splitext(os.path.basename(p))[0] == stem), None)
    ax[0, j].imshow(cv2.cvtColor(load_bgr(*src), cv2.COLOR_BGR2RGB))
    ax[1, j].imshow(np.asarray(Image.open(f"{OUT}/{stem}.png")), cmap="gray")
    ax[0, j].set_title(f"{stem[:18]}\nfg={fg:.2f}", fontsize=8)
    for r in (0, 1):
        ax[r, j].axis("off")
plt.tight_layout(); plt.show()

# %%
#  8 · Export ---------------------------------------------------------------
# Unzip into v2/runs/.cache/matte/ locally, then:
#   python v2/build/garment_crop.py --refs-dir test_set/people
!cd /content && zip -qr mattes.zip matte
print(f"{os.path.getsize('/content/mattes.zip') / 1e6:.1f} MB")
from google.colab import files
files.download("/content/mattes.zip")
