"""v3.4 link B: fal Vnc on 30 clean controls beside the A100 v3.3 output. Mark any fal cell
as a fail (default pass); export CSV. python3 v3/build/v34_controls_page.py [--embed out]"""
import base64, csv, html, io, os, sys
from PIL import Image
REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
IM = os.path.join(REPO, "v3", "runs", "ironman", "20260830_0548"); OUT = os.path.join(REPO, "v3", "runs", "v34", "linkB_controls")
REPORT = os.path.join(REPO, "v3", "report"); IMG = os.path.join(REPORT, "img_v34b"); EMBED = None
def src(path, w=340):
    if not os.path.exists(path): return None
    im = Image.open(path).convert("RGB"); im.thumbnail((w, 480))
    if EMBED:
        b = io.BytesIO(); im.save(b, "JPEG", quality=72, optimize=True); return "data:image/jpeg;base64," + base64.b64encode(b.getvalue()).decode()
    os.makedirs(IMG, exist_ok=True); o = os.path.join(IMG, os.path.basename(path).replace("__", "_"))
    if not os.path.exists(o): im.save(o, quality=86, optimize=True)
    return "img_v34b/" + os.path.basename(o)
def fig(path, cap, cls=""):
    s = src(path); return f"<figure class='{cls}'><img src='{s}' alt='{html.escape(cap)}' loading='lazy'><figcaption>{cap}</figcaption></figure>" if s else f"<figure><div class='ph'>missing</div><figcaption>{cap}</figcaption></figure>"
def main(embed=None):
    global EMBED; EMBED = embed
    rows = list(csv.DictReader(open(os.path.join(REPO, "v3", "testsets", "v34_controls.csv"))))
    o = [HEAD, "<div class='wrap'>", BAR, "<h1>v3.4 link B &mdash; fal on 30 clean controls</h1>",
         "<p class='lede'>30 pairs on which v3.3 had no failing cell at any seed on the A100. The same version, <b>no ankle cut</b>, regenerated on fal at seeds 46/47/48, beside the A100 output the reviewer scored. "
         "If fal is genuinely more consistent, it should not fail these; if it is just a fresh draw, it will fail a few at the fold's ~4% rate. Mark any fal cell that is a failure (extra limbs, leaked clothing, wrong garment); default is pass.</p>"]
    for r in rows:
        sid, p, g = r["set_id"], r["person"], r["garment"]
        o.append(f"<h2>{html.escape(p)} wears {html.escape(g)}<span class='ar'>A100 verdicts: {r['v46']} / {r['v47']} / {r['v48']}</span></h2>")
        o.append("<div class='strip s3'>" + fig(os.path.join(IM, "inputs", f"{p}.jpg"), "person") + fig(os.path.join(IM, "inputs", f"{g}.jpg"), "garment photograph")
                 + fig(os.path.join(OUT, "refs", f"{g}__Vnc.jpg"), "reference, uncut (fal)") + "</div>")
        for s in ("46", "47", "48"):
            o.append(f"<div class='lab'>seed {s}<span class='mk' data-sid='{html.escape(sid)}' data-seed='{s}'><button data-m='pass' class='on'>fal pass</button><button data-m='fail'>fal FAIL</button></span></div><div class='strip s2'>"
                     + fig(os.path.join(OUT, "gen", f"{sid}__Vnc__s{s}.jpg"), "<b>fal</b> &mdash; no cut", "ship") + fig(os.path.join(IM, "gen", f"{sid}__V__s{s}.jpg"), "A100 v3.3 as scored") + "</div>")
    o.append(FOOT + "</div>" + LB + SCRIPT)
    dst = embed or os.path.join(REPORT, "v34_controls.html"); open(dst, "w").write("\n".join(o)); print(dst, f"{os.path.getsize(dst)/1e6:.1f} MB")
BAR = """<div class='bar'><button id='export'>Export CSV</button><span id='count'></span></div><textarea id='csvbox'></textarea>"""
HEAD = """<title>Fal on the Controls</title><meta name='viewport' content='width=device-width,initial-scale=1'>
<style>:root{--bg:#0d0d10;--fg:#e8e8ea;--dim:#8a8a94;--line:#26262c;--acc:#7c5cff;--good:#3fb950;--bad:#f0655a}*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.6 ui-sans-serif,-apple-system,"Segoe UI",Roboto,sans-serif}.wrap{max-width:1300px;margin:0 auto;padding:30px 26px 0}
h1{margin:0 0 6px;font-size:25px}h2{font-size:14px;margin:40px 0 6px;padding-top:12px;border-top:1px solid var(--line);display:flex;gap:10px;align-items:center;flex-wrap:wrap}h2 .ar{font-size:12px;color:var(--dim);font-weight:400}
.lede{color:var(--dim);max-width:100ch;font-size:14px;margin:0 0 14px}.lede b{color:var(--fg)}.lab{font-size:12px;color:var(--dim);margin:10px 0 4px;display:flex;gap:10px;align-items:center}
.strip{display:grid;gap:5px}.s3{grid-template-columns:repeat(3,minmax(0,1fr));max-width:800px}.s2{grid-template-columns:repeat(2,minmax(0,1fr));max-width:800px}
figure{margin:0}figure img{width:100%;display:block;background:#fff;border-radius:6px;cursor:zoom-in;aspect-ratio:3/4;object-fit:contain;border:3px solid transparent}figure.ship img{border-color:#2c5c33}figure.failed img{border-color:#b43c3c}
figcaption{font-size:11px;color:var(--dim);text-align:center;padding:5px 2px}.ph{background:#17171d;border:1px dashed var(--line);border-radius:6px;aspect-ratio:3/4;display:flex;align-items:center;justify-content:center;color:var(--dim);font-size:11px}
.bar{position:sticky;top:0;background:var(--bg);padding:8px 0;z-index:5;border-bottom:1px solid var(--line);display:flex;gap:10px;align-items:center}.bar button{background:#17171d;color:var(--fg);border:1px solid var(--acc);border-radius:5px;padding:5px 12px;cursor:pointer}
#count{color:var(--dim);font-size:12px}#csvbox{width:100%;height:50px;margin:6px 0 0;background:#17171d;color:var(--dim);border:1px solid var(--line);font:11px ui-monospace,monospace;display:none}
.mk button{background:#17171d;color:var(--fg);border:1px solid var(--line);border-radius:5px;padding:3px 9px;font-size:11px;cursor:pointer;margin-left:4px}.mk button.on{background:#3a3a55;border-color:#8a8ad0}.mk button[data-m='fail'].on{background:#4d1f1f;border-color:#b43c3c}
#lb{display:none;position:fixed;inset:0;background:rgba(0,0,0,.96);z-index:99;align-items:center;justify-content:center;flex-direction:column;gap:10px;padding:16px}#lb.on{display:flex}#lb img{max-width:96vw;max-height:92vh;object-fit:contain;background:#fff}#lbc{color:var(--dim);font-size:13px}
footer{border-top:1px solid var(--line);margin-top:44px;padding:22px 0 30px;color:var(--dim);font-size:12.5px}code{background:#1b1b22;padding:1px 5px;border-radius:4px;font-size:12px}</style>"""
FOOT = """<footer>Run <code>v3/build/run_v34_linkA.py --matrix v34_controls.csv --arms Vnc</code> (fal), outputs <code>v3/runs/v34/linkB_controls/</code>; matrix <code>v3/testsets/v34_controls.csv</code>. <code>prd/v3/v3.4/EXPERIMENT.md</code> link B.</footer>"""
LB = "<div id='lb'><img id='lbi' alt=''><div id='lbc'></div></div>"
SCRIPT = """<script>document.addEventListener('click',e=>{const im=e.target.closest('figure img');if(!im)return;document.getElementById('lbi').src=im.getAttribute('src');document.getElementById('lbc').textContent=im.getAttribute('alt');document.getElementById('lb').classList.add('on');});
document.getElementById('lb').addEventListener('click',()=>document.getElementById('lb').classList.remove('on'));document.addEventListener('keydown',e=>{if(e.key==='Escape')document.getElementById('lb').classList.remove('on')});
const KEY='v34-controls-'+location.pathname;let marks={};try{marks=JSON.parse(localStorage.getItem(KEY)||'{}')}catch(e){}
const mks=[...document.querySelectorAll('.mk')];
function paint(){let n=0;mks.forEach(m=>{const k=m.dataset.sid+'|'+m.dataset.seed;const v=marks[k]||'pass';m.querySelectorAll('button').forEach(b=>b.classList.toggle('on',b.dataset.m===v));
 const f=m.closest('.lab').nextElementSibling.querySelector('figure');f.classList.toggle('failed',v==='fail');f.classList.toggle('ship',v!=='fail');if(v==='fail')n++;});document.getElementById('count').textContent=n+' / '+mks.length+' fal cells marked fail';}
document.addEventListener('click',e=>{const b=e.target.closest('.mk button');if(!b)return;const m=b.closest('.mk');marks[m.dataset.sid+'|'+m.dataset.seed]=b.dataset.m;try{localStorage.setItem(KEY,JSON.stringify(marks))}catch(x){}paint();});
document.getElementById('export').onclick=()=>{let csv='set_id,seed,fal_verdict\\\\n';mks.forEach(m=>{const k=m.dataset.sid+'|'+m.dataset.seed;csv+=m.dataset.sid+','+m.dataset.seed+','+(marks[k]||'pass')+'\\\\n';});
 const box=document.getElementById('csvbox');box.style.display='block';box.value=csv;box.select();try{const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([csv],{type:'text/csv'}));a.download='v34_controls_fal.csv';a.click();}catch(x){}};
paint();</script>"""
if __name__ == "__main__":
    main(sys.argv[sys.argv.index("--embed") + 1] if "--embed" in sys.argv else None)
