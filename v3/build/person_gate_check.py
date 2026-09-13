"""Does the uploaded garment photo contain a person? Measured, before it gates anything.

The pipeline's person-side stages - the bald pass and the head-subtracting crop - exist to
get a wearer out of the way. A flat-lay has no wearer, and on one the bald pass invents one
(v3/report/flatlay_hips.html). So the gate is worth having, but only if it is right about
which photographs have people in them, and that is what this script measures rather than
assumes.

The check is the crop's own models, not a new one: Selfie Multiclass, which the crop already
segments with. So the gate adds nothing to download.

  head    THE GATE. Selfie Multiclass FACE + HAIR confidence > 0.6, at least MIN_HEAD_PX
          pixels. Chosen 2026-09-12 over the alternatives below: it is the only candidate
          that makes no error on either class, and it needs no pose call
  face    the FACE channel alone - v3lib.tone's test. Misses p016 of the fold, a worn
          photograph whose face measures 469 px, 31 under the threshold. A face is small in
          a full-body photograph, which is this system's input; a head is not
  nose     MediaPipe Pose landmark 0. Fooled by g010, a ghost-mannequin tee whose hollow
          shoulders read as a nose at 0.96

The margin is what decides it: on the fold the lowest worn photograph measures 1,849 head
pixels and the highest person-free one measures 0, so the 500 threshold sits in a very wide
gap. FACE alone has no such gap.

This script measures ACCURACY, which is a property of the model and not of the device, so it
is fine to run here. Timing is not measured here and must not be: production runs these on a
GPU.

  python3 v3/build/person_gate_check.py
"""
import csv
import glob
import os
import sys

import cv2
import numpy as np

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
MODELS = os.path.join(REPO, "models")
VIS = 0.5
MARGIN = 0.02
FACE_T = 0.6
MIN_HEAD_PX = 500
MIN_FACE_PX = 500   # the face-only candidate, kept for comparison
BG, HAIR, BODY, FACE, CLOTHES, OTHER = range(6)
_S = {}


def _mp_image(bgr):
    import mediapipe as mp
    return mp.Image(image_format=mp.ImageFormat.SRGB,
                    data=np.ascontiguousarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)))


def _poser():
    if "pose" not in _S:
        from mediapipe.tasks import python as mpp
        from mediapipe.tasks.python import vision
        _S["pose"] = vision.PoseLandmarker.create_from_options(
            vision.PoseLandmarkerOptions(
                base_options=mpp.BaseOptions(
                    model_asset_path=os.path.join(MODELS, "pose_landmarker_lite.task")),
                running_mode=vision.RunningMode.IMAGE))
    return _S["pose"]


def _segmenter():
    if "seg" not in _S:
        from mediapipe.tasks import python as mpp
        from mediapipe.tasks.python import vision
        _S["seg"] = vision.ImageSegmenter.create_from_options(
            vision.ImageSegmenterOptions(
                base_options=mpp.BaseOptions(
                    model_asset_path=os.path.join(MODELS, "selfie_multiclass_256x256.tflite")),
                running_mode=vision.RunningMode.IMAGE, output_confidence_masks=True))
    return _S["seg"]


def nose_present(bgr):
    """Pose landmark 0, confident and inside the frame."""
    res = _poser().detect(_mp_image(bgr))
    if not res.pose_landmarks:
        return False, 0.0
    p = res.pose_landmarks[0][0]
    ok = p.visibility >= VIS and -MARGIN <= p.x <= 1 + MARGIN and -MARGIN <= p.y <= 1 + MARGIN
    return bool(ok), round(float(p.visibility), 3)


def face_pixels(bgr):
    """FACE channel area, the test v3lib.tone already uses."""
    res = _segmenter().segment(_mp_image(bgr))
    h, w = bgr.shape[:2]
    m = cv2.resize(res.confidence_masks[FACE].numpy_view(), (w, h),
                   interpolation=cv2.INTER_LINEAR)
    return int((m > FACE_T).sum())


def head_pixels(bgr):
    """FACE + HAIR area. A head survives the framing a face does not."""
    res = _segmenter().segment(_mp_image(bgr))
    h, w = bgr.shape[:2]
    ch = res.confidence_masks
    m = (cv2.resize(ch[FACE].numpy_view(), (w, h), interpolation=cv2.INTER_LINEAR)
         + cv2.resize(ch[HAIR].numpy_view(), (w, h), interpolation=cv2.INTER_LINEAR))
    return int((m > FACE_T).sum())


def person_present(bgr):
    """The gate, as production runs it: is there a head."""
    return head_pixels(bgr) >= MIN_HEAD_PX


def main():
    manifest = os.path.join(REPO, "test_set1", "manifest.csv")
    rows = [r for r in csv.DictReader(open(manifest)) if r["kind"] == "garment"]
    free = {r["id"] for r in rows if r["photo_style"] in ("flat_lay", "ghost_mannequin")}
    worn = {r["id"] for r in rows if r["photo_style"] == "on_model"}

    sets = []
    sets.append(("fold garments (person wearing)", True,
                 sorted(glob.glob(os.path.join(REPO, "v3/runs/v310/a100/in1mp/*.jpg")))))
    sets.append(("test_set1 on-model garments", True,
                 [os.path.join(REPO, "test_set1/garments", f"{g}.jpg") for g in sorted(worn)]))
    sets.append(("inquiry product shots", False,
                 sorted(glob.glob(os.path.join(REPO,
                        "v3/runs/inquiry/a100/inquiry/inputs/*.jpg")))))
    sets.append(("test_set1 flat-lay / ghost mannequin", False,
                 [os.path.join(REPO, "test_set1/garments", f"{g}.jpg") for g in sorted(free)]))

    out = []
    for name, expect_person, files in sets:
        files = [f for f in files if os.path.exists(f)]
        rowsout = []
        for f in files:
            bgr = cv2.imread(f)
            if bgr is None:
                continue
            nose, v = nose_present(bgr)
            px = face_pixels(bgr)
            hpx = head_pixels(bgr)
            gate = hpx >= MIN_HEAD_PX
            rowsout.append((os.path.basename(f), nose, v, px, gate, hpx))
        n = len(rowsout)
        agree = sum(1 for r in rowsout if r[4] == expect_person)
        print(f"\n{name}  (expect {'person' if expect_person else 'NO person'}) - {n} images")
        print(f"  gate agrees on {agree}/{n}")
        for label, hits in (("head (the gate)", sum(1 for r in rowsout if r[5] >= MIN_HEAD_PX)),
                            ("face only", sum(1 for r in rowsout if r[3] >= MIN_FACE_PX)),
                            ("nose only", sum(1 for r in rowsout if r[1]))):
            print(f"    {label:16s} says person on {hits}/{n}")
        if rowsout:
            hs = sorted(r[5] for r in rowsout)
            print(f"    head px: min {hs[0]}  max {hs[-1]}")
        wrong = [r for r in rowsout if r[4] != expect_person]
        for r in wrong:
            print(f"    DISAGREES  {r[0]:52s} head_px={r[5]} face_px={r[3]} nose={r[1]} vis={r[2]}")
        out.append((name, expect_person, rowsout))
    return out


if __name__ == "__main__":
    sys.exit(0 if main() else 0)
