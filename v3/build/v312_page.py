"""One row per product shot: where the band would cut, and what came out.

Runbo asked whether a flat-lay "won't work 4 times out of 10". The count it comes from measures
the detector, not the outcome: on some of these person-free photographs Pose reports a hip and
the band cuts at a row it invented, and on the rest nothing fires and the request quietly
becomes a whole-outfit swap. This page puts the drawn cut line beside the try-on it produced so
the difference between a silent error and a visible no-op can be seen rather than described.

  python3 v3/build/v312_page.py   ->  v3/report/v312.html
"""
import csv
import html
import json
import os

from PIL import Image

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RUN = os.path.join(REPO, "v3", "runs", "v312", "a100")
REPORT = os.path.join(REPO, "v3", "report")
SET = os.path.join(REPO, "v3", "colab", "v312_set.csv")
IMG = os.path.join(REPORT, "img_v312")
HIP_W, REF_W, GEN_W = 340, 210, 260
REGIONS = (("full", "A_full", "FULL BODY"), ("upper", "A_upper_R", "UPPER HALF"),
           ("lower", "A_lower_R", "LOWER HALF"))


def web(src, dst, width):
    if not os.path.exists(src):
        return None, None
    out = os.path.join(IMG, dst)
    if not os.path.exists(out):
        im = Image.open(src).convert("RGB")
        if im.width > width:
            im = im.resize((width, int(im.height * width / im.width)), Image.LANCZOS)
        im.save(out, quality=88, optimize=True)
    w, h = Image.open(src).size
    return "img_v312/" + dst, f"{w}x{h}"


def fig(src, dst, width, cap, cls=""):
    u, wh = web(src, dst, width)
    if not u:
        return '<div class=miss>not generated</div>'
    return (f'<figure class="{cls}"><img loading=lazy src="{u}" onclick="z(this)">'
            f'<figcaption>{cap} · {wh}</figcaption></figure>')


def main():
    meta_p = os.path.join(RUN, "meta", "v312_flatlay.json")
    if not os.path.exists(meta_p):
        raise SystemExit(f"no run at {RUN} - unpack the notebook's zip there first")
    meta = json.load(open(meta_p))
    rows = list(csv.DictReader(open(SET)))
    os.makedirs(IMG, exist_ok=True)
    by_g = {}
    for r in rows:
        by_g.setdefault(r["garment"], []).append(r)

    blocks = []
    for g, cells in sorted(by_g.items()):
        info = meta["garments"].get(g, {})
        hit = info.get("hip_reported")
        badge = ('<div class="verdict hit">HIP DETECTED — the band cuts here</div>'
                 if hit else
                 '<div class="verdict miss2">NO HIP — FELL BACK TO FULL</div>')
        why = (f'the detector placed a hip at {info.get("hip_frac")} of the height of a '
               f'photograph with no person in it'
               if hit else html.escape(info.get("why") or "no landmark"))
        hip_img = fig(os.path.join(RUN, "hip", f"{g}__orig.jpg"), f"hip_{g}.jpg", HIP_W,
                      "the garment photo, with the cut drawn", "hip")
        region_rows = []
        for region, tag, said in REGIONS:
            ri = info.get("regions", {}).get(region, {})
            route = ri.get("route", "")
            fell = ri.get("fallback", "")
            ref = fig(os.path.join(RUN, "refs", f"{g}__A_{region}.jpg"),
                      f"ref_{g}_{region}.jpg", REF_W, "reference", "ref")
            gens = "".join(
                fig(os.path.join(RUN, "gen", f"{c['set_id']}__{tag}__s{c['seed']}.jpg"),
                    f"gen_{c['set_id']}_{tag}.jpg", GEN_W, html.escape(c["person"]))
                for c in cells)
            note = (f'<div class="route fell">fell back: {html.escape(fell)} — the user asked for '
                    f'{said.lower()} and got the whole outfit</div>' if fell else
                    f'<div class="route cut">{html.escape(route)}</div>' if region != "full" else
                    '<div class="route">the control — what the ticket says to send for these</div>')
            region_rows.append(
                f'<div class=rrow><div class="rlabel {region}">{said}</div>'
                f'<div class=rbody>{note}<div class=imgs>{ref}{gens}</div></div></div>')
        blocks.append(f"""<section>
  <h2>{html.escape(g)} <span class=sub>product shot · no person in the photograph</span></h2>
  <div class=io><div class=left>{hip_img}{badge}<div class=why>{why}</div></div>
  <div class=right>{''.join(region_rows)}</div></div>
</section>""")

    c = meta["counts"]
    doc = f"""<!doctype html><meta charset=utf-8><title>v3.12 — regions on a garment-only photo</title>
<style>
body{{background:#0f1114;color:#e8eaed;font:14px/1.55 system-ui,sans-serif;margin:0;padding:0 18px 80px}}
h1{{font-size:19px;margin:20px 0 6px}}
p.lede,.sum{{color:#aab3c0;max-width:70em}}
.sum{{background:#15181d;border:1px solid #23262b;border-radius:8px;padding:14px 16px;margin:14px 0 6px}}
.sum b{{color:#fff}} .sum .n{{font-size:22px;font-weight:800}}
.hit{{color:#ff8a8a}} .miss2{{color:#ffd08a}}
section{{border-top:1px solid #23262b;padding:16px 0}}
h2{{font-size:15px;margin:0 0 10px}} .sub{{color:#6b7280;font-weight:400}}
.io{{display:flex;gap:22px;align-items:flex-start;flex-wrap:wrap}}
.left{{position:sticky;top:12px}} .right{{flex:1;min-width:560px}}
.verdict{{font-weight:800;font-size:12px;letter-spacing:.03em;margin-top:6px}}
.why{{color:#8a8f98;font-size:11px;max-width:340px;margin-top:2px}}
.rrow{{display:flex;gap:12px;padding:9px 0;border-top:1px solid #1b1e23}}
.rlabel{{flex:0 0 104px;font-weight:800;font-size:14px;padding-top:20px}}
.rlabel.upper{{color:#7fd1ff}} .rlabel.lower{{color:#ffc46b}} .rlabel.full{{color:#b6f5a8}}
.rbody{{flex:1}} .imgs{{display:flex;gap:10px;flex-wrap:wrap;align-items:flex-start}}
.route{{font-size:11px;color:#9aa4b2;margin-bottom:4px}}
.route.fell{{color:#ffd08a}} .route.cut{{color:#ff8a8a}}
figure{{margin:0}} img{{display:block;border-radius:4px;cursor:zoom-in;max-width:100%}}
figcaption{{color:#8a8f98;font-size:11px;padding-top:3px}}
.hip img{{outline:2px solid #3fa06b}}
.miss{{color:#6b7280;font-size:12px;padding:16px 0}}
#zz{{position:fixed;inset:0;background:#000d;display:none;align-items:center;justify-content:center;z-index:9}}
#zz img{{max-width:96vw;max-height:96vh}}
</style>
<h1>v3.12 — what a region request does to a garment photo with no person in it</h1>
<div class=sum>
  <div><span class="n hit">{c['cut_at_reported_hip']}</span> of {c['garments']} cut at a hip the detector
  <b>reported on a photograph containing no person</b> — the band slices at an invented row and
  nothing reports a problem.</div>
  <div style="margin-top:6px"><span class="n miss2">{c['fell_back_to_full']}</span> of {c['garments']}
  found no hip and <b>fell back to the whole outfit</b> — safe, and visibly not what was asked for.</div>
  <div style="margin-top:8px">Neither group returns the half the user selected. That is why the ticket
  says to send product shots as <b>full</b>: it is not that some fraction works.</div>
</div>
<p class=lede>Each row: the garment photo with the cut line drawn, then the reference and the
try-ons for each region. <b>FULL BODY</b> is the control. Click any image to enlarge.</p>
{''.join(blocks)}
<div id=zz onclick="this.style.display='none'"><img></div>
<script>function z(el){{const d=document.getElementById('zz');d.querySelector('img').src=el.src;d.style.display='flex';}}</script>
"""
    os.makedirs(REPORT, exist_ok=True)
    open(os.path.join(REPORT, "v312.html"), "w").write(doc)
    print(f"v3/report/v312.html  ({len(by_g)} garments, {c['cut_at_reported_hip']} cut, "
          f"{c['fell_back_to_full']} fell back)")


if __name__ == "__main__":
    main()
