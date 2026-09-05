"""SR probe page: (1) what a lightweight super-resolution model (realesr-general-x4v3,
1.2M params, CPU) does to the small inputs, beside Lanczos; (2) the VS recipe (SR inputs
-> klein) run on fal for the dwarfism pair and the placket reference.
  python3 v3/build/v34_sr_page.py <sr_probe_dir>   -> v3/report/v34_sr_probe.html
"""
import html, os, shutil, sys
import cv2

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
IM = os.path.join(REPO, "v3", "runs", "ironman", "20260830_0548", "inputs")
REPORT = os.path.join(REPO, "v3", "report"); IMG = os.path.join(REPORT, "img_v34sr")
NAMES = ["p003__A4", "p004__A4", "p016__A4", "p002__A4", "g024__A4", "g005__A4", "g013__A4", "g015__A4", "g027", "p014__A4"]


def fig(path, title, how="", cls=""):
    os.makedirs(IMG, exist_ok=True)
    o = os.path.join(IMG, title.replace(" ", "_").replace("&", "")[:40] + "_" + os.path.basename(path))
    if not os.path.exists(o):
        shutil.copy(path, o)
    im = cv2.imread(path); h, w = im.shape[:2]
    return (f"<figure class='{cls}'><img src='img_v34sr/{os.path.basename(o)}' alt='{html.escape(title)}' loading='lazy'>"
            f"<figcaption><b>{title}</b><br>{w}&times;{h} &middot; {w*h/1e6:.2f} MP" + (f"<br><span class='how'>{how}</span>" if how else "") + "</figcaption></figure>")


def main(sp):
    o = [HEAD, "<div class='wrap'><h1>The SR probe &mdash; sharp algorithmic upscaling, seen</h1>",
         "<p class='lede'><b>realesr-general-x4v3</b>: 1.2M parameters, 4.9 MB, 1.5&ndash;11.5 s per image on this CPU "
         "(tens of ms on the A100 &mdash; &lt;2% of a pair). Per row: the input as-is &middot; <b>Lanczos</b> to ~1 MP "
         "(VA's scaler &mdash; soft) &middot; <b>SR</b> to ~1 MP (&times;4 then area-down). Click to zoom &mdash; the "
         "difference is in fabric texture, print edges, seam lines.</p>"]
    for n in NAMES:
        o.append(f"<h2>{html.escape(n)}</h2><div class='strip'>"
                 + fig(os.path.join(IM, f"{n}.jpg"), "input, native")
                 + fig(os.path.join(sp, f"{n}__lz.jpg"), "Lanczos &rarr; 1 MP", "interpolation &mdash; no information added")
                 + fig(os.path.join(sp, f"{n}__sr.jpg"), "SR &rarr; 1 MP", "learned texture prior &mdash; sharp, structure-conservative", "ship")
                 + "</div>")
    o.append("<h1 style='margin-top:50px'>The VS recipe on fal &mdash; SR inputs &rarr; klein, seed 49</h1>"
             "<p class='lede'>One end to end on the dwarfism pair, plus the placket reference. fal draw &mdash; "
             "orientation only; the A100 run decides (link E showed fal and A100 draws can disagree on this pair).</p>"
             "<h2>g027 + p003 &mdash; three input treatments, same backend, same seed</h2><div class='strip'>"
             + fig(os.path.join(sp, "ve_out_g027_p003_fal.jpg"), "native inputs &mdash; klein scales (VE)", "framing held &middot; faint print bleed in the bodice", "ship")
             + fig(os.path.join(os.path.dirname(sp), "va_demo", "4_output.jpg"), "Lanczos inputs (VA)", "framing held on this fal draw &mdash; the A100 lost it 3/3", "ship")
             + fig(os.path.join(sp, "vs_out_g027_p003.jpg"), "SR inputs (VS)", "framing held &middot; cleanest bodice", "ship")
             + "</div><h2>p004 &mdash; the placket check</h2><div class='strip'>"
             + fig(os.path.join(IM, "p004__A4.jpg"), "A4 crop &mdash; NO buttons")
             + fig(os.path.join(sp, "vs_ref_p004.jpg"), "reference (SR-conditioned)", "placket STILL invented &mdash; call-1 regeneration, not scaling", "bad")
             + "</div>"
             "<footer>Model: realesr-general-x4v3 (Real-ESRGAN release v0.2.5.0). 3 fal calls, $0.045. "
             "<code>prd/v3/v3.4/EXPERIMENT.md</code> &sect;F.</footer></div>" + LB + SCRIPT)
    dst = os.path.join(REPORT, "v34_sr_probe.html")
    open(dst, "w").write("\n".join(o)); print(dst, f"{os.path.getsize(dst)/1e6:.1f} MB")


HEAD = """<title>SR Probe</title><meta name='viewport' content='width=device-width,initial-scale=1'>
<style>:root{--bg:#0d0d10;--fg:#e8e8ea;--dim:#8a8a94;--line:#26262c;--acc:#7c5cff}*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.6 ui-sans-serif,-apple-system,"Segoe UI",Roboto,sans-serif}.wrap{max-width:1100px;margin:0 auto;padding:30px 26px}
h1{margin:0 0 6px;font-size:23px}h2{font-size:14px;margin:32px 0 6px;padding-top:12px;border-top:1px solid var(--line)}
.lede{color:var(--dim);max-width:110ch;font-size:14px;margin:0 0 12px}.lede b{color:var(--fg)}
.strip{display:grid;gap:6px;grid-template-columns:repeat(3,minmax(0,1fr));max-width:960px}
figure{margin:0}figure img{width:100%;display:block;background:#fff;border-radius:6px;cursor:zoom-in;aspect-ratio:3/4;object-fit:contain;border:3px solid transparent}
figure.ship img{border-color:#2c5c33}figure.bad img{border-color:#7a3a33}
figcaption{font-size:11px;color:var(--dim);text-align:center;padding:5px 2px}figcaption b{color:var(--fg)}.how{color:#a89ce8}
footer{margin:36px 0 20px;font-size:12px;color:var(--dim)}
#lb{position:fixed;inset:0;background:#000d;display:none;align-items:center;justify-content:center;z-index:9}#lb.on{display:flex}#lb img{max-width:96vw;max-height:92vh}#lbc{position:fixed;bottom:8px;color:#fff;font-size:13px}</style>"""
LB = "<div id='lb'><img id='lbi' alt=''><div id='lbc'></div></div>"
SCRIPT = """<script>document.addEventListener('click',e=>{const im=e.target.closest('figure img');if(!im)return;document.getElementById('lbi').src=im.getAttribute('src');document.getElementById('lbc').textContent=im.getAttribute('alt');document.getElementById('lb').classList.add('on');});
document.getElementById('lb').addEventListener('click',()=>document.getElementById('lb').classList.remove('on'));document.addEventListener('keydown',e=>{if(e.key==='Escape')document.getElementById('lb').classList.remove('on')});</script>"""

if __name__ == "__main__":
    main(sys.argv[1])
