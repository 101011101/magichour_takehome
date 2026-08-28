"""Does the mannequin's colour change the try-on, or only the reference?

Reference row and output row for every colour, so the question can be answered on the
thing that matters. Every colour experiment before this one stopped at the reference.
"""
import html
import json
import os
import sys

from PIL import Image

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RUN = os.path.join(REPO, "v3", "runs", "v3.0b")
REPORT = os.path.join(REPO, "v3", "report")
IMG = os.path.join(REPORT, "img_ck")
sys.path.insert(0, os.path.join(REPO, "v3", "build"))
import run_colour_klein as CK  # noqa: E402

ARMS = ["matched", "white", "grey", "black", "opposite"]


def web(src, dst, width=420):
    if not os.path.exists(src):
        return None, None
    out, full = os.path.join(IMG, dst), os.path.join(IMG, dst.replace(".jpg", "@f.jpg"))
    im = None
    if not os.path.exists(out):
        im = Image.open(src).convert("RGB")
        t = im.resize((width, int(im.height * width / im.width)), Image.LANCZOS) \
            if im.width > width else im
        t.save(out, quality=90, optimize=True)
    if not os.path.exists(full):
        im = im or Image.open(src).convert("RGB")
        im.save(full, quality=94, optimize=True)
    return "img_ck/" + dst, "img_ck/" + os.path.basename(full)


def fig(pair, cap, cls=""):
    src, full = pair
    if not src:
        return f"<figure class='miss'><div class='ph'>not run</div><figcaption>{cap}</figcaption></figure>"
    return (f"<figure class='{cls}'><img src='{src}' data-full='{full}' "
            f"alt='{html.escape(cap)}' loading='lazy'><figcaption>{cap}</figcaption></figure>")


def main():
    os.makedirs(IMG, exist_ok=True)
    log = json.load(open(os.path.join(RUN, "_ck_prompts.json")))
    o = [HEAD, "<div class='wrap'>", NOTE]

    for g, why in CK.PAIRS.items():
        e = log[f"{g}|matched"]
        sid, person = e["set_id"], e["person"]
        o.append(f"<h2>{html.escape(g)}<span class='r'>{html.escape(why)}</span></h2>")
        o.append(f"<div class='lab'>person <b>{html.escape(person)}</b> reads "
                 f"<b>{e['matched']}</b> &middot; the reference each colour produced</div>")
        o.append("<div class='strip s6'>"
                 + fig(web(os.path.join(RUN, "inputs", f"{g}__A4.jpg"), f"{g}__A4.jpg"),
                       "A4 crop &mdash; the input")
                 + "".join(fig(web(os.path.join(RUN, "refs", f"{g}__ck.{a}.jpg"),
                                   f"{g}__ck.{a}.jpg"),
                               f"{a}<span class='n'>&ldquo;{log[f'{g}|{a}']['colour']}&rdquo;</span>",
                               "ship" if a == "matched" else "")
                           for a in ARMS) + "</div>")
        o.append("<div class='lab'>what klein made from each &mdash; "
                 "<b>this row is the experiment</b></div>")
        o.append("<div class='strip s6'>"
                 + fig(web(os.path.join(RUN, "inputs", f"{person}.jpg"), f"{person}__p.jpg"),
                       "person &mdash; the input")
                 + "".join(fig(web(os.path.join(RUN, "gen", f"{sid}__ck.{a}.jpg"),
                                   f"{sid}__ck.{a}.jpg"),
                               f"{a}<span class='n'>&ldquo;{log[f'{g}|{a}']['colour']}&rdquo;</span>",
                               "ship" if a == "matched" else "")
                           for a in ARMS) + "</div>")

    o.append(FOOT + "</div>" + LB + SCRIPT)
    open(os.path.join(REPORT, "v31_colour_klein.html"), "w").write("\n".join(o))
    print(f"v3/report/v31_colour_klein.html  ({len(CK.PAIRS)} pairs x {len(ARMS)} colours)")


HEAD = """<title>Does the mannequin colour matter?</title>
<meta name='viewport' content='width=device-width,initial-scale=1'>
<style>
:root{--bg:#0d0d10;--fg:#e8e8ea;--dim:#8a8a94;--line:#26262c;--acc:#7c5cff;--good:#3fb950}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
 font:15px/1.6 ui-sans-serif,-apple-system,"Segoe UI",Roboto,sans-serif}
.wrap{max-width:1620px;margin:0 auto;padding:30px 26px 0}
h1{margin:0 0 6px;font-size:25px}
h2{font-size:14px;margin:48px 0 8px;padding-top:14px;border-top:1px solid var(--line);
 display:flex;gap:12px;align-items:baseline;flex-wrap:wrap}
h2 .r{font-size:11.5px;color:var(--dim);font-weight:400}
.lede{color:var(--dim);max-width:96ch;font-size:14px;margin:0 0 14px}
.lede b{color:var(--fg)}
.q{border-left:3px solid var(--acc);padding:2px 0 2px 14px;margin:14px 0;max-width:98ch;
 font-size:13.5px;color:#c8c8d0}
.q b{color:var(--fg)}
.lab{font-size:11.5px;color:var(--dim);margin:14px 0 5px}
.lab b{color:var(--fg)}
.strip{display:grid;gap:5px;margin-bottom:6px}
.s6{grid-template-columns:repeat(6,1fr)}
@media(max-width:1100px){.s6{grid-template-columns:repeat(3,1fr)}}
@media(max-width:700px){.s6{grid-template-columns:repeat(2,1fr)}}
figure{margin:0}
figure img{width:100%;display:block;background:#fff;border-radius:6px;cursor:zoom-in;
 aspect-ratio:3/4;object-fit:contain}
figure.ship img{outline:2px solid #2c5c33;outline-offset:-2px}
figure.ship figcaption{color:var(--good);font-weight:700}
figcaption{font-size:11px;color:var(--dim);text-align:center;padding:5px 2px;line-height:1.4}
figcaption .n{display:block;font-size:9.5px;opacity:.85}
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
<div class='wrap'><h1>Does the mannequin's colour matter?</h1>
<p class='lede'>Six references, five mannequin colours, <b>each taken all the way through
both calls</b>. Every colour experiment before this one stopped at the reference: 120
colour variants sit on disk and not one had ever been edited, so the question the colour
reader was built to answer had never been asked. The <b>lower row of each block is the
experiment</b>; the upper row is only there to show what the colour did to the reference.
Click any image for full size.</p></div>
"""

NOTE = """<div class='q'><b>matched</b> is the CPU skin reader on the paired person &mdash;
what ships today. <b>white</b> is the old <code>p7</code> default and the low-amplitude
case whenever the garment is pale. <b>grey</b> is achromatic and person-independent, so if
it does as well as matched <b>the reader is unnecessary</b>. <b>black</b> is the other
achromatic extreme. <b>opposite</b> is the ladder step furthest in lightness from matched
&mdash; a wrong answer by construction, so that a null result reads as
<i>&ldquo;colour does not matter&rdquo;</i> rather than <i>&ldquo;these two colours
happened to be close&rdquo;</i>.</div>
<div class='q'><b>The outcome that would matter most is a null one.</b> If the five output
columns are indistinguishable, the entire colour apparatus &mdash; the reader, the ladder,
the quantisation, the calibration problem in §3c.25 &mdash; is machinery attached to
something that does not affect the product, and it can all be deleted in favour of a
fixed word.</div>"""

FOOT = """<footer>References <code>refs/{ref}__ck.{arm}.jpg</code>, outputs
<code>gen/{set_id}__ck.{arm}.jpg</code>, prompts as sent <code>_ck_prompts.json</code>
&middot; rebuild <code>python3 v3/build/colour_klein_page.py</code>. One prompt shape, one
seed, one edit prompt &mdash; the colour word is the only variable.</footer>"""

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
