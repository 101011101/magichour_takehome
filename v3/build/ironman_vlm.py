"""VLM judge for the iron-man run, on V2's rubric, blind to the arm.

  python3 v3/build/ironman_vlm.py <run_dir> --model gpt-5-mini [--limit N] [--workers 8]
  python3 v3/build/ironman_vlm.py <run_dir> --compare [--votes votes.csv]

Score mode: every gen/{set_id}__{arm}__s{seed}.jpg gets one call with three images
(person, garment photograph, result) and returns six 1-5 scores + a note. Resumable:
rows already in meta/vlm_scores.csv are skipped. Token usage is recorded per call.

Compare mode (no API): per pair and seed, V against BC on the mean of the six and per
criterion -> meta/vlm_compare.csv and a summary; with --votes, agreement with the
reviewer's A/B votes after unblinding through key.csv.
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

CRITERIA = ["garment", "identity", "scene", "clean", "hands", "realism"]
SCHEMA = {"type": "object", "additionalProperties": False,
          "required": CRITERIA + ["note"],
          "properties": {**{k: {"type": "integer", "minimum": 1, "maximum": 5} for k in CRITERIA},
                         "note": {"type": "string", "maxLength": 300}}}
PROMPT = (
    "You are judging a virtual try-on output. Image 1: the original person. "
    "Image 2: the reference garment, as photographed on someone else. Image 3: the generated result. "
    "Score 1-5 (5 flawless): garment = is the output garment exactly the reference "
    "(color, print, cut, every piece); identity = same face/hair/body as image 1; scene = "
    "pose and background unchanged from image 1; clean = free of AI artifacts in skin, seams "
    "and textures (extra limbs or feet count here); hands = hands specifically are anatomically "
    "correct - score 5 if no hands are visible; realism = the image reads as a real photograph "
    "rather than an AI render. Return ONLY JSON matching the schema, keys: "
    + ", ".join(CRITERIA) + ", note.")
# USD per 1M tokens (input, output) - EDIT to the current price list before trusting the $ column
PRICE = {"gpt-5.5": (5.0, 15.0), "gpt-5": (1.25, 10.0), "gpt-5-mini": (0.25, 2.0), "gpt-4.1-mini": (0.4, 1.6)}


def b64(path):
    im = Image.open(path).convert("RGB"); im.thumbnail((768, 768))
    buf = io.BytesIO(); im.save(buf, "JPEG", quality=90)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def load_env():
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".env")
    for line in open(p):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1); os.environ.setdefault(k.strip(), v.strip())


def judge(client, model, person, garment, result, attempts=3):
    import jsonschema
    prompt, usage = PROMPT, {"in": 0, "out": 0}
    for _ in range(attempts):
        t0 = time.time()
        r = client.responses.create(model=model, input=[{"role": "user", "content": [
            {"type": "input_text", "text": prompt},
            {"type": "input_image", "image_url": b64(person)},
            {"type": "input_image", "image_url": b64(garment)},
            {"type": "input_image", "image_url": b64(result)}]}])
        u = getattr(r, "usage", None)
        if u is not None:
            usage["in"] += getattr(u, "input_tokens", 0) or 0; usage["out"] += getattr(u, "output_tokens", 0) or 0
        txt = r.output_text
        try:
            obj = json.loads(txt[txt.index("{"):txt.rindex("}") + 1]); jsonschema.validate(obj, SCHEMA)
            obj["seconds"] = round(time.time() - t0, 2); obj.update({"tokens_in": usage["in"], "tokens_out": usage["out"]})
            return obj
        except Exception as e:
            prompt = f"{PROMPT}\n\nYour previous reply was invalid ({str(e)[:120]}). Reply with valid JSON only."
    return None


def score(run, model, limit=None, workers=8):
    from openai import OpenAI
    load_env(); client = OpenAI()
    out = os.path.join(run, "meta", "vlm_scores.csv")
    done = set()
    if os.path.exists(out):
        done = {(r["set_id"], r["arm"], r["seed"]) for r in csv.DictReader(open(out))}
    jobs = []
    for f in sorted(os.listdir(os.path.join(run, "gen"))):
        if not f.endswith(".jpg"): continue
        sid, arm, seed = f[:-4].split("__"); seed = seed[1:]
        if (sid, arm, seed) in done: continue
        p, g = sid.split("+", 1)
        jobs.append((sid, arm, seed, os.path.join(run, "inputs", f"{p}.jpg"), os.path.join(run, "inputs", f"{g}.jpg"), os.path.join(run, "gen", f)))
    if limit: jobs = jobs[:int(limit)]
    print(f"{len(jobs)} outputs to judge on {model} ({len(done)} already scored)", flush=True)
    fields = ["set_id", "arm", "seed", "model"] + CRITERIA + ["note", "seconds", "tokens_in", "tokens_out"]
    new = not os.path.exists(out)
    with open(out, "a", newline="") as fh, ThreadPoolExecutor(workers) as ex:
        w = csv.DictWriter(fh, fieldnames=fields)
        if new: w.writeheader()
        futs = {ex.submit(judge, client, model, pp, gp, rp): (sid, arm, seed) for sid, arm, seed, pp, gp, rp in jobs}
        n = tin = tout = 0
        for f in as_completed(futs):
            sid, arm, seed = futs[f]; v = f.result()
            if v is None: print("  unscored", sid, arm, seed, flush=True); continue
            w.writerow({"set_id": sid, "arm": arm, "seed": seed, "model": model, **{k: v[k] for k in CRITERIA + ["note", "seconds", "tokens_in", "tokens_out"]}}); fh.flush()
            n += 1; tin += v["tokens_in"]; tout += v["tokens_out"]
            if n % 25 == 0: print(f"  {n}/{len(jobs)}", flush=True)
    pi, po = PRICE.get(model, (0, 0))
    usd = (tin * pi + tout * po) / 1e6
    print(f"scored {n}: {tin} in / {tout} out tokens; ~${usd:.2f} at the PRICE table "
          f"(${usd / max(n, 1):.4f} per output; extrapolated to 1200: ${usd / max(n, 1) * 1200:.2f})")


def compare(run, votes=None):
    rows = list(csv.DictReader(open(os.path.join(run, "meta", "vlm_scores.csv"))))
    by = {}
    for r in rows: by[(r["set_id"], r["seed"], r["arm"])] = r
    pairs = sorted({(r["set_id"], r["seed"]) for r in rows})
    out, wins = [], {"V": 0, "BC": 0, "tie": 0}
    crit_w = {c: {"V": 0, "BC": 0, "tie": 0} for c in CRITERIA}
    for sid, seed in pairs:
        v, b = by.get((sid, seed, "V")), by.get((sid, seed, "BC"))
        if not v or not b: continue
        mv = sum(int(v[c]) for c in CRITERIA) / 6; mb = sum(int(b[c]) for c in CRITERIA) / 6
        win = "V" if mv > mb else "BC" if mb > mv else "tie"; wins[win] += 1
        for c in CRITERIA:
            d = int(v[c]) - int(b[c]); crit_w[c]["V" if d > 0 else "BC" if d < 0 else "tie"] += 1
        out.append({"set_id": sid, "seed": seed, "mean_V": round(mv, 2), "mean_BC": round(mb, 2), "vlm_winner": win,
                    **{f"{c}_V": v[c] for c in CRITERIA}, **{f"{c}_BC": b[c] for c in CRITERIA}})
    with open(os.path.join(run, "meta", "vlm_compare.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out[0].keys())); w.writeheader(); w.writerows(out)
    n = len(out)
    print(f"{n} pair-seeds compared. VLM winner: V {wins['V']} ({wins['V']/n:.0%}) · BC {wins['BC']} ({wins['BC']/n:.0%}) · tie {wins['tie']}")
    for c in CRITERIA:
        mv = sum(int(by[(s, d, 'V')][c]) for s, d in pairs if (s, d, 'V') in by and (s, d, 'BC') in by) / n
        mb = sum(int(by[(s, d, 'BC')][c]) for s, d in pairs if (s, d, 'V') in by and (s, d, 'BC') in by) / n
        print(f"  {c:9s} mean V {mv:.2f}  BC {mb:.2f}   V better {crit_w[c]['V']:3d} · BC better {crit_w[c]['BC']:3d} · tie {crit_w[c]['tie']:3d}")
    if votes:
        key = {(r["set_id"], r["label"]): r["arm"] for r in csv.DictReader(open(os.path.join(run, "key.csv")))}
        hv = {(r["set_id"], r["seed"]): r["vote"] for r in csv.DictReader(open(votes))}
        agree = tot = 0
        for r in out:
            v = hv.get((r["set_id"], r["seed"]))
            if v in ("A", "B"):
                tot += 1; agree += key[(r["set_id"], v)] == r["vlm_winner"]
        print(f"agreement with the reviewer on {tot} decided pair-seeds: {agree/max(tot,1):.0%}")


if __name__ == "__main__":
    a = sys.argv
    run = a[1]
    if "--compare" in a:
        compare(run, a[a.index("--votes") + 1] if "--votes" in a else None)
    else:
        score(run, a[a.index("--model") + 1] if "--model" in a else "gpt-5-mini",
              a[a.index("--limit") + 1] if "--limit" in a else None,
              int(a[a.index("--workers") + 1]) if "--workers" in a else 8)
