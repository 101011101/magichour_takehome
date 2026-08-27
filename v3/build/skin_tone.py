"""CPU skin-tone and framing readers for the v3.1 mannequin work.

Two things the mannequin prompt needs to know about the source photograph, both
answered on CPU in under 200 ms and neither needing a GPU or an API call:

  tone(bgr)     what colour the mannequin should be, as a common colour word
  framing(bgr)  how much of the body the photograph actually shows

TONE. Face-skin pixels come from MediaPipe Selfie Multiclass (149 ms). The statistic is
the MEDIAN in Lab, not the mean: a face carries shadow, specular highlight and sometimes
makeup, and the median survives all three where the mean does not. The median is then
reported two ways - as ITA, the standard Individual Typology Angle used in dermatology
and in fairness work, and as one of eight ordinary colour words. The words are the
output that reaches the prompt; the hex is kept for the record but is NOT what gets
asked for, because a diffusion model reads "tan" and does not read "#D2A679".

FRAMING. Pose landmarks (36 ms). The question asked is only "is this joint inside the
frame", which is a far weaker question than the eight head-detection heuristics V2
burned through - those tried to find a boundary, this reads a coordinate that the
detector already returns.

Neither reader decides anything. They return a word and a category; what the prompt does
with them is the experiment.
"""
import os
import sys

import cv2
import numpy as np

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "v2", "build"))
import garment_crop as G  # noqa: E402

# Ordered light -> dark. Ordinary words only: these go into a prompt, and a model that
# has read the internet knows "tan" far better than it knows any fancier name.
# Ten steps, light -> dark, each an ordinary phrase. The words carry "skin" because
# p7.2 established that a bare chromatic adjective leaks into the garment - "tan" turned
# a white shirt into a tan polo - while naming what the colour belongs to holds it.
# "grey" is deliberately absent: it is the achromatic control and is not a complexion.
TONES = [
    ("pale skin", 88, "#F2E2D5"),
    ("light beige skin", 80, "#EBD3BB"),
    ("beige skin", 72, "#E0C3A3"),
    ("dark beige skin", 65, "#D3AF8B"),
    ("light tan skin", 58, "#C69A72"),
    ("tan skin", 51, "#B5835C"),
    ("light brown skin", 44, "#9E6B49"),
    ("brown skin", 36, "#84553A"),
    ("dark brown skin", 27, "#63402C"),
    ("black skin", 0, "#41291D"),
]
# For the arms that are not trying to match anyone.
NEUTRALS = [("white", "#FFFFFF"), ("light grey", "#D9D9D9"),
            ("grey", "#9E9E9E"), ("dark grey", "#5A5A5A"), ("black", "#1C1C1C")]

_seg = None
_pose = None


def _segmenter():
    global _seg
    if _seg is None:
        _seg = G._multiclass()
    return _seg


def _poser():
    global _pose
    if _pose is None:
        from mediapipe.tasks import python as mpp
        from mediapipe.tasks.python import vision
        _pose = vision.PoseLandmarker.create_from_options(
            vision.PoseLandmarkerOptions(
                base_options=mpp.BaseOptions(model_asset_path=os.path.join(
                    REPO, "v2", "runs", ".models", "pose_landmarker_lite.task")),
                running_mode=vision.RunningMode.IMAGE))
    return _pose


def _mp_image(bgr):
    import mediapipe as mp
    return mp.Image(image_format=mp.ImageFormat.SRGB,
                    data=np.ascontiguousarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)))


def tone(bgr):
    """Median skin colour of the face, as a colour word plus the evidence for it."""
    res = _segmenter().segment(_mp_image(bgr))
    h, w = bgr.shape[:2]
    ch = [cv2.resize(m.numpy_view(), (w, h), interpolation=cv2.INTER_LINEAR)
          for m in res.confidence_masks]
    face, body = ch[G.FACE] > 0.6, ch[G.BODY] > 0.6
    sel, src = (face, "face") if face.sum() > 500 else (body, "body")
    if sel.sum() < 300:
        return None
    lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB).astype(np.float32)
    L = float(np.median(lab[..., 0][sel])) * 100.0 / 255.0
    a = float(np.median(lab[..., 1][sel])) - 128.0
    b = float(np.median(lab[..., 2][sel])) - 128.0
    # ITA: the standard angle. Steep = light, shallow/negative = deep.
    ita = float(np.degrees(np.arctan2(L - 50.0, b))) if b else 0.0
    name, hexv = next(((n, x) for n, lo, x in TONES if L >= lo), TONES[-1][::2])
    px = cv2.cvtColor(np.uint8([[[np.median(lab[..., 0][sel]),
                                  np.median(lab[..., 1][sel]),
                                  np.median(lab[..., 2][sel])]]]), cv2.COLOR_LAB2BGR)[0][0]
    return {"name": name, "swatch": hexv, "L": round(L, 1), "a": round(a, 1),
            "b": round(b, 1), "ITA": round(ita, 1), "from": src,
            "measured_hex": "#%02X%02X%02X" % (px[2], px[1], px[0]),
            "pixels": int(sel.sum()), "coverage": round(float(sel.mean()), 4)}


# Landmark indices: 11/12 shoulders, 23/24 hips, 25/26 knees, 27/28 ankles.
JOINTS = [("shoulder", (11, 12)), ("hip", (23, 24)),
          ("knee", (25, 26)), ("ankle", (27, 28))]


def framing(bgr, vis=0.5, margin=0.02):
    """How much of the body is in frame. A joint counts only if the detector is
    confident AND its coordinate falls inside the image."""
    res = _poser().detect(_mp_image(bgr))
    if not res.pose_landmarks:
        return {"framing": "unknown", "present": [], "reason": "no pose detected"}
    lms = res.pose_landmarks[0]
    present = []
    for label, idx in JOINTS:
        ok = any(lms[i].visibility >= vis and -margin <= lms[i].x <= 1 + margin
                 and -margin <= lms[i].y <= 1 + margin for i in idx)
        if ok:
            present.append(label)
    if "ankle" in present:
        f = "full_body"
    elif "knee" in present:
        f = "knee_up"
    elif "hip" in present:
        f = "waist_up"
    elif "shoulder" in present:
        f = "chest_up"
    else:
        f = "unknown"
    return {"framing": f, "present": present, "reason": ""}


# What the prompt says for each framing category. The mannequin is asked for the same
# extent the photograph has, and nothing beyond it.
FRAME_PHRASE = {
    "full_body": "a full-length mannequin",
    "knee_up": "a mannequin shown from the head to the knee, cut off below the knee",
    "waist_up": "a mannequin shown from the head to the hip, cut off below the hip",
    "chest_up": "a mannequin shown from the head to the chest, cut off below the chest",
    "unknown": "a mannequin",
}


def read(path):
    bgr = cv2.imread(path)
    if bgr is None:
        return None
    out = {"path": path}
    out.update(framing(bgr))
    t = tone(bgr)
    out["tone"] = t
    return out


if __name__ == "__main__":
    import csv
    import json
    import time
    rows = list(csv.DictReader(open(os.path.join(REPO, "test_set3", "manifest.csv"))))
    t0 = time.time()
    out = []
    for r in rows:
        d = read(os.path.join(REPO, r["path"]))
        if d:
            d["id"] = r["id"]
            out.append(d)
    json.dump(out, open(os.path.join(REPO, "v3", "runs", "skin_framing.json"), "w"), indent=1)
    print(f"{len(out)} images in {time.time()-t0:.1f}s "
          f"({(time.time()-t0)/len(out)*1000:.0f} ms each)")
    import collections
    print("framing:", dict(collections.Counter(d["framing"] for d in out)))
    print("tone:   ", dict(collections.Counter(
        d["tone"]["name"] if d["tone"] else "none" for d in out)))
