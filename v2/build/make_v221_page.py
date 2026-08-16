# v2/artifacts/v221_klein_trial.html — did the crops change what klein produced?
# Each set: person, garment reference, then base and each cropped variant.
# One variable across a set — the garment reference; everything else is fixed.
import json, os
import pandas as pd
from PIL import Image

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
TS2 = os.path.join(REPO, "v2", "runs", "ts2")
V221 = os.path.join(REPO, "v2", "runs", "v221")
CROPS = os.path.join(REPO, "v2", "runs", "crop_screen")
ART = os.path.join(REPO, "v2", "artifacts")
REL = "../runs"

# C1 deliberately excluded — it isolates framing from background removal, which
# is not the question this page answers.
ORDER = ["base", "c2_bbox_nobg", "c31_no_face", "c32_keep_hair", "c4_clothes_only"]
LBL = {"base": "BASE — uncropped reference",
       "c2_bbox_nobg": "C2 — background white, wearer kept",
       "c31_no_face": "C3.1 — face AND hair removed",
       "c32_keep_hair": "C3.2 — face removed, HAIR KEPT",
       "c4_clothes_only": "C4 — clothes only, all skin removed"}
CROPSUF = {"c2_bbox_nobg": "c2_bbox_nobg", "c31_no_face": "c3_no_face",
           "c32_keep_hair": "c32_no_face_keep_hair", "c4_clothes_only": "c4_clothes_only"}
KIND = {"product": "garment only", "duo_lookbook": "garment + human (lookbook)",
        "duo_swap": "garment + human (swap)"}

mx = pd.read_csv(os.path.join(TS2, "matrix.csv")).set_index("id")
d = pd.read_csv(os.path.join(V221, "v221_metrics.csv"))


def stem(rel):
    return os.path.splitext(os.path.basename(rel))[0]


def out_for(v, pid):
    return (f"{REL}/ts2/outputs/klein_4b_edit__{pid}.png" if v == "base"
            else f"{REL}/v221/{v}__{pid}.png")


sets = []
for pid, r in mx.iterrows():
    items = [{"label": "PERSON (image 1)", "src": f"{REL}/ts2/inputs/{stem(r.person)}.jpg",
              "sub": KIND[r.kind], "tag": None},
             {"label": "GARMENT REF — uncropped", "src": f"{REL}/ts2/inputs/{stem(r.garment)}.jpg",
              "sub": f"target: {r.target}", "tag": None}]
    best = d[d.id == pid].sort_values("score", ascending=False)
    top = best.variant.iloc[0] if len(best) else None
    for v in ORDER:
        p = os.path.join(REPO, "v2", "runs", out_for(v, pid).replace(f"{REL}/", ""))
        if not os.path.exists(p):
            continue
        m = d[(d.variant == v) & (d.id == pid)]
        sub = []
        if len(m):
            sub = [f"det {m.score.iloc[0]:.3f}", f"garment {m.garment_sim.iloc[0]:.3f}",
                   f"id {m.identity_cos.iloc[0]:.3f}", f"bg {m.bg_psnr.iloc[0]:.1f}dB"]
        items.append({"label": LBL[v], "src": out_for(v, pid),
                      "sub": " · ".join(sub), "tag": (v == top) if top else None})
    sets.append({"pair": f"{pid} · {KIND[r.kind]}", "items": items, "before_i": 0})

ov = (d.groupby("variant")[["garment_sim", "identity_cos", "pose_err", "bg_psnr", "score"]]
      .mean().reindex(ORDER).round(3))
duo = (d[d.duo].groupby("variant")[["garment_sim", "score"]].mean().reindex(ORDER).round(3))
prod = (d[~d.duo].groupby("variant")[["garment_sim", "score"]].mean().reindex(ORDER).round(3))


def rows(df, cols):
    best = {c: df[c].max() for c in cols}
    out = ""
    for v in ORDER:
        if v not in df.index:
            continue
        cells = "".join(
            f"<td{' class=hi' if df.loc[v, c] == best[c] else ''}>{df.loc[v, c]:.3f}</td>"
            for c in cols)
        out += f"<tr{' class=base' if v == 'base' else ''}><td class='n'>{LBL[v]}</td>{cells}</tr>"
    return out


page = f"""<!doctype html><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>v2.2.1 — klein on cropped references</title><style>
:root{{--bg:#14141d;--card:#1b1b26;--card2:#20202c;--line:#2b2b3a;--ink:#f3f3f7;
--body:#aab0be;--mut:#868da0;--acc:#928af5;--acc2:#b7b1fa;--ok:rgba(90,200,140,.16);
--okb:rgba(90,200,140,.65)}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--body);
font:15px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}}
.wrap{{max-width:1600px;margin:0 auto;padding:30px 28px 60px}}
h1{{font-size:29px;margin:2px 0 6px;color:var(--ink);font-weight:700;letter-spacing:-.4px}}
h2{{font-size:19px;margin:34px 0 8px;color:var(--ink);font-weight:700}}
.kick{{color:var(--mut);font-size:13.5px}}p{{max-width:1000px}}b{{color:var(--ink)}}
.mut{{color:var(--mut);font-size:12.5px}}
table{{border-collapse:collapse;margin:10px 0;width:100%;font-variant-numeric:tabular-nums}}
th,td{{border-bottom:1px solid var(--line);padding:6px 10px;font-size:12.5px;text-align:right}}
th{{color:var(--mut);font-weight:600;text-transform:uppercase;font-size:10.5px;letter-spacing:.5px}}
td.n,th:first-child{{text-align:left}}td.n{{color:var(--ink);font-weight:600;white-space:nowrap}}
td.hi{{background:var(--ok);color:#bff0d4;font-weight:700}}
tr.base td{{color:var(--mut)}}tr.base td.n{{color:var(--body)}}
.tw{{overflow-x:auto}}
.mcard{{background:var(--card);border:1px solid var(--line);border-radius:12px;
padding:16px 18px;margin:16px 0}}
.mh{{font-size:10.5px;font-weight:700;letter-spacing:.09em;text-transform:uppercase;
color:var(--acc);margin-bottom:6px}}
#v{{margin:14px 0 0;background:var(--card);border:1px solid var(--line);border-radius:12px;
padding:14px 18px 18px;position:sticky;top:0;z-index:5}}
.vbar{{display:flex;gap:14px;align-items:baseline;flex-wrap:wrap;margin-bottom:10px}}
.vlabel{{font-size:20px;font-weight:700;color:var(--ink);letter-spacing:-.2px}}
.vlabel.inp{{color:var(--acc2)}}
.pill{{font-size:10.5px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;
padding:2px 8px;border-radius:99px;background:var(--ok);color:#7fe3ac;
border:1px solid var(--okb)}}
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
.strip figure.ref{{width:70px;opacity:.32}}
.strip figure.ref.on{{opacity:.9}}
.strip img{{width:100%;height:104px;object-fit:cover;border-radius:6px;
border:2px solid transparent;background:var(--card2);display:block}}
.strip figure.ref img{{height:70px}}
.strip figure.on img{{border-color:var(--acc)}}
.strip figure.win img{{border-color:var(--okb)}}
.strip figcaption{{font-size:9.5px;color:var(--mut);margin-top:4px;line-height:1.25;
overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
.pairs{{display:flex;flex-wrap:wrap;gap:8px;margin-top:12px}}
.pairs button{{border:1px solid var(--line);background:var(--card2);color:var(--body);
border-radius:6px;padding:5px 12px;font-size:12px;cursor:pointer;
font-family:ui-monospace,Menlo,monospace}}
.pairs button.on{{background:var(--acc);color:#14141d;border-color:var(--acc);font-weight:700}}
footer{{margin:40px 0 8px;padding-top:14px;border-top:1px solid var(--line);
color:var(--mut);font-size:12.5px}}
</style><div class="wrap">
<div class="kick">Virtual try-on v2.2.1 phase 2 — attention</div>
<h1>Does cropping the garment reference change what klein produces?</h1>
<div class="mcard"><div class="mh">One variable</div>
<p>Every result in a set used the <b>same person image, prompt, seed (46), endpoint
and arm</b>. The only thing that changed is the garment reference klein was shown.
13 Testset2 pairs, 65 generations.</p>
<p class="mut">Deterministic metrics are computed against the <b>original</b>
reference, never the cropped one — the crop must not also be the yardstick. Duo
references use their torso crop as the garment, as in the Testset2 harness.
Judged by eye first; these numbers are support, not the verdict.</p></div>
<div id="v">
<div class="vbar"><span class="vlabel" id="vl"></span><span id="vp"></span>
<span class="vsub" id="vs"></span><span class="vpos" id="vpos"></span></div>
<div id="stage"><img id="vi"></div>
<div class="keys"><kbd>&larr;</kbd><kbd>&rarr;</kbd> step through this pair &middot;
<kbd>&uarr;</kbd><kbd>&darr;</kbd> next pair &middot;
<kbd>B</kbd> hold for the person input &middot; <kbd>Z</kbd> zoom 1:1 &middot;
<kbd>O</kbd> open full size</div>
<div class="strip" id="strip"></div>
<div class="pairs" id="pairs"></div>
</div>
<h2>All 13 pairs</h2>
<div class="tw"><table><tr><th>variant</th><th>garment sim</th><th>identity</th>
<th>pose err</th><th>bg psnr</th><th>det score</th></tr>
{rows(ov, ['garment_sim','identity_cos','pose_err','bg_psnr','score'])}</table></div>
<h2>Duo pairs only (7) — where the reference is a whole person</h2>
<div class="tw"><table><tr><th>variant</th><th>garment sim</th><th>det score</th></tr>
{rows(duo, ['garment_sim','score'])}</table></div>
<h2>Product pairs only (6) — reference was already a clean flat-lay</h2>
<div class="tw"><table><tr><th>variant</th><th>garment sim</th><th>det score</th></tr>
{rows(prod, ['garment_sim','score'])}</table></div>
<p class="mut">Green = best in column. n=13 overall, 7 duo, 6 product — differences
under roughly 0.01 are inside noise at this sample size.</p>
<footer>Generated by v2/build/make_v221_page.py from v2/runs/v221/. C1 (tight crop,
background kept) was generated but is excluded here — it isolates framing from
background removal, which is not the question this page answers.</footer>
</div>
<script>
const SETS={json.dumps(sets)};
let S=0,I=0,ZOOM=false,PEEK=false;
const el=id=>document.getElementById(id);
const strip=el("strip"),pairs=el("pairs");
SETS.forEach((s,i)=>{{const b=document.createElement("button");b.textContent=s.pair;
b.onclick=()=>{{S=i;I=0;build();render()}};pairs.appendChild(b)}});
function build(){{strip.innerHTML="";SETS[S].items.forEach((it,i)=>{{
const f=document.createElement("figure");
f.className=(it.ref?"ref ":"")+(it.tag===true?"win":"");
f.innerHTML='<img src="'+it.src+'"><figcaption>'+it.label.trim().slice(0,22)+'</figcaption>';
f.onclick=()=>{{I=i;render()}};strip.appendChild(f)}})}}
function render(){{const set=SETS[S];const it=set.items[PEEK?0:I];
el("vi").src=it.src;
el("vl").textContent=it.label;el("vl").className="vlabel"+((I<2||PEEK||it.ref)?" inp":"");
el("vs").textContent=it.sub;
el("vp").innerHTML=it.tag===true?'<span class="pill">best on this pair</span>':"";
el("vpos").textContent=set.pair+"   "+(I+1)+"/"+set.items.length+
"   pair "+(S+1)+"/"+SETS.length+(PEEK?"   [PERSON]":"");
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
out = os.path.join(ART, "v221_klein_trial.html")
open(out, "w").write(page)
print(f"wrote {out} ({len(page)//1024}KB, {len(sets)} pairs)")
print(ov.to_string())
