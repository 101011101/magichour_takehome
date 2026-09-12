"""The v3.10 marking page - the shipped canvas rule against the no-upscale candidate, blind.

One card per cell whose two canvases differ: SCALE against NOSCALE, arm hidden, sides shuffled
per card and the card order shuffled, all at a fixed seed. The prior verdict (did this cell
already pass) is carried in the card's data and the export but is NOT shown, so one bar covers
both groups; the split happens at analysis time, not at marking time.

WHY ONE SHUFFLED STREAM AND NOT TWO SITTINGS. v3.8's most expensive lesson was that the same
reviewer's bar moved 1.72x between two sittings on the same 600 cells. Marking the clean cells
in one sitting and the failing cells in another would reintroduce exactly that, on the axis the
whole run is about. So every card sits in one shuffled stream: mark as far as you get, and
because the order is shuffled a partial pass is still a random sample of both groups. Progress
survives a reload.

THE RESOLUTION TELL. NOSCALE's canvas is 0.57-0.85 of SCALE's in area, so a reviewer could pick
the arm out by pixel count rather than by content. Both sides are therefore resampled to the
SAME display width, the lightbox copies are resampled the same way, and the card does not print
either size. The true pixel sizes are carried in the export (wh_A, wh_B).

  python3 v3/build/v310_page.py [run_dir] [out_html] [--clean N]
      defaults: v3/runs/v310/a100  ->  v3/report/v310.html
      --clean N  keep only N of the prior-clean cards, sampled at SEED, for a shorter sitting;
                 the footer and the export record the denominator it was drawn from
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

RUN = os.path.join(REPO, "v3", "runs", "v310", "a100")
OUT = os.path.join(REPO, "v3", "report", "v310.html")
SEED = 46
BASE = "SCALE"
ARM = "NOSCALE"
CARD_W = 460          # every output is rendered at exactly this width, whatever its canvas


def web(src, img_dir, width, exact=False):
    """Copy an image into the page's folder under a hashed name - the name must not say which
    arm made it. exact=True resamples up or down to `width`, so two canvases of different size
    cannot be told apart by how big they render."""
    if not os.path.exists(src):
        return None, None, None
    h = hashlib.md5(f"v310|{os.path.basename(src)}|{width}|{int(exact)}".encode()).hexdigest()[:14]
    out, full = os.path.join(img_dir, f"{h}.jpg"), os.path.join(img_dir, f"{h}@full.jpg")
    im = Image.open(src).convert("RGB")
    wh = f"{im.width}x{im.height}"
    if not os.path.exists(out) or not os.path.exists(full):
        t = (im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
             if exact or im.width > width else im)
        t.save(out, quality=90, optimize=True)
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


def main(run=RUN, out=OUT, clean_n=None):
    img_dir = os.path.join(os.path.dirname(out), "img_v310")
    os.makedirs(img_dir, exist_ok=True)
    matrix = os.path.join(run, "v310_set.csv")
    if not os.path.exists(matrix):
        matrix = os.path.join(REPO, "v3", "colab", "v310_set.csv")
    rows = list(csv.DictReader(open(matrix)))
    mp = os.path.join(run, "meta", "v310_meta.json")
    meta = json.load(open(mp)) if os.path.exists(mp) else {"cells": {}}
    rng = random.Random(SEED)

    todo, noops, missing = [], [], []
    for r in rows:
        sid, sd = r["set_id"], r["seed"]
        cm = meta["cells"].get(f"{sid}|{sd}", {})
        if cm.get("NOSCALE_noop", r.get("noscale_noop") == "1"):
            noops.append(f"{sid}@{sd}")
            continue
        gen = {a: os.path.join(run, "gen", f"{sid}__{a}__s{sd}.jpg") for a in (BASE, ARM)}
        if not all(os.path.exists(p) for p in gen.values()):
            missing.append(f"{sid}@{sd}")
            continue
        todo.append((r, gen))

    drawn_from = sum(1 for r, _ in todo if r["prior"] == "clean")
    if clean_n:
        clean = [t for t in todo if t[0]["prior"] == "clean"]
        keep = set(id(t) for t in random.Random(SEED).sample(clean, min(int(clean_n), len(clean))))
        todo = [t for t in todo if t[0]["prior"] != "clean" or id(t) in keep]

    cards = []
    for r, gen in todo:
        sid, sd, g = r["set_id"], r["seed"], r["garment"]
        left, right = (BASE, ARM) if rng.random() < 0.5 else (ARM, BASE)
        src = [fig(os.path.join(run, "in1mp", f"{r['person']}.jpg"), img_dir,
                   "the person (image 1)")[0],
               fig(os.path.join(run, "refs", f"{g}__BC.jpg"), img_dir,
                   "the reference (image 2)")[0]]
        fa, wha = fig(gen[left], img_dir, "A", CARD_W, exact=True)
        fb, whb = fig(gen[right], img_dir, "B", CARD_W, exact=True)
        cards.append(
            f"<div class='cellcard' data-sid='{html.escape(sid)}' data-seed='{sd}' "
            f"data-prior='{r['prior']}' data-a='{left}' data-b='{right}' "
            f"data-wha='{wha}' data-whb='{whb}'>"
            f"<div class='ch'><b>{html.escape(sid)}</b><span class='t'>seed {sd}</span>"
            "<span class='marks'>"
            "<button class='v' data-v='A'>A better</button>"
            "<button class='v' data-v='same'>same</button>"
            "<button class='v' data-v='B'>B better</button>"
            "<button class='v' data-v='both_bad'>both bad</button>"
            "</span></div>"
            f"<div class='cellbody'><div class='src'>{''.join(src)}</div>"
            f"<div class='outs'>{fa}{fb}</div></div></div>")
    rng.shuffle(cards)

    n_fail = sum(1 for r, _ in todo if r["prior"] == "fail")
    n_clean = len(todo) - n_fail
    sampled = (f" &middot; <b>prior-clean cards sampled: {n_clean} of {drawn_from}</b> at seed "
               f"{SEED}" if clean_n else "")
    page = f"""{R.HEAD.replace('TITLE', 'v3.10 - the canvas without the upscale, on the whole fold')}
<div class='wrap'>
<p class='lede'><b>{len(cards)} comparisons</b> &mdash; the shipped call-2 canvas against the
same cell with the upscale removed, on the same transformer, reference, seed and person, every
photo bounded to 1 MP. Which side is which is hidden and shuffled, <b>and so is whether the
cell already passed its blind count</b> &mdash; that split is the point of the run and it is
applied afterwards, so one bar covers every card. <b>Both sides are rendered at the same width
on purpose</b>: one arm's canvas is genuinely smaller, and the question is which image you
would ship, not which file is larger. Mark one &mdash; or <i>same</i>, or <i>both bad</i>.
Marks survive a reload; the order is shuffled, so stopping part-way still leaves a random
sample of both groups.</p>
{BAR}
{''.join(cards)}
<footer>{len(rows)} cells of <code>v310_set.csv</code> &middot; cards {len(cards)}
(prior fail {n_fail}, prior clean {n_clean}){sampled} &middot; sides and order shuffled with
seed {SEED} &middot; <b>{len(noops)} no-ops</b> (the person photo is already at the bound, so
both rules give one canvas and there is nothing to compare) &middot; missing:
{len(missing)} &middot; true canvas sizes are in the export, not on the card &middot; rebuild:
<code>python3 v3/build/v310_page.py</code></footer>
</div>{R.LB}{R.SCRIPT}{SCRIPT}"""
    open(out, "w").write(page)
    print(f"{os.path.relpath(out, REPO) if out.startswith(REPO) else out}  "
          f"({len(cards)} cards: prior fail {n_fail}, prior clean {n_clean}; "
          f"{len(noops)} no-ops; {len(missing)} missing)")


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
const K='v310-marks-v1';let m={};try{m=JSON.parse(localStorage.getItem(K)||'{}')}catch(e){}
const cards=[...document.querySelectorAll('.cellcard')];
const key=c=>c.dataset.sid+'|'+c.dataset.seed;
function verdict(c,v){if(!v)return '';if(v==='same'||v==='both_bad')return v;
 const w=v==='A'?c.dataset.a:c.dataset.b;return w==='SCALE'?'baseline_better':'arm_better';}
function paint(){
 const t={arm_better:0,baseline_better:0,same:0,both_bad:0};
 cards.forEach(c=>{const v=m[key(c)];
  c.querySelectorAll('.marks button').forEach(b=>b.classList.toggle('on',v===b.dataset.v));
  if(v)t[verdict(c,v)]++;});
 document.getElementById('tally').textContent=Object.keys(m).length+'/'+cards.length+' judged  '
  +'no-upscale '+t.arm_better+' / shipped '+t.baseline_better+' / same '+t.same
  +' / both bad '+t.both_bad;}
document.addEventListener('click',e=>{const b=e.target.closest('.marks button');if(!b)return;
 const c=b.closest('.cellcard'),k=key(c);
 m[k]=(m[k]===b.dataset.v)?undefined:b.dataset.v;if(!m[k])delete m[k];
 try{localStorage.setItem(K,JSON.stringify(m))}catch(x){}paint();});
document.getElementById('reset').onclick=()=>{if(!confirm('clear?'))return;m={};
 try{localStorage.removeItem(K)}catch(x){}paint();};
document.getElementById('export').onclick=()=>{
 let csv='set_id,seed,prior,shown_A,shown_B,wh_A,wh_B,answer,verdict\\n';
 cards.forEach(c=>{const v=m[key(c)]||'';
  csv+=[c.dataset.sid,c.dataset.seed,c.dataset.prior,c.dataset.a,c.dataset.b,
        c.dataset.wha,c.dataset.whb,v,verdict(c,v)].join(',')+'\\n';});
 const t=document.getElementById('csvbox');t.style.display='block';t.value=csv;t.select();
 try{const a=document.createElement('a');
  a.href=URL.createObjectURL(new Blob([csv],{type:'text/csv'}));
  a.download='v310_marks.csv';a.click();}catch(x){}};
paint();</script>"""


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    n = next((sys.argv[i + 1] for i, a in enumerate(sys.argv) if a == "--clean"), None)
    main(*(args + [RUN, OUT][len(args):]), clean_n=n)
