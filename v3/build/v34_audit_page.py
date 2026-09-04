"""Intermediate audit for one pair: per arm (V34 / VE / VA), every image as klein saw it
- call 1 input, reference, call 2 person input, output s49 - with exact pixel counts and
the render canvas. Answers "is everything 1 MP / is anything scaled twice".
  python3 v3/build/v34_audit_page.py   -> v3/report/v34_audit_g027.html
"""
import html, os, sys
import cv2

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "v3", "colab", "lib"))
from run_ironman import to_1mp                     # noqa: E402
from klein_local import _size, _size_fal           # noqa: E402

IM = os.path.join(REPO, "v3", "runs", "ironman", "20260830_0548")
RUNS = {"V34": "v34_a100_v34_20260904_0458", "VE": "v34_a100_ve_20260904_0611", "VA": "v34_a100_va_20260904_0728"}
DESC = {"V34": "everything native; klein upscales the canvas on call 2 only",
        "VE": "inputs native and sharp; klein renders BOTH calls at ~1 MP (klein does the upscaling)",
        "VA": "inputs Lanczos-scaled to ~1 MP first (soft); klein renders at the input's size"}
REPORT = os.path.join(REPO, "v3", "report"); IMG = os.path.join(REPORT, "img_v34audit")
CAP = 1_048_576


def fig(im, name, title, how, cls=""):
    os.makedirs(IMG, exist_ok=True)
    p = os.path.join(IMG, name)
    if not os.path.exists(p):
        cv2.imwrite(p, im, [cv2.IMWRITE_JPEG_QUALITY, 92])
    h, w = im.shape[:2]
    return (f"<figure class='{cls}'><img src='img_v34audit/{name}' alt='{html.escape(title)}' loading='lazy'>"
            f"<figcaption><b>{title}</b><br>{w}&times;{h} &middot; {w*h:,} px &middot; {'&le;2&sup2;&#8304; ok' if w*h <= CAP else 'OVER CAP'}<br>"
            f"<span class='how'>{how}</span></figcaption></figure>")


def main():
    crop = cv2.imread(os.path.join(IM, "inputs", "p003__A4.jpg"))
    person = cv2.imread(os.path.join(IM, "inputs", "g027.jpg"))
    o = [HEAD, "<div class='wrap'><h1>g027 + p003, audited &mdash; every image as klein saw it</h1>",
         "<p class='lede'>Seed 49 throughout. The 1 MP cap is 2&sup2;&#8304; = 1,048,576 px; nothing here is scaled twice "
         "&mdash; the pipeline re-resizes only inputs <i>over</i> the cap, and none are. <b>VE and VA give klein the "
         "same canvases</b>; they differ only in whether the input pixels are native-sharp (VE, klein invents the "
         "extra resolution) or Lanczos-soft (VA, the algorithm made the pixels). V34 is the small-reference baseline.</p>"]
    for arm, rd in RUNS.items():
        run = os.path.join(REPO, "v3", "runs", "v34", rd)
        c1in = to_1mp(crop) if arm == "VA" else crop
        ch, cw = (_size_fal if arm in ("VE", "VA") else _size)(c1in)
        ref = cv2.imread(os.path.join(run, "refs", f"p003__{arm}.jpg"))
        c2in = to_1mp(person) if arm == "VA" else person
        eh, ew = _size_fal(c2in)
        out = cv2.imread(os.path.join(run, "gen", f"g027+p003__{arm}__s49.jpg"))
        o.append(f"<h2>{arm} <span class='ar'>{DESC[arm]}</span></h2><div class='flow'>"
                 + fig(c1in, f"{arm}_c1in.jpg", "call 1 input (crop)", "as fed" + (" &middot; Lanczos &times;2.0" if arm == "VA" else " &middot; native"))
                 + f"<div class='arw'>&rarr;<span>canvas<br>{cw}&times;{ch}</span></div>"
                 + fig(ref, f"{arm}_ref.jpg", "reference", "klein call 1 output, recropped")
                 + f"<div class='arw'>+</div>"
                 + fig(c2in, f"{arm}_c2in.jpg", "call 2 input (person)", "as fed" + (" &middot; Lanczos &times;1.3" if arm == "VA" else " &middot; native"))
                 + f"<div class='arw'>&rarr;<span>canvas<br>{ew}&times;{eh}</span></div>"
                 + fig(out, f"{arm}_out.jpg", "output s49", {"V34": "dwarfism", "VE": "framing HELD", "VA": "dwarfism back"}[arm],
                       "ship" if arm == "VE" else "bad")
                 + "</div>")
    o.append("<p class='lede'><b>Reading.</b> Same canvases, three different fates. The only variable that tracks the "
             "outcome is the <i>sharpness of the person evidence</i>: VE's native 0.60 MP person anchors the framing; "
             "VA's softened 1.05 MP person does not; V34's small 0.24 MP reference loses it too. "
             "And VA's p004 reference still invents the placket &mdash; the hallucination comes from call 1's "
             "regeneration, not from who scales the pixels.</p>"
             "<footer><code>prd/v3/v3.4/EXPERIMENT.md</code> &sect;F &middot; numeric audit in the session log.</footer></div>" + LB + SCRIPT)
    dst = os.path.join(REPORT, "v34_audit_g027.html")
    open(dst, "w").write("\n".join(o)); print(dst, f"{os.path.getsize(dst)/1e6:.1f} MB")


HEAD = """<title>g027 Audit</title><meta name='viewport' content='width=device-width,initial-scale=1'>
<style>:root{--bg:#0d0d10;--fg:#e8e8ea;--dim:#8a8a94;--line:#26262c;--acc:#7c5cff}*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.6 ui-sans-serif,-apple-system,"Segoe UI",Roboto,sans-serif}.wrap{max-width:1250px;margin:0 auto;padding:30px 26px}
h1{margin:0 0 6px;font-size:23px}h2{font-size:16px;margin:34px 0 8px;padding-top:12px;border-top:1px solid var(--line)}h2 .ar{font-size:12px;color:var(--dim);font-weight:400;margin-left:10px}
.lede{color:var(--dim);max-width:115ch;font-size:14px;margin:0 0 10px}.lede b,.lede i{color:var(--fg)}
.flow{display:flex;align-items:flex-start;gap:6px;flex-wrap:wrap}
.flow figure{margin:0;flex:1 1 0;min-width:120px;max-width:210px}
.flow .arw{align-self:center;color:var(--acc);font-size:22px;padding:0 2px;text-align:center}.arw span{display:block;font-size:10px;color:var(--dim)}
figure img{width:100%;display:block;background:#fff;border-radius:6px;cursor:zoom-in;aspect-ratio:3/4;object-fit:contain;border:3px solid transparent}
figure.ship img{border-color:#2c5c33}figure.bad img{border-color:#7a3a33}
figcaption{font-size:11px;color:var(--dim);text-align:center;padding:5px 2px}figcaption b{color:var(--fg)}.how{color:#a89ce8}
footer{margin:36px 0 20px;font-size:12px;color:var(--dim)}
#lb{position:fixed;inset:0;background:#000d;display:none;align-items:center;justify-content:center;z-index:9}#lb.on{display:flex}#lb img{max-width:96vw;max-height:92vh}#lbc{position:fixed;bottom:8px;color:#fff;font-size:13px}</style>"""
LB = "<div id='lb'><img id='lbi' alt=''><div id='lbc'></div></div>"
SCRIPT = """<script>document.addEventListener('click',e=>{const im=e.target.closest('figure img');if(!im)return;document.getElementById('lbi').src=im.getAttribute('src');document.getElementById('lbc').textContent=im.getAttribute('alt');document.getElementById('lb').classList.add('on');});
document.getElementById('lb').addEventListener('click',()=>document.getElementById('lb').classList.remove('on'));document.addEventListener('keydown',e=>{if(e.key==='Escape')document.getElementById('lb').classList.remove('on')});</script>"""

if __name__ == "__main__":
    main()
