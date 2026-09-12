"""The Inquiry Confirmation marking page - three blind A/B blocks, one per open inquiry.

  upscale       SCALE vs NOSCALE   call 2's canvas, scaled to 1 MP or left alone   (v3.9)
  crop2         SCALE vs CROP2     one crop or two                                 (v3.9)
  garment_only  PROD vs NOBALD     a product shot through the bald pass, or straight
                                   to call 2 with the background removed

Arm labels are hidden, sides shuffled per card and the card order shuffled within each
block, all at a fixed seed; image files are named by hash so the page source does not name
the arm.  One question per card: A better, same, B better, both bad.

THE RESOLUTION TELL.  NOSCALE's canvas is smaller than SCALE's, so a reviewer could pick the
arm out by pixel count rather than by content.  Every output is therefore resampled to the
SAME display width and the card prints no size; the true sizes ride in the export (wh_A,
wh_B) so the marks can still be read against canvas area.

  python3 v3/build/inquiry_page.py [run_dir] [out_html]
      defaults: v3/runs/inquiry/a100  ->  v3/report/inquiry.html
      run_dir holds the unpacked notebook zip: v39/{gen,refs,in1mp,meta} and
      inquiry/{gen,refs,in1mp,meta}
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

RUN = os.path.join(REPO, "v3", "runs", "inquiry", "a100")
OUT = os.path.join(REPO, "v3", "report", "inquiry.html")
MARKS = "inquiry_marks.csv"
SEED = 46
CARD_W = 460
BLOCKS = {"upscale": ("SCALE", "NOSCALE", "call-2 canvas: scaled to 1 MP vs never upscaled"),
          "crop2": ("SCALE", "CROP2", "one crop vs two"),
          "garment_only": ("PROD", "NOBALD", "product shot: through the bald pass vs straight in")}


def web(src, img_dir, width, exact=False):
    """Copy an image into the page's folder under a hashed name - the name must not say which
    arm made it.  exact=True resamples up or down to `width`, so two canvases of different
    size cannot be told apart by how big they render."""
    if not os.path.exists(src):
        return None, None, None
    h = hashlib.md5(f"inq|{src}|{width}|{int(exact)}".encode()).hexdigest()[:14]
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


def card(block, sid, seed, group, base, arm, a_src, b_src, sources, img_dir, rng):
    left, right = (base, arm) if rng.random() < 0.5 else (arm, base)
    paths = {base: a_src, arm: b_src}
    fa, wha = fig(paths[left], img_dir, "A", CARD_W, exact=True)
    fb, whb = fig(paths[right], img_dir, "B", CARD_W, exact=True)
    if not (fa and fb):
        return None
    return (f"<div class='cellcard' data-block='{block}' data-sid='{html.escape(sid)}' "
            f"data-seed='{seed}' data-group='{group}' data-base='{base}' "
            f"data-a='{left}' data-b='{right}' data-wha='{wha}' data-whb='{whb}'>"
            f"<div class='ch'><b>{html.escape(sid)}</b><span class='t'>seed {seed} &middot; "
            f"{BLOCKS[block][2]}</span><span class='marks'>"
            "<button class='v' data-v='A'>A better</button>"
            "<button class='v' data-v='same'>same</button>"
            "<button class='v' data-v='B'>B better</button>"
            "<button class='v' data-v='both_bad'>both bad</button>"
            "</span></div>"
            f"<div class='cellbody'><div class='src'>{''.join(s for s in sources if s)}</div>"
            f"<div class='outs'>{fa}{fb}</div></div></div>")


def v39_cards(run, img_dir, rng):
    """The two v3.9 blocks.  Cells whose NOSCALE canvas equals SCALE's are no-ops."""
    d = os.path.join(run, "v39")
    matrix = os.path.join(d, "v39_set.csv")
    if not os.path.exists(matrix):
        matrix = os.path.join(REPO, "v3", "colab", "v39_set.csv")
    if not os.path.exists(matrix):
        return [], []
    rows = list(csv.DictReader(open(matrix)))
    mp = os.path.join(d, "meta", "v39_meta.json")
    meta = json.load(open(mp)) if os.path.exists(mp) else {"cells": {}}
    out, noops = [], []
    for r in rows:
        sid, sd, g = r["set_id"], r["seed"], r["garment"]
        cm = meta["cells"].get(f"{sid}|{sd}", {})
        noop = cm.get("NOSCALE_noop", r.get("noscale_noop") == "1")
        gen = lambda a: os.path.join(d, "gen", f"{sid}__{a}__s{sd}.jpg")    # noqa: E731
        person = fig(os.path.join(d, "in1mp", f"{r['person']}.jpg"), img_dir,
                     "the person (image 1)")[0]
        for block, (base, arm, _) in BLOCKS.items():
            if block == "garment_only":
                continue
            if arm == "NOSCALE" and noop:
                noops.append(f"{sid}@{sd}")
                continue
            src = [person]
            if arm == "CROP2":
                src += [fig(os.path.join(d, "refs", f"{g}__1crop.jpg"), img_dir,
                            "reference &middot; one crop")[0],
                        fig(os.path.join(d, "refs", f"{g}__2crop.jpg"), img_dir,
                            "reference &middot; two crops")[0]]
            else:
                src += [fig(os.path.join(d, "refs", f"{g}__1crop.jpg"), img_dir,
                            "the reference (image 2)")[0]]
            c = card(block, sid, sd, r.get("group", ""), base, arm,
                     gen(base), gen(arm), src, img_dir, rng)
            if c:
                out.append(c)
    return out, noops


def garment_cards(run, img_dir, rng):
    """The garment-only block: every product shot against every person it was paired with."""
    d = os.path.join(run, "inquiry")
    gen = os.path.join(d, "gen")
    if not os.path.isdir(gen):
        return [], {}
    meta_p = os.path.join(d, "meta", "garment_only.json")
    meta = json.load(open(meta_p)) if os.path.exists(meta_p) else {}
    base, arm, _ = BLOCKS["garment_only"]
    out = []
    for f in sorted(os.listdir(gen)):
        if not f.endswith(".jpg") or f"__{base}__" not in f:
            continue
        sid, rest = f.split("__", 1)
        seed = rest.rsplit("__s", 1)[1][:-len(".jpg")]
        g = sid.split("+")[1]
        person = sid.split("+")[0]
        m = meta.get(g, {})
        note = (f"product shot &middot; parser found a head: {m.get('cranium_used')} &middot; "
                f"bald pass changed {m.get('bald_changed_pct', '?')}% of pixels")
        src = [fig(os.path.join(d, "in1mp", f"{person}.jpg"), img_dir, "the person (image 1)")[0],
               fig(os.path.join(d, "inputs", f"{g}.jpg"), img_dir, "the product shot")[0]
               or fig(os.path.join(d, "in1mp", f"{g}.jpg"), img_dir, "the product shot")[0],
               fig(os.path.join(d, "refs", f"{g}__{base}.jpg"), img_dir,
                   "reference &middot; bald pass then crop")[0],
               fig(os.path.join(d, "refs", f"{g}__{arm}.jpg"), img_dir,
                   "reference &middot; crop only")[0]]
        c = card("garment_only", sid, seed, note, base, arm,
                 os.path.join(gen, f), os.path.join(gen, f.replace(f"__{base}__", f"__{arm}__")),
                 src, img_dir, rng)
        if c:
            out.append(c)
    return out, meta


def main(run=RUN, out=OUT):
    img_dir = os.path.join(os.path.dirname(out), "img_inquiry")
    os.makedirs(img_dir, exist_ok=True)
    rng = random.Random(SEED)
    cards, noops = v39_cards(run, img_dir, rng)
    gcards, gmeta = garment_cards(run, img_dir, rng)
    rng.shuffle(cards)
    rng.shuffle(gcards)
    cards += gcards
    n = {b: sum(f"data-block='{b}'" in c for c in cards) for b in BLOCKS}
    fired = sorted(g for g, v in gmeta.items() if v.get("cranium_used"))

    page = f"""{R.HEAD.replace('TITLE', 'Inquiry Confirmation')}
<div class='wrap'>
<p class='lede'><b>{len(cards)} comparisons across three inquiries.</b> Each card is one
question, one seed, one person: which side would you ship. Which arm made which side is
hidden and shuffled. <b>Both sides render at the same width on purpose</b> &mdash; one arm's
canvas is genuinely smaller, and the question is which image you would ship, not which file
is larger. Mark one &mdash; or <i>same</i>, or <i>both bad</i>.</p>
<p class='lede'>Blocks: <b>{n['upscale']}</b> the upscale &middot; <b>{n['crop2']}</b> the
second crop &middot; <b>{n['garment_only']}</b> product shots with no person in them, where
the question is whether the bald pass should run at all.</p>
{BAR}
{''.join(cards)}
<footer><b>{len(noops)} NOSCALE no-ops</b> (canvas identical to the baseline's, not
generated): {html.escape(', '.join(noops)) or 'none'} &middot; product shots where the parser
found a head: {html.escape(', '.join(fired)) or 'none'} &middot; sides and order shuffled with
seed {SEED} &middot; true canvas sizes are in the export, not on the card &middot; rebuild:
<code>python3 v3/build/inquiry_page.py</code></footer>
</div>{R.LB}{R.SCRIPT}{SCRIPT}"""
    open(out, "w").write(page)
    print(f"{os.path.relpath(out, REPO) if out.startswith(REPO) else out}  "
          f"({len(cards)} cards: {n}; {len(noops)} no-ops)")


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
const K='inquiry-marks-v1';let m={};try{m=JSON.parse(localStorage.getItem(K)||'{}')}catch(e){}
const cards=[...document.querySelectorAll('.cellcard')];
const key=c=>c.dataset.block+'|'+c.dataset.sid+'|'+c.dataset.seed;
function verdict(c,v){if(!v)return '';if(v==='same'||v==='both_bad')return v;
 const w=v==='A'?c.dataset.a:c.dataset.b;return w===c.dataset.base?'baseline_better':'arm_better';}
function paint(){
 const t={};cards.forEach(c=>{const v=m[key(c)];
  c.querySelectorAll('.marks button').forEach(b=>b.classList.toggle('on',v===b.dataset.v));
  if(!v)return;const a=c.dataset.block;
  t[a]=t[a]||{arm_better:0,baseline_better:0,same:0,both_bad:0};t[a][verdict(c,v)]++;});
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
 let csv='block,set_id,seed,group,baseline,shown_A,shown_B,wh_A,wh_B,answer,verdict\\n';
 cards.forEach(c=>{const v=m[key(c)]||'';
  csv+=[c.dataset.block,c.dataset.sid,c.dataset.seed,'"'+(c.dataset.group||'')+'"',
        c.dataset.base,c.dataset.a,c.dataset.b,c.dataset.wha,c.dataset.whb,v,
        verdict(c,v)].join(',')+'\\n';});
 const t=document.getElementById('csvbox');t.style.display='block';t.value=csv;t.select();
 try{const a=document.createElement('a');
  a.href=URL.createObjectURL(new Blob([csv],{type:'text/csv'}));
  a.download='MARKSFILE';a.click();}catch(x){}};
paint();</script>""".replace("MARKSFILE", MARKS)


if __name__ == "__main__":
    main(*sys.argv[1:3])
