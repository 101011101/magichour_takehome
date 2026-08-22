# Run the chosen realism pass over exactly what the harness would ship.
#
# No new generations: the harness is replayed over stored arm outputs, the final
# selected frame per set is identified, and only that frame goes through SeedVR2.
# 38 calls. This is the first time the v2.1 winner has been applied to the v2.2.3
# output -- the "composite never validated end to end" gap.
import csv, json, os, sys, time

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(REPO, "v2", "runs", "realism")
LOG = os.path.join(OUT, "_realism.json")
ENDPOINT = "fal-ai/seedvr/upscale/image"
SEED = 46
HAIR_T = 0.14
ID_ESCALATE = 0.90
BAD = {"FAIL", "BROKEN"}


def shipped():
    """The frame the shipped harness lands on, per set.

    Escalate to QX if ANY of: noop < 0.5, identity < 0.90, garment == FAIL,
    tryon != PERFECT. Identity joined the rule on 2026-08-22 -- it fires once, on
    HD_p028+navy_peacoat, and is the difference between 1 shipped failure and 0."""
    T = list(csv.DictReader(open(f"{REPO}/v223_perfect_tier_picks.csv")))
    E = list(csv.DictReader(open(f"{REPO}/v223_vlm_eval.csv")))
    run = json.load(open(f"{REPO}/v2/runs/amt/_run.json"))
    tier = {(r["set_id"], r["arm"]): r["tier"] for r in T}
    hair = {r["set_id"]: float(r["hair_over_garment"]) for r in T}
    noop = {(r["set_id"], r["arm"]): float(r["chk_noop"]) for r in T}
    ident = {(r["set_id"], r["arm"]): float(r["chk_identity"]) for r in T}
    V = {(r["set_id"], r["arm"], r["prompt"]): r["vlm_verdict"] for r in E}

    out = []
    for sid in sorted(hair):
        arm = "BC_klein" if hair[sid] >= HAIR_T else "PHEAD"
        fired = (noop[(sid, arm)] < 0.5
                 or ident[(sid, arm)] < ID_ESCALATE
                 or V.get((sid, arm, "tryon")) != "PERFECT"
                 or V.get((sid, arm, "garment")) == "FAIL")
        landed = "QX_qwen_p1" if fired else arm
        out.append({"set_id": sid, "first_arm": arm, "escalated": fired,
                    "arm": landed, "tier": tier[(sid, landed)],
                    "src": os.path.join(REPO, "v2", "runs", "amt", "gen",
                                        run["gen"][f"{sid}|{landed}"])})
    return out


# --- the shipped policy, gated on both ends. Thresholds are fitted on 38 frames;
# the mechanism (a pass that fails to sharpen is also damaging the face) is the
# transferable part. See prd/v2/v2.4/RESULTS.md.
HF_SKIP = 2.5      # already sharp: nothing to restore, so the call is dead cost
ID_FLOOR = 0.90    # it damaged the face: keep the original


def hf(gray):
    import cv2
    import numpy as np
    b = cv2.GaussianBlur(gray, (0, 0), 2.0)
    return float(np.abs(gray.astype(np.float32) - b).mean())


def should_run(bgr):
    """Pre-check. Skip frames that are already sharp."""
    import cv2
    return hf(cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)) < HF_SKIP


def accept(before_bgr, after_bgr, face_app):
    """Post-check. Revert when the pass cost identity -- which, empirically, is the
    same set of frames on which it failed to sharpen (corr = +0.512)."""
    import cv2
    import numpy as np
    a = cv2.resize(after_bgr, (before_bgr.shape[1], before_bgr.shape[0]),
                   interpolation=cv2.INTER_AREA)

    def emb(x):
        fs = face_app.get(x) if face_app else []
        if not fs:
            return None
        f = max(fs, key=lambda z: (z.bbox[2] - z.bbox[0]) * (z.bbox[3] - z.bbox[1]))
        v = f.normed_embedding
        return v / (np.linalg.norm(v) + 1e-9)
    e0, e1 = emb(before_bgr), emb(a)
    if e0 is None or e1 is None:
        return True, None            # no face to protect: nothing to revert for
    c = float(np.dot(e0, e1))
    return c >= ID_FLOOR, c


def main(live=False):
    os.makedirs(OUT, exist_ok=True)
    rows = shipped()
    done = json.load(open(LOG)) if os.path.exists(LOG) else {}
    esc = sum(r["escalated"] for r in rows)
    print(f"{len(rows)} sets | {esc} escalated to QX | "
          f"{len(rows)-esc} shipped the first arm")
    print(f"est ${0.04*len([r for r in rows if r['set_id'] not in done]):.2f}")
    if not live:
        print("dry run — pass --live to spend")
        return

    for line in open(f"{REPO}/.env"):
        if line.startswith("FAL_KEY="):
            os.environ["FAL_KEY"] = line.split("=", 1)[1].strip()
    import fal_client
    import urllib.request

    t0 = time.time()
    for i, r in enumerate(rows, 1):
        if r["set_id"] in done:
            continue
        dst = os.path.join(OUT, f"{r['set_id']}__after.png")
        try:
            u = fal_client.upload_file(r["src"])
            res = fal_client.subscribe(ENDPOINT, arguments={
                "image_url": u, "upscale_mode": "factor", "upscale_factor": 2,
                "noise_scale": 0.0, "seed": SEED, "output_format": "png"})
            url = (res.get("image") or {}).get("url") or res.get("url")
            urllib.request.urlretrieve(url, dst)
            done[r["set_id"]] = dict(r, after=os.path.relpath(dst, REPO))
        except Exception as ex:
            print(f"  {r['set_id'][:40]:40} ERR {type(ex).__name__}: {str(ex)[:70]}")
            continue
        json.dump(done, open(LOG, "w"), indent=1)
        if i % 5 == 0 or i == len(rows):
            print(f"  {len(done)}/{len(rows)}  {(time.time()-t0)/max(len(done),1):.1f}s each")
    print(f"done: {len(done)}/{len(rows)} in {(time.time()-t0)/60:.1f} min")


if __name__ == "__main__":
    main("--live" in sys.argv)
