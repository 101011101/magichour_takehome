"""Iron man 2 review page, VEi arm only: the locked v3.4 version on the full 200-pair
matrix at seeds 46/47/48. Per pair one context strip (person, garment, VEi ref) and one
row of the three seed cells; every cell gets a pass / ok / FAIL mark, CSV export.
  python3 v3/build/ironman2_vei_page.py [run_dir]"""
import csv, html, os, sys
from PIL import Image

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RUN = os.path.join(REPO, "v3", "runs", "v34", "ironman2")
MATRIX = os.path.join(REPO, "v3", "colab", "matrix.csv")
REPORT = os.path.join(REPO, "v3", "report")
IMG = os.path.join(REPORT, "img_im2vei")
SEEDS = (46, 47, 48)


def src(path, w=300):
    if not os.path.exists(path):
        return None
    im = Image.open(path).convert("RGB")
    im.thumbnail((w, 420))
    os.makedirs(IMG, exist_ok=True)
    o = os.path.join(IMG, os.path.basename(path))
    if not os.path.exists(o):
        im.save(o, quality=85, optimize=True)
    return "img_im2vei/" + os.path.basename(o)


def fig(path, cap, cls=""):
    s = src(path)
    if s is None:
        return f"<figure class='{cls}'><div class='ph'>&mdash;</div><figcaption>{cap}</figcaption></figure>"
    return f"<figure class='{cls}'><img src='{s}' alt='{html.escape(cap)}' loading='lazy'><figcaption>{cap}</figcaption></figure>"


def main(run):
    rows = list(csv.DictReader(open(MATRIX)))
    o = [HEAD, "<div class='wrap'>", BAR,
         "<h1>Iron man 2 &mdash; VEi arm (200 pairs)</h1>",
         "<p class='lede'>The locked v3.4 version (<b>VEi</b>) on the full 200-pair matrix at seeds <b>46/47/48</b> "
         "&mdash; 600 cells. The BC comparison lands with session 2; this page is VEi only. "
         "Mark each cell <b>pass</b> (default) &middot; <b>ok</b> &middot; <b>FAIL</b>, then export the CSV.</p>"]
    for r in rows:
        sid, p, g = r["set_id"], r["person"], r["garment"]
        o.append(f"<h2>{html.escape(p)} wears {html.escape(g)}<span class='ar'>{html.escape(sid)}</span></h2>")
        o.append("<div class='strip s3 ctx'>"
                 + fig(os.path.join(run, "inputs", f"{p}.jpg"), "person")
                 + fig(os.path.join(run, "inputs", f"{g}.jpg"), "garment photograph")
                 + fig(os.path.join(run, "refs", f"{g}__VEi.jpg"), "VEi reference")
                 + "</div>")
        cells = []
        for s in SEEDS:
            cells.append("<div class='cell'>"
                         + fig(os.path.join(run, "gen", f"{sid}__VEi__s{s}.jpg"), f"VEi s{s}")
                         + f"<div class='mk' data-sid='{html.escape(sid)}' data-seed='{s}'>"
                         "<button data-m='pass' class='on'>pass</button>"
                         "<button data-m='ok'>ok</button>"
                         "<button data-m='fail'>FAIL</button></div></div>")
        o.append("<div class='strip s3 gen'>" + "".join(cells) + "</div>")
    o.append(FOOT + "</div>" + LB + SCRIPT)
    dst = os.path.join(REPORT, "ironman2_vei.html")
    open(dst, "w").write("\n".join(o))
    page = open(dst).read()
    print(dst, f"{os.path.getsize(dst)/1e6:.1f} MB")
    print("pair headers:", page.count("<h2>"))
    print("mark widgets:", page.count("class='mk'"))
    print("missing-image placeholders:", page.count("class='ph'"))


BAR = "<div class='bar'><button id='export'>Export CSV</button><span id='count'></span></div><textarea id='csvbox'></textarea>"
HEAD = """<title>Iron Man 2 — VEi Review</title><meta name='viewport' content='width=device-width,initial-scale=1'>
<style>:root{--bg:#0d0d10;--fg:#e8e8ea;--dim:#8a8a94;--line:#26262c;--acc:#7c5cff;--good:#3fb950;--warn:#c9862c;--bad:#f0655a}*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.6 ui-sans-serif,-apple-system,"Segoe UI",Roboto,sans-serif}.wrap{max-width:1000px;margin:0 auto;padding:30px 26px 0}
h1{margin:0 0 6px;font-size:25px}h2{font-size:14px;margin:40px 0 6px;padding-top:12px;border-top:1px solid var(--line);display:flex;gap:10px;align-items:center;flex-wrap:wrap}h2 .ar{font-size:12px;color:var(--dim);font-weight:400}
.lede{color:var(--dim);max-width:100ch;font-size:14px;margin:0 0 14px}.lede b{color:var(--fg)}
.strip{display:grid;gap:5px}.s3{grid-template-columns:repeat(3,minmax(0,1fr));max-width:900px}.ctx{opacity:.9}.gen{margin-top:8px}
figure{margin:0}figure img{width:100%;display:block;background:#fff;border-radius:6px;cursor:zoom-in;aspect-ratio:3/4;object-fit:contain;border:3px solid transparent}
.cell.pass figure img{border-color:#2c5c33}.cell.ok figure img{border-color:var(--warn)}.cell.fail figure img{border-color:#b43c3c}
figcaption{font-size:11px;color:var(--dim);text-align:center;padding:5px 2px}.ph{background:#17171d;border:1px dashed var(--line);border-radius:6px;aspect-ratio:3/4;display:flex;align-items:center;justify-content:center;color:var(--dim)}
.bar{position:sticky;top:0;background:var(--bg);padding:8px 0;z-index:5;border-bottom:1px solid var(--line);display:flex;gap:10px;align-items:center}.bar button{background:#17171d;color:var(--fg);border:1px solid var(--acc);border-radius:5px;padding:5px 12px;cursor:pointer}
#count{color:var(--dim);font-size:12px}#csvbox{width:100%;height:50px;margin:6px 0 0;background:#17171d;color:var(--dim);border:1px solid var(--line);font:11px ui-monospace,monospace;display:none}
.mk{text-align:center;margin-top:2px}.mk button{background:#17171d;color:var(--fg);border:1px solid var(--line);border-radius:5px;padding:3px 9px;font-size:11px;cursor:pointer;margin:0 2px}
.mk button[data-m='pass'].on{background:#1e3a24;border-color:var(--good)}.mk button[data-m='ok'].on{background:#4d3a1a;border-color:var(--warn)}.mk button[data-m='fail'].on{background:#4d1f1f;border-color:#b43c3c}
#lb{display:none;position:fixed;inset:0;background:rgba(0,0,0,.96);z-index:99;align-items:center;justify-content:center;flex-direction:column;gap:10px;padding:16px}#lb.on{display:flex}#lb img{max-width:96vw;max-height:92vh;object-fit:contain;background:#fff}#lbc{color:var(--dim);font-size:13px}
footer{border-top:1px solid var(--line);margin-top:44px;padding:22px 0 30px;color:var(--dim);font-size:12.5px}code{background:#1b1b22;padding:1px 5px;border-radius:4px;font-size:12px}</style>"""
FOOT = """<footer>Run <code>v3/runs/v34/ironman2/</code> (VEi, seeds 46/47/48, full matrix <code>v3/colab/matrix.csv</code>). BC cells come with session 2.</footer>"""
LB = "<div id='lb'><img id='lbi' alt=''><div id='lbc'></div></div>"
SCRIPT = """<script>document.addEventListener('click',e=>{const im=e.target.closest('figure img');if(!im)return;document.getElementById('lbi').src=im.getAttribute('src');document.getElementById('lbc').textContent=im.getAttribute('alt');document.getElementById('lb').classList.add('on');});
document.getElementById('lb').addEventListener('click',()=>document.getElementById('lb').classList.remove('on'));document.addEventListener('keydown',e=>{if(e.key==='Escape')document.getElementById('lb').classList.remove('on')});
const KEY='ironman2-vei-marks';let marks={};try{marks=JSON.parse(localStorage.getItem(KEY)||'{}')}catch(e){}
const mks=[...document.querySelectorAll('.mk')];
function paint(){const t={pass:0,ok:0,fail:0};mks.forEach(m=>{const v=marks[m.dataset.sid+'|'+m.dataset.seed]||'pass';
 m.querySelectorAll('button').forEach(b=>b.classList.toggle('on',b.dataset.m===v));
 const c=m.closest('.cell');c.classList.remove('pass','ok','fail');c.classList.add(v);t[v]++;});
 document.getElementById('count').textContent=t.pass+' pass · '+t.ok+' ok · '+t.fail+' FAIL of '+mks.length;}
document.addEventListener('click',e=>{const b=e.target.closest('.mk button');if(!b)return;const m=b.closest('.mk');marks[m.dataset.sid+'|'+m.dataset.seed]=b.dataset.m;try{localStorage.setItem(KEY,JSON.stringify(marks))}catch(x){}paint();});
document.getElementById('export').onclick=()=>{let csv='set_id,seed,verdict\\n';mks.forEach(m=>{csv+=m.dataset.sid+','+m.dataset.seed+','+(marks[m.dataset.sid+'|'+m.dataset.seed]||'pass')+'\\n';});
 const box=document.getElementById('csvbox');box.style.display='block';box.value=csv;box.select();try{const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([csv],{type:'text/csv'}));a.download='ironman2_vei_marks.csv';a.click();}catch(x){}};
paint();</script>"""

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else RUN)
