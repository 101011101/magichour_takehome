"""Does the uploaded garment photo contain a person? Measured, before it gates anything.

The pipeline's person-side stages - the bald pass and the head-subtracting crop - exist to
get a wearer out of the way. A flat-lay has no wearer, and on one the bald pass invents one
(v3/report/flatlay_hips.html). So the gate is worth having, but only if it is right about
which photographs have people in them, and that is what this script measures rather than
assumes.

The check is the crop's own, not a new model: the FACE test from v3lib.tone, with the pose
nose as a tie-break. Both already run inside the crop, so the gate adds nothing to download.

  face    Selfie Multiclass FACE channel > 0.6, at least MIN_FACE_PX pixels - the same
          test v3lib.tone already applies before it reads a skin tone. Decides on its own
          when it fires
  nose    MediaPipe Pose landmark 0, visibility >= VIS and inside the frame. Only consulted
          when the face is short, because a face is small in a full-body photograph: p016 of
          the fold measures 464 px, 36 under the threshold, and its nose reads 0.999

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
MIN_FACE_PX = 500
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


def person_present(bgr):
    """The gate: a nose OR a face region. Either alone is evidence of a wearer."""
    nose, _ = nose_present(bgr)
    return nose or face_pixels(bgr) >= MIN_FACE_PX


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
            gate = nose or px >= MIN_FACE_PX
            rowsout.append((os.path.basename(f), nose, v, px, gate))
        n = len(rowsout)
        agree = sum(1 for r in rowsout if r[4] == expect_person)
        print(f"\n{name}  (expect {'person' if expect_person else 'NO person'}) - {n} images")
        print(f"  gate agrees on {agree}/{n}")
        for k, label in ((1, "nose"), (4, "gate")):
            hits = sum(1 for r in rowsout if r[k])
            print(f"    {label:5s} says person on {hits}/{n}")
        wrong = [r for r in rowsout if r[4] != expect_person]
        for r in wrong:
            print(f"    DISAGREES  {r[0]:52s} nose={r[1]} vis={r[2]} face_px={r[3]}")
        out.append((name, expect_person, rowsout))
    return out


if __name__ == "__main__":
    sys.exit(0 if main() else 0)
