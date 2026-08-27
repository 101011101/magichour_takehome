"""Build the p7 accuracy page: source photograph against the p7 mannequin, nothing else.

Two columns, large, full resolution in the lightbox. The question this page is for is
narrow - is the mannequin the same garment as the one in the photograph - so everything
that is not those two images is off it.

Drift numbers come from V2's triage script against the subtractive crop of the same
reference: the same garment on the same white ground, cut instead of regenerated. They
rank references for attention, they do not decide accuracy - a changed collar or a moved
seam appears in none of them, which is what the eye is for.
"""
import csv
import html
import os
import sys

import cv2
from PIL import Image

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RUN = os.path.join(REPO, "v3", "runs", "v3.0b")
REPORT = os.path.join(REPO, "v3", "report")
IMG = os.path.join(REPORT, "img_p7")
TAG = "QMB"
sys.path.insert(0, os.path.join(REPO, "v3", "build"))
import run_v30 as R  # noqa: E402


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
    return "img_p7/" + dst, "img_p7/" + os.path.basename(full)


def fill_fraction(path):
    """How much of the frame the subject occupies - low means low effective resolution."""
    import numpy as np
    a = np.array(Image.open(path).convert("L"))
    nw = a < 244
    ys, xs = np.where(nw.any(axis=1))[0], np.where(nw.any(axis=0))[0]
    if len(ys) < 3 or len(xs) < 3:
        return None
    return ((ys[-1] - ys[0]) * (xs[-1] - xs[0])) / (a.shape[0] * a.shape[1])


def main():
    os.makedirs(IMG, exist_ok=True)
    sys.path.insert(0, os.path.join(REPO, "v2", "build"))
    import extraction_drift as D
    rows = list(csv.DictReader(open(os.path.join(REPO, "v3/testsets/v30_matrix_b.csv"))))

    o = [HEAD, "<div class='wrap'>"]
    o.append(f"<div class='prompt'><div class='ph'><b>p7</b><code>{TAG}</code>"
             "<span>every mannequin on this page came from this prompt</span></div>"
             f"<pre>{html.escape(R.EXTRACT[TAG])}</pre></div>")
    o.append(NOTE)

    cards, n = [], 0
    for r in rows:
        g = r["garment"]
        mqp = os.path.join(RUN, "refs", f"{g}__{TAG}.jpg")
        if not os.path.exists(mqp):
            continue
        n += 1
        src, srcf = web(os.path.join(RUN, "inputs", f"{g}.jpg"), f"{g}__raw.jpg", 720)
        mq, mqf = web(mqp, f"{g}__{TAG}.jpg", 720)

        base = os.path.join(RUN, "refs", f"{g}__BC.jpg")
        d = D.compare(cv2.imread(base), cv2.imread(mqp)) if os.path.exists(base) else None
        ff = fill_fraction(mqp)
        stats = []
        if d:
            stats += [("hue", f"{d['dHue']:.0f}&deg;", d["dHue"] > 25),
                      ("edge kept", f"&times;{d['dEdge']:.2f}",
                       d["dEdge"] < 0.5 or d["dEdge"] > 1.9),
                      ("lightness", f"{d['dL']:+.0f}", abs(d["dL"]) > 12)]
        if ff is not None:
            stats.append(("fills frame", f"{ff:.0%}", ff < 0.35))
        chips = "".join(f"<span class='s{' hot' if hot else ''}'>{k} {v}</span>"
                        for k, v, hot in stats)
        bits = [b for b in (r["garment_category"], r["garment_hard_case"]) if b]
        tags = "".join(f"<span class='t'>{html.escape(b)}</span>" for b in bits)
        cards.append(
            f"<div class='card'><div class='ch'><b>{html.escape(g)}</b>{tags}"
            f"<span class='chips'>{chips}</span></div><div class='two'>"
            f"<figure><img src='{src}' data-full='{srcf}' alt='{html.escape(g)} source'"
            " loading='lazy'><figcaption>the photograph</figcaption></figure>"
            f"<figure class='mq'><img src='{mq}' data-full='{mqf}' "
            f"alt='{html.escape(g)} p7 mannequin' loading='lazy'>"
            "<figcaption>p7 mannequin</figcaption></figure></div></div>")
    o.append("<div class='grid'>" + "".join(cards) + "</div>")
    o.append(f"<footer>{n} references &middot; "
             f"<code>v3/runs/v3.0b/refs/{{ref}}__{TAG}.jpg</code> against "
             "<code>inputs/{ref}.jpg</code> &middot; prompt of record: "
             f"<code>EXTRACT[&quot;{TAG}&quot;]</code> in <code>v3/build/run_v30.py</code>. "
             "Rebuild: <code>python3 v3/build/p7_accuracy_page.py</code>.</footer></div>")
    o.append(LB + SCRIPT)
    open(os.path.join(REPORT, "v31_p7_accuracy.html"), "w").write("\n".join(o))
    print(f"v3/report/v31_p7_accuracy.html  ({n} references)")


HEAD = """<title>p7 accuracy</title>
<meta name='viewport' content='width=device-width,initial-scale=1'>
<style>
:root{--bg:#0d0d10;--fg:#e8e8ea;--dim:#8a8a94;--line:#26262c;--acc:#7c5cff;
 --good:#3fb950;--mid:#d29922}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
 font:15px/1.6 ui-sans-serif,-apple-system,"Segoe UI",Roboto,sans-serif}
.wrap{max-width:1700px;margin:0 auto;padding:30px 26px 0}
h1{margin:0 0 6px;font-size:25px}
.lede{color:var(--dim);max-width:92ch;font-size:14px;margin:0 0 8px}
.lede b{color:var(--fg)}
.prompt{border:1px solid #2c5c33;border-radius:9px;background:#101014;margin:16px 0 14px;
 overflow:hidden;max-width:1100px}
.prompt .ph{display:flex;gap:10px;align-items:center;padding:8px 15px;background:#141419;
 border-bottom:1px solid var(--line);font-size:13px;flex-wrap:wrap}
.prompt .ph b{font-size:14px;color:var(--good)}
.prompt .ph span{color:var(--dim);font-size:12.5px}
.prompt pre{margin:0;padding:12px 16px;font:13px/1.7 ui-monospace,SFMono-Regular,monospace;
 white-space:pre-wrap;color:#c3c3ce;background:#0b0b0e}
.q{border-left:3px solid var(--acc);padding:2px 0 2px 14px;margin:14px 0;max-width:94ch;
 font-size:13.5px;color:#c8c8d0}
.q b{color:var(--fg)}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(660px,1fr));gap:14px;
 margin-top:20px}
.card{border:1px solid var(--line);border-radius:10px;background:#101014;overflow:hidden}
.ch{display:flex;gap:7px;align-items:center;padding:8px 12px;background:#141419;
 border-bottom:1px solid var(--line);font-size:12.5px;flex-wrap:wrap}
.ch b{font-size:13px;word-break:break-all}
.chips{margin-left:auto;display:flex;gap:5px;flex-wrap:wrap}
.s{font-size:10px;padding:1px 7px;border-radius:20px;border:1px solid var(--line);
 color:var(--dim);white-space:nowrap}
.s.hot{border-color:#6b4423;background:#2a1a12;color:var(--mid)}
.t{font-size:9.5px;padding:1px 7px;border-radius:20px;background:#1a1226;
 border:1px solid #4b3a78;color:#b9a7ec}
.two{display:grid;grid-template-columns:1fr 1fr;gap:5px;padding:7px}
figure{margin:0}
figure img{width:100%;display:block;background:#fff;border-radius:6px;cursor:zoom-in;
 aspect-ratio:3/4;object-fit:contain}
figure.mq img{outline:2px solid #2c5c33;outline-offset:-2px}
figcaption{font-size:11px;color:var(--dim);text-align:center;padding:5px 2px}
figure.mq figcaption{color:var(--good);font-weight:600}
#lb{display:none;position:fixed;inset:0;background:rgba(0,0,0,.96);z-index:99;
 align-items:center;justify-content:center;flex-direction:column;gap:10px;padding:16px}
#lb.on{display:flex}#lb img{max-width:96vw;max-height:92vh;object-fit:contain;background:#fff}
#lbc{color:var(--dim);font-size:13px}
footer{border-top:1px solid var(--line);margin-top:40px;padding:22px 0 30px;
 color:var(--dim);font-size:12.5px}
code{background:#1b1b22;padding:1px 5px;border-radius:4px;font-size:12px}
</style>
<div class='wrap'><h1>p7 &mdash; is it the same garment?</h1>
<p class='lede'>The photograph and the mannequin p7 made from it, side by side, at full
resolution. <b>Nothing else is on this page</b>, because the only question is whether the
extraction is faithful. Click either image to compare at full size.</p></div>
"""

NOTE = """<div class='q'>The chips on each card are a <b>rank, not a verdict</b>. Hue and
edge retention are measured against the subtractive crop of the same reference &mdash; the
same garment on the same white ground, cut instead of regenerated &mdash; so they catch
gross recolouring and pattern loss and nothing subtler. <b>A changed collar, a moved seam,
a sleeve that got longer: none of those appear in any column.</b> Amber marks a value past
a flag threshold.</div>
<div class='q'><b>fills frame</b> is not a drift statistic, it is a resolution warning.
Where the mannequin occupies a small part of the frame the rest is white ground, so the
garment carries proportionally fewer tokens into the edit call &mdash; BFL's
<code>cap_pixels</code> only ever downsizes, and it never upsamples a small subject back.
Median here is 61%; the worst references are under 20%.</div>"""

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
