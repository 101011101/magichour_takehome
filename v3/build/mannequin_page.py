"""Build the v3.1 ghost-mannequin gallery: just the latest extractions.

All three mannequin prompts, all 28 references, side by side. Each card is the source
photograph and the three mannequins made from it - nothing else on the page, because
this is for judging the extraction on its own terms, before any edit is involved.

The three differ by one idea each: p3 asks for a ghost mannequin and nothing more, p5
adds a named list of accessory slots, p7 removes that list and forbids addition instead.
"""
import csv
import html
import os
import sys

from PIL import Image

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RUN = os.path.join(REPO, "v3", "runs", "v3.0b")
REPORT = os.path.join(REPO, "v3", "report")
IMG = os.path.join(REPORT, "img_mq")
# tag, prompt id, label, one-line character
SHAPES = [
    ("QM", "p3", "the original",
     "asks for a ghost mannequin and nothing more"),
    ("QMA", "p5", "slots named",
     "lists the accessory slots to include - and they get generated"),
    ("QMB", "p7", "current",
     "no list; forbids addition with a concrete example instead"),
]
sys.path.insert(0, os.path.join(REPO, "v3", "build"))
import run_v30 as R  # noqa: E402


def web(src, dst, width):
    """Returns (thumb, full). The lightbox must serve the original, not the thumb -
    an earlier version of this page pointed the lightbox at the 460px thumbnail, so
    clicking to inspect an extraction showed a smaller image than the file on disk."""
    if not os.path.exists(src):
        return None, None
    out = os.path.join(IMG, dst)
    full = os.path.join(IMG, dst.replace(".jpg", "@full.jpg"))
    im = None
    if not os.path.exists(out):
        im = Image.open(src).convert("RGB")
        t = im.resize((width, int(im.height * width / im.width)), Image.LANCZOS) \
            if im.width > width else im
        t.save(out, quality=90, optimize=True)
    if not os.path.exists(full):
        im = im or Image.open(src).convert("RGB")
        im.save(full, quality=94, optimize=True)
    return "img_mq/" + dst, "img_mq/" + os.path.basename(full)


def main():
    os.makedirs(IMG, exist_ok=True)
    rows = list(csv.DictReader(open(os.path.join(REPO, "v3/testsets/v30_matrix_b.csv"))))
    o = [HEAD, "<div class='wrap'>"]
    for tag, pid, label, character in SHAPES:
        o.append(f"<div class='prompt{' good' if tag == 'QMB' else ''}'>"
                 f"<div class='ph'><b>{tag}</b><code>{pid}</code>"
                 f"<span>{label} &mdash; {character}</span></div>"
                 f"<pre>{html.escape(R.EXTRACT[tag])}</pre></div>")
    o.append(LEDE)

    made = 0
    cards = []
    for r in rows:
        g = r["garment"]
        src, srcf = web(os.path.join(RUN, "inputs", f"{g}.jpg"), f"{g}__raw.jpg", 640)
        mqs = [(tag, pid) + web(os.path.join(RUN, "refs", f"{g}__{tag}.jpg"),
                                f"{g}__{tag}.jpg", 640)
               for tag, pid, _, _ in SHAPES]
        if not any(m for _, _, m, _ in mqs):
            continue
        made += 1
        bits = [b for b in (r["garment_category"], r["garment_hard_case"]) if b]
        tags = "".join(f"<span class='t'>{html.escape(b)}</span>" for b in bits)
        cards.append(
            f"<div class='card'><div class='ch'><b>{html.escape(g)}</b>{tags}"
            f"<span class='src'>{html.escape(r['garment_src'])}</span></div>"
            "<div class='four'>"
            f"<figure><img src='{src}' data-full='{srcf}' "
            f"alt='{html.escape(g)} source' loading='lazy'>"
            "<figcaption>source photograph</figcaption></figure>"
            + "".join(
                (f"<figure class='mq{' best' if tag == 'QMB' else ''}'>"
                 f"<img src='{m}' data-full='{mf}' alt='{html.escape(g)} {tag}' "
                 "loading='lazy'>"
                 f"<figcaption>{tag} &middot; {pid}</figcaption></figure>")
                if m else
                (f"<figure><div class='miss'>not run</div>"
                 f"<figcaption>{tag} &middot; {pid}</figcaption></figure>")
                for tag, pid, m, mf in mqs)
            + "</div></div>")
    o.append(f"<div class='grid'>{''.join(cards)}</div>")
    o.append(f"<footer>{made} references &times; {len(SHAPES)} prompts &middot; "
             "<code>v3/runs/v3.0b/refs/{ref}__{QM,QMA,QMB}.jpg</code> &middot; prompts "
             "of record: <code>EXTRACT</code> in <code>v3/build/run_v30.py</code>, each "
             "with the failure it produced in the comment above it. Rebuild: "
             "<code>python3 v3/build/mannequin_page.py</code>.</footer></div>")
    o.append(LB + SCRIPT)
    open(os.path.join(REPORT, "v31_mannequins.html"), "w").write("\n".join(o))
    print(f"v3/report/v31_mannequins.html  ({made} references x {len(SHAPES)} prompts)")


HEAD = """<title>Ghost mannequins</title>
<meta name='viewport' content='width=device-width,initial-scale=1'>
<style>
:root{--bg:#0d0d10;--fg:#e8e8ea;--dim:#8a8a94;--line:#26262c;--acc:#7c5cff;--mid:#d29922}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
 font:15px/1.6 ui-sans-serif,-apple-system,"Segoe UI",Roboto,sans-serif}
.wrap{max-width:1480px;margin:0 auto;padding:30px 26px 0}
h1{margin:0 0 6px;font-size:25px}
.lede{color:var(--dim);max-width:88ch;font-size:14px;margin:0 0 8px}
.lede b{color:var(--fg)}
.prompt{border:1px solid var(--line);border-radius:9px;background:#101014;margin:10px 0;
 overflow:hidden}
.prompt.good{border-color:#2c5c33}
.prompt .ph{display:flex;gap:10px;align-items:center;padding:8px 15px;background:#141419;
 border-bottom:1px solid var(--line);font-size:13px;flex-wrap:wrap}
.prompt .ph b{font-size:14px}
.prompt .ph span{color:var(--dim);font-size:12.5px}
.prompt pre{margin:0;padding:12px 16px;font:13px/1.7 ui-monospace,SFMono-Regular,monospace;
 white-space:pre-wrap;color:#c3c3ce;background:#0b0b0e}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(680px,1fr));gap:12px;
 margin-top:18px}
.card{border:1px solid var(--line);border-radius:9px;background:#101014;overflow:hidden}
.ch{display:flex;gap:6px;align-items:center;padding:7px 11px;background:#141419;
 border-bottom:1px solid var(--line);font-size:12px;flex-wrap:wrap}
.ch b{font-size:12.5px;word-break:break-all}
.ch .src{margin-left:auto;color:var(--dim);font-size:10.5px}
.t{font-size:9.5px;padding:1px 7px;border-radius:20px;background:#2a1a12;
 border:1px solid #6b4423;color:var(--mid)}
.four{display:grid;grid-template-columns:repeat(4,1fr);gap:4px;padding:6px}
@media(max-width:620px){.four{grid-template-columns:1fr 1fr}}
.miss{background:#17171d;border:1px dashed var(--line);border-radius:5px;aspect-ratio:3/4;
 display:flex;align-items:center;justify-content:center;color:var(--dim);font-size:11px}
figure{margin:0}
figure img{width:100%;display:block;background:#fff;border-radius:5px;cursor:zoom-in;
 aspect-ratio:3/4;object-fit:contain;image-rendering:-webkit-optimize-contrast}
figure.mq img{background:#fff;outline:1px solid var(--line);outline-offset:-1px}
figure.mq.best img{outline:2px solid #2c5c33;outline-offset:-2px}
figure.mq.best figcaption{color:#3fb950;font-weight:700}
figcaption{font-size:10.5px;color:var(--dim);text-align:center;padding:4px 2px}
figure.mq figcaption{color:var(--fg)}
#lb{display:none;position:fixed;inset:0;background:rgba(0,0,0,.95);z-index:99;
 align-items:center;justify-content:center;flex-direction:column;gap:10px;padding:20px}
#lb.on{display:flex}#lb img{max-width:95vw;max-height:90vh;object-fit:contain;background:#fff}
#lbc{color:var(--dim);font-size:13px}
footer{border-top:1px solid var(--line);margin-top:40px;padding:22px 0 30px;
 color:var(--dim);font-size:12.5px}
code{background:#1b1b22;padding:1px 5px;border-radius:4px;font-size:12px}
</style>
<div class='wrap'><h1>Ghost mannequins &mdash; the latest extractions</h1>
<p class='lede'>All 28 garment references from the v3.0 run-B fold, through
<b>all three mannequin prompts</b>. Source on the left, then p3, p5 and p7 &mdash;
nothing else on the page, because this is for judging the extraction on its own terms,
before any edit is involved. <b>Green marks p7, the current one.</b> Click any image for
full size.</p></div>
"""

LEDE = """<p class='lede'>What to look at: <b>is every piece there</b> (the earlier
prompts dropped footwear and whole trousers), <b>is anything present that was not in the
photograph</b> (naming accessory slots made the previous version invent hats and bags),
and <b>is the colour and pattern the same garment</b> &mdash; regeneration is free to
change what it cannot copy.</p>"""

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
