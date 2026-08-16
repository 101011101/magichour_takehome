# Auxiliary models, two batches — how far do they get, and what do they cost?
#
#   batch "original" : the REAL photos from Testset2 (person inputs).
#                      A realism pass on an undamaged photo should be a NO-OP.
#                      Whatever it changes here is damage the model does
#                      regardless of input quality — the floor.
#   batch "klein"    : klein_4b_edit outputs for the same five subjects — the
#                      actual deployed case (editing base decided in V2.1).
#
# Same subjects in both batches, so any difference is attributable to
# "real photo vs generated image", not to different content.
# Metrics compare each output against ITS OWN INPUT (prd/v2/SCORING_CRITERIA.md).
#
# Usage: python v2/build/aux_batch.py --generate --score --judge --html
import argparse, base64, io, json, os, sys, threading
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pandas as pd
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import metrics_v2 as M
from aux_harness import (CONFIGS, STACKS, REALISM, FIDELITY, FIDELITY_GATE,
                         AUX_SCHEMA, AUX_PROMPT, _hf_energy, _ssim, judge_one)

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
TS2 = os.path.join(REPO, "v2", "runs", "ts2")
OUTDIR = os.path.join(REPO, "v2", "runs", "aux_batches")
ART = os.path.join(REPO, "v2", "artifacts")
BUDGET_USD = 3.00
SEED = 46

# five distinct subjects spanning the pair kinds; klein outputs exist for all
PAIRS = ["ts2_01", "ts2_05", "ts2_07", "ts2_12", "ts2_13"]
# the known-bad low-strength configs are dropped; s035 already proved the
# breaking point, s015 already failed the gate
USE = ["seedvr2_x2_noise0", "seedvr2_x2_noise01", "zimage_s025", "seedvr2_then_zimage"]

BATCHES = {
    "original": {"label": "real photo (Testset2 person input)",
                 "why": "an undamaged photo — a realism pass should change nothing"},
    "klein":    {"label": "klein_4b_edit output",
                 "why": "the deployed case: repair a generated try-on"},
}

_lock = threading.Lock()
_spent = [0.0]


def before_path(batch, pair):
    m = json.load(open(os.path.join(TS2, "outputs", f"klein_4b_edit__{pair}.json")))
    if batch == "klein":
        return os.path.join(TS2, "outputs", f"klein_4b_edit__{pair}.png")
    base = os.path.splitext(os.path.basename(m["person"]))[0] + ".jpg"
    return os.path.join(TS2, "inputs", base)


def generate():
    import fal_client, requests
    os.makedirs(OUTDIR, exist_ok=True)
    jobs = [(b, p, c) for b in BATCHES for p in PAIRS for c in USE
            if not os.path.exists(os.path.join(OUTDIR, f"{b}__{c}__{p}.png"))]
    est = sum(CONFIGS[c]["est_usd"] if c in CONFIGS
              else sum(CONFIGS[s]["est_usd"] for s in STACKS[c]) for _, _, c in jobs)
    print(f"{len(jobs)} generations ({len(BATCHES)} batches x {len(PAIRS)} images "
          f"x {len(USE)} configs) — est ${est:.2f}")
    if est > BUDGET_USD:
        sys.exit(f"estimate exceeds ${BUDGET_USD:.2f}")

    cache = {}
    def url(path):
        with _lock:
            if path not in cache:
                cache[path] = fal_client.upload_file(path)
        return cache[path]

    def run_cfg(name, u):
        cfg = CONFIGS[name]
        res = fal_client.subscribe(cfg["endpoint"], arguments=cfg["args"](u, SEED))
        out = (res.get("images") or [res.get("image", {})])[0]
        with _lock:
            _spent[0] += cfg["est_usd"]
        return Image.open(io.BytesIO(requests.get(out["url"]).content)).convert("RGB")

    def one(job):
        batch, pair, name = job
        src = before_path(batch, pair)
        try:
            u, img = url(src), None
            for step in STACKS.get(name, [name]):
                img = run_cfg(step, u)
                if step != STACKS.get(name, [name])[-1]:
                    tmp = os.path.join(OUTDIR, f"_tmp_{batch}_{name}_{pair}.png")
                    img.save(tmp); u = fal_client.upload_file(tmp); os.remove(tmp)
        except Exception as e:
            print(f"  FAIL {batch}/{name}/{pair}: {str(e)[:130]}")
            return
        stem = os.path.join(OUTDIR, f"{batch}__{name}__{pair}")
        img.save(stem + ".png")
        json.dump({"batch": batch, "config": name, "pair": pair,
                   "before": os.path.relpath(src, REPO), "size": img.size, "seed": SEED},
                  open(stem + ".json", "w"), indent=2)
        print(f"  ok {batch}/{name}/{pair} {img.size}")

    with ThreadPoolExecutor(max_workers=6) as ex:
        list(ex.map(one, jobs))
    print(f"done — est ${_spent[0]:.2f}")


def score_all():
    import glob
    rows = []
    for f in sorted(glob.glob(os.path.join(OUTDIR, "*.png"))):
        m = json.load(open(f.replace(".png", ".json")))
        before = Image.open(os.path.join(REPO, m["before"])).convert("RGB")
        after = Image.open(f).convert("RGB").resize(before.size, Image.LANCZOS)
        tb, ta = M._torso_crop(before), M._torso_crop(after)
        hb = _hf_energy(tb)
        rows.append({"batch": m["batch"], "config": m["config"], "pair": m["pair"],
                     "id_preserve": M.identity_cosine(before, after),
                     "garment_preserve": float(np.dot(M._embed(tb), M._embed(ta))),
                     "hf_ratio": round(_hf_energy(ta) / hb, 3) if hb else None,
                     "content_ssim": round(_ssim(before, after), 4)})
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(OUTDIR, "metrics.csv"), index=False)
    print(f"scored {len(df)} outputs")
    print(df.groupby(["batch", "config"])[["id_preserve", "content_ssim", "hf_ratio"]]
          .mean().round(3).to_string())
    return df


def judge_all():
    import glob
    jobs = [(json.load(open(f.replace(".png", ".json"))), f)
            for f in sorted(glob.glob(os.path.join(OUTDIR, "*.png")))]
    print(f"VLM: judging {len(jobs)} before/after pairs")

    def one(job):
        m, f = job
        before = Image.open(os.path.join(REPO, m["before"])).convert("RGB")
        after = Image.open(f).convert("RGB").resize(before.size, Image.LANCZOS)
        v = judge_one(before, after)
        return {"batch": m["batch"], "config": m["config"], "pair": m["pair"],
                **(v or {k: None for k in AUX_SCHEMA["properties"]})}

    with ThreadPoolExecutor(max_workers=6) as ex:
        rows = list(ex.map(one, jobs))
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(OUTDIR, "vlm.csv"), index=False)
    print(f"VLM: {df['photo_real'].notna().sum()}/{len(df)} scored")
    return df


def boards():
    d = pd.read_csv(os.path.join(OUTDIR, "metrics.csv"))
    v = pd.read_csv(os.path.join(OUTDIR, "vlm.csv"))
    v["realism"] = v[REALISM].mean(axis=1)
    v["fidelity"] = v[FIDELITY].mean(axis=1)
    b = (v.groupby(["batch", "config"])[REALISM + FIDELITY + ["realism", "fidelity"]].mean()
         .join(d.groupby(["batch", "config"])[["id_preserve", "garment_preserve",
                                               "hf_ratio", "content_ssim"]].mean()).round(3))
    b["gate"] = b.fidelity >= FIDELITY_GATE
    return b.sort_values(["batch", "realism"], ascending=[True, False]), d, v


def html():
    b, d, v = boards()
    REL = "../runs"
    sets = []
    for batch in BATCHES:
        for pair in PAIRS:
            js = os.path.join(OUTDIR, f"{batch}__{USE[0]}__{pair}.json")
            if not os.path.exists(js):
                continue
            meta = json.load(open(js))
            # meta["before"] is repo-relative; the page sits in v2/artifacts/
            items = []
            if batch == "klein":
                # context: the real photo klein started from, so the chain reads
                # source photo -> klein try-on -> auxiliary repair
                src0 = os.path.relpath(before_path("original", pair), REPO)
                items.append({"label": "ORIGINAL PHOTO — klein's input",
                              "src": f"../../{src0}",
                              "sub": "context: the real photograph the try-on started from",
                              "gate": None})
            items.append({"label": f"BEFORE — {BATCHES[batch]['label']}",
                          "src": f"../../{meta['before']}", "sub": BATCHES[batch]["why"],
                          "gate": None})
            for cfg in [c for c in b.loc[batch].index if c in USE]:
                f = os.path.join(OUTDIR, f"{batch}__{cfg}__{pair}.png")
                if not os.path.exists(f):
                    continue
                dm = d[(d.batch == batch) & (d.config == cfg) & (d.pair == pair)]
                vm = v[(v.batch == batch) & (v.config == cfg) & (v.pair == pair)]
                sub = []
                if len(vm):
                    sub += [f"realism {vm[REALISM].mean(axis=1).iloc[0]:.2f}",
                            f"fidelity {vm[FIDELITY].mean(axis=1).iloc[0]:.2f}"]
                if len(dm):
                    sub += [f"id {dm.id_preserve.iloc[0]:.3f}",
                            f"ssim {dm.content_ssim.iloc[0]:.3f}",
                            f"hf {dm.hf_ratio.iloc[0]}"]
                items.append({"label": cfg, "src": f"{REL}/aux_batches/{os.path.basename(f)}",
                              "sub": " · ".join(sub),
                              "gate": bool(b.loc[(batch, cfg), "gate"])})
            sets.append({"pair": f"{batch} · {pair}", "items": items,
                         "before_i": 1 if batch == "klein" else 0})

    def rows_for(batch):
        sub = b.loc[batch]
        return "".join(
            f'<tr class="{"win" if r.gate else "fail"}"><td class="n">{i}</td>'
            f"<td>{r.realism:.2f}</td><td>{r.fidelity:.2f}</td>"
            f"<td>{r.artifact_fix:.2f}</td><td>{r.no_new_artifacts:.2f}</td>"
            f"<td>{r.smoothness:.2f}</td><td>{r.photo_real:.2f}</td>"
            f"<td>{r.garment_untouched:.2f}</td><td>{r.identity_untouched:.2f}</td>"
            f"<td>{r.id_preserve:.3f}</td><td>{r.content_ssim:.3f}</td>"
            f"<td>{r.hf_ratio:.2f}</td><td>{'PASS' if r.gate else 'FAIL'}</td></tr>"
            for i, r in sub.iterrows())

    hdr = ("<tr><th>config</th><th>realism</th><th>fidelity</th><th>artifact fix</th>"
           "<th>no new art.</th><th>smooth</th><th>photo real</th><th>garment untouched</th>"
           "<th>identity untouched</th><th>id cos</th><th>ssim</th><th>hf ratio</th>"
           "<th>gate</th></tr>")

    page = f"""<!doctype html><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Auxiliary Models — Two Batches</title><style>
:root{{--bg:#14141d;--card:#1b1b26;--card2:#20202c;--line:#2b2b3a;--ink:#f3f3f7;
--body:#aab0be;--mut:#868da0;--acc:#928af5;--acc2:#b7b1fa;--ok:rgba(90,200,140,.14);
--bad:rgba(230,110,110,.12);--okb:rgba(90,200,140,.65);--badb:rgba(230,110,110,.6)}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--body);
font:15px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}}
.wrap{{max-width:1600px;margin:0 auto;padding:30px 28px 60px}}
h1{{font-size:29px;margin:2px 0 6px;color:var(--ink);font-weight:700;letter-spacing:-.4px}}
h2{{font-size:19px;margin:34px 0 8px;color:var(--ink);font-weight:700}}
.kick{{color:var(--mut);font-size:13.5px}}p{{max-width:1000px}}b{{color:var(--ink)}}
.mut{{color:var(--mut);font-size:12.5px}}
table{{border-collapse:collapse;margin:10px 0;width:100%;font-variant-numeric:tabular-nums}}
th,td{{border-bottom:1px solid var(--line);padding:6px 9px;font-size:12.5px;text-align:right}}
th{{color:var(--mut);font-weight:600;text-transform:uppercase;font-size:10.5px;letter-spacing:.5px}}
td.n,th:first-child{{text-align:left}}td.n{{color:var(--ink);font-weight:600;white-space:nowrap}}
tr.win td{{background:var(--ok)}}tr.fail td{{background:var(--bad)}}
.tw{{overflow-x:auto}}
.meta{{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin:16px 0 4px}}
@media(max-width:1100px){{.meta{{grid-template-columns:1fr}}}}
.mcard{{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px 18px}}
.mh{{font-size:10.5px;font-weight:700;letter-spacing:.09em;text-transform:uppercase;
color:var(--acc);margin-bottom:6px}}
.mt{{font-size:17px;font-weight:700;color:var(--ink);margin-bottom:6px}}
.mp{{font-size:12.5px;color:var(--mut);margin:8px 0 0}}
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
.strip figure.fail img{{border-color:var(--badb)}}
.strip figcaption{{font-size:10px;color:var(--mut);margin-top:4px;line-height:1.3;
overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
.pairs{{display:flex;flex-wrap:wrap;gap:8px;margin-top:12px}}
.pairs button{{border:1px solid var(--line);background:var(--card2);color:var(--body);
border-radius:6px;padding:5px 12px;font-size:12px;cursor:pointer;
font-family:ui-monospace,Menlo,monospace}}
.pairs button.on{{background:var(--acc);color:#14141d;border-color:var(--acc);font-weight:700}}
footer{{margin:40px 0 8px;padding-top:14px;border-top:1px solid var(--line);
color:var(--mut);font-size:12.5px}}
</style><div class="wrap">
<div class="kick">Virtual try-on V2 — auxiliary models, two batches</div>
<h1>How Far Do the Realism Models Get?</h1>
<div class="meta">
<div class="mcard"><div class="mh">Batch A — control</div>
<div class="mt">original &mdash; real photos</div>
<p class="mp">The Testset2 <b>person inputs</b>: real photographs that need no
repair. A realism pass here should be a <b>no-op</b> &mdash; anything it changes is
damage the model inflicts regardless of input quality. This is the floor, and it is
the only way to tell "improved the image" apart from "rebuilt the image".</p></div>
<div class="mcard"><div class="mh">Batch B — the deployed case</div>
<div class="mt">klein &mdash; klein_4b_edit outputs</div>
<p class="mp">The same five subjects, but the try-on results from the chosen editing
base (V2.1). This is what the auxiliary stage will actually receive in production:
a generated image with the artifacts and plastic-skin tendencies the aux bucket
exists to repair.</p></div>
</div>
<div id="v">
<div class="vbar"><span class="vlabel" id="vl"></span><span id="vp"></span>
<span class="vsub" id="vs"></span><span class="vpos" id="vpos"></span></div>
<div id="stage"><img id="vi"></div>
<div class="keys"><kbd>&larr;</kbd><kbd>&rarr;</kbd> step through this set &middot;
<kbd>&uarr;</kbd><kbd>&darr;</kbd> next / previous set &middot;
<kbd>B</kbd> hold to flip back to BEFORE &middot; <kbd>Z</kbd> or click to zoom 1:1 &middot;
<kbd>O</kbd> open full size</div>
<div class="strip" id="strip"></div>
<div class="pairs" id="pairs"></div>
</div>
<h2>Batch A — original (real photos): what a pass costs when nothing needs fixing</h2>
<div class="tw"><table>{hdr}{rows_for('original')}</table></div>
<h2>Batch B — klein outputs: the deployed case</h2>
<div class="tw"><table>{hdr}{rows_for('klein')}</table></div>
<p class="mut">Every metric compares an output against <b>its own input</b>. VLM
criteria 1&ndash;5 (blind gpt-5.5, BEFORE/AFTER pairwise); gate = VLM fidelity
&ge; {FIDELITY_GATE}. id cos = AuraFace input&harr;output; ssim = global content
preservation; hf ratio = high-frequency energy after/before on the torso
(1.00 = untouched, &gt;1 sharper, &lt;1 smoothed) &mdash; a review trigger, not a
pass/fail. Outputs compared at matched resolution; upscalers keep native size on disk.</p>
<footer>Generated by v2/build/aux_batch.py from v2/runs/aux_batches/. Open from
v2/artifacts/.</footer></div>
<script>
const SETS={json.dumps(sets)};
let S=0,I=0,ZOOM=false,PEEK=false;
const el=id=>document.getElementById(id);
const strip=el("strip"),pairs=el("pairs");
SETS.forEach((s,i)=>{{const b=document.createElement("button");b.textContent=s.pair;
b.onclick=()=>{{S=i;I=0;build();render()}};pairs.appendChild(b)}});
function build(){{strip.innerHTML="";SETS[S].items.forEach((it,i)=>{{
const f=document.createElement("figure");f.className=(it.gate===false?"fail":"");
f.innerHTML='<img src="'+it.src+'"><figcaption>'+it.label+'</figcaption>';
f.onclick=()=>{{I=i;render()}};strip.appendChild(f)}})}}
function render(){{const set=SETS[S];const bi=set.before_i||0;\nconst it=set.items[PEEK?bi:I];
el("vi").src=it.src;
el("vl").textContent=it.label;el("vl").className="vlabel"+((I<=bi||PEEK)?" before":"");
el("vs").textContent=it.sub;
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
    out = os.path.join(ART, "v21_aux_batches.html")
    open(out, "w").write(page)
    print(f"wrote {out} ({len(page)//1024}KB, {len(sets)} sets)")
    print(b.to_string())


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--generate", action="store_true")
    ap.add_argument("--score", action="store_true")
    ap.add_argument("--judge", action="store_true")
    ap.add_argument("--html", action="store_true")
    a = ap.parse_args()
    if a.generate: generate()
    if a.score: score_all()
    if a.judge: judge_all()
    if a.html: html()
