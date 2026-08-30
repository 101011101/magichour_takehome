"""v3.3 phase-3 probes, after review of link 5:
  p030   arms raised over the head in a chest_up crop -> Q3 + an arms sentence, p030 only
  Q6     "Feet straight." instead of "feet point towards the camera", full_body only
Outputs refs/{g}__p3_{arm}raw.jpg / .jpg; prompts appended to _v33_p3_prompts.json.
"""
import csv, json, os, sys
from concurrent.futures import ThreadPoolExecutor, as_completed
import cv2
REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "v3", "colab", "lib")); sys.path.insert(0, os.path.join(REPO, "v3", "build"))
import v3lib as L
from run_v33_phase2 import recrop, load_env
from run_v33_phase3 import build, RUN, META
ARMS = {"A1_armsdown": " Arms down, relaxed at the sides.",
        "A2_armssides": " Arms at the sides.",
        "Q6_feetstraight": " Feet straight."}

def main():
    load_env(); L.MODEL_DIR = os.path.join(REPO, "v2", "runs", ".models"); paths = L.fetch_models(verbose=False)
    rows = list(csv.DictReader(open(os.path.join(REPO, "v3/testsets/v30_matrix_b.csv"))))
    meta = json.load(open(META)); jobs = []
    for r in rows:
        g = r["garment"]; fr = meta[f"{g}|Q0"]["framing"]
        crop = cv2.imread(os.path.join(RUN, "inputs", f"{g}__A4.jpg"))
        for arm, add in ARMS.items():
            if arm.startswith("A") and g != "p030": continue
            if arm == "Q6_feetstraight" and fr != "full_body": continue
            prompt = build("Q3_garment", fr) + add
            meta[f"{g}|{arm}"] = {"prompt": prompt, "framing": fr, "same_as_Q0": False, "endpoint": L.KLEIN, "seed": L.SEED, "base": "Q3"}
            out = os.path.join(RUN, "refs", f"{g}__p3_{arm}raw.jpg")
            if os.path.exists(out): continue
            jobs.append((out, (lambda b=crop, q=prompt: L.call(L.KLEIN, {"image_urls": [L.b64(b)], "prompt": q, "seed": L.SEED}))))
    json.dump(meta, open(META, "w"), indent=1); print(f"{len(jobs)} calls", flush=True)
    with ThreadPoolExecutor(4) as ex:
        futs = {ex.submit(fn): out for out, fn in jobs}
        for f in as_completed(futs):
            try:
                im = f.result(); cv2.imwrite(futs[f], im, [cv2.IMWRITE_JPEG_QUALITY, 95])
                cv2.imwrite(futs[f].replace("raw.jpg", ".jpg"), recrop(im), [cv2.IMWRITE_JPEG_QUALITY, 95])
                print("  ok  ", os.path.basename(futs[f]), "BLACK" if im.mean() < 5 else "", flush=True)
            except Exception as e:
                print("  FAIL", os.path.basename(futs[f]), str(e)[:100], flush=True)
    print("done")

if __name__ == "__main__":
    main()
