"""Build the phase-4 crop-ladder page.

Six references, five preparations, one prompt. Ordered by CPU cost so the page reads
as a curve: where does quality stop improving, and does the 49-second matte earn it.
"""
import html
import json
import os
import sys

from PIL import Image

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RUN = os.path.join(REPO, "v3", "runs", "v3.0b")
REPORT = os.path.join(REPO, "v3", "report")
IMG = os.path.join(REPORT, "img_cl")
sys.path.insert(0, os.path.join(REPO, "v3", "build"))
import run_croplad as CL      # noqa: E402
import run_haircohort as HC   # noqa: E402

LABEL = {"A0raw": ("A0 · raw", "the photograph"),
         "A1bbox": ("A1 · bbox", "pose bounding box, background kept"),
         "A2mask256": ("A2 · mask256", "Selfie Multiclass 256², bg removed"),
         "A4biref1024": ("A4 · biref1024", "BiRefNet @1024², bg removed"),
         "A5biref1024h": ("A5 · biref+head", "BiRefNet, bg and head removed")}


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
    return "img_cl/" + dst, "img_cl/" + os.path.basename(full)


def fig(pair, cap, cls=""):
    src, full = pair
    if not src:
        return f"<figure class='miss'><div class='ph'>not run</div><figcaption>{cap}</figcaption></figure>"
    return (f"<figure class='{cls}'><img src='{src}' data-full='{full}' "
            f"alt='{html.escape(cap)}' loading='lazy'><figcaption>{cap}</figcaption></figure>")


def main():
    os.makedirs(IMG, exist_ok=True)
    prep = json.load(open(os.path.join(RUN, "_croplad_prep.json")))
    log = json.load(open(os.path.join(RUN, "_croplad_prompts.json")))
    secs, rough = prep["seconds"], prep["roughness"]
    o = [HEAD, "<div class='wrap'>", NOTE]

    import statistics
    rows = []
    for a in CL.ARMS:
        name, desc = LABEL[a]
        s = secs.get(a, 0.0)
        rs = [r[a] for r in rough.values() if r.get(a)]
        rows.append(f"<tr><td class='l'><b>{name}</b><span>{desc}</span></td>"
                    f"<td>{'—' if a == 'A0raw' else f'{s:.2f} s'}</td>"
                    f"<td>{statistics.median(rs):.2f}</td></tr>" if rs else "")
    o.append("<table><tr><th>arm</th><th>CPU per reference</th>"
             "<th>edge roughness</th></tr>" + "".join(rows) + "</table>")
    o.append(COSTNOTE)

    for stem, hair, person in HC.COHORT:
        e = log[f"{stem}|cl.A0raw"]
        o.append(f"<h2>{html.escape(stem)}<span class='r'>V2 hair over garment "
                 f"<b>{hair}</b> &middot; colour <b>{e['colour']}</b></span></h2>")
        o.append("<div class='lab'>what the model was given</div>")
        o.append("<div class='strip s5'>" + "".join(
            fig(web(os.path.join(REPO, log[f'{stem}|cl.{a}']["input"]),
                    f"{stem}__{a}_in.jpg"),
                f"{LABEL[a][0]}<span class='n'>"
                f"{'—' if a == 'A0raw' else f'{secs.get(a, 0):.2f} s'}</span>")
            for a in CL.ARMS) + "</div>")
        o.append("<div class='lab'>what came back</div>")
        o.append("<div class='strip s5'>" + "".join(
            fig(web(os.path.join(RUN, "refs", f"{stem}__cl.{a}.jpg"), f"{stem}__{a}.jpg"),
                f"{LABEL[a][0]}<span class='n'>{LABEL[a][1]}</span>",
                "cheap" if a in ("A1bbox", "A2mask256") else
                ("ctrl" if a == "A0raw" else ""))
            for a in CL.ARMS) + "</div>")

    o.append(FOOT + "</div>" + LB + SCRIPT)
    open(os.path.join(REPORT, "v31_croplad.html"), "w").write("\n".join(o))
    print(f"v3/report/v31_croplad.html  ({len(HC.COHORT)} references x {len(CL.ARMS)} arms)")


HEAD = """<title>How good does the crop have to be?</title>
<meta name='viewport' content='width=device-width,initial-scale=1'>
<style>
:root{--bg:#0d0d10;--fg:#e8e8ea;--dim:#8a8a94;--line:#26262c;--acc:#7c5cff;
 --good:#3fb950;--mid:#d29922}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
 font:15px/1.6 ui-sans-serif,-apple-system,"Segoe UI",Roboto,sans-serif}
.wrap{max-width:1560px;margin:0 auto;padding:30px 26px 0}
h1{margin:0 0 6px;font-size:25px}
h2{font-size:14px;margin:46px 0 8px;padding-top:14px;border-top:1px solid var(--line);
 display:flex;gap:12px;align-items:baseline;flex-wrap:wrap}
h2 .r{font-size:11.5px;color:var(--dim);font-weight:400}
h2 .r b{color:var(--fg)}
.lede{color:var(--dim);max-width:96ch;font-size:14px;margin:0 0 14px}
.lede b{color:var(--fg)}
.q{border-left:3px solid var(--acc);padding:2px 0 2px 14px;margin:14px 0;max-width:98ch;
 font-size:13.5px;color:#c8c8d0}
.q b{color:var(--fg)}
.lab{font-size:11px;text-transform:uppercase;letter-spacing:1px;color:var(--dim);
 margin:14px 0 5px}
table{border-collapse:collapse;font-size:13px;margin:16px 0}
th,td{padding:7px 16px;border-bottom:1px solid #1d1d23;text-align:right}
th:first-child,td.l{text-align:left}
th{color:var(--dim);font-weight:600}
td.l b{display:block}
td.l span{font-size:11px;color:var(--dim)}
.strip{display:grid;gap:5px;margin-bottom:6px}
.s5{grid-template-columns:repeat(5,1fr)}
@media(max-width:1000px){.s5{grid-template-columns:repeat(3,1fr)}}
@media(max-width:700px){.s5{grid-template-columns:repeat(2,1fr)}}
figure{margin:0}
figure img{width:100%;display:block;background:#fff;border-radius:6px;cursor:zoom-in;
 aspect-ratio:3/4;object-fit:contain}
figure.cheap img{outline:2px solid #2c5c33;outline-offset:-2px}
figure.cheap figcaption{color:var(--good)}
figure.ctrl img{outline:2px solid #3a3a46;outline-offset:-2px}
figcaption{font-size:11px;color:var(--dim);text-align:center;padding:5px 2px;line-height:1.4}
figcaption .n{display:block;font-size:9.5px;opacity:.8}
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
<div class='wrap'><h1>How good does the crop have to be?</h1>
<p class='lede'>The six references V2 measured as <b>worst for hair over the garment</b>,
each prepared five ways and put through the same prompt. Arms are ordered by CPU cost, so
this reads as a curve rather than a comparison: <b>where does quality stop improving?</b>
The two sub-second arms are outlined green. Click any image for full size.</p></div>
"""

NOTE = """<div class='q'>V2 chose BiRefNet at 1024² for a measured reason: the cheap 256²
map is <i>&ldquo;a staircase by construction&rdquo;</i> and <b>klein copies the staircase
into its output</b>. That finding is what the whole cropper was rebuilt around.
<b>But the consumer here is not klein.</b> QX regenerates rather than subtracts, and the
same argument that says a regenerative model absorbs a cut boundary says it absorbs a
stair-stepped edge. If it does, <b>49 seconds buys nothing</b>.</div>
<div class='q'><b>A1 is the arm that separates cropping from background removal.</b> They
have always been done together and they are different operations at very different prices.
If A1 is enough, no matte is needed at all.</div>
<div class='q'><b>There is no middle rung, and not by choice.</b> The intended
<code>A3</code> was BiRefNet at 512² &mdash; the same model at a quarter of the pixels.
It cannot be run: <code>BiRefNet_lite.onnx</code> is exported with <b>static 1024×1024
input dimensions</b> and onnxruntime rejects any other shape. There is no resolution knob
without re-exporting from the PyTorch weights, so the real choice is <b>sub-second or
99 seconds</b>, with nothing in between.</div>"""

COSTNOTE = """<div class='q'><b>Edge roughness</b> is the subject contour's perimeter over
its own convex hull's perimeter &mdash; 1.00 is a smooth outline, higher is more
convoluted. <code>A0</code> and <code>A1</code> read 1.00 because they keep the background,
so there is no silhouette to measure and the contour is just the frame. <b>The number that
matters is A2 against A4: 1.27 versus 1.24.</b> By this measure the &ldquo;staircase&rdquo;
is about 2% rougher than the 99-second matte.</div>
<div class='q'><b>That metric is coarse and should not be over-read.</b> Perimeter over
hull perimeter is dominated by overall shape complexity, not by fine stair-stepping at the
edge &mdash; it will under-report exactly the defect it is being used to look for. It is
here to show the two mattes are in the same range, not to prove they are equivalent. The
frames are the evidence.</div>"""

FOOT = """<footer>Inputs: <code>v3/runs/v3.0b/inputs/{ref}__A*.jpg</code> &middot; outputs:
<code>refs/{ref}__cl.A*.jpg</code> &middot; timings and roughness:
<code>_croplad_prep.json</code> &middot; prompts as sent:
<code>_croplad_prompts.json</code> &middot; rebuild:
<code>python3 v3/build/croplad_page.py</code>. One prompt on every arm &mdash; the full
<code>p7.3</code>, so the input is the only variable.</footer>"""

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
