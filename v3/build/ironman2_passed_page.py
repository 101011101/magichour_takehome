"""Iron man 2, the passes only: every VEi cell the judge did NOT fail under the
lenient proxy (garment<=2 or clean<=2), marginal first (garment ascending, then
fidelity) - a false-negative audit of the judge's passes.
  python3 v3/build/ironman2_passed_page.py   -> v3/report/ironman2_passed.html
"""
import csv, html, os
from collections import Counter
from PIL import Image

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RUN = os.path.join(REPO, "v3", "runs", "v34", "ironman2")
SCORES = os.path.join(REPO, "v3", "runs", "v34", "judge_ironman2_vei", "meta", "vlm_scores.csv")
REPORT = os.path.join(REPO, "v3", "report"); IMG = os.path.join(REPORT, "img_im2pass")
CRIT = ("garment", "identity", "scene", "clean", "hands", "realism")
MISSING = 0


def failed(r):
    return int(r["garment"]) <= 2 or int(r["clean"]) <= 2


def fid(c):
    return (int(c["garment"]) + int(c["identity"]) + int(c["scene"])) / 3


def key(c):
    return (int(c["garment"]), fid(c), int(c["seed"]))


def fig(path, cap, cls=""):
    global MISSING
    if not os.path.exists(path):
        MISSING += 1
        return f"<figure><div class='ph'>&mdash;</div><figcaption>{cap}</figcaption></figure>"
    im = Image.open(path).convert("RGB"); im.thumbnail((320, 440)); os.makedirs(IMG, exist_ok=True)
    o = os.path.join(IMG, os.path.basename(path))
    if not os.path.exists(o):
        im.save(o, quality=85, optimize=True)
    return f"<figure class='{cls}'><img src='img_im2pass/{os.path.basename(o)}' alt='{html.escape(cap)}' loading='lazy'><figcaption>{cap}</figcaption></figure>"


def main():
    scores = list(csv.DictReader(open(SCORES)))
    pairs_meta = {r["set_id"]: r for r in csv.DictReader(open(os.path.join(REPO, "v3", "colab", "matrix.csv")))}
    good = [r for r in scores if not failed(r)]
    nfail = len(scores) - len(good)
    hist = Counter(int(r["garment"]) for r in good)
    by = {}
    for r in good:
        by.setdefault(r["set_id"], []).append(r)
    # most-likely-wrong pass first: the pair's weakest passing cell leads the order
    order = sorted(by, key=lambda s: min(key(c) for c in by[s]))

    o = [HEAD, "<div class='wrap'>", BAR, "<h1>Iron man 2 &mdash; the passes, audited</h1>",
         f"<p class='lede'>These are the <b>{len(good)} of {len(scores)}</b> <b>VEi</b> cells the judge "
         f"<b>passed</b> under the lenient fail proxy (<b>garment&le;2 or clean&le;2 = fail</b>), across "
         f"<b>{len(by)}</b> of 200 pairs. The modal garment score here is <b>3 &mdash; &ldquo;partially "
         f"correct&rdquo;</b>, so many of these passes are <b>marginal</b>: they clear the bar only because the "
         f"bar is low. <b>Mark any that actually fail.</b> Ordered most-likely-wrong first &mdash; garment score "
         f"ascending, then fidelity (mean of garment/identity/scene), so the garment=3 cells come before the "
         f"clean ones. Judge of record, gpt-5.5, 2026-09-07 &mdash; "
         f"<code>v3/runs/v34/judge_ironman2_vei/</code>. <b>Audit each cell</b>: <b>pass &mdash; agree</b> "
         f"(default) &middot; <b>borderline</b> &middot; <b>actually fails</b>. The bar above keeps a live tally "
         f"and the corrected failure rate; export the CSV when done.</p>",
         "<table><tr><th>garment score</th><th>what it means</th><th>passed cells</th><th>share of passes</th></tr>"]
    for g, what in ((5, "fully correct"), (4, "mostly correct"), (3, "partially correct &mdash; the marginal ones")):
        n = hist.get(g, 0)
        cls = "neg" if g == 3 else ("pos" if g == 5 else "")
        o.append(f"<tr><td><b>garment {g}</b></td><td class='l'>{what}</td>"
                 f"<td class='{cls}'>{n}</td><td>{n/len(good)*100:.1f}%</td></tr>")
    o.append(f"<tr><td><b>all</b></td><td class='l'>every passed cell</td><td>{len(good)}</td><td>100.0%</td></tr></table>")
    o.append(f"<p class='foot'>The other <b>{nfail}</b> of {len(scores)} cells the judge already failed &mdash; "
             "they are on <code>ironman2_failures.html</code>. Every <b>actually fails</b> mark here adds to that "
             "count, so the bar shows what the true failure rate would be.</p>")

    for sid in order:
        cells = sorted(by[sid], key=key)
        m = pairs_meta.get(sid, {}); p, g = m.get("person", "?"), m.get("garment", "?")
        gs = "/".join(c["garment"] for c in cells)
        o.append(f"<h2>{html.escape(p)} wears {html.escape(g)}"
                 f"<span class='ar'>{len(cells)} of 3 seeds passed &middot; garment {gs} &middot; "
                 f"fidelity {sum(fid(c) for c in cells)/len(cells):.1f}</span></h2>")
        o.append("<div class='strip s3'>" + fig(os.path.join(RUN, "inputs", f"{p}.jpg"), "person")
                 + fig(os.path.join(RUN, "inputs", f"{g}.jpg"), "garment photograph")
                 + fig(os.path.join(RUN, "refs", f"{g}__VEi.jpg"), "VEi reference") + "</div>")
        for c in cells:
            sc = " &middot; ".join(f"<b class='{'warn' if int(c[k]) == 3 else ''}'>{k} {c[k]}</b>" for k in CRIT)
            mk = (f"<span class='mk' data-sid='{html.escape(sid)}' data-seed='{c['seed']}'>"
                  "<button data-m='agree' class='on'>pass &mdash; agree</button>"
                  "<button data-m='borderline'>borderline</button>"
                  "<button data-m='fails'>actually fails</button></span>")
            o.append(f"<div class='cell'><div class='out'>"
                     + fig(os.path.join(RUN, "gen", f"{sid}__VEi__s{c['seed']}.jpg"), f"s{c['seed']}", "ok")
                     + f"</div><div class='why'>{mk}<div class='sc'>{sc}</div>"
                     f"<p>{html.escape(c['note'])}</p></div></div>")
    o.append("<footer>Scores <code>v3/runs/v34/judge_ironman2_vei/meta/vlm_scores.csv</code>; "
             "<code>prd/v3/v3.4/RESULTS.md</code> &sect;10.2.</footer></div>" + LB
             + SCRIPT.replace("__TOTAL__", str(len(scores))).replace("__NFAIL__", str(nfail)))
    doc = "\n".join(o)
    dst = os.path.join(REPORT, "ironman2_passed.html")
    open(dst, "w").write(doc)
    print(dst, f"{os.path.getsize(dst)/1e6:.1f} MB")
    print(f"passed cells rendered: {len(good)} · pairs: {len(by)}")
    print("mark widgets:", doc.count("<span class='mk'"))
    print(f"missing-image placeholders: {MISSING}")
    print("garment histogram (passed): " + " · ".join(f"{g}:{hist.get(g,0)}" for g in (5, 4, 3)))


HEAD = """<title>Iron man 2 — Passes Audited</title><meta name='viewport' content='width=device-width,initial-scale=1'>
<style>:root{--bg:#0d0d10;--fg:#e8e8ea;--dim:#8a8a94;--line:#26262c;--acc:#7c5cff}*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.6 ui-sans-serif,-apple-system,"Segoe UI",Roboto,sans-serif}.wrap{max-width:1150px;margin:0 auto;padding:30px 26px}
h1{margin:0 0 6px;font-size:24px}h2{font-size:14px;margin:38px 0 6px;padding-top:12px;border-top:1px solid var(--line)}h2 .ar{font-size:12px;color:var(--dim);font-weight:400;margin-left:10px}
.lede{color:var(--dim);max-width:110ch;font-size:14px;margin:0 0 14px}.lede b{color:var(--fg)}
table{border-collapse:collapse;margin:6px 0 8px;font-size:13px}td,th{border:1px solid var(--line);padding:6px 12px;text-align:right}th{color:var(--dim)}td.l,th:nth-child(2){text-align:left}td:first-child{text-align:left}
.neg{color:#f0655a}.pos{color:#3fb950}.foot{color:var(--dim);font-size:12px;max-width:110ch;margin:0 0 10px}
.strip{display:grid;gap:6px}.s3{grid-template-columns:repeat(3,minmax(0,1fr));max-width:700px}
.cell{display:grid;grid-template-columns:230px 1fr;gap:14px;margin:10px 0;padding:10px;background:#15151b;border-radius:8px}
figure{margin:0}figure img{width:100%;display:block;background:#fff;border-radius:6px;cursor:zoom-in;aspect-ratio:3/4;object-fit:contain;border:3px solid transparent}
figure.bad img{border-color:#b43c3c}figure.warn img{border-color:#c9862c}figure.ok img{border-color:#2c5c33}
figcaption{font-size:11px;color:var(--dim);text-align:center;padding:4px 2px}
.sc{font-size:11px;color:var(--dim);margin-bottom:6px}.sc b{font-weight:600;color:#c9c9d2}.sc b.warn{color:#c9862c}
.why p{margin:0;font-size:13px;color:#c9c9d2}
.mk{display:inline-flex;gap:5px;margin-bottom:7px}.mk button{background:#1c1c24;color:var(--dim);border:1px solid var(--line);border-radius:5px;padding:3px 10px;font:inherit;font-size:11.5px;cursor:pointer}
.mk button:hover{color:var(--fg)}.mk button.on{background:#2a2a36;color:#fff;border-color:var(--acc)}
.mk button[data-m='agree'].on{border-color:#3fb950}.mk button[data-m='borderline'].on{border-color:#c9862c}.mk button[data-m='fails'].on{border-color:#f0655a}
.bar{position:sticky;top:0;z-index:5;background:#0d0d10ee;backdrop-filter:blur(6px);border-bottom:1px solid var(--line);padding:10px 0;margin:-30px -26px 16px;padding-left:26px;padding-right:26px;display:flex;gap:14px;align-items:center;flex-wrap:wrap;font-size:12.5px;color:var(--dim)}
.bar button{background:var(--acc);color:#fff;border:0;border-radius:6px;padding:6px 14px;font:inherit;cursor:pointer}
#rate{color:var(--fg);font-weight:600}
#csvbox{display:none;width:100%;height:120px;background:#15151b;color:var(--fg);border:1px solid var(--line);border-radius:6px;font:12px ui-monospace,monospace;padding:8px;margin-bottom:10px}
.ph{background:#17171d;border:1px dashed var(--line);border-radius:6px;aspect-ratio:3/4;display:flex;align-items:center;justify-content:center;color:var(--dim)}
footer{margin:40px 0 20px;font-size:12px;color:var(--dim)}
#lb{position:fixed;inset:0;background:#000d;display:none;align-items:center;justify-content:center;z-index:9}#lb.on{display:flex}#lb img{max-width:96vw;max-height:92vh}#lbc{position:fixed;bottom:8px;color:#fff;font-size:13px}</style>"""
LB = "<div id='lb'><img id='lbi' alt=''><div id='lbc'></div></div>"
BAR = ("<div class='bar'><button id='export'>Export CSV</button><span id='count'></span>"
       "<span id='rate'></span></div><textarea id='csvbox'></textarea>")
SCRIPT = """<script>document.addEventListener('click',e=>{const im=e.target.closest('figure img');if(!im)return;document.getElementById('lbi').src=im.getAttribute('src');document.getElementById('lbc').textContent=im.getAttribute('alt');document.getElementById('lb').classList.add('on');});
document.getElementById('lb').addEventListener('click',()=>document.getElementById('lb').classList.remove('on'));document.addEventListener('keydown',e=>{if(e.key==='Escape')document.getElementById('lb').classList.remove('on')});
const KEY='im2-passaudit';let marks={};try{marks=JSON.parse(localStorage.getItem(KEY)||'{}')}catch(e){}
const mks=[...document.querySelectorAll('.mk')];const TOTAL=__TOTAL__,JFAIL=__NFAIL__;
function paint(){const t={agree:0,borderline:0,fails:0};
 mks.forEach(m=>{const k=m.dataset.sid+'|'+m.dataset.seed;const v=marks[k]||'agree';
  m.querySelectorAll('button').forEach(b=>b.classList.toggle('on',b.dataset.m===v));
  const f=m.closest('.cell').querySelector('figure');
  f.classList.toggle('ok',v==='agree');f.classList.toggle('warn',v==='borderline');f.classList.toggle('bad',v==='fails');
  t[v]++;});
 document.getElementById('count').textContent=t.agree+' agreed · '+t.borderline+' borderline · '+t.fails+' actually fail, of '+mks.length;
 const real=JFAIL+t.fails;
 document.getElementById('rate').textContent='→ corrected: ('+JFAIL+' + '+t.fails+' actually-fails) = '+real+'/'+TOTAL+' fail ('+(real/TOTAL*100).toFixed(1)+'%)';}
document.addEventListener('click',e=>{const b=e.target.closest('.mk button');if(!b)return;const m=b.closest('.mk');
 marks[m.dataset.sid+'|'+m.dataset.seed]=b.dataset.m;try{localStorage.setItem(KEY,JSON.stringify(marks))}catch(x){}paint();});
document.getElementById('export').onclick=()=>{let csv='set_id,seed,judge_verdict,audit\\n';
 mks.forEach(m=>{const k=m.dataset.sid+'|'+m.dataset.seed;csv+=m.dataset.sid+','+m.dataset.seed+',pass,'+(marks[k]||'agree')+'\\n';});
 const box=document.getElementById('csvbox');box.style.display='block';box.value=csv;box.select();
 try{const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([csv],{type:'text/csv'}));a.download='im2_pass_audit.csv';a.click();}catch(x){}};
paint();</script>"""

if __name__ == "__main__":
    main()
