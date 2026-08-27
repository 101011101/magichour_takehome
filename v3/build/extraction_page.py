"""Build the extraction-shape comparison page.

Two questions, one page. What shape should the garment reference be in - flat, on a
mannequin, or simply isolated - and what wording actually gets the whole outfit out of
the photograph. The second turned out to be the harder one: the shipped prompt says
"the garment", singular, and the model takes it literally.

Every prompt tried is shown with the failure it produced, because the failures are the
argument. Prompts of record live in EXTRACT in run_v30.py.

Drift is recomputed with V2's triage statistics against the SUBTRACTIVE CROP. The raw
photograph is the wrong baseline and was tried first: the statistics run over non-white
pixels, so against a raw frame they compare the garment to the whole scene and report a
lightness drift near 90 for every shape - a measurement of the white ground, not the
garment.
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
IMG = os.path.join(REPORT, "img_ext")
sys.path.insert(0, os.path.join(REPO, "v3", "build"))
import run_v30 as R  # noqa: E402

# tag, prompt id, short label, what it fixed, what it broke
LINE = [
    ("QX", "p1", "isolated on white",
     "the shipped extraction", "says <b>&ldquo;the garment&rdquo;, singular</b> &mdash; drops pieces"),
    ("QF", "p2", "flat lay",
     "asks for a flat product photograph",
     "same singular noun, plus <i>&ldquo;do not complete anything that is not visible&rdquo;</i>. "
     "<b>g018 returns a blazer with no trousers</b>"),
    ("QM", "p3", "ghost mannequin",
     "says &ldquo;outfit&rdquo; &mdash; drops least of the three originals",
     "V2 found it read as <i>&ldquo;make it pale and simple&rdquo;</i>; footwear still dropped"),
    ("QFA", "p4", "flat, slots named",
     "<b>dropping fixed</b> &mdash; every piece present",
     "naming the slots made the model <b>generate</b> them: hats, bags and scarves that "
     "are in no photograph"),
    ("QMA", "p5", "mannequin, slots named",
     "<b>dropping fixed</b>", "same invention &mdash; every mannequin wears a hat"),
    ("QFB", "p6", "flat, no slot list",
     "<b>invention fixed</b>",
     "&ldquo;from what is on their head to what is on their feet&rdquo; read as "
     "<b>include the head</b> &mdash; floating wigs and faces"),
    ("QMB", "p7", "mannequin, no slot list",
     "<b>invention fixed, head gone, full outfit</b>",
     "&mdash; nothing yet. The shape v3.1 is built on"),
    ("QFC", "p8", "flat, footwear named",
     "<b>head fixed</b>",
     "&ldquo;side by side&rdquo; read as <b>show variants</b> &mdash; pieces duplicated"),
]
PROBE = ["dualuse_woman_top_denim_skirt_nonceleb", "g024",
         "dualuse_man_black_suit_studio_nonceleb", "g018"]
FULL = ["QX", "QF", "QM", "QFA", "QMA", "QMB"]


def web(src, dst, width=420):
    out = os.path.join(IMG, dst)
    if not os.path.exists(src):
        return None
    if not os.path.exists(out):
        im = Image.open(src).convert("RGB")
        if im.width > width:
            im = im.resize((width, int(im.height * width / im.width)), Image.LANCZOS)
        im.save(out, quality=87, optimize=True)
    return "img_ext/" + dst


def fig(src, cap, cls=""):
    if not src:
        return ("<figure class='miss'><div class='ph'>not run</div>"
                f"<figcaption>{cap}</figcaption></figure>")
    return (f"<figure class='{cls}'><img src='{src}' alt='{cap}' loading='lazy'>"
            f"<figcaption>{cap}</figcaption></figure>")


def ref(g, tag):
    return web(os.path.join(RUN, "refs", f"{g}__{tag}.jpg"), f"{g}__{tag}.jpg")


def flagged(d):
    return (abs(d["dL"]) > 12 or abs(d["dC"]) > 10 or d["dHue"] > 25
            or d["dEdge"] > 1.9 or d["dEdge"] < 0.5)


def drift():
    sys.path.insert(0, os.path.join(REPO, "v2", "build"))
    import extraction_drift as D
    rows = list(csv.DictReader(open(os.path.join(REPO, "v3/testsets/v30_matrix_b.csv"))))
    out, agg = {}, {t: [] for t in FULL}
    for r in rows:
        g = r["garment"]
        base = os.path.join(RUN, "refs", f"{g}__BC.jpg")
        if not os.path.exists(base):
            continue
        raw = cv2.imread(base)
        out[g] = {}
        for tag in FULL:
            f = os.path.join(RUN, "refs", f"{g}__{tag}.jpg")
            if not os.path.exists(f):
                continue
            dd = D.compare(raw, cv2.imread(f))
            if dd:
                out[g][tag] = dd
                agg[tag].append(dd)
    return rows, out, agg


def main():
    os.makedirs(IMG, exist_ok=True)
    rows, dr, agg = drift()
    o = [HEAD, "<div class='wrap'>"]

    # 1. The prompts, each with what it broke.
    o.append("<h2>1 &middot; Every prompt tried, and what each one broke</h2>")
    o.append("<p class='note'>The failures are the argument, so they are all here. "
             "Prompts of record: <code>EXTRACT</code> in <code>v3/build/run_v30.py</code>.</p>")
    for tag, pid, label, fixed, broke in LINE:
        n = len([g for g in dr if os.path.exists(os.path.join(RUN, "refs", f"{g}__{tag}.jpg"))])
        n = n or len([g for g in PROBE
                      if os.path.exists(os.path.join(RUN, "refs", f"{g}__{tag}.jpg"))])
        good = "good" if tag == "QMB" else ""
        o.append(
            f"<div class='pr {good}'><div class='prh'><b>{tag}</b>"
            f"<code>{pid}</code><span>{label}</span>"
            f"<span class='n'>{n} references</span></div>"
            f"<pre>{html.escape(R.EXTRACT[tag])}</pre>"
            f"<div class='fx'><span class='ok'>fixed</span> {fixed}</div>"
            f"<div class='fx'><span class='no'>broke</span> {broke}</div></div>")

    # 2. The probe cohort, whole evolution.
    o.append("<h2>2 &middot; The four probe references, through every prompt</h2>")
    o.append("<p class='note'>Four multi-piece outfits &mdash; a tank with shorts and "
             "sneakers, a sweater with a skirt and shoes, a suit with shoes, and a "
             "blazer with trousers. Read left to right: pieces appear, then invented "
             "accessories appear, then heads appear, then duplicates appear.</p>")
    for g in PROBE:
        o.append(f"<h3>{g}</h3><div class='strip s9'>"
                 + fig(web(os.path.join(RUN, "inputs", f"{g}.jpg"), f"{g}__raw.jpg"),
                       "raw photograph")
                 + "".join(fig(ref(g, t), f"{t} &middot; {p}",
                               "good" if t == "QMB" else "")
                           for t, p, _, _, _ in LINE) + "</div>")

    # 3. All references, the five shapes that cover the whole set.
    o.append("<h2>3 &middot; All 28 references &mdash; the five shapes run over the whole set</h2>")
    head = ("<tr><th>shape</th><th>|dL|</th><th>|dC|</th><th>dHue</th>"
            "<th>edge kept</th><th>flagged</th></tr>")
    body = []
    for tag in FULL:
        ds = agg[tag]
        n = len(ds) or 1
        fl = sum(1 for d in ds if flagged(d))
        lbl = next(f"{t} &middot; {lb}" for t, p, lb, _, _ in LINE if t == tag)
        body.append(f"<tr><td>{lbl}</td>"
                    f"<td>{sum(abs(d['dL']) for d in ds)/n:.1f}</td>"
                    f"<td>{sum(abs(d['dC']) for d in ds)/n:.1f}</td>"
                    f"<td>{sum(d['dHue'] for d in ds)/n:.0f}&deg;</td>"
                    f"<td>&times;{sum(d['dEdge'] for d in ds)/n:.2f}</td>"
                    f"<td class='{'bad' if fl > len(ds)*.5 else 'mid'}'>{fl}/{len(ds)}</td></tr>")
    o.append("<table>" + head + "".join(body) + "</table>")
    o.append(DRIFTNOTE)
    for r in rows:
        g = r["garment"]
        bits = [b for b in (r["garment_category"], r["garment_hard_case"]) if b]
        o.append(f"<h3 id='{g}'>{g}"
                 + (f"<span class='sub'> &middot; {html.escape(' · '.join(bits))}</span>"
                    if bits else "") + "</h3>")
        cells = [fig(web(os.path.join(RUN, "inputs", f"{g}.jpg"), f"{g}__raw.jpg"), "raw"),
                 fig(ref(g, "BC"), "BC &middot; subtractive crop")]
        for tag in FULL:
            dd = dr.get(g, {}).get(tag)
            lbl = next(f"{t} &middot; {lb}" for t, p, lb, _, _ in LINE if t == tag)
            cap = (f"{lbl}<span class='n'>hue {dd['dHue']:.0f}&deg; &middot; edge "
                   f"&times;{dd['dEdge']:.2f}</span>") if dd else lbl
            cells.append(fig(ref(g, tag), cap, "warn" if dd and flagged(dd) else ""))
        o.append("<div class='strip s7'>" + "".join(cells) + "</div>")

    o.append(FOOT + "</div>" + LB + SCRIPT)
    open(os.path.join(REPORT, "extraction_shapes.html"), "w").write("\n".join(o))
    print(f"v3/report/extraction_shapes.html  ({len(rows)} references, {len(LINE)} prompts)")


HEAD = """<title>Extraction shapes</title>
<meta name='viewport' content='width=device-width,initial-scale=1'>
<style>
:root{--bg:#0d0d10;--fg:#e8e8ea;--dim:#8a8a94;--line:#26262c;--acc:#7c5cff;
 --good:#3fb950;--mid:#d29922;--bad:#f85149}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
 font:15px/1.6 ui-sans-serif,-apple-system,"Segoe UI",Roboto,sans-serif}
.wrap{max-width:1500px;margin:0 auto;padding:30px 26px 0}
h1{margin:0 0 6px;font-size:25px}
h2{font-size:20px;margin:52px 0 8px;padding-top:16px;border-top:1px solid var(--line)}
h3{font-size:14px;margin:26px 0 6px;color:var(--fg);font-weight:600}
h3 .sub{font-size:12px;color:var(--dim);font-weight:400}
.lede{color:var(--dim);max-width:90ch;font-size:14px;margin:0 0 16px}
.lede b{color:var(--fg)}
.note{color:#c8c8d0;max-width:92ch;font-size:13.5px;margin:8px 0 14px}
table{border-collapse:collapse;font-size:13px;margin:16px 0}
th,td{padding:6px 14px;border-bottom:1px solid #1d1d23;text-align:right}
th:first-child,td:first-child{text-align:left}
th{color:var(--dim);font-weight:600}
.bad{color:var(--bad);font-weight:700}.mid{color:var(--mid)}
.q{border-left:3px solid var(--acc);padding:2px 0 2px 14px;margin:16px 0;max-width:92ch;
 font-size:13.5px;color:#c8c8d0}
.q b{color:var(--fg)}
.pr{border:1px solid var(--line);border-radius:9px;background:#101014;margin:10px 0;
 overflow:hidden}
.pr.good{border-color:#2c5c33}
.prh{display:flex;gap:10px;align-items:center;padding:8px 14px;background:#141419;
 border-bottom:1px solid var(--line);font-size:13px;flex-wrap:wrap}
.prh b{font-size:14px}
.prh span{color:var(--dim);font-size:12.5px}
.prh .n{margin-left:auto;font-size:11px}
.pr pre{margin:0;padding:11px 15px;font:12.5px/1.65 ui-monospace,SFMono-Regular,monospace;
 white-space:pre-wrap;color:#b9b9c4;background:#0b0b0e}
.fx{padding:6px 15px;font-size:13px;border-top:1px solid #17171d}
.fx span{display:inline-block;min-width:52px;font-size:10.5px;text-transform:uppercase;
 letter-spacing:1px;font-weight:700}
.fx .ok{color:var(--good)}.fx .no{color:var(--bad)}
.strip{display:grid;gap:5px;margin-bottom:6px}
.s9{grid-template-columns:repeat(9,1fr)}
.s7{grid-template-columns:repeat(8,1fr)}
@media(max-width:1200px){.s9{grid-template-columns:repeat(5,1fr)}
 .s7{grid-template-columns:repeat(4,1fr)}}
@media(max-width:760px){.s9,.s7{grid-template-columns:repeat(2,1fr)}}
figure{margin:0}
figure img{width:100%;display:block;background:#fff;border-radius:5px;cursor:zoom-in;
 aspect-ratio:3/4;object-fit:contain}
figcaption{font-size:10.5px;color:var(--dim);text-align:center;padding:4px 2px;
 line-height:1.35}
figcaption .n{display:block;font-size:9.5px;opacity:.85}
figure.warn img{outline:2px solid var(--mid);outline-offset:-2px}
figure.good img{outline:2px solid var(--good);outline-offset:-2px}
figure.good figcaption{color:var(--good);font-weight:700}
.ph{background:#17171d;border:1px dashed var(--line);border-radius:5px;aspect-ratio:3/4;
 display:flex;align-items:center;justify-content:center;color:var(--dim);font-size:11px}
#lb{display:none;position:fixed;inset:0;background:rgba(0,0,0,.95);z-index:99;
 align-items:center;justify-content:center;flex-direction:column;gap:10px;padding:20px}
#lb.on{display:flex}#lb img{max-width:95vw;max-height:90vh;object-fit:contain;background:#fff}
#lbc{color:var(--dim);font-size:13px}
footer{border-top:1px solid var(--line);margin-top:44px;padding:22px 0 30px;
 color:var(--dim);font-size:12.5px}
code{background:#1b1b22;padding:1px 5px;border-radius:4px;font-size:12px}
</style>
<div class='wrap'><h1>What shape should the reference be &mdash; and what wording gets the whole outfit?</h1>
<p class='lede'>The shipped extraction prompt says <b>&ldquo;the garment&rdquo;, singular</b>, and
the model takes it literally: pieces go missing, footwear and jewellery almost always.
Eight prompts were tried. Each fixed something and broke something else, and the sequence
of breakages is the useful part. <b>Amber outline = past a drift flag. Green = clean on
every probe.</b> Click any image for full size.</p></div>
"""

DRIFTNOTE = """<div class='q'>Drift is measured against the <b>subtractive crop</b> &mdash;
the same garment on the same white ground, arrived at by cutting instead of regenerating.
<b>The raw photograph was tried first and is the wrong baseline:</b> the statistics run
over non-white pixels, so against a raw frame they compare the garment to the entire
scene and report a lightness drift near 90 for every shape. Recorded because that wrong
number is plausible enough to be quoted.</div>
<div class='q'><b>One caveat on the mannequin rows.</b> Their lightness figure is inflated
by the mannequin itself: it renders as a light grey form, which is not white enough to be
excluded and is therefore counted as garment. V2's finding that the mannequin prompt
&ldquo;makes it pale and simple&rdquo; may be measuring the mannequin rather than the
clothing. <b>Do not quote the mannequin dL until it is re-measured with the form masked
out.</b></div>"""

FOOT = """<footer>References: <code>v3/runs/v3.0b/refs/{ref}__{tag}.jpg</code>.
Prompts of record: <code>EXTRACT</code> in <code>v3/build/run_v30.py</code>, each with the
failure it produced in the comment above it. Statistics recomputed by
<code>v2/build/extraction_drift.py</code> &mdash; a rank, not a verdict: a changed collar
or a moved seam appears in none of these columns.</footer>"""

LB = "<div id='lb'><img id='lbi' alt=''><div id='lbc'></div></div>"
SCRIPT = """<script>
document.addEventListener('click',e=>{const im=e.target.closest('figure img');
  if(!im)return;document.getElementById('lbi').src=im.getAttribute('src');
  document.getElementById('lbc').textContent=im.getAttribute('alt').replace(/&middot;/g,'-');
  document.getElementById('lb').classList.add('on');});
document.getElementById('lb').addEventListener('click',()=>
  document.getElementById('lb').classList.remove('on'));
document.addEventListener('keydown',e=>{if(e.key==='Escape')
  document.getElementById('lb').classList.remove('on')});
</script>"""

if __name__ == "__main__":
    main()
