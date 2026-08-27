"""Phase 2: audit the colour reader, combine the two components, stress accessories.

  audit    CPU only, no spend - measured hex, assigned enum, quantisation error
  p7.3     framing clause AND ladder phrase in one prompt
  p7.1.3.n four accessory clauses: three that keep, one that drops

The accessory clauses are appended after the framing clause, so p7.1.3.n is p7.1.3 plus
one sentence and nothing else has moved.
"""
import csv
import json
import os
import sys

import cv2
import numpy as np

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "v2", "build"))
sys.path.insert(0, os.path.join(REPO, "v3", "build"))
import garment_crop as G     # noqa: E402
import phase3_fal as F       # noqa: E402
import run_p7n as P          # noqa: E402
import skin_tone as S        # noqa: E402

RUN = os.path.join(REPO, "v3", "runs", "v3.0b")
QWEN = "fal-ai/qwen-image-edit-2511"
SEED = 46

ACCESSORY = {
    "a": ("keep, symmetric",
          " Whatever the person is wearing or carrying, the mannequin has too, in the "
          "same place; whatever they do not have, it does not."),
    "b": ("keep, enumerated",
          " Keep the bag, hat, scarf, belt, glasses and jewellery if the person has "
          "them, and add none if they do not."),
    "c": ("drop",
          " Show the clothing only: no bag, no hat, no jewellery, no eyewear, even if "
          "the person has them."),
    "d": ("keep, placement",
          " Anything the person carries hangs on the mannequin the same way - over the "
          "same shoulder, in the same hand."),
    # e/f/g name the CLASS rather than the instances. "Accessories" has no canonical
    # instantiation - there is no default accessory the model can produce to satisfy the
    # word - so a category term asks for retention without handing over a list of
    # producible nouns. e is bare, f is grounded in the photograph, g is the negative.
    "e": ("keep, category, bare",
          " Keep all accessories."),
    "f": ("keep, category, grounded",
          " Keep every accessory the person is wearing or carrying, and add none they "
          "do not have."),
    "g": ("drop, category",
          " Remove all accessories."),
}


def hex_of(bgr_px):
    return "#%02X%02X%02X" % (bgr_px[2], bgr_px[1], bgr_px[0])


def delta_e(hex_a, hex_b):
    """CIE76 in Lab. Coarse, but the right units for 'is the swatch near the skin'."""
    def lab(h):
        r, g, b = (int(h[i:i + 2], 16) for i in (1, 3, 5))
        px = np.uint8([[[b, g, r]]])
        return cv2.cvtColor(px, cv2.COLOR_BGR2LAB)[0][0].astype(float)
    a, b = lab(hex_a), lab(hex_b)
    a[0] *= 100 / 255
    b[0] *= 100 / 255
    return float(np.sqrt(((a - b) ** 2).sum()))


def audit():
    """Every image, measured against assigned. CPU only."""
    rows = list(csv.DictReader(open(os.path.join(REPO, "test_set3", "manifest.csv"))))
    ladder = {n: h for n, _, h in S.TONES}
    out = []
    for r in rows:
        t = S.tone(cv2.imread(os.path.join(REPO, r["path"])))
        if not t:
            out.append({"id": r["id"], "path": r["path"], "tone": None})
            continue
        t["assigned_hex"] = ladder[t["name"]]
        t["deltaE"] = round(delta_e(t["measured_hex"], t["assigned_hex"]), 1)
        out.append({"id": r["id"], "path": r["path"], "tone": t})
    json.dump(out, open(os.path.join(REPO, "v3", "runs", "colour_audit.json"), "w"),
              indent=1)
    ok = [d for d in out if d["tone"]]
    de = sorted(d["tone"]["deltaE"] for d in ok)
    print(f"audit: {len(ok)}/{len(out)} read · deltaE median {de[len(de)//2]:.1f} "
          f"max {de[-1]:.1f} · over 20: {sum(1 for x in de if x > 20)}")
    return out


def build_jobs():
    rows = [r for r in csv.DictReader(open(os.path.join(
        REPO, "v3/testsets/v30_matrix_b.csv"))) if r["garment"] in P.PROBE]
    log, jobs = {}, []
    for r in rows:
        g, person = r["garment"], r["person"]
        gp = os.path.join(RUN, "inputs", f"{g}.jpg")
        t = S.tone(cv2.imread(os.path.join(RUN, "inputs", f"{person}.jpg")))
        word = t["name"] if t else "beige skin"
        fr = S.framing(cv2.imread(gp))
        clause = P.FRAME_SENTENCE[fr["framing"]]

        # p7.3 - both components, nothing else changed.
        pr = P.PREFIX + word + " " + P.SUFFIX + clause
        log[f"{g}|p7.3"] = {"prompt": pr, "colour": word, "framing": fr["framing"],
                            "person": person}
        jobs.append((f"{g}|p7.3", pr, gp))

        # p7.1.3.n - framing clause plus one accessory clause. No colour word, so the
        # accessory result is not entangled with the colour result.
        for k, (label, extra) in ACCESSORY.items():
            pr = P.PREFIX + P.SUFFIX + clause + extra
            log[f"{g}|p7.1.3.{k}"] = {"prompt": pr, "intent": label,
                                      "framing": fr["framing"]}
            jobs.append((f"{g}|p7.1.3.{k}", pr, gp))
    json.dump(log, open(os.path.join(RUN, "_phase2_prompts.json"), "w"), indent=1)
    return jobs


def main():
    F._load_env()
    audit()
    if "--audit-only" in sys.argv:
        return
    jobs = build_jobs()
    todo = [(k, p, gp) for k, p, gp in jobs
            if not os.path.exists(os.path.join(RUN, "refs", f"{k.replace('|', '__')}.jpg"))]
    print(f"{len(jobs)} arms, {len(todo)} to run")
    if "--dry" in sys.argv or not todo:
        return
    res = F.run([(k, (lambda pr=p, gp=gp: F.call(
        QWEN, {"image_urls": [F._b64(cv2.imread(gp))], "prompt": pr, "seed": SEED})))
        for k, p, gp in todo], 6)
    for k, v in res.items():
        if v is not None:
            G.write_rgb(os.path.join(RUN, "refs", f"{k.replace('|', '__')}.jpg"), v)
    print(f"\n{sum(1 for v in res.values() if v is not None)}/{len(todo)} written")


if __name__ == "__main__":
    main()
