# Generates v2/artifacts/v20_triage_v1set.html — V2 analog of v1/artifacts/compare.html.
# Reads v2/runs/cv_metrics.csv + composite run packages; images stay in v2/runs/
# and are referenced as ../runs/... from the artifacts folder.
import json, os, glob
import pandas as pd

RUNS = os.path.join(os.path.dirname(__file__), "..", "runs")
ART = os.path.join(os.path.dirname(__file__), "..", "artifacts")
# The page lives in v2/artifacts/ but the images stay in v2/runs/, so every run
# path is emitted relative to artifacts/. test_set/ is two levels up from both.
RUNS_REL = "../runs"
CV = pd.read_csv(os.path.join(RUNS, "cv_metrics.csv"))

W = {"garment_sim": 2.0, "identity_cos": 1.0, "pose_err": 1.0, "bg_psnr": 1.0}
A = {"garment_sim": (0.55, 0.85), "identity_cos": (0.42, 0.80),
     "pose_err": (0.25, 0.0), "bg_psnr": (12.0, 32.0)}

def det_score(row):
    num = den = 0.0
    for m, w in W.items():
        v = row[m]
        if pd.isna(v):
            continue
        lo, hi = A[m]
        num += w * min(1.0, max(0.0, (v - lo) / (hi - lo)))
        den += w
    return round(num / den, 3) if den else None

CV["det"] = CV.apply(det_score, axis=1)

GARMENT = {"g015": "Slip dress", "g022": "Tailored trousers", "g023": "Plaid mini skirt",
           "g006": "Graphic hoodie", "g019": "Puffer jacket", "g024": "Pleated midi skirt",
           "g004": "Fitted knit", "g011": "Bodycon midi dress", "g002": "Striped tee",
           "g001": "Logo tee", "g028": "Striped shirt", "g007": "Polka-dot blouse"}
LBL = {"qwen_2511": "Qwen 2511 (baseline)", "klein_4b_edit": "FLUX.2 klein 4B",
       "fashn_v15": "FASHN v1.5", "firered_edit": "FireRed v1.1",
       "composite_v2ow": "Composite (proposed)"}
RIGHT = ["qwen_2511", "klein_4b_edit", "fashn_v15", "firered_edit"]

def run_dir(stage, arm, pair):
    hits = glob.glob(os.path.join(RUNS, f"{stage}_{arm}_{pair}_s*"))
    return os.path.basename(hits[0]) if hits else None

def cvrow(stage, arm, pair):
    r = CV[(CV.stage == stage) & (CV.arm == arm) & (CV.pair == pair)]
    return r.iloc[0] if len(r) else None

data = []
for d in sorted(glob.glob(os.path.join(RUNS, "grid_composite_v2ow_*"))):
    pair = os.path.basename(d).split("_")[3]
    pid, gid = pair.split("x")
    meta = json.load(open(os.path.join(d, "run_config.json")))["pipeline_meta"]
    best = meta["candidates"][meta["shipped_candidate"]]
    r = cvrow("grid", "composite_v2ow", pair)
    comp = {"src": f"{RUNS_REL}/{os.path.basename(d)}/result.png",
            "det": None if r is None else r.det,
            "gate": None if best["cos_post_refine"] is None
                    else round(best["cos_post_refine"], 3),
            "paste": bool(best["paste_applied"] or best["repasted"]),
            "cands": len(meta["candidates"])}
    arms = {}
    for a in RIGHT:
        rd = run_dir("triage", a, pair)
        if rd:
            tr = cvrow("triage", a, pair)
            arms[a] = {"src": f"{RUNS_REL}/{rd}/result.png",
                       "det": None if tr is None else tr.det}
    data.append({"pair": pair, "garment": GARMENT.get(gid, gid),
                 "person": f"../../test_set/people/{pid}.jpg",
                 "garment_img": f"../../test_set/garments/{gid}.jpg",
                 "composite": comp, "arms": arms})

# boards for the tables
tri = (CV[CV.stage == "triage"].groupby("arm")
       .agg(garment_sim=("garment_sim", "mean"), identity_cos=("identity_cos", "mean"),
            pose_err=("pose_err", "mean"), bg_psnr=("bg_psnr", "mean"),
            score=("det", "mean")).round(3).sort_values("score", ascending=False))
cmpb = (CV[(CV.stage == "grid") & (CV.arm == "composite_v2ow")]
        [["garment_sim", "identity_cos", "pose_err", "bg_psnr", "det"]]
        .mean().round(3))

def board_rows(df):
    out = []
    for arm, r in df.iterrows():
        cls = ' class="win"' if arm == df.index[0] else ""
        out.append(f'<tr{cls}><td class="n">{LBL.get(arm, arm)}</td>'
                   + "".join(f"<td>{r[c]:.3f}</td>" for c in
                             ("garment_sim", "identity_cos", "pose_err"))
                   + f"<td>{r.bg_psnr:.1f}</td><td><b>{r.score:.3f}</b></td></tr>")
    return "\n".join(out)

html = f"""<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Output Comparison — V2 Open Weights</title><style>
:root{{--bg:#14141d;--card:#1b1b26;--card2:#20202c;--line:#2b2b3a;--ink:#f3f3f7;
--body:#aab0be;--mut:#868da0;--acc:#928af5;--acc2:#b7b1fa;--tint:rgba(146,138,245,.10)}}
*{{box-sizing:border-box}}html{{background:var(--bg)}}
body{{margin:0;background:var(--bg);color:var(--body);
font:15px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}}
.wrap{{max-width:1480px;margin:0 auto;padding:44px 32px 36px}}
h1{{font-size:31px;margin:2px 0 26px;color:var(--ink);font-weight:700;letter-spacing:-.4px}}
h2{{font-size:20px;margin:46px 0 12px;color:var(--ink);font-weight:700;letter-spacing:-.2px}}
.kick{{color:var(--mut);font-size:14px}}
p{{max-width:880px}}.mut{{color:var(--mut);font-size:13px}}b{{color:var(--ink)}}
.exec{{max-width:1000px}}.exec b.t{{font-size:16px}}
.exec ul{{margin:8px 0 0;padding-left:20px}}.exec li{{margin:7px 0;max-width:880px}}
.tw{{overflow-x:auto;max-width:920px}}
table{{border-collapse:collapse;margin:10px 0 6px;width:100%;font-variant-numeric:tabular-nums}}
th,td{{border-bottom:1px solid var(--line);padding:7px 10px;font-size:13px;text-align:right}}
th{{color:var(--mut);font-weight:600;text-transform:uppercase;font-size:11px;letter-spacing:.5px}}
td{{color:var(--body)}}td.n,th:first-child{{text-align:left}}
td.n{{color:var(--ink);font-weight:600;white-space:nowrap}}
tr.win td{{background:var(--tint)}}
#app{{margin-top:16px;background:var(--card);border:1px solid var(--line);border-radius:12px;padding:20px 24px 22px}}
.bar{{display:flex;gap:12px;align-items:baseline;flex-wrap:wrap;margin-bottom:12px}}
.bar b{{font-size:19px;color:var(--ink)}}
.chip{{color:var(--mut);font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:12.5px}}
kbd{{background:var(--card2);border:1px solid var(--line);border-bottom-width:2px;border-radius:4px;
padding:0 6px;font-size:11.5px;color:var(--body)}}
.tabsrow{{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin:0 0 16px;
padding:0 0 14px;border-bottom:1px solid var(--line)}}
.tabsrow .lbl{{color:var(--mut);font-size:13px;margin-right:6px}}
.tabsrow button,.pairs button{{border:1px solid var(--line);background:var(--card2);color:var(--body);
border-radius:6px;padding:5px 13px;font-size:13px;cursor:pointer}}
.tabsrow button.on,.pairs button.on{{background:var(--acc);color:#14141d;border-color:var(--acc);font-weight:700}}
.tabsrow button:disabled{{opacity:.35;cursor:default}}
.stage{{display:grid;grid-template-columns:200px 1fr 1fr;gap:16px;align-items:start}}
.slot,.gcol{{text-align:center}}
.ttl{{font-size:13.5px;font-weight:600;margin-bottom:8px;color:var(--body)}}
.gcol.ours .ttl{{color:var(--acc2)}}
.gcol img,.slot img{{width:100%;max-height:72vh;object-fit:contain;border-radius:8px;
background:var(--card2);cursor:zoom-in;display:block}}
.slot img{{max-height:34vh;margin-bottom:12px}}
.sc{{font-size:12.5px;color:var(--mut);margin-top:7px;font-variant-numeric:tabular-nums}}
.missing{{display:flex;align-items:center;justify-content:center;height:50vh;background:var(--card2);
border-radius:8px;color:var(--mut);font-size:13px;padding:20px;text-align:center}}
.pairs{{display:flex;flex-wrap:wrap;gap:8px;margin-top:16px}}
.pairs button{{font-size:12.5px;padding:5px 12px;white-space:nowrap}}
footer{{margin:44px 0 8px;padding-top:14px;border-top:1px solid var(--line);color:var(--mut);font-size:12.5px}}
a{{color:var(--acc2)}}
</style><div class="wrap">
<div class="kick">Virtual try-on V2 — open-weights arms, wave 1 (triage + composite)</div>
<h1>Output Comparison</h1>
<div class="exec"><b class="t">Where this stands</b>
<ul>
<li>Four open-weights arms triaged (4 pairs each): <b>klein 4B</b> and <b>FASHN v1.5</b>
advance; FireRed v1.1 eliminated; the Qwen 2511 baseline advances by rule.</li>
<li>The proposed <b>composite</b> (klein 4B &rarr; face paste-back &rarr; Z-Image refine
&rarr; AuraFace identity gate) has run on all 12 grid pairs: 10/12 passed the 0.55
identity gate; paste-back applied on 7, correctly refused on 4 head-covering garments.</li>
<li>Deterministic metrics are V2-upgraded: FashionSigLIP garment similarity + AuraFace
identity, fixed anchors recalibrated on V1 outputs. VLM judging and the grid/holdout
stages for the surviving single arms have not run yet &mdash; right-column comparisons
exist only on the four triage pairs.</li>
<li>Spend: $1.33 of the $10 ceiling (28/28 generations succeeded).</li>
</ul></div>
<h2>Triage board (deterministic, garment &times;2)</h2>
<div class="tw"><table><tr><th>arm</th><th>garment_sim</th><th>identity_cos</th>
<th>pose_err</th><th>bg_psnr</th><th>score</th></tr>
{board_rows(tri)}
<tr><td class="n">{LBL['composite_v2ow']} &middot; grid</td>
<td>{cmpb.garment_sim:.3f}</td><td>{cmpb.identity_cos:.3f}</td><td>{cmpb.pose_err:.3f}</td>
<td>{cmpb.bg_psnr:.1f}</td><td><b>{cmpb.det:.3f}</b></td></tr></table></div>
<p class="mut">Composite row is measured on the 12 grid pairs (different, harder set than
the 4 triage pairs) &mdash; directional until the survivors run the same grid.</p>
<div id="app">
<div class="bar"><b id="pairname"></b><span class="chip" id="pairid"></span>
<span class="chip">keys: <kbd>&larr;</kbd><kbd>&rarr;</kbd> arm &middot;
<kbd>&uarr;</kbd><kbd>&darr;</kbd> pair &middot; <kbd>1</kbd>&ndash;<kbd>4</kbd> jump &middot;
click any image to open full size</span></div>
<div class="tabsrow"><span class="lbl">Compare against:</span><span id="tabs"></span></div>
<div class="stage">
<div class="slot"><div class="ttl">person</div><a id="pl" target="_blank"><img id="pi"></a>
<div class="ttl">garment</div><a id="gl" target="_blank"><img id="gi"></a></div>
<div class="gcol ours"><div class="ttl">Composite (proposed)</div>
<a id="cl" target="_blank"><img id="ci"></a><div class="sc" id="cs"></div></div>
<div class="gcol"><div class="ttl" id="rt"></div><div id="rwrap"></div><div class="sc" id="rs"></div></div>
</div>
<div class="pairs" id="pairs"></div>
</div>
<footer>Generated by v2/build/make_compare.py from cv_metrics.csv and run packages in
v2/runs/. Deterministic score = fixed-anchor weighted composite (garment &times;2);
gate = AuraFace cosine of the shipped candidate. Images live in v2/runs/; open this file from v2/artifacts/.</footer>
</div><script>
const DATA={json.dumps(data)};
const RIGHT={json.dumps(RIGHT)};
const LBL={json.dumps(LBL)};let P=0,R=0;
const tabs=document.getElementById("tabs"),pairs=document.getElementById("pairs");
RIGHT.forEach((a,i)=>{{const b=document.createElement("button");b.textContent=(i+1)+". "+LBL[a];
b.onclick=()=>{{R=i;render()}};tabs.appendChild(b)}});
DATA.forEach((d,i)=>{{const b=document.createElement("button");b.textContent=d.garment;
b.onclick=()=>{{P=i;render()}};pairs.appendChild(b)}});
function compsc(c){{let s=["deterministic "+(c.det==null?"n/a":c.det.toFixed(3))];
s.push("gate "+(c.gate==null?"no face":c.gate.toFixed(3)));
s.push(c.paste?"face pasted":"paste skipped");
if(c.cands>1)s.push(c.cands+" candidates");return s.join(" · ")}}
function render(){{const d=DATA[P],ra=RIGHT[R],ro=d.arms[ra];
document.getElementById("pairname").textContent=d.garment;
document.getElementById("pairid").textContent=d.pair;
[["pi","pl",d.person],["gi","gl",d.garment_img],["ci","cl",d.composite.src]]
.forEach(([im,ln,src])=>{{document.getElementById(im).src=src;document.getElementById(ln).href=src}});
document.getElementById("cs").textContent=compsc(d.composite);
document.getElementById("rt").textContent=LBL[ra];
const w=document.getElementById("rwrap");
if(ro){{w.innerHTML='<a href="'+ro.src+'" target="_blank"><img src="'+ro.src+'"></a>';
document.getElementById("rs").textContent="deterministic "+(ro.det==null?"n/a":ro.det.toFixed(3))+" (triage)";}}
else{{w.innerHTML='<div class="missing">not generated yet — this arm has only run on the '+
'4 triage pairs; the grid stage for survivors is the next paid step</div>';
document.getElementById("rs").textContent="";}}
[...tabs.children].forEach((b,i)=>{{b.classList.toggle("on",i===R);
b.disabled=!DATA[P].arms[RIGHT[i]]}});
[...pairs.children].forEach((b,i)=>b.classList.toggle("on",i===P));}}
document.addEventListener("keydown",e=>{{
if(e.key==="ArrowRight"){{R=(R+1)%RIGHT.length;render();e.preventDefault()}}
else if(e.key==="ArrowLeft"){{R=(R+RIGHT.length-1)%RIGHT.length;render();e.preventDefault()}}
else if(e.key==="ArrowDown"){{P=(P+1)%DATA.length;render();e.preventDefault()}}
else if(e.key==="ArrowUp"){{P=(P+DATA.length-1)%DATA.length;render();e.preventDefault()}}
else if("1234".includes(e.key)){{R=parseInt(e.key)-1;render()}}}});
render();
</script>"""
os.makedirs(ART, exist_ok=True)
out = os.path.join(ART, "v20_triage_v1set.html")
open(out, "w").write(html)
print(f"wrote {out} ({len(html)//1024}KB, {len(data)} pairs)")
