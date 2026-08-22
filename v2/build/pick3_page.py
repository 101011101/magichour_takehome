# Three-tier pick sheet -- stop on PERFECT, not on merely usable.
#
# Supersedes v223_cheapest_usable.html. That sheet asked a binary usable/not question,
# which conflated "ship it" with "acceptable", and the cascade it implied optimised for
# coverage rather than quality. The objective is to maximise perfect outputs, so the
# stopping rule has to be the perfect verdict itself.
#
# It also replaces the AMT tier as the label of record for this question. AMT "perfect"
# meant TIED FOR FIRST among ten arms -- a relative ranking. An arm can top a weak field
# without being shippable, so a relative label cannot drive an absolute stop decision.
#
# Arm order is PHEAD -> BC_klein -> QX. QX is deliberately last: it has the lowest
# standalone perfect rate of the three and exists to route around AI artefacts, not to
# produce the best frame. PHEAD and BC_klein are the arms that can be perfect.
import csv, html, json, os

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
ART = os.path.join(REPO, "v2", "artifacts")
NL = chr(10)
ORDER = ["PHEAD", "BC_klein", "QX_qwen_p1"]
LAB = {"PHEAD": "PHEAD", "BC_klein": "BC_klein", "QX_qwen_p1": "QX"}
CUM = {"PHEAD": 1, "BC_klein": 3, "QX_qwen_p1": 5}
TIERS = [("perfect", "perfect"), ("ok", "ok"), ("fail", "fail")]

CSS = """
:root{--bg:#0d0d10;--fg:#e8e8ea;--dim:#8a8a94;--line:#26262c;--acc:#7c5cff;
 --good:#3fb950;--mid:#d29922;--bad:#f85149}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
 font:14px/1.55 ui-sans-serif,-apple-system,"Segoe UI",Roboto,sans-serif}
header{padding:22px 30px 14px;border-bottom:1px solid var(--line)}
h1{margin:0 0 6px;font-size:20px}
.q{color:var(--acc);font-weight:600}
.sub{color:var(--dim);max-width:92ch;font-size:13px}
.sub code{background:#1b1b22;padding:1px 5px;border-radius:4px}
.sub b{color:var(--fg)}
#bar{position:sticky;top:0;z-index:20;background:#121216;border-bottom:1px solid var(--line);
 padding:11px 30px;display:flex;gap:16px;align-items:center;flex-wrap:wrap;font-size:12.5px}
#bar button{background:#1b1b22;border:1px solid var(--line);color:var(--dim);
 border-radius:7px;padding:6px 13px;font-size:12px;cursor:pointer;font-family:inherit}
#bar button.on{background:var(--acc);border-color:var(--acc);color:#fff;font-weight:600}
#bar button:hover{color:var(--fg)}
#save{background:var(--good);border-color:var(--good);color:#08130a;font-weight:700}
#stats{margin-left:auto;color:var(--dim);text-align:right;line-height:1.7}
#stats b{color:var(--fg)}
.ref{margin:0 30px 18px;border:1px solid var(--line);border-radius:10px;overflow:hidden}
.ref.done{opacity:.55}
.ref.done:hover{opacity:1}
.rh{padding:8px 14px;background:#141419;border-bottom:1px solid var(--line);
 display:flex;gap:12px;align-items:center;flex-wrap:wrap;font-size:13px}
.rh .m{color:var(--dim);font-size:12px}
.pill{font-size:11px;padding:2px 8px;border-radius:20px;border:1px solid var(--line)}
.pill.hd{border-color:var(--mid);color:var(--mid)}
.stop{margin-left:auto;font-size:12px;font-weight:700;color:var(--dim)}
.row{display:flex;align-items:stretch;overflow-x:auto;padding:9px 7px;gap:4px}
.inp{flex:0 0 130px;padding:8px;opacity:.85}
.inp img{width:100%;background:#fff;border-radius:4px;display:block;cursor:zoom-in}
.inp .t{font-size:11px;color:var(--dim);text-align:center;margin-top:4px}
.sep{width:1px;background:var(--line);margin:10px 7px}
.cell{flex:0 0 224px;padding:8px;border:2px solid var(--line);border-radius:9px;
 background:#111116}
.cell img{width:100%;background:#fff;border-radius:4px;display:block;cursor:zoom-in}
.cell .t{font-weight:700;font-size:12.5px;margin:7px 0 5px;display:flex;
 align-items:center;gap:6px}
.cell .t .c{color:var(--dim);font-weight:500;font-size:11px;margin-left:auto}
.tb{display:flex;gap:4px}
.tb button{flex:1;background:#1b1b22;border:1px solid var(--line);color:var(--dim);
 border-radius:6px;padding:5px 0;font-size:11px;cursor:pointer;font-family:inherit;
 font-weight:600}
.tb button:hover{color:var(--fg);border-color:#3a3a44}
.tb button.on[data-t=perfect]{background:var(--good);border-color:var(--good);color:#08130a}
.tb button.on[data-t=ok]{background:var(--mid);border-color:var(--mid);color:#191200}
.tb button.on[data-t=fail]{background:var(--bad);border-color:var(--bad);color:#1c0708}
.cell.perfect{border-color:var(--good)}
.cell.ok{border-color:var(--mid)}
.cell.fail{border-color:var(--bad);opacity:.72}
.cell.ship{box-shadow:0 0 0 3px rgba(63,185,80,.4)}
.cell.unreached{opacity:.34}
.cell .g{font-size:11px;color:var(--acc);display:none;margin-top:5px}
body.showgate .cell .g{display:block}
#lb{display:none;position:fixed;inset:0;background:rgba(0,0,0,.93);z-index:99;
 align-items:center;justify-content:center;flex-direction:column;gap:10px;padding:20px}
#lb.on{display:flex} #lb img{max-width:94vw;max-height:88vh;object-fit:contain;background:#fff}
#lbc{color:var(--dim);font-size:13px}
.legend{padding:12px 30px 2px;color:var(--dim);font-size:12.5px}
.legend b{color:var(--fg)} .legend li{margin:3px 0}
.legend code{background:#1b1b22;padding:1px 5px;border-radius:4px}
"""

JS = """
const D=window.PICK3, ORDER=D.order, CUM=D.cum, KEY='v221_pick3_v1';
let V=JSON.parse(localStorage.getItem(KEY)||'{}');
const id=(s,a)=>'c_'+s+'__'+a;

function paintSet(st){
  const s=st.id;
  let stop=null, marked=0, anyOk=null;
  for(const a of ORDER){
    const v=V[s+'|'+a]||'';
    if(v)marked++;
    if(stop===null&&v==='perfect')stop=a;
    if(anyOk===null&&v==='ok')anyOk=a;
  }
  for(const a of ORDER){
    const el=document.getElementById(id(s,a)); if(!el)continue;
    const v=V[s+'|'+a]||'';
    el.classList.remove('perfect','ok','fail','ship','unreached');
    if(v)el.classList.add(v);
    el.querySelectorAll('.tb button').forEach(b=>
      b.classList.toggle('on',b.dataset.t===v));
    // an arm after the stop point is never reached in production
    if(stop&&ORDER.indexOf(a)>ORDER.indexOf(stop))el.classList.add('unreached');
  }
  const lab=document.getElementById('stop_'+s);
  let cost=0;
  if(stop){
    document.getElementById(id(s,stop)).classList.add('ship');
    lab.textContent='ships '+D.lab[stop]+' \\u2014 '+CUM[stop]+' generations';
    lab.style.color='var(--good)'; cost=CUM[stop];
  }else if(marked>=ORDER.length){
    cost=CUM[ORDER[ORDER.length-1]];
    if(anyOk){lab.textContent='no perfect arm \\u2014 best available is '+D.lab[anyOk]+' (ok)';
      lab.style.color='var(--mid)'}
    else{lab.textContent='every arm failed \\u2014 VLM picks least-bad';
      lab.style.color='var(--bad)'}
  }else{lab.textContent=''}
  document.getElementById('row_'+s).classList.toggle('done',marked>=ORDER.length);
  return {stop,cost,marked,anyOk};
}

function paintAll(){
  let done=0,cost=0,noperf=0,allfail=0,cells=0,ag=0,agn=0;
  const per={}; for(const a of ORDER)per[a]={perfect:0,ok:0,fail:0};
  for(const st of D.sets){
    const r=paintSet(st);
    if(r.marked>=ORDER.length){done++;cost+=r.cost;
      if(!r.stop){noperf++; if(!r.anyOk)allfail++}}
    for(const a of ORDER){
      const v=V[st.id+'|'+a]; if(!v)continue;
      cells++; per[a][v]++;
      if(st.amt[a]){agn++; if(st.amt[a]===v)ag++}
    }
  }
  const n=D.sets.length;
  let s='<b>'+done+'</b> / '+n+' sets complete \\u00b7 <b>'+cells+'</b> / '+(n*3)+' cells';
  if(done)s+='<br><b>'+(cost/done).toFixed(2)+'</b> generations per request \\u00b7 '+
    '<b>'+Math.round(100*(done-noperf)/done)+'%</b> ship a perfect frame \\u00b7 '+
    noperf+' no-perfect ('+allfail+' all-fail \\u2192 VLM)';
  s+='<br>';
  for(const a of ORDER){const t=per[a].perfect+per[a].ok+per[a].fail;
    s+=D.lab[a]+' '+(t?per[a].perfect+'P/'+per[a].ok+'O/'+per[a].fail+'F':'\\u2013')+' &nbsp; '}
  if(agn)s+='<br>matches the old AMT tier on <b>'+Math.round(100*ag/agn)+'%</b> of '+
    agn+' cells';
  document.getElementById('stats').innerHTML=s;
  localStorage.setItem(KEY,JSON.stringify(V));
}

document.addEventListener('click',e=>{
  const b=e.target.closest('.tb button');
  if(b){const c=b.closest('.cell'), k=c.dataset.set+'|'+c.dataset.arm;
    if(V[k]===b.dataset.t)delete V[k]; else V[k]=b.dataset.t;
    paintAll(); return}
  const im=e.target.closest('.cell img,.inp img');
  if(im){document.getElementById('lbi').src=im.getAttribute('src');
    document.getElementById('lbc').textContent=im.getAttribute('alt');
    document.getElementById('lb').classList.add('on')}
});
document.getElementById('lb').addEventListener('click',()=>
  document.getElementById('lb').classList.remove('on'));
document.addEventListener('keydown',e=>{if(e.key==='Escape')
  document.getElementById('lb').classList.remove('on')});
document.getElementById('gt').addEventListener('click',function(){
  document.body.classList.toggle('showgate'); this.classList.toggle('on');
  this.textContent=document.body.classList.contains('showgate')
    ?'gate scores: shown':'gate scores: hidden (blind)';
});
document.getElementById('reset').addEventListener('click',()=>{
  if(confirm('Clear every mark?')){V={};paintAll()}});

document.getElementById('save').addEventListener('click',()=>{
  const head=['set_id','condition','person','garment','arm','order_position',
    'generations_cumulative','tier','ships','reached','hair_over_garment',
    'gate_score','chk_degenerate','chk_noop','chk_people','chk_identity',
    'chk_background','amt_tier_old','binary_usable_old'];
  const rows=[head];
  for(const st of D.sets){
    let stop=null;
    for(const a of ORDER)if(stop===null&&V[st.id+'|'+a]==='perfect')stop=a;
    ORDER.forEach((a,i)=>{
      if(st.gate[a]===undefined)return;
      const c=st.checks[a]||{};
      rows.push([st.id,st.cond,st.person,st.garment,a,i+1,CUM[a],
        V[st.id+'|'+a]||'', stop===a?'1':'0',
        (stop&&ORDER.indexOf(a)>ORDER.indexOf(stop))?'0':'1',
        st.hair.toFixed(4), st.gate[a].toFixed(4),
        c.degenerate,c.noop,c.people,c.identity,c.background,
        st.amt[a]||'', st.bin[a]||'']);
    });
  }
  const csv=rows.map(r=>r.map(x=>'"'+String(x??'').replace(/"/g,'""')+'"').join(',')).join('\\n');
  const u=URL.createObjectURL(new Blob([csv],{type:'text/csv'}));
  const a=document.createElement('a'); a.href=u; a.download='v223_perfect_tier_picks.csv';
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(()=>URL.revokeObjectURL(u),2000);
});
paintAll();
"""


def hair_fracs():
    """Hair over garment = the area C3.1 removes that C3.2 keeps, as a share of C3.2.
    Already on disk from the crop screen -- BiRefNet matte plus the parser hair class."""
    import glob
    import cv2
    d = os.path.join(REPO, "v2", "runs", "crop_screen")
    stems = {os.path.basename(p).split("__c3_no_face_alpha")[0]
             for p in glob.glob(d + "/*__c3_no_face_alpha.png")}
    out = {}
    for st in stems:
        A = cv2.imread(f"{d}/{st}__c3_no_face_alpha.png", cv2.IMREAD_UNCHANGED)
        B = cv2.imread(f"{d}/{st}__c32_no_face_keep_hair_alpha.png", cv2.IMREAD_UNCHANGED)
        if A is None or B is None or A.ndim < 3 or A.shape[2] < 4:
            continue
        a, b = (A[..., 3] > 127).sum(), (B[..., 3] > 127).sum()
        if b:
            out[st] = max(0.0, float(b - a) / float(b))
    return out


def build():
    run = json.load(open(os.path.join(REPO, "v2", "runs", "amt", "_run.json")))
    gate = json.load(open(os.path.join(REPO, "v2", "runs", "amt", "_gate.json")))
    meta = {r["stem"]: r["src_path"] for r in csv.DictReader(
        open(os.path.join(REPO, "v2", "runs", "crop_screen", "crop_log.csv")))}
    T = {"top": "perfect", "mid": "ok", "out": "fail"}
    amt = {}
    for r in csv.DictReader(open(os.path.join(REPO, "v221_attention_mod_rankings (1).csv"))):
        if r.get("tier") in T:
            amt[(r["set_id"], r["arm"])] = T[r["tier"]]
    p = os.path.join(REPO, "v221_phead_verdicts.csv")
    if os.path.exists(p):
        for r in csv.DictReader(open(p)):
            amt[(r["set_id"], "PHEAD")] = r["verdict"]
    binary = {}
    p = os.path.join(REPO, "v223_cheapest_usable_picks.csv")
    if os.path.exists(p):
        for r in csv.DictReader(open(p)):
            binary[(r["set_id"], r["arm"])] = r["my_verdict"]

    HF = hair_fracs()

    def hair_for(g):
        st = next((s for s in HF if s.endswith(g) or s == g), None) \
            or next((s for s in HF if g in s), None)
        return HF.get(st, 0.0)

    def rel(x):
        return os.path.relpath(os.path.join(REPO, x), ART)

    sets, body = [], []
    e = html.escape
    for sid, per, src in run["pairs"]:
        have = [a for a in ORDER if f"{sid}|{a}" in gate and f"{sid}|{a}" in run["gen"]]
        if len(have) < len(ORDER):
            continue
        hd = sid.startswith("HD_")
        sets.append({
            "id": sid, "cond": "high" if hd else "low", "person": per, "garment": src,
            "hair": hair_for(src),
            "gate": {a: gate[f"{sid}|{a}"]["score"] for a in have},
            "checks": {a: gate[f"{sid}|{a}"]["checks"] for a in have},
            "amt": {a: amt.get((sid, a), "") for a in have},
            "bin": {a: binary.get((sid, a), "") for a in have}})

        body.append(
            f"<div class='ref' id='row_{e(sid)}'><div class='rh'><b>{e(sid)}</b>"
            f"<span class='m'>garment {e(src)}</span>"
            f"<span class='m'>hair over garment {hair_for(src):.1%}</span>"
            + ("<span class='pill hd'>HIGH-DAMAGE</span>" if hd else
               "<span class='pill'>low-damage</span>")
            + f"<span class='stop' id='stop_{e(sid)}'></span></div><div class='row'>")
        for who, lab in ((per, "person"), (src, "garment")):
            q = rel(meta.get(who, ""))
            if q and os.path.exists(os.path.normpath(os.path.join(ART, q))):
                body.append(f"<div class='inp'><img src='{q}' alt='{e(sid)} {lab} "
                            f"&mdash; {e(who)}'><div class='t'>{lab}</div></div>")
        body.append("<div class='sep'></div>")
        for i, a in enumerate(have):
            g = gate[f"{sid}|{a}"]
            ch = " · ".join(f"{k[:4]} {v:.2f}" for k, v in sorted(g["checks"].items()))
            btns = "".join(f"<button data-t='{t}'>{nm}</button>" for t, nm in TIERS)
            body.append(
                f"<div class='cell' id='c_{e(sid)}__{a}' data-set='{e(sid)}' "
                f"data-arm='{a}'>"
                f"<img src='../runs/amt/gen/{run['gen'][f'{sid}|{a}']}' "
                f"alt='{e(sid)} &mdash; {LAB[a]}'>"
                f"<div class='t'>{i+1}. {LAB[a]}<span class='c'>{CUM[a]} gen</span></div>"
                f"<div class='tb'>{btns}</div>"
                f"<div class='g'>gate {g['score']:.2f}<br>{ch}</div></div>")
        body.append("</div></div>")

    data = {"sets": sets, "order": ORDER, "cum": CUM, "lab": LAB}
    doc = NL.join([
        "<title>Perfect-tier pick sheet</title>", "<style>" + CSS + "</style>",
        "<header><h1>Perfect-tier pick sheet &mdash; stop on perfect</h1>"
        "<div class='q'>Mark every cell perfect / ok / fail. The cascade stops at the "
        "first <b>perfect</b> arm, not the first tolerable one.</div>"
        "<div class='sub'>This replaces the binary usable/not sheet, which conflated "
        "<i>ship it</i> with <i>acceptable</i> and therefore optimised coverage instead "
        "of quality. It also replaces the old AMT tier as the label of record: AMT "
        "<code>perfect</code> meant <b>tied for first among ten arms</b> &mdash; a "
        "relative ranking &mdash; and an arm can top a weak field without being "
        "shippable, so a relative label cannot drive an absolute stop decision. "
        "Order is <code>PHEAD</code> (1 gen) &rarr; <code>BC_klein</code> (3) &rarr; "
        "<code>QX</code> (5). QX is last deliberately: it exists to route around AI "
        "artefacts, not to produce the best frame.</div></header>",
        "<div id='bar'>"
        "<button id='gt'>gate scores: hidden (blind)</button>"
        "<button id='save'>Save tier CSV</button>"
        "<button id='reset'>Clear all</button>"
        "<span id='stats'></span></div>",
        "<div class='legend'><ul>"
        "<li><b>perfect</b> = you would ship this to a user unchanged. <b>ok</b> = "
        "acceptable but you would rather have something better. <b>fail</b> = "
        "unusable. The distinction between the first two is the whole point of "
        "re-marking &mdash; the previous sheet could not see it.</li>"
        "<li>The green halo is the arm that <b>ships</b>: the first <i>perfect</i> one. "
        "Cells past it dim to show they are never reached in production. <b>Mark them "
        "anyway</b> &mdash; they are the only evidence for whether the ordering is "
        "right.</li>"
        "<li>Judge blind. Gate scores start hidden so your marks are not anchored to "
        "an instrument already measured at AUC 0.506 against you.</li>"
        "<li>The header tracks generations per request, the share of sets shipping a "
        "<b>perfect</b> frame, how many have no perfect arm at all, and how often your "
        "new marks match the old AMT tier &mdash; that last number says whether the "
        "relative ranking was a safe stand-in.</li>"
        "<li>Each row shows <b>hair over garment</b>, the candidate routing feature "
        "(BiRefNet matte minus the parser hair class, already on disk). It predicted "
        "PHEAD failure at AUC 0.918 on the binary marks; the CSV carries it so it can "
        "be re-tested against perfection rather than usability.</li>"
        "</ul></div>"] + body + [
        "<div id='lb'><img id='lbi' alt=''><div id='lbc'></div></div>",
        "<script>window.PICK3=" + json.dumps(data) + ";</script>",
        "<script>" + JS + "</script>"])
    o = os.path.join(ART, "v223_perfect_tier.html")
    open(o, "w", encoding="utf-8").write(doc)
    return o, len(sets)


if __name__ == "__main__":
    print(build())
