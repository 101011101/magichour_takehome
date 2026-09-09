"""Build the v3.5 link-B page: the head-cropped reference through call 2, on the pairs
v3.4 actually failed.

Every pair on this page is one the reviewer marked FAIL on the locked `VEi` arm in iron
man 2 (`v34_im2_truth.json`) — so the v3.4 verdict per seed rides along on each card, and
the question the page asks is narrow: does the head-crop reference reach a failure the
mannequin reference did not.

Per pair: the person photo, then one column per arm carrying the reference call 2 was
given (as it saw it, SR'd to ~1 MP) above the output it produced.
"""
import csv
import html
import json
import os

from PIL import Image

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RUN = os.path.join(REPO, "v3", "runs", "v35", "linkB")
SRC = os.path.join(REPO, "v3", "runs", "v34", "ironman2")
REPORT = os.path.join(REPO, "v3", "report")
IMG = os.path.join(REPORT, "img_v35b")
SET = os.path.join(REPO, "v3", "testsets", "v35_failures.csv")

LABEL = {"BC": ("BC", "the incumbent: bald pass, V2 crop, head subtracted"),
         "VEi": ("VEi", "the v3.4 lock, as shipped"),
         "M0": ("M0", "the lock's prompt on fal — mannequin + repose"),
         "M0c": ("M0c", "M0 with the mannequin head cut off"),
         "M1": ("M1", "turn only, head kept"),
         "M1c": ("M1c", "turn only, head cut off — the target shape"),
         "M2": ("M2", "mannequin + the explicit turn"),
         "G1": ("G1", "the clothing alone")}


def web(src, dst, width=520):
    if not os.path.exists(src):
        return None, None
    out, full = os.path.join(IMG, dst), os.path.join(IMG, dst.replace(".jpg", "@full.jpg"))
    im = None
    if not os.path.exists(out):
        im = Image.open(src).convert("RGB")
        t = im.resize((width, int(im.height * width / im.width)), Image.LANCZOS) if im.width > width else im
        t.save(out, quality=90, optimize=True)
    if not os.path.exists(full):
        im = im or Image.open(src).convert("RGB")
        im.save(full, quality=94, optimize=True)
    return "img_v35b/" + dst, "img_v35b/" + os.path.basename(full)


def main():
    os.makedirs(IMG, exist_ok=True)
    meta = json.load(open(os.path.join(RUN, "meta", "run.json")))
    arms, seeds = meta["arms"], meta["seeds"]
    rows = {r["set_id"]: r for r in csv.DictReader(open(SET))}
    gen = os.path.join(RUN, "gen")
    made = sorted({f.split("__")[0] for f in os.listdir(gen) if f.endswith(".jpg")})

    cards = []
    for sid in made:
        r = rows[sid]
        pt, pf = web(os.path.join(SRC, "inputs", f"{r['person']}.jpg"), f"{r['person']}__person.jpg")
        verds = " ".join(f"<span class='v v-{r['v' + str(s)].lower()}'>s{s} {r['v' + str(s)]}</span>"
                         for s in (46, 47, 48))
        cols = []
        for arm in arms:
            rt, rf = web(os.path.join(RUN, "refs_sr", f"{r['garment']}__{arm}.jpg"),
                         f"{r['garment']}__{arm}__ref.jpg", 400)
            outs = []
            for s in seeds:
                ot, of = web(os.path.join(gen, f"{sid}__{arm}__s{s}.jpg"), f"{sid}__{arm}__s{s}.jpg")
                if ot:
                    outs.append(f"<figure class='out'><img src='{ot}' data-full='{of}' "
                                f"alt='{html.escape(sid)} {arm} s{s}' loading='lazy'>"
                                f"<figcaption>seed {s}</figcaption></figure>")
            if not outs:
                continue
            lab, ch = LABEL.get(arm, (arm, ""))
            cols.append(
                f"<div class='arm{' hero' if arm == 'M1c' else ''}'>"
                f"<div class='ah'><b>{lab}</b><span>{html.escape(ch)}</span></div>"
                + (f"<figure class='ref'><img src='{rt}' data-full='{rf}' "
                   f"alt='{html.escape(r['garment'])} {arm} reference' loading='lazy'>"
                   "<figcaption>the reference call 2 was given</figcaption></figure>" if rt else "")
                + f"<div class='outs'>{''.join(outs)}</div></div>")
        cards.append(
            f"<div class='card'><div class='ch'><b>{html.escape(sid)}</b>"
            f"<span class='t'>{'seed-stable failure' if r['seed_stable'] == 'yes' else 'fails at some seeds'}</span>"
            f"<span class='vd'>v3.4 VEi: {verds}</span></div>"
            f"<div class='body'><figure class='person'><img src='{pt}' data-full='{pf}' "
            f"alt='{html.escape(r['person'])} person' loading='lazy'>"
            "<figcaption>the person (image 1)</figcaption></figure>"
            f"<div class='arms'>{''.join(cols)}</div></div></div>")

    o = [HEAD, "<div class='wrap'>", LEDE, f"<div class='grid'>{''.join(cards)}</div>",
         f"<footer>{len(made)} of {len(rows)} failure-set pairs &middot; arms "
         f"{', '.join(arms)} &middot; seeds {', '.join(str(s) for s in seeds)} &middot; "
         f"{meta['calls']} klein calls on <code>{meta['endpoint']}</code>, "
         f"${meta['usd']:.2f} &middot; call 2: {html.escape(meta['canvas'])}; reference "
         f"{html.escape(meta['reference'])} &middot; set: <code>{html.escape(meta['set'])}</code> "
         f"&mdash; {html.escape(meta['set_definition'])} &middot; rebuild: "
         "<code>python3 v3/build/v35_linkB_page.py</code>.</footer></div>", LB, SCRIPT]
    open(os.path.join(REPORT, "v35_linkB.html"), "w").write("\n".join(o))
    print(f"v3/report/v35_linkB.html  ({len(made)} pairs x {len(arms)} arms x {len(seeds)} seeds)")


HEAD = """<title>v3.5 link B - the head-cropped reference through call 2</title>
<meta name='viewport' content='width=device-width,initial-scale=1'>
<style>
:root{--bg:#0d0d10;--fg:#e8e8ea;--dim:#8a8a94;--line:#26262c;--acc:#7c5cff;--mid:#d29922}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
 font:15px/1.6 ui-sans-serif,-apple-system,"Segoe UI",Roboto,sans-serif}
.wrap{max-width:1900px;margin:0 auto;padding:26px 22px 0}
h1{margin:0 0 6px;font-size:25px}
.lede{color:var(--dim);max-width:96ch;font-size:14px;margin:0 0 14px}
.lede b{color:var(--fg)}
.grid{display:grid;grid-template-columns:1fr;gap:14px}
.card{border:1px solid var(--line);border-radius:9px;background:#101014;overflow:hidden}
.ch{display:flex;gap:9px;align-items:center;padding:7px 12px;background:#141419;
 border-bottom:1px solid var(--line);font-size:12px;flex-wrap:wrap}
.ch b{font-size:12.5px;word-break:break-all}
.t{font-size:9.5px;padding:1px 7px;border-radius:20px;background:#2a1a12;
 border:1px solid #6b4423;color:var(--mid)}
.vd{margin-left:auto;display:flex;gap:5px;align-items:center;color:var(--dim);font-size:11px}
.v{font:10.5px ui-monospace,monospace;padding:1px 7px;border-radius:20px;border:1px solid var(--line)}
.v-fail{background:#2d1418;border-color:#8a2b34;color:#ff9aa2}
.v-mid{background:#2a2110;border-color:#6b4423;color:var(--mid)}
.v-clean{background:#12240f;border-color:#2c5c33;color:#7ee787}
.body{display:grid;grid-template-columns:210px 1fr;gap:10px;padding:8px}
@media(max-width:900px){.body{grid-template-columns:1fr}}
.arms{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:10px}
.arm{border:1px solid var(--line);border-radius:8px;background:#0b0b0e;padding:6px}
.arm.hero{border-color:#3b3160;background:#0e0c16}
.ah{display:flex;gap:7px;align-items:baseline;padding:2px 4px 6px;font-size:12px}
.ah span{color:var(--dim);font-size:11px}
.outs{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:4px}
figure{margin:0}
figure img{width:100%;display:block;background:#fff;border-radius:5px;cursor:zoom-in;
 aspect-ratio:3/4;object-fit:contain}
figure.ref img{aspect-ratio:2/3;outline:1px solid var(--line);outline-offset:-1px}
figcaption{font-size:10.5px;color:var(--dim);text-align:center;padding:3px 2px}
.person img{aspect-ratio:2/3}
#lb{display:none;position:fixed;inset:0;background:rgba(0,0,0,.95);z-index:99;
 align-items:center;justify-content:center;flex-direction:column;gap:10px;padding:20px}
#lb.on{display:flex}#lb img{max-width:95vw;max-height:90vh;object-fit:contain;background:#fff}
#lbc{color:var(--dim);font-size:13px}
footer{border-top:1px solid var(--line);margin-top:36px;padding:20px 0 30px;color:var(--dim);font-size:12.5px}
code{background:#1b1b22;padding:1px 5px;border-radius:4px;font-size:12px}
</style>
<div class='wrap'><h1>v3.5 link B &mdash; the head-cropped reference through call 2</h1></div>
"""

LEDE = """<p class='lede'>Every pair here is one the reviewer marked <b>FAIL</b> on the
locked <b>VEi</b> arm in iron man 2 &mdash; the per-seed verdict of record rides along on
each card, so a cell that works is a failure reached, not a fresh sample. Call 2 is the
lock's: prompt <code>E3</code>, fal's own canvas, the reference SR'd to ~1&nbsp;MP first,
exactly as VEi does it. The only variable is <b>which reference call 2 was given</b>, shown
above each output. <b>M1c</b> is the target shape: klein's re-pose, the incumbent's head
removal. Click any image for full size.</p>"""

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
