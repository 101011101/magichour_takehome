"""The marked failures, three ways: every link-D cell the reviewer marked non-pass, shown
as [V34 - the marked failure] · [VE, same seed] · [VS - SR inputs, fal draw], with the
pair's person / garment / VS reference above.
  python3 v3/build/v34_vs_failed_page.py   -> v3/report/v34_vs_failed.html
"""
import csv, html, os
import cv2
from PIL import Image

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
IM = os.path.join(REPO, "v3", "runs", "ironman", "20260830_0548")
LD = os.path.join(REPO, "v3", "runs", "v34", "v34_a100_v34_20260904_0458")
LE = os.path.join(REPO, "v3", "runs", "v34", "v34_a100_ve_20260904_0611")
VS = os.path.join(REPO, "v3", "runs", "v34", "vs_fal")
REPORT = os.path.join(REPO, "v3", "report"); IMG = os.path.join(REPORT, "img_v34vsf")
MARK = {"worse": "marked WORSE than fal", "fail_better": "marked FAIL (but &ge;fal)"}


def fig(path, cap, cls=""):
    if not os.path.exists(path):
        return f"<figure><div class='ph'>&mdash;</div><figcaption>{cap}</figcaption></figure>"
    im = Image.open(path).convert("RGB"); im.thumbnail((340, 460)); os.makedirs(IMG, exist_ok=True)
    o = os.path.join(IMG, os.path.basename(os.path.dirname(os.path.dirname(path)))[:6] + "_" + os.path.basename(path))
    if not os.path.exists(o):
        im.save(o, quality=85, optimize=True)
    return f"<figure class='{cls}'><img src='img_v34vsf/{os.path.basename(o)}' alt='{html.escape(cap)}' loading='lazy'><figcaption>{cap}</figcaption></figure>"


def main():
    marks = [r for r in csv.DictReader(open(os.path.join(REPO, "v34_linkD_marks.csv"))) if r["verdict"] != "pass"]
    rows = {r["set_id"]: r for r in csv.DictReader(open(os.path.join(REPO, "v3", "testsets", "v34_failures.csv")))}
    by = {}
    for m in marks:
        by.setdefault(m["set_id"], []).append(m)
    o = [HEAD, "<div class='wrap'><h1>The marked failures, three ways</h1>",
         "<p class='lede'>Every link-D cell marked non-pass, at its failing seed: <b>V34</b> (the A100 cell that was "
         "marked) &middot; <b>VE</b> (klein-scaled reference, A100, same seed) &middot; <b>VS</b> (SR-scaled inputs, "
         "<i>fal draw</i> &mdash; orientation, not record; fal and A100 draws can disagree). "
         "Context row per pair: person &middot; garment &middot; the VS reference.</p>"]
    for sid, ms in by.items():
        r = rows[sid]; p, g = r["person"], r["garment"]
        o.append(f"<h2>{html.escape(p)} wears {html.escape(g)}<span class='ar'>{html.escape(r.get('class', ''))}</span></h2>")
        o.append("<div class='strip'>" + fig(os.path.join(IM, "inputs", f"{p}.jpg"), "person")
                 + fig(os.path.join(IM, "inputs", f"{g}.jpg"), "garment photograph")
                 + fig(os.path.join(VS, "refs", f"{g}__VS.jpg"), "VS reference (SR-conditioned)") + "</div>")
        for m in ms:
            s = m["seed"]
            o.append(f"<div class='lab'>seed {s} &middot; {MARK[m['verdict']]}</div><div class='strip'>"
                     + fig(os.path.join(LD, "gen", f"{sid}__V34__s{s}.jpg"), f"V34 s{s} &mdash; the marked cell", "bad" if m["verdict"] == "worse" else "warn")
                     + fig(os.path.join(LE, "gen", f"{sid}__VE__s{s}.jpg"), f"VE s{s} (A100)")
                     + fig(os.path.join(VS, "gen", f"{sid}__VS__s{s}.jpg"), f"VS s{s} &mdash; SR inputs (fal)", "ship") + "</div>")
    o.append("<footer>VS run: <code>v3/build/run_v34_vs_fal.py</code> &rarr; <code>v3/runs/v34/vs_fal/</code>; "
             "SR = realesr-general-x4v3. Marks: <code>v34_linkD_marks.csv</code>. "
             "<code>prd/v3/v3.4/EXPERIMENT.md</code> &sect;F.</footer></div>" + LB + SCRIPT)
    dst = os.path.join(REPORT, "v34_vs_failed.html")
    open(dst, "w").write("\n".join(o)); print(dst, f"{os.path.getsize(dst)/1e6:.1f} MB")


HEAD = """<title>Marked Failures, Three Ways</title><meta name='viewport' content='width=device-width,initial-scale=1'>
<style>:root{--bg:#0d0d10;--fg:#e8e8ea;--dim:#8a8a94;--line:#26262c;--acc:#7c5cff}*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.6 ui-sans-serif,-apple-system,"Segoe UI",Roboto,sans-serif}.wrap{max-width:1050px;margin:0 auto;padding:30px 26px}
h1{margin:0 0 6px;font-size:24px}h2{font-size:14px;margin:40px 0 6px;padding-top:12px;border-top:1px solid var(--line)}h2 .ar{font-size:12px;color:var(--dim);font-weight:400;margin-left:10px}
.lede{color:var(--dim);max-width:110ch;font-size:14px;margin:0 0 12px}.lede b,.lede i{color:var(--fg)}
.lab{font-size:12px;color:var(--dim);margin:10px 0 4px}
.strip{display:grid;gap:6px;grid-template-columns:repeat(3,minmax(0,1fr));max-width:920px}
figure{margin:0}figure img{width:100%;display:block;background:#fff;border-radius:6px;cursor:zoom-in;aspect-ratio:3/4;object-fit:contain;border:3px solid transparent}
figure.ship img{border-color:#2c5c33}figure.bad img{border-color:#b43c3c}figure.warn img{border-color:#c9862c}
figcaption{font-size:11px;color:var(--dim);text-align:center;padding:5px 2px}
.ph{background:#17171d;border:1px dashed var(--line);border-radius:6px;aspect-ratio:3/4;display:flex;align-items:center;justify-content:center;color:var(--dim)}
footer{margin:40px 0 20px;font-size:12px;color:var(--dim)}
#lb{position:fixed;inset:0;background:#000d;display:none;align-items:center;justify-content:center;z-index:9}#lb.on{display:flex}#lb img{max-width:96vw;max-height:92vh}#lbc{position:fixed;bottom:8px;color:#fff;font-size:13px}</style>"""
LB = "<div id='lb'><img id='lbi' alt=''><div id='lbc'></div></div>"
SCRIPT = """<script>document.addEventListener('click',e=>{const im=e.target.closest('figure img');if(!im)return;document.getElementById('lbi').src=im.getAttribute('src');document.getElementById('lbc').textContent=im.getAttribute('alt');document.getElementById('lb').classList.add('on');});
document.getElementById('lb').addEventListener('click',()=>document.getElementById('lb').classList.remove('on'));document.addEventListener('keydown',e=>{if(e.key==='Escape')document.getElementById('lb').classList.remove('on')});</script>"""

if __name__ == "__main__":
    main()
