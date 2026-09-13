"""v3/report/v314.html - the consolidation inquiry, read in the order Runbo cares about.

Branch inventory and route frequency first, because "how many ways can this behave" is the
question; the per-garment pictures after, because that is how a quality veto is checked.

  python3 v3/build/v314_page.py
"""
import csv
import html
import json
import os

from PIL import Image

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RUN = os.environ.get("V314_RUN", os.path.join(REPO, "v3", "runs", "v314", "a100"))
REPORT = os.path.join(REPO, "v3", "report")
SET = os.path.join(REPO, "v3", "colab", "v314_set.csv")
IMG = os.path.join(REPORT, "img_v314")
W = 320

# Counted from the code, not estimated: every decision point a garment can take in
# preparation. `head route` is one row per outcome because each is a different code path.
BRANCHES = [
    ("person gate: worn or product", "today", "both candidates", "2 routes"),
    ("head route: parser", "today", "both", "the path that fires"),
    ("head route: pose ellipse fallback", "today", "A removes its input", "fires ~0%"),
    ("head route: face-anchored cranium band", "today", "A removes its input", "fires ~0%"),
    ("head route: none", "today", "A makes this the only fallback", "fires ~0%"),
    ("collar guard (HEAD_CLOTHES_GUARD)", "today", "A removes", "env-switchable"),
    ("neck line found or not", "today", "unchanged - Pose stays", "inside parser_classes"),
    ("nose component kept or not", "today", "unchanged", "inside parser_classes"),
    ("region: full / upper / lower", "today", "unchanged", "3 routes"),
    ("region fallback to full", "today", "B changes its trigger", "no hip, or band <2%"),
]


def web(src, dst, width=W):
    if not os.path.exists(src):
        return None
    out = os.path.join(IMG, dst)
    if not os.path.exists(out):
        im = Image.open(src).convert("RGB")
        if im.width > width:
            im = im.resize((width, int(im.height * width / im.width)), Image.LANCZOS)
        im.save(out, quality=88, optimize=True)
    return "img_v314/" + dst


def fig(src, dst, cap, cls=""):
    u = web(src, dst)
    if not u:
        return '<div class=miss>not generated</div>'
    return (f'<figure class="{cls}"><img loading=lazy src="{u}" onclick="z(this)">'
            f'<figcaption>{cap}</figcaption></figure>')


def main():
    meta_path = os.path.join(RUN, "meta", "v314_meta.json")
    if not os.path.exists(meta_path):
        raise SystemExit(f"no run at {RUN} - unpack the notebook's zip there first")
    rec = json.load(open(meta_path))
    rows = {r["stem"]: r for r in csv.DictReader(open(SET))}
    os.makedirs(IMG, exist_ok=True)

    A = {k: v for k, v in rec.get("A", {}).items() if "mad" in v}
    skipped = [k for k, v in rec.get("A", {}).items() if "skipped" in v]
    B = rec.get("B", {})
    wb = {k: v for k, v in B.items() if v.get("kind") == "worn"}
    pb = {k: v for k, v in B.items() if v.get("kind") == "product"}
    both = {k: v for k, v in wb.items() if v.get("diff") is not None}

    # --- candidate A, worst movers first -------------------------------------------
    cards = []
    for k, v in sorted(A.items(), key=lambda kv: -kv[1]["mad"]):
        verdict = ("<span class=bad>moves the reference</span>" if v["mad"] > 4
                   else "<span class=ok>no visible movement</span>")
        cards.append(f"""<section><h3>{html.escape(k)} — MAD {v['mad']:.2f}, {v['changed_pct']:.2f}% of pixels changed {verdict}</h3>
<div class=pair>{fig(os.path.join(RUN, 'refs', f'{k}__today.jpg'), f'{k}_today.jpg', 'today — parser + selfie union + collar guard')}
{fig(os.path.join(RUN, 'refs', f'{k}__parser_only.jpg'), f'{k}_only.jpg', 'candidate A — parser only')}</div>
<div class=meta>head mask {v['head_px_today']:,} px → {v['head_px_only']:,} px</div></section>""")

    # --- candidate B ----------------------------------------------------------------
    brows = []
    for k, v in sorted(both.items(), key=lambda kv: -kv[1]["diff"]):
        bad = v["diff"] > 0.15
        brows.append(f"<tr class='{'bad' if bad else ''}'><td>{html.escape(k)[:38]}</td>"
                     f"<td>{rows.get(k, {}).get('category', '')}</td>"
                     f"<td>{v['waist']:.2f}</td><td>{v['hip']:.2f}</td>"
                     f"<td>{v['diff']:.3f}</td><td>{html.escape(v['waist_why'])}</td></tr>")
    prows = []
    for k, v in sorted(pb.items()):
        inv = v["waist"] is not None
        prows.append(f"<tr class='{'bad' if inv else ''}'><td>{html.escape(k)}</td>"
                     f"<td>{rows.get(k, {}).get('photo_style', '')}</td>"
                     f"<td>{'INVENTS a waist at %.2f' % v['waist'] if inv else 'correctly none'}</td>"
                     f"<td>{'invents a hip at %.2f' % v['hip'] if v['hip'] is not None else 'correctly none'}</td>"
                     f"<td>{html.escape(v['waist_why'])}</td></tr>")

    binv = "".join(f"<tr><td>{html.escape(a)}</td><td>{html.escape(c)}</td><td>{html.escape(n)}</td></tr>"
                   for a, _t, c, n in BRANCHES)
    reasons = {}
    for v in wb.values():
        reasons[v.get("waist_why", "?")] = reasons.get(v.get("waist_why", "?"), 0) + 1

    doc = f"""<!doctype html><meta charset=utf-8><title>v3.14 — consolidation</title>
<style>
body{{background:#0f1114;color:#e9ecf1;font:14px/1.6 system-ui,sans-serif;margin:0;padding:0 22px 80px;max-width:1180px}}
h1{{font-size:20px;margin:22px 0 6px}} h2{{font-size:16px;margin:28px 0 8px;color:#cfe}}
h3{{font-size:13px;margin:0 0 8px;color:#cfd8e3;font-weight:600}}
.lede{{color:#9aa4b2;max-width:70em}}
table{{border-collapse:collapse;margin:10px 0 4px;font-size:13px}}
td,th{{border:1px solid #2a2e35;padding:5px 11px;text-align:left}} th{{color:#9bd;font-weight:600}}
tr.bad td{{background:#3a1416}}
section{{border-top:1px solid #23262b;padding:12px 0}}
.pair{{display:flex;gap:16px;flex-wrap:wrap}} figure{{margin:0}}
img{{display:block;border-radius:4px;cursor:zoom-in;max-width:100%}}
figcaption{{color:#8a8f98;font-size:11px;padding-top:3px}}
.meta{{color:#8a8f98;font-size:12px;padding-top:4px}}
.ok{{color:#7ee2a8;font-weight:700}} .bad{{color:#ff8a8f;font-weight:700}}
.miss{{color:#6b7280;font-size:12px}}
#zz{{position:fixed;inset:0;background:#000d;display:none;align-items:center;justify-content:center;z-index:9}}
#zz img{{max-width:96vw;max-height:96vh}}
</style>
<h1>v3.14 — can any of the four small models be consolidated?</h1>
<p class=lede>Judged on Runbo's criterion, not on cost: <b>quality must not drop</b>, <b>fewer
branches beats fewer models</b>, and a route that almost never fires is where an unnoticed bug
will live. Consolidating into klein is closed — v3.5 measured the regeneration tax at 9.2%
against 4.8%.</p>

<h2>1 · Branch inventory — the thing that can go wrong</h2>
<p class=lede>Every decision point a garment can take during preparation, counted from the code.</p>
<table><tr><th>decision point</th><th>under the candidates</th><th>note</th></tr>{binv}</table>

<h2>2 · Route frequency — which paths are actually exercised</h2>
<p class=lede>The head route is a chain: parser, then a pose ellipse, then a face-anchored band.
On the record the parser fired on <b>112 of 112</b> and <b>33 of 33</b> garments (v3.5), so the
two fallbacks are near-dead code — simpler to delete than to keep, but deleting them means a
garment the parser cannot read has no head removed at all.</p>
<table><tr><th>parser waist reason (worn photos, this run)</th><th>count</th></tr>
{''.join(f'<tr><td>{html.escape(k)}</td><td>{v}</td></tr>' for k, v in sorted(reasons.items(), key=lambda kv: -kv[1]))}</table>

<h2>3 · Candidate B — the waist from the parser, against the hip from Pose</h2>
<p class=lede>Worn photographs, worst disagreement first. Rows over 0.15 of image height are
flagged: that is a cut in the wrong place, not a rounding difference.</p>
<table><tr><th>garment</th><th>category</th><th>parser waist</th><th>pose hip</th><th>|diff|</th><th>how</th></tr>{''.join(brows)}</table>
<p class=lede>Product shots — the case the parser was hoped to decline:</p>
<table><tr><th>garment</th><th>style</th><th>parser</th><th>pose</th><th>how</th></tr>{''.join(prows)}</table>

<h2>4 · Candidate A — does dropping the segmenter move the reference?</h2>
<p class=lede>Worst mover first. The question is not whether the two are identical but whether
the difference is visible; a reference that moves for the worse is a rejection.
{f'<br><b>Not comparable ({len(skipped)}):</b> {html.escape(", ".join(skipped))} — the parser did not fire, so today falls back and candidate A has nothing to fall back to.' if skipped else ''}</p>
{''.join(cards) if cards else '<p class=lede>No candidate-A measurements in this run.</p>'}
<div id=zz onclick="this.style.display='none'"><img></div>
<script>function z(el){{const d=document.getElementById('zz');d.querySelector('img').src=el.src;d.style.display='flex';}}</script>
"""
    os.makedirs(REPORT, exist_ok=True)
    out = os.path.join(REPORT, "v314.html")
    open(out, "w").write(doc)
    print(f"{out}  ({len(A)} candidate-A pairs, {len(wb)} worn / {len(pb)} product for B)")


if __name__ == "__main__":
    main()
