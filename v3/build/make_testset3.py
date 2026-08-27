"""Assemble test_set3 from test_set (1) and test_set2.

Every image in this project is dual-use: a photo of a person wearing an outfit can
serve as the person input OR as the garment source. test_set3 makes that explicit by
sorting on what an image IS, not what it was downloaded for:

  people/    every photo containing a person. Any of these can play either role.
  clothes/   product-only shots - flat-lay or ghost mannequin, no wearer. Garment only.

SYMLINKS, not copies and not moves. The source sets are cited by runs already paid for,
so they cannot be emptied; and copying would duplicate ~20 MB of images that already
exist two directories away. Each entry is a relative symlink into test_set1 or test_set2,
so test_set3 is a VIEW - a selection and a manifest - rather than a third pile of JPEGs.
Nothing is deleted from either source set.

Deduplicated: the seven clothesonly_ts1g* files in test_set2/clothes are byte-identical
re-imports of test_set1/garments/g*.jpg. The test_set2 filename is kept because it is
descriptive; the file is taken once.
"""
import csv
import hashlib
import os

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(REPO, "test_set3")


def md5(p):
    return hashlib.md5(open(p, "rb").read()).hexdigest()


def add_head_signal(rows):
    """Coarse hair/face area from the 256x256 selfie multiclass map.

    Recorded because it is the variable that decides whether BC_klein's bald pass has
    anything to do: several on-model garment shots are cropped at the neck, and a
    reference with no hair in frame cannot have hair removed from it. This is a RAW
    SIGNAL, not a verdict - the map is 256x256 and the fractions are of whole-frame
    area, so they rank references rather than classify them.
    """
    import sys as _s
    _s.path.insert(0, os.path.join(REPO, "v2", "build"))
    try:
        import cv2
        import numpy as np
        import mediapipe as mp
        import garment_crop as G
        seg = G._multiclass()
        if seg is None:
            raise RuntimeError("multiclass unavailable")
    except Exception as e:
        print(f"  head signal skipped: {str(e)[:70]}")
        for r in rows:
            r["hair_frac"] = r["face_frac"] = ""
        return
    for r in rows:
        b = cv2.imread(os.path.join(REPO, r["path"]))
        res = seg.segment(mp.Image(image_format=mp.ImageFormat.SRGB,
                                   data=np.ascontiguousarray(cv2.cvtColor(b, cv2.COLOR_BGR2RGB))))
        p = [m.numpy_view() for m in res.confidence_masks]
        r["hair_frac"] = f"{float((p[G.HAIR] > 0.5).mean()):.5f}"
        r["face_frac"] = f"{float((p[G.FACE] > 0.5).mean()):.5f}"


def main():
    os.makedirs(os.path.join(OUT, "people"), exist_ok=True)

    ts1 = {r["id"]: r for r in csv.DictReader(open(os.path.join(REPO, "test_set1/manifest.csv")))}
    rows, seen = [], {}

    def take(src, role, name=None, meta=None, note=""):
        h = md5(src)
        if h in seen:
            rows.append({**seen[h], "note": f"duplicate of {seen[h]['id']}, not copied"})
            return
        name = name or os.path.basename(src)
        dst = os.path.join(OUT, role, name)
        rel = os.path.relpath(src, os.path.dirname(dst))
        if os.path.islink(dst) or os.path.exists(dst):
            os.remove(dst)
        os.symlink(rel, dst)
        m = meta or {}
        rec = {
            "id": os.path.splitext(name)[0],
            "role_pool": role,
            "source_set": note,
            "source_path": os.path.relpath(src, REPO),
            "path": os.path.relpath(dst, REPO),
            "pose": m.get("pose", ""), "body_size": m.get("body_size", ""),
            "skin_tone": m.get("skin_tone", ""), "gender": m.get("gender", ""),
            "framing": m.get("framing", ""), "photo_style": m.get("photo_style", ""),
            "hard_case": m.get("hard_case", ""), "category": m.get("category", ""),
            "note": "",
        }
        seen[h] = rec
        rows.append(rec)

    # 1. test-set-1 people -> people/. Explicitly available as garment sources too.
    d = os.path.join(REPO, "test_set1/people")
    for f in sorted(os.listdir(d)):
        take(os.path.join(d, f), "people", meta=ts1.get(os.path.splitext(f)[0]), note="test_set1")

    # 2. test_set2 people -> people/ (all dualuse on-model photos)
    d = os.path.join(REPO, "test_set2/people")
    for f in sorted(os.listdir(d)):
        take(os.path.join(d, f), "people", note="test_set2/people")

    # 3. test_set2 dualuse CLOTHES -> people/. They are on-model photos: a person is in
    #    the frame, so they belong with the people by the rule above.
    d = os.path.join(REPO, "test_set2/clothes")
    for f in sorted(os.listdir(d)):
        if f.startswith("dualuse_"):
            take(os.path.join(d, f), "people", note="test_set2/clothes (on-model)")

    # 4. test-set-1 garments that are WORN. Product-only shots are excluded by the
    #    rule above; the tag is the manifest's and was verified against the images.
    d = os.path.join(REPO, "test_set1/garments")
    for f in sorted(os.listdir(d)):
        m = ts1.get(os.path.splitext(f)[0], {})
        if m.get("photo_style") == "on_model":
            take(os.path.join(d, f), "people", meta=m, note="test_set1/garments (on-model)")

    keep = [r for r in rows if not r["note"]]
    add_head_signal(keep)

    with open(os.path.join(OUT, "manifest.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(keep[0]))
        w.writeheader()
        w.writerows(keep)

    nohair = sum(1 for r in keep if r["hair_frac"] and float(r["hair_frac"]) < 0.0005)
    print(f"test_set3: {len(keep)} on-model images, "
          f"{len(rows) - len(keep)} duplicates skipped, "
          f"{nohair} with no hair detected")
    return len(keep)


if __name__ == "__main__":
    main()
