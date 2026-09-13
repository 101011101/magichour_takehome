"""One row per try-on: the two photographs that went in, then every output for that pair.

The other page carries the bald frames and the references, which is what you want when a
reference looks wrong. This one answers the only question the selector has to pass: with a
half chosen, does the other half come back the person's own. So it shows the inputs and the
outputs, and nothing in between.

  python3 v3/build/v311_outputs_page.py   ->  v3/report/v311_outputs.html
"""
import csv
import html
import os
import sys

from PIL import Image

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RUN = os.path.join(REPO, "v3", "runs", "v311", "a100")
REPORT = os.path.join(REPO, "v3", "report")
SET = os.path.join(REPO, "v3", "colab", "v311_set.csv")
IMG = os.path.join(REPORT, "img_v311out")
# --selector: only the candidate feature - the band cut AND a call 2 that names it
SELECTOR_ONLY = "--selector" in sys.argv
OUT_HTML = "v311_selector.html" if SELECTOR_ONLY else "v311_outputs.html"
IN_W, OUT_W = 300, 300
SAID = {"upper": "UPPER HALF", "full": "FULL BODY", "lower": "LOWER HALF"}
# (arm, region, prompt tag, what to call it)
COLS = [("A", "ER"), ("A", "REGION"), ("B", "ER"), ("B", "REGION")]


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
    return "img_v311out/" + dst, f"{w}x{h}"


def fig(src, dst, width, label, cls=""):
    u, wh = web(src, dst, width)
    if not u:
        return '<div class=miss>not generated</div>'
    return (f'<figure class="{cls}"><img loading=lazy src="{u}" onclick="z(this)">'
            f'<figcaption>{label} · {wh}</figcaption></figure>')


def main():
    rows = list(csv.DictReader(open(SET)))
    os.makedirs(IMG, exist_ok=True)
    blocks, n = [], 0
    for r in rows:
        sid, p, g, seed = r["set_id"], r["person"], r["garment"], r["seed"]
        ins = (fig(os.path.join(RUN, "in1mp", f"{p}.jpg"), f"in_{p}.jpg", IN_W,
                   "INPUT person", "inp")
               + fig(os.path.join(RUN, "in1mp", f"{g}.jpg"), f"in_{g}.jpg", IN_W,
                     "INPUT garment", "inp"))
        region_rows = []
        for region in ("upper", "lower", "full"):
            cells = []
            for arm, ptag in COLS:
                if region == "full" and (arm == "B" or ptag == "REGION"):
                    continue
                if SELECTOR_ONLY and (ptag != "REGION" or region == "full"):
                    continue
                suffix = "_R" if ptag == "REGION" else ""
                src = os.path.join(RUN, "gen", f"{sid}__{arm}_{region}{suffix}__s{seed}.jpg")
                if not os.path.exists(src):
                    continue
                n += 1
                cells.append(
                    f'<div class=out><div class="badge {region}">OUTPUT · {SAID[region]}</div>'
                    f'<div class=how>arm {arm} · call 2 {"names the region" if ptag == "REGION" else "as shipped"}</div>'
                    + fig(src, os.path.basename(src), OUT_W, f"arm {arm} · {ptag}") + '</div>')
            if cells:
                region_rows.append(f'<div class=rrow><div class="rlabel {region}">{SAID[region]}</div>'
                                   f'<div class=outs>{"".join(cells)}</div></div>')
        blocks.append(f"""<section>
  <h2>{html.escape(p[:38])} <span class=x>wearing</span> {html.escape(g[:38])}</h2>
  <div class=io><div class=ins>{ins}</div><div class=rs>{''.join(region_rows)}</div></div>
</section>""")

    doc = f"""<!doctype html><meta charset=utf-8><title>v3.11 — inputs and outputs</title>
<style>
body{{background:#0f1114;color:#e8eaed;font:14px/1.55 system-ui,sans-serif;margin:0;padding:0 18px 80px}}
h1{{font-size:19px;margin:20px 0 4px}} p.lede{{color:#9aa4b2;max-width:64em;margin:0 0 18px}}
section{{border-top:1px solid #23262b;padding:18px 0}}
h2{{font-size:15px;margin:0 0 12px;color:#dfe6f2}} h2 .x{{color:#6b7280;font-weight:400}}
.io{{display:flex;gap:26px;align-items:flex-start;flex-wrap:wrap}}
.ins{{display:flex;gap:10px;position:sticky;top:12px}}
.rs{{flex:1;min-width:520px}}
.rrow{{display:flex;gap:14px;align-items:flex-start;padding:8px 0;border-top:1px solid #1b1e23}}
.rlabel{{flex:0 0 108px;font-weight:800;font-size:15px;padding-top:26px}}
.rlabel.upper{{color:#7fd1ff}} .rlabel.lower{{color:#ffc46b}} .rlabel.full{{color:#b6f5a8}}
.outs{{display:flex;gap:14px;flex-wrap:wrap}}
figure{{margin:0}} img{{display:block;border-radius:4px;cursor:zoom-in;max-width:100%}}
figcaption{{color:#8a8f98;font-size:11px;padding-top:3px}}
.inp img{{outline:2px solid #3fa06b}} .inp figcaption{{color:#8fe3b0;font-weight:700}}
.badge{{font-weight:800;font-size:11px;letter-spacing:.04em;padding:2px 7px;border-radius:4px;
display:inline-block;color:#06121a}}
.badge.upper{{background:#7fd1ff}} .badge.lower{{background:#ffc46b}} .badge.full{{background:#b6f5a8}}
.how{{color:#9aa4b2;font-size:11px;margin:3px 0 4px}}
.miss{{color:#6b7280;font-size:12px;padding:20px 0}}
#zz{{position:fixed;inset:0;background:#000d;display:none;align-items:center;justify-content:center;z-index:9}}
#zz img{{max-width:96vw;max-height:96vh}}
</style>
<h1>{'v3.11 — the selector: band cut, and a call 2 that names it' if SELECTOR_ONLY else 'v3.11 — what went in, and what came out'}</h1>
<p class=lede>{'Only the candidate feature is shown: the reference cut at the hip AND a call 2 naming the half. Arm A cuts alone; arm B also neutralises the other half in call 1.' if SELECTOR_ONLY else 'The two photographs on the left are the inputs.'}
<br>The two photographs on the left are the inputs. Everything to the right is an output.
With <b>UPPER HALF</b> chosen, the trousers in the output should still be the trousers in the input
person photo — that is the whole test. Intermediates are on <a href="v311.html">the other page</a>.
Click any image to enlarge.</p>
{''.join(blocks)}
<div id=zz onclick="this.style.display='none'"><img></div>
<script>
function z(el){{const d=document.getElementById('zz');d.querySelector('img').src=el.src;d.style.display='flex';}}
</script>
"""
    open(os.path.join(REPORT, OUT_HTML), "w").write(doc)
    print(f"v3/report/{OUT_HTML}  ({len(rows)} pairs, {n} outputs)")


if __name__ == "__main__":
    main()
