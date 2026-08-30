"""v3.3 phase 8: the complete version on the fold, as one pipeline.
  reference  Q3 (M1 head swap + PERSON_CLAUSE with the arms row + garment hold), crop-first,
             bbox re-crop, ANKLE CUT   -> refs/{g}__V.jpg
  edit       E3 prompt                 -> gen/{set_id}__V.jpg
Control: gen/{set_id}__E3.jpg (same everything, no ankle cut).
"""
import csv, json, os, sys
from concurrent.futures import ThreadPoolExecutor, as_completed
import cv2
REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "v3", "colab", "lib")); sys.path.insert(0, os.path.join(REPO, "v3", "build"))
import v3lib as L
from run_v33_phase2 import load_env
from run_v33_feet import cut_ankle, ankle_y, FALLBACK
RUN = os.path.join(REPO, "v3", "runs", "v3.0b")
E3 = L.EDIT_PROMPT + " The person's body, limbs and feet are exactly as in image 1 - nothing added, nothing removed."

def main():
    load_env(); L.MODEL_DIR = os.path.join(REPO, "v2", "runs", ".models"); paths = L.fetch_models(verbose=False)
    rows = list(csv.DictReader(open(os.path.join(REPO, "v3/testsets/v30_matrix_b.csv"))))
    meta, jobs = {}, []
    for r in rows:
        g, p, sid = r["garment"], r["person"], r["set_id"]
        ref = os.path.join(RUN, "refs", f"{g}__V.jpg")
        src = os.path.join(RUN, "refs", "p030__p7_Q3.jpg") if g == "p030" else os.path.join(RUN, "refs", f"{g}__p3_Q3_garment.jpg")
        if not os.path.exists(ref):
            if g == "p030":
                im, y = cv2.imread(src), "already cut in phase 7"
            else:
                a4 = cv2.imread(os.path.join(RUN, "inputs", f"{g}__A4.jpg")); ya = ankle_y(a4, paths)
                if ya is not None: FALLBACK[g] = ya / a4.shape[0]
                im, y = cut_ankle(cv2.imread(src), paths, g)
            cv2.imwrite(ref, im, [cv2.IMWRITE_JPEG_QUALITY, 95])
            meta[g] = {"source": os.path.basename(src), "ankle_cut_row": y, "reader_on_reference": ankle_y(cv2.imread(src), paths) is not None}
        out = os.path.join(RUN, "gen", f"{sid}__V.jpg")
        if os.path.exists(out): continue
        person = cv2.imread(os.path.join(RUN, "inputs", f"{p}.jpg"))
        jobs.append((out, (lambda a=person, b=cv2.imread(ref): L.call(L.KLEIN, {"image_urls": [L.b64(a), L.b64(b)], "prompt": E3, "seed": L.SEED}))))
    json.dump({"refs": meta, "edit_prompt": E3, "seed": L.SEED}, open(os.path.join(RUN, "_v33_version.json"), "w"), indent=1)
    uncut = [g for g, m in meta.items() if m["ankle_cut_row"] is None]
    print(f"{len(meta)} refs cut ({len(uncut)} with no ankle found: {uncut}); {len(jobs)} edits", flush=True)
    with ThreadPoolExecutor(4) as ex:
        futs = {ex.submit(fn): out for out, fn in jobs}
        for f in as_completed(futs):
            try:
                im = f.result(); cv2.imwrite(futs[f], im, [cv2.IMWRITE_JPEG_QUALITY, 95]); print("  ok  ", os.path.basename(futs[f]), "BLACK" if im.mean() < 5 else "", flush=True)
            except Exception as e: print("  FAIL", os.path.basename(futs[f]), str(e)[:100], flush=True)
    print("done")

if __name__ == "__main__":
    main()
