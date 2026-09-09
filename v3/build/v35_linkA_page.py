"""Build the v3.5 link-A page: what call 1 does to the reference, four ways.

Per garment: the A4 crop it starts from, the v3.4 lock's own A100 reference for context,
then the four fal arms at seed 46 and the derived head crop. Unblinded - the question is
not which is prettier but three readable facts per cell: did the wearer turn front-on, did
the garment survive unchanged, and is the head gone.
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

# tag, where it comes from, label, one-line character
COLS = [
    ("crop", "src", "A4 crop", "what call 1 is given"),
    ("VEi", "lock", "VEi (A100)", "the v3.4 lock's own reference - different backend, context only"),
    ("M0", "fal", "M0 mannequin + repose", "the lock's Q3 verbatim, on fal - the control"),
    ("M1", "fal", "M1 turn only", "no mannequin sentence; the face survives"),
    ("M1c", "derived", "M1c turn + head cut", "M1 through BC's own head subtraction - no model call"),
    ("M2", "fal", "M2 mannequin + turn", "M1 plus the mannequin sentence"),
    ("G1", "fal", "G1 garment only", "the clothing alone, wearer removed"),
]


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
    prompts = {}
    for r in csv.DictReader(open(os.path.join(RUN, "meta", "prompts.csv"))):
        prompts.setdefault(r["arm"], r["prompt"])       # one example per arm, framing varies
    framing = {r["garment"]: r["framing"] for r in csv.DictReader(open(os.path.join(RUN, "meta", "prompts.csv")))}
    garments = sorted(framing)

    o = [HEAD, "<div class='wrap'>"]
    for tag, kind, label, ch in COLS:
        if kind != "fal":
            continue
        o.append(f"<div class='prompt'><div class='ph'><b>{tag}</b>"
                 f"<span>{html.escape(label)} &mdash; {html.escape(ch)}</span></div>"
                 f"<pre>{html.escape(prompts.get(tag, '-'))}</pre></div>")
    o.append(LEDE)

    cards, made = [], 0
    for g in garments:
        cells = []
        for tag, kind, label, _ in COLS:
            t, f = web(path_for(tag, kind, g), f"{g}__{tag}.jpg")
            cells.append((tag, label, t, f))
        if not any(t for _, _, t, _ in cells[2:]):
            continue
        made += 1
        cards.append(
            f"<div class='card'><div class='ch'><b>{html.escape(g)}</b>"
            f"<span class='t'>{framing[g]}</span></div><div class='cols'>"
            + "".join(
                (f"<figure class='{tag}'><img src='{t}' data-full='{f}' "
                 f"alt='{html.escape(g)} {tag}' loading='lazy'>"
                 f"<figcaption>{html.escape(label)}</figcaption></figure>") if t else
                (f"<figure><div class='miss'>not run</div>"
                 f"<figcaption>{html.escape(label)}</figcaption></figure>")
                for tag, label, t, f in cells)
            + "</div></div>")
    o.append(f"<div class='grid'>{''.join(cards)}</div>")
    o.append(f"<footer>{made} garments &middot; {meta['calls']} klein calls on "
             f"<code>{meta['endpoint']}</code>, seed {meta['seed']}, "
             f"${meta['usd']:.2f} &middot; canvas: {html.escape(meta['canvas_rule'])} "
             "&middot; crops and framing reused from "
             f"<code>{html.escape(meta['source_run'])}</code> &middot; "
             "<code>v3/runs/v35/linkA/refs/{g}__{M0,M1,M1c,M2,G1}.jpg</code> &middot; "
             "rebuild: <code>python3 v3/build/v35_linkA_page.py</code>.</footer></div>")
    o.append(LB + SCRIPT)
    open(os.path.join(REPORT, "v35_linkA.html"), "w").write("\n".join(o))
    print(f"v3/report/v35_linkA.html  ({made} garments x {len(COLS)} columns)")


HEAD = """<title>v3.5 link A - what call 1 does to the reference</title>
<meta name='viewport' content='width=device-width,initial-scale=1'>
<style>
:root{--bg:#0d0d10;--fg:#e8e8ea;--dim:#8a8a94;--line:#26262c;--acc:#7c5cff;--mid:#d29922}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
 font:15px/1.6 ui-sans-serif,-apple-system,"Segoe UI",Roboto,sans-serif}
.wrap{max-width:1720px;margin:0 auto;padding:30px 26px 0}
h1{margin:0 0 6px;font-size:25px}
.lede{color:var(--dim);max-width:92ch;font-size:14px;margin:0 0 8px}
.lede b{color:var(--fg)}
.prompt{border:1px solid var(--line);border-radius:9px;background:#101014;margin:10px 0;overflow:hidden}
.prompt .ph{display:flex;gap:10px;align-items:center;padding:8px 15px;background:#141419;
 border-bottom:1px solid var(--line);font-size:13px;flex-wrap:wrap}
.prompt .ph b{font-size:14px}
.prompt .ph span{color:var(--dim);font-size:12.5px}
.prompt pre{margin:0;padding:12px 16px;font:13px/1.7 ui-monospace,SFMono-Regular,monospace;
 white-space:pre-wrap;color:#c3c3ce;background:#0b0b0e}
.grid{display:grid;grid-template-columns:1fr;gap:12px;margin-top:18px}
.card{border:1px solid var(--line);border-radius:9px;background:#101014;overflow:hidden}
.ch{display:flex;gap:8px;align-items:center;padding:7px 11px;background:#141419;
 border-bottom:1px solid var(--line);font-size:12px;flex-wrap:wrap}
.ch b{font-size:12.5px;word-break:break-all}
.t{font-size:9.5px;padding:1px 7px;border-radius:20px;background:#2a1a12;
 border:1px solid #6b4423;color:var(--mid)}
.cols{display:grid;grid-template-columns:repeat(7,1fr);gap:4px;padding:6px}
@media(max-width:1100px){.cols{grid-template-columns:repeat(4,1fr)}}
@media(max-width:640px){.cols{grid-template-columns:repeat(2,1fr)}}
.miss{background:#17171d;border:1px dashed var(--line);border-radius:5px;aspect-ratio:3/4;
 display:flex;align-items:center;justify-content:center;color:var(--dim);font-size:11px}
figure{margin:0}
figure img{width:100%;display:block;background:#fff;border-radius:5px;cursor:zoom-in;
 aspect-ratio:3/4;object-fit:contain;image-rendering:-webkit-optimize-contrast}
figure.M1 img,figure.M1c img{outline:2px solid #3b3160;outline-offset:-2px}
figure.crop figcaption,figure.VEi figcaption{color:var(--dim)}
figcaption{font-size:10.5px;color:var(--fg);text-align:center;padding:4px 2px}
#lb{display:none;position:fixed;inset:0;background:rgba(0,0,0,.95);z-index:99;
 align-items:center;justify-content:center;flex-direction:column;gap:10px;padding:20px}
#lb.on{display:flex}#lb img{max-width:95vw;max-height:90vh;object-fit:contain;background:#fff}
#lbc{color:var(--dim);font-size:13px}
footer{border-top:1px solid var(--line);margin-top:40px;padding:22px 0 30px;color:var(--dim);font-size:12.5px}
code{background:#1b1b22;padding:1px 5px;border-radius:4px;font-size:12px}
</style>
<div class='wrap'><h1>v3.5 link A &mdash; what call 1 does to the reference</h1>
<p class='lede'>The v3.4 lock asks call 1 for two things in one sentence: <b>replace the
head with a mannequin head</b> and <b>re-pose the wearer front-on</b>. This page separates
them. Every arm starts from the same A4 crop, one klein call, seed 46, on fal. The last
column asks for the clothing with no wearer at all; the <b>M1c</b> column is M1 with the
head subtracted by the incumbent <code>BC</code> cropper &mdash; no model call, so it is
free. Click any image for full size.</p></div>
"""

LEDE = """<p class='lede'>What to look at, per cell: <b>did the wearer turn front-on</b>
(the backview dress is the case of record), <b>did the garment survive unchanged</b>
&mdash; same pieces, same length, same colour, the F3 failure v3.4 carried open &mdash;
and <b>is the head gone</b>. M1 keeps the face by construction; that is what M1c is
for.</p>"""

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
</script>"""

if __name__ == "__main__":
    main()
