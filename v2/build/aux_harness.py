# Auxiliary-model harness — single-image realism models.
#
# Criteria and bucket definitions: prd/v2/SCORING_CRITERIA.md.
# Auxiliary models take ONE image and must raise realism without touching
# fidelity, so every metric here compares the model's OUTPUT against its own
# INPUT (not against the original person/garment): fidelity = "did not change
# what it was given".
#
# Stages (each flag-gated; nothing paid runs without an explicit flag):
#   generate -> deterministic scoring -> pairwise VLM -> v21_aux_screen.html
# Usage:
#   python v2/build/aux_harness.py --generate --judge --html
#   python v2/build/aux_harness.py --html          # rebuild page from CSVs
import argparse
import base64
import io
import json
import os
import sys
import threading
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pandas as pd
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import metrics_v2 as M                      # _embed, _torso_crop, identity_cosine

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RUNS = os.path.join(REPO, "v2", "runs")
for _line in (open(os.path.join(REPO, ".env")) if
              os.path.exists(os.path.join(REPO, ".env")) else []):
    _line = _line.strip()
    if _line and not _line.startswith("#") and "=" in _line:
        _k, _, _v = _line.partition("=")
        os.environ.setdefault(_k.strip(), _v.strip())
AUX = os.path.join(RUNS, "aux")
ART = os.path.join(REPO, "v2", "artifacts")
RUNS_REL = "../runs"        # page lives in v2/artifacts/, images stay in v2/runs/
JUDGE_MODEL = "gpt-5.5"
BUDGET_USD = 3.00

# BEFORE set: outputs of the editing base (FASHN v1.5). Aux models are selected
# on the inputs they will actually see in the deployed pipeline.
BEFORE_ARM = "fashn_v15"

# One entry per CONFIG, not per model: fidelity preservation is
# config-dependent (strength / noise), so each setting is ranked separately.
CONFIGS = {
    "seedvr2_x2_noise0": {
        "endpoint": "fal-ai/seedvr/upscale/image", "est_usd": 0.04,
        "args": lambda url, seed: {"image_url": url, "upscale_mode": "factor",
                                   "upscale_factor": 2, "noise_scale": 0.0,
                                   "seed": seed, "output_format": "png"},
        "note": "restore/sharpen, noise injection off"},
    "seedvr2_x2_noise01": {
        "endpoint": "fal-ai/seedvr/upscale/image", "est_usd": 0.04,
        "args": lambda url, seed: {"image_url": url, "upscale_mode": "factor",
                                   "upscale_factor": 2, "noise_scale": 0.1,
                                   "seed": seed, "output_format": "png"},
        "note": "restore/sharpen, fal default noise"},
    "zimage_s015": {
        "endpoint": "fal-ai/z-image/turbo/image-to-image", "est_usd": 0.01,
        "args": lambda url, seed: {"image_url": url, "prompt": REFINE_PROMPT,
                                   "strength": 0.15, "seed": seed,
                                   "enable_prompt_expansion": False},
        "note": "de-plastic pass, low denoise"},
    "zimage_s025": {
        "endpoint": "fal-ai/z-image/turbo/image-to-image", "est_usd": 0.01,
        "args": lambda url, seed: {"image_url": url, "prompt": REFINE_PROMPT,
                                   "strength": 0.25, "seed": seed,
                                   "enable_prompt_expansion": False},
        "note": "de-plastic pass, mid denoise"},
    "zimage_s035": {
        "endpoint": "fal-ai/z-image/turbo/image-to-image", "est_usd": 0.01,
        "args": lambda url, seed: {"image_url": url, "prompt": REFINE_PROMPT,
                                   "strength": 0.35, "seed": seed,
                                   "enable_prompt_expansion": False},
        "note": "de-plastic pass, high denoise — expected fidelity breaking point"},
}
# Stacks run one config's output through another (complementary hypothesis:
# SeedVR2 restores structure, Z-Image fixes skin texture).
STACKS = {"seedvr2_then_zimage": ["seedvr2_x2_noise0", "zimage_s015"]}

REFINE_PROMPT = ("Enhance the photographic realism of this image. Fix artifacts in "
                 "hands, skin and fabric texture. Do not change the person's "
                 "identity, face, pose, clothing, or the background.")
SEED = 46

_lock = threading.Lock()
_spent = [0.0]


def _fal_image(endpoint, args):
    import fal_client
    res = fal_client.subscribe(endpoint, arguments=args)
    out = (res.get("images") or [res.get("image", {})])[0]
    import requests
    return Image.open(io.BytesIO(requests.get(out["url"]).content)).convert("RGB")


def _upload(path):
    import fal_client
    return fal_client.upload_file(path)


def before_set():
    """BEFORE images = the editing base's outputs already on disk."""
    import glob
    rows = []
    for d in sorted(glob.glob(os.path.join(RUNS, f"*_{BEFORE_ARM}_*"))):
        rc = json.load(open(os.path.join(d, "run_config.json")))
        rows.append({"pair": rc["pair"], "stage": rc["stage"],
                     "path": os.path.join(d, "result.png")})
    return rows


# -- generation --------------------------------------------------------------
def generate(names):
    os.makedirs(AUX, exist_ok=True)
    befores = before_set()
    if not befores:
        sys.exit(f"no {BEFORE_ARM} outputs found in {RUNS} — run the editing arm first")
    todo = [(n, b) for n in names for b in befores
            if not os.path.exists(os.path.join(AUX, f"{n}__{b['pair']}.png"))]
    est = sum(CONFIGS[n]["est_usd"] if n in CONFIGS
              else sum(CONFIGS[s]["est_usd"] for s in STACKS[n]) for n, _ in todo)
    print(f"{len(todo)} generations over {len(befores)} BEFORE images — est ${est:.2f}")
    if est > BUDGET_USD:
        sys.exit(f"estimate exceeds ${BUDGET_USD:.2f} ceiling")

    urls = {b["path"]: _upload(b["path"]) for b in befores}

    def one(job):
        name, b = job
        chain = STACKS.get(name, [name])
        url, img = urls[b["path"]], None
        try:
            for step in chain:
                cfg = CONFIGS[step]
                img = _fal_image(cfg["endpoint"], cfg["args"](url, SEED))
                if step is not chain[-1]:      # upload intermediate for the next step
                    tmp = os.path.join(AUX, f"_tmp_{name}_{b['pair']}.png")
                    img.save(tmp)
                    url = _upload(tmp)
                    os.remove(tmp)
                with _lock:
                    _spent[0] += cfg["est_usd"]
        except Exception as e:
            print(f"  FAIL {name} {b['pair']}: {str(e)[:140]}")
            return
        out = os.path.join(AUX, f"{name}__{b['pair']}.png")
        img.save(out)
        json.dump({"config": name, "pair": b["pair"], "chain": chain,
                   "before": os.path.relpath(b["path"], RUNS),
                   "native_size": img.size, "seed": SEED},
                  open(out.replace(".png", ".json"), "w"), indent=2)
        print(f"  ok {name} {b['pair']} {img.size}")

    with ThreadPoolExecutor(max_workers=6) as ex:
        list(ex.map(one, todo))
    print(f"generation done — est ${_spent[0]:.2f}")


# -- deterministic scoring ---------------------------------------------------
def _hf_energy(img):
    """High-frequency energy: detects both loss (smoothing) and inflation
    (oversharpening) of garment print detail."""
    import cv2
    g = cv2.cvtColor(np.array(img.convert("RGB")), cv2.COLOR_RGB2GRAY)
    return float(cv2.Laplacian(g, cv2.CV_64F).var())


def _ssim(a, b):
    import cv2
    ga = cv2.cvtColor(np.array(a.convert("RGB")), cv2.COLOR_RGB2GRAY).astype(np.float64)
    gb = cv2.cvtColor(np.array(b.convert("RGB").resize(a.size)),
                      cv2.COLOR_RGB2GRAY).astype(np.float64)
    C1, C2 = (0.01 * 255) ** 2, (0.03 * 255) ** 2
    mu_a = cv2.GaussianBlur(ga, (11, 11), 1.5)
    mu_b = cv2.GaussianBlur(gb, (11, 11), 1.5)
    sa = cv2.GaussianBlur(ga * ga, (11, 11), 1.5) - mu_a ** 2
    sb = cv2.GaussianBlur(gb * gb, (11, 11), 1.5) - mu_b ** 2
    sab = cv2.GaussianBlur(ga * gb, (11, 11), 1.5) - mu_a * mu_b
    s = (((2 * mu_a * mu_b + C1) * (2 * sab + C2)) /
         ((mu_a ** 2 + mu_b ** 2 + C1) * (sa + sb + C2)))
    return float(s.mean())


def score_all():
    rows = []
    import glob
    for f in sorted(glob.glob(os.path.join(AUX, "*.png"))):
        meta = json.load(open(f.replace(".png", ".json")))
        before = Image.open(os.path.join(RUNS, meta["before"])).convert("RGB")
        after_native = Image.open(f).convert("RGB")
        # compare at matched size: an aux model may legitimately upscale
        after = after_native.resize(before.size, Image.LANCZOS)
        tb, ta = M._torso_crop(before), M._torso_crop(after)
        hb, ha = _hf_energy(tb), _hf_energy(ta)
        rows.append({
            "config": meta["config"], "pair": meta["pair"],
            "native_w": meta["native_size"][0], "native_h": meta["native_size"][1],
            # fidelity preservation (reference = the aux model's own input)
            "id_preserve": M.identity_cosine(before, after),
            "garment_preserve": float(np.dot(M._embed(tb), M._embed(ta))),
            "hf_ratio": round(ha / hb, 3) if hb else None,   # 1.0 = detail unchanged
            "content_ssim": round(_ssim(before, after), 4),
            # realism proxy (VLM is authoritative for this axis)
            "sharpness_delta": round(_hf_energy(after) - _hf_energy(before), 1),
        })
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(RUNS, "aux_metrics.csv"), index=False)
    print(f"deterministic: scored {len(df)} outputs -> aux_metrics.csv")
    return df


# -- pairwise VLM judge ------------------------------------------------------
AUX_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "required": ["artifact_fix", "no_new_artifacts", "smoothness", "photo_real",
                 "garment_untouched", "identity_untouched", "note"],
    "properties": {k: {"type": "integer", "minimum": 1, "maximum": 5} for k in
                   ("artifact_fix", "no_new_artifacts", "smoothness", "photo_real",
                    "garment_untouched", "identity_untouched")}}
AUX_SCHEMA["properties"]["note"] = {"type": "string", "maxLength": 300}

AUX_PROMPT = """You are grading an image post-processing step, blind to which model produced it.
IMAGE 1 = BEFORE. IMAGE 2 = AFTER the processing step.
The step is only allowed to improve realism. It must NOT change content.

Score each 1-5 (5 best), strictly:
- artifact_fix: were artifacts present in BEFORE (bad hands, seams, warped fabric) repaired in AFTER? 3 = no change.
- no_new_artifacts: 5 = AFTER introduces zero new non-logical items; 1 = obvious new artifacts.
- smoothness: 5 = natural skin and fabric; 1 = plastic, waxy, over-smoothed or mushy.
- photo_real: 5 = reads as a real photograph (lighting, grain, shadows, materials).
- garment_untouched: 5 = garment color, pattern and print identical to BEFORE; 1 = clearly altered.
- identity_untouched: 5 = face, hair and body identical to BEFORE; 1 = a different-looking person.
note: one sentence on the most important difference.

Reply with ONLY a JSON object with exactly these keys:
artifact_fix, no_new_artifacts, smoothness, photo_real, garment_untouched, identity_untouched, note."""


def _b64(img):
    im = img.copy(); im.thumbnail((768, 768))
    buf = io.BytesIO(); im.convert("RGB").save(buf, "JPEG", quality=90)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def judge_one(before, after, attempts=3):
    from openai import OpenAI
    import jsonschema
    msg, client = AUX_PROMPT, OpenAI()
    for _ in range(attempts):
        r = client.responses.create(model=JUDGE_MODEL, input=[{"role": "user", "content": [
            {"type": "input_text", "text": msg},
            {"type": "input_image", "image_url": _b64(before)},
            {"type": "input_image", "image_url": _b64(after)}]}])
        txt = r.output_text
        try:
            obj = json.loads(txt[txt.index("{"):txt.rindex("}") + 1])
            jsonschema.validate(obj, AUX_SCHEMA)
            return obj
        except Exception as e:
            msg = f"{AUX_PROMPT}\n\nYour previous reply was invalid ({str(e)[:120]}). Reply with valid JSON only."
    return None


def judge_all():
    import glob
    jobs = []
    for f in sorted(glob.glob(os.path.join(AUX, "*.png"))):
        meta = json.load(open(f.replace(".png", ".json")))
        jobs.append((meta, os.path.join(RUNS, meta["before"]), f))
    print(f"VLM: judging {len(jobs)} before/after pairs on {JUDGE_MODEL}")

    def one(job):
        meta, bp, ap = job
        before = Image.open(bp).convert("RGB")
        after = Image.open(ap).convert("RGB").resize(before.size, Image.LANCZOS)
        v = judge_one(before, after)
        row = {"config": meta["config"], "pair": meta["pair"]}
        row.update(v or {k: None for k in AUX_SCHEMA["properties"]})
        return row

    with ThreadPoolExecutor(max_workers=6) as ex:
        rows = list(ex.map(one, jobs))
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(RUNS, "aux_vlm.csv"), index=False)
    print(f"VLM: {df['photo_real'].notna().sum()}/{len(df)} scored -> aux_vlm.csv")
    return df


# -- leaderboard + page ------------------------------------------------------
REALISM = ["artifact_fix", "no_new_artifacts", "smoothness", "photo_real"]
FIDELITY = ["garment_untouched", "identity_untouched"]
FIDELITY_GATE = 4.5      # SCORING_CRITERIA.md section 4


def leaderboard():
    d = pd.read_csv(os.path.join(RUNS, "aux_metrics.csv"))
    v = pd.read_csv(os.path.join(RUNS, "aux_vlm.csv"))
    v["realism"] = v[REALISM].mean(axis=1)
    v["fidelity"] = v[FIDELITY].mean(axis=1)
    b = (v.groupby("config")[REALISM + FIDELITY + ["realism", "fidelity"]].mean()
         .join(d.groupby("config")[["id_preserve", "garment_preserve", "hf_ratio",
                                    "content_ssim"]].mean()).round(3))
    b["passes_gate"] = b.fidelity >= FIDELITY_GATE
    return b.sort_values(["passes_gate", "realism"], ascending=[False, False]), d, v


def html():
    """Page = leaderboard + a large-image viewer. Arrow keys: left/right step
    through BEFORE then every config for the current pair; up/down change pair."""
    b, d, v = leaderboard()
    import glob
    sets = []
    for pair in sorted(d.pair.unique()):
        before_rel = json.load(open(glob.glob(os.path.join(AUX, f"*__{pair}.json"))[0]))["before"]
        bimg = Image.open(os.path.join(RUNS, before_rel))
        items = [{"label": f"BEFORE — {BEFORE_ARM}", "src": f"{RUNS_REL}/{before_rel}", "sub": "the aux model's input",
                  "size": f"{bimg.width}x{bimg.height}", "gate": None}]
        for cfg in b.index:
            f = os.path.join(AUX, f"{cfg}__{pair}.png")
            if not os.path.exists(f):
                continue
            dm = d[(d.config == cfg) & (d.pair == pair)]
            vm = v[(v.config == cfg) & (v.pair == pair)]
            sub = []
            if len(vm):
                sub.append(f"realism {vm[REALISM].mean(axis=1).iloc[0]:.2f}")
                sub.append(f"fidelity {vm[FIDELITY].mean(axis=1).iloc[0]:.2f}")
            if len(dm):
                sub += [f"id {dm.id_preserve.iloc[0]:.3f}",
                        f"garment {dm.garment_preserve.iloc[0]:.3f}",
                        f"hf {dm.hf_ratio.iloc[0]}"]
            items.append({"label": cfg, "src": f"{RUNS_REL}/aux/{os.path.basename(f)}",
                          "sub": " · ".join(sub),
                          "size": f"{int(dm.native_w.iloc[0])}x{int(dm.native_h.iloc[0])}" if len(dm) else "",
                          "gate": bool(b.loc[cfg, "passes_gate"])})
        sets.append({"pair": pair, "items": items})

    rows = "\n".join(
        f'<tr class="{"win" if r.passes_gate else "fail"}"><td class="n">{i}</td>'
        f"<td>{r.realism:.2f}</td><td>{r.fidelity:.2f}</td><td>{r.artifact_fix:.2f}</td>"
        f"<td>{r.no_new_artifacts:.2f}</td><td>{r.smoothness:.2f}</td><td>{r.photo_real:.2f}</td>"
        f"<td>{r.garment_untouched:.2f}</td><td>{r.identity_untouched:.2f}</td>"
        f"<td>{r.id_preserve:.3f}</td><td>{r.garment_preserve:.3f}</td>"
        f"<td>{r.hf_ratio:.2f}</td><td>{r.content_ssim:.3f}</td>"
        f'<td>{"PASS" if r.passes_gate else "FAIL"}</td></tr>'
        for i, r in b.iterrows())

    page = f"""<!doctype html><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Auxiliary Realism Models — Screen</title><style>
:root{{--bg:#14141d;--card:#1b1b26;--card2:#20202c;--line:#2b2b3a;--ink:#f3f3f7;
--body:#aab0be;--mut:#868da0;--acc:#928af5;--acc2:#b7b1fa;--ok:rgba(90,200,140,.14);
--bad:rgba(230,110,110,.12);--okb:rgba(90,200,140,.65);--badb:rgba(230,110,110,.6)}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--body);
font:15px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}}
.wrap{{max-width:1600px;margin:0 auto;padding:30px 28px 60px}}
h1{{font-size:29px;margin:2px 0 6px;color:var(--ink);font-weight:700;letter-spacing:-.4px}}
h2{{font-size:19px;margin:34px 0 8px;color:var(--ink);font-weight:700}}
.kick{{color:var(--mut);font-size:13.5px}}p{{max-width:980px}}b{{color:var(--ink)}}
.mut{{color:var(--mut);font-size:12.5px}}
table{{border-collapse:collapse;margin:10px 0;width:100%;font-variant-numeric:tabular-nums}}
th,td{{border-bottom:1px solid var(--line);padding:6px 9px;font-size:12.5px;text-align:right}}
th{{color:var(--mut);font-weight:600;text-transform:uppercase;font-size:10.5px;letter-spacing:.5px}}
td.n,th:first-child{{text-align:left}}td.n{{color:var(--ink);font-weight:600;white-space:nowrap}}
tr.win td{{background:var(--ok)}}tr.fail td{{background:var(--bad)}}
.tw{{overflow-x:auto}}
/* viewer */
#v{{margin:14px 0 0;background:var(--card);border:1px solid var(--line);border-radius:12px;
padding:14px 18px 18px;position:sticky;top:0;z-index:5}}
.vbar{{display:flex;gap:14px;align-items:baseline;flex-wrap:wrap;margin-bottom:10px}}
.vlabel{{font-size:20px;font-weight:700;color:var(--ink);letter-spacing:-.2px}}
.vlabel.before{{color:var(--acc2)}}
.pill{{font-size:10.5px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;
padding:2px 8px;border-radius:99px}}
.pill.pass{{background:var(--ok);color:#7fe3ac;border:1px solid var(--okb)}}
.pill.fail{{background:var(--bad);color:#ff9d9d;border:1px solid var(--badb)}}
.vsub{{color:var(--mut);font-size:13px;font-variant-numeric:tabular-nums}}
.vpos{{margin-left:auto;color:var(--mut);font-size:12.5px;font-family:ui-monospace,Menlo,monospace}}
#stage{{background:#0d0d14;border-radius:10px;display:flex;align-items:center;
justify-content:center;overflow:auto;height:74vh;min-height:420px}}
#stage img{{display:block;max-width:100%;max-height:74vh;object-fit:contain;cursor:zoom-in}}
#stage.zoom{{align-items:flex-start;justify-content:flex-start}}
#stage.zoom img{{max-width:none;max-height:none;cursor:zoom-out}}
.keys{{margin-top:10px;color:var(--mut);font-size:12.5px}}
kbd{{background:var(--card2);border:1px solid var(--line);border-bottom-width:2px;
border-radius:4px;padding:1px 6px;font-size:11.5px;color:var(--body)}}
.strip{{display:flex;gap:8px;overflow-x:auto;margin-top:12px;padding-bottom:4px}}
.strip figure{{margin:0;flex:0 0 auto;width:104px;text-align:center;cursor:pointer;opacity:.5}}
.strip figure.on{{opacity:1}}
.strip img{{width:100%;height:104px;object-fit:cover;border-radius:6px;
border:2px solid transparent;background:var(--card2);display:block}}
.strip figure.on img{{border-color:var(--acc)}}
.strip figure.pass img{{border-color:var(--okb)}}.strip figure.fail img{{border-color:var(--badb)}}
.strip figure.on.pass img,.strip figure.on.fail img{{border-color:var(--acc)}}
.strip figcaption{{font-size:10px;color:var(--mut);margin-top:4px;line-height:1.3;
overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
.pairs{{display:flex;flex-wrap:wrap;gap:8px;margin-top:12px}}
.pairs button{{border:1px solid var(--line);background:var(--card2);color:var(--body);
border-radius:6px;padding:5px 12px;font-size:12.5px;cursor:pointer;
font-family:ui-monospace,Menlo,monospace}}
.pairs button.on{{background:var(--acc);color:#14141d;border-color:var(--acc);font-weight:700}}
footer{{margin:40px 0 8px;padding-top:14px;border-top:1px solid var(--line);
color:var(--mut);font-size:12.5px}}
</style><div class="wrap">
<div class="kick">Virtual try-on V2 — auxiliary model screen</div>
<h1>Single-Image Realism Models</h1>
<div id="v">
<div class="vbar"><span class="vlabel" id="vl"></span><span id="vp"></span>
<span class="vsub" id="vs"></span><span class="vpos" id="vpos"></span></div>
<div id="stage"><img id="vi"></div>
<div class="keys"><kbd>&larr;</kbd><kbd>&rarr;</kbd> step through this set &middot;
<kbd>&uarr;</kbd><kbd>&darr;</kbd> previous / next set &middot;
<kbd>B</kbd> hold to flip back to BEFORE &middot; <kbd>Z</kbd> or click to zoom 1:1 &middot;
<kbd>O</kbd> open the file full size</div>
<div class="strip" id="strip"></div>
<div class="pairs" id="pairs"></div>
</div>
<p>Auxiliary models take <b>one image</b> and may only improve realism &mdash; changing
content is a failure. Every metric compares each output against <b>its own input</b>
(a FASHN v1.5 try-on result), per <code>prd/v2/SCORING_CRITERIA.md</code>. Selection =
highest realism among configs clearing the fidelity gate (VLM fidelity &ge;
{FIDELITY_GATE}). Configs rank individually because fidelity preservation depends on
strength/noise settings, not just on the model.</p>
<h2>Leaderboard</h2>
<div class="tw"><table>
<tr><th>config</th><th>realism</th><th>fidelity</th><th>artifact fix</th><th>no new art.</th>
<th>smooth</th><th>photo real</th><th>garment untouched</th><th>identity untouched</th>
<th>id cos</th><th>garment cos</th><th>hf ratio</th><th>ssim</th><th>gate</th></tr>
{rows}</table></div>
<p class="mut">VLM criteria 1&ndash;5 (blind gpt-5.5, BEFORE/AFTER pairwise).
Deterministic: id cos = AuraFace input&harr;output; garment cos = FashionSigLIP on the
torso crop; <b>hf ratio</b> = high-frequency energy after/before on the garment
(1.00 = detail untouched, &gt;1 sharper, &lt;1 smoothed) &mdash; a review trigger, not a
pass/fail; ssim = global content preservation. Metrics are computed at matched
resolution; upscaler outputs keep their native size on disk.</p>
<footer>Generated by v2/build/aux_harness.py from aux_metrics.csv and aux_vlm.csv.
Images live in v2/runs/aux/; open from v2/artifacts/.</footer></div>
<script>
const SETS={json.dumps(sets)};
let S=0,I=0,ZOOM=false,PEEK=false;
const el=id=>document.getElementById(id);
const strip=el("strip"),pairs=el("pairs");
SETS.forEach((s,i)=>{{const b=document.createElement("button");b.textContent=s.pair;
b.onclick=()=>{{S=i;I=0;build();render()}};pairs.appendChild(b)}});
function build(){{strip.innerHTML="";SETS[S].items.forEach((it,i)=>{{
const f=document.createElement("figure");
f.className=(it.gate===true?"pass":it.gate===false?"fail":"");
f.innerHTML='<img src="'+it.src+'"><figcaption>'+(i===0?"BEFORE":it.label)+'</figcaption>';
f.onclick=()=>{{I=i;render()}};strip.appendChild(f)}})}}
function render(){{const set=SETS[S];const it=set.items[PEEK?0:I];
el("vi").src=it.src;
el("vl").textContent=it.label;el("vl").className="vlabel"+(I===0||PEEK?" before":"");
el("vs").textContent=it.sub+(it.size?"  ·  "+it.size:"");
el("vp").innerHTML=it.gate===true?'<span class="pill pass">gate pass</span>':
it.gate===false?'<span class="pill fail">gate fail</span>':"";
el("vpos").textContent=set.pair+"   "+(I+1)+"/"+set.items.length+
"   set "+(S+1)+"/"+SETS.length+(PEEK?"   [BEFORE]":"");
[...strip.children].forEach((c,i)=>c.classList.toggle("on",i===I));
[...pairs.children].forEach((c,i)=>c.classList.toggle("on",i===S));
const nx=SETS[(S+1)%SETS.length];nx.items.forEach(x=>{{(new Image()).src=x.src}});}}
el("stage").onclick=()=>{{ZOOM=!ZOOM;el("stage").classList.toggle("zoom",ZOOM)}};
document.addEventListener("keydown",e=>{{const n=SETS[S].items.length;
if(e.key==="ArrowRight"){{I=(I+1)%n;render();e.preventDefault()}}
else if(e.key==="ArrowLeft"){{I=(I+n-1)%n;render();e.preventDefault()}}
else if(e.key==="ArrowDown"){{S=(S+1)%SETS.length;I=0;build();render();e.preventDefault()}}
else if(e.key==="ArrowUp"){{S=(S+SETS.length-1)%SETS.length;I=0;build();render();e.preventDefault()}}
else if(e.key==="b"||e.key==="B"){{if(!PEEK){{PEEK=true;render()}}}}
else if(e.key==="z"||e.key==="Z"){{ZOOM=!ZOOM;el("stage").classList.toggle("zoom",ZOOM)}}
else if(e.key==="o"||e.key==="O"){{window.open(SETS[S].items[I].src,"_blank")}}}});
document.addEventListener("keyup",e=>{{if((e.key==="b"||e.key==="B")&&PEEK){{PEEK=false;render()}}}});
build();render();
</script>"""
    os.makedirs(ART, exist_ok=True)
    out = os.path.join(ART, "v21_aux_screen.html")
    open(out, "w").write(page)
    print(f"wrote {out} ({len(page)//1024}KB, {len(sets)} sets x {len(sets[0]['items'])} images)")
    return b


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--generate", action="store_true", help="paid: run aux configs")
    ap.add_argument("--configs", default="all")
    ap.add_argument("--score", action="store_true", help="free: deterministic metrics")
    ap.add_argument("--judge", action="store_true", help="paid: pairwise VLM")
    ap.add_argument("--html", action="store_true")
    a = ap.parse_args()
    names = (list(CONFIGS) + list(STACKS)) if a.configs == "all" else a.configs.split(",")
    if a.generate:
        generate(names)
    if a.score:
        score_all()
    if a.judge:
        judge_all()
    if a.html:
        print(html().to_string())
