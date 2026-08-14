#  §5c · Deterministic judges, V2 — drop-in replacements for the V1 metrics.
#  Changes vs V1: garment_sim = Marqo-FashionSigLIP embedding cosine (was HSV
#  histogram, structure-blind); identity_cos = AuraFace-v1 (Apache-2.0, was
#  insightface buffalo_l, NC-licensed pack). pose_error / background_psnr
#  unchanged (mediapipe-only). Same signatures; None on detection failure.
#  pip deps: numpy opencv-python-headless mediapipe insightface onnxruntime
#            huggingface_hub open_clip_torch torch torchvision pillow
import os
import threading
import numpy as np, cv2
import mediapipe as mp

_tls = threading.local()   # mediapipe graphs are not thread-safe; one set per thread
_lock = threading.Lock()   # shared torch / onnx models load once


# -- model loaders -----------------------------------------------------------
_AURA_ROOT = os.environ.get("AURAFACE_ROOT", os.path.expanduser("~/.cache/auraface"))
_aura = None
def _face():
    global _aura
    with _lock:
        if _aura is None:
            from huggingface_hub import snapshot_download
            from insightface.app import FaceAnalysis
            snapshot_download("fal/AuraFace-v1",
                              local_dir=os.path.join(_AURA_ROOT, "models", "auraface"))
            _aura = FaceAnalysis(name="auraface", root=_AURA_ROOT,
                                 providers=["CPUExecutionProvider"])
            _aura.prepare(ctx_id=-1, det_size=(640, 640))
    return _aura

_siglip = None
def _fashion_clip():
    global _siglip
    with _lock:
        if _siglip is None:
            import torch, open_clip
            model, _, preprocess = open_clip.create_model_and_transforms(
                "hf-hub:Marqo/marqo-fashionSigLIP")
            model.eval()
            _siglip = (model, preprocess, torch)
    return _siglip

def _pose_g():
    if not hasattr(_tls, "pose"):
        _tls.pose = mp.solutions.pose.Pose(static_image_mode=True)
    return _tls.pose

def _seg_g():
    if not hasattr(_tls, "seg"):
        _tls.seg = mp.solutions.selfie_segmentation.SelfieSegmentation(model_selection=1)
    return _tls.seg

def _rgb(img): return np.array(img.convert("RGB"))


# -- shared helpers (unchanged from V1) --------------------------------------
def _landmarks(img):
    res = _pose_g().process(_rgb(img))
    if not res.pose_landmarks: return None
    return np.array([[l.x, l.y, l.visibility] for l in res.pose_landmarks.landmark])

def _torso_crop(img):
    lm = _landmarks(img); w, h = img.size
    if lm is None:
        return img.crop((int(w * .25), int(h * .2), int(w * .75), int(h * .8)))
    pts = lm[[11, 12, 23, 24], :2] * [w, h]
    x0, y0 = pts.min(0); x1, y1 = pts.max(0)
    mx, my = (x1 - x0) * 0.25, (y1 - y0) * 0.15
    return img.crop((max(0, int(x0 - mx)), max(0, int(y0 - my)),
                     min(w, int(x1 + mx)), min(h, int(y1 + my))))


# -- V2 metrics --------------------------------------------------------------
def _embed(img):
    model, preprocess, torch = _fashion_clip()
    with torch.no_grad(), _lock:
        return model.encode_image(preprocess(img.convert("RGB")).unsqueeze(0),
                                  normalize=True)[0].numpy()

def garment_similarity(result_img, garment_img):
    """FashionSigLIP cosine: garment reference vs torso crop of the result."""
    return float(np.dot(_embed(garment_img), _embed(_torso_crop(result_img))))

def identity_cosine(person_img, result_img):
    fa = _face().get(cv2.cvtColor(_rgb(person_img), cv2.COLOR_RGB2BGR))
    fb = _face().get(cv2.cvtColor(_rgb(result_img), cv2.COLOR_RGB2BGR))
    if not fa or not fb: return None
    ea = max(fa, key=lambda f: f.bbox[2] - f.bbox[0]).normed_embedding
    eb = max(fb, key=lambda f: f.bbox[2] - f.bbox[0]).normed_embedding
    return float(np.dot(ea, eb))


# -- V1 metrics carried over unchanged ---------------------------------------
def pose_error(person_img, result_img):
    la, lb = _landmarks(person_img), _landmarks(result_img)
    if la is None or lb is None: return None
    vis = (la[:, 2] > 0.5) & (lb[:, 2] > 0.5)
    if vis.sum() < 6: return None
    torso = np.linalg.norm(la[11, :2] - la[24, :2]) + 1e-6
    return float(np.linalg.norm(la[vis, :2] - lb[vis, :2], axis=1).mean() / torso)

def background_psnr(person_img, result_img):
    a = _rgb(person_img).astype(np.float64)
    b = np.array(result_img.convert("RGB").resize(person_img.size)).astype(np.float64)
    mask = _seg_g().process(_rgb(person_img)).segmentation_mask
    bg = mask < 0.5
    if bg.sum() < 500: return None
    mse = ((a - b) ** 2)[bg].mean()
    return float(10 * np.log10(255 ** 2 / mse)) if mse > 0 else 99.0


# recalibrated on V1 outputs, see metric_recalibration.md
# garment_sim: lo = wrong-garment control median (0.54), hi = matched p95 (0.85)
# identity_cos: lo = same-person verification level on AuraFace scale (V1's
#   0.35 buffalo anchor maps to 0.42 via linear fit), hi = 0.80 kept below
#   paste-back saturation (fashn_v16 AuraFace median 0.97)
CV_ANCHORS = {"garment_sim": (0.55, 0.85), "identity_cos": (0.42, 0.80),
              "pose_err": (0.25, 0.0), "bg_psnr": (12.0, 32.0)}
