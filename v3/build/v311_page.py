"""The v3.11 page - the garment-type selector, and the two ways of building it, side by side.

Per garment: the inputs, the bald frames each arm produced (with the hip row drawn on them), then
one row per region - `upper`, `full`, `lower` - carrying each arm's reference and, beside it, the
try-ons under BOTH call-2 texts.

  A  crop only: call 1 is BALD_PROMPT byte for byte, the band is cut on the mask.
  B  call 1 also neutralises the half the user did not select, with a plain white garment.
  S  call 2 is ER byte for byte - the control, and what the first run made.
  R  call 2 names the half being replaced and says the other half is the person's own.

S and R sit side by side per reference: same reference, same seed, different instruction. If R
holds the unselected half where S does not, the prompt was what the first run was missing.

NOT blind, and not a marking instrument. v3.11 asks whether a selector is buildable and which
mechanism delivers it - a question answered by looking, not by counting. Arms are labelled, the
hip row is drawn, and a reference that fell back to `full` says so on its face.

Two questions per try-on, and the second is the one that decides it:

  1. Did the selected half get swapped?
  2. Did the UNSELECTED half survive untouched - are the person's own trousers still their own
     trousers when the user asked for a top?

  python3 v3/build/v311_page.py [run_dir] [out_html]
      defaults: v3/runs/v311/a100  ->  v3/report/v311.html
"""
import csv
import html
import json
import os
import sys

from PIL import Image, ImageDraw

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RUN = sys.argv[1] if len(sys.argv) > 1 else os.path.join(REPO, "v3", "runs", "v311", "a100")
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(REPO, "v3", "report", "v311.html")
SET = os.path.join(REPO, "v3", "colab", "v311_set.csv")
IMG = os.path.join(os.path.dirname(OUT), "img_v311")
ROWS = ("upper", "full", "lower")      # reads down the body
SAID = {"upper": "UPPER HALF", "full": "FULL BODY", "lower": "LOWER HALF"}
PLAN = {"upper": ("A", "B"), "full": ("A",), "lower": ("A", "B")}
# the call-2 texts, side by side: same reference, same seed, different instruction
PROMPTS = (("S", "call 2 · ER as shipped", "ER"),
           ("R", "call 2 · names the region", "REGION"))
REF_W, GEN_W, BALD_W = 240, 200, 220


def web(src, name, width, hip=None):
    """Copy an image into the page folder at `width`; with `hip`, draw the hip row on it."""
    if not os.path.exists(src):
        return None, None
    out = os.path.join(IMG, name)
    im = Image.open(src).convert("RGB")
    wh = f"{im.width}x{im.height}"
    if not os.path.exists(out):
        if hip is not None and 0 <= hip < im.height:
            im = im.copy()
            ImageDraw.Draw(im).line([(0, hip), (im.width, hip)], fill=(229, 72, 77),
                                    width=max(2, im.height // 300))
        if im.width > width:
            im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
        im.save(out, quality=90, optimize=True)
    return os.path.relpath(out, os.path.dirname(OUT)), wh


def figure(src, name, width, caption, cls=""):
    u, wh = web(src, name, width)
    if not u:
        return f'<div class=miss>missing</div>'
    return (f'<figure class="{cls}"><img loading=lazy src="{u}" onclick="z(this)">'
            f'<figcaption>{html.escape(caption)} · {wh}</figcaption></figure>')


def main():
    meta_path = os.path.join(RUN, "meta", "v311_meta.json")
    if not os.path.exists(meta_path):
        raise SystemExit(f"no run at {RUN} - unpack the notebook's zip there first")
    meta = json.load(open(meta_path))
    rows = list(csv.DictReader(open(SET)))
    os.makedirs(IMG, exist_ok=True)
    by_garment = {}
    for r in rows:
        by_garment.setdefault(r["garment"], []).append(r)

    blocks, n_gen = [], 0
    for g, cells in by_garment.items():
        info = meta.get("garments", {}).get(g, {})
        hip = next((i.get("hip_y") for i in info.values() if i.get("hip_y") is not None), None)
        balds = []
        for c in dict.fromkeys(x["person"] for x in cells):
            u, wh = web(os.path.join(RUN, "in1mp", f"{c}.jpg"), f"in_{c}.jpg", BALD_W)
            if u:
                balds.append(f'<figure class=inp><img loading=lazy src="{u}" onclick="z(this)">'
                             f'<figcaption>INPUT person · {html.escape(c[:28])} · {wh}</figcaption></figure>')
        u, wh = web(os.path.join(RUN, "in1mp", f"{g}.jpg"), f"in_{g}.jpg", BALD_W)
        if u:
            balds.append(f'<figure class=inp><img loading=lazy src="{u}" onclick="z(this)">'
                         f'<figcaption>INPUT garment · {wh}</figcaption></figure>')
        for key, label in (("A", "call 1 of record"), ("B_upper", "B · lower neutralised"),
                           ("B_lower", "B · upper neutralised")):
            u, wh = web(os.path.join(RUN, "refs", f"{g}__bald_{key}.jpg"),
                        f"{g}__bald_{key}.jpg", BALD_W, hip=hip)
            if u:
                balds.append(f'<figure><img loading=lazy src="{u}" onclick="z(this)">'
                             f'<figcaption>INTERMEDIATE bald frame · {html.escape(label)} · {wh}</figcaption></figure>')

        region_rows = []
        for region in ROWS:
            cols = []
            for arm in ("A", "B"):
                if arm not in PLAN[region]:
                    cols.append('<div class="col none"><h4>B</h4>'
                                '<div class=note>nothing unselected to neutralise —<br>B’s call 1 '
                                'would be A’s, so <i>full</i> is generated once</div></div>')
                    continue
                i = info.get(f"{arm}_{region}", {})
                fell = i.get("fallback", "")
                ref = figure(os.path.join(RUN, "refs", f"{g}__{arm}_{region}.jpg"),
                             f"{g}__{arm}_{region}.jpg", REF_W,
                             f"INTERMEDIATE reference{' · fell back' if fell else ''}", cls="ref")
                groups = []
                for ptag, head, short in PROMPTS:
                    if ptag == "R" and region == "full":
                        continue            # nothing to name: full is the whole outfit
                    tag = f"{arm}_{region}" if ptag == "S" else f"{arm}_{region}_R"
                    shots = []
                    for c in cells:
                        src = os.path.join(RUN, "gen",
                                           f"{c['set_id']}__{tag}__s{c['seed']}.jpg")
                        if os.path.exists(src):
                            shots.append(f'<div class=gen><div class="badge {region}">'
                                         f'OUTPUT · {SAID[region]} · {short}</div>'
                                         + figure(src, os.path.basename(src), GEN_W, c["person"])
                                         + '</div>')
                            n_gen += 1
                    if shots:               # an arm that has not been generated simply is not drawn
                        groups.append(f'<div class="pgroup {ptag}"><div class=phead>{head}</div>'
                                      f'<div class=shots>{"".join(shots)}</div></div>')
                gens = groups
                kept = i.get("kept_fraction")
                cols.append(f"""<div class="col{' fell' if fell else ''}">
  <h4>{arm} · {'crop only' if arm == 'A' else 'call 1 neutralises the other half'}</h4>
  {ref}
  <div class=meta>{'kept ' + format(kept, '.1%') + ' of the subject' if kept is not None else '&nbsp;'}</div>
  {f'<div class=why>fell back to full: {html.escape(fell)}</div>' if fell else ''}
  <div class=gens>{''.join(gens)}</div>
</div>""")
            region_rows.append(f'<div class=region><div class="rlabel {region}">'
                               f'{SAID[region]}</div>'
                               f'<div class=cols>{"".join(cols)}</div></div>')

        blocks.append(f"""<section>
  <h2>{html.escape(g)} <span class=sub>hip row {f'{hip:.0f}' if hip is not None else 'not found'}
    · {html.escape(', '.join(c['person'] for c in cells))}</span></h2>
  <div class=balds>{''.join(balds)}</div>
  {''.join(region_rows)}
</section>""")

    cost = os.path.join(RUN, "meta", "cost_v311.json")
    c = json.load(open(cost)) if os.path.exists(cost) else {}
    foot = (f"{c.get('klein_calls','?')} klein calls · {c.get('wall_minutes','?')} min · "
            f"CAD {c.get('cad_gpu','?')}" if c else "")

    doc = f"""<!doctype html><meta charset=utf-8><title>v3.11 — the garment-type selector</title>
<style>
body{{background:#111;color:#eee;font:14px/1.55 system-ui,sans-serif;margin:0;padding:0 18px 80px;max-width:1600px}}
h1{{font-size:19px;margin:20px 0 6px}} p.lede{{color:#9aa;max-width:66em;margin:0 0 8px}}
b.q{{color:#cde;font-weight:600}}
section{{border-top:1px solid #333;margin-top:28px;padding-top:12px}}
h2{{font-size:15px;margin:0 0 10px;font-weight:600}}
.sub{{color:#889;font-weight:400;font-size:12px;margin-left:8px}}
.balds{{display:flex;gap:10px;margin-bottom:14px}}
.region{{display:flex;gap:12px;align-items:flex-start;border-top:1px solid #222;padding:10px 0}}
.rlabel{{flex:0 0 104px;font-weight:800;font-size:15px;padding-top:4px;letter-spacing:.02em}}
.rlabel.upper{{color:#7fd1ff}} .rlabel.lower{{color:#ffc46b}} .rlabel.full{{color:#b6f5a8}}
.gen{{position:relative}}
.ref figcaption{{color:#8a8f98}}
.inp{{outline:2px solid #4a7; border-radius:4px}}
.inp figcaption{{color:#8fe3b0;font-weight:700}}
.badge{{font-weight:800;font-size:11px;letter-spacing:.04em;padding:2px 7px;border-radius:4px;
display:inline-block;margin:0 0 3px;color:#06121a}}
.badge.upper{{background:#7fd1ff}} .badge.lower{{background:#ffc46b}} .badge.full{{background:#b6f5a8}}
.cols{{display:flex;gap:18px;flex-wrap:wrap}}
.col{{flex:0 0 {REF_W + GEN_W * 4 + 60}px;display:flex;gap:8px;flex-wrap:wrap;align-items:flex-start}}
.pgroup{{border:1px solid #2a2f36;border-radius:6px;padding:6px 8px 8px}}
.pgroup.R{{border-color:#5a4b2a;background:#1a170f}}
.phead{{font-size:11px;font-weight:700;color:#9bd;margin-bottom:4px;white-space:nowrap}}
.pgroup.R .phead{{color:#e8c07d}}
.shots{{display:flex;gap:8px}}
.col h4{{flex:0 0 100%;font-size:12px;margin:0 0 4px;color:#9bd;font-weight:600}}
.col.fell h4{{color:#e8a33d}}
.col.none .note{{color:#778;font-size:11px;max-width:220px}}
figure{{margin:0}} figure.ref img{{border:1px solid #345}}
img{{display:block;border-radius:5px;cursor:zoom-in;background:#000;max-width:{GEN_W}px}}
figcaption{{color:#889;font-size:10px;margin-top:3px;max-width:{GEN_W}px;overflow:hidden;
text-overflow:ellipsis;white-space:nowrap}}
.meta,.why{{flex:0 0 100%;font-size:11px}} .meta{{color:#889}} .why{{color:#e8a33d}}
.gens{{display:flex;gap:10px;flex-wrap:wrap}}
.miss{{color:#a55;font-size:12px;padding:16px 0}}
#lb{{position:fixed;inset:0;background:#000e;display:none;align-items:center;justify-content:center;z-index:9;cursor:zoom-out}}
#lb img{{max-width:96vw;max-height:96vh;width:auto;max-height:96vh;border-radius:0}}
footer{{color:#778;margin-top:34px;font-size:12px}}
</style>
<h1>v3.11 — choosing the garment type: upper, lower, or the whole outfit</h1>
<p class=lede>A full-body photograph goes in and the user asks for <i>the top</i>. Two ways to
build the reference that delivers it: <b>A</b> cuts the garment reference at the hip and leaves
call 1 alone; <b>B</b> also has call 1 replace the half you did not select with a plain white
garment, so the crop has something uniform to cut against.</p>
<p class=lede><b class=q>1.</b> Did the selected half get swapped?
&nbsp;&nbsp;<b class=q>2.</b> Did the unselected half survive untouched — are the person's own
trousers still their own trousers when they asked for a top? The second question is the one that
decides whether a selector is a crop change or a much larger piece of work.</p>
<p class=lede>Each reference carries <b>two</b> sets of try-ons, side by side: <b class=q>call 2 ·
ER as shipped</b> (the control, what the first run made) and <b class=q>call 2 · names the
region</b> — same reference, same seed, different instruction. <i>full</i> has no half to name, so
it is shown under ER only.</p>
<p class=lede>The red line on each bald frame is the hip row the band was cut at. <b>B departs
from the call-1 prompt of record</b>, so no earlier number transfers to it.</p>
{''.join(blocks)}
<footer>{foot} · {n_gen} try-ons · run {html.escape(os.path.relpath(RUN, REPO))}</footer>
<div id=lb onclick="this.style.display='none'"><img></div>
<script>
function z(el){{const b=document.getElementById('lb');b.querySelector('img').src=el.src;b.style.display='flex';}}
document.addEventListener('keydown',e=>{{if(e.key==='Escape')document.getElementById('lb').style.display='none';}});
</script>
"""
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, "w").write(doc)
    print(f"{os.path.relpath(OUT, REPO)}  ({len(blocks)} garments, {n_gen} try-ons)")


if __name__ == "__main__":
    main()
