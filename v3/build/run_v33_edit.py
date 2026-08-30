"""v3.3 phase 4 / link 2: the edit. Q0 and Q3 references through klein, same 28 pairs,
same EDIT_PROMPT and seed as BC/MQ already in gen/. Outputs gen/{set_id}__{arm}.jpg.
"""
import csv, json, os, sys
from concurrent.futures import ThreadPoolExecutor, as_completed
import cv2
REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "v3", "colab", "lib")); sys.path.insert(0, os.path.join(REPO, "v3", "build"))
import v3lib as L
from run_v33_phase2 import load_env
RUN = os.path.join(REPO, "v3", "runs", "v3.0b")
REFS = {"Q0": "p3_Q0", "Q3": "p3_Q3_garment"}

def main():
    load_env()
    rows = list(csv.DictReader(open(os.path.join(REPO, "v3/testsets/v30_matrix_b.csv"))))
    jobs = []
    for r in rows:
        sid, p, g = r["set_id"], r["person"], r["garment"]
        person = cv2.imread(os.path.join(RUN, "inputs", f"{p}.jpg"))
        for arm, tag in REFS.items():
            out = os.path.join(RUN, "gen", f"{sid}__{arm}.jpg")
            if os.path.exists(out): continue
            ref = cv2.imread(os.path.join(RUN, "refs", f"{g}__{tag}.jpg"))
            jobs.append((out, (lambda a=person, b=ref: L.call(L.KLEIN, {"image_urls": [L.b64(a), L.b64(b)], "prompt": L.EDIT_PROMPT, "seed": L.SEED}))))
    print(f"{len(jobs)} edits", flush=True)
    with ThreadPoolExecutor(4) as ex:
        futs = {ex.submit(fn): out for out, fn in jobs}
        for f in as_completed(futs):
            try:
                im = f.result(); cv2.imwrite(futs[f], im, [cv2.IMWRITE_JPEG_QUALITY, 95])
                print("  ok  ", os.path.basename(futs[f]), "BLACK" if im.mean() < 5 else "", flush=True)
            except Exception as e:
                print("  FAIL", os.path.basename(futs[f]), str(e)[:100], flush=True)
                if "balance" in str(e).lower(): break
    json.dump({"arms": REFS, "edit_prompt": L.EDIT_PROMPT, "seed": L.SEED}, open(os.path.join(RUN, "_v33_edit.json"), "w"), indent=1)
    print("done")

if __name__ == "__main__":
    main()
