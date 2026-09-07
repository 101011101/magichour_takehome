"""Iron man 2, the failures only: every VEi cell the judge failed (garment<=2 or
clean<=2), worst first, with the judge's six scores and its note on each - plus the
failure rates of the v3.3 lock (V) and the incumbent (BC) for context.
  python3 v3/build/ironman2_failures_page.py   -> v3/report/ironman2_failures.html
"""
import csv, html, os
from PIL import Image

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RUN = os.path.join(REPO, "v3", "runs", "v34", "ironman2")
SCORES = os.path.join(REPO, "v3", "runs", "v34", "judge_ironman2_vei", "meta", "vlm_scores.csv")
BASE = os.path.join(REPO, "v33_ironman_vlm_scores_bca4.csv")
REPORT = os.path.join(REPO, "v3", "report"); IMG = os.path.join(REPORT, "img_im2fail")
CRIT = ("garment", "identity", "scene", "clean", "hands", "realism")


def failed(r):
    return int(r["garment"]) <= 2 or int(r["clean"]) <= 2


def rates(rows):
    """cell fail %, all-seed-clean %, >=1-seed %"""
    pairs = {}
    for r in rows:
        pairs.setdefault(r["set_id"], []).append(not failed(r))
    f = sum(1 for r in rows if failed(r))
    ap = sum(1 for v in pairs.values() if all(v)); an = sum(1 for v in pairs.values() if any(v))
    return len(rows), f, f / len(rows) * 100, len(pairs), ap / len(pairs) * 100, an / len(pairs) * 100


def fig(path, cap, cls=""):
    if not os.path.exists(path):
        return f"<figure><div class='ph'>&mdash;</div><figcaption>{cap}</figcaption></figure>"
    im = Image.open(path).convert("RGB"); im.thumbnail((320, 440)); os.makedirs(IMG, exist_ok=True)
    o = os.path.join(IMG, os.path.basename(path))
    if not os.path.exists(o):
        im.save(o, quality=85, optimize=True)
    return f"<figure class='{cls}'><img src='img_im2fail/{os.path.basename(o)}' alt='{html.escape(cap)}' loading='lazy'><figcaption>{cap}</figcaption></figure>"


def main():
    scores = list(csv.DictReader(open(SCORES)))
    base = list(csv.DictReader(open(BASE)))
    pairs_meta = {r["set_id"]: r for r in csv.DictReader(open(os.path.join(REPO, "v3", "colab", "matrix.csv")))}
    bad = [r for r in scores if failed(r)]
    by = {}
    for r in bad:
        by.setdefault(r["set_id"], []).append(r)
    # worst pair first: mean fidelity of its failing cells, then number of failing cells
    order = sorted(by, key=lambda s: (sum((int(c["garment"]) + int(c["identity"]) + int(c["scene"])) / 3 for c in by[s]) / len(by[s]), -len(by[s])))

    vei = rates(scores)
    v = rates([r for r in base if r["arm"] == "V"])
    bc = rates([r for r in base if r["arm"] == "BC"])
    o = [HEAD, "<div class='wrap'><h1>Iron man 2 &mdash; the failures only</h1>",
         f"<p class='lede'>Every <b>VEi</b> cell the judge failed (garment&le;2 or clean&le;2): "
         f"<b>{vei[1]} of {vei[0]}</b> cells, across <b>{len(by)}</b> of 200 pairs. Worst pair first (by the mean "
         f"fidelity of its failing cells). Each row: the judge's six scores and its note. "
         f"Judge of record, gpt-5.5, 2026-09-07 &mdash; <code>v3/runs/v34/judge_ironman2_vei/</code>.</p>",
         "<table><tr><th>arm</th><th>what it is</th><th>cells</th><th>cell fail</th><th>cell pass</th>"
         "<th>pairs clean at all seeds</th><th>pairs clean at &ge;1 seed</th></tr>"]
    for name, what, t in (("VEi", "the v3.4 version (this run)", vei),
                          ("V", "the v3.3 lock", v),
                          ("BC / BCA4", "the incumbent, as it was actually built", bc)):
        o.append(f"<tr><td><b>{name}</b></td><td class='l'>{what}</td><td>{t[0]}</td>"
                 f"<td class='neg'>{t[1]} &middot; {t[2]:.1f}%</td><td class='pos'>{100-t[2]:.1f}%</td>"
                 f"<td>{t[4]:.1f}%</td><td>{t[5]:.1f}%</td></tr>")
    o.append("</table><p class='foot'>V and BC come from the v3.3 iron man's scored record "
             "(<code>v33_ironman_vlm_scores_bca4.csv</code>) &mdash; an <b>incomplete</b> run (seed 48 mostly "
             "missing: V 396 cells, BC 388) from an earlier judge pass, and that <b>BC is the mis-built BCA4</b> "
             "(bald frame &rarr; A4 crop, head never subtracted). On the 353 cells all three arms share: "
             "V 23.8% fail &middot; BC 20.7% &middot; VEi 27.8%. Treat gaps under ~5 points as calibration noise.</p>")

    for sid in order:
        cells = sorted(by[sid], key=lambda c: int(c["seed"]))
        m = pairs_meta.get(sid, {}); p, g = m.get("person", "?"), m.get("garment", "?")
        o.append(f"<h2>{html.escape(p)} wears {html.escape(g)}<span class='ar'>{len(cells)} of 3 seeds failed</span></h2>")
        o.append("<div class='strip s3'>" + fig(os.path.join(RUN, "inputs", f"{p}.jpg"), "person")
                 + fig(os.path.join(RUN, "inputs", f"{g}.jpg"), "garment photograph")
                 + fig(os.path.join(RUN, "refs", f"{g}__VEi.jpg"), "VEi reference") + "</div>")
        for c in cells:
            sc = " &middot; ".join(f"<b class='{'bad' if int(c[k]) <= 2 else ''}'>{k} {c[k]}</b>" for k in CRIT)
            o.append(f"<div class='cell'><div class='out'>"
                     + fig(os.path.join(RUN, "gen", f"{sid}__VEi__s{c['seed']}.jpg"), f"s{c['seed']}", "bad")
                     + f"</div><div class='why'><div class='sc'>{sc}</div>"
                     f"<p>{html.escape(c['note'])}</p></div></div>")
    o.append("<footer>Scores <code>v3/runs/v34/judge_ironman2_vei/meta/vlm_scores.csv</code>; "
             "<code>prd/v3/v3.4/RESULTS.md</code> &sect;10.2.</footer></div>" + LB + SCRIPT)
    dst = os.path.join(REPORT, "ironman2_failures.html")
    open(dst, "w").write("\n".join(o))
    print(dst, f"{os.path.getsize(dst)/1e6:.1f} MB · {vei[1]} failing cells · {len(by)} pairs")


HEAD = """<title>Iron man 2 — Failures</title><meta name='viewport' content='width=device-width,initial-scale=1'>
<style>:root{--bg:#0d0d10;--fg:#e8e8ea;--dim:#8a8a94;--line:#26262c;--acc:#7c5cff}*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.6 ui-sans-serif,-apple-system,"Segoe UI",Roboto,sans-serif}.wrap{max-width:1150px;margin:0 auto;padding:30px 26px}
h1{margin:0 0 6px;font-size:24px}h2{font-size:14px;margin:38px 0 6px;padding-top:12px;border-top:1px solid var(--line)}h2 .ar{font-size:12px;color:var(--dim);font-weight:400;margin-left:10px}
.lede{color:var(--dim);max-width:110ch;font-size:14px;margin:0 0 14px}.lede b{color:var(--fg)}
table{border-collapse:collapse;margin:6px 0 8px;font-size:13px}td,th{border:1px solid var(--line);padding:6px 12px;text-align:right}th{color:var(--dim)}td.l,th:nth-child(2){text-align:left}td:first-child{text-align:left}
.neg{color:#f0655a}.pos{color:#3fb950}.foot{color:var(--dim);font-size:12px;max-width:110ch;margin:0 0 10px}
.strip{display:grid;gap:6px}.s3{grid-template-columns:repeat(3,minmax(0,1fr));max-width:700px}
.cell{display:grid;grid-template-columns:230px 1fr;gap:14px;margin:10px 0;padding:10px;background:#15151b;border-radius:8px}
figure{margin:0}figure img{width:100%;display:block;background:#fff;border-radius:6px;cursor:zoom-in;aspect-ratio:3/4;object-fit:contain;border:3px solid transparent}
figure.bad img{border-color:#b43c3c}
figcaption{font-size:11px;color:var(--dim);text-align:center;padding:4px 2px}
.sc{font-size:11px;color:var(--dim);margin-bottom:6px}.sc b{font-weight:600;color:#c9c9d2}.sc b.bad{color:#f0655a}
.why p{margin:0;font-size:13px;color:#c9c9d2}
.ph{background:#17171d;border:1px dashed var(--line);border-radius:6px;aspect-ratio:3/4;display:flex;align-items:center;justify-content:center;color:var(--dim)}
footer{margin:40px 0 20px;font-size:12px;color:var(--dim)}
#lb{position:fixed;inset:0;background:#000d;display:none;align-items:center;justify-content:center;z-index:9}#lb.on{display:flex}#lb img{max-width:96vw;max-height:92vh}#lbc{position:fixed;bottom:8px;color:#fff;font-size:13px}</style>"""
LB = "<div id='lb'><img id='lbi' alt=''><div id='lbc'></div></div>"
SCRIPT = """<script>document.addEventListener('click',e=>{const im=e.target.closest('figure img');if(!im)return;document.getElementById('lbi').src=im.getAttribute('src');document.getElementById('lbc').textContent=im.getAttribute('alt');document.getElementById('lb').classList.add('on');});
document.getElementById('lb').addEventListener('click',()=>document.getElementById('lb').classList.remove('on'));document.addEventListener('keydown',e=>{if(e.key==='Escape')document.getElementById('lb').classList.remove('on')});</script>"""

if __name__ == "__main__":
    main()
