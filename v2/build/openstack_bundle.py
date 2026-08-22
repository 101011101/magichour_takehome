# Everything the fully-open-weights Colab run needs, in one zip.
#
# Carries RAW inputs (so references are rebuilt from scratch, which is also the
# unseen-garment path) plus the stored references, fal outputs and realism results
# to compare against stage by stage. A divergence then localises itself instead of
# showing up only at the end.
import csv, io, json, os, sys, zipfile

import cv2

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(REPO, "v2", "runs", "openstack_bundle.zip")
ARMS = ["PHEAD", "BC_klein", "QX_qwen_p1"]


def build(n_sets=None):
    sys.path.insert(0, os.path.join(REPO, "v2"))
    from pipeline import arms
    run = json.load(open(f"{REPO}/v2/runs/amt/_run.json"))
    meta = {r["stem"]: r["src_path"] for r in csv.DictReader(
        open(f"{REPO}/v2/runs/crop_screen/crop_log.csv"))}
    T = list(csv.DictReader(open(f"{REPO}/v223_perfect_tier_picks.csv")))
    real = json.load(open(f"{REPO}/v2/runs/realism/_realism.json"))
    tier = {(r["set_id"], r["arm"]): r["tier"] for r in T}
    sets = {r["set_id"]: r for r in T}
    order = sorted(sets)
    if n_sets:
        order = order[:n_sets]

    rows, seen = [], set()
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
        def add(p, rel, shrink=False):
            """shrink=True for comparison images: they are looked at, not shipped,
            so a 1024px q82 JPEG is plenty and keeps the zip sendable. RAW INPUTS
            ARE NEVER SHRUNK -- references are rebuilt from them, and resampling the
            input would make the rebuild incomparable to the stored one."""
            if not (p and os.path.exists(p)):
                return ""
            if rel in seen:
                return rel
            if shrink:
                im = cv2.imread(p)
                if im is not None:
                    h, w = im.shape[:2]
                    k = 1024.0 / max(h, w)
                    if k < 1:
                        im = cv2.resize(im, (int(w * k), int(h * k)),
                                        interpolation=cv2.INTER_AREA)
                    ok, buf = cv2.imencode(".jpg", im,
                                           [cv2.IMWRITE_JPEG_QUALITY, 82])
                    if ok:
                        z.writestr(os.path.splitext(rel)[0] + ".jpg", buf.tobytes())
                        seen.add(rel)
                        return os.path.splitext(rel)[0] + ".jpg"
            z.write(p, rel); seen.add(rel)
            return rel

        for sid in order:
            s = sets[sid]
            pr = os.path.join(REPO, meta[s["person"]])
            gr = os.path.join(REPO, meta[s["garment"]])
            row = dict(
                set_id=sid, person=s["person"], garment=s["garment"],
                # RAW inputs -- the notebook rebuilds references from these
                person_img=add(pr, f"inputs/person/{os.path.basename(pr)}"),
                garment_img=add(gr, f"inputs/garment/{os.path.basename(gr)}"),
                hair_over_garment=s["hair_over_garment"],
                shipped_arm=real.get(sid, {}).get("arm", ""),
                shipped_tier=real.get(sid, {}).get("tier", ""))
            for a in ARMS:
                ref = arms.reference(a, s["garment"])
                row[f"ref_{a}"] = add(ref, f"stored_refs/{a}/{os.path.basename(ref)}", shrink=True) if ref else ""
                g = run["gen"].get(f"{sid}|{a}")
                row[f"fal_{a}"] = add(os.path.join(REPO, "v2/runs/amt/gen", g),
                                      f"stored_outputs/{g}", shrink=True) if g else ""
                row[f"tier_{a}"] = tier.get((sid, a), "")
            if sid in real:
                row["fal_realism"] = add(os.path.join(REPO, real[sid]["after"]),
                                         f"stored_realism/{os.path.basename(real[sid]['after'])}", shrink=True)
            rows.append(row)

        cols = list(rows[0])
        z.writestr("manifest.csv", "\n".join(
            [",".join(cols)] + [",".join('"' + str(r.get(c, "")).replace('"', '""') + '"'
                                         for c in cols) for r in rows]))
        z.writestr("README.txt",
                   "inputs/       raw person and garment -- references are rebuilt from these\n"
                   "stored_refs/  the fal-era references, to compare the rebuild against\n"
                   "stored_outputs/  the fal klein outputs, to compare generations against\n"
                   "stored_realism/  the fal SeedVR2 results\n"
                   "manifest.csv  one row per set, with the human tier for every arm\n")
    return OUT, len(rows), len(seen), os.path.getsize(OUT)


if __name__ == "__main__":
    p, n, f, s = build()
    print(f"{p}\n  {n} sets, {f} files, {s/1048576:.1f} MB")
