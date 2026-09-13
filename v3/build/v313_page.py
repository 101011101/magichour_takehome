"""Every candidate person-gate, image by image, with the number behind each verdict.

The gate decides whether a garment photograph has a person in it. Get it wrong one way and a
worn garment skips the bald pass it needs; wrong the other way and a flat-lay is sent through
a pass that invents a wearer. So this page shows each candidate's answer per image, the raw
measurement behind it, and puts every disagreement at the top - those are the only rows worth
a reviewer's time.

Ground truth is `test_set1/manifest.csv`, not anyone's eye: kind=garment with photo_style
flat_lay or ghost_mannequin has no person; everything else here is worn.

  python3 v3/build/v313_page.py [measurements.json]   ->  v3/report/v313.html
"""
import html
import json
import os
import sys

from PIL import Image

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
REPORT = os.path.join(REPO, "v3", "report")
IMG = os.path.join(REPORT, "img_v313")
THUMB = 150

# The candidates live in the runner, so the page and the notebook cannot disagree about
# what "HEAD selfie" means. Falls back to a local copy only if the bundle is not on the path.
sys.path.insert(0, os.path.join(REPO, "v3", "colab", "lib"))
from run_v313 import CANDIDATES  # noqa: E402


def thumb(src, stem):
    dst = os.path.join(IMG, stem + ".jpg")
    if not os.path.exists(dst):
        im = Image.open(os.path.join(REPO, src)).convert("RGB")
        im.thumbnail((THUMB, THUMB * 3), Image.LANCZOS)
        im.save(dst, quality=85, optimize=True)
    return "img_v313/" + stem + ".jpg"


def main(path="/tmp/gate_all.json"):
    rows = json.load(open(path))
    os.makedirs(IMG, exist_ok=True)
    score = {}
    for name, fn, _ in CANDIDATES:
        fp = [r for r in rows if r["truth"] == "no_person" and fn(r)]
        fn_ = [r for r in rows if r["truth"] == "person" and not fn(r)]
        score[name] = (len(fn_), len(fp))
    for r in rows:
        r["_wrong"] = sum(1 for name, fn, _ in CANDIDATES
                          if fn(r) != (r["truth"] == "person"))
    rows.sort(key=lambda r: (-r["_wrong"], r["truth"], r["stem"]))

    head = "".join(f"<th>{html.escape(n)}</th>" for n, _, _ in CANDIDATES)
    body = []
    for r in rows:
        cells = []
        for name, fn, num in CANDIDATES:
            said = fn(r)
            right = said == (r["truth"] == "person")
            cells.append(f'<td class="{"ok" if right else "bad"}">{"person" if said else "no person"}'
                         f'<div class=num>{html.escape(num(r))}</div></td>')
        body.append(
            f'<tr class="{"dis" if r["_wrong"] else ""}">'
            f'<td class=im><img loading=lazy src="{thumb(r["path"], r["stem"])}"></td>'
            f'<td class=st>{html.escape(r["stem"][:34])}<div class=num>{html.escape(r["why"])}</div></td>'
            f'<td class="truth {r["truth"]}">{"person" if r["truth"] == "person" else "no person"}</td>'
            + "".join(cells) + "</tr>")

    summary = "".join(
        f'<tr><td>{html.escape(n)}</td><td class="{"bad" if score[n][0] else "ok"}">{score[n][0]}</td>'
        f'<td class="{"bad" if score[n][1] else "ok"}">{score[n][1]}</td>'
        f'<td class="{"bad" if sum(score[n]) else "ok"}"><b>{sum(score[n])}</b></td></tr>'
        for n, _, _ in CANDIDATES)
    n_p = sum(1 for r in rows if r["truth"] == "person")
    n_n = len(rows) - n_p

    doc = f"""<!doctype html><meta charset=utf-8><title>v3.13 — which person-gate</title>
<style>
body{{background:#0f1114;color:#e9ecf1;font:13px/1.5 system-ui,sans-serif;margin:0;padding:0 18px 70px}}
h1{{font-size:19px;margin:20px 0 4px}} p.lede{{color:#9aa4b2;max-width:70em}}
table{{border-collapse:collapse;margin:14px 0}} th,td{{border:1px solid #262a31;padding:5px 9px;text-align:left;vertical-align:top}}
th{{background:#171a1f;color:#c8d2e0;font-size:12px;position:sticky;top:0}}
td.ok{{background:#14301f;color:#9fe7b8}} td.bad{{background:#3a1418;color:#ff9ca3;font-weight:700}}
td.truth.person{{color:#9fe7b8}} td.truth.no_person{{color:#ffc46b}}
tr.dis td{{border-top:2px solid #e5484d}}
.num{{color:#7d8794;font-size:11px;font-weight:400}}
td.im img{{display:block;border-radius:3px}} td.st{{min-width:180px}}
.sum td,.sum th{{padding:4px 14px}}
</style>
<h1>v3.13 — which test decides whether a photo has a person in it</h1>
<p class=lede>{len(rows)} distinct images: <b>{n_p}</b> with a person wearing the garment,
<b>{n_n}</b> flat-lay or ghost-mannequin. Ground truth is the manifest, not a judgement of the
picture. Every candidate is built from a model the crop already loads. Rows where any candidate
is wrong are at the top, ruled in red; green is a correct verdict, red an incorrect one, and the
small figure is the measurement behind it.</p>
<table class=sum><tr><th>candidate</th><th>missed a worn photo</th><th>missed a flat-lay</th><th>wrong</th></tr>
{summary}</table>
<p class=lede>Missing a worn photo is the dangerous error: that garment would skip the bald pass
it needs. Missing a flat-lay only keeps today's behaviour.</p>
<table><tr><th></th><th>image</th><th>truth</th>{head}</tr>
{''.join(body)}</table>
"""
    open(os.path.join(REPORT, "v313.html"), "w").write(doc)
    print(f"v3/report/v313.html  ({len(rows)} images, {len(CANDIDATES)} candidates)")
    for n, _, _ in CANDIDATES:
        print(f"  {n:14s} missed-worn {score[n][0]}  missed-flatlay {score[n][1]}")


if __name__ == "__main__":
    main(*sys.argv[1:])
