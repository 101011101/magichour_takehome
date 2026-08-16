# Generates v2/artifacts/v20_klein_variant.html — distilled vs base, head to head.
# Both variants ran the full 13-pair Testset2 matrix; this page exists because
# their means tie (VLM fidelity 4.410 each) while the per-pair story does not.
import json, os, glob
import pandas as pd

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
TS2 = os.path.join(REPO, "v2", "runs", "ts2")
ART = os.path.join(REPO, "v2", "artifacts")
REL = "../runs/ts2"

A, B = "klein_4b_edit", "klein_4b_base_edit"
LBL = {A: "klein 4B distilled", B: "klein 4B base"}
KIND_LABEL = {"product": "garment only", "duo_lookbook": "garment + human (lookbook)",
              "duo_swap": "garment + human (swap)"}
FID, REAL = ["garment", "identity", "scene"], ["clean", "hands", "realism"]

d = pd.read_csv(os.path.join(TS2, "ts2_cv_metrics.csv"))
v = pd.read_csv(os.path.join(TS2, "ts2_vlm.csv"))
v["fid"] = v[FID].mean(axis=1)
v["real"] = v[REAL].mean(axis=1)
mx = pd.read_csv(os.path.join(TS2, "matrix.csv")).set_index("id")

dv, dd = v[v.arm.isin([A, B])], d[d.arm.isin([A, B])]
overall = (dv.groupby("arm")[["fid", "real"] + FID + REAL].mean()
           .join(dd.groupby("arm")[["garment_sim", "identity_cos", "bg_psnr", "score"]].mean())
           .round(3))
bykind = dv.groupby(["kind", "arm"])[["fid", "real", "garment", "identity", "scene"]].mean().round(2)
perpair = dv.pivot_table(index="id", columns="arm", values="fid")
perpair["delta"] = (perpair[B] - perpair[A]).round(2)
perpair = perpair.sort_values("delta")


def local(rel):
    return f"{REL}/inputs/" + os.path.splitext(os.path.basename(rel))[0] + ".jpg"


sets = []
for pid in perpair.index:
    r = mx.loc[pid]
    items = [{"label": "PERSON (image 1)", "src": local(r.person),
              "sub": KIND_LABEL[r.kind], "tag": None},
             {"label": "GARMENT REF (image 2)", "src": local(r.garment),
              "sub": f"target: {r.target}", "tag": None}]
    for arm in (A, B):
        f = os.path.join(TS2, "outputs", f"{arm}__{pid}.png")
        if not os.path.exists(f):
            continue
        vm = dv[(dv.arm == arm) & (dv.id == pid)]
        dm = dd[(dd.arm == arm) & (dd.id == pid)]
        sub = []
        if len(vm):
            sub += [f"fidelity {vm.fid.iloc[0]:.2f}", f"realism {vm.real.iloc[0]:.2f}",
                    f"garment {vm.garment.iloc[0]}", f"identity {vm.identity.iloc[0]}",
                    f"scene {vm.scene.iloc[0]}"]
        if len(dm):
            sub += [f"det {dm.score.iloc[0]:.3f}", f"id {dm.identity_cos.iloc[0]:.3f}"]
        win = None
        if len(vm):
            other = dv[(dv.arm == (B if arm == A else A)) & (dv.id == pid)]
            if len(other):
                win = bool(vm.fid.iloc[0] > other.fid.iloc[0])
        items.append({"label": LBL[arm], "src": f"{REL}/outputs/{arm}__{pid}.png",
                      "sub": " · ".join(sub), "tag": win})
    dl = perpair.loc[pid, "delta"]
    arrow = "base +{:.2f}".format(dl) if dl > 0 else ("tie" if dl == 0 else "distilled +{:.2f}".format(-dl))
    sets.append({"pair": f"{pid} · {KIND_LABEL[r.kind]} · {arrow}", "items": items})


def two_row(df, cols, fmt="{:.2f}"):
    head = "".join(f"<th>{c}</th>" for c in ["variant"] + cols)
    body = ""
    for arm in (A, B):
        cells = "".join(
            f"<td>{fmt.format(df.loc[arm, c]) if df.loc[arm, c] == df.loc[arm, c] else ''}"
            f"</td>" for c in cols)
        best = " class='win'" if arm == B else ""
        body += f"<tr><td class='n'>{LBL[arm]}</td>{cells}</tr>"
    return f"<div class='tw'><table><tr>{head}</tr>{body}</table></div>"


ov_cols = ["fid", "real", "garment", "identity", "scene", "clean", "hands",
           "realism", "garment_sim", "identity_cos", "bg_psnr", "score"]
ov_head = ["VLM fidelity", "VLM realism", "garment", "identity", "scene", "clean",
           "hands", "realism", "garment sim", "id cos", "bg psnr", "det score"]
ov_rows = ""
for arm in (A, B):
    cells = "".join(f"<td>{overall.loc[arm, c]:.3f}</td>" for c in ov_cols)
    ov_rows += f"<tr><td class='n'>{LBL[arm]}</td>{cells}</tr>"

kind_rows = ""
for kind in ("product", "duo_lookbook", "duo_swap"):
    for arm in (A, B):
        if (kind, arm) not in bykind.index:
            continue
        r = bykind.loc[(kind, arm)]
        w = " class='win'" if r.fid == bykind.loc[kind]["fid"].max() else ""
        kind_rows += (f"<tr{w}><td class='n'>{KIND_LABEL[kind]}</td><td class='n'>{LBL[arm]}</td>"
                      f"<td>{r.fid:.2f}</td><td>{r.real:.2f}</td><td>{r.garment:.2f}</td>"
                      f"<td>{r.identity:.2f}</td><td>{r.scene:.2f}</td></tr>")

pp_rows = ""
for pid, r in perpair.iterrows():
    dl = r["delta"]
    cls = "win" if dl > 0 else ("fail" if dl < 0 else "")
    pp_rows += (f"<tr class='{cls}'><td class='n'>{pid}</td>"
                f"<td class='n'>{KIND_LABEL[mx.loc[pid,'kind']]}</td>"
                f"<td>{r[A]:.2f}</td><td>{r[B]:.2f}</td><td><b>{dl:+.2f}</b></td></tr>")

page = f"""<!doctype html><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>klein distilled vs base</title><style>
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
.mt{{font-size:17px;font-weight:700;color:var(--ink);margin-bottom:2px}}
.mc{{font-family:ui-monospace,Menlo,monospace;font-size:11.5px;color:var(--mut);margin-bottom:8px}}
.mp{{font-size:12.5px;color:var(--mut);margin:8px 0 0}}
.warn{{background:rgba(230,180,90,.10);border:1px solid rgba(230,180,90,.45);
border-radius:10px;padding:12px 16px;margin:16px 0;font-size:13px;color:#e8c98a;max-width:1000px}}
#v{{margin:14px 0 0;background:var(--card);border:1px solid var(--line);border-radius:12px;
padding:14px 18px 18px;position:sticky;top:0;z-index:5}}
.vbar{{display:flex;gap:14px;align-items:baseline;flex-wrap:wrap;margin-bottom:10px}}
.vlabel{{font-size:20px;font-weight:700;color:var(--ink);letter-spacing:-.2px}}
.vlabel.before{{color:var(--acc2)}}
.pill{{font-size:10.5px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;
padding:2px 8px;border-radius:99px}}
.pill.pass{{background:var(--ok);color:#7fe3ac;border:1px solid var(--okb)}}
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
.strip figure.winner img{{border-color:var(--okb)}}
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
<div class="kick">Virtual try-on V2 — which klein?</div>
<h1>klein 4B: distilled vs base</h1>
<div class="meta">
<div class="mcard"><div class="mh">Variant A — currently shipped in every V2 number</div>
<div class="mt">klein 4B distilled</div>
<div class="mc">fal-ai/flux-2/klein/4b/distilled/edit</div>
<p class="mp">Apache 2.0, ~4 steps, sub-second. <b>No negative prompt and no
guidance exposed</b>, and distillation brings low seed diversity plus the known
flake (one solid-black frame in 16 triage runs). Every "klein" figure in
V2.0/V2.1 is this variant.</p></div>
<div class="mcard"><div class="mh">Variant B — the undistilled sibling</div>
<div class="mt">klein 4B base</div>
<div class="mc">fal-ai/flux-2/klein/4b/base/edit</div>
<p class="mp">Same Apache 2.0 family, true CFG and <b>negative prompts</b>.
Ran the full 13-pair matrix with a negative prompt of
<i>"different person, changed face, changed background, extra limbs, deformed
hands"</i>.</p></div>
</div>
<div class="warn"><b>Read the comparison this way.</b> Base ran <i>with</i> a
negative prompt; distilled cannot accept one. This is therefore a
variant-plus-prompt comparison, not a clean variant-only one — some of base's
identity and scene advantage may come from the negative prompt rather than the
checkpoint. An isolation run (base without the negative prompt) is required
before attributing the difference.</div>
<div id="v">
<div class="vbar"><span class="vlabel" id="vl"></span><span id="vp"></span>
<span class="vsub" id="vs"></span><span class="vpos" id="vpos"></span></div>
<div id="stage"><img id="vi"></div>
<div class="keys"><kbd>&larr;</kbd><kbd>&rarr;</kbd> person, garment, distilled, base &middot;
<kbd>&uarr;</kbd><kbd>&darr;</kbd> next pair (ordered worst-for-base first) &middot;
<kbd>B</kbd> hold to flip back to the person &middot; <kbd>Z</kbd> or click to zoom 1:1 &middot;
<kbd>O</kbd> open full size</div>
<div class="strip" id="strip"></div>
<div class="pairs" id="pairs"></div>
</div>
<h2>Overall — 13 pairs each</h2>
<div class="tw"><table><tr><th>variant</th>{''.join(f'<th>{h}</th>' for h in ov_head)}</tr>
{ov_rows}</table></div>
<p class="mut">They tie exactly on VLM fidelity (4.410). Distilled wins garment
transfer and the deterministic composite; base wins identity, scene and realism.</p>
<h2>By pair kind</h2>
<div class="tw"><table><tr><th>kind</th><th>variant</th><th>VLM fidelity</th>
<th>VLM realism</th><th>garment</th><th>identity</th><th>scene</th></tr>
{kind_rows}</table></div>
<h2>Per pair — where the tie comes from</h2>
<div class="tw"><table><tr><th>pair</th><th>kind</th><th>distilled</th><th>base</th>
<th>delta (base &minus; distilled)</th></tr>{pp_rows}</table></div>
<p class="mut">The mean hides the shape: base is slightly worse on five pairs,
identical on six, and <b>+2.00 on ts2_12</b> — the pair where distilled collapsed
(fidelity 2.67; it is also v2.3's worst known-bad fixture, VLM clean 2 / scene 1 /
realism 2). One catastrophic distilled output is doing all the work in an
otherwise mild loss. That is the distillation flake showing up in the aggregate,
and it is the single strongest argument for base.</p>
<footer>Generated by v2/build/make_klein_page.py from v2/runs/ts2/. Both variants
are Apache 2.0 and self-hostable; all numbers are fal numbers pending parity.</footer>
</div>
<script>
const SETS={json.dumps(sets)};
let S=0,I=0,ZOOM=false,PEEK=false;
const el=id=>document.getElementById(id);
const strip=el("strip"),pairs=el("pairs");
SETS.forEach((s,i)=>{{const b=document.createElement("button");b.textContent=s.pair;
b.onclick=()=>{{S=i;I=0;build();render()}};pairs.appendChild(b)}});
function build(){{strip.innerHTML="";SETS[S].items.forEach((it,i)=>{{
const f=document.createElement("figure");f.className=(it.tag===true?"winner":"");
f.innerHTML='<img src="'+it.src+'"><figcaption>'+it.label+'</figcaption>';
f.onclick=()=>{{I=i;render()}};strip.appendChild(f)}})}}
function render(){{const set=SETS[S];const it=set.items[PEEK?0:I];
el("vi").src=it.src;
el("vl").textContent=it.label;el("vl").className="vlabel"+((I<2||PEEK)?" before":"");
el("vs").textContent=it.sub;
el("vp").innerHTML=it.tag===true?'<span class="pill pass">wins this pair</span>':"";
el("vpos").textContent=set.pair+"   "+(I+1)+"/"+set.items.length+
"   set "+(S+1)+"/"+SETS.length+(PEEK?"   [PERSON]":"");
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
out = os.path.join(ART, "v20_klein_variant.html")
open(out, "w").write(page)
print(f"wrote {out} ({len(page)//1024}KB, {len(sets)} pairs)")
