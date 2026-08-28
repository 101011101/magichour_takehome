"""v3.1 try-on pipeline — self-contained, for Colab.

Nothing here imports from the repo: the notebook downloads its own weights and this
module carries every stage. It is the v3.1 arm as locked, plus the two incumbents it is
measured against.

  BC   klein makes the wearer bald -> CPU crop -> klein edit          2 calls
  QX   Qwen regenerates the garment isolated on white -> klein edit   2 calls
  MQ   CPU crop -> Qwen regenerates it as a MANNEQUIN -> klein edit   2 calls   (v3.1)

MQ is the locked arm. Its extraction prompt is assembled from two CPU reads of the
inputs, which is the thing v3.1 established:

  colour   median Lab of the PERSON's face -> one of ten named steps -> a word
  framing  which pose joints are in frame on the GARMENT crop -> a category
           -> one table lookup giving the extent AND the pose clause together

The table is the point. Extent and pose were once separate sentences and contradicted
each other - "feet together" told the model feet were in frame while the extent clause
said to cut above them, and the pose clause won. One lookup, one rule: never name a
body part the crop excludes.
"""
import base64
import os
import shutil
import time
import urllib.request

import cv2
import numpy as np

# ----------------------------------------------------------------- weights ----
# name -> (url, filename, expected bytes). The size is checked, not just existence:
# an interrupted download leaves a file that passes os.path.exists and then fails
# somewhere much less obvious.
MODELS = {
    "birefnet": ("https://huggingface.co/onnx-community/BiRefNet_lite-ONNX/resolve/"
                 "main/onnx/model.onnx", "BiRefNet_lite.onnx", 224_005_088),
    "selfie": ("https://storage.googleapis.com/mediapipe-models/image_segmenter/"
               "selfie_multiclass_256x256/float32/latest/"
               "selfie_multiclass_256x256.tflite",
               "selfie_multiclass_256x256.tflite", 16_371_837),
    "pose": ("https://storage.googleapis.com/mediapipe-models/pose_landmarker/"
             "pose_landmarker_lite/float16/latest/pose_landmarker_lite.task",
             "pose_landmarker_lite.task", 5_777_746),
}
MODEL_DIR = "models"

# Where an already-downloaded copy might be. Searched in order, and the first file of
# the right size wins. BiRefNet is 224 MB, so finding it beats fetching it - especially
# on a Colab runtime that has been restarted.
def search_dirs():
    dirs = []
    if os.environ.get("V3_MODEL_DIR"):
        dirs.append(os.environ["V3_MODEL_DIR"])
    dirs += [
        MODEL_DIR,
        "/content/models",
        "/content/drive/MyDrive/v3_models",
        "/content/drive/MyDrive/models",
        "/content/drive/MyDrive/tryon_v2_runs/models",
        os.path.expanduser("~/.cache/v3_models"),
        "v2/runs/.models",                       # the repo, if run outside Colab
    ]
    return [x for x in dirs if x]


BIREF_SIDE = 1024
BIREF_MEAN = np.array([0.485, 0.456, 0.406], np.float32)
BIREF_STD = np.array([0.229, 0.224, 0.225], np.float32)
# selfie multiclass channel order
BG, HAIR, BODY, FACE, CLOTHES, OTHER = range(6)
_S = {}


def _ok(path, want, tol=0.02):
    """Present and the right size. Tolerance because a re-export can shift a file by a
    few bytes; a truncated download will not be within 2%."""
    if not os.path.exists(path):
        return False
    got = os.path.getsize(path)
    return abs(got - want) <= want * tol


def fetch_models(persist=None, verbose=True):
    """Find each model or download it. Returns {name: path}.

    persist: a directory to copy downloads into so the next run finds them - point it at
    Drive on Colab and the 224 MB fetch happens once ever, not once per runtime.
    """
    os.makedirs(MODEL_DIR, exist_ok=True)
    if persist:
        os.makedirs(persist, exist_ok=True)
    out = {}
    for key, (url, name, size) in MODELS.items():
        local = os.path.join(MODEL_DIR, name)
        if _ok(local, size):
            if verbose:
                print(f"  {name}: cached ({os.path.getsize(local)/1e6:.0f} MB)")
            out[key] = local
            continue
        found = next((os.path.join(dd, name) for dd in search_dirs()
                      if _ok(os.path.join(dd, name), size)), None)
        if found:
            if os.path.abspath(found) != os.path.abspath(local):
                shutil.copy2(found, local)
            if verbose:
                print(f"  {name}: found in {os.path.dirname(found)}")
        else:
            if os.path.exists(local):
                if verbose:
                    print(f"  {name}: wrong size on disk "
                          f"({os.path.getsize(local)/1e6:.0f} MB, want "
                          f"{size/1e6:.0f} MB) - refetching")
                os.remove(local)
            if verbose:
                print(f"  {name}: downloading {size/1e6:.0f} MB ...", flush=True)
            tmp = local + ".part"
            urllib.request.urlretrieve(url, tmp)
            os.replace(tmp, local)
            if not _ok(local, size) and verbose:
                print(f"    WARNING: got {os.path.getsize(local)/1e6:.1f} MB, "
                      f"expected {size/1e6:.1f} MB")
        if persist and not _ok(os.path.join(persist, name), size):
            shutil.copy2(local, os.path.join(persist, name))
            if verbose:
                print(f"    saved to {persist}")
        out[key] = local
    return out


# ------------------------------------------------------------------ colour ----
# Ten steps, light to dark. Ordinary phrases, each carrying the word "skin": a bare
# chromatic adjective leaks into the garment ("tan" turned a white shirt into a tan
# polo), and naming what the colour belongs to keeps it on the mannequin.
TONES = [
    ("pale skin", 88, "#F2E2D5"), ("light beige skin", 80, "#EBD3BB"),
    ("beige skin", 72, "#E0C3A3"), ("dark beige skin", 65, "#D3AF8B"),
    ("light tan skin", 58, "#C69A72"), ("tan skin", 51, "#B5835C"),
    ("light brown skin", 44, "#9E6B49"), ("brown skin", 36, "#84553A"),
    ("dark brown skin", 27, "#63402C"), ("black skin", 0, "#41291D"),
]

# ------------------------------------------------------------------ prompts ---
PREFIX = "Show this person's outfit on a "
SUFFIX = ("mannequin against pure white. The mannequin wears every piece the person is "
          "actually wearing, exactly as they wear it, keeping its shape and drape - and "
          "the person themself is gone, no face, no skin, no hair. Copy each piece "
          "exactly - the same colour, print, texture and cut. The mannequin wears only "
          "what the person is wearing and nothing else: if they are not carrying a bag, "
          "there is no bag.")

# DYNAMIC PROMPTING. Extent and pose from one framing read, so they cannot disagree.
# Rule: never name a body part the crop excludes.
FRAME_CLAUSE = {
    "full_body": (" Show the whole mannequin, head to feet. It stands in a neutral "
                  "upright pose, feet together, facing forward."),
    "knee_up": (" Show the mannequin from the head to the knee only, cut off below the "
                "knee. It stands in a neutral upright pose, legs together, facing "
                "forward."),
    "waist_up": (" Show the mannequin from the head to the hip only, cut off below the "
                 "hip. It stands upright and square to the camera, shoulders level."),
    "chest_up": (" Show the mannequin from the head to the chest only, cut off below "
                 "the chest. It stands upright and square to the camera, shoulders "
                 "level."),
    "unknown": (" Show only the part of the body that the photograph shows. It stands "
                "upright and square to the camera."),
}
# QX incumbent - V2's p1, garment isolated on white, no mannequin
QX_PROMPT = ("Return only the clothing from this photo, isolated on a plain white "
             "background. Remove the person entirely - no face, no skin, no hair, no "
             "background. Preserve the garment's exact colour, pattern and shape.")
# BC incumbent - V2's PRE2, a small in-distribution edit
BALD_PROMPT = ("Make this person completely bald. Remove all hair from the head and any "
               "hair falling over the shoulders, chest or back, and show the scalp. "
               "Keep the clothing, the body, the pose and the background exactly as "
               "they are.")
# Call 2, unchanged since V2's attention-modulation run
EDIT_PROMPT = ("Dress the person in image 1 in the clothing shown in image 2. Keep the "
               "person's face, identity, body and the background exactly as they are.")

KLEIN = "fal-ai/flux-2/klein/4b/distilled/edit"
QWEN = "fal-ai/qwen-image-edit-2511"
SEED = 46
MAXPIX = 1_150_000
PAD = 0.04


# ------------------------------------------------------------------ readers ---
def _mp_image(bgr):
    import mediapipe as mp
    return mp.Image(image_format=mp.ImageFormat.SRGB,
                    data=np.ascontiguousarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)))


def _segmenter(paths):
    if "seg" not in _S:
        from mediapipe.tasks import python as mpp
        from mediapipe.tasks.python import vision
        _S["seg"] = vision.ImageSegmenter.create_from_options(
            vision.ImageSegmenterOptions(
                base_options=mpp.BaseOptions(model_asset_path=paths["selfie"]),
                running_mode=vision.RunningMode.IMAGE, output_confidence_masks=True))
    return _S["seg"]


def _poser(paths):
    if "pose" not in _S:
        from mediapipe.tasks import python as mpp
        from mediapipe.tasks.python import vision
        _S["pose"] = vision.PoseLandmarker.create_from_options(
            vision.PoseLandmarkerOptions(
                base_options=mpp.BaseOptions(model_asset_path=paths["pose"]),
                running_mode=vision.RunningMode.IMAGE))
    return _S["pose"]


def _biref(paths):
    if "biref" not in _S:
        import onnxruntime as ort
        prov = ["CUDAExecutionProvider", "CPUExecutionProvider"] \
            if "CUDAExecutionProvider" in ort.get_available_providers() \
            else ["CPUExecutionProvider"]
        _S["biref"] = ort.InferenceSession(paths["birefnet"], providers=prov)
        _S["biref_prov"] = _S["biref"].get_providers()[0]
    return _S["biref"]


def tone(bgr, paths):
    """Median Lab of the FACE pixels -> one named ladder step. Face only: the body-skin
    fallback was removed because body skin is a different, more exposed surface and a
    silent substitution reports as if nothing happened."""
    res = _segmenter(paths).segment(_mp_image(bgr))
    h, w = bgr.shape[:2]
    ch = [cv2.resize(m.numpy_view(), (w, h), interpolation=cv2.INTER_LINEAR)
          for m in res.confidence_masks]
    sel = ch[FACE] > 0.6
    if sel.sum() < 500:
        return None
    lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB).astype(np.float32)
    L = float(np.median(lab[..., 0][sel])) * 100.0 / 255.0
    b = float(np.median(lab[..., 2][sel])) - 128.0
    px = cv2.cvtColor(np.uint8([[[np.median(lab[..., 0][sel]),
                                  np.median(lab[..., 1][sel]),
                                  np.median(lab[..., 2][sel])]]]), cv2.COLOR_LAB2BGR)[0][0]
    name = next((n for n, lo, _ in TONES if L >= lo), TONES[-1][0])
    return {"name": name, "L": round(L, 1),
            "ITA": round(float(np.degrees(np.arctan2(L - 50.0, b))) if b else 0.0, 1),
            "measured_hex": "#%02X%02X%02X" % (px[2], px[1], px[0]),
            "pixels": int(sel.sum())}


JOINTS = [("shoulder", (11, 12)), ("hip", (23, 24)),
          ("knee", (25, 26)), ("ankle", (27, 28))]


def framing(bgr, paths, vis=0.5, margin=0.02):
    """Which joints are confident AND inside the frame. Reads a coordinate the detector
    already returns - a far weaker question than trying to locate a boundary."""
    res = _poser(paths).detect(_mp_image(bgr))
    if not res.pose_landmarks:
        return {"framing": "unknown", "present": []}
    lms = res.pose_landmarks[0]
    present = [lab for lab, idx in JOINTS
               if any(lms[i].visibility >= vis and -margin <= lms[i].x <= 1 + margin
                      and -margin <= lms[i].y <= 1 + margin for i in idx)]
    f = ("full_body" if "ankle" in present else "knee_up" if "knee" in present
         else "waist_up" if "hip" in present else "chest_up" if "shoulder" in present
         else "unknown")
    return {"framing": f, "present": present}


# -------------------------------------------------------------------- crop ----
def normalise(bgr):
    h, w = bgr.shape[:2]
    if h * w <= MAXPIX:
        return bgr
    k = (MAXPIX / (h * w)) ** 0.5
    return cv2.resize(bgr, (int(w * k), int(h * k)), interpolation=cv2.INTER_AREA)


def matte(bgr, paths):
    s = _biref(paths)
    rgb = cv2.cvtColor(cv2.resize(bgr, (BIREF_SIDE, BIREF_SIDE),
                                  interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2RGB)
    x = (rgb.astype(np.float32) / 255.0 - BIREF_MEAN) / BIREF_STD
    y = s.run(None, {s.get_inputs()[0].name:
                     np.ascontiguousarray(x.transpose(2, 0, 1)[None])})[0][0, 0]
    p = 1.0 / (1.0 + np.exp(-y.astype(np.float32)))
    p = np.clip(cv2.resize(p, (bgr.shape[1], bgr.shape[0]),
                           interpolation=cv2.INTER_CUBIC), 0, 1)
    # drop specks: keep only the largest connected component of the confident region
    m = (p > 0.5).astype(np.uint8)
    n, lbl, stats, _ = cv2.connectedComponentsWithStats(m, 8)
    if n > 1:
        keep = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
        p = p * (lbl == keep)
    return p


def crop_a4(bgr, paths):
    """A4: background removed, HEAD KEPT, cropped to the subject bbox on white.
    Chosen over the 256 matte (which removes garment) and over head-removal (which
    loses the context the hair needs)."""
    p = matte(bgr, paths)
    h, w = bgr.shape[:2]
    ys, xs = np.where(p > 0.5)
    if len(ys) < 20:
        b = (0, 0, w, h)
    else:
        py, px = int(h * PAD), int(w * PAD)
        b = (max(0, xs.min() - px), max(0, ys.min() - py),
             min(w, xs.max() + px), min(h, ys.max() + py))
    sub, a = bgr[b[1]:b[3], b[0]:b[2]], p[b[1]:b[3], b[0]:b[2], None]
    return (sub.astype(np.float32) * a + 255.0 * (1 - a)).astype(np.uint8)


def mq_prompt(person_bgr, crop_bgr, paths):
    t = tone(person_bgr, paths)
    colour = t["name"] if t else "beige skin"
    fr = framing(crop_bgr, paths)["framing"]
    return PREFIX + colour + " " + SUFFIX + FRAME_CLAUSE[fr], colour, fr


# --------------------------------------------------------------------- fal ----
def b64(bgr):
    ok, buf = cv2.imencode(".png", bgr)
    if not ok:
        raise RuntimeError("encode failed")
    return "data:image/png;base64," + base64.b64encode(buf.tobytes()).decode()


def call(endpoint, args, retries=3):
    import fal_client
    last = None
    for i in range(retries):
        try:
            r = fal_client.subscribe(endpoint, arguments=args, with_logs=False)
            imgs = r.get("images") or ([r["image"]] if r.get("image") else [])
            if not imgs:
                raise RuntimeError(f"no image: {str(r)[:120]}")
            with urllib.request.urlopen(imgs[0]["url"], timeout=180) as resp:
                return cv2.imdecode(np.frombuffer(resp.read(), np.uint8),
                                    cv2.IMREAD_COLOR)
        except Exception as e:
            last = e
            if "balance" in str(e).lower() or "locked" in str(e).lower():
                raise
            time.sleep(2 * (i + 1))
    raise last
