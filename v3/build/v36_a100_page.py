"""Build the v3.6 A100 page: call 2's prompt on 150 cells, both sides of BC's record.

One card per cell. Left: the person (image 1) and the `BC` reference (image 2), exactly as
the shipped cell got them. Right: `E0` — the shipped prompt, which here is the archived
`BC` cell itself, byte for byte — then the three variants, all made on the same A100 from
the same two images. Call 1 does not vary anywhere on this page.

The set is 29 cells the reviewer marked FAIL for `BC` and 121 it left unmarked, and the
tally keeps them apart on purpose: on the 29 a fail-mark that disappears is a **rescue**,
on the 121 a fail-mark that appears is a **regression**, and only the second number decides
whether a prompt ships.

  python3 v3/build/v36_a100_page.py     ->  v3/report/v36_a100.html
"""
import csv
import html
import json
import os

from PIL import Image

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RUN = os.path.join(REPO, "v3", "runs", "v36", "a100")
REPORT = os.path.join(REPO, "v3", "report")
IMG = os.path.join(REPORT, "img_v36a")

ARMS = ("E0", "ER", "EFR", "EX")
LABEL = {"E0": ("E0", "the shipped prompt &mdash; the archived BC cell itself"),
         "ER": ("ER", "the verb: replace the clothing, not dress the person"),
         "EFR": ("EFR", "ER + the no-blend paragraph"),
         "EX": ("EX", "removal, layering, piece count, limb count, framing")}


def web(src, dst, width=440):
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
    return "img_v36a/" + dst, "img_v36a/" + os.path.basename(full)


def main():
    os.makedirs(IMG, exist_ok=True)
    meta = json.load(open(os.path.join(RUN, "meta", "cost_v36.json")))
    rows = list(csv.DictReader(open(os.path.join(RUN, "v36_editset.csv"))))

    cards, n = [], 0
    for r in rows:
        sid, p, g, s, bc = r["set_id"], r["person"], r["garment"], r["seed"], r["bc"]
        pt, pf = web(os.path.join(RUN, "inputs", f"{p}.jpg"), f"{p}__person.jpg", 280)
        rt, rf = web(os.path.join(RUN, "refs", f"{g}__BC.jpg"), f"{g}__ref.jpg", 280)
        cols = []
        for arm in ARMS:
            t, f = web(os.path.join(RUN, "gen", f"{sid}__{arm}__s{s}.jpg"),
                       f"{sid}__{arm}__s{s}.jpg")
            if not t:
                continue
            n += 1
            lab, ch = LABEL[arm]
            cols.append(
                f"<figure class='out' data-sid='{html.escape(sid)}' data-seed='{s}' "
                f"data-arm='{arm}' data-bc='{bc}'>"
                f"<div class='ah'><b>{lab}</b><span>{ch}</span></div>"
                f"<img src='{t}' data-full='{f}' alt='{html.escape(sid)} {arm} s{s}' "
                "loading='lazy'>"
                "<figcaption><button class='fail'>fail</button></figcaption></figure>")
        cards.append(
            f"<div class='card' data-bc='{bc}'><div class='ch'>"
            f"<b>{html.escape(sid)}</b><span class='t'>seed {s}</span>"
            f"<span class='b b-{bc}'>BC {bc}</span>"
            f"<span class='cnt' data-sid='{html.escape(sid)}' data-seed='{s}'></span></div>"
            "<div class='body'><div class='src'>"
            f"<figure><img src='{pt}' data-full='{pf}' alt='{html.escape(p)} person' "
            "loading='lazy'><figcaption>the person (image 1)</figcaption></figure>"
            f"<figure><img src='{rt}' data-full='{rf}' alt='{html.escape(g)} BC reference' "
            "loading='lazy'><figcaption>the BC reference (image 2)</figcaption></figure>"
            f"</div><div class='outs'>{''.join(cols)}</div></div></div>")

    prompts = "".join(
        f"<div class='pr'><b>{a}</b><code>{html.escape(meta['prompts'][a])}</code></div>"
        for a in ARMS)
    k = meta["klein"]
    o = [HEAD, "<div class='wrap'>", LEDE, f"<div class='prompts'>{prompts}</div>", BAR,
         f"<div class='grid'>{''.join(cards)}</div>",
         f"<footer>{len(rows)} cells &times; {len(ARMS)} arms = {n} images &middot; "
         f"{meta['calls']} klein calls self-hosted on {html.escape(k['gpu'])} "
         f"(<code>{html.escape(k['repo'])}</code>, {k['dtype']}), {meta['wall_minutes']} min, "
         f"CAD {meta['usd_gpu']:.2f} &mdash; ${meta['usd_fal_equivalent']:.2f} of fal calls "
         f"&middot; median call {meta['call_seconds_median']}s &middot; call 2 only: "
         f"{html.escape(meta['reference'])}, {html.escape(meta['canvas'])} &middot; "
         f"E0 is not a call &mdash; it is the archived BC cell, verified byte-identical "
         f"&middot; set: <code>{html.escape(meta['set'])}</code> &mdash; "
         f"{html.escape(meta['set_definition'])} &middot; rebuild: "
         "<code>python3 v3/build/v36_a100_page.py</code>.</footer></div>", LB, SCRIPT]
    open(os.path.join(REPORT, "v36_a100.html"), "w").write("\n".join(o))
    print(f"v3/report/v36_a100.html  ({len(rows)} cells x {len(ARMS)} arms, {n} images)")


HEAD = """<title>v3.6 - call 2's prompt on 150 cells</title>
<meta name='viewport' content='width=device-width,initial-scale=1'>
<style>
:root{--bg:#0d0d10;--fg:#e8e8ea;--dim:#8a8a94;--line:#26262c;--acc:#7c5cff;--red:#8a2b34;
 --grn:#2c5c33}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
 font:15px/1.6 ui-sans-serif,-apple-system,"Segoe UI",Roboto,sans-serif}
.wrap{max-width:1900px;margin:0 auto;padding:24px 20px 0}
h1{margin:0 0 2px;font-size:24px}
.lede{color:var(--dim);max-width:94ch;font-size:14px;margin:6px 0 12px}
.lede b{color:var(--fg)}
.prompts{display:grid;gap:6px;margin:0 0 4px}
.pr{display:grid;grid-template-columns:38px 1fr;gap:8px;align-items:start;font-size:12.5px}
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
#tally b{color:#ff9aa2}
#tally .hd{color:var(--dim)}
.grid{display:grid;grid-template-columns:1fr;gap:10px;margin-top:14px}
.card{border:1px solid var(--line);border-radius:9px;background:#101014;overflow:hidden}
.ch{display:flex;gap:8px;align-items:center;padding:6px 11px;background:#141419;
 border-bottom:1px solid var(--line);font-size:12px;flex-wrap:wrap}
.ch b{font-size:12.5px;word-break:break-all}
.t{font-size:9.5px;padding:1px 7px;border-radius:20px;background:#2a1a12;
 border:1px solid #6b4423;color:#d29922}
.b{font:10px ui-monospace,monospace;padding:1px 8px;border-radius:20px;border:1px solid var(--line)}
.b-fail{background:#2d1418;border-color:#8a2b34;color:#ff9aa2}
.b-ok{background:#12240f;border-color:var(--grn);color:#7ee787}
.cnt{margin-left:auto;color:var(--dim);font:11px ui-monospace,monospace}
.body{display:grid;grid-template-columns:280px 1fr;gap:10px;padding:7px}
@media(max-width:1100px){.body{grid-template-columns:1fr}}
.src{display:grid;grid-template-columns:repeat(2,1fr);gap:5px;align-content:start}
.outs{display:grid;grid-template-columns:repeat(4,1fr);gap:7px}
@media(max-width:900px){.outs{grid-template-columns:repeat(2,1fr)}}
figure{margin:0}
figure img{width:100%;display:block;background:#fff;border-radius:5px;cursor:zoom-in;
 aspect-ratio:3/4;object-fit:contain}
.src figure img{aspect-ratio:2/3}
.ah{display:flex;gap:6px;align-items:baseline;padding:1px 3px 4px;font-size:11.5px}
.ah b{font:11.5px ui-monospace,monospace}
.ah span{color:var(--dim);font-size:10.5px;line-height:1.3}
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
<div class='wrap'><h1>v3.6 &mdash; call 2's prompt, on both sides of <code>BC</code>'s record</h1></div>
"""

LEDE = """<p class='lede'>150 cells: the <b>29 the reviewer marked FAIL</b> for <b>BC</b> in
the blind 600-cell sweep, and <b>121 it left unmarked</b>, sampled with a fixed seed from
the other 571. Every arm on a row got <b>the same two images</b> &mdash; the person, and the
<b>BC</b> reference as shipped &mdash; on <b>the same A100</b>, on BC's own call-2 canvas.
<b>Call 1 does not vary anywhere on this page.</b> <b>E0</b> is not a fresh call: it is the
archived BC cell itself, byte-identical, which is what the reviewer's verdicts were made on.
<b>Mark every arm you would not ship.</b> On a <b>BC fail</b> row, an arm you leave unmarked
is a <b>rescue</b>; on a <b>BC ok</b> row, an arm you mark is a <b>regression</b> &mdash; and
the regression number is the one that decides whether a longer prompt ships. Click any image
for full size.</p>"""

BAR = """<div id='bar'>
<button id='jump'>jump to first unmarked</button>
<button id='f-all' class='on'>all 150</button>
<button id='f-fail'>the 29 BC failures</button>
<button id='f-ok'>the 121 BC passes</button>
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

const KEY='v36-a100-v1';let f={};try{f=JSON.parse(localStorage.getItem(KEY)||'{}')}catch(e){}
const outs=[...document.querySelectorAll('figure.out')];
const key=o=>o.dataset.sid+'|'+o.dataset.seed+'|'+o.dataset.arm;
const ARMS=[...new Set(outs.map(o=>o.dataset.arm))];
function paint(){
 outs.forEach(o=>o.classList.toggle('failed',!!f[key(o)]));
 document.querySelectorAll('.cnt').forEach(c=>{
  const v=outs.filter(o=>o.dataset.sid===c.dataset.sid&&o.dataset.seed===c.dataset.seed);
  const bad=v.filter(o=>f[key(o)]).map(o=>o.dataset.arm);
  const seen=v.filter(o=>key(o) in f).length;
  c.textContent=bad.length?'failed: '+bad.join(' '):(seen?'all clean':'');});
 const cell=(a,bc)=>{const v=outs.filter(o=>o.dataset.arm===a&&o.dataset.bc===bc);
  return v.filter(o=>f[key(o)]).length+'/'+v.length;};
 const rows=ARMS.map(a=>'<div>'+a.padEnd(4,'\\u00a0')+' &nbsp; on the 29: <b>'+cell(a,'fail')
  +'</b> &nbsp; on the 121: <b>'+cell(a,'ok')+'</b></div>').join('');
 const marked=Object.keys(f).length;
 document.getElementById('tally').innerHTML=
  '<div class="hd">cells you would not ship &nbsp;('+marked+' marks)</div>'+rows;}
document.addEventListener('click',e=>{const b=e.target.closest('button.fail');if(!b)return;
 const o=b.closest('figure.out'),k=key(o);
 if(f[k])delete f[k];else f[k]=1;
 try{localStorage.setItem(KEY,JSON.stringify(f))}catch(x){}paint();});
function filter(which,btn){
 document.querySelectorAll('.card').forEach(c=>
  c.style.display=(which==='all'||c.dataset.bc===which)?'':'none');
 ['f-all','f-fail','f-ok'].forEach(i=>document.getElementById(i).classList.remove('on'));
 btn.classList.add('on');}
document.getElementById('f-all').onclick=e=>filter('all',e.target);
document.getElementById('f-fail').onclick=e=>filter('fail',e.target);
document.getElementById('f-ok').onclick=e=>filter('ok',e.target);
document.getElementById('jump').onclick=()=>{
 const vis=outs.filter(o=>o.closest('.card').style.display!=='none');
 const o=vis.find(x=>!(key(x) in f));
 if(o)o.scrollIntoView({behavior:'smooth',block:'center'});else alert('every visible cell is marked');};
document.getElementById('reset').onclick=()=>{
 if(!confirm('clear every mark?'))return;f={};
 try{localStorage.removeItem(KEY)}catch(x){}paint();};
document.getElementById('export').onclick=()=>{
 let csv='set_id,seed,arm,bc,failed\\n';
 outs.forEach(o=>{csv+=o.dataset.sid+','+o.dataset.seed+','+o.dataset.arm+','+o.dataset.bc
  +','+(f[key(o)]?'fail':'')+'\\n';});
 const box=document.getElementById('csvbox');box.style.display='block';box.value=csv;box.select();
 try{const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([csv],{type:'text/csv'}));
  a.download='v36_a100_marks.csv';a.click();}catch(x){}};
paint();</script>"""

if __name__ == "__main__":
    main()
