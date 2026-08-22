# Cheapest-usable pick sheet.
#
# Three arms per set in ascending cost -- PHEAD (1 generation, free preprocessing),
# BC_klein (2: bald pass + try-on), QX (2: extract pass + try-on) -- and the reviewer
# marks each one usable or not. The cheapest usable arm is the one the pipeline would
# ship, so the sheet produces both a per-cell verdict and a per-set stop point.
#
# Gate scores are HIDDEN by default. The point of the exercise is to compare the
# reviewer against the grader, and a visible score anchors the reviewer -- which would
# manufacture the agreement the sheet is meant to measure.
import csv, html, json, os

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
ART = os.path.join(REPO, "v2", "artifacts")
NL = chr(10)

# Ray's ordering: BC_klein before QX. BC solves PHEAD's failure mode directly, QX is
# the fallback for what BC cannot do. Note this is NOT the cost-optimal order measured
# in RESULTS.md -- PHEAD -> QX -> BC came out at 1.421 units against 1.526 -- because
# QX converts more cases on the first escalation. Both cost the same per call, so the
# order only changes expected spend, not coverage; this sheet re-measures it anyway.
ORDER = ["PHEAD", "BC_klein", "QX_qwen_p1"]
LAB = {"PHEAD": "PHEAD", "BC_klein": "BC_klein", "QX_qwen_p1": "QX"}
GENS = {"PHEAD": 1, "BC_klein": 2, "QX_qwen_p1": 2}          # generations to produce
CUM = {"PHEAD": 1, "BC_klein": 3, "QX_qwen_p1": 5}           # cumulative if cascaded

CSS = """
:root{--bg:#0d0d10;--fg:#e8e8ea;--dim:#8a8a94;--line:#26262c;--acc:#7c5cff;
 --good:#3fb950;--bad:#f85149;--mid:#d29922}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
 font:14px/1.55 ui-sans-serif,-apple-system,"Segoe UI",Roboto,sans-serif}
header{padding:22px 30px 14px;border-bottom:1px solid var(--line)}
h1{margin:0 0 6px;font-size:20px}
.q{color:var(--acc);font-weight:600}
.sub{color:var(--dim);max-width:88ch;font-size:13px}
.sub code{background:#1b1b22;padding:1px 5px;border-radius:4px}
#bar{position:sticky;top:0;z-index:20;background:#121216;border-bottom:1px solid var(--line);
 padding:11px 30px;display:flex;gap:18px;align-items:center;flex-wrap:wrap;font-size:12.5px}
#bar button{background:#1b1b22;border:1px solid var(--line);color:var(--dim);
 border-radius:7px;padding:6px 13px;font-size:12px;cursor:pointer;font-family:inherit}
#bar button.on{background:var(--acc);border-color:var(--acc);color:#fff;font-weight:600}
#bar button:hover{color:var(--fg)}
#save{background:var(--good);border-color:var(--good);color:#08130a;font-weight:700}
#stats{margin-left:auto;color:var(--dim);text-align:right;line-height:1.65}
#stats b{color:var(--fg)}
.ref{margin:0 30px 18px;border:1px solid var(--line);border-radius:10px;overflow:hidden}
.rh{padding:8px 14px;background:#141419;border-bottom:1px solid var(--line);
 display:flex;gap:12px;align-items:center;flex-wrap:wrap;font-size:13px}
.rh .m{color:var(--dim);font-size:12px}
.pill{font-size:11px;padding:2px 8px;border-radius:20px;border:1px solid var(--line)}
.pill.hd{border-color:var(--mid);color:var(--mid)}
.stop{margin-left:auto;font-size:12px;font-weight:700;color:var(--dim)}
.row{display:flex;align-items:stretch;overflow-x:auto;padding:9px 7px;gap:4px}
.inp{flex:0 0 132px;padding:8px;opacity:.85}
.inp img{width:100%;background:#fff;border-radius:4px;display:block;cursor:zoom-in}
.inp .t{font-size:11px;color:var(--dim);text-align:center;margin-top:4px}
.sep{width:1px;background:var(--line);margin:10px 7px}
.cell{flex:0 0 216px;padding:8px;border:2px solid var(--line);border-radius:9px;
 cursor:pointer;user-select:none;background:#111116}
.cell img{width:100%;background:#fff;border-radius:4px;display:block}
.cell .t{font-weight:700;font-size:12.5px;margin:7px 0 1px;display:flex;
 align-items:center;gap:6px}
.cell .t .c{color:var(--dim);font-weight:500;font-size:11px;margin-left:auto}
.cell .v{font-size:11.5px;color:var(--dim);min-height:16px}
.cell .g{font-size:11px;color:var(--acc);display:none}
body.showgate .cell .g{display:block}
.cell.u{border-color:var(--good);background:#0f1a11}
.cell.n{border-color:var(--bad);background:#1a0f10;opacity:.7}
.cell.ship{box-shadow:0 0 0 3px rgba(63,185,80,.35)}
.cell .zi{float:right;font-size:11px;color:var(--dim);border:1px solid var(--line);
 border-radius:4px;padding:0 5px;margin-left:6px}
#lb{display:none;position:fixed;inset:0;background:rgba(0,0,0,.93);z-index:99;
 align-items:center;justify-content:center;flex-direction:column;gap:10px;padding:20px}
#lb.on{display:flex} #lb img{max-width:94vw;max-height:88vh;object-fit:contain;background:#fff}
#lbc{color:var(--dim);font-size:13px}
.legend{padding:12px 30px 2px;color:var(--dim);font-size:12.5px}
.legend b{color:var(--fg)} .legend li{margin:3px 0}
"""

JS = """
const D=window.PICK, ORDER=D.order, CUM=D.cum;
const KEY='v221_pick_v1';
let V=JSON.parse(localStorage.getItem(KEY)||'{}');

function cellId(s,a){return 'c_'+s+'__'+a}

function paintSet(s){
  let stop=null, cost=0, marked=0;
  for(const a of ORDER){
    const el=document.getElementById(cellId(s,a)); if(!el) continue;
    const v=V[s+'|'+a]||'';
    el.classList.toggle('u',v==='usable');
    el.classList.toggle('n',v==='unusable');
    el.classList.remove('ship');
    el.querySelector('.v').textContent = v?('marked '+v):'unmarked \\u2014 click to judge';
    if(v) marked++;
    if(stop===null&&v==='usable') stop=a;
  }
  const lab=document.getElementById('stop_'+s);
  if(stop){
    document.getElementById(cellId(s,stop)).classList.add('ship');
    lab.textContent='ships '+D.lab[stop]+' \\u2014 '+CUM[stop]+' generations';
    lab.style.color='var(--good)'; cost=CUM[stop];
  }else if(marked>=ORDER.length){
    lab.textContent='no usable arm'; lab.style.color='var(--bad)'; cost=CUM[ORDER[ORDER.length-1]];
  }else{ lab.textContent=''; cost=0 }
  return {stop,cost,marked};
}

function paintAll(){
  let done=0,cost=0,none=0,cells=0,agree=0,cmp=0;
  const per={};
  for(const a of ORDER) per[a]={u:0,n:0};
  for(const st of D.sets){
    const r=paintSet(st.id);
    if(r.marked>=ORDER.length||r.stop){done++;cost+=r.cost}
    if(r.marked>=ORDER.length&&!r.stop)none++;
    for(const a of ORDER){
      const v=V[st.id+'|'+a]; if(!v) continue;
      cells++; per[a][v==='usable'?'u':'n']++;
      const g=st.gate[a];
      if(g!==undefined){cmp++; if((g>=D.th)===(v==='usable'))agree++}
    }
  }
  const n=D.sets.length;
  let s='<b>'+done+'</b> / '+n+' sets decided \\u00b7 <b>'+cells+'</b> cells marked';
  if(done)s+='<br><b>'+(cost/done).toFixed(2)+'</b> generations per request \\u00b7 '+
    none+' with no usable arm';
  s+='<br>';
  for(const a of ORDER){const t=per[a].u+per[a].n;
    s+=D.lab[a]+' '+(t?Math.round(100*per[a].u/t)+'% usable':'\\u2013')+' &nbsp; '}
  if(cmp)s+='<br>grader agrees on <b>'+Math.round(100*agree/cmp)+'%</b> of '+cmp+
    ' marked cells (at '+D.th+')';
  document.getElementById('stats').innerHTML=s;
  localStorage.setItem(KEY,JSON.stringify(V));
}

document.addEventListener('click',e=>{
  const z=e.target.closest('.zi');
  if(z){const im=z.closest('.cell,.inp').querySelector('img');
    document.getElementById('lbi').src=im.getAttribute('src');
    document.getElementById('lbc').textContent=im.getAttribute('alt');
    document.getElementById('lb').classList.add('on');e.stopPropagation();return}
  if(e.target.closest('.inp')){const im=e.target.closest('.inp').querySelector('img');
    document.getElementById('lbi').src=im.getAttribute('src');
    document.getElementById('lbc').textContent=im.getAttribute('alt');
    document.getElementById('lb').classList.add('on');return}
  const c=e.target.closest('.cell');
  if(!c)return;
  const k=c.dataset.set+'|'+c.dataset.arm, cur=V[k]||'';
  V[k]= cur===''?'usable': cur==='usable'?'unusable':'';
  if(!V[k])delete V[k];
  paintAll();
});
document.getElementById('lb').addEventListener('click',()=>
  document.getElementById('lb').classList.remove('on'));
document.addEventListener('keydown',e=>{if(e.key==='Escape')
  document.getElementById('lb').classList.remove('on')});

document.getElementById('gt').addEventListener('click',function(){
  document.body.classList.toggle('showgate');
  this.classList.toggle('on');
  this.textContent=document.body.classList.contains('showgate')
    ?'gate scores: shown':'gate scores: hidden (blind)';
});
document.getElementById('reset').addEventListener('click',()=>{
  if(confirm('Clear every mark?')){V={};paintAll()}});

document.getElementById('save').addEventListener('click',()=>{
  const head=['set_id','condition','person','garment','arm','order_position',
    'generations_cumulative','my_verdict','ships','gate_score','gate_weakest',
    'chk_degenerate','chk_noop','chk_people','chk_identity','chk_background',
    'amt_tier','phead_verdict'];
  const rows=[head];
  for(const st of D.sets){
    let stop=null;
    for(const a of ORDER)if(stop===null&&V[st.id+'|'+a]==='usable')stop=a;
    ORDER.forEach((a,i)=>{
      if(st.gate[a]===undefined)return;
      const c=st.checks[a]||{};
      rows.push([st.id,st.cond,st.person,st.garment,a,i+1,CUM[a],
        V[st.id+'|'+a]||'',stop===a?'1':'0',
        st.gate[a].toFixed(4),st.weakest[a]||'',
        (c.degenerate??'').toString().slice(0,6),(c.noop??'').toString().slice(0,6),
        (c.people??'').toString().slice(0,6),(c.identity??'').toString().slice(0,6),
        (c.background??'').toString().slice(0,6),
        st.human[a]||'', st.human['PHEAD']||'']);
    });
  }
  const csv=rows.map(r=>r.map(x=>'"'+String(x).replace(/"/g,'""')+'"').join(',')).join('\\n');
  const b=new Blob([csv],{type:'text/csv'});
  const u=URL.createObjectURL(b), a=document.createElement('a');
  a.href=u; a.download='v223_cheapest_usable_picks.csv';
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(()=>URL.revokeObjectURL(u),2000);
});

paintAll();
"""


def build():
    run = json.load(open(os.path.join(REPO, "v2", "runs", "amt", "_run.json")))
    gate = json.load(open(os.path.join(REPO, "v2", "runs", "amt", "_gate.json")))
    meta = {r["stem"]: r["src_path"] for r in csv.DictReader(
        open(os.path.join(REPO, "v2", "runs", "crop_screen", "crop_log.csv")))}
    T = {"top": "perfect", "mid": "ok", "out": "fail"}
    human = {}
    for r in csv.DictReader(open(os.path.join(REPO, "v221_attention_mod_rankings (1).csv"))):
        if r.get("tier") in T:
            human[(r["set_id"], r["arm"])] = T[r["tier"]]
    p = os.path.join(REPO, "v221_phead_verdicts.csv")
    if os.path.exists(p):
        for r in csv.DictReader(open(p)):
            human[(r["set_id"], "PHEAD")] = r["verdict"]

    def rel(x):
        return os.path.relpath(os.path.join(REPO, x), ART)

    sets, body = [], []
    for sid, per, src in run["pairs"]:
        have = [a for a in ORDER if f"{sid}|{a}" in gate
                and f"{sid}|{a}" in run["gen"]]
        if len(have) < len(ORDER):
            continue
        hd = sid.startswith("HD_")
        e = html.escape
        sets.append({
            "id": sid, "cond": "high" if hd else "low", "person": per, "garment": src,
            "gate": {a: gate[f"{sid}|{a}"]["score"] for a in have},
            "checks": {a: gate[f"{sid}|{a}"]["checks"] for a in have},
            "weakest": {a: gate[f"{sid}|{a}"].get("weakest", "") for a in have},
            "human": {a: human.get((sid, a), "") for a in have}})

        body.append(
            f"<div class='ref'><div class='rh'><b>{e(sid)}</b>"
            f"<span class='m'>garment {e(src)}</span>"
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
            body.append(
                f"<div class='cell' id='c_{e(sid)}__{a}' data-set='{e(sid)}' "
                f"data-arm='{a}'>"
                f"<img src='../runs/amt/gen/{run['gen'][f'{sid}|{a}']}' "
                f"alt='{e(sid)} &mdash; {LAB[a]}'>"
                f"<div class='t'>{i+1}. {LAB[a]}<span class='zi'>zoom</span>"
                f"<span class='c'>{CUM[a]} gen</span></div>"
                f"<div class='v'></div>"
                f"<div class='g'>gate {g['score']:.2f} &middot; weakest "
                f"{g.get('weakest','')}<br>{ch}</div></div>")
        body.append("</div></div>")

    data = {"sets": sets, "order": ORDER, "cum": CUM, "lab": LAB, "th": 0.5}
    doc = NL.join([
        "<title>Cheapest usable arm</title>", "<style>" + CSS + "</style>",
        "<header><h1>Cheapest usable arm &mdash; pick sheet</h1>"
        "<div class='q'>Three arms per set, ordered by cost. Mark each usable or not; "
        "the cheapest usable one is what ships.</div>"
        "<div class='sub'>Order is <code>PHEAD</code> (1 generation, parser head "
        "removal, no extra model call) &rarr; <code>BC_klein</code> (3 cumulative "
        "&mdash; a bald pass then the try-on) &rarr; <code>QX</code> (5 cumulative "
        "&mdash; a Qwen extraction then the try-on). BC_klein sits second because it "
        "attacks PHEAD's failure mode directly; QX is the fallback for what "
        "subtraction cannot recover. Click a cell to cycle "
        "<b>unmarked &rarr; usable &rarr; unusable</b>. Marks persist in this "
        "browser.</div></header>",
        "<div id='bar'>"
        "<button id='gt'>gate scores: hidden (blind)</button>"
        "<button id='save'>Save picks CSV</button>"
        "<button id='reset'>Clear all</button>"
        "<span id='stats'></span></div>",
        "<div class='legend'><ul>"
        "<li><b>Judge blind.</b> The gate's scores start hidden on purpose &mdash; the "
        "whole point is to find out whether the grader sees what you see, and a "
        "visible score would anchor you into agreeing with it. Mark everything first, "
        "then reveal.</li>"
        "<li>The green halo marks the arm that <b>ships</b>: the first usable one "
        "going down the list. Mark all three even after you find a usable one &mdash; "
        "the cells past the stop point are what say whether the ordering is right.</li>"
        "<li>The header tracks <b>generations per request</b> under your picks, each "
        "arm's usable rate, and live agreement with the grader at threshold 0.5.</li>"
        "<li>The CSV carries your verdict beside the gate score, all five sub-scores "
        "and the earlier AMT tier, so the grader can be scored against you per cell.</li>"
        "</ul></div>"] + body + [
        "<div id='lb'><img id='lbi' alt=''><div id='lbc'></div></div>",
        "<script>window.PICK=" + json.dumps(data) + ";</script>",
        "<script>" + JS + "</script>"])
    o = os.path.join(ART, "v223_cheapest_usable.html")
    open(o, "w", encoding="utf-8").write(doc)
    return o, len(sets)


if __name__ == "__main__":
    print(build())
