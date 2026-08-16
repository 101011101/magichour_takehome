# v2/artifacts/v221_duo_transfer.html — person-to-person garment transfer.
#
# The metric that matters here is identity attribution: the result should look
# like the BASE person wearing the SOURCE person's outfit. If the face is closer
# to the source, klein imported the wrong identity — failure mode F1, and the one
# the crop is supposed to make structurally impossible.
import glob, json, os, sys
import numpy as np
import pandas as pd
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
COMBO = os.path.join(REPO, "v2", "runs", "combo")
ART = os.path.join(REPO, "v2", "artifacts")
CSV = os.path.join(COMBO, "combo_metrics.csv")


def score():
    """For each combination, score the cropped arm and the uncropped control.

    Identity attribution compares the result against the source person's
    ORIGINAL photo, never their crop: the crop has the face removed by
    construction, so AuraFace finds nothing in it and every margin comes back
    undefined. That bug voided 69 of 83 rows on the first pass."""
    import metrics_v2 as M
    orig_of = {}
    for f in glob.glob(os.path.join(COMBO, "*.json")):
        m = json.load(open(f))
        orig_of[m["base"]] = m["base_img"]      # every person appears as a base

    rows = []
    for f in sorted(glob.glob(os.path.join(COMBO, "*.png"))):
        m = json.load(open(f.replace(".png", ".json")))
        arm = "base" if m.get("uncropped") else "crop"
        base_img = Image.open(os.path.join(REPO, m["base_img"])).convert("RGB")
        src_rel = orig_of.get(m["source"])
        src_img = (Image.open(os.path.join(REPO, src_rel)).convert("RGB")
                   if src_rel else None)
        res = Image.open(f).convert("RGB")
        id_base = M.identity_cosine(base_img, res)
        id_src = M.identity_cosine(src_img, res) if src_img is not None else None
        rows.append({
            "arm": arm, "base": m["base"], "source": m["source"],
            "file": os.path.basename(f),
            "id_base": id_base, "id_src": id_src,
            "id_margin": (None if id_base is None or id_src is None
                          else round(id_base - id_src, 3)),
            "garment_sim": float(np.dot(
                M._embed(M._torso_crop(Image.open(
                    os.path.join(REPO, m["source_crop"])).convert("RGB"))),
                M._embed(M._torso_crop(res)))),
            "bg_psnr": M.background_psnr(base_img, res),
        })
    d = pd.DataFrame(rows)
    d.to_csv(CSV, index=False)
    return d


def html(d):
    REL = "../runs"
    piv = {}
    for r in d.itertuples():
        piv.setdefault((r.base, r.source), {})[r.arm] = r

    def verdict_of(r):
        if r is None or r.id_margin is None or pd.isna(r.id_margin):
            return "no face found"
        return ("WRONG PERSON" if r.id_margin < 0 else
                "weak" if r.id_margin < 0.15 else "base identity held")

    def sub_of(r):
        if r is None:
            return "not generated"
        bits = []
        if r.id_base is not None and not pd.isna(r.id_base):
            bits.append(f"id vs base {r.id_base:.3f}")
        if r.id_src is not None and not pd.isna(r.id_src):
            bits.append(f"id vs source {r.id_src:.3f}")
        if r.id_margin is not None and not pd.isna(r.id_margin):
            bits.append(f"margin {r.id_margin:+.3f}")
        bits.append(f"garment {r.garment_sim:.3f}")
        return " · ".join(bits)

    def keyfn(kv):
        c = kv[1].get("crop")
        return (-1e9 if c is None or c.id_margin is None or pd.isna(c.id_margin)
                else c.id_margin)

    sets = []
    for (b, src), arms in sorted(piv.items(), key=keyfn):
        crop, base = arms.get("crop"), arms.get("base")
        any_r = crop or base
        m = json.load(open(os.path.join(
            COMBO, any_r.file.replace(".png", ".json"))))
        items = [
            {"label": f"BASE PERSON — {b}", "src": f"../../{m['base_img']}",
             "sub": "identity, pose and background to keep", "tag": None},
            {"label": f"OUTFIT SOURCE — {src} (C3.2 crop)",
             "src": f"../../{m['source_crop']}",
             "sub": "face removed, hair kept — only the outfit should transfer",
             "tag": None}]
        if crop is not None:
            items.append({"label": "RESULT — CROPPED reference",
                          "src": f"{REL}/combo/{crop.file}",
                          "sub": sub_of(crop), "tag": True})
        if base is not None:
            items.append({"label": "RESULT — uncropped control",
                          "src": f"{REL}/combo/{base.file}",
                          "sub": sub_of(base), "tag": False})
        # which arm kept the right identity better
        delta = None
        if (crop is not None and base is not None
                and crop.id_margin is not None and base.id_margin is not None
                and not pd.isna(crop.id_margin) and not pd.isna(base.id_margin)):
            delta = round(crop.id_margin - base.id_margin, 3)
        sets.append({"pair": f"{b} wears {src}".replace("dualuse_", ""),
                     "verdict": verdict_of(crop),
                     "delta": delta, "items": items, "before_i": 0})

    def counts(arm):
        a = d[d.arm == arm]
        return (int((a.id_margin >= 0.15).sum()),
                int(((a.id_margin >= 0) & (a.id_margin < 0.15)).sum()),
                int((a.id_margin < 0).sum()),
                int(a.id_margin.isna().sum()))
    ok, weak, wrong, noface = counts("crop")
    bok, bweak, bwrong, bnoface = counts("base")
    cm = d[d.arm == "crop"].id_margin.mean()
    bm = d[d.arm == "base"].id_margin.mean()
    cg = d[d.arm == "crop"].garment_sim.mean()
    bg = d[d.arm == "base"].garment_sim.mean()
    wins = sum(1 for s_ in sets if s_["delta"] is not None and s_["delta"] > 0)
    losses = sum(1 for s_ in sets if s_["delta"] is not None and s_["delta"] < 0)

    page = f"""<!doctype html><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>v2.2.1 — person-to-person transfer</title><style>
:root{{--bg:#14141d;--card:#1b1b26;--card2:#20202c;--line:#2b2b3a;--ink:#f3f3f7;
--body:#aab0be;--mut:#868da0;--acc:#928af5;--acc2:#b7b1fa;--ok:rgba(90,200,140,.16);
--okb:rgba(90,200,140,.65);--bad:rgba(230,110,110,.14);--badb:rgba(230,110,110,.6);
--warn:rgba(230,180,90,.14);--warnb:rgba(230,180,90,.55)}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--body);
font:15px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}}
.wrap{{max-width:1600px;margin:0 auto;padding:30px 28px 60px}}
h1{{font-size:29px;margin:2px 0 6px;color:var(--ink);font-weight:700;letter-spacing:-.4px}}
h2{{font-size:19px;margin:32px 0 8px;color:var(--ink);font-weight:700}}
.kick{{color:var(--mut);font-size:13.5px}}p{{max-width:1000px}}b{{color:var(--ink)}}
.mut{{color:var(--mut);font-size:12.5px}}
.tiles{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:16px 0}}
.tile{{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px 16px}}
.tile.ok{{border-color:var(--okb)}}.tile.bad{{border-color:var(--badb)}}
.tile.warn{{border-color:var(--warnb)}}
.tnum{{font-size:28px;font-weight:700;color:var(--ink)}}
.tlab{{font-size:12px;color:var(--mut)}}
.mcard{{background:var(--card);border:1px solid var(--line);border-radius:12px;
padding:16px 18px;margin:14px 0}}
#v{{margin:14px 0 0;background:var(--card);border:1px solid var(--line);border-radius:12px;
padding:14px 18px 18px;position:sticky;top:0;z-index:5}}
.vbar{{display:flex;gap:14px;align-items:baseline;flex-wrap:wrap;margin-bottom:10px}}
.vlabel{{font-size:19px;font-weight:700;color:var(--ink);letter-spacing:-.2px}}
.vlabel.inp{{color:var(--acc2)}}
.pill{{font-size:10.5px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;
padding:2px 8px;border-radius:99px}}
.pill.ok{{background:var(--ok);color:#7fe3ac;border:1px solid var(--okb)}}
.pill.bad{{background:var(--bad);color:#ff9d9d;border:1px solid var(--badb)}}
.pill.warn{{background:var(--warn);color:#e8c98a;border:1px solid var(--warnb)}}
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
.strip{{display:flex;gap:8px;margin-top:12px}}
.strip figure{{margin:0;flex:0 0 auto;width:110px;text-align:center;cursor:pointer;opacity:.5}}
.strip figure.on{{opacity:1}}
.strip img{{width:100%;height:110px;object-fit:cover;border-radius:6px;
border:2px solid transparent;background:var(--card2);display:block}}
.strip figure.on img{{border-color:var(--acc)}}
.strip figcaption{{font-size:10px;color:var(--mut);margin-top:4px;
overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
.pairs{{display:flex;flex-wrap:wrap;gap:6px;margin-top:12px;max-height:150px;overflow-y:auto}}
.pairs button{{border:1px solid var(--line);background:var(--card2);color:var(--body);
border-radius:6px;padding:4px 9px;font-size:11px;cursor:pointer;
font-family:ui-monospace,Menlo,monospace}}
.pairs button.on{{background:var(--acc);color:#14141d;border-color:var(--acc);font-weight:700}}
.pairs button.bad{{border-color:var(--badb);color:#ff9d9d}}
.pairs button.warn{{border-color:var(--warnb)}}
footer{{margin:36px 0 8px;padding-top:14px;border-top:1px solid var(--line);
color:var(--mut);font-size:12.5px}}
</style><div class="wrap">
<div class="kick">Virtual try-on v2.2.1 — person to person</div>
<h1>Taking one person's outfit and putting it on another</h1>
<div class="mcard"><p>Two people per test: <b>image 1</b> is the base person whose
identity, pose and background must survive; <b>image 2</b> is another person's
<b>C3.2 crop</b> (face removed, hair kept), supplying only the outfit. No
product flat-lays — every reference here is a garment on a human, which is the
case klein is weakest on. {len(sets)} combinations from 42 people, each appearing as base and as source,
no one paired with themselves — each run twice, once with the source's
<b>cropped</b> reference and once with their <b>uncropped photo</b> as the
control.</p>
<p class="mut">The verdict is <b>identity margin</b> = AuraFace(result, base)
&minus; AuraFace(result, source). Positive means the result resembles the base
person, which is correct. <b>Negative means klein imported the source person's
face</b> — failure mode F1, exactly what cropping is meant to make impossible.
Sets are ordered worst-margin first.</p></div>
<div class="tw"><table>
<tr><th>arm</th><th>identity margin (mean)</th><th>garment sim</th>
<th>identity held</th><th>weak</th><th>wrong person</th><th>no face</th></tr>
<tr><td class="n">CROPPED reference (C3.2)</td><td>{cm:+.3f}</td><td>{cg:.3f}</td>
<td>{ok}</td><td>{weak}</td><td>{wrong}</td><td>{noface}</td></tr>
<tr class="base"><td class="n">uncropped control</td><td>{bm:+.3f}</td><td>{bg:.3f}</td>
<td>{bok}</td><td>{bweak}</td><td>{bwrong}</td><td>{bnoface}</td></tr>
</table></div>
<p class="mut">Per-combination, the cropped arm beat the control on identity
margin <b>{wins}</b> times and lost <b>{losses}</b> times. Sets are ordered
worst-cropped-margin first, so failures are at the top.</p>
<div id="v">
<div class="vbar"><span class="vlabel" id="vl"></span><span id="vp"></span>
<span class="vsub" id="vs"></span><span class="vpos" id="vpos"></span></div>
<div id="stage"><img id="vi"></div>
<div class="keys"><kbd>&larr;</kbd><kbd>&rarr;</kbd> base / outfit source / result &middot;
<kbd>&uarr;</kbd><kbd>&darr;</kbd> next combination &middot;
<kbd>B</kbd> hold for the base person &middot; <kbd>Z</kbd> zoom &middot; <kbd>O</kbd> full size</div>
<div class="strip" id="strip"></div>
<div class="pairs" id="pairs"></div>
</div>
<footer>Generated by v2/build/make_combo_page.py from v2/runs/combo/.
Crop variant C3.2; klein 4B distilled; seed 46; prompt names the outfit generically
since arbitrary combinations have no per-pair target garment.</footer>
</div>
<script>
const SETS={json.dumps(sets)};
let S=0,I=0,ZOOM=false,PEEK=false;
const el=id=>document.getElementById(id);
const strip=el("strip"),pairs=el("pairs");
SETS.forEach((s,i)=>{{const b=document.createElement("button");
b.textContent=s.pair.replace(/dualuse_/g,"").slice(0,30);
b.className=s.verdict==="WRONG PERSON"?"bad":(s.verdict==="weak"?"warn":"");
b.onclick=()=>{{S=i;I=0;build();render()}};pairs.appendChild(b)}});
function build(){{strip.innerHTML="";SETS[S].items.forEach((it,i)=>{{
const f=document.createElement("figure");
f.innerHTML='<img src="'+it.src+'"><figcaption>'+it.label.split(" —")[0]+'</figcaption>';
f.onclick=()=>{{I=i;render()}};strip.appendChild(f)}})}}
function render(){{const set=SETS[S];const it=set.items[PEEK?0:I];
el("vi").src=it.src;
el("vl").textContent=it.label;el("vl").className="vlabel"+((I<2||PEEK)?" inp":"");
el("vs").textContent=it.sub;
const cls=set.verdict==="WRONG PERSON"?"bad":(set.verdict==="weak"?"warn":"ok");
el("vp").innerHTML=I===2?'<span class="pill '+cls+'">'+set.verdict+'</span>':"";
el("vpos").textContent=(S+1)+"/"+SETS.length+"   "+(I+1)+"/3"+(PEEK?"   [BASE]":"");
[...strip.children].forEach((c,i)=>c.classList.toggle("on",i===I));
[...pairs.children].forEach((c,i)=>c.classList.toggle("on",i===S));
const nx=SETS[(S+1)%SETS.length];nx.items.forEach(x=>{{(new Image()).src=x.src}});}}
el("stage").onclick=()=>{{ZOOM=!ZOOM;el("stage").classList.toggle("zoom",ZOOM)}};
document.addEventListener("keydown",e=>{{
if(e.key==="ArrowRight"){{I=(I+1)%3;render();e.preventDefault()}}
else if(e.key==="ArrowLeft"){{I=(I+2)%3;render();e.preventDefault()}}
else if(e.key==="ArrowDown"){{S=(S+1)%SETS.length;I=0;build();render();e.preventDefault()}}
else if(e.key==="ArrowUp"){{S=(S+SETS.length-1)%SETS.length;I=0;build();render();e.preventDefault()}}
else if(e.key==="b"||e.key==="B"){{if(!PEEK){{PEEK=true;render()}}}}
else if(e.key==="z"||e.key==="Z"){{ZOOM=!ZOOM;el("stage").classList.toggle("zoom",ZOOM)}}
else if(e.key==="o"||e.key==="O"){{window.open(SETS[S].items[I].src,"_blank")}}}});
document.addEventListener("keyup",e=>{{if((e.key==="b"||e.key==="B")&&PEEK){{PEEK=false;render()}}}});
build();render();
</script>"""
    os.makedirs(ART, exist_ok=True)
    out = os.path.join(ART, "v221_duo_transfer.html")
    open(out, "w").write(page)
    print(f"wrote {out} ({len(page)//1024}KB, {len(sets)} combinations)")
    print(f"  base identity held {ok} | weak {weak} | WRONG PERSON {wrong} | no face {noface}")


if __name__ == "__main__":
    d = pd.read_csv(CSV) if "--html-only" in sys.argv else score()
    html(d)
