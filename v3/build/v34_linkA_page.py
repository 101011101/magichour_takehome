"""v3.4 link A page: for every cell of the failure set, the version with and without the
ankle cut (both on fal), beside the A100 v3.3 output the reviewer scored, grouped by class.
  python3 v3/build/v34_linkA_page.py [--embed out.html]
"""
import base64, csv, html, io, os, sys
from PIL import Image
REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
IM = os.path.join(REPO, "v3", "runs", "ironman", "20260830_0548"); OUT = os.path.join(REPO, "v3", "runs", "v34", "linkA")
REPORT = os.path.join(REPO, "v3", "report"); IMG = os.path.join(REPORT, "img_v34a"); EMBED = None
NAMES = {"F1": "wearer's own clothing survives", "F2": "skirt / dress → trousers on the wearer", "F3": "regenerated reference drifts", "F4": "exposed-skin pairing"}

def src(path, w=360):
    if not os.path.exists(path): return None
    im = Image.open(path).convert("RGB"); im.thumbnail((w, 500))
    if EMBED:
        b = io.BytesIO(); im.save(b, "JPEG", quality=72, optimize=True); return "data:image/jpeg;base64," + base64.b64encode(b.getvalue()).decode()
    os.makedirs(IMG, exist_ok=True); o = os.path.join(IMG, os.path.basename(path).replace("__", "_"))
    if not os.path.exists(o): im.save(o, quality=86, optimize=True)
    return "img_v34a/" + os.path.basename(o)

def fig(path, cap, cls=""):
    s = src(path); return (f"<figure class='{cls}'><img src='{s}' alt='{html.escape(cap)}' loading='lazy'><figcaption>{cap}</figcaption></figure>" if s
                           else f"<figure><div class='ph'>missing</div><figcaption>{cap}</figcaption></figure>")

def main(embed=None):
    global EMBED; EMBED = embed
    rows = list(csv.DictReader(open(os.path.join(REPO, "v3", "testsets", "v34_failures.csv"))))
    o = [HEAD, "<div class='wrap'><h1>v3.4 link A &mdash; the ankle cut removed, on the failure set</h1>",
         "<p class='lede'>The 31 pairs where v3.3 had a failing cell on the iron-man run, three seeds. Both arms here are the locked version regenerated on <b>fal</b> "
         "from one reference call per garment: <b>V</b> keeps the ankle cut, <b>Vnc</b> does not; nothing else differs. The last column is the A100 v3.3 output the reviewer "
         "actually scored, for orientation (fal and the A100 are not seed-identical). Red heading = the reviewer's verdict on that cell; a cell is on this page because "
         "at least one seed of its pair failed.</p>"]
    for cls in ("F1", "F2", "F3", "F4"):
        grp = [r for r in rows if r["class"] == cls]
        if not grp: continue
        o.append(f"<h2 class='sec'>{cls} &mdash; {html.escape(NAMES[cls])}<span class='ar'>{len(grp)} pairs</span></h2>")
        for r in grp:
            sid, p, g = r["set_id"], r["person"], r["garment"]
            o.append(f"<h2>{html.escape(p)} wears {html.escape(g)}<span class='ar'>seed-stable: {r['seed_stable']}</span></h2>")
            o.append("<div class='strip s5'>"
                     + fig(os.path.join(IM, "inputs", f"{p}.jpg"), "person") + fig(os.path.join(IM, "inputs", f"{g}.jpg"), "garment photograph")
                     + fig(os.path.join(IM, "inputs", f"{g}__A4.jpg"), "A4 crop")
                     + fig(os.path.join(OUT, "refs", f"{g}__V.jpg"), "reference, cut<span class='n'>V (fal)</span>")
                     + fig(os.path.join(OUT, "refs", f"{g}__Vnc.jpg"), "reference, uncut<span class='n'>Vnc (fal)</span>", "ship") + "</div>")
            for s in ("46", "47", "48"):
                v = r[f"v{s}"]; lab = {"V": "v3.3 better", "BC": "BC klein better", "tie": "tie", "fail": "both fail", "": "not voted"}[v]
                bad = v in ("BC", "fail")
                o.append(f"<div class='lab'>seed {s} &middot; <span class='{'bad' if bad else 'ok'}'>{lab}</span></div><div class='strip s3'>"
                         + fig(os.path.join(OUT, "gen", f"{sid}__V__s{s}.jpg"), "<b>V</b> &mdash; cut (fal)")
                         + fig(os.path.join(OUT, "gen", f"{sid}__Vnc__s{s}.jpg"), "<b>Vnc</b> &mdash; no cut (fal)", "ship")
                         + fig(os.path.join(IM, "gen", f"{sid}__V__s{s}.jpg"), "v3.3 as scored (A100)", "bad" if bad else "") + "</div>")
    o.append(FOOT + "</div>" + LB + SCRIPT)
    dst = embed or os.path.join(REPORT, "v34_linkA.html"); open(dst, "w").write("\n".join(o)); print(dst, f"{os.path.getsize(dst)/1e6:.1f} MB")

HEAD = """<title>Ankle Cut Removed</title><meta name='viewport' content='width=device-width,initial-scale=1'>
<style>:root{--bg:#0d0d10;--fg:#e8e8ea;--dim:#8a8a94;--line:#26262c;--acc:#7c5cff;--good:#3fb950;--bad:#f0655a}*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.6 ui-sans-serif,-apple-system,"Segoe UI",Roboto,sans-serif}.wrap{max-width:1500px;margin:0 auto;padding:30px 26px 0}
h1{margin:0 0 6px;font-size:25px}h2{font-size:14px;margin:34px 0 6px;padding-top:12px;border-top:1px solid var(--line);display:flex;gap:10px;align-items:center;flex-wrap:wrap}
h2.sec{font-size:20px;margin-top:56px;border-top:2px solid var(--acc)}h2 .ar{font-size:12px;color:var(--dim);font-weight:400}
.lede{color:var(--dim);max-width:100ch;font-size:14px;margin:0 0 14px}.lede b{color:var(--fg)}.lab{font-size:12px;color:var(--dim);margin:10px 0 4px}.lab .bad{color:var(--bad);font-weight:700}.lab .ok{color:var(--good)}
.strip{display:grid;gap:5px}.s5{grid-template-columns:repeat(5,minmax(0,1fr));max-width:1100px}.s3{grid-template-columns:repeat(3,minmax(0,1fr));max-width:1100px}
figure{margin:0}figure img{width:100%;display:block;background:#fff;border-radius:6px;cursor:zoom-in;aspect-ratio:3/4;object-fit:contain;border:3px solid transparent}
figure.ship img{border-color:var(--good)}figure.bad img{border-color:#7a3a33}figcaption{font-size:11px;color:var(--dim);text-align:center;padding:5px 2px;line-height:1.4}figcaption .n{display:block;font-size:9.5px;opacity:.85}
.ph{background:#17171d;border:1px dashed var(--line);border-radius:6px;aspect-ratio:3/4;display:flex;align-items:center;justify-content:center;color:var(--dim);font-size:11px}
#lb{display:none;position:fixed;inset:0;background:rgba(0,0,0,.96);z-index:99;align-items:center;justify-content:center;flex-direction:column;gap:10px;padding:16px}#lb.on{display:flex}#lb img{max-width:96vw;max-height:92vh;object-fit:contain;background:#fff}#lbc{color:var(--dim);font-size:13px}
footer{border-top:1px solid var(--line);margin-top:44px;padding:22px 0 30px;color:var(--dim);font-size:12.5px}code{background:#1b1b22;padding:1px 5px;border-radius:4px;font-size:12px}</style>"""
FOOT = """<footer>Run <code>v3/build/run_v34_linkA.py</code> (fal, seeds 46/47/48), outputs <code>v3/runs/v34/linkA/</code>; matrix <code>v3/testsets/v34_failures.csv</code>; rebuild <code>python3 v3/build/v34_linkA_page.py</code>. <code>prd/v3/v3.4/EXPERIMENT.md</code> link A.</footer>"""
LB = "<div id='lb'><img id='lbi' alt=''><div id='lbc'></div></div>"
SCRIPT = """<script>document.addEventListener('click',e=>{const im=e.target.closest('figure img');if(!im)return;document.getElementById('lbi').src=im.getAttribute('src');document.getElementById('lbc').textContent=im.getAttribute('alt');document.getElementById('lb').classList.add('on');});
document.getElementById('lb').addEventListener('click',()=>document.getElementById('lb').classList.remove('on'));document.addEventListener('keydown',e=>{if(e.key==='Escape')document.getElementById('lb').classList.remove('on')});</script>"""
if __name__ == "__main__":
    main(sys.argv[sys.argv.index("--embed") + 1] if "--embed" in sys.argv else None)
