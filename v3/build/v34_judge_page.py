"""The judge's verdict, seen: aggregate six-criterion table for VEi / VE / VS, then per
pair the judge's numbers and every arm's cells beside the original v3.3 run (arm V) and
the incumbent BC — both at their iron-man seeds 46/47/48, image context only (not in
this judge batch; their scored record is the iron-man blind vote).
  python3 v3/build/v34_judge_page.py   -> v3/report/v34_judge.html
"""
import csv, html, os
from PIL import Image

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
IM = os.path.join(REPO, "v3", "runs", "ironman", "20260830_0548")
RUNS = {"VEi": "v34_a100_vei_20260906_0334", "VE": "v34_a100_ve_20260904_0611", "VS": "v34_a100_vs_20260905_0550"}
J = os.path.join(REPO, "v3", "runs", "v34", "judge_vei", "meta", "per_pair.csv")
REPORT = os.path.join(REPO, "v3", "report"); IMG = os.path.join(REPORT, "img_v34j")
CRIT = ["fid", "garment", "identity", "scene", "clean", "hands", "realism"]
LAB = {"fid": "fidelity (g·i·s)", "garment": "garment", "identity": "identity", "scene": "scene",
       "clean": "clean", "hands": "hands", "realism": "realism"}


def fig(path, cap, cls=""):
    if not os.path.exists(path):
        return f"<figure><div class='ph'>&mdash;</div><figcaption>{cap}</figcaption></figure>"
    im = Image.open(path).convert("RGB"); im.thumbnail((300, 420)); os.makedirs(IMG, exist_ok=True)
    o = os.path.join(IMG, os.path.basename(os.path.dirname(os.path.dirname(path)))[:6] + "_" + os.path.basename(path))
    if not os.path.exists(o):
        im.save(o, quality=85, optimize=True)
    return f"<figure class='{cls}'><img src='img_v34j/{os.path.basename(o)}' alt='{html.escape(cap)}' loading='lazy'><figcaption>{cap}</figcaption></figure>"


def main():
    rows = list(csv.DictReader(open(J)))
    n = len(rows)
    agg = {a: {c: sum(float(r[f"{a}_{c}"]) for r in rows) / n for c in CRIT} for a in RUNS}
    o = [HEAD, "<div class='wrap'><h1>The judge's verdict &mdash; VEi &middot; VE &middot; VS, beside V and BC</h1>",
         "<p class='lede'>Blind gpt-5.5 judge (RESULTS &sect;9.1): 279 cells, arm names never sent, statistics as the "
         "judge of record. <b>VE &ge; VEi &gt; VS</b> — VEi beats VS outside seed noise (+0.125 fid, 23&ndash;7 pairs, "
         "p=0.008); VEi trails VE inside it (&minus;0.068, 21&ndash;10 to VE), with real deficits on hands and the "
         "realism axis. On the <b>garment</b> criterion the three arms are statistically identical. "
         "The <b>V</b> (v3.3 lock) and <b>BC</b> (incumbent) columns are image context at seeds 46/47/48 — "
         "not in this judge batch; their scored record is the iron-man blind vote (v3.3 RESULTS &sect;14).</p>",
         "<table><tr><th>criterion</th>" + "".join(f"<th>{a}</th>" for a in RUNS)
         + "<th>&Delta; VEi&minus;VE</th><th>&Delta; VEi&minus;VS</th></tr>"]
    for c in CRIT:
        cls = " class='hi'" if c == "fid" else ""
        d1, d2 = agg["VEi"][c] - agg["VE"][c], agg["VEi"][c] - agg["VS"][c]
        o.append(f"<tr{cls}><td>{LAB[c]}</td>" + "".join(f"<td>{agg[a][c]:.3f}</td>" for a in RUNS)
                 + f"<td class='{'neg' if d1 < -0.02 else 'pos' if d1 > 0.02 else ''}'>{d1:+.3f}</td>"
                 + f"<td class='{'neg' if d2 < -0.02 else 'pos' if d2 > 0.02 else ''}'>{d2:+.3f}</td></tr>")
    w1 = sum(1 for r in rows if r["winner_VEivVE"] == "VEi"), sum(1 for r in rows if r["winner_VEivVE"] == "VE")
    w2 = sum(1 for r in rows if r["winner_VEivVS"] == "VEi"), sum(1 for r in rows if r["winner_VEivVS"] == "VS")
    o.append(f"<tr><td>pair wins</td><td colspan=3></td><td>{w1[0]}&ndash;{w1[1]} VE</td><td>{w2[0]}&ndash;{w2[1]} <b>VEi</b></td></tr></table>")

    for r in sorted(rows, key=lambda x: float(x["diff_fid_VEivVE"])):
        sid = r["set_id"]
        mrows = {s: dict((k.split("_")[0], r.get(k)) for k in []) for s in []}
        m = list(csv.DictReader(open(os.path.join(REPO, "v3", "testsets", "v34_failures.csv"))))
        pr = next(x for x in m if x["set_id"] == sid); p, g = pr["person"], pr["garment"]
        o.append(f"<h2>{html.escape(p)} wears {html.escape(g)}<span class='ar'>{r['class']}"
                 f" &middot; fid VEi {float(r['VEi_fid']):.2f} / VE {float(r['VE_fid']):.2f} / VS {float(r['VS_fid']):.2f}"
                 f" &middot; VEi-vs-VE winner: <b>{r['winner_VEivVE']}</b> &middot; VEi-vs-VS winner: <b>{r['winner_VEivVS']}</b></span></h2>")
        for new, old in ((49, 46), (50, 47), (51, 48)):
            o.append(f"<div class='lab'>seed {new} (v3.4 arms) &middot; {old} (V / BC)</div><div class='strip'>"
                     + fig(os.path.join(REPO, "v3", "runs", "v34", RUNS["VEi"], "gen", f"{sid}__VEi__s{new}.jpg"), f"<b>VEi</b> s{new}", "a")
                     + fig(os.path.join(REPO, "v3", "runs", "v34", RUNS["VE"], "gen", f"{sid}__VE__s{new}.jpg"), f"<b>VE</b> s{new}", "b")
                     + fig(os.path.join(REPO, "v3", "runs", "v34", RUNS["VS"], "gen", f"{sid}__VS__s{new}.jpg"), f"<b>VS</b> s{new}", "c")
                     + fig(os.path.join(IM, "gen", f"{sid}__V__s{old}.jpg"), f"V (v3.3 lock) s{old}")
                     + fig(os.path.join(IM, "gen", f"{sid}__BC__s{old}.jpg"), f"BC (incumbent) s{old}")
                     + "</div>")
    o.append("<footer>Judge outputs: <code>v3/runs/v34/judge_vei/</code> (REPORT.md, meta/). Pairs ordered hardest-for-VEi first "
             "(by fid &Delta; vs VE). <code>prd/v3/v3.4/RESULTS.md</code> &sect;9.1.</footer></div>" + LB + SCRIPT)
    dst = os.path.join(REPORT, "v34_judge.html")
    open(dst, "w").write("\n".join(o)); print(dst, f"{os.path.getsize(dst)/1e6:.1f} MB")


HEAD = """<title>Judge Verdict: VEi · VE · VS</title><meta name='viewport' content='width=device-width,initial-scale=1'>
<style>:root{--bg:#0d0d10;--fg:#e8e8ea;--dim:#8a8a94;--line:#26262c;--acc:#7c5cff}*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.6 ui-sans-serif,-apple-system,"Segoe UI",Roboto,sans-serif}.wrap{max-width:1250px;margin:0 auto;padding:30px 26px}
h1{margin:0 0 6px;font-size:23px}h2{font-size:14px;margin:38px 0 4px;padding-top:12px;border-top:1px solid var(--line)}h2 .ar{font-size:12px;color:var(--dim);font-weight:400;margin-left:10px}
.lede{color:var(--dim);max-width:115ch;font-size:14px;margin:0 0 14px}.lede b{color:var(--fg)}
table{border-collapse:collapse;margin:10px 0 20px;font-size:13px}td,th{border:1px solid var(--line);padding:5px 12px;text-align:right}th{color:var(--dim)}td:first-child{text-align:left}
tr.hi td{background:#1c1c26;font-weight:600}.neg{color:#f0655a}.pos{color:#3fb950}
.lab{font-size:12px;color:var(--dim);margin:8px 0 3px}
.strip{display:grid;gap:5px;grid-template-columns:repeat(5,minmax(0,1fr));max-width:1200px}
figure{margin:0}figure img{width:100%;display:block;background:#fff;border-radius:6px;cursor:zoom-in;aspect-ratio:3/4;object-fit:contain;border:3px solid transparent}
figure.a img{border-color:#7c5cff}figure.b img{border-color:#2c5c33}figure.c img{border-color:#7a5a2c}
figcaption{font-size:11px;color:var(--dim);text-align:center;padding:4px 2px}
.ph{background:#17171d;border:1px dashed var(--line);border-radius:6px;aspect-ratio:3/4;display:flex;align-items:center;justify-content:center;color:var(--dim)}
footer{margin:40px 0 20px;font-size:12px;color:var(--dim)}
#lb{position:fixed;inset:0;background:#000d;display:none;align-items:center;justify-content:center;z-index:9}#lb.on{display:flex}#lb img{max-width:96vw;max-height:92vh}#lbc{position:fixed;bottom:8px;color:#fff;font-size:13px}</style>"""
LB = "<div id='lb'><img id='lbi' alt=''><div id='lbc'></div></div>"
SCRIPT = """<script>document.addEventListener('click',e=>{const im=e.target.closest('figure img');if(!im)return;document.getElementById('lbi').src=im.getAttribute('src');document.getElementById('lbc').textContent=im.getAttribute('alt');document.getElementById('lb').classList.add('on');});
document.getElementById('lb').addEventListener('click',()=>document.getElementById('lb').classList.remove('on'));document.addEventListener('keydown',e=>{if(e.key==='Escape')document.getElementById('lb').classList.remove('on')});</script>"""

if __name__ == "__main__":
    main()
