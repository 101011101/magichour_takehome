"""v3.3 phase 7: the chest_up row of PERSON_CLAUSE gains "arms down". Only p030's prompt
changes; regenerate its reference from the table and edit its pair with the E3 prompt.
"""
import csv, json, os, sys
import cv2
REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "v3", "colab", "lib")); sys.path.insert(0, os.path.join(REPO, "v3", "build"))
import v3lib as L
from run_v33_phase2 import recrop, load_env
from run_v33_phase3 import build
from run_v33_feet import cut_ankle
RUN = os.path.join(REPO, "v3", "runs", "v3.0b")
E3 = L.EDIT_PROMPT + " The person's body, limbs and feet are exactly as in image 1 - nothing added, nothing removed."

def main():
    load_env(); L.MODEL_DIR = os.path.join(REPO, "v2", "runs", ".models"); paths = L.fetch_models(verbose=False)
    rows = {r["garment"]: r for r in csv.DictReader(open(os.path.join(REPO, "v3/testsets/v30_matrix_b.csv")))}
    p3 = json.load(open(os.path.join(RUN, "_v33_p3_prompts.json")))
    changed, meta = [], {}
    for g in rows:
        crop = cv2.imread(os.path.join(RUN, "inputs", f"{g}__A4.jpg")); fr = L.framing(crop, paths)["framing"]
        prompt = build("Q3_garment", fr)
        if prompt != p3[f"{g}|Q3_garment"]["prompt"]:
            changed.append(g); meta[g] = {"framing": fr, "prompt": prompt, "seed": L.SEED}
    print("prompts changed by the row edit:", changed, flush=True)
    for g in changed:
        r = rows[g]; sid, p = r["set_id"], r["person"]
        crop = cv2.imread(os.path.join(RUN, "inputs", f"{g}__A4.jpg"))
        ref = os.path.join(RUN, "refs", f"{g}__p7_Q3.jpg")
        if not os.path.exists(ref):
            im = recrop(L.call(L.KLEIN, {"image_urls": [L.b64(crop)], "prompt": meta[g]["prompt"], "seed": L.SEED}))
            im, y = cut_ankle(im, paths); meta[g]["ankle_cut_row"] = y
            cv2.imwrite(ref, im, [cv2.IMWRITE_JPEG_QUALITY, 95]); print("  ref ", os.path.basename(ref), flush=True)
        out = os.path.join(RUN, "gen", f"{sid}__P7E3.jpg")
        if not os.path.exists(out):
            person = cv2.imread(os.path.join(RUN, "inputs", f"{p}.jpg"))
            cv2.imwrite(out, L.call(L.KLEIN, {"image_urls": [L.b64(person), L.b64(cv2.imread(ref))], "prompt": E3, "seed": L.SEED}), [cv2.IMWRITE_JPEG_QUALITY, 95])
            print("  edit", os.path.basename(out), flush=True)
    json.dump({"changed": changed, "meta": meta, "edit_prompt": E3}, open(os.path.join(RUN, "_v33_p7.json"), "w"), indent=1)
    print("done")

if __name__ == "__main__":
    main()
