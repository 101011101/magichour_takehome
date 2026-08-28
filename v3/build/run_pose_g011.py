"""Two diagnostics.

A. POSE WORD. The colour word decides whether a person or an object is rendered, and a
   person brings a stride. Rather than give up the skin-tone word, ask for the pose
   directly - a positive instruction naming what IS wanted, which is the form that has
   worked throughout this investigation. Two phrasings, on the four references whose
   matched colour produced a moving figure.

B. WHAT IS WRONG WITH g011. Its output has a "cooked" skin texture that colour does not
   fix. Three questions, separated so the answer names a stage:

     B1 is it the PERSON?     klein on p019 alone, text-only clothing edits, no reference
     B2 is it the REFERENCE?  klein on p019 with OTHER garment references
     B3 is it the PROMPT?     klein on p019 + g011 with different edit instructions

   If B1 cooks, p019 is simply hard to edit and the reference is innocent. If only B2's
   g011 cooks, the reference is at fault. If B3 varies, the edit instruction is a lever.
"""
import csv
import json
import os
import sys

import cv2

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "v2", "build"))
sys.path.insert(0, os.path.join(REPO, "v3", "build"))
import garment_crop as G     # noqa: E402
import phase3_fal as F       # noqa: E402
import run_p7n as P          # noqa: E402
import run_v30 as V          # noqa: E402
import skin_tone as S        # noqa: E402

RUN = os.path.join(REPO, "v3", "runs", "v3.0b")
QWEN = "fal-ai/qwen-image-edit-2511"
KLEIN = "fal-ai/flux-2/klein/4b/distilled/edit"
SEED = 46

POSE = {
    "none": "",
    "neutral": " The mannequin stands in a neutral upright pose, feet together.",
    "forward": " The mannequin stands straight and faces forward, weight even on both feet.",
}
POSE_REFS = ["g013", "g011", "g014", "g030"]

# B1 - text-only edits on the person, no garment reference at all
B1 = {
    "b1_black_tee": "Change the person's clothing to a plain black t-shirt.",
    "b1_red_dress": "Change the person's clothing to a red dress.",
    "b1_blue_shirt": "Change the person's clothing to a blue button-down shirt.",
}
# B2 - the standard try-on prompt, other references
B2 = ["g014", "g030", "dualuse_man_black_suit_studio_nonceleb"]
# B3 - g011's own reference, different edit instructions
B3 = {
    "b3_standard": V.PROMPT,
    "b3_garment_only": ("Replace only the clothing in image 1 with the clothing in "
                        "image 2. The person's skin, face, hair and the background are "
                        "unchanged."),
    "b3_terse": "Put the outfit from image 2 onto the person in image 1.",
    "b3_skin": ("Dress the person in image 1 in the clothing shown in image 2. The "
                "person's own skin tone and skin texture are unchanged everywhere they "
                "are visible."),
}


def main():
    F._load_env()
    rows = {r["garment"]: r for r in csv.DictReader(open(os.path.join(
        REPO, "v3/testsets/v30_matrix_b.csv")))}
    log, qjobs, kjobs = {}, [], []

    # ---- A: pose word ------------------------------------------------
    for g in POSE_REFS:
        r = rows[g]
        src = os.path.join(RUN, "inputs", f"{g}__A4.jpg")
        t = S.tone(cv2.imread(os.path.join(RUN, "inputs", f"{r['person']}.jpg")))
        colour = t["name"] if t else "beige skin"
        fr = S.framing(cv2.imread(src))["framing"]
        for tag, extra in POSE.items():
            if tag == "none":
                continue
            pr = P.PREFIX + colour + " " + P.SUFFIX + P.FRAME_SENTENCE[fr] + extra
            key = f"{g}__pose.{tag}"
            log[key] = {"prompt": pr, "colour": colour, "pose": tag,
                        "set_id": r["set_id"], "person": r["person"]}
            if not os.path.exists(os.path.join(RUN, "refs", f"{key}.jpg")):
                qjobs.append((key, pr, src))

    # ---- B: what is wrong with g011 ----------------------------------
    p019 = os.path.join(RUN, "inputs", "p019.jpg")
    for tag, pr in B1.items():
        out = f"p019__{tag}"
        log[out] = {"prompt": pr, "kind": "B1 person only, no reference"}
        if not os.path.exists(os.path.join(RUN, "gen", f"{out}.jpg")):
            kjobs.append((out, pr, [p019]))
    for g in B2:
        ref = os.path.join(RUN, "refs", f"{g}__MQ.jpg")
        out = f"p019__b2_{g[:18]}"
        log[out] = {"prompt": V.PROMPT, "kind": f"B2 other reference: {g}"}
        if os.path.exists(ref) and not os.path.exists(os.path.join(RUN, "gen", f"{out}.jpg")):
            kjobs.append((out, V.PROMPT, [p019, ref]))
    g011ref = os.path.join(RUN, "refs", "g011__MQ.jpg")
    for tag, pr in B3.items():
        out = f"p019__{tag}"
        log[out] = {"prompt": pr, "kind": "B3 g011 reference, varied instruction"}
        if not os.path.exists(os.path.join(RUN, "gen", f"{out}.jpg")):
            kjobs.append((out, pr, [p019, g011ref]))

    json.dump(log, open(os.path.join(RUN, "_pose_g011.json"), "w"), indent=1)
    print(f"pose: {len(qjobs)} qwen · g011 diagnostic: {len(kjobs)} klein")
    if "--dry" in sys.argv:
        return

    if qjobs:
        res = F.run([(k, (lambda p=pr, s=src: F.call(
            QWEN, {"image_urls": [F._b64(cv2.imread(s))], "prompt": p, "seed": SEED})))
            for k, pr, src in qjobs], 6)
        for k, v in res.items():
            if v is not None:
                G.write_rgb(os.path.join(RUN, "refs", f"{k}.jpg"), v)
        # edit each new pose reference so the effect is visible end to end
        for k in res:
            if res[k] is None:
                continue
            g = k.split("__")[0]
            sid = log[k]["set_id"]
            out = f"{sid}__{k.split('__')[1]}"
            if not os.path.exists(os.path.join(RUN, "gen", f"{out}.jpg")):
                kjobs.append((out, V.PROMPT,
                              [os.path.join(RUN, "inputs", f"{log[k]['person']}.jpg"),
                               os.path.join(RUN, "refs", f"{k}.jpg")]))

    if kjobs:
        print(f"klein: {len(kjobs)} calls (~${len(kjobs)*0.015:.2f})")
        res = F.run([(k, (lambda p=pr, im=imgs: F.call(
            KLEIN, {"image_urls": [F._b64(cv2.imread(x)) for x in im],
                    "prompt": p, "seed": SEED}))) for k, pr, imgs in kjobs], 6)
        for k, v in res.items():
            if v is not None:
                G.write_rgb(os.path.join(RUN, "gen", f"{k}.jpg"), v)
    print("done")


if __name__ == "__main__":
    main()
