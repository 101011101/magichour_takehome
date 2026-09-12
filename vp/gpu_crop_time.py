"""End-to-end time for the garment crop, on GPU and on CPU, with the provider each model got.

The crop is BiRefNet plus the SCHP parser plus MediaPipe plus an OpenCV guided filter, and
only the first two can move to the GPU. A figure for BiRefNet alone says nothing about the
stage, so this times `crop_bc` whole - the call production actually makes - and prints the
provider per model, because the CUDA provider can fail to load and fall back in silence.

  !wget -q -O gpu_crop_time.py https://raw.githubusercontent.com/101011101/magichour_takehome/v3.3-lock/vp/gpu_crop_time.py
  !python3 gpu_crop_time.py
"""
import ctypes
import glob
import json
import os
import shutil
import site
import statistics
import subprocess
import sys
import time

RAW = "https://raw.githubusercontent.com/101011101/magichour_takehome/v3.3-lock"
REPO = "/content/repo"
MODELS = f"{REPO}/v2/runs/.models"
GARMENTS = ("g001", "g004", "g010", "g016")


def sh(*cmd, check=True):
    return subprocess.run(list(cmd), capture_output=True, text=True, check=check)


def install():
    sh(sys.executable, "-m", "pip", "-q", "uninstall", "-y", "onnxruntime", "onnxruntime-gpu", check=False)
    sh(sys.executable, "-m", "pip", "install", "-q", "onnxruntime-gpu==1.22.0", "mediapipe",
       "opencv-contrib-python-headless", "huggingface_hub")
    dirs = sorted({d for p in site.getsitepackages() for d in glob.glob(os.path.join(p, "nvidia", "*", "lib"))})
    os.environ["LD_LIBRARY_PATH"] = ":".join(dirs + [os.environ.get("LD_LIBRARY_PATH", "")])
    for d in dirs:
        for f in os.listdir(d):
            if ".so" in f and any(k in f for k in ("cudart", "cublas", "cudnn", "cufft", "curand")):
                try:
                    ctypes.CDLL(os.path.join(d, f), mode=ctypes.RTLD_GLOBAL)
                except OSError:
                    pass


def fetch():
    for d in (f"{REPO}/v2/build", f"{REPO}/v3/build", MODELS, "/content/imgs"):
        os.makedirs(d, exist_ok=True)
    for src in ("v2/build/garment_crop.py", "v2/build/phase3_variants.py", "v3/build/ironman_bc_crop.py"):
        sh("wget", "-q", "-O", f"{REPO}/{src}", f"{RAW}/{src}")
    imgs = []
    for g in GARMENTS:
        dst = f"/content/imgs/{g}.jpg"
        for sub in ("test_set1/garments", "test_set2/garments"):
            r = sh("wget", "-q", "-O", dst, f"{RAW}/{sub}/{g}.jpg", check=False)
            if r.returncode == 0 and os.path.exists(dst) and os.path.getsize(dst) > 10000:
                imgs.append(dst)
                break
    if not imgs:
        raise RuntimeError(f"no garment images fetched from {RAW}/test_set1/garments/ - "
                           "check the branch is reachable")
    os.environ["HF_HOME"] = f"{MODELS}/hf"
    from huggingface_hub import hf_hub_download
    shutil.copy(hf_hub_download("onnx-community/BiRefNet_lite-ONNX", "onnx/model.onnx"),
                f"{MODELS}/BiRefNet_lite.onnx")
    for url, name in (
        ("https://storage.googleapis.com/mediapipe-models/image_segmenter/selfie_multiclass_256x256/"
         "float32/latest/selfie_multiclass_256x256.tflite", "selfie_multiclass_256x256.tflite"),
        ("https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/"
         "float16/1/pose_landmarker_lite.task", "pose_landmarker_lite.task"),
    ):
        sh("wget", "-q", "-O", f"{MODELS}/{name}", url)
    return imgs


def run(device, imgs):
    os.environ["V2_ORT_GPU"] = "1" if device == "gpu" else "0"
    for mod in ("ironman_bc_crop", "garment_crop", "phase3_variants"):
        sys.modules.pop(mod, None)
    shutil.rmtree(f"{REPO}/v2/runs/.cache", ignore_errors=True)
    import cv2
    import garment_crop as G
    import ironman_bc_crop as C
    import phase3_variants as P
    C.crop_bc(cv2.imread(imgs[0]), f"warm_{device}")
    seconds = []
    for i, p in enumerate(imgs):
        im = cv2.imread(p)
        t0 = time.time()
        C.crop_bc(im, f"{device}_{i}")
        seconds.append(time.time() - t0)
    return {"device": device,
            "biref_provider": G._STATE.get("biref_prov", "?"),
            "parser_provider": P._HP["m"].get_providers()[0] if P._HP.get("m") else "unavailable",
            "seconds_each": [round(s, 2) for s in seconds],
            "median_seconds": round(statistics.median(seconds), 2)}


def main():
    install()
    imgs = fetch()
    sys.path.insert(0, f"{REPO}/v3/build")
    sys.path.insert(0, f"{REPO}/v2/build")
    print(f"{len(imgs)} garments\n")
    gpu = run("gpu", imgs)
    print(json.dumps(gpu, indent=1))
    cpu = run("cpu", imgs)
    print(json.dumps(cpu, indent=1))
    print(json.dumps({"crop_gpu_median_s": gpu["median_seconds"],
                      "crop_cpu_median_s": cpu["median_seconds"],
                      "speedup": round(cpu["median_seconds"] / gpu["median_seconds"], 1),
                      "gpu_really_used": gpu["biref_provider"].startswith("CUDA")
                                         and gpu["parser_provider"].startswith("CUDA")}, indent=1))


if __name__ == "__main__":
    main()
