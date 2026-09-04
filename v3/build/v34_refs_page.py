"""Reference upscale, seen: per garment of the failure set, the A4 crop (call 1's input)
beside the V34 reference (v3.3 canvas, never upscaled) and the VE reference (fal canvas,
generated at ~1 MP). Same prompt, same seed 49 - the canvas is the only difference.
  python3 v3/build/v34_refs_page.py   -> v3/report/v34_refs_upscale.html
"""
import csv, html, os
import cv2
from PIL import Image

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
IM = os.path.join(REPO, "v3", "runs", "ironman", "20260830_0548")
LD = os.path.join(REPO, "v3", "runs", "v34", "v34_a100_v34_20260904_0458")
VE = os.path.join(REPO, "v3", "runs", "v34", "v34_a100_ve_20260904_0611")
REPORT = os.path.join(REPO, "v3", "report"); IMG = os.path.join(REPORT, "img_v34refs")


def fig(path, cap):
    if not os.path.exists(path):
        return f"<figure><div class='ph'>&mdash;</div><figcaption>{cap}</figcaption></figure>"
    im = cv2.imread(path); mp = im.shape[1] * im.shape[0] / 1e6
    t = Image.open(path).convert("RGB"); t.thumbnail((360, 480))
    os.makedirs(IMG, exist_ok=True)
    o = os.path.join(IMG, os.path.basename(os.path.dirname(os.path.dirname(path)) or "x")[:6] + "_" + os.path.basename(path))
    if not os.path.exists(o):
        t.save(o, quality=85, optimize=True)
    return (f"<figure><img src='img_v34refs/{os.path.basename(o)}' alt='{html.escape(cap)}' loading='lazy'>"
            f"<figcaption>{cap}<br><b>{im.shape[1]}&times;{im.shape[0]}</b> &middot; {mp:.2f} MP</figcaption></figure>")


def main():
    rows = list(csv.DictReader(open(os.path.join(REPO, "v3", "testsets", "v34_failures.csv"))))
    garments = sorted({r["garment"] for r in rows})
    o = [HEAD, "<div class='wrap'><h1>The reference upscale, seen</h1>",
         "<p class='lede'>Per garment: the <b>A4 crop</b> (call 1's input) &middot; the <b>V34 reference</b> "
         "(v3.3 canvas &mdash; render at the crop's size, never upscaled) &middot; the <b>VE reference</b> "
         "(fal canvas &mdash; rendered at area 1024&sup2;, up or down). Same prompt, same seed 49; the render "
         "canvas is the only difference. The upscale is not interpolation: call 1 <i>generates</i> at the "
         "larger canvas (<code>klein_local._size_fal</code>, chosen per call in <code>run_ironman.klein()</code>), "
         "so the added detail is synthesized, not stretched.</p>"]
    for g in garments:
        o.append(f"<h2>{html.escape(g)}</h2><div class='strip'>"
                 + fig(os.path.join(IM, "inputs", f"{g}__A4.jpg"), "A4 crop &mdash; call 1 input")
                 + fig(os.path.join(LD, "refs", f"{g}__V34.jpg"), "V34 ref &mdash; not upscaled")
                 + fig(os.path.join(VE, "refs", f"{g}__VE.jpg"), "VE ref &mdash; generated at ~1 MP")
                 + "</div>")
    o.append("<footer>Runs: link D <code>v34_a100_v34_20260904_0458</code>, link E <code>v34_a100_ve_20260904_0611</code>. "
             "<code>prd/v3/v3.4/RESULTS.md</code> &sect;6&ndash;7.</footer></div>" + LB + SCRIPT)
    dst = os.path.join(REPORT, "v34_refs_upscale.html")
    open(dst, "w").write("\n".join(o)); print(dst, f"{os.path.getsize(dst) / 1e6:.1f} MB")


HEAD = """<title>Reference Upscale, Seen</title><meta name='viewport' content='width=device-width,initial-scale=1'>
<style>:root{--bg:#0d0d10;--fg:#e8e8ea;--dim:#8a8a94;--line:#26262c;--acc:#7c5cff}*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.6 ui-sans-serif,-apple-system,"Segoe UI",Roboto,sans-serif}.wrap{max-width:1100px;margin:0 auto;padding:30px 26px}
h1{margin:0 0 6px;font-size:25px}h2{font-size:14px;margin:36px 0 6px;padding-top:12px;border-top:1px solid var(--line)}
.lede{color:var(--dim);max-width:100ch;font-size:14px;margin:0 0 14px}.lede b,.lede i{color:var(--fg)}
.strip{display:grid;gap:6px;grid-template-columns:repeat(3,minmax(0,1fr));max-width:1000px}
figure{margin:0}figure img{width:100%;display:block;background:#fff;border-radius:6px;cursor:zoom-in;aspect-ratio:3/4;object-fit:contain}
figcaption{font-size:11px;color:var(--dim);text-align:center;padding:5px 2px}figcaption b{color:var(--fg)}
.ph{background:#17171d;border:1px dashed var(--line);border-radius:6px;aspect-ratio:3/4;display:flex;align-items:center;justify-content:center;color:var(--dim)}
footer{margin:40px 0 20px;font-size:12px;color:var(--dim)}
#lb{position:fixed;inset:0;background:#000d;display:none;align-items:center;justify-content:center;z-index:9}#lb.on{display:flex}#lb img{max-width:96vw;max-height:92vh}#lbc{position:fixed;bottom:8px;color:#fff;font-size:13px}</style>"""
LB = "<div id='lb'><img id='lbi' alt=''><div id='lbc'></div></div>"
SCRIPT = """<script>document.addEventListener('click',e=>{const im=e.target.closest('figure img');if(!im)return;document.getElementById('lbi').src=im.getAttribute('src');document.getElementById('lbc').textContent=im.getAttribute('alt');document.getElementById('lb').classList.add('on');});
document.getElementById('lb').addEventListener('click',()=>document.getElementById('lb').classList.remove('on'));document.addEventListener('keydown',e=>{if(e.key==='Escape')document.getElementById('lb').classList.remove('on')});</script>"""

if __name__ == "__main__":
    main()
