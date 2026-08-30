"""v3.3 phase 6: the first variation of call 2. Four sentences appended to EDIT_PROMPT,
Q3 reference held fixed, on the seated case and three clean pairs. gen/{set_id}__E{n}.jpg.
"""
import csv, json, os, sys
from concurrent.futures import ThreadPoolExecutor, as_completed
import cv2
REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "v3", "colab", "lib")); sys.path.insert(0, os.path.join(REPO, "v3", "build"))
import v3lib as L
from run_v33_phase2 import load_env
RUN = os.path.join(REPO, "v3", "runs", "v3.0b")
PAIRS = [r["set_id"] for r in csv.DictReader(open(os.path.join(REPO, "v3/testsets/v30_matrix_b.csv")))] if "--all" in sys.argv else ["p021+g013", "p022+g014", "p008+dualuse_scarlett_johansson_black_dress_backview_night",
         "p003+dualuse_emma_watson_black_blazer_armscrossed"]
ONLY = {"E3"} if "--all" in sys.argv else None
E = {"E1": " Do not add any body parts.",
     "E2": " The person has exactly two legs and two feet.",
     "E3": " The person's body, limbs and feet are exactly as in image 1 - nothing added, nothing removed.",
     "E4": " The clothing drapes over the body as one garment; the body underneath is unchanged."}

def main():
    load_env()
    rows = {r["set_id"]: r for r in csv.DictReader(open(os.path.join(REPO, "v3/testsets/v30_matrix_b.csv")))}
    meta, jobs = {"E0": L.EDIT_PROMPT}, []
    for sid in PAIRS:
        r = rows[sid]; p, g = r["person"], r["garment"]
        person = cv2.imread(os.path.join(RUN, "inputs", f"{p}.jpg")); ref = cv2.imread(os.path.join(RUN, "refs", f"{g}__p3_Q3_garment.jpg"))
        for arm, add in E.items():
            if ONLY and arm not in ONLY: continue
            meta[arm] = L.EDIT_PROMPT + add
            out = os.path.join(RUN, "gen", f"{sid}__{arm}.jpg")
            if os.path.exists(out): continue
            jobs.append((out, (lambda a=person, b=ref, q=L.EDIT_PROMPT + add: L.call(L.KLEIN, {"image_urls": [L.b64(a), L.b64(b)], "prompt": q, "seed": L.SEED}))))
    if not ONLY:
        json.dump({"pairs": PAIRS, "prompts": meta, "reference": "p3_Q3_garment", "seed": L.SEED}, open(os.path.join(RUN, "_v33_edit2.json"), "w"), indent=1)
    print(f"{len(jobs)} edits", flush=True)
    with ThreadPoolExecutor(4) as ex:
        futs = {ex.submit(fn): out for out, fn in jobs}
        for f in as_completed(futs):
            try:
                im = f.result(); cv2.imwrite(futs[f], im, [cv2.IMWRITE_JPEG_QUALITY, 95]); print("  ok  ", os.path.basename(futs[f]), "BLACK" if im.mean() < 5 else "", flush=True)
            except Exception as e: print("  FAIL", os.path.basename(futs[f]), str(e)[:100], flush=True)
    print("done")

if __name__ == "__main__":
    main()
