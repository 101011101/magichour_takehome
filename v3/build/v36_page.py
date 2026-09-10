"""Build the v3.6 page: call 2's prompt, on the 29 cells `BC_klein` actually failed.

One card per failing cell. Left: the person (image 1) and the `BC` reference (image 2),
both exactly as the shipped cell got them. Right: four outputs of the same two images —
the archived failure, then the same prompt re-run on fal, then the two variants.

  BC  the archived cell, self-hosted on an A100 - the failure of record
  E0  that prompt re-run on fal                  - the control the variants are read against
  EL  E0 + a limb and extremity count
  EF  E0 + full replacement, fabrics that do not merge
  ER  E0's verb changed: replace the clothing, not dress the person

Every output carries a fail button; the tally is per arm, so the page produces four
comparable numbers on one set under one eye. Marks live in the browser and export to CSV.

  python3 v3/build/v36_page.py     ->  v3/report/v36_editprompts.html
"""
import csv
import html
import json
import os

from PIL import Image

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RUN = os.path.join(REPO, "v3", "runs", "v36", "editprompts")
SRC = os.path.join(REPO, "v3", "runs", "v34", "ironman2")
BCR = os.path.join(REPO, "v3", "runs", "v34", "ironman2_bc")
REPORT = os.path.join(REPO, "v3", "report")
IMG = os.path.join(REPORT, "img_v36")
SET = os.path.join(REPO, "v3", "testsets", "v36_bc_failures.csv")

ARMS = ("BC", "E0", "EL", "EF", "ER")
LABEL = {"BC": ("BC", "archived, A100 &mdash; the failure of record"),
         "E0": ("E0", "the same prompt, re-run on fal &mdash; the control"),
         "EL": ("EL", "+ limb and extremity count"),
         "EF": ("EF", "+ full replacement, no fabric blending"),
         "ER": ("ER", "E0's verb: replace the clothing, not dress the person")}


def web(src, dst, width=460):
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
    return "img_v36/" + dst, "img_v36/" + os.path.basename(full)


def gen_path(arm, sid, seed):
    if arm == "BC":
        return os.path.join(BCR, "gen", f"{sid}__BC__s{seed}.jpg")
    return os.path.join(RUN, "gen", f"{sid}__{arm}__s{seed}.jpg")


def main():
    os.makedirs(IMG, exist_ok=True)
    meta = json.load(open(os.path.join(RUN, "meta", "run.json")))
    rows = list(csv.DictReader(open(SET)))

    cards, n = [], 0
    for r in rows:
        sid, p, g, s = r["set_id"], r["person"], r["garment"], r["seed"]
        pt, pf = web(os.path.join(SRC, "inputs", f"{p}.jpg"), f"{p}__person.jpg", 300)
        rt, rf = web(os.path.join(BCR, "refs", f"{g}__BC.jpg"), f"{g}__ref.jpg", 300)
        cols = []
        for arm in ARMS:
            t, f = web(gen_path(arm, sid, s), f"{sid}__{arm}__s{s}.jpg")
            if not t:
                continue
            n += 1
            lab, ch = LABEL[arm]
            cols.append(
                f"<figure class='out' data-sid='{html.escape(sid)}' data-seed='{s}' "
                f"data-arm='{arm}'>"
                f"<div class='ah'><b>{lab}</b><span>{ch}</span></div>"
                f"<img src='{t}' data-full='{f}' alt='{html.escape(sid)} {arm} s{s}' "
                "loading='lazy'>"
                "<figcaption><button class='fail'>fail</button></figcaption></figure>")
        cards.append(
            f"<div class='card' data-sid='{html.escape(sid)}'><div class='ch'>"
            f"<b>{html.escape(sid)}</b><span class='t'>seed {s}</span>"
            f"<span class='cnt' data-sid='{html.escape(sid)}' data-seed='{s}'></span></div>"
            "<div class='body'><div class='src'>"
            f"<figure><img src='{pt}' data-full='{pf}' alt='{html.escape(p)} person' "
            "loading='lazy'><figcaption>the person (image 1)</figcaption></figure>"
            f"<figure><img src='{rt}' data-full='{rf}' alt='{html.escape(g)} BC reference' "
            "loading='lazy'><figcaption>the BC reference (image 2)</figcaption></figure>"
            f"</div><div class='outs'>{''.join(cols)}</div></div></div>")

    prompts = "".join(
        f"<div class='pr'><b>{a}</b><code>{html.escape(meta['prompts'][a])}</code></div>"
        for a in ("E0", "EL", "EF", "ER"))

    o = [HEAD, "<div class='wrap'>", LEDE, f"<div class='prompts'>{prompts}</div>", BAR,
         f"<div class='grid'>{''.join(cards)}</div>",
         f"<footer>{len(rows)} cells &times; {len(ARMS)} arms = {n} images &middot; "
         f"{meta['calls']} klein calls on <code>{html.escape(meta['endpoint'])}</code>, "
         f"${meta['usd']:.2f} &middot; call 2 only: same two images every arm "
         f"({html.escape(meta['reference'])}), {html.escape(meta['canvas'])} &middot; "
         f"set: <code>{html.escape(meta['set'])}</code> &mdash; "
         f"{html.escape(meta['set_definition'])} &middot; rerun: "
         "<code>python3 v3/build/run_v36_editprompts.py</code>, rebuild: "
         "<code>python3 v3/build/v36_page.py</code>.</footer></div>", LB, SCRIPT]
    open(os.path.join(REPORT, "v36_editprompts.html"), "w").write("\n".join(o))
    print(f"v3/report/v36_editprompts.html  ({len(rows)} cells x {len(ARMS)} arms)")


HEAD = """<title>v3.6 - call 2's prompt on BC's own failures</title>
<meta name='viewport' content='width=device-width,initial-scale=1'>
<style>
:root{--bg:#0d0d10;--fg:#e8e8ea;--dim:#8a8a94;--line:#26262c;--acc:#7c5cff;--red:#8a2b34}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
 font:15px/1.6 ui-sans-serif,-apple-system,"Segoe UI",Roboto,sans-serif}
.wrap{max-width:1900px;margin:0 auto;padding:24px 20px 0}
h1{margin:0 0 2px;font-size:24px}
.lede{color:var(--dim);max-width:94ch;font-size:14px;margin:6px 0 12px}
.lede b{color:var(--fg)}
.prompts{display:grid;gap:6px;margin:0 0 4px}
.pr{display:grid;grid-template-columns:34px 1fr;gap:8px;align-items:start;font-size:12.5px}
.pr b{color:var(--acc);font:12.5px ui-monospace,monospace}
.pr code{background:#15151b;border:1px solid var(--line);border-radius:6px;padding:5px 8px;
 color:#c3c3ce;font:12px/1.55 ui-monospace,monospace;display:block}
#bar{position:sticky;top:0;z-index:40;display:flex;gap:12px;align-items:center;flex-wrap:wrap;
 padding:10px 13px;margin:12px 0 0;background:#141419;border:1px solid var(--line);
 border-radius:9px;font-size:13px}
#bar button{background:#101014;color:var(--fg);border:1px solid var(--line);border-radius:20px;
 padding:4px 12px;cursor:pointer;font:12px ui-sans-serif,sans-serif}
#bar button.on{background:var(--acc);border-color:var(--acc);color:#fff}
#tally{margin-left:auto;font:13px ui-monospace,monospace;display:flex;gap:12px}
#tally span b{color:#ff9aa2}
.grid{display:grid;grid-template-columns:1fr;gap:10px;margin-top:14px}
.card{border:1px solid var(--line);border-radius:9px;background:#101014;overflow:hidden}
.ch{display:flex;gap:8px;align-items:center;padding:6px 11px;background:#141419;
 border-bottom:1px solid var(--line);font-size:12px;flex-wrap:wrap}
.ch b{font-size:12.5px;word-break:break-all}
.t{font-size:9.5px;padding:1px 7px;border-radius:20px;background:#2a1a12;
 border:1px solid #6b4423;color:#d29922}
.cnt{margin-left:auto;color:var(--dim);font:11px ui-monospace,monospace}
.body{display:grid;grid-template-columns:300px 1fr;gap:10px;padding:7px}
@media(max-width:1100px){.body{grid-template-columns:1fr}}
.src{display:grid;grid-template-columns:repeat(2,1fr);gap:5px;align-content:start}
.outs{display:grid;grid-template-columns:repeat(5,1fr);gap:7px}
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
<div class='wrap'><h1>v3.6 &mdash; call 2's prompt, on the cells <code>BC_klein</code> failed</h1></div>
"""

LEDE = """<p class='lede'>The set is the <b>29 cells of the 600-cell iron-man-2 sweep the
reviewer marked FAIL for BC</b> (19 pairs, 4.8% &mdash; <code>v3/testsets/bc_count.csv</code>).
Every arm on a row was given <b>the same two images</b>: the person as shipped, and the
<b>BC</b> reference as shipped &mdash; bald pass plus the V2 head-subtracting crop, not
SR'd. <b>Call 1 does not change anywhere on this page.</b> The only variable is call 2's
prompt. <b>E0</b> is the shipped prompt re-run on fal, so the variants are read against a
control made on the same hardware rather than against the A100 archive. Selected on
failure: a rate here is <b>not</b> a rate on the fold, and what a longer prompt costs on
the 571 cells that already pass is a separate run. Click <b>fail</b> on any cell you would
not ship; the tally is per arm. Click any image for full size.</p>"""

BAR = """<div id='bar'>
<button id='jump'>jump to first unmarked</button>
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

const KEY='v36-editprompts-v1';let f={};try{f=JSON.parse(localStorage.getItem(KEY)||'{}')}catch(e){}
const outs=[...document.querySelectorAll('figure.out')];
const key=o=>o.dataset.sid+'|'+o.dataset.seed+'|'+o.dataset.arm;
const ARMS=[...new Set(outs.map(o=>o.dataset.arm))];
function paint(){
 outs.forEach(o=>o.classList.toggle('failed',!!f[key(o)]));
 document.querySelectorAll('.cnt').forEach(c=>{
  const v=outs.filter(o=>o.dataset.sid===c.dataset.sid&&o.dataset.seed===c.dataset.seed);
  const bad=v.filter(o=>f[key(o)]).map(o=>o.dataset.arm);
  c.textContent=bad.length?'failed: '+bad.join(' '):'';});
 document.getElementById('tally').innerHTML=ARMS.map(a=>{
  const v=outs.filter(o=>o.dataset.arm===a),bad=v.filter(o=>f[key(o)]).length;
  return '<span>'+a+' <b>'+bad+'</b>/'+v.length+'</span>';}).join('');}
document.addEventListener('click',e=>{const b=e.target.closest('button.fail');if(!b)return;
 const o=b.closest('figure.out'),k=key(o);
 if(f[k])delete f[k];else f[k]=1;
 try{localStorage.setItem(KEY,JSON.stringify(f))}catch(x){}paint();});
document.getElementById('jump').onclick=()=>{
 const o=outs.find(x=>!(key(x) in f));
 if(o)o.scrollIntoView({behavior:'smooth',block:'center'});else alert('every cell is marked');};
document.getElementById('reset').onclick=()=>{
 if(!confirm('clear every mark?'))return;f={};
 try{localStorage.removeItem(KEY)}catch(x){}paint();};
document.getElementById('export').onclick=()=>{
 let csv='set_id,seed,arm,failed\\n';
 outs.forEach(o=>{csv+=o.dataset.sid+','+o.dataset.seed+','+o.dataset.arm+','+(f[key(o)]?'fail':'')+'\\n';});
 const box=document.getElementById('csvbox');box.style.display='block';box.value=csv;box.select();
 try{const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([csv],{type:'text/csv'}));
  a.download='v36_editprompts.csv';a.click();}catch(x){}};
paint();</script>"""

if __name__ == "__main__":
    main()
