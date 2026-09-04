"""One VA end-to-end, staged: every image the pipeline touches for one pair, in order,
with its size and how it was produced. Demo artifacts from a fal run of the VA recipe
(same model; with pre-scaled inputs fal's canvas rule is a no-op, so the semantics match).
  python3 v3/build/v34_e2e_page.py <demo_dir>   -> v3/report/v34_va_e2e.html
"""
import html, os, shutil, sys
import cv2

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
IM = os.path.join(REPO, "v3", "runs", "ironman", "20260830_0548")
REPORT = os.path.join(REPO, "v3", "report"); IMG = os.path.join(REPORT, "img_v34e2e")


def fig(path, title, how, cls=""):
    im = cv2.imread(path)
    os.makedirs(IMG, exist_ok=True)
    o = os.path.join(IMG, os.path.basename(path))
    if not os.path.exists(o):
        shutil.copy(path, o)
    return (f"<figure class='{cls}'><img src='img_v34e2e/{os.path.basename(o)}' alt='{html.escape(title)}' loading='lazy'>"
            f"<figcaption><b>{title}</b><br>{im.shape[1]}&times;{im.shape[0]} &middot; {im.shape[1]*im.shape[0]/1e6:.2f} MP<br>"
            f"<span class='how'>{how}</span></figcaption></figure>")


def main(demo):
    o = [HEAD, "<div class='wrap'><h1>One VA end to end &mdash; g027 wears p003, seed 49</h1>",
         "<p class='lede'>Arm <b>VA</b> (link F): every input resized to ~1 MP <b>by an algorithm</b> before its klein call; "
         "klein renders at the size of its evidence &mdash; it never upscales, so it never invents detail. "
         "Two klein calls total. This demo ran on fal (same model; with pre-scaled inputs fal's canvas rule is a no-op); "
         "the A100 notebook run is the run of record.</p>",
         "<h2>Call 1 &mdash; the reference</h2><div class='flow'>",
         fig(os.path.join(IM, "inputs", "p003.jpg"), "garment photograph", "input, normalised (algorithmic downscale only)"),
         AR, fig(os.path.join(IM, "inputs", "p003__A4.jpg"), "A4 crop", "BiRefNet matte &rarr; bbox &middot; milliseconds"),
         AR, fig(os.path.join(demo, "1_crop_scaled.jpg"), "crop &rarr; ~1 MP", "<b>Lanczos &mdash; algorithmic</b>, before klein"),
         AR, fig(os.path.join(demo, "2_ref.jpg"), "reference", "klein call 1: head swap + PERSON_CLAUSE + hold &middot; canvas = input size &middot; ~1&ndash;1.6 s A100", "ship"),
         "</div>",
         "<h2>Call 2 &mdash; the edit</h2><div class='flow'>",
         fig(os.path.join(IM, "inputs", "g027.jpg"), "person photograph", "input, normalised"),
         AR, fig(os.path.join(demo, "3_person_scaled.jpg"), "person &rarr; ~1 MP", "<b>Lanczos &mdash; algorithmic</b>, before klein"),
         PL, fig(os.path.join(demo, "2_ref.jpg"), "+ the reference", "already ~1 MP &mdash; enters untouched"),
         AR, fig(os.path.join(demo, "4_output.jpg"), "output", "klein call 2: E3 sentence &middot; canvas = person's size &middot; ~3 s A100", "ship"),
         "</div>",
         "<p class='lede'>What to confirm: the reference carries no invented structure (the dress as-is &mdash; "
         "straps, bodice, pleats), and the output holds the person's waist-up framing with natural proportions "
         "(no dwarfism), the tattoo kept, the dress flowing out of frame.</p>",
         "<footer>Recipe: <code>run_ironman.py</code> arm <code>VA</code> (<code>to_1mp</code>, <code>ALGO_ARMS</code>); "
         "<code>prd/v3/v3.4/EXPERIMENT.md</code> &sect;F. Demo cost: 2 fal calls, $0.03.</footer></div>", LB, SCRIPT]
    dst = os.path.join(REPORT, "v34_va_e2e.html")
    open(dst, "w").write("\n".join(o)); print(dst, f"{os.path.getsize(dst)/1e6:.1f} MB")


AR = "<div class='ar'>&rarr;</div>"
PL = "<div class='ar'>+</div>"
HEAD = """<title>VA End to End</title><meta name='viewport' content='width=device-width,initial-scale=1'>
<style>:root{--bg:#0d0d10;--fg:#e8e8ea;--dim:#8a8a94;--line:#26262c;--acc:#7c5cff}*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.6 ui-sans-serif,-apple-system,"Segoe UI",Roboto,sans-serif}.wrap{max-width:1200px;margin:0 auto;padding:30px 26px}
h1{margin:0 0 6px;font-size:24px}h2{font-size:15px;margin:34px 0 10px;padding-top:12px;border-top:1px solid var(--line)}
.lede{color:var(--dim);max-width:110ch;font-size:14px;margin:0 0 10px}.lede b{color:var(--fg)}
.flow{display:flex;align-items:flex-start;gap:8px;flex-wrap:wrap}
.flow figure{margin:0;flex:1 1 0;min-width:130px;max-width:220px}
.flow .ar{align-self:center;color:var(--acc);font-size:26px;padding:0 2px}
figure img{width:100%;display:block;background:#fff;border-radius:6px;cursor:zoom-in;aspect-ratio:3/4;object-fit:contain;border:3px solid transparent}
figure.ship img{border-color:#2c5c33}
figcaption{font-size:11px;color:var(--dim);text-align:center;padding:6px 2px}figcaption b{color:var(--fg)}.how{color:#a89ce8}
footer{margin:36px 0 20px;font-size:12px;color:var(--dim)}
#lb{position:fixed;inset:0;background:#000d;display:none;align-items:center;justify-content:center;z-index:9}#lb.on{display:flex}#lb img{max-width:96vw;max-height:92vh}#lbc{position:fixed;bottom:8px;color:#fff;font-size:13px}</style>"""
LB = "<div id='lb'><img id='lbi' alt=''><div id='lbc'></div></div>"
SCRIPT = """<script>document.addEventListener('click',e=>{const im=e.target.closest('figure img');if(!im)return;document.getElementById('lbi').src=im.getAttribute('src');document.getElementById('lbc').textContent=im.getAttribute('alt');document.getElementById('lb').classList.add('on');});
document.getElementById('lb').addEventListener('click',()=>document.getElementById('lb').classList.remove('on'));document.addEventListener('keydown',e=>{if(e.key==='Escape')document.getElementById('lb').classList.remove('on')});</script>"""

if __name__ == "__main__":
    main(sys.argv[1])
