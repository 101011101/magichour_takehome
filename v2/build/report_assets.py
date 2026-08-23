# Collect every image the report needs into one self-contained directory.
#
# v2/runs/ is gitignored (~1 GB, and generated try-ons of identifiable people), so
# the report cannot reference it and still deploy. This copies ONLY what is used,
# downsized, into v2/report/img/ -- which is then a standalone folder that can be
# served anywhere.
import csv, glob, hashlib, json, os

import cv2

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(REPO, "v2", "report")
IMG = os.path.join(OUT, "img")
_seen = {}


def asset(src, maxw=900, q=84):
    """Copy an image into the report folder, downsized. Returns the relative path."""
    if not src or not os.path.exists(src):
        return ""
    key = os.path.abspath(src)
    if key in _seen:
        return _seen[key]
    im = cv2.imread(src)
    if im is None:
        return ""
    h, w = im.shape[:2]
    if w > maxw:
        im = cv2.resize(im, (maxw, int(h * maxw / w)), interpolation=cv2.INTER_AREA)
    # content hash, so the same source never lands twice under two names
    name = hashlib.md5(key.encode()).hexdigest()[:10] + ".jpg"
    os.makedirs(IMG, exist_ok=True)
    cv2.imwrite(os.path.join(IMG, name), im, [cv2.IMWRITE_JPEG_QUALITY, q])
    _seen[key] = "img/" + name
    return _seen[key]


def pairs():
    """Sets where an uncropped BASE klein output and the shipped result both exist.

    BASE is the v2.0 baseline: klein given the whole reference photo, person and all.
    It is what the product would do with no cropping, no routing and no gate, and is
    the honest thing to measure the harness against.
    """
    real = json.load(open(f"{REPO}/v2/runs/realism/_realism.json"))
    T = {r["set_id"]: r for r in csv.DictReader(
        open(f"{REPO}/v223_perfect_tier_picks.csv"))}
    tier = {(r["set_id"], r["arm"]): r["tier"] for r in csv.DictReader(
        open(f"{REPO}/v223_perfect_tier_picks.csv"))}
    meta = {r["stem"]: r["src_path"] for r in csv.DictReader(
        open(f"{REPO}/v2/runs/crop_screen/crop_log.csv"))}
    combo = {os.path.basename(p).replace("__base.png", ""): p
             for p in glob.glob(f"{REPO}/v2/runs/combo/*__base.png")}
    ts2 = {os.path.basename(p): p
           for p in glob.glob(f"{REPO}/v2/runs/ts2/outputs/klein_4b_edit__*")}
    ann = {}
    p = f"{REPO}/v221_review_annotations.csv"
    if os.path.exists(p):
        ann = {r["set_id"]: r for r in csv.DictReader(open(p))}

    out = []
    for sid, r in real.items():
        t = T[sid]
        base = (combo.get(f"{t['garment']}__wears__{t['person']}")
                or combo.get(f"{t['person']}__wears__{t['garment']}")
                or (ts2.get(f"klein_4b_edit__{sid}.png") if sid.startswith("ts2_") else None))
        if not base:
            continue
        shipped = os.path.join(REPO, r["after"])          # after the realism pass
        if not os.path.exists(shipped):
            shipped = r["src"]
        a = ann.get(sid, {})
        faults = [k.replace("base_", "") for k in
                  ("base_wrongperson", "base_wrongclothes", "base_wrongbg",
                   "base_duplication", "base_nontransfer")
                  if str(a.get(k, "")).strip().lower() in ("1", "true", "yes", "y")]
        out.append(dict(
            set_id=sid, arm=r["arm"], tier=r["tier"],
            person=meta.get(t["person"], ""), garment=meta.get(t["garment"], ""),
            base=base, shipped=shipped, faults=faults,
            base_tier=tier.get((sid, "control"), ""),
            hair=float(t["hair_over_garment"]), escalated=r["escalated"]))
    out.sort(key=lambda x: (-len(x["faults"]), x["set_id"]))
    return out


if __name__ == "__main__":
    ps = pairs()
    print(f"{len(ps)} base/shipped pairs")
    print(f"  with recorded baseline faults: {sum(1 for p in ps if p['faults'])}")
    for p in ps[:6]:
        print(f"    {p['set_id'][:38]:40} {p['arm']:12} {p['tier']:8} "
              f"faults={','.join(p['faults']) or '-'}")
