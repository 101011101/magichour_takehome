"""Build the three-arm comparison: BC_klein, QX and the p7 mannequin, same pairs.

All three end in the same klein edit call with the same seed and the same prompt. The
only thing that differs is the reference image handed to that call, so any difference
between the three columns is attributable to the reference and nothing else.

  BC   klein bald pass, then the CPU crop      subtraction
  QX   Qwen "isolated on a plain white ground" regeneration, p1
  QMB  Qwen "on a mannequin", p7               regeneration, whole outfit

No verdict buttons: this page is for looking. Marking lives on v30b_review.html.
"""
import csv
import html
import os

from PIL import Image

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RUN = os.path.join(REPO, "v3", "runs", "v3.0b")
REPORT = os.path.join(REPO, "v3", "report")
IMG = os.path.join(REPORT, "img_vs")
ARMS = [("BC", "BC_klein", "subtractive crop"),
        ("QX", "QX", "regenerated, isolated on white"),
        ("QMB", "QMB", "regenerated, p7 mannequin")]


def web(src, dst, width):
    if not os.path.exists(src):
        return None, None
    out, full = os.path.join(IMG, dst), os.path.join(IMG, dst.replace(".jpg", "@full.jpg"))
    im = None
    if not os.path.exists(out):
        im = Image.open(src).convert("RGB")
        t = im.resize((width, int(im.height * width / im.width)), Image.LANCZOS) \
            if im.width > width else im
        t.save(out, quality=91, optimize=True)
    if not os.path.exists(full):
        im = im or Image.open(src).convert("RGB")
        im.save(full, quality=95, optimize=True)
    return "img_vs/" + dst, "img_vs/" + os.path.basename(full)


def fig(pair, cap, cls=""):
    src, full = pair
    if not src:
        return ("<figure class='miss'><div class='ph'>not generated</div>"
                f"<figcaption>{cap}</figcaption></figure>")
    return (f"<figure class='{cls}'><img src='{src}' data-full='{full}' "
            f"alt='{html.escape(cap)}' loading='lazy'>"
            f"<figcaption>{cap}</figcaption></figure>")


def build(arms, out_name, head, note, best, ref_tags=None):
    """One page: the inputs, one reference per tag in ref_tags, one output per arm."""
    os.makedirs(IMG, exist_ok=True)
    ref_tags = [t for t, _, _ in arms] if ref_tags is None else ref_tags
    rows = list(csv.DictReader(open(os.path.join(REPO, "v3/testsets/v30_matrix_b.csv"))))
    o = [head, "<div class='wrap'>", note]

    n = 0
    for r in rows:
        g, sid = r["garment"], r["set_id"]
        outs = [(t, lb, ds, web(os.path.join(RUN, "gen", f"{sid}__{t}.jpg"),
                                f"{sid}__{t}.jpg", 620)) for t, lb, ds in arms]
        if not any(p[0] for _, _, _, p in outs):
            continue
        n += 1
        bits = [b for b in (r["garment_category"], r["garment_hard_case"]) if b]
        o.append(f"<h2><span class='m'>pair {r['pair']} of 28</span>"
                 f"{html.escape(r['person'])} <span class='ar'>&larr;</span> "
                 f"{html.escape(g)}"
                 + ("".join(f"<span class='t'>{html.escape(b)}</span>" for b in bits))
                 + "</h2>")
        o.append("<div class='refs'>"
                 + fig(web(os.path.join(RUN, "inputs", f"{r['person']}.jpg"),
                           f"{r['person']}__p.jpg", 300), "person")
                 + fig(web(os.path.join(RUN, "inputs", f"{g}.jpg"),
                           f"{g}__raw.jpg", 300), "garment photo")
                 + "".join(fig(web(os.path.join(RUN, "refs", f"{g}__{t}.jpg"),
                                   f"{g}__{t}ref.jpg", 300), f"{t} reference")
                           for t in ref_tags) + "</div>")
        o.append("<div class='outs'>"
                 + "".join(fig(p, f"{lb}<span class='n'>{ds}</span>",
                               "best" if t == best else "")
                           for t, lb, ds, p in outs) + "</div>")

    tags = ",".join(t for t, _, _ in arms)
    o.append(f"<footer>{n} pairs &middot; outputs "
             f"<code>v3/runs/v3.0b/gen/{{set_id}}__{{{tags}}}.jpg</code> &middot; one seed "
             "(46), one prompt, one model. Marking page: "
             "<code>v30b_review.html</code>. Rebuild: "
             "<code>python3 v3/build/arms_vs_page.py</code>.</footer></div>")
    o.append(LB + SCRIPT)
    open(os.path.join(REPORT, out_name), "w").write("\n".join(o))
    print(f"v3/report/{out_name}  ({n} pairs x {len(arms)} arms)")


def main():
    build(ARMS, "v31_arms_vs.html", HEAD, NOTE, best="QMB")


HEAD = """<title>Three references, one editor</title>
<meta name='viewport' content='width=device-width,initial-scale=1'>
<style>
:root{--bg:#0d0d10;--fg:#e8e8ea;--dim:#8a8a94;--line:#26262c;--acc:#7c5cff;--good:#3fb950}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
 font:15px/1.6 ui-sans-serif,-apple-system,"Segoe UI",Roboto,sans-serif}
.wrap{max-width:1600px;margin:0 auto;padding:30px 26px 0}
h1{margin:0 0 6px;font-size:25px}
h2{font-size:15px;margin:44px 0 8px;padding-top:14px;border-top:1px solid var(--line);
 display:flex;gap:8px;align-items:center;flex-wrap:wrap;font-weight:600}
h2 .m{font-size:11px;color:var(--dim);font-weight:400;letter-spacing:.6px;
 text-transform:uppercase;width:100%;margin-bottom:2px}
h2 .ar{color:var(--dim);font-weight:400}
.t{font-size:9.5px;padding:1px 7px;border-radius:20px;background:#1a1226;
 border:1px solid #4b3a78;color:#b9a7ec;font-weight:400}
.lede{color:var(--dim);max-width:92ch;font-size:14px;margin:0 0 8px}
.lede b{color:var(--fg)}
.q{border-left:3px solid var(--acc);padding:2px 0 2px 14px;margin:14px 0;max-width:94ch;
 font-size:13.5px;color:#c8c8d0}
.q b{color:var(--fg)}
.refs{display:grid;grid-template-columns:repeat(auto-fill,minmax(0,132px));gap:5px;margin-bottom:7px}
.outs{display:grid;grid-template-columns:repeat(3,1fr);gap:6px}
@media(max-width:900px){.outs{grid-template-columns:1fr}
 .refs{grid-template-columns:repeat(5,minmax(0,1fr))}}
figure{margin:0}
figure img{width:100%;display:block;background:#fff;border-radius:6px;cursor:zoom-in;
 aspect-ratio:3/4;object-fit:contain}
.refs figure img{aspect-ratio:3/4;object-fit:cover;object-position:top center}
figcaption{font-size:11px;color:var(--dim);text-align:center;padding:5px 2px;line-height:1.4}
figcaption .n{display:block;font-size:10px;opacity:.8}
.refs figcaption{font-size:9.5px;padding:3px 2px}
.outs figure.best img{outline:2px solid #2c5c33;outline-offset:-2px}
.outs figure.best figcaption{color:var(--good);font-weight:700}
.ph{background:#17171d;border:1px dashed var(--line);border-radius:6px;aspect-ratio:3/4;
 display:flex;align-items:center;justify-content:center;color:var(--dim);font-size:11px}
#lb{display:none;position:fixed;inset:0;background:rgba(0,0,0,.96);z-index:99;
 align-items:center;justify-content:center;flex-direction:column;gap:10px;padding:16px}
#lb.on{display:flex}#lb img{max-width:96vw;max-height:92vh;object-fit:contain;background:#fff}
#lbc{color:var(--dim);font-size:13px}
footer{border-top:1px solid var(--line);margin-top:44px;padding:22px 0 30px;
 color:var(--dim);font-size:12.5px}
code{background:#1b1b22;padding:1px 5px;border-radius:4px;font-size:12px}
</style>
<div class='wrap'><h1>Three references, one editor</h1>
<p class='lede'>The same 28 pairs, the same klein edit call, the same seed and prompt.
<b>Only the reference image differs</b>, so every difference between the three columns is
attributable to the reference and nothing else. Small strip: the inputs and the three
references. Large row: what klein made from each. Click any image for full size.</p></div>
"""

NOTE = """<div class='q'><b>BC</b> subtracts &mdash; klein makes the wearer bald, then the
CPU stack cuts the head out. <b>QX</b> regenerates the garment isolated on white
(<code>p1</code>). <b>QMB</b> regenerates the whole outfit on a mannequin
(<code>p7</code>), and is the only reference of the three that reliably carries the
<b>footwear</b> &mdash; so it is also the only arm that can transfer shoes. Whether that
is wanted is a product decision, not a quality one.</div>"""

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
