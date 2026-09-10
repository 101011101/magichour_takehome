"""Build the head-to-head page: `BC` against `ER`, one word apart, 150 cells.

Two columns and one question per cell. `BC` is the archived iron-man-2 cell; `ER` is the
same two images, the same seed, the same canvas, the same A100, with one verb changed in
call 2. Nothing else on the page, because nothing else is being decided: `EFR`, `EX`, `ERD`
and `ERS` are on `v36_a100.html` and stay there.

Two independent marks per cell, and they do different jobs:

  which is better   ER / same / BC   - the verdict. Three keys, or three buttons.
  showcase          a star           - "this cell shows the difference" - the shortlist the
                                       report's figures get picked from, kept apart from the
                                       verdict so a striking cell cannot inflate a count

The tally splits by `BC`'s own record, because a win on a cell `BC` already failed and a win
on one it passed mean different things.

  python3 v3/build/v36_ervbc_page.py     ->  v3/report/v36_er_vs_bc.html
"""
import csv
import html
import json
import os
import sys

from PIL import Image

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "v3", "colab", "lib"))
import run_v36 as V                   # noqa: E402  the prompts as the runner defines them

RUN = os.path.join(REPO, "v3", "runs", "v36", "a100")
REPORT = os.path.join(REPO, "v3", "report")
IMG = os.path.join(REPORT, "img_v36e")


def web(src, dst, width=520):
    if not os.path.exists(src):
        return None, None
    out, full = os.path.join(IMG, dst), os.path.join(IMG, dst.replace(".jpg", "@full.jpg"))
    im = None
    if not os.path.exists(out):
        im = Image.open(src).convert("RGB")
        t = im.resize((width, int(im.height * width / im.width)), Image.LANCZOS) if im.width > width else im
        t.save(out, quality=90, optimize=True)
    if not os.path.exists(full):
        im = im or Image.open(src).convert("RGB")
        im.save(full, quality=94, optimize=True)
    return "img_v36e/" + dst, "img_v36e/" + os.path.basename(full)


def main():
    os.makedirs(IMG, exist_ok=True)
    meta = json.load(open(os.path.join(RUN, "meta", "cost_v36.json")))
    rows = list(csv.DictReader(open(os.path.join(RUN, "v36_editset.csv"))))

    cards = []
    for r in rows:
        sid, p, g, s, bc = r["set_id"], r["person"], r["garment"], r["seed"], r["bc"]
        pt, pf = web(os.path.join(RUN, "inputs", f"{p}.jpg"), f"{p}__person.jpg", 300)
        rt, rf = web(os.path.join(RUN, "refs", f"{g}__BC.jpg"), f"{g}__ref.jpg", 300)
        cols = []
        for arm, lab, note in (("E0", "BC", "the shipped prompt &mdash; <i>dress the person in&hellip;</i>"),
                               ("ER", "ER", "one verb changed &mdash; <i>replace the clothing with&hellip;</i>")):
            t, f = web(os.path.join(RUN, "gen", f"{sid}__{arm}__s{s}.jpg"), f"{sid}__{arm}__s{s}.jpg")
            if not t:
                continue
            cols.append(f"<figure class='out'><div class='ah'><b>{lab}</b><span>{note}</span></div>"
                        f"<img src='{t}' data-full='{f}' alt='{html.escape(sid)} {lab} s{s}' "
                        "loading='lazy'></figure>")
        cards.append(
            f"<div class='card' data-sid='{html.escape(sid)}' data-seed='{s}' data-bc='{bc}'>"
            f"<div class='ch'><b>{html.escape(sid)}</b><span class='t'>seed {s}</span>"
            f"<span class='b b-{bc}'>BC {bc}</span>"
            "<span class='marks'>"
            "<button class='v' data-v='ER'>ER better</button>"
            "<button class='v' data-v='same'>same</button>"
            "<button class='v' data-v='BC'>BC better</button>"
            "<button class='star' title='shows the difference - shortlist for the report'>&#9733;</button>"
            "</span></div>"
            "<div class='body'><div class='src'>"
            f"<figure><img src='{pt}' data-full='{pf}' alt='{html.escape(p)} person' "
            "loading='lazy'><figcaption>the person (image 1)</figcaption></figure>"
            f"<figure><img src='{rt}' data-full='{rf}' alt='{html.escape(g)} BC reference' "
            "loading='lazy'><figcaption>the reference (image 2)</figcaption></figure>"
            f"</div><div class='outs'>{''.join(cols)}</div></div></div>")

    o = [HEAD, "<div class='wrap'>", LEDE,
         "<div class='prompts'>"
         f"<div class='pr'><b>BC</b><code>{html.escape(V.E0)}</code></div>"
         f"<div class='pr'><b>ER</b><code>{html.escape(V.ER)}</code></div>"
         "</div>", BAR,
         f"<div class='grid'>{''.join(cards)}</div>",
         f"<footer>{len(rows)} cells &middot; <code>BC</code> is the archived iron-man-2 cell; "
         f"<code>ER</code> is the same two images, seed and canvas on "
         f"{html.escape(meta['klein']['gpu'])}, one verb changed &middot; call 2 only: "
         f"{html.escape(meta['reference'])} &middot; set: "
         f"{html.escape(meta['set_definition'])} &middot; the other four arms are on "
         "<code>v36_a100.html</code> &middot; rebuild: "
         "<code>python3 v3/build/v36_ervbc_page.py</code>.</footer></div>", LB, SCRIPT]
    open(os.path.join(REPORT, "v36_er_vs_bc.html"), "w").write("\n".join(o))
    print(f"v3/report/v36_er_vs_bc.html  ({len(rows)} cells, BC vs ER)")


HEAD = """<title>BC against ER - one word apart</title>
<meta name='viewport' content='width=device-width,initial-scale=1'>
<style>
:root{--bg:#0d0d10;--fg:#e8e8ea;--dim:#8a8a94;--line:#26262c;--acc:#7c5cff;--red:#8a2b34;
 --grn:#2c5c33;--gold:#d29922}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
 font:15px/1.6 ui-sans-serif,-apple-system,"Segoe UI",Roboto,sans-serif}
.wrap{max-width:1500px;margin:0 auto;padding:24px 20px 0}
h1{margin:0 0 2px;font-size:24px}
.lede{color:var(--dim);max-width:92ch;font-size:14px;margin:6px 0 12px}
.lede b{color:var(--fg)}
.lede kbd{background:#1b1b22;border:1px solid var(--line);border-bottom-width:2px;
 border-radius:4px;padding:0 5px;font:11px ui-monospace,monospace;color:var(--fg)}
.prompts{display:grid;gap:6px;margin:0 0 4px}
.pr{display:grid;grid-template-columns:34px 1fr;gap:8px;align-items:start;font-size:12.5px}
.pr b{color:var(--acc);font:12.5px ui-monospace,monospace}
.pr code{background:#15151b;border:1px solid var(--line);border-radius:6px;padding:5px 8px;
 color:#c3c3ce;font:12px/1.55 ui-monospace,monospace;display:block}
#bar{position:sticky;top:0;z-index:40;display:flex;gap:10px;align-items:center;flex-wrap:wrap;
 padding:10px 13px;margin:12px 0 0;background:#141419;border:1px solid var(--line);
 border-radius:9px;font-size:13px}
#bar button{background:#101014;color:var(--fg);border:1px solid var(--line);border-radius:20px;
 padding:4px 12px;cursor:pointer;font:12px ui-sans-serif,sans-serif}
#bar button.on{background:var(--acc);border-color:var(--acc);color:#fff}
#tally{margin-left:auto;font:12px ui-monospace,monospace;display:grid;gap:2px;text-align:right}
#tally .hd{color:var(--dim)}
#tally b{color:#7ee787}
.grid{display:grid;grid-template-columns:1fr;gap:10px;margin-top:14px}
.card{border:1px solid var(--line);border-radius:9px;background:#101014;overflow:hidden}
.card.cur{border-color:var(--acc)}
.card.star{box-shadow:inset 3px 0 0 var(--gold)}
.ch{display:flex;gap:8px;align-items:center;padding:6px 11px;background:#141419;
 border-bottom:1px solid var(--line);font-size:12px;flex-wrap:wrap}
.ch b{font-size:12.5px;word-break:break-all}
.t{font-size:9.5px;padding:1px 7px;border-radius:20px;background:#2a1a12;
 border:1px solid #6b4423;color:var(--gold)}
.b{font:10px ui-monospace,monospace;padding:1px 8px;border-radius:20px;border:1px solid var(--line)}
.b-fail{background:#2d1418;border-color:#8a2b34;color:#ff9aa2}
.b-ok{background:#12240f;border-color:var(--grn);color:#7ee787}
.marks{margin-left:auto;display:flex;gap:5px}
.marks button{background:#101014;color:var(--dim);border:1px solid var(--line);
 border-radius:20px;padding:2px 11px;cursor:pointer;font:11px ui-sans-serif,sans-serif}
.marks button.on[data-v="ER"]{background:#12240f;border-color:var(--grn);color:#7ee787}
.marks button.on[data-v="same"]{background:#1b1b22;border-color:#4a4a55;color:var(--fg)}
.marks button.on[data-v="BC"]{background:#2d1418;border-color:#8a2b34;color:#ff9aa2}
.marks button.star.on{background:#2a2110;border-color:#6b4423;color:var(--gold)}
.body{display:grid;grid-template-columns:300px 1fr;gap:10px;padding:7px}
@media(max-width:1000px){.body{grid-template-columns:1fr}}
.src{display:grid;grid-template-columns:repeat(2,1fr);gap:5px;align-content:start}
.outs{display:grid;grid-template-columns:repeat(2,1fr);gap:8px}
figure{margin:0}
figure img{width:100%;display:block;background:#fff;border-radius:5px;cursor:zoom-in;
 aspect-ratio:3/4;object-fit:contain}
.src figure img{aspect-ratio:2/3}
.ah{display:flex;gap:7px;align-items:baseline;padding:1px 3px 4px;font-size:12px}
.ah b{font:12px ui-monospace,monospace}
.ah span{color:var(--dim);font-size:11px}
figcaption{font-size:10.5px;color:var(--dim);text-align:center;padding:3px 2px}
#lb{display:none;position:fixed;inset:0;background:rgba(0,0,0,.95);z-index:99;
 align-items:center;justify-content:center;flex-direction:column;gap:10px;padding:20px}
#lb.on{display:flex}#lb img{max-width:95vw;max-height:90vh;object-fit:contain;background:#fff}
#lbc{color:var(--dim);font-size:13px}
footer{border-top:1px solid var(--line);margin-top:34px;padding:20px 0 30px;color:var(--dim);font-size:12.5px}
code{background:#1b1b22;padding:1px 5px;border-radius:4px;font-size:12px}
textarea{display:none;width:100%;height:150px;margin-top:10px;background:#0b0b0e;color:#c3c3ce;
 border:1px solid var(--line);border-radius:6px;font:12px ui-monospace,monospace;padding:8px}
</style>
<div class='wrap'><h1><code>BC</code> against <code>ER</code> &mdash; one word apart</h1></div>
"""

LEDE = """<p class='lede'>Two columns, one question. Both cells were made from <b>the same
two images</b>, at the same seed, on the same canvas, on the same A100 &mdash; the only
difference is the verb in call 2. Mark <b>which one you would ship</b>; star the cells that
<b>show the difference</b>, which is the shortlist the report's figures come from. The star
is kept apart from the verdict on purpose, so a striking cell cannot quietly inflate a count.
Keyboard: <kbd>1</kbd> ER &middot; <kbd>2</kbd> same &middot; <kbd>3</kbd> BC &middot;
<kbd>s</kbd> star &middot; <kbd>j</kbd>/<kbd>k</kbd> next and previous. Marks live in this
browser. Click any image for full size.</p>"""

BAR = """<div id='bar'>
<button id='jump'>jump to first unmarked</button>
<button id='f-all' class='on'>all 150</button>
<button id='f-fail'>the 29 BC failures</button>
<button id='f-ok'>the 121 BC passes</button>
<button id='f-star'>starred</button>
<button id='export'>Export CSV</button>
<button id='reset'>clear marks</button>
<span id='tally'></span></div><textarea id='csvbox'></textarea>"""

LB = "<div id='lb'><img id='lbi' alt=''><div id='lbc'></div></div>"
SCRIPT = """<script>
document.addEventListener('click',e=>{const im=e.target.closest('figure img');
  if(!im)return;document.getElementById('lbi').src=im.dataset.full||im.getAttribute('src');
  document.getElementById('lbc').textContent=im.getAttribute('alt');
  document.getElementById('lb').classList.add('on');});
document.getElementById('lb').addEventListener('click',()=>
  document.getElementById('lb').classList.remove('on'));
document.addEventListener('keydown',e=>{if(e.key==='Escape')
  document.getElementById('lb').classList.remove('on')});

const KEY='v36-er-vs-bc-v1';let m={};try{m=JSON.parse(localStorage.getItem(KEY)||'{}')}catch(e){}
const cards=[...document.querySelectorAll('.card')];
const key=c=>c.dataset.sid+'|'+c.dataset.seed;
let cur=0;
const save=()=>{try{localStorage.setItem(KEY,JSON.stringify(m))}catch(x){}};
function paint(){
 cards.forEach((c,i)=>{const v=m[key(c)]||{};
  c.classList.toggle('cur',i===cur);
  c.classList.toggle('star',!!v.star);
  c.querySelectorAll('.marks button').forEach(b=>{
   b.classList.toggle('on', b.classList.contains('star') ? !!v.star : v.verdict===b.dataset.v);});});
 const n=(bc,v)=>cards.filter(c=>c.dataset.bc===bc&&(m[key(c)]||{}).verdict===v).length;
 const line=bc=>{const t=cards.filter(c=>c.dataset.bc===bc).length;
  const done=cards.filter(c=>c.dataset.bc===bc&&(m[key(c)]||{}).verdict).length;
  return '<div>'+(bc==='fail'?'the 29 BC failures':'the 121 BC passes')
   +' &nbsp; ER <b>'+n(bc,'ER')+'</b> &nbsp; same '+n(bc,'same')
   +' &nbsp; BC <b>'+n(bc,'BC')+'</b> &nbsp; <span class="hd">('+done+'/'+t+' marked)</span></div>';};
 const stars=cards.filter(c=>(m[key(c)]||{}).star).length;
 document.getElementById('tally').innerHTML=line('fail')+line('ok')
  +'<div class="hd">'+stars+' starred for the report</div>';}
function set(c,v){const k=key(c);m[k]=m[k]||{};
 m[k].verdict=(m[k].verdict===v)?undefined:v;save();paint();}
function star(c){const k=key(c);m[k]=m[k]||{};m[k].star=!m[k].star;save();paint();}
document.addEventListener('click',e=>{
 const b=e.target.closest('.marks button');if(!b)return;
 const c=b.closest('.card');cur=cards.indexOf(c);
 b.classList.contains('star')?star(c):set(c,b.dataset.v);});
function go(i){const vis=cards.filter(c=>c.style.display!=='none');
 if(!vis.length)return;cur=cards.indexOf(vis[Math.max(0,Math.min(vis.length-1,i))]);
 cards[cur].scrollIntoView({behavior:'smooth',block:'center'});paint();}
document.addEventListener('keydown',e=>{
 if(e.target.tagName==='TEXTAREA')return;
 const vis=cards.filter(c=>c.style.display!=='none');const at=vis.indexOf(cards[cur]);
 if(e.key==='1')set(cards[cur],'ER'); else if(e.key==='2')set(cards[cur],'same');
 else if(e.key==='3')set(cards[cur],'BC'); else if(e.key==='s')star(cards[cur]);
 else if(e.key==='j')go(at+1); else if(e.key==='k')go(at-1); else return;
 e.preventDefault();});
function filter(which,btn){
 cards.forEach(c=>c.style.display=(which==='all'||(which==='star'?(m[key(c)]||{}).star:c.dataset.bc===which))?'':'none');
 ['f-all','f-fail','f-ok','f-star'].forEach(i=>document.getElementById(i).classList.remove('on'));
 btn.classList.add('on');}
document.getElementById('f-all').onclick=e=>filter('all',e.target);
document.getElementById('f-fail').onclick=e=>filter('fail',e.target);
document.getElementById('f-ok').onclick=e=>filter('ok',e.target);
document.getElementById('f-star').onclick=e=>filter('star',e.target);
document.getElementById('jump').onclick=()=>{
 const vis=cards.filter(c=>c.style.display!=='none');
 const c=vis.find(x=>!(m[key(x)]||{}).verdict);
 if(c){cur=cards.indexOf(c);c.scrollIntoView({behavior:'smooth',block:'center'});paint();}
 else alert('every visible cell has a verdict');};
document.getElementById('reset').onclick=()=>{
 if(!confirm('clear every mark?'))return;m={};save();paint();};
document.getElementById('export').onclick=()=>{
 let csv='set_id,seed,bc,better,showcase\\n';
 cards.forEach(c=>{const v=m[key(c)]||{};
  csv+=c.dataset.sid+','+c.dataset.seed+','+c.dataset.bc+','+(v.verdict||'')+','+(v.star?'star':'')+'\\n';});
 const box=document.getElementById('csvbox');box.style.display='block';box.value=csv;box.select();
 try{const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([csv],{type:'text/csv'}));
  a.download='v36_er_vs_bc.csv';a.click();}catch(x){}};
paint();</script>"""

if __name__ == "__main__":
    main()
