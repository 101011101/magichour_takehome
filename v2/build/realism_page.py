# Before/after for the realism pass, over exactly the frames the harness ships.
#
# A drag slider rather than side-by-side thumbnails: SeedVR2's changes are small
# and local (mean absolute pixel change 2.28/255), so two images placed next to
# each other look identical and the reviewer learns nothing. A wipe over the same
# pixels is the only presentation that shows a 2% change.
import json, os, html, statistics as st

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
ART = os.path.join(REPO, "v2", "artifacts")
NL = chr(10)

CSS = """
:root{--bg:#0d0d10;--fg:#e8e8ea;--dim:#8a8a94;--line:#26262c;--acc:#7c5cff;
 --good:#3fb950;--mid:#d29922;--bad:#f85149}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
 font:14px/1.55 ui-sans-serif,-apple-system,"Segoe UI",Roboto,sans-serif}
header{padding:22px 30px 14px;border-bottom:1px solid var(--line)}
h1{margin:0 0 6px;font-size:20px}
.q{color:var(--acc);font-weight:600}
.sub{color:var(--dim);max-width:96ch;font-size:13px;margin-top:6px}
.sub b{color:var(--fg)} .sub code{background:#1b1b22;padding:1px 5px;border-radius:4px}
.panel{margin:16px 30px;border:1px solid var(--line);border-radius:10px;background:#121216}
.panel h2{margin:0;padding:10px 14px;font-size:13px;border-bottom:1px solid var(--line)}
.panel .in{padding:12px 14px}
table{border-collapse:collapse;font-size:12.5px}
th,td{padding:4px 10px;text-align:right;border-bottom:1px solid #1d1d23}
th:first-child,td:first-child{text-align:left}
th{color:var(--dim);font-weight:600}
.win{color:var(--good);font-weight:700}.lose{color:var(--bad);font-weight:700}
.note{color:var(--dim);font-size:12px;margin:9px 0 0;max-width:100ch}
#bar{position:sticky;top:0;z-index:20;background:#121216;border-bottom:1px solid var(--line);
 padding:10px 30px;display:flex;gap:14px;align-items:center;flex-wrap:wrap;font-size:12.5px}
#bar button{background:#1b1b22;border:1px solid var(--line);color:var(--dim);
 border-radius:7px;padding:5px 12px;font-size:12px;cursor:pointer;font-family:inherit}
#bar button.on{background:var(--acc);border-color:var(--acc);color:#fff;font-weight:600}
input[type=range]{width:240px;accent-color:var(--acc)}
#cnt{margin-left:auto;color:var(--dim)}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));
 gap:14px;padding:4px 30px 30px}
/* Size modes. In `full` the frame is height-capped to the viewport so one whole
   image fits the screen -- the point is inspecting faces, and a card you have to
   scroll through vertically defeats that. */
.grid.two{grid-template-columns:repeat(auto-fill,minmax(560px,1fr))}
.grid.full{grid-template-columns:1fr;gap:26px}
.grid.full .card{margin:0 auto;width:max-content;max-width:100%}
.grid.full .wrap{width:max-content;max-width:100%}
.grid.full .wrap>img{max-height:86vh;width:auto;max-width:100%}
.grid.full .cap{font-size:13px}
.card{border:1px solid var(--line);border-radius:10px;overflow:hidden;background:#101014}
.card.idlow{border-color:#5a2a2a}
.wrap{position:relative;overflow:hidden;cursor:ew-resize;background:#fff}
.wrap img{display:block;width:100%}
.wrap .aft{position:absolute;inset:0;overflow:hidden}
.wrap .aft img{position:absolute;top:0;left:0;height:100%;width:auto;max-width:none}
.hand{position:absolute;top:0;bottom:0;width:2px;background:var(--acc);pointer-events:none}
.hand::after{content:'';position:absolute;top:50%;left:-8px;width:18px;height:18px;
 margin-top:-9px;border-radius:50%;background:var(--acc);border:2px solid #fff}
.tagL,.tagR{position:absolute;bottom:6px;font-size:10px;padding:2px 7px;border-radius:4px;
 background:rgba(0,0,0,.72);color:#fff;pointer-events:none}
.tagL{left:6px}.tagR{right:6px}
.cap{padding:8px 11px;font-size:12px}
.cap .sid{font-weight:700;font-size:12px;word-break:break-all}
.cap .m{color:var(--dim);font-size:11.5px;margin-top:3px}
.cap .m b{color:var(--fg)}
.pill{display:inline-block;font-size:10px;padding:1px 7px;border-radius:20px;
 border:1px solid var(--line);margin-right:4px}
.pill.esc{border-color:var(--acc);color:var(--acc)}
.pill.id{border-color:var(--bad);color:var(--bad)}
.zb{position:absolute;top:6px;right:6px;z-index:3;background:rgba(0,0,0,.7);
 color:#fff;border:1px solid rgba(255,255,255,.25);border-radius:6px;
 padding:2px 8px;font-size:11px;cursor:zoom-in;font-family:inherit}
.zb:hover{background:var(--acc)}
#zoom{display:none;position:fixed;inset:0;background:#08080a;z-index:99;
 flex-direction:column}
#zoom.on{display:flex}
#zstage{flex:1;overflow:hidden;position:relative;cursor:grab;
 display:flex;align-items:center;justify-content:center}
#zstage.drag{cursor:grabbing}
#zpan{position:relative;transform-origin:0 0;will-change:transform}
#zpan img{display:block;width:100%;height:auto;background:#fff}
#zaft{position:absolute;top:0;left:0;bottom:0;overflow:hidden}
#zaft img{position:absolute;top:0;left:0;max-width:none}
#zhand{position:absolute;top:0;bottom:0;width:2px;background:var(--acc);
 pointer-events:none}
#zctl{background:#121216;border-top:1px solid var(--line);padding:10px 20px;
 display:flex;gap:16px;align-items:center;flex-wrap:wrap;font-size:12.5px}
#zctl button{background:#1b1b22;border:1px solid var(--line);color:var(--fg);
 border-radius:6px;padding:4px 11px;cursor:pointer;font-family:inherit;font-size:12px}
#zctl button:hover{border-color:var(--acc)}
#ztitle{font-weight:700;font-size:12.5px;word-break:break-all;max-width:44ch}
#zmeta{color:var(--dim)}
#zctl .sp{margin-left:auto;color:var(--dim);font-size:11.5px}
"""

JS = """
function place(w){
  const im=w.querySelector('.aft img'), r=w.getBoundingClientRect();
  if(im) im.style.width=r.width+'px';
}
function setp(w,p){
  p=Math.max(0,Math.min(1,p));
  w.querySelector('.aft').style.width=(p*100)+'%';
  w.querySelector('.hand').style.left=(p*100)+'%';
  w.dataset.p=p;
}
function wire(w){
  place(w); setp(w, parseFloat(w.dataset.p||0.5));
  const move=e=>{const r=w.getBoundingClientRect();
    const x=(e.touches?e.touches[0].clientX:e.clientX)-r.left;
    setp(w,x/r.width);};
  w.addEventListener('mousedown',e=>{move(e);
    const up=()=>{document.removeEventListener('mousemove',move);
      document.removeEventListener('mouseup',up);};
    document.addEventListener('mousemove',move);document.addEventListener('mouseup',up);});
  w.addEventListener('touchmove',e=>{move(e);e.preventDefault();},{passive:false});
}
document.querySelectorAll('.wrap').forEach(wire);
document.querySelectorAll('.wrap > img').forEach(im=>{
  if(!im.complete) im.addEventListener('load',()=>{
    const w=im.closest('.wrap'); place(w); setp(w, parseFloat(w.dataset.p||0.5));});
});
window.addEventListener('resize',()=>document.querySelectorAll('.wrap')
  .forEach(w=>{place(w);setp(w,parseFloat(w.dataset.p||0.5));}));

document.getElementById('all').addEventListener('input',function(){
  const p=this.value/100;
  document.querySelectorAll('.wrap').forEach(w=>setp(w,p));
  document.getElementById('allv').textContent=this.value+'%';
});
const GRID=document.querySelector('.grid');
function relayout(){document.querySelectorAll('.wrap').forEach(w=>{
  place(w); setp(w, parseFloat(w.dataset.p||0.5));});}

document.addEventListener('click',e=>{
  const sb=e.target.closest('#bar button[data-s]');
  if(sb){document.querySelectorAll('#bar button[data-s]').forEach(x=>x.classList.remove('on'));
    sb.classList.add('on');
    GRID.className='grid'+(sb.dataset.s==='grid'?'':' '+sb.dataset.s);
    requestAnimationFrame(relayout); return;}
  const b=e.target.closest('#bar button[data-f]');
  if(!b)return;
  document.querySelectorAll('#bar button[data-f]').forEach(x=>x.classList.remove('on'));
  b.classList.add('on');let n=0;
  document.querySelectorAll('.card').forEach(c=>{
    const f=b.dataset.f;
    const show = f==='all' || (f==='esc'&&c.dataset.esc==='1') ||
                 (f==='id'&&c.classList.contains('idlow'));
    c.style.display=show?'':'none'; if(show)n++;});
  document.getElementById('cnt').textContent=n+' shown';
});
document.getElementById('cnt').textContent=
  document.querySelectorAll('.card').length+' shown';

/* ---- zoom lightbox: wheel zooms at the cursor, drag pans, slider wipes.
   The wipe is a slider rather than a drag because drag is already pan, and
   overloading one gesture with two meanings makes both feel broken. ---- */
const Z={el:document.getElementById('zoom'),stage:document.getElementById('zstage'),
         pan:document.getElementById('zpan'),aft:document.getElementById('zaft'),
         afti:document.querySelector('#zaft img'),
         bef:document.getElementById('zbef'),hand:document.getElementById('zhand'),
         s:1,x:0,y:0,base:0,p:0.5};

function zapply(){
  Z.pan.style.transform='translate('+Z.x+'px,'+Z.y+'px) scale('+Z.s+')';
  document.getElementById('zpct').textContent=Math.round(Z.s*100)+'%';
}
function zwipe(p){
  Z.p=Math.max(0,Math.min(1,p));
  Z.aft.style.width=(Z.p*100)+'%';
  Z.hand.style.left=(Z.p*100)+'%';
  document.getElementById('zwv').textContent=Math.round(Z.p*100)+'%';
}
function zfit(){
  const r=Z.stage.getBoundingClientRect();
  const nw=Z.bef.naturalWidth||1, nh=Z.bef.naturalHeight||1;
  Z.base=Math.min(r.width/nw,(r.height-10)/nh)*nw;
  Z.pan.style.width=Z.base+'px';
  Z.afti.style.width=Z.base+'px';
  Z.s=1;
  Z.x=(r.width-Z.base)/2;
  Z.y=(r.height-Z.base*nh/nw)/2;
  zapply(); zwipe(Z.p);
}
function zopen(card){
  const b=card.querySelector('.wrap > img'), a=card.querySelector('.aft img');
  Z.bef.src=b.getAttribute('src'); Z.afti.src=a.getAttribute('src');
  document.getElementById('ztitle').textContent=
    card.querySelector('.sid').textContent;
  document.getElementById('zmeta').textContent=
    card.querySelectorAll('.m')[1].textContent;
  Z.p=parseFloat(card.querySelector('.wrap').dataset.p||0.5);
  Z.el.classList.add('on');
  if(Z.bef.complete) zfit(); else Z.bef.onload=zfit;
}
function zclose(){Z.el.classList.remove('on');}

document.addEventListener('click',e=>{
  const zb=e.target.closest('.zb');
  if(zb){zopen(zb.closest('.card'));e.stopPropagation();}
});
document.getElementById('zclose').addEventListener('click',zclose);
document.getElementById('zreset').addEventListener('click',zfit);
document.getElementById('zin').addEventListener('click',()=>zstep(1.25));
document.getElementById('zout').addEventListener('click',()=>zstep(1/1.25));
document.getElementById('zwipe').addEventListener('input',function(){
  zwipe(this.value/100);});

function zstep(f,cx,cy){
  const r=Z.stage.getBoundingClientRect();
  if(cx===undefined){cx=r.width/2;cy=r.height/2;}
  const ns=Math.max(0.2,Math.min(12,Z.s*f));
  const k=ns/Z.s;
  Z.x=cx-(cx-Z.x)*k; Z.y=cy-(cy-Z.y)*k; Z.s=ns; zapply();
}
Z.stage.addEventListener('wheel',e=>{
  e.preventDefault();
  const r=Z.stage.getBoundingClientRect();
  zstep(e.deltaY<0?1.12:1/1.12, e.clientX-r.left, e.clientY-r.top);
},{passive:false});
Z.stage.addEventListener('mousedown',e=>{
  e.preventDefault();
  const sx=e.clientX-Z.x, sy=e.clientY-Z.y;
  Z.stage.classList.add('drag');
  const mv=ev=>{Z.x=ev.clientX-sx; Z.y=ev.clientY-sy; zapply();};
  const up=()=>{Z.stage.classList.remove('drag');
    document.removeEventListener('mousemove',mv);
    document.removeEventListener('mouseup',up);};
  document.addEventListener('mousemove',mv); document.addEventListener('mouseup',up);
});
document.addEventListener('keydown',e=>{
  if(!Z.el.classList.contains('on'))return;
  if(e.key==='Escape')zclose();
  else if(e.key==='+'||e.key==='=')zstep(1.25);
  else if(e.key==='-')zstep(1/1.25);
  else if(e.key==='0')zfit();
  else if(e.key==='ArrowLeft')zwipe(Z.p-0.02);
  else if(e.key==='ArrowRight')zwipe(Z.p+0.02);
});
window.addEventListener('resize',()=>{if(Z.el.classList.contains('on'))zfit();});
"""


def build():
    M = json.load(open(f"{REPO}/v2/runs/realism/_metrics.json"))
    D = json.load(open(f"{REPO}/v2/runs/realism/_realism.json"))
    e = html.escape
    idc = [r["identity_cos"] for r in M if r["identity_cos"] is not None]
    low = [r for r in M if r["identity_cos"] is not None and r["identity_cos"] < 0.90]

    tbl = ("<table><tr><th>measure</th><th>value</th></tr>"
           f"<tr><td>frames</td><td>{len(M)}</td></tr>"
           f"<tr><td>resolution</td><td>{M[0]['dim_before']} &rarr; "
           f"{M[0]['dim_after']}</td></tr>"
           f"<tr><td>mean absolute pixel change</td>"
           f"<td>{st.mean(r['mae'] for r in M):.2f} / 255</td></tr>"
           f"<tr><td>high-frequency ratio (after / before)</td>"
           f"<td>{st.mean(r['hf_ratio'] for r in M):.3f}</td></tr>"
           f"<tr><td>identity cosine, mean</td>"
           f"<td class='{'win' if st.mean(idc)>0.95 else 'lose'}'>"
           f"{st.mean(idc):.4f}</td></tr>"
           f"<tr><td>identity cosine, worst</td>"
           f"<td class='lose'>{min(idc):.4f}</td></tr>"
           f"<tr><td>frames below 0.90 identity</td>"
           f"<td class='{'lose' if low else 'win'}'>{len(low)} of {len(idc)}</td></tr>"
           "</table>")

    cards = []
    for r in sorted(M, key=lambda x: (x["identity_cos"] or 1)):
        sid = r["set_id"]
        before = os.path.relpath(D[sid]["src"], ART)
        after = os.path.relpath(os.path.join(REPO, D[sid]["after"]), ART)
        ic = r["identity_cos"]
        idlow = ic is not None and ic < 0.90
        pills = ""
        if r["escalated"]:
            pills += "<span class='pill esc'>escalated &rarr; QX</span>"
        if idlow:
            pills += "<span class='pill id'>identity drift</span>"
        cards.append(
            f"<div class='card{' idlow' if idlow else ''}' "
            f"data-esc='{'1' if r['escalated'] else '0'}'>"
            f"<button class='zb'>zoom</button>"
            f"<div class='wrap' data-p='0.5'>"
            f"<img src='{before}' alt='{e(sid)} before'>"
            f"<div class='aft'><img src='{after}' alt='{e(sid)} after'></div>"
            f"<div class='hand'></div>"
            f"<span class='tagL'>before</span><span class='tagR'>after</span></div>"
            f"<div class='cap'><div class='sid'>{e(sid)}</div>"
            f"<div class='m'>{pills}{r['arm']} &middot; human <b>{r['tier']}</b></div>"
            f"<div class='m'>hf &times;<b>{r['hf_ratio']:.2f}</b> &middot; identity "
            f"<b>{'n/a' if ic is None else format(ic, '.3f')}</b> &middot; "
            f"&Delta;px <b>{r['mae']:.1f}</b></div></div></div>")

    doc = NL.join([
        "<title>Realism pass — before and after</title>",
        "<style>" + CSS + "</style>",
        "<header><h1>Realism pass &mdash; SeedVR2 over what the harness ships</h1>"
        "<div class='q'>Drag any image to wipe between before and after.</div>"
        "<div class='sub'>The harness was replayed over stored arm outputs, the frame "
        "it lands on was taken for each of the 38 sets, and only that frame went "
        "through <code>SeedVR2 &times;2, noise_scale = 0</code> &mdash; the v2.1 "
        "winner. 38 calls, no new generations. <b>This is the first time the v2.1 "
        "realism choice has been applied to a v2.2.3 output</b>, which is the "
        "\"composite never validated end to end\" gap.</div></header>",
        "<div class='panel'><h2>What the pass actually did</h2><div class='in'>" + tbl +
        "<p class='note'><b>The change is small and the identity cost is not.</b> "
        "Mean absolute pixel change is 2.28/255 &mdash; under 1% &mdash; and "
        "high-frequency energy rises only 12%. Against that, mean identity cosine is "
        f"{st.mean(idc):.3f} with a worst case of {min(idc):.3f}, and {len(low)} of "
        f"{len(idc)} frames fall below 0.90. For scale, v2.1 measured this same "
        "configuration at <b>0.943</b> identity on klein outputs and rejected Z-Image "
        "Turbo for dropping to 0.72 &mdash; and the worst frame here is 0.77.</p>"
        "<p class='note'>Read the identity number with care: AuraFace is comparing a "
        "832&times;1248 frame against a 2&times; upscale of itself, so some of the "
        "drop is resampling rather than damage. That is exactly why this page exists "
        "&mdash; <b>the metric cannot settle it and the eye can.</b> Sort order is "
        "worst identity first.</p></div></div>",
        "<div id='bar'>"
        "<button data-f='all' class='on'>all 38</button>"
        "<button data-f='esc'>escalated to QX</button>"
        "<button data-f='id'>identity &lt; 0.90</button>"
        "<span style='color:#8a8a94'>&nbsp;size&nbsp;</span>"
        "<button data-s='grid'>grid</button>"
        "<button data-s='two'>2-up</button>"
        "<button data-s='full' class='on'>full page</button>"
        "<label>wipe all <span id='allv'>50%</span></label>"
        "<input type='range' id='all' min='0' max='100' value='50'>"
        "<span id='cnt'></span></div>",
        "<div class='grid full'>" + "".join(cards) + "</div>",
        "<div id='zoom'><div id='zstage'><div id='zpan'>"
        "<img id='zbef' alt='before'>"
        "<div id='zaft'><img alt='after'></div><div id='zhand'></div>"
        "</div></div>"
        "<div id='zctl'>"
        "<span id='ztitle'></span><span id='zmeta'></span>"
        "<button id='zout'>&minus;</button><span id='zpct'>100%</span>"
        "<button id='zin'>+</button><button id='zreset'>fit</button>"
        "<label>wipe <span id='zwv'>50%</span></label>"
        "<input type='range' id='zwipe' min='0' max='100' value='50'>"
        "<button id='zclose'>close</button>"
        "<span class='sp'>scroll to zoom &middot; drag to pan &middot; "
        "&larr;&rarr; wipe &middot; 0 fit &middot; Esc close</span></div></div>",
        "<script>" + JS + "</script>"])
    o = os.path.join(ART, "v223_realism_pass.html")
    open(o, "w", encoding="utf-8").write(doc)
    return o, len(M)


if __name__ == "__main__":
    print(build())
