"""v3.4 link A on fal: the locked version with and without the ankle cut, on the 31-pair
failure set, three seeds. One reference call per garment serves both arms (the cut is a
post-process). Inputs and A4 crops are the iron-man run's. Outputs v3/runs/v34/linkA/.
"""
import csv, json, os, sys, time
from concurrent.futures import ThreadPoolExecutor, as_completed
import cv2
REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "v3", "colab", "lib")); sys.path.insert(0, os.path.join(REPO, "v3", "build"))
import v3lib as L
import klein_local  # noqa  (not used; run_ironman imports it)
from run_ironman import SWAP, KEEP, HOLD, PERSON_CLAUSE, E3, recrop, ankle_cut, ankle_y
from run_v33_phase2 import load_env
IM = os.path.join(REPO, "v3", "runs", "ironman", "20260830_0548")
OUT = os.path.join(REPO, "v3", "runs", "v34", "linkA")
SEEDS = (46, 47, 48)

def main():
    load_env(); L.MODEL_DIR = os.path.join(REPO, "v2", "runs", ".models"); paths = L.fetch_models(verbose=False)
    for x in ("refs", "gen", "meta"): os.makedirs(os.path.join(OUT, x), exist_ok=True)
    rows = list(csv.DictReader(open(os.path.join(REPO, "v3", "testsets", "v34_failures.csv"))))
    garments = sorted({r["garment"] for r in rows}); meta = {}
    # references: one call per garment, then cut / uncut
    jobs = []
    for g in garments:
        crop = cv2.imread(os.path.join(IM, "inputs", f"{g}__A4.jpg")); fr = L.framing(crop, paths)["framing"]
        prompt = SWAP + KEEP + PERSON_CLAUSE[fr] + HOLD; meta[g] = {"framing": fr, "prompt": prompt}
        if not os.path.exists(os.path.join(OUT, "refs", f"{g}__Vnc.jpg")):
            jobs.append((g, crop, prompt))
    print(f"{len(garments)} garments, {len(jobs)} reference calls", flush=True)
    def ref(g, crop, prompt):
        im = recrop(L.call(L.KLEIN, {"image_urls": [L.b64(crop)], "prompt": prompt, "seed": SEEDS[0]}))
        cv2.imwrite(os.path.join(OUT, "refs", f"{g}__Vnc.jpg"), im, [cv2.IMWRITE_JPEG_QUALITY, 95])
        ya = ankle_y(crop, paths); cut, y = ankle_cut(im, paths, (ya / crop.shape[0]) if ya is not None else None)
        cv2.imwrite(os.path.join(OUT, "refs", f"{g}__V.jpg"), cut, [cv2.IMWRITE_JPEG_QUALITY, 95]); return g, y
    with ThreadPoolExecutor(4) as ex:
        for f in as_completed([ex.submit(ref, *j) for j in jobs]):
            g, y = f.result(); meta[g]["ankle_cut_row"] = y; print("  ref", g, "cut at", y, flush=True)
    json.dump(meta, open(os.path.join(OUT, "meta", "prompts.json"), "w"), indent=1)
    # edits
    jobs = []
    for r in rows:
        sid, p, g = r["set_id"], r["person"], r["garment"]
        person = cv2.imread(os.path.join(IM, "inputs", f"{p}.jpg"))
        for arm in ("V", "Vnc"):
            refim = cv2.imread(os.path.join(OUT, "refs", f"{g}__{arm}.jpg"))
            for s in SEEDS:
                out = os.path.join(OUT, "gen", f"{sid}__{arm}__s{s}.jpg")
                if os.path.exists(out): continue
                jobs.append((out, (lambda a=person, b=refim, s=s: L.call(L.KLEIN, {"image_urls": [L.b64(a), L.b64(b)], "prompt": E3, "seed": s}))))
    print(f"{len(jobs)} edits", flush=True); n = 0
    with ThreadPoolExecutor(6) as ex:
        futs = {ex.submit(fn): out for out, fn in jobs}
        for f in as_completed(futs):
            try: cv2.imwrite(futs[f], f.result(), [cv2.IMWRITE_JPEG_QUALITY, 95]); n += 1
            except Exception as e: print("  FAIL", os.path.basename(futs[f]), str(e)[:80], flush=True)
            if n % 40 == 0: print(f"  {n}", flush=True)
    json.dump({"backend": "fal " + L.KLEIN, "seeds": SEEDS, "edit_prompt": E3, "pairs": len(rows), "calls": len(garments) + len(jobs), "usd_fal": round((len(garments) + len(jobs)) * 0.015, 2)},
              open(os.path.join(OUT, "meta", "run.json"), "w"), indent=1)
    print("done")

if __name__ == "__main__":
    main()
