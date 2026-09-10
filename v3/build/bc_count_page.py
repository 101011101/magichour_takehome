"""Every cell of one iron-man-2 arm, with one button each: does it fail?

600 cells - 200 pairs x seeds 46/47/48 - of v3.1's incumbent as v3.4 rebuilt it properly
(bald pass -> V2 crop with the head subtracted -> klein edit). One question per cell, so a
rate can be counted rather than argued.

Deliberately blind on one axis: the reviewer's VEi verdicts are NOT shown and are not in
the page at all. The point is an independent BC number; joining it to the VEi record
afterwards on set_id+seed is a separate step, and it is only worth anything if this pass
did not know the answer while it was being made.

  python3 v3/build/bc_count_page.py [ARM]    ->  v3/report/{arm}_count.html

ARM is BC (default) or VEi. The two pages are identical in every respect except the images,
which is the point: one rate is comparable to another only if the same eye made both calls
under the same protocol. The VEi record already in the repo (v34_im2_truth.json) came from
a judge-then-audit process, so setting it beside a single fresh sweep needs a caveat - this
page removes the need for one.
"""
import csv
import html
import os
import sys

from PIL import Image

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RUN = os.path.join(REPO, "v3", "runs", "v34", "ironman2")
REPORT = os.path.join(REPO, "v3", "report")
MATRIX = os.path.join(REPO, "v3", "colab", "matrix.csv")
SEEDS = (46, 47, 48)

ARM = sys.argv[1] if len(sys.argv) > 1 else "BC"
SLUG = ARM.lower()
TITLE = {"BC": "BC_klein &mdash; bald pass, V2 crop, klein edit",
         "VEi": "VEi &mdash; the v3.4 lock: mannequin reference, SR, klein edit",
         "ER": "ER &mdash; BC's pipeline, one word changed in call 2"}.get(ARM, ARM)
# An arm made in a later run keeps its cells in its own directory; its references and
# inputs are still BC's, because that is what makes the two rates comparable.
GEN = {"ER": os.path.join(REPO, "v3", "runs", "v36", "ironman_er", "gen")}.get(ARM, os.path.join(RUN, "gen"))
REF_ARM = {"ER": "BC"}.get(ARM, ARM)
IMG = os.path.join(REPORT, "img_" + SLUG + "count")


def web(src, dst, width):
    if not os.path.exists(src):
        return None, None
    out, full = os.path.join(IMG, dst), os.path.join(IMG, dst.replace(".jpg", "@full.jpg"))
    im = None
    if not os.path.exists(out):
        im = Image.open(src).convert("RGB")
        t = im.resize((width, int(im.height * width / im.width)), Image.LANCZOS) if im.width > width else im
        t.save(out, quality=88, optimize=True)
    if not os.path.exists(full):
        im = im or Image.open(src).convert("RGB")
        im.save(full, quality=93, optimize=True)
    return "img_" + SLUG + "count/" + dst, "img_" + SLUG + "count/" + os.path.basename(full)


def main():
    os.makedirs(IMG, exist_ok=True)
    rows = list(csv.DictReader(open(MATRIX)))
    cards, n = [], 0
    for r in rows:
        sid, p, g = r["set_id"], r["person"], r["garment"]
        cells = []
        for s in SEEDS:
            t, f = web(os.path.join(GEN, f"{sid}__{ARM}__s{s}.jpg"), f"{sid}__s{s}.jpg", 420)
            if not t:
                continue
            n += 1
            cells.append(f"<figure class='out' data-sid='{html.escape(sid)}' data-seed='{s}'>"
                         f"<img src='{t}' data-full='{f}' alt='{html.escape(sid)} {ARM} s{s}' loading='lazy'>"
                         f"<figcaption><button class='fail'>fail</button><span>s{s}</span></figcaption>"
                         "</figure>")
        if not cells:
            continue
        pt, pf = web(os.path.join(RUN, "inputs", f"{p}.jpg"), f"{p}__p.jpg", 260)
        ct, cf = web(os.path.join(RUN, "inputs", f"{g}__A4.jpg"), f"{g}__a4.jpg", 260)
        rt, rf = web(os.path.join(RUN, "refs", f"{g}__{REF_ARM}.jpg"), f"{g}__ref.jpg", 260)
        tags = "".join(f"<span class='t'>{html.escape(x)}</span>"
                       for x in (r["garment_category"], r["garment_hard_case"]) if x)
        cards.append(
            f"<div class='card' data-sid='{html.escape(sid)}'><div class='ch'>"
            f"<b>{html.escape(sid)}</b>{tags}"
            f"<span class='cnt' data-sid='{html.escape(sid)}'></span></div>"
            "<div class='body'><div class='src'>"
            + "".join(f"<figure><img src='{a}' data-full='{b}' alt='{c}' loading='lazy'>"
                      f"<figcaption>{c}</figcaption></figure>"
                      for a, b, c in ((pt, pf, "person"), (ct, cf, "garment"), (rt, rf, f"{REF_ARM} reference")) if a)
            + f"</div><div class='outs'>{''.join(cells)}</div></div></div>")

    head = HEAD.replace("ARMTITLE", TITLE)
    script = SCRIPT.replace("ARMKEY", SLUG)
    o = [head, "<div class='wrap'>", LEDE.replace("ARMNAME", ARM), BAR,
         f"<div class='grid'>{''.join(cards)}</div>",
         f"<footer>{n} cells &middot; {len(cards)} pairs &times; {len(SEEDS)} seeds &middot; "
         f"arm <code>{ARM}</code>, seeds 46/47/48 on an A100 &middot; "
         f"<code>{os.path.relpath(GEN, REPO)}/&#123;set_id&#125;__{ARM}__s&#123;seed&#125;.jpg</code>"
         f" &middot; rebuild: <code>python3 v3/build/bc_count_page.py {ARM}</code>"
         "</footer></div>", LB, script]
    open(os.path.join(REPORT, SLUG + "_count.html"), "w").write("\n".join(o))
    print(f"v3/report/{SLUG}_count.html  ({n} cells, {len(cards)} pairs)")


HEAD = """<title>ARMTITLE - 600 cells</title>
<meta name='viewport' content='width=device-width,initial-scale=1'>
<style>
:root{--bg:#0d0d10;--fg:#e8e8ea;--dim:#8a8a94;--line:#26262c;--acc:#7c5cff;--red:#8a2b34}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
 font:15px/1.6 ui-sans-serif,-apple-system,"Segoe UI",Roboto,sans-serif}
.wrap{max-width:1780px;margin:0 auto;padding:24px 20px 0}
h1{margin:0 0 2px;font-size:24px}
.sub{margin:0 0 8px;color:var(--dim);font-size:13px}
.lede{color:var(--dim);max-width:92ch;font-size:14px;margin:0 0 10px}
.lede b{color:var(--fg)}
#bar{position:sticky;top:0;z-index:40;display:flex;gap:14px;align-items:center;flex-wrap:wrap;
 padding:10px 13px;margin:12px 0 0;background:#141419;border:1px solid var(--line);
 border-radius:9px;font-size:13px}
#bar button{background:#101014;color:var(--fg);border:1px solid var(--line);border-radius:20px;
 padding:4px 12px;cursor:pointer;font:12px ui-sans-serif,sans-serif}
#bar button.on{background:var(--acc);border-color:var(--acc);color:#fff}
#tally{margin-left:auto;font:13px ui-monospace,monospace}
#tally b{color:#ff9aa2;font-size:15px}
.grid{display:grid;grid-template-columns:1fr;gap:10px;margin-top:14px}
.card{border:1px solid var(--line);border-radius:9px;background:#101014;overflow:hidden}
.ch{display:flex;gap:8px;align-items:center;padding:6px 11px;background:#141419;
 border-bottom:1px solid var(--line);font-size:12px;flex-wrap:wrap}
.ch b{font-size:12.5px;word-break:break-all}
.t{font-size:9.5px;padding:1px 7px;border-radius:20px;background:#2a1a12;
 border:1px solid #6b4423;color:#d29922}
.cnt{margin-left:auto;color:var(--dim);font:11px ui-monospace,monospace}
.body{display:grid;grid-template-columns:280px 1fr;gap:10px;padding:7px}
@media(max-width:1000px){.body{grid-template-columns:1fr}}
.src{display:grid;grid-template-columns:repeat(3,1fr);gap:5px}
.outs{display:grid;grid-template-columns:repeat(3,1fr);gap:6px}
@media(max-width:700px){.outs{grid-template-columns:1fr}}
figure{margin:0}
figure img{width:100%;display:block;background:#fff;border-radius:5px;cursor:zoom-in;
 aspect-ratio:3/4;object-fit:contain}
.src figure img{aspect-ratio:2/3}
figcaption{font-size:10.5px;color:var(--dim);text-align:center;padding:3px 2px;
 display:flex;gap:6px;align-items:center;justify-content:center}
.out.failed img{outline:3px solid var(--red);outline-offset:-3px;opacity:.55}
button.fail{background:#101014;color:var(--dim);border:1px solid var(--line);border-radius:20px;
 padding:1px 10px;cursor:pointer;font:11px ui-sans-serif,sans-serif}
.out.failed button.fail{background:var(--red);border-color:#ff9aa2;color:#fff}
#lb{display:none;position:fixed;inset:0;background:rgba(0,0,0,.95);z-index:99;
 align-items:center;justify-content:center;flex-direction:column;gap:10px;padding:20px}
#lb.on{display:flex}#lb img{max-width:95vw;max-height:90vh;object-fit:contain;background:#fff}
#lbc{color:var(--dim);font-size:13px}
footer{border-top:1px solid var(--line);margin-top:34px;padding:20px 0 30px;color:var(--dim);font-size:12.5px}
code{background:#1b1b22;padding:1px 5px;border-radius:4px;font-size:12px}
textarea{display:none;width:100%;height:150px;margin-top:10px;background:#0b0b0e;color:#c3c3ce;
 border:1px solid var(--line);border-radius:6px;font:12px ui-monospace,monospace;padding:8px}
</style>
<div class='wrap'><h1>ARMTITLE</h1><p class='sub'>600 cells, one button</p></div>
"""

LEDE = """<p class='lede'>Every cell of arm <b>ARMNAME</b> from iron man 2 &mdash; 200 pairs,
seeds 46/47/48. Person, garment and the reference that arm was given sit on the left of each
row; its three draws are on the right. Click <b>fail</b> on any cell you would not ship.
Marks are kept in this browser, so you can stop and come back. <b>No prior verdict is on
this page or in it</b> &mdash; a rate is only worth something if the pass did not know the
answer while it was being made, and only comparable to another rate made the same way.
Click any image for full size.</p>"""

BAR = """<div id='bar'>
<button id='jump'>jump to first unmarked</button>
<button id='only-fail'>show only failed</button>
<button id='show-all' class='on'>show all</button>
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

const KEY='ARMKEY-count-v1';let f={};try{f=JSON.parse(localStorage.getItem(KEY)||'{}')}catch(e){}
const outs=[...document.querySelectorAll('figure.out')];
const key=o=>o.dataset.sid+'|'+o.dataset.seed;
function paint(){
 let bad=0,seen=0;
 outs.forEach(o=>{const on=!!f[key(o)];o.classList.toggle('failed',on);bad+=on;});
 seen=Object.keys(f).length;
 const pairs={};outs.forEach(o=>{(pairs[o.dataset.sid]=pairs[o.dataset.sid]||[]).push(!!f[key(o)])});
 let allthree=0,any=0;
 document.querySelectorAll('.cnt').forEach(c=>{const v=pairs[c.dataset.sid]||[];
  const k=v.filter(Boolean).length;c.textContent=k?k+'/'+v.length+' failed':'';
  if(k===v.length&&v.length)allthree++; if(k)any++;});
 const t=outs.length;
 document.getElementById('tally').innerHTML=
  '<b>'+bad+'</b> / '+t+' cells failed ('+(100*bad/t).toFixed(1)+'%) &nbsp;·&nbsp; '
  +any+' pairs with a failure &nbsp;·&nbsp; '+allthree+' failing at every seed';}
document.addEventListener('click',e=>{const b=e.target.closest('button.fail');if(!b)return;
 const o=b.closest('figure.out'),k=key(o);
 if(f[k])delete f[k];else f[k]=1;
 try{localStorage.setItem(KEY,JSON.stringify(f))}catch(x){}paint();});

document.getElementById('only-fail').onclick=e=>{
 document.querySelectorAll('.card').forEach(c=>
  c.style.display=c.querySelector('figure.out.failed')?'':'none');
 e.target.classList.add('on');document.getElementById('show-all').classList.remove('on');};
document.getElementById('show-all').onclick=e=>{
 document.querySelectorAll('.card').forEach(c=>c.style.display='');
 e.target.classList.add('on');document.getElementById('only-fail').classList.remove('on');};
document.getElementById('jump').onclick=()=>{
 const o=outs.find(x=>!(key(x) in f));
 if(o)o.scrollIntoView({behavior:'smooth',block:'center'});else alert('every cell is marked');};
document.getElementById('reset').onclick=()=>{
 if(!confirm('clear every mark?'))return;f={};
 try{localStorage.removeItem(KEY)}catch(x){}paint();};
document.getElementById('export').onclick=()=>{
 let csv='set_id,seed,bc_failed\\n';
 outs.forEach(o=>{csv+=o.dataset.sid+','+o.dataset.seed+','+(f[key(o)]?'fail':'')+'\\n';});
 const box=document.getElementById('csvbox');box.style.display='block';box.value=csv;box.select();
 try{const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([csv],{type:'text/csv'}));
  a.download='ARMKEY_count.csv';a.click();}catch(x){}};
paint();</script>"""

if __name__ == "__main__":
    main()
