"""Build the skin-tone and framing reader page: how good are the CPU readers?

Every image in test_set3, with what the two readers said about it and the evidence
they said it from. This page exists to be disagreed with - the point is to find where
the readers are wrong before anything is built on top of them.
"""
import collections
import html
import json
import os
import sys

import cv2
import numpy as np
from PIL import Image

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
REPORT = os.path.join(REPO, "v3", "report")
IMG = os.path.join(REPORT, "img_skin")
sys.path.insert(0, os.path.join(REPO, "v3", "build"))
import skin_tone as S  # noqa: E402


def web(src, dst, width=340):
    if not os.path.exists(src):
        return None
    out = os.path.join(IMG, dst)
    if not os.path.exists(out):
        im = Image.open(src).convert("RGB")
        if im.width > width:
            im = im.resize((width, int(im.height * width / im.width)), Image.LANCZOS)
        im.save(out, quality=88, optimize=True)
    return "img_skin/" + dst


def overlay(src, dst, width=340):
    """The face-skin pixels the median was taken from, tinted so they can be checked."""
    out = os.path.join(IMG, dst)
    if not os.path.exists(out):
        bgr = cv2.imread(src)
        res = S._segmenter().segment(S._mp_image(bgr))
        h, w = bgr.shape[:2]
        ch = [cv2.resize(m.numpy_view(), (w, h), interpolation=cv2.INTER_LINEAR)
              for m in res.confidence_masks]
        import garment_crop as G
        face, body = ch[G.FACE] > 0.6, ch[G.BODY] > 0.6
        sel = face if face.sum() > 500 else body
        vis = bgr.copy()
        vis[sel] = (0.45 * vis[sel] + 0.55 * np.array([255, 0, 200])).astype(np.uint8)
        im = Image.fromarray(cv2.cvtColor(vis, cv2.COLOR_BGR2RGB))
        if im.width > width:
            im = im.resize((width, int(im.height * width / im.width)), Image.LANCZOS)
        im.save(out, quality=88, optimize=True)
    return "img_skin/" + dst


def main():
    os.makedirs(IMG, exist_ok=True)
    data = json.load(open(os.path.join(REPO, "v3", "runs", "skin_framing.json")))
    o = [HEAD, "<div class='wrap'>"]

    fr = collections.Counter(d["framing"] for d in data)
    tn = collections.Counter(d["tone"]["name"] if d["tone"] else "none" for d in data)
    o.append("<div class='tallies'>"
             "<div><b>framing</b>" + "".join(
                 f"<span><i>{k}</i>{v}</span>" for k, v in fr.most_common()) + "</div>"
             "<div><b>tone</b>" + "".join(
                 f"<span><i>{k}</i>{v}</span>" for k, v in tn.most_common()) + "</div>"
             "</div>")
    o.append(NOTE)
    o.append("<div class='swatches'><b>the eight tone words</b>"
             + "".join(f"<span><i style='background:{h}'></i>{n}</span>"
                       for n, _, h in S.TONES) + "</div>")

    cards = []
    for d in data:
        src = web(os.path.join(REPO, d["path"]), f"{d['id']}.jpg")
        ov = overlay(os.path.join(REPO, d["path"]), f"{d['id']}__mask.jpg")
        t = d["tone"]
        if t:
            chips = (f"<span class='sw' style='background:{t['swatch']}'></span>"
                     f"<b>{t['name']}</b>"
                     f"<span class='m'>ITA {t['ITA']:.0f}&deg;</span>"
                     f"<span class='m'>L* {t['L']:.0f}</span>"
                     f"<span class='m'>from {t['from']}</span>"
                     f"<span class='m mx'>measured <i style='background:"
                     f"{t['measured_hex']}'></i>{t['measured_hex']}</span>")
            low = t["pixels"] < 3000
        else:
            chips, low = "<b class='no'>no skin found</b>", True
        cards.append(
            f"<div class='card{' low' if low else ''}'>"
            f"<div class='ch'><b>{html.escape(d['id'])}</b>"
            f"<span class='fr'>{d['framing']}</span>"
            f"<span class='j'>{' · '.join(d['present']) or 'no joints'}</span></div>"
            "<div class='two'>"
            f"<figure><img src='{src}' loading='lazy' alt='{html.escape(d['id'])}'>"
            "<figcaption>photograph</figcaption></figure>"
            f"<figure><img src='{ov}' loading='lazy' alt='{html.escape(d['id'])} mask'>"
            "<figcaption>pixels the median came from</figcaption></figure></div>"
            f"<div class='chips'>{chips}</div></div>")
    o.append("<div class='grid'>" + "".join(cards) + "</div>")
    o.append(FOOT + "</div>")
    open(os.path.join(REPORT, "v31_skin_reader.html"), "w").write("\n".join(o))
    print(f"v3/report/v31_skin_reader.html  ({len(data)} images)")


HEAD = """<title>Skin tone and framing readers</title>
<meta name='viewport' content='width=device-width,initial-scale=1'>
<style>
:root{--bg:#0d0d10;--fg:#e8e8ea;--dim:#8a8a94;--line:#26262c;--acc:#7c5cff;
 --good:#3fb950;--mid:#d29922;--bad:#f85149}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
 font:15px/1.6 ui-sans-serif,-apple-system,"Segoe UI",Roboto,sans-serif}
.wrap{max-width:1560px;margin:0 auto;padding:30px 26px 0}
h1{margin:0 0 6px;font-size:25px}
.lede{color:var(--dim);max-width:94ch;font-size:14px;margin:0 0 14px}
.lede b{color:var(--fg)}
.q{border-left:3px solid var(--acc);padding:2px 0 2px 14px;margin:14px 0;max-width:96ch;
 font-size:13.5px;color:#c8c8d0}
.q b{color:var(--fg)}
.tallies{display:flex;gap:26px;flex-wrap:wrap;margin:16px 0 6px;font-size:12.5px}
.tallies b{display:block;color:var(--dim);font-size:11px;text-transform:uppercase;
 letter-spacing:1px;margin-bottom:5px}
.tallies span{display:inline-flex;gap:5px;align-items:center;margin-right:9px}
.tallies i{font-style:normal;color:var(--dim)}
.swatches{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin:14px 0 6px;
 font-size:12px;color:var(--dim)}
.swatches b{color:var(--fg);font-size:11px;text-transform:uppercase;letter-spacing:1px}
.swatches span{display:inline-flex;gap:5px;align-items:center}
.swatches i{width:15px;height:15px;border-radius:4px;display:inline-block;
 border:1px solid #333}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(330px,1fr));gap:11px;
 margin-top:18px}
.card{border:1px solid var(--line);border-radius:9px;background:#101014;overflow:hidden}
.card.low{border-color:#6b4423}
.ch{display:flex;gap:7px;align-items:center;padding:7px 11px;background:#141419;
 border-bottom:1px solid var(--line);font-size:11.5px;flex-wrap:wrap}
.ch b{font-size:12px;word-break:break-all}
.ch .fr{margin-left:auto;padding:1px 8px;border-radius:20px;border:1px solid var(--line);
 color:var(--fg);font-size:10.5px}
.ch .j{width:100%;color:var(--dim);font-size:10px}
.two{display:grid;grid-template-columns:1fr 1fr;gap:4px;padding:6px}
figure{margin:0}
figure img{width:100%;display:block;background:#fff;border-radius:5px;aspect-ratio:3/4;
 object-fit:cover;object-position:top center}
figcaption{font-size:9.5px;color:var(--dim);text-align:center;padding:3px 2px}
.chips{display:flex;gap:7px;align-items:center;flex-wrap:wrap;padding:7px 11px 10px;
 font-size:11.5px;border-top:1px solid #17171d}
.chips b{font-size:13px}
.chips .no{color:var(--bad)}
.sw{width:22px;height:22px;border-radius:5px;border:1px solid #444}
.chips .m{color:var(--dim);font-size:10.5px}
.chips .mx{display:inline-flex;gap:4px;align-items:center}
.chips .mx i{width:12px;height:12px;border-radius:3px;display:inline-block;
 border:1px solid #444}
footer{border-top:1px solid var(--line);margin-top:40px;padding:22px 0 30px;
 color:var(--dim);font-size:12.5px}
code{background:#1b1b22;padding:1px 5px;border-radius:4px;font-size:12px}
</style>
<div class='wrap'><h1>The CPU readers &mdash; how good are they?</h1>
<p class='lede'>Every image in test_set3 with what the two readers said and the evidence
they said it from. <b>This page exists to be disagreed with</b>: the point is to find
where the readers are wrong before anything is built on them. Amber border marks a card
where the skin mask was small enough that the median is thin evidence.</p></div>
"""

NOTE = """<div class='q'><b>Tone</b> is the <b>median</b> Lab of the face-skin pixels, not
the mean &mdash; a face carries shadow, highlight and sometimes makeup, and the median
survives all three. It is reported as ITA, the standard Individual Typology Angle, and as
one of eight ordinary colour words. <b>The word is what reaches the prompt, not the
hex</b>: a diffusion model reads &ldquo;tan&rdquo; and does not read
<code>#D2A679</code>. The measured hex is shown only so the mapping can be checked.
149&nbsp;ms per image.</div>
<div class='q'><b>Framing</b> is pose-landmark presence: is this joint confident and
inside the frame. Shoulder &rarr; hip &rarr; knee &rarr; ankle. That is a much weaker
question than the eight head-detection heuristics V2 burned through &mdash; those tried
to locate a boundary; this reads a coordinate the detector already returns. 36&nbsp;ms
per image.</div>
<div class='q'><b>Where this will be wrong, predictably:</b> strong colour casts move the
median; a face in deep shadow reads darker than the person is; heavy makeup reads as
skin; and where no face is in frame the reader falls back to body skin, which is a
different and usually more exposed surface. Each of those is visible on this page rather
than hidden behind a number.</div>"""

FOOT = """<footer>Readers: <code>v3/build/skin_tone.py</code> &middot; data:
<code>v3/runs/skin_framing.json</code> &middot; rebuild:
<code>python3 v3/build/skin_page.py</code>. Neither reader decides anything &mdash; they
return a word and a category, and what the prompt does with them is the experiment.
</footer>"""

if __name__ == "__main__":
    main()
