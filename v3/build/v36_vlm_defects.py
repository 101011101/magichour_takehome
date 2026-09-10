"""VLM defect judge for v3.6: three booleans per output, blind to the arm.

  python3 v3/build/v36_vlm_defects.py --arms ER,BC [--model gpt-5-mini] [--limit N] [--workers 8]

One call per cell with three images (person, reference garment, result). The rubric is
defects only - no fidelity, identity or realism scoring: limbs_over (the output has more
limbs/extremities than the person does), phasing (the old garment bleeding through the
new one), artifacts (any other clear AI artifact). Resumable: rows already in
meta/vlm_defects.csv are skipped. Token usage is recorded per call.
"""
import base64
import csv
import io
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from PIL import Image

REPO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
CELLS = os.path.join(REPO, "v3", "colab", "v36_ironman_er.csv")
PERSONS = os.path.join(REPO, "v3", "runs", "v34", "ironman2", "inputs")
REFS = os.path.join(REPO, "v3", "runs", "v34", "ironman2_bc", "refs")
OUT = os.path.join(REPO, "v3", "runs", "v36", "ironman_er", "meta", "vlm_defects.csv")
GEN = {"ER": os.path.join(REPO, "v3", "runs", "v36", "ironman_er", "gen"),
       "BC": os.path.join(REPO, "v3", "runs", "v34", "ironman2_bc", "gen")}

FIELDS = ["set_id", "seed", "arm", "limbs_over", "limb_count_note", "phasing", "artifacts",
          "artifact_note", "tokens_in", "tokens_out"]
SCHEMA = {"type": "object", "additionalProperties": False,
          "required": ["limbs_over", "limb_count_note", "phasing", "artifacts", "artifact_note"],
          "properties": {"limbs_over": {"type": "boolean"},
                         "limb_count_note": {"type": "string", "maxLength": 120},
                         "phasing": {"type": "boolean"},
                         "artifacts": {"type": "boolean"},
                         "artifact_note": {"type": "string", "maxLength": 120}}}
PROMPT = (
    "You are inspecting one image for defects. Image 1: the original person. Image 2: a "
    "reference garment, as photographed on someone else. Image 3: an image of the person "
    "from image 1 wearing the garment from image 2. Judge image 3 only, against image 1 for "
    "what the person's body actually is. Report three defects as booleans, true when the "
    "defect is present:\n"
    "limbs_over - image 3 shows more limbs or extremities than the person has: an extra arm, "
    "hand, leg, foot or shoe, or two limbs fused into one. Count what is visible in image 1 "
    "before deciding; a limb merely uncovered or newly visible is not a defect.\n"
    "limb_count_note - a few words naming what you saw, empty string if limbs_over is false.\n"
    "phasing - clothing bleeding through: the person's original garment from image 1 showing "
    "through, under or behind the new clothing, or two fabrics merging into each other with no "
    "clear edge between them.\n"
    "artifacts - any other clear AI artifact: melted or warped skin or texture, impossible "
    "seams, garbled text or logos, duplicated background objects, smeared hands.\n"
    "artifact_note - a few words naming it, empty string if artifacts is false.\n"
    "Judge only what is clearly visible. Return ONLY JSON matching the schema, keys: "
    "limbs_over, limb_count_note, phasing, artifacts, artifact_note.")
# USD per 1M tokens (input, output) - EDIT to the current price list before trusting the $ column
PRICE = {"gpt-5.5": (5.0, 15.0), "gpt-5": (1.25, 10.0), "gpt-5-mini": (0.25, 2.0), "gpt-4.1-mini": (0.4, 1.6)}


def b64(path):
    im = Image.open(path).convert("RGB"); im.thumbnail((768, 768))
    buf = io.BytesIO(); im.save(buf, "JPEG", quality=90)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def load_env():
    for line in open(os.path.join(REPO, ".env"), encoding="utf-8"):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def judge(client, model, person, garment, result, attempts=3):
    import jsonschema
    prompt, usage = PROMPT, {"in": 0, "out": 0}
    imgs = [b64(person), b64(garment), b64(result)]      # encode once, reused across retries
    for _ in range(attempts):
        try:
            r = client.responses.create(model=model, input=[{"role": "user", "content": [
                {"type": "input_text", "text": prompt}] + [{"type": "input_image", "image_url": u} for u in imgs]}])
        except Exception:
            time.sleep(2); continue
        u = getattr(r, "usage", None)
        if u is not None:
            usage["in"] += getattr(u, "input_tokens", 0) or 0; usage["out"] += getattr(u, "output_tokens", 0) or 0
        txt = r.output_text
        try:
            obj = json.loads(txt[txt.index("{"):txt.rindex("}") + 1]); jsonschema.validate(obj, SCHEMA)
            obj.update({"tokens_in": usage["in"], "tokens_out": usage["out"]})
            return obj
        except Exception as e:
            prompt = f"{PROMPT}\n\nYour previous reply was invalid ({str(e)[:120]}). Reply with valid JSON only."
    return None


def run(arms, model, limit=None, workers=8, budget_usd=5.0):
    from openai import OpenAI
    load_env(); client = OpenAI()
    done = set()
    if os.path.exists(OUT):
        done = {(r["set_id"], r["seed"], r["arm"]) for r in csv.DictReader(open(OUT))}
    cells = list(csv.DictReader(open(CELLS)))
    jobs = []
    for r in cells:
        for arm in arms:
            key = (r["set_id"], r["seed"], arm)
            if key in done: continue
            res = os.path.join(GEN[arm], f"{r['set_id']}__{arm}__s{r['seed']}.jpg")
            if not os.path.exists(res): print("  no image", key, flush=True); continue
            jobs.append((key, os.path.join(PERSONS, f"{r['person']}.jpg"),
                         os.path.join(REFS, f"{r['garment']}__BC.jpg"), res))
    jobs.sort(key=lambda j: (int(j[0][1]), j[0][0], j[0][2]))   # seed 46 across both arms first
    if limit: jobs = jobs[:int(limit)]
    print(f"{len(jobs)} cells to judge on {model} ({len(done)} already judged)", flush=True)
    new = not os.path.exists(OUT)
    pi, po = PRICE.get(model, (0, 0))
    n = tin = tout = 0; usd = 0.0
    with open(OUT, "a", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        if new: w.writeheader()
        for i in range(0, len(jobs), workers * 4):          # batches, so the budget stop is honoured
            batch = jobs[i:i + workers * 4]
            with ThreadPoolExecutor(workers) as ex:
                futs = {ex.submit(judge, client, model, pp, gp, rp): key for key, pp, gp, rp in batch}
                for f in as_completed(futs):
                    sid, seed, arm = futs[f]; v = f.result()
                    if v is None: print("  unjudged", sid, seed, arm, flush=True); continue
                    w.writerow({"set_id": sid, "seed": seed, "arm": arm,
                                **{k: v[k] for k in FIELDS[3:]}}); fh.flush()
                    n += 1; tin += v["tokens_in"]; tout += v["tokens_out"]
            usd = (tin * pi + tout * po) / 1e6
            print(f"  {n}/{len(jobs)}  ~${usd:.3f}", flush=True)
            if usd >= budget_usd:
                print(f"BUDGET STOP at ~${usd:.3f} (limit ${budget_usd}); re-run to continue", flush=True); break
    print(f"judged {n}: {tin} in / {tout} out tokens; ~${usd:.3f} at the PRICE table "
          f"(${usd / max(n, 1):.5f} per cell)")


if __name__ == "__main__":
    a = sys.argv
    run(a[a.index("--arms") + 1].split(",") if "--arms" in a else ["ER", "BC"],
        a[a.index("--model") + 1] if "--model" in a else "gpt-5-mini",
        a[a.index("--limit") + 1] if "--limit" in a else None,
        int(a[a.index("--workers") + 1]) if "--workers" in a else 8,
        float(a[a.index("--budget") + 1]) if "--budget" in a else 5.0)
