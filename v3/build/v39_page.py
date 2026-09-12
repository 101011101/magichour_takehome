"""The v3.9 marking page - each arm against a fresh SCALE baseline, judged blind.

For every cell, up to two cards: SCALE against NOSCALE (skipped where the two canvases are
identical - a no-op, listed in the footer) and SCALE against CROP2. Arm labels are hidden,
sides shuffled per card and the card order shuffled, all at a fixed seed; the group (fail /
clean) is hidden too, and image files are named by hash so the page source does not name the
arm. One question: A better, same, B better, both bad.

THE RESOLUTION TELL. NOSCALE's canvas is 0.57-0.85 of SCALE's in area, so a reviewer could
pick the arm out by pixel count rather than by content. Both sides are therefore resampled to
the SAME display width, and the card does not print either size. The true pixel sizes are
carried in the export (wh_A, wh_B) so the marks can still be read against canvas area.

  python3 v3/build/v39_page.py [run_dir] [out_html]
      defaults: v3/runs/v39/a100  ->  v3/report/v39.html
"""
import csv
import hashlib
import html
import json
import os
import random
import sys

from PIL import Image

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import v36_report as R                # noqa: E402  styles, lightbox

RUN = os.path.join(REPO, "v3", "runs", "v39", "a100")
OUT = os.path.join(REPO, "v3", "report", "v39.html")
SEED = 46
BASE = "SCALE"
ARMS = ("NOSCALE", "CROP2")
QUESTION = {"NOSCALE": "call-2 canvas: scaled to 1 MP vs never upscaled",
            "CROP2": "one crop vs two"}
CARD_W = 460          # every output is rendered at exactly this width, whatever its canvas


def web(src, img_dir, width, exact=False):
    """Copy an image into the page's folder under a hashed name - the name must not say which
    arm made it. exact=True resamples up or down to `width`, so two canvases of different size
    cannot be told apart by how big they render."""
    if not os.path.exists(src):
        return None, None, None
    h = hashlib.md5(f"v39|{os.path.basename(src)}|{width}|{int(exact)}".encode()).hexdigest()[:14]
    out, full = os.path.join(img_dir, f"{h}.jpg"), os.path.join(img_dir, f"{h}@full.jpg")
    im = Image.open(src).convert("RGB")
    wh = f"{im.width}x{im.height}"
    if not os.path.exists(out) or not os.path.exists(full):
        t = (im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
             if exact or im.width > width else im)
        t.save(out, quality=90, optimize=True)
        # the lightbox copy is resampled the same way, so a click cannot reveal the canvas
        (im.resize((1024, round(im.height * 1024 / im.width)), Image.LANCZOS)
         if exact else im).save(full, quality=94, optimize=True)
    rel = os.path.basename(img_dir)
    return f"{rel}/{h}.jpg", f"{rel}/{h}@full.jpg", wh


def fig(src, img_dir, cap, width=300, exact=False):
    t, f, wh = web(src, img_dir, width, exact)
    if not t:
        return "", None
    return (f"<figure><img src='{t}' data-full='{f}' alt='{html.escape(cap)}' loading='lazy'>"
            f"<figcaption>{cap}</figcaption></figure>"), wh


def main(run=RUN, out=OUT):
    img_dir = os.path.join(os.path.dirname(out), "img_v39")
    os.makedirs(img_dir, exist_ok=True)
    matrix = os.path.join(run, "v39_set.csv")
    if not os.path.exists(matrix):
        matrix = os.path.join(REPO, "v3", "colab", "v39_set.csv")
    rows = list(csv.DictReader(open(matrix)))
    mp = os.path.join(run, "meta", "v39_meta.json")
    meta = json.load(open(mp)) if os.path.exists(mp) else {"cells": {}}
    rng = random.Random(SEED)

    cards, noops, missing = [], [], []
    for r in rows:
        sid, sd, g = r["set_id"], r["seed"], r["garment"]
        cm = meta["cells"].get(f"{sid}|{sd}", {})
        noop = cm.get("NOSCALE_noop", r.get("noscale_noop") == "1")
        gen = lambda a: os.path.join(run, "gen", f"{sid}__{a}__s{sd}.jpg")    # noqa: E731
        for arm in ARMS:
            if arm == "NOSCALE" and noop:
                noops.append(f"{sid}@{sd}")
                continue
            if not (os.path.exists(gen(BASE)) and os.path.exists(gen(arm))):
                missing.append(f"{sid}@{sd}/{arm}")
                continue
            left, right = (BASE, arm) if rng.random() < 0.5 else (arm, BASE)
            src = [fig(os.path.join(run, "in1mp", f"{r['person']}.jpg"), img_dir,
                       "the person (image 1)")[0]]
            if arm == "CROP2":
                src += [fig(os.path.join(run, "refs", f"{g}__1crop.jpg"), img_dir, "reference &middot; one crop")[0],
                        fig(os.path.join(run, "refs", f"{g}__2crop.jpg"), img_dir, "reference &middot; two crops")[0]]
            else:
                src += [fig(os.path.join(run, "refs", f"{g}__1crop.jpg"), img_dir, "the reference (image 2)")[0]]
            fa, wha = fig(gen(left), img_dir, "A", CARD_W, exact=True)
            fb, whb = fig(gen(right), img_dir, "B", CARD_W, exact=True)
            cards.append(
                f"<div class='cellcard' data-sid='{html.escape(sid)}' data-seed='{sd}' "
                f"data-group='{r['group']}' data-cmp='{arm}' data-a='{left}' data-b='{right}' "
                f"data-wha='{wha}' data-whb='{whb}'>"
                f"<div class='ch'><b>{html.escape(sid)}</b><span class='t'>seed {sd} &middot; "
                f"{QUESTION[arm]}</span><span class='marks'>"
                "<button class='v' data-v='A'>A better</button>"
                "<button class='v' data-v='same'>same</button>"
                "<button class='v' data-v='B'>B better</button>"
                "<button class='v' data-v='both_bad'>both bad</button>"
                "</span></div>"
                f"<div class='cellbody'><div class='src'>{''.join(src)}</div>"
                f"<div class='outs'>{fa}{fb}</div></div></div>")
    rng.shuffle(cards)

    page = f"""{R.HEAD.replace('TITLE', 'v3.9 - crop twice, and the canvas without the upscale')}
<div class='wrap'>
<p class='lede'><b>{len(cards)} comparisons.</b> Each card is a fresh baseline against one arm,
on the same transformer, seed and person, every photo bounded to 1 MP. Which side is which is
hidden and shuffled, and so is whether the cell failed before. <b>Both sides are rendered at the
same width on purpose</b> &mdash; one arm's canvas is genuinely smaller, and the question is
which image you would ship, not which file is larger. Mark one &mdash; or <i>same</i>, or
<i>both bad</i>. The header says which question the card belongs to; it does not say which side
is the baseline.</p>
{BAR}
{''.join(cards)}
<footer>{len(rows)} cells of <code>v39_set.csv</code> &middot; sides and order shuffled with
seed {SEED} &middot; <b>{len(noops)} NOSCALE no-ops</b> (canvas identical to the baseline's,
not generated): {html.escape(', '.join(noops)) or 'none'} &middot; missing: {len(missing)}
&middot; true canvas sizes are in the export, not on the card &middot; rebuild:
<code>python3 v3/build/v39_page.py</code></footer>
</div>{R.LB}{R.SCRIPT}{SCRIPT}"""
    open(out, "w").write(page)
    n = {a: sum(f"data-cmp='{a}'" in c for c in cards) for a in ARMS}
    print(f"{os.path.relpath(out, REPO) if out.startswith(REPO) else out}  "
          f"({len(cards)} cards: {n}; {len(noops)} NOSCALE no-ops; {len(missing)} missing)")


BAR = """<div id='bar'>
<button id='export'>Export CSV</button><button id='reset'>clear</button>
<span id='tally'></span></div><textarea id='csvbox'></textarea>"""

SCRIPT = """<style>
#bar{position:sticky;top:0;z-index:40;display:flex;gap:10px;align-items:center;
 padding:10px 13px;margin:8px 0 14px;background:#141419;border:1px solid var(--line);
 border-radius:9px;font-size:13px}
#bar button{background:#101014;color:var(--fg);border:1px solid var(--line);
 border-radius:20px;padding:4px 12px;cursor:pointer;font:12px ui-sans-serif,sans-serif}
#tally{margin-left:auto;font:12px ui-monospace,monospace;color:var(--dim)}
.marks{margin-left:auto;display:flex;gap:5px}
.marks button{background:#101014;color:var(--dim);border:1px solid var(--line);
 border-radius:20px;padding:2px 11px;cursor:pointer;font:11px ui-sans-serif,sans-serif}
.marks button.on{background:var(--acc);border-color:var(--acc);color:#fff}
.outs figure img{width:460px;max-width:100%}
textarea{display:none;width:100%;height:160px;margin-top:10px;background:#0b0b0e;
 color:#c3c3ce;border:1px solid var(--line);border-radius:6px;
 font:12px ui-monospace,monospace;padding:8px}
</style>
<script>
const K='v39-marks-v2';let m={};try{m=JSON.parse(localStorage.getItem(K)||'{}')}catch(e){}
const cards=[...document.querySelectorAll('.cellcard')];
const key=c=>c.dataset.sid+'|'+c.dataset.seed+'|'+c.dataset.cmp;
function verdict(c,v){if(!v)return '';if(v==='same'||v==='both_bad')return v;
 const w=v==='A'?c.dataset.a:c.dataset.b;return w==='SCALE'?'baseline_better':'arm_better';}
function paint(){
 const t={};cards.forEach(c=>{const v=m[key(c)];
  c.querySelectorAll('.marks button').forEach(b=>b.classList.toggle('on',v===b.dataset.v));
  if(!v)return;const a=c.dataset.cmp;t[a]=t[a]||{arm_better:0,baseline_better:0,same:0,both_bad:0};
  t[a][verdict(c,v)]++;});
 document.getElementById('tally').textContent=Object.keys(m).length+'/'+cards.length+' judged  '
  +Object.entries(t).map(([a,n])=>a+': arm '+n.arm_better+' / baseline '+n.baseline_better
  +' / same '+n.same+' / both bad '+n.both_bad).join('  |  ');}
document.addEventListener('click',e=>{const b=e.target.closest('.marks button');if(!b)return;
 const c=b.closest('.cellcard'),k=key(c);
 m[k]=(m[k]===b.dataset.v)?undefined:b.dataset.v;if(!m[k])delete m[k];
 try{localStorage.setItem(K,JSON.stringify(m))}catch(x){}paint();});
document.getElementById('reset').onclick=()=>{if(!confirm('clear?'))return;m={};
 try{localStorage.removeItem(K)}catch(x){}paint();};
document.getElementById('export').onclick=()=>{
 let csv='set_id,seed,group,comparison,shown_A,shown_B,wh_A,wh_B,answer,verdict\\n';
 cards.forEach(c=>{const v=m[key(c)]||'';
  csv+=[c.dataset.sid,c.dataset.seed,c.dataset.group,c.dataset.cmp,c.dataset.a,c.dataset.b,
        c.dataset.wha,c.dataset.whb,v,verdict(c,v)].join(',')+'\\n';});
 const t=document.getElementById('csvbox');t.style.display='block';t.value=csv;t.select();
 try{const a=document.createElement('a');
  a.href=URL.createObjectURL(new Blob([csv],{type:'text/csv'}));
  a.download='v39_marks.csv';a.click();}catch(x){}};
paint();</script>"""


if __name__ == "__main__":
    main(*sys.argv[1:3])
