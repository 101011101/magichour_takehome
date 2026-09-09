"""Build the v3.5 link-A page: what call 1 does to the reference, five ways.

Per garment: the A4 crop it starts from, the v3.4 lock's own A100 reference for context,
then the four fal arms at seed 46 and the two derived head crops. Unblinded - the question
is not which is prettier but three readable facts per cell: did the wearer turn front-on,
did the garment survive unchanged, and is the head gone.

The page is a comparison instrument, not a gallery: columns toggle off so any two arms can
be put side by side, the framing filter isolates a class, and the per-garment verdict
exports as CSV for the readout in prd/v3/v3.5/RESULTS.md.
"""
import csv
import html
import json
import os

from PIL import Image

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RUN = os.path.join(REPO, "v3", "runs", "v35", "linkA")
SRC = os.path.join(REPO, "v3", "runs", "v34", "ironman2")
REPORT = os.path.join(REPO, "v3", "report")
IMG = os.path.join(REPORT, "img_v35a")

# tag, source, label, one-line character, on-by-default
COLS = [
    ("crop", "src", "A4 crop", "what call 1 is given", True),
    ("VEi", "lock", "VEi (A100)", "the v3.4 lock's own reference - other backend, context only", True),
    ("M0", "fal", "M0 mannequin + repose", "the lock's Q3 verbatim, on fal - the control", True),
    ("M0c", "derived", "M0c + head cut", "M0 through BC's head subtraction - no model call", True),
    ("M1", "fal", "M1 turn only", "no mannequin sentence; the face survives", True),
    ("M1c", "derived", "M1c turn + head cut", "the target shape: VEi's re-pose, BC's head removal", True),
    ("M2", "fal", "M2 mannequin + turn", "M1 plus the mannequin sentence", True),
    ("G1", "fal", "G1 garment only", "the clothing alone, wearer removed", True),
]
VERDICTS = ["M0", "M0c", "M1", "M1c", "M2", "G1", "none"]


def path_for(tag, kind, g):
    if kind == "src":
        return os.path.join(SRC, "inputs", f"{g}__A4.jpg")
    if kind == "lock":
        return os.path.join(SRC, "refs", f"{g}__VEi_uncut.jpg")
    return os.path.join(RUN, "refs", f"{g}__{tag}.jpg")


def web(src, dst, width=560):
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
    return "img_v35a/" + dst, "img_v35a/" + os.path.basename(full)


def main():
    os.makedirs(IMG, exist_ok=True)
    meta = json.load(open(os.path.join(RUN, "meta", "run.json")))
    rows = list(csv.DictReader(open(os.path.join(RUN, "meta", "prompts.csv"))))
    prompts = {}
    for r in rows:
        prompts.setdefault(r["arm"], r["prompt"])       # one example per arm, framing varies
    framing = {r["garment"]: r["framing"] for r in rows}
    garments = sorted(framing)

    o = [HEAD, "<div class='wrap'>", LEDE]
    for tag, kind, label, ch, _ in COLS:
        if kind != "fal":
            continue
        o.append(f"<details class='prompt'><summary><b>{tag}</b> "
                 f"<span>{html.escape(label)} &mdash; {html.escape(ch)}</span></summary>"
                 f"<pre>{html.escape(prompts.get(tag, '-'))}</pre></details>")
    o.append(TOOLBAR.replace("{{COLS}}", "".join(
        f"<label class='cb'><input type='checkbox' data-col='{t}'{' checked' if on else ''}>{t}</label>"
        for t, _, _, _, on in COLS)))

    cards, made, missing = [], 0, {}
    for g in garments:
        cells = []
        for tag, kind, label, _, _ in COLS:
            t, f = web(path_for(tag, kind, g), f"{g}__{tag}.jpg")
            if not t and kind in ("fal", "derived"):
                missing[tag] = missing.get(tag, 0) + 1
            cells.append((tag, label, t, f))
        if not any(t for _, _, t, _ in cells[2:]):
            continue
        made += 1
        vote = "".join(f"<button data-v='{v}'>{v}</button>" for v in VERDICTS)
        cards.append(
            f"<div class='card' data-g='{html.escape(g)}' data-framing='{framing[g]}'>"
            f"<div class='ch'><b>{html.escape(g)}</b><span class='t'>{framing[g]}</span>"
            f"<span class='vote' data-g='{html.escape(g)}'>best reference: {vote}</span></div>"
            "<div class='cols'>"
            + "".join(
                (f"<figure class='c-{tag}{' hero' if tag == 'M1c' else ''}'>"
                 f"<img src='{t}' data-full='{f}' alt='{html.escape(g)} {tag}' loading='lazy'>"
                 f"<figcaption>{html.escape(label)}</figcaption></figure>") if t else
                (f"<figure class='c-{tag}'><div class='miss'>not run</div>"
                 f"<figcaption>{html.escape(label)}</figcaption></figure>")
                for tag, label, t, f in cells)
            + "</div></div>")
    o.append(f"<div class='grid'>{''.join(cards)}</div>")
    pend = (" &middot; <b>pending:</b> " + ", ".join(f"{k} {v} not yet made" for k, v in sorted(missing.items()))
            if missing else "")
    o.append(f"<footer>{made} garments &middot; {meta['calls']} klein calls on "
             f"<code>{meta['endpoint']}</code>, seed {meta['seed']}, ${meta['usd']:.2f} "
             f"&middot; head crops derived locally, no model call &middot; canvas: "
             f"{html.escape(meta['canvas_rule'])} &middot; crops and framing reused from "
             f"<code>{html.escape(meta['source_run'])}</code> &middot; "
             "<code>v3/runs/v35/linkA/refs/{g}__{M0,M0c,M1,M1c,M2,G1}.jpg</code>"
             f"{pend} &middot; rebuild: <code>python3 v3/build/v35_linkA_page.py</code>."
             "</footer></div>")
    o.append(LB + SCRIPT)
    open(os.path.join(REPORT, "v35_linkA.html"), "w").write("\n".join(o))
    print(f"v3/report/v35_linkA.html  ({made} garments x {len(COLS)} columns"
          + (f"; pending {missing}" if missing else "") + ")")


HEAD = """<title>v3.5 link A - what call 1 does to the reference</title>
<meta name='viewport' content='width=device-width,initial-scale=1'>
<style>
:root{--bg:#0d0d10;--fg:#e8e8ea;--dim:#8a8a94;--line:#26262c;--acc:#7c5cff;--mid:#d29922}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
 font:15px/1.6 ui-sans-serif,-apple-system,"Segoe UI",Roboto,sans-serif}
.wrap{max-width:1900px;margin:0 auto;padding:26px 22px 0}
h1{margin:0 0 6px;font-size:25px}
.lede{color:var(--dim);max-width:96ch;font-size:14px;margin:0 0 10px}
.lede b{color:var(--fg)}
.prompt{border:1px solid var(--line);border-radius:9px;background:#101014;margin:6px 0;overflow:hidden}
.prompt summary{padding:7px 14px;background:#141419;font-size:13px;cursor:pointer}
.prompt summary span{color:var(--dim);font-size:12.5px}
.prompt pre{margin:0;padding:12px 16px;font:13px/1.7 ui-monospace,SFMono-Regular,monospace;
 white-space:pre-wrap;color:#c3c3ce;background:#0b0b0e}
#bar{position:sticky;top:0;z-index:40;display:flex;gap:14px;align-items:center;flex-wrap:wrap;
 padding:9px 12px;margin:14px 0 0;background:#141419;border:1px solid var(--line);border-radius:9px;
 font-size:12.5px}
#bar .grp{display:flex;gap:7px;align-items:center;flex-wrap:wrap}
#bar .lbl{color:var(--dim);font-size:11.5px;text-transform:uppercase;letter-spacing:.05em}
.cb{display:inline-flex;gap:4px;align-items:center;padding:2px 8px;border:1px solid var(--line);
 border-radius:20px;background:#101014;cursor:pointer;font:12px ui-monospace,monospace}
#bar button{background:#101014;color:var(--fg);border:1px solid var(--line);border-radius:20px;
 padding:3px 11px;cursor:pointer;font:12px ui-sans-serif,sans-serif}
#bar button.on{background:var(--acc);border-color:var(--acc);color:#fff}
#tally{margin-left:auto;color:var(--dim);font-size:12px}
.grid{display:grid;grid-template-columns:1fr;gap:12px;margin-top:14px}
.card{border:1px solid var(--line);border-radius:9px;background:#101014;overflow:hidden}
.ch{display:flex;gap:8px;align-items:center;padding:6px 11px;background:#141419;
 border-bottom:1px solid var(--line);font-size:12px;flex-wrap:wrap}
.ch b{font-size:12.5px;word-break:break-all}
.t{font-size:9.5px;padding:1px 7px;border-radius:20px;background:#2a1a12;
 border:1px solid #6b4423;color:var(--mid)}
.vote{margin-left:auto;display:flex;gap:4px;align-items:center;color:var(--dim);font-size:11px}
.vote button{background:#101014;color:var(--dim);border:1px solid var(--line);border-radius:20px;
 padding:1px 8px;cursor:pointer;font:11px ui-monospace,monospace}
.vote button.on{background:#2c5c33;border-color:#3fb950;color:#e8e8ea}
.cols{display:grid;gap:4px;padding:6px;grid-template-columns:repeat(var(--n,8),1fr)}
@media(max-width:1400px){.cols{grid-template-columns:repeat(4,1fr)}}
@media(max-width:700px){.cols{grid-template-columns:repeat(2,1fr)}}
.miss{background:#17171d;border:1px dashed var(--line);border-radius:5px;aspect-ratio:3/4;
 display:flex;align-items:center;justify-content:center;color:var(--dim);font-size:11px}
figure{margin:0}
figure img{width:100%;display:block;background:#fff;border-radius:5px;cursor:zoom-in;
 aspect-ratio:3/4;object-fit:contain;image-rendering:-webkit-optimize-contrast}
figure.hero img{outline:2px solid #3b3160;outline-offset:-2px}
figure.c-crop figcaption,figure.c-VEi figcaption{color:var(--dim)}
figcaption{font-size:10.5px;color:var(--fg);text-align:center;padding:4px 2px}
body.tall figure img{aspect-ratio:auto;object-fit:contain}
#lb{display:none;position:fixed;inset:0;background:rgba(0,0,0,.95);z-index:99;
 align-items:center;justify-content:center;flex-direction:column;gap:10px;padding:20px}
#lb.on{display:flex}#lb img{max-width:95vw;max-height:90vh;object-fit:contain;background:#fff}
#lbc{color:var(--dim);font-size:13px}
footer{border-top:1px solid var(--line);margin-top:36px;padding:20px 0 30px;color:var(--dim);font-size:12.5px}
code{background:#1b1b22;padding:1px 5px;border-radius:4px;font-size:12px}
textarea{display:none;width:100%;height:150px;margin-top:10px;background:#0b0b0e;color:#c3c3ce;
 border:1px solid var(--line);border-radius:6px;font:12px ui-monospace,monospace;padding:8px}
</style>
<div class='wrap'><h1>v3.5 link A &mdash; what call 1 does to the reference</h1></div>
"""

LEDE = """<p class='lede'>The v3.4 lock asks call 1 for two things in one sentence:
<b>replace the head with a mannequin head</b> and <b>re-pose the wearer front-on</b>. This
page separates them. Every arm starts from the same A4 crop, one klein call, seed 46, on
fal &mdash; <b>M1</b> is the turn with no mannequin sentence, <b>M2</b> is the same turn
with it, <b>M0</b> is the lock's own prompt as the control, <b>G1</b> asks for the clothing
with no wearer at all. The <b>c</b> columns are those references with the head subtracted
by the incumbent <code>BC</code> cropper &mdash; no model call, so they are free, and
<b>M1c</b> is the shape this experiment is aiming at. What to look at per cell: <b>did the
wearer turn front-on</b>, <b>did the garment survive unchanged</b> (same pieces, same
length, same colour &mdash; the F3 failure v3.4 carried open) and <b>is the head
gone</b>. Turn columns off to put any two arms side by side. Click any image for full
size.</p>"""

TOOLBAR = """<div id='bar'>
<span class='grp'><span class='lbl'>columns</span>{{COLS}}
<button id='only-m'>M1 vs M1c only</button><button id='all-c'>all</button></span>
<span class='grp'><span class='lbl'>framing</span>
<button class='f on' data-f='all'>all</button><button class='f' data-f='full_body'>full_body</button>
<button class='f' data-f='waist_up'>waist_up</button><button class='f' data-f='knee_up'>knee_up</button>
<button class='f' data-f='chest_up'>chest_up</button></span>
<span class='grp'><span class='lbl'>fit</span><button id='tall'>true aspect</button>
<button id='export'>Export CSV</button></span>
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

const boxes=[...document.querySelectorAll('#bar input[data-col]')];
function cols(){let n=0;boxes.forEach(b=>{const on=b.checked;n+=on;
  document.querySelectorAll('figure.c-'+b.dataset.col).forEach(f=>f.style.display=on?'':'none');});
 document.querySelectorAll('.cols').forEach(c=>c.style.setProperty('--n',Math.max(n,1)));}
boxes.forEach(b=>b.onchange=cols);
document.getElementById('only-m').onclick=()=>{boxes.forEach(b=>
  b.checked=['crop','M1','M1c'].includes(b.dataset.col));cols();};
document.getElementById('all-c').onclick=()=>{boxes.forEach(b=>b.checked=true);cols();};
document.getElementById('tall').onclick=e=>{document.body.classList.toggle('tall');
  e.target.classList.toggle('on');};
document.querySelectorAll('#bar .f').forEach(b=>b.onclick=()=>{
  document.querySelectorAll('#bar .f').forEach(x=>x.classList.toggle('on',x===b));
  document.querySelectorAll('.card').forEach(c=>c.style.display=
    (b.dataset.f==='all'||c.dataset.framing===b.dataset.f)?'':'none');});

const KEY='v35-linkA-best';let v={};try{v=JSON.parse(localStorage.getItem(KEY)||'{}')}catch(e){}
function paint(){const t={};
 document.querySelectorAll('.vote').forEach(w=>{const pick=v[w.dataset.g];
  w.querySelectorAll('button').forEach(b=>b.classList.toggle('on',b.dataset.v===pick));
  if(pick)t[pick]=(t[pick]||0)+1;});
 const n=Object.values(t).reduce((a,b)=>a+b,0);
 document.getElementById('tally').textContent=n?('marked '+n+' · '+
   Object.entries(t).sort((a,b)=>b[1]-a[1]).map(([k,c])=>k+' '+c).join(' · ')):'no marks yet';}
document.addEventListener('click',e=>{const b=e.target.closest('.vote button');if(!b)return;
 const g=b.closest('.vote').dataset.g;v[g]=(v[g]===b.dataset.v)?undefined:b.dataset.v;
 try{localStorage.setItem(KEY,JSON.stringify(v))}catch(x){}paint();});
document.getElementById('export').onclick=()=>{let csv='garment,framing,best_reference\\n';
 document.querySelectorAll('.card').forEach(c=>{const g=c.dataset.g;
  csv+=g+','+c.dataset.framing+','+(v[g]||'')+'\\n';});
 const box=document.getElementById('csvbox');box.style.display='block';box.value=csv;box.select();
 try{const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([csv],{type:'text/csv'}));
  a.download='v35_linkA_best.csv';a.click();}catch(x){}};
cols();paint();</script>"""

if __name__ == "__main__":
    main()
