# v2/artifacts/v221_review.html — the single review page for v2.2.1 phase 2.
#
# 33 sets: the 13 Testset2 pairs plus 20 person-to-person combinations, each
# showing the two inputs and then all five arms. Every slide states what it is
# and which inputs produced it — an earlier page did not, and was unreadable.
#
# Also carries a NO-OP flag. SSIM between the output and the person input tells
# you whether the model changed anything at all. This matters because a no-op
# scores perfectly on identity preservation: the highest identity margin in the
# combination run was an output identical to its input. Without this column the
# other numbers can be read exactly backwards.
import glob, json, os, sys
import numpy as np, cv2, pandas as pd
from PIL import Image

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
TS2, V221 = os.path.join(REPO, "v2", "runs", "ts2"), os.path.join(REPO, "v2", "runs", "v221")
COMBO, CROPS = os.path.join(REPO, "v2", "runs", "combo"), os.path.join(REPO, "v2", "runs", "crop_screen")
ART = os.path.join(REPO, "v2", "artifacts")
REL = "../runs"
CACHE = os.path.join(REPO, "v2", "runs", "v221_review_noop.csv")

ARMS = [("base", "BASE", "uncropped reference — the control"),
        ("c2", "C2", "background white, wearer kept"),
        ("c31", "C3.1", "face AND hair removed"),
        ("c32", "C3.2", "face removed, hair kept"),
        ("c4", "C4", "clothes only, all skin removed")]
COMBO_TAG = {"base": "__base", "c2": "__c2_bbox_nobg", "c31": "__c3_no_face",
             "c32": "", "c4": "__c4_clothes_only"}
TS2_FILE = {"base": None, "c2": "c2_bbox_nobg", "c31": "c31_no_face",
            "c32": "c32_keep_hair", "c4": "c4_clothes_only"}
CROP_SUF = {"c2": "c2_bbox_nobg", "c31": "c3_no_face",
            "c32": "c32_no_face_keep_hair", "c4": "c4_clothes_only"}


def ssim(a, b):
    ga = cv2.cvtColor(np.array(a.convert("RGB")), cv2.COLOR_RGB2GRAY).astype(np.float64)
    gb = cv2.cvtColor(np.array(b.convert("RGB").resize(a.size)), cv2.COLOR_RGB2GRAY).astype(np.float64)
    C1, C2 = (0.01 * 255) ** 2, (0.03 * 255) ** 2
    ma, mb = cv2.GaussianBlur(ga, (11, 11), 1.5), cv2.GaussianBlur(gb, (11, 11), 1.5)
    sa = cv2.GaussianBlur(ga * ga, (11, 11), 1.5) - ma ** 2
    sb = cv2.GaussianBlur(gb * gb, (11, 11), 1.5) - mb ** 2
    sab = cv2.GaussianBlur(ga * gb, (11, 11), 1.5) - ma * mb
    return float((((2 * ma * mb + C1) * (2 * sab + C2)) /
                  ((ma ** 2 + mb ** 2 + C1) * (sa + sb + C2))).mean())


def stem(p):
    return os.path.splitext(os.path.basename(p))[0]


def build_sets():
    mx = pd.read_csv(os.path.join(TS2, "matrix.csv")).set_index("id")
    sets = []
    # --- the 13 Testset2 pairs
    for pid, r in mx.iterrows():
        person = os.path.join(TS2, "inputs", f"{stem(r.person)}.jpg")
        garment = os.path.join(TS2, "inputs", f"{stem(r.garment)}.jpg")
        outs = {}
        for k, _, _ in ARMS:
            f = (os.path.join(TS2, "outputs", f"klein_4b_edit__{pid}.png") if k == "base"
                 else os.path.join(V221, f"{TS2_FILE[k]}__{pid}.png"))
            if os.path.exists(f):
                outs[k] = f
        sets.append({"id": pid, "group": "Testset2", "kind": r.kind,
                     "person": person, "person_name": stem(r.person),
                     "garment": garment, "garment_name": stem(r.garment),
                     "target": r.target, "outs": outs,
                     "crops": {k: os.path.join(CROPS, f"{stem(r.garment)}__{v}.jpg")
                               for k, v in CROP_SUF.items()}})
    # --- the 20 selected person-to-person combinations
    for line in open("/tmp/combo_sel.txt"):
        b, s = line.strip().split("|")
        j = os.path.join(COMBO, f"{b}__wears__{s}.json")
        if not os.path.exists(j):
            continue
        m = json.load(open(j))
        outs = {}
        for k, _, _ in ARMS:
            f = os.path.join(COMBO, f"{b}__wears__{s}{COMBO_TAG[k]}.png")
            if os.path.exists(f):
                outs[k] = f
        src_orig = os.path.join(REPO, m["base_img"]).replace(f"/{b}.", f"/{s}.")
        if not os.path.exists(src_orig):
            src_orig = (os.path.join(REPO, "test_set", "people", f"{s}.jpg")
                        if s.startswith("p") else os.path.join(TS2, "inputs", f"{s}.jpg"))
        sets.append({"id": f"{b}+{s}", "group": "person-to-person", "kind": "duo_swap",
                     "person": os.path.join(REPO, m["base_img"]), "person_name": b,
                     "garment": src_orig, "garment_name": s,
                     "target": "the complete outfit", "outs": outs,
                     "crops": {k: os.path.join(CROPS, f"{s}__{v}.jpg")
                               for k, v in CROP_SUF.items()}})
    return sets


def noop_table(sets):
    if os.path.exists(CACHE):
        return pd.read_csv(CACHE).set_index(["id", "arm"]).ssim.to_dict()
    rows = []
    for st in sets:
        pin = Image.open(st["person"]).convert("RGB")
        for k, f in st["outs"].items():
            rows.append({"id": st["id"], "arm": k,
                         "ssim": round(ssim(pin, Image.open(f).convert("RGB")), 4)})
    d = pd.DataFrame(rows)
    d.to_csv(CACHE, index=False)
    return d.set_index(["id", "arm"]).ssim.to_dict()


def main():
    sets = build_sets()
    noop = noop_table(sets)
    payload = []
    for st in sets:
        items = [
            {"label": "INPUT 1 · PERSON TO DRESS",
             "name": st["person_name"],
             "src": os.path.relpath(st["person"], ART),
             "sub": f"{st['group']} · {st['kind']} — identity, pose and background must survive",
             "cls": "input"},
            {"label": "INPUT 2 · GARMENT SOURCE (uncropped)",
             "name": st["garment_name"],
             "src": os.path.relpath(st["garment"], ART),
             "sub": f"target: {st['target']} — only this should transfer",
             "cls": "input"}]
        for k, short, desc in ARMS:
            f = st["outs"].get(k)
            if not f:
                continue
            s_ = noop.get((st["id"], k))
            flag = ""
            if s_ is not None:
                flag = ("NO-OP — output ≈ input" if s_ > 0.90 else
                        "barely changed" if s_ > 0.80 else "")
            ref = ("the uncropped INPUT 2 above" if k == "base"
                   else f"INPUT 2 cropped: {desc}")
            items.append({
                "label": f"OUTPUT · {short}",
                "name": f"{st['person_name']} wearing {st['garment_name']}'s outfit",
                "src": os.path.relpath(f, ART),
                "sub": f"reference sent = {ref}" +
                       (f"   ·   SSIM to input {s_:.3f}" if s_ is not None else ""),
                "cls": "noop" if flag.startswith("NO-OP") else "output",
                "flag": flag})
            if k != "base":
                cf = st["crops"].get(k)
                if cf and os.path.exists(cf):
                    items[-1]["refimg"] = os.path.relpath(cf, ART)
        payload.append({"id": st["id"], "group": st["group"],
                        "title": f"{st['person_name']}  ←  {st['garment_name']}",
                        "items": items})

    n_noop = sum(1 for p in payload for i in p["items"]
                 if i.get("flag", "").startswith("NO-OP"))
    page = f"""<!doctype html><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>v2.2.1 review — cropping the garment reference</title><style>
:root{{--bg:#14141d;--card:#1b1b26;--card2:#20202c;--line:#2b2b3a;--ink:#f3f3f7;
--body:#aab0be;--mut:#868da0;--acc:#928af5;--acc2:#b7b1fa;
--in:rgba(146,138,245,.16);--inb:rgba(146,138,245,.6);
--bad:rgba(230,110,110,.16);--badb:rgba(230,110,110,.65)}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--body);
font:15px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}}
.wrap{{max-width:1600px;margin:0 auto;padding:26px 28px 60px}}
h1{{font-size:28px;margin:2px 0 6px;color:var(--ink);font-weight:700;letter-spacing:-.4px}}
.kick{{color:var(--mut);font-size:13.5px}}p{{max-width:1020px}}b{{color:var(--ink)}}
.mut{{color:var(--mut);font-size:12.5px}}
.mcard{{background:var(--card);border:1px solid var(--line);border-radius:12px;
padding:14px 18px;margin:14px 0}}
#v{{margin:14px 0 0;background:var(--card);border:1px solid var(--line);border-radius:12px;
padding:14px 18px 18px;position:sticky;top:0;z-index:5}}
.vtop{{display:flex;gap:12px;align-items:baseline;flex-wrap:wrap;margin-bottom:2px}}
.vrole{{font-size:11px;font-weight:800;letter-spacing:.1em;text-transform:uppercase;
padding:3px 9px;border-radius:5px;background:var(--card2);color:var(--body)}}
.vrole.input{{background:var(--in);color:var(--acc2);border:1px solid var(--inb)}}
.vrole.noop{{background:var(--bad);color:#ff9d9d;border:1px solid var(--badb)}}
.vname{{font-size:19px;font-weight:700;color:var(--ink);letter-spacing:-.2px}}
.vflag{{font-size:11px;font-weight:800;letter-spacing:.08em;text-transform:uppercase;
color:#ff9d9d;border:1px solid var(--badb);border-radius:99px;padding:2px 9px}}
.vsub{{color:var(--mut);font-size:12.5px;font-variant-numeric:tabular-nums;margin-bottom:9px}}
.vpos{{margin-left:auto;color:var(--mut);font-size:12px;font-family:ui-monospace,Menlo,monospace}}
.stagewrap{{display:flex;gap:10px}}
#stage{{background:#0d0d14;border-radius:10px;display:flex;align-items:center;
justify-content:center;overflow:auto;height:72vh;min-height:400px;flex:1}}
#stage img{{display:block;max-width:100%;max-height:72vh;object-fit:contain;cursor:zoom-in}}
#stage.zoom{{align-items:flex-start;justify-content:flex-start}}
#stage.zoom img{{max-width:none;max-height:none;cursor:zoom-out}}
#refbox{{width:150px;flex:0 0 auto;display:none;flex-direction:column;gap:6px}}
#refbox.on{{display:flex}}
#refbox img{{width:100%;border-radius:8px;background:#0d0d14;border:1px solid var(--line)}}
#refbox .cap{{font-size:10.5px;color:var(--mut);line-height:1.3}}
.keys{{margin-top:10px;color:var(--mut);font-size:12.5px}}
kbd{{background:var(--card2);border:1px solid var(--line);border-bottom-width:2px;
border-radius:4px;padding:1px 6px;font-size:11.5px;color:var(--body)}}
.strip{{display:flex;gap:8px;overflow-x:auto;margin-top:12px;padding-bottom:4px}}
.strip figure{{margin:0;flex:0 0 auto;width:96px;text-align:center;cursor:pointer;opacity:.45}}
.strip figure.on{{opacity:1}}
.strip img{{width:100%;height:96px;object-fit:cover;border-radius:6px;
border:2px solid transparent;background:var(--card2);display:block}}
.strip figure.input img{{border-color:var(--inb)}}
.strip figure.noop img{{border-color:var(--badb)}}
.strip figure.on img{{border-color:var(--acc)}}
.strip figcaption{{font-size:9.5px;color:var(--mut);margin-top:4px;
overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
.pairs{{display:flex;flex-wrap:wrap;gap:6px;margin-top:12px;max-height:120px;overflow-y:auto}}
.pairs button{{border:1px solid var(--line);background:var(--card2);color:var(--body);
border-radius:6px;padding:4px 9px;font-size:11px;cursor:pointer;
font-family:ui-monospace,Menlo,monospace}}
.pairs button.on{{background:var(--acc);color:#14141d;border-color:var(--acc);font-weight:700}}
.pairs button.p2p{{border-style:dashed}}
footer{{margin:34px 0 8px;padding-top:14px;border-top:1px solid var(--line);
color:var(--mut);font-size:12.5px}}
#ann{{margin-top:12px;border-top:1px solid var(--line);padding-top:12px;
display:grid;grid-template-columns:1fr 1fr;gap:14px}}
@media(max-width:1100px){{#ann{{grid-template-columns:1fr}}}}
.annh{{font-size:10.5px;font-weight:800;letter-spacing:.09em;text-transform:uppercase;
color:var(--acc);margin-bottom:7px}}
.chips{{display:flex;flex-wrap:wrap;gap:6px}}
.chip{{border:1px solid var(--line);background:var(--card2);color:var(--body);
border-radius:6px;padding:5px 11px;font-size:12px;cursor:pointer;user-select:none}}
.chip:hover{{border-color:var(--acc)}}
.chip.on{{background:var(--bad);border-color:var(--badb);color:#ffbcbc;font-weight:700}}
.chip.art.on{{background:rgba(230,180,90,.18);border-color:rgba(230,180,90,.6);color:#e8c98a}}
.chip kbd{{margin-left:6px;opacity:.55;font-size:10px;padding:0 4px}}
.solverow{{display:flex;align-items:center;gap:8px;margin:5px 0;font-size:12.5px}}
.solverow .nm{{width:44px;color:var(--ink);font-weight:700}}
.sbtn{{border:1px solid var(--line);background:var(--card2);color:var(--body);
border-radius:6px;padding:3px 12px;font-size:11.5px;cursor:pointer}}
.sbtn.yes.on{{background:rgba(90,200,140,.2);border-color:rgba(90,200,140,.65);
color:#7fe3ac;font-weight:700}}
.sbtn.no.on{{background:var(--bad);border-color:var(--badb);color:#ffbcbc;font-weight:700}}
#notes{{width:100%;margin-top:8px;background:var(--card2);border:1px solid var(--line);
border-radius:6px;color:var(--body);padding:6px 9px;font:12.5px/1.4 inherit;resize:vertical}}
.annbar{{display:flex;gap:10px;align-items:center;margin-top:10px;flex-wrap:wrap}}
.annbar button{{border:1px solid var(--acc);background:var(--acc);color:#14141d;
border-radius:6px;padding:6px 14px;font-size:12.5px;font-weight:700;cursor:pointer}}
.annbar button.ghost{{background:transparent;color:var(--body);border-color:var(--line);font-weight:400}}
.prog{{color:var(--mut);font-size:12px;margin-left:auto;font-variant-numeric:tabular-nums}}
</style><div class="wrap">
<div class="kick">Virtual try-on v2.2.1 phase 2 — does cropping the garment reference help?</div>
<h1>33 sets · 2 inputs and 5 arms each</h1>
<div class="mcard">
<p><b>Every set is the same shape.</b> Two inputs first, then the five results:
<b>INPUT 1</b> the person being dressed, <b>INPUT 2</b> the garment source
uncropped, then <b>BASE</b> (klein given INPUT 2 as-is) and <b>C2 / C3.1 / C3.2 /
C4</b> (klein given progressively more aggressive crops of INPUT 2). Person,
prompt, seed and endpoint are identical across an entire set — the only thing
that changes is which version of INPUT 2 the model saw. Each cropped result shows
the exact reference it received in the side panel.</p>
<p class="mut">13 sets are Testset2 pairs, 20 are person-to-person combinations
(both inputs are people; the outfit is taken from the second). The 20 were chosen
deliberately: 14 where the uncropped run substituted the wrong identity, 6 where
it did not, so both the failure and the control case are visible.</p>
<p><b>Read the NO-OP flag first.</b> {n_noop} of the {sum(len(p['items'])-2 for p in payload)}
outputs are near-identical to their input — the model did nothing. These score
<i>perfectly</i> on identity preservation, so any identity metric read without
this flag says the opposite of the truth.</p>
</div>
<div id="v">
<div class="vtop"><span class="vrole" id="vrole"></span><span class="vname" id="vname"></span>
<span id="vflag"></span><span class="vpos" id="vpos"></span></div>
<div class="vsub" id="vsub"></div>
<div class="stagewrap">
<div id="stage"><img id="vi"></div>
<div id="refbox"><img id="refi"><div class="cap">the cropped INPUT 2 actually sent to klein for this result</div></div>
</div>
<div class="keys"><kbd>&larr;</kbd><kbd>&rarr;</kbd> inputs then arms &middot;
<kbd>&uarr;</kbd><kbd>&darr;</kbd> next set &middot; <kbd>B</kbd> hold for INPUT 1 &middot;
<kbd>Z</kbd> zoom &middot; <kbd>O</kbd> full size</div>
<div class="strip" id="strip"></div>
<div class="pairs" id="pairs"></div>
<div id="ann">
  <div>
    <div class="annh">What did BASE get wrong? (uncropped reference)</div>
    <div class="chips" id="failchips"></div>
    <textarea id="notes" rows="2" placeholder="notes for this set (optional)"></textarea>
  </div>
  <div>
    <div class="annh">Did the crop solve it?</div>
    <div id="solves"></div>
    <div class="annbar">
      <button id="dlbtn">Download CSV</button>
      <button class="ghost" id="clearbtn">Clear this set</button>
      <span class="prog" id="prog"></span>
    </div>
  </div>
</div>
</div>
<footer>Generated by v2/build/make_v221_review.py. Outputs in v2/runs/v221/ and
v2/runs/combo/; crops in v2/runs/crop_screen/. klein 4B distilled, seed 46.</footer>
</div>
<script>
const SETS={json.dumps(payload)};
let S=0,I=0,ZOOM=false,PEEK=false;
const el=id=>document.getElementById(id);
const strip=el("strip"),pairs=el("pairs");
SETS.forEach((s,i)=>{{const b=document.createElement("button");
b.textContent=s.title.replace(/dualuse_/g,"").slice(0,34);
b.className=s.group==="person-to-person"?"p2p":"";
b.onclick=()=>{{S=i;I=0;build();render()}};pairs.appendChild(b)}});
function build(){{strip.innerHTML="";SETS[S].items.forEach((it,i)=>{{
const f=document.createElement("figure");f.className=it.cls;
f.innerHTML='<img src="'+it.src+'"><figcaption>'+it.label.replace("OUTPUT · ","").replace("INPUT 1 · ","1: ").replace("INPUT 2 · ","2: ")+'</figcaption>';
f.onclick=()=>{{I=i;render()}};strip.appendChild(f)}})}}
function render(){{const set=SETS[S];const it=set.items[PEEK?0:I];
el("vi").src=it.src;
el("vrole").textContent=it.label;el("vrole").className="vrole "+it.cls;
el("vname").textContent=it.name;
el("vflag").innerHTML=it.flag?'<span class="vflag">'+it.flag+'</span>':"";
el("vsub").textContent=it.sub;
const rb=el("refbox");
if(it.refimg&&!PEEK){{rb.classList.add("on");el("refi").src=it.refimg}}
else rb.classList.remove("on");
el("vpos").textContent=set.title+"   "+(I+1)+"/"+set.items.length+
"   set "+(S+1)+"/"+SETS.length+(PEEK?"   [INPUT 1]":"");
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
const FAILS=[["nontransfer","no transfer","N"],["wrongperson","wrong person","P"],
["wrongclothes","wrong clothes","C"],["duplication","duplication","D"],
["wrongbg","wrong background","G"],["artefacts","AI artefacts (v2.3)","A"]];
const CROPARMS=["C2","C3.1","C3.2","C4"];
const KEY="v221_review_annotations";
let ANN={{}};
try{{ANN=JSON.parse(localStorage.getItem(KEY)||"{{}}")}}catch(e){{ANN={{}}}}
function cur(){{const id=SETS[S].id;
  if(!ANN[id])ANN[id]={{fails:{{}},solved:{{}},notes:""}};
  return ANN[id];}}
function saveAnn(){{localStorage.setItem(KEY,JSON.stringify(ANN));renderProg();}}
function toggleFail(k){{const a=cur();a.fails[k]=!a.fails[k];saveAnn();renderAnn();}}
function setSolved(arm,v){{const a=cur();a.solved[arm]=(a.solved[arm]===v?null:v);
  saveAnn();renderAnn();}}
function renderProg(){{
  const n=Object.keys(ANN).filter(function(k){{const a=ANN[k]||{{}};
    return Object.values(a.fails||{{}}).some(Boolean)
      ||Object.values(a.solved||{{}}).some(function(v){{return !!v}})
      ||(a.notes||"");}}).length;
  el("prog").textContent=n+" / "+SETS.length+" sets annotated";}}
function renderAnn(){{
  const a=cur();
  const fc=el("failchips");fc.innerHTML="";
  FAILS.forEach(function(f){{
    const sp=document.createElement("span");
    sp.className="chip"+(f[0]==="artefacts"?" art":"")+(a.fails[f[0]]?" on":"");
    sp.dataset.k=f[0];
    sp.innerHTML=f[1]+'<kbd>'+f[2]+'</kbd>';
    fc.appendChild(sp);}});
  const sv=el("solves");sv.innerHTML="";
  CROPARMS.forEach(function(arm){{
    const v=a.solved[arm];
    const row=document.createElement("div");row.className="solverow";
    const nm=document.createElement("span");nm.className="nm";nm.textContent=arm;
    const y=document.createElement("span");
    y.className="sbtn yes"+(v==="yes"?" on":"");y.textContent="solved";
    y.dataset.arm=arm;y.dataset.v="yes";
    const n=document.createElement("span");
    n.className="sbtn no"+(v==="no"?" on":"");n.textContent="not solved";
    n.dataset.arm=arm;n.dataset.v="no";
    row.appendChild(nm);row.appendChild(y);row.appendChild(n);
    sv.appendChild(row);}});
  el("notes").value=a.notes||"";
  renderProg();}}
el("failchips").addEventListener("click",function(e){{
  const t=e.target.closest("[data-k]");if(t)toggleFail(t.dataset.k);}});
el("solves").addEventListener("click",function(e){{
  const t=e.target.closest("[data-arm]");if(t)setSolved(t.dataset.arm,t.dataset.v);}});
el("clearbtn").addEventListener("click",function(){{
  delete ANN[SETS[S].id];saveAnn();renderAnn();}});
el("notes").addEventListener("input",function(e){{cur().notes=e.target.value;saveAnn();}});
el("dlbtn").addEventListener("click",function(){{
  const head=["set_id","group","person","garment_source"]
    .concat(FAILS.map(function(f){{return "base_"+f[0]}}))
    .concat(CROPARMS.map(function(x){{return "solved_"+x.replace(".","_")}}))
    .concat(["notes"]);
  function q(v){{return '"'+String(v==null?"":v).split('"').join('""')+'"';}}
  const lines=[head.join(",")];
  SETS.forEach(function(st){{
    const a=ANN[st.id]||{{fails:{{}},solved:{{}},notes:""}};
    lines.push([st.id,st.group,st.items[0].name,st.items[1].name].map(q)
      .concat(FAILS.map(function(f){{return q(a.fails[f[0]]?1:0)}}))
      .concat(CROPARMS.map(function(x){{return q(a.solved[x]||"")}}))
      .concat([q(a.notes||"")]).join(","));}});
  const blob=new Blob([lines.join(String.fromCharCode(10))],{{type:"text/csv"}});
  const u=URL.createObjectURL(blob),dl=document.createElement("a");
  dl.href=u;dl.download="v221_review_annotations.csv";dl.click();
  URL.revokeObjectURL(u);}});
document.addEventListener("keydown",function(e){{
  if(e.target.tagName==="TEXTAREA")return;
  for(let i=0;i<FAILS.length;i++){{
    if(FAILS[i][2].toLowerCase()===e.key.toLowerCase()){{
      toggleFail(FAILS[i][0]);e.preventDefault();return;}}}}}});
const _render=render;render=function(){{_render();renderAnn()}};
build();render();
</script>"""
    os.makedirs(ART, exist_ok=True)
    out = os.path.join(ART, "v221_review.html")
    open(out, "w").write(page)
    print(f"wrote {out} ({len(page)//1024}KB, {len(payload)} sets)")
    print(f"  no-op outputs flagged: {n_noop}")


if __name__ == "__main__":
    main()
