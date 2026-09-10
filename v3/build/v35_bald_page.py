"""Build the bald-probe page: does one klein call re-pose AND bald the wearer?

`BC` bald-passes the raw photograph before it crops, because hair on the shoulders and
chest cannot be told from garment by any matte. `VEi` gets it free — the mannequin sentence
takes the head and its hair together. The re-pose arm does neither, so this page asks
whether one added sentence closes the gap.

Five garments, ranked by the quantity V2 itself gates on: garment lost to hair removal.
"""
import csv
import html
import json
import os

from PIL import Image

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RUN = os.path.join(REPO, "v3", "runs", "v35", "bald_probe")
LINKA = os.path.join(REPO, "v3", "runs", "v35", "linkA", "refs")
SRC = os.path.join(REPO, "v3", "runs", "v34", "ironman2")
REPORT = os.path.join(REPO, "v3", "report")
IMG = os.path.join(REPORT, "img_v35bald")

COLS = [("crop", "A4 crop", "what call 1 is given"),
        ("M0", "M0 — mannequin", "the lock's Q3: head replaced, hair goes with it"),
        ("M1q", "M1q — re-pose", "Q3 minus the mannequin sentence — hair kept"),
        ("M1qb", "M1qb — re-pose + bald", "M1q plus one sentence from v3lib.BALD_PROMPT")]


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
    return "img_v35bald/" + dst, "img_v35bald/" + os.path.basename(full)


def path_for(tag, g):
    if tag == "crop":
        return os.path.join(SRC, "inputs", f"{g}__A4.jpg")
    if tag == "M0":
        return os.path.join(LINKA, f"{g}__M0.jpg")
    return os.path.join(RUN, "refs", f"{g}__{tag}.jpg")


def main():
    os.makedirs(IMG, exist_ok=True)
    meta = json.load(open(os.path.join(RUN, "meta", "run.json")))
    rows = list(csv.DictReader(open(os.path.join(RUN, "meta", "probe.csv"))))
    prompts = {}
    for r in rows:
        prompts.setdefault(r["arm"], r["prompt"])
    share = {r["garment"]: float(r["hair_share"]) for r in rows}
    garments = sorted(share, key=lambda g: -share[g])

    o = [HEAD, "<div class='wrap'>", LEDE]
    for tag in ("M1q", "M1qb"):
        o.append(f"<details class='prompt'{' open' if tag == 'M1qb' else ''}>"
                 f"<summary><b>{tag}</b> <span>{'the approved re-pose arm' if tag == 'M1q' else 'the same, with the bald sentence'}</span></summary>"
                 f"<pre>{html.escape(prompts.get(tag, '-'))}</pre></details>")

    cards = []
    for g in garments:
        cells = []
        for tag, label, _ in COLS:
            t, f = web(path_for(tag, g), f"{g}__{tag}.jpg")
            cells.append((tag, label, t, f))
        over = share[g] > 0.14
        cards.append(
            f"<div class='card'><div class='ch'><b>{html.escape(g)}</b>"
            f"<span class='t{' over' if over else ''}'>hair share {share[g]:.3f}"
            f"{' — over V2&rsquo;s 0.14' if over else ''}</span></div><div class='cols'>"
            + "".join(
                (f"<figure class='c-{tag}'><img src='{t}' data-full='{f}' "
                 f"alt='{html.escape(g)} {tag}' loading='lazy'>"
                 f"<figcaption>{html.escape(label)}</figcaption></figure>") if t else
                (f"<figure class='c-{tag}'><div class='miss'>not run</div>"
                 f"<figcaption>{html.escape(label)}</figcaption></figure>")
                for tag, label, t, f in cells)
            + "</div></div>")

    o += [f"<div class='grid'>{''.join(cards)}</div>",
          f"<footer>{len(garments)} garments &middot; {meta['calls']} klein calls on "
          f"<code>{meta['endpoint']}</code>, seed {meta['seed']}, ${meta['usd']:.2f} "
          f"&middot; <code>M0</code> reused from link A (same backend, same seed) &middot; "
          f"hair metric: {html.escape(meta['hair_metric'])} &middot; outputs "
          "<code>v3/runs/v35/bald_probe/refs/</code> &middot; rebuild: "
          "<code>python3 v3/build/v35_bald_page.py</code>.</footer></div>", LB, SCRIPT]
    open(os.path.join(REPORT, "v35_bald.html"), "w").write("\n".join(o))
    print(f"v3/report/v35_bald.html  ({len(garments)} garments x {len(COLS)} columns)")


HEAD = """<title>v3.5 - re-pose and bald in one call?</title>
<meta name='viewport' content='width=device-width,initial-scale=1'>
<style>
:root{--bg:#0d0d10;--fg:#e8e8ea;--dim:#8a8a94;--line:#26262c;--acc:#7c5cff;--mid:#d29922}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
 font:15px/1.6 ui-sans-serif,-apple-system,"Segoe UI",Roboto,sans-serif}
.wrap{max-width:1500px;margin:0 auto;padding:26px 22px 0}
h1{margin:0 0 6px;font-size:25px}
.lede{color:var(--dim);max-width:94ch;font-size:14px;margin:0 0 12px}
.lede b{color:var(--fg)}
.prompt{border:1px solid var(--line);border-radius:9px;background:#101014;margin:7px 0;overflow:hidden}
.prompt summary{padding:7px 14px;background:#141419;font-size:13px;cursor:pointer}
.prompt summary span{color:var(--dim);font-size:12.5px}
.prompt pre{margin:0;padding:12px 16px;font:13px/1.7 ui-monospace,SFMono-Regular,monospace;
 white-space:pre-wrap;color:#c3c3ce;background:#0b0b0e}
.grid{display:grid;grid-template-columns:1fr;gap:12px;margin-top:16px}
.card{border:1px solid var(--line);border-radius:9px;background:#101014;overflow:hidden}
.ch{display:flex;gap:9px;align-items:center;padding:7px 12px;background:#141419;
 border-bottom:1px solid var(--line);font-size:12px;flex-wrap:wrap}
.ch b{font-size:12.5px;word-break:break-all}
.t{font-size:10px;padding:1px 8px;border-radius:20px;background:#17171d;
 border:1px solid var(--line);color:var(--dim);font-family:ui-monospace,monospace}
.t.over{background:#2d1418;border-color:#8a2b34;color:#ff9aa2}
.cols{display:grid;grid-template-columns:repeat(4,1fr);gap:5px;padding:6px}
@media(max-width:760px){.cols{grid-template-columns:repeat(2,1fr)}}
figure{margin:0}
figure img{width:100%;display:block;background:#fff;border-radius:5px;cursor:zoom-in;
 aspect-ratio:2/3;object-fit:contain}
figure.c-M1qb img{outline:2px solid #2c5c33;outline-offset:-2px}
figure.c-M1qb figcaption{color:#7ee787;font-weight:600}
figure.c-crop figcaption{color:var(--dim)}
figcaption{font-size:11px;color:var(--fg);text-align:center;padding:4px 2px}
.miss{background:#17171d;border:1px dashed var(--line);border-radius:5px;aspect-ratio:2/3;
 display:flex;align-items:center;justify-content:center;color:var(--dim);font-size:11px}
#lb{display:none;position:fixed;inset:0;background:rgba(0,0,0,.95);z-index:99;
 align-items:center;justify-content:center;flex-direction:column;gap:10px;padding:20px}
#lb.on{display:flex}#lb img{max-width:95vw;max-height:90vh;object-fit:contain;background:#fff}
#lbc{color:var(--dim);font-size:13px}
footer{border-top:1px solid var(--line);margin-top:36px;padding:20px 0 30px;color:var(--dim);font-size:12.5px}
code{background:#1b1b22;padding:1px 5px;border-radius:4px;font-size:12px}
</style>
<div class='wrap'><h1>Re-pose and bald in one call?</h1></div>
"""

LEDE = """<p class='lede'><b>BC</b> bald-passes the raw photograph before it crops, because
hair on the shoulders and chest cannot be told from garment by any matte. <b>VEi</b> gets
that free &mdash; the mannequin sentence takes the head and its hair together. The re-pose
arm <b>M1q</b> does neither: it keeps the wearer's own head, so cropping it leaves whatever
hair spilled onto the garment. <b>M1qb</b> adds one sentence, lifted from
<code>v3lib.BALD_PROMPT</code> so the wording is the record's. Five garments, ranked by the
quantity V2 itself gates on &mdash; <b>garment lost to hair removal</b>, measured as
<code>c32_no_face_keep_hair</code> minus <code>c3_no_face</code>; V2 routes to BC_klein
above <b>0.14</b>, and four of these five are over it. One klein call each, seed 46, on
fal. Click any image for full size.</p>"""

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
