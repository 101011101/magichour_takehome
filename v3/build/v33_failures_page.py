"""The v3.3 iron man's failures: every scored cell where the lock (V) or the incumbent
as-built (BCA4) failed the proxy, both arms side by side with the judge's six scores and
its notes, so the two can be compared on the same cell.
  python3 v3/build/v33_failures_page.py   -> v3/report/v33_failures.html
"""
import csv, html, os
from PIL import Image

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RUN = os.path.join(REPO, "v3", "runs", "ironman", "20260830_0548")
SCORES = os.path.join(REPO, "v33_ironman_vlm_scores_bca4.csv")
REPORT = os.path.join(REPO, "v3", "report"); IMG = os.path.join(REPORT, "img_v33fail")
CRIT = ("garment", "identity", "scene", "clean", "hands", "realism")


def failed(r):
    return int(r["garment"]) <= 2 or int(r["clean"]) <= 2


def fid(r):
    return (int(r["garment"]) + int(r["identity"]) + int(r["scene"])) / 3


def fig(path, cap, cls=""):
    if not os.path.exists(path):
        return f"<figure><div class='ph'>&mdash;</div><figcaption>{cap}</figcaption></figure>"
    im = Image.open(path).convert("RGB"); im.thumbnail((320, 440)); os.makedirs(IMG, exist_ok=True)
    o = os.path.join(IMG, os.path.basename(path))
    if not os.path.exists(o):
        im.save(o, quality=85, optimize=True)
    return f"<figure class='{cls}'><img src='img_v33fail/{os.path.basename(o)}' alt='{html.escape(cap)}' loading='lazy'><figcaption>{cap}</figcaption></figure>"


def scores_line(r):
    if r is None:
        return "<span class='dim'>not scored in this run</span>"
    return " &middot; ".join(f"<b class='{'bad' if int(r[k]) <= 2 else ''}'>{k} {r[k]}</b>" for k in CRIT)


def main():
    rows = list(csv.DictReader(open(SCORES)))
    cells = {}
    for r in rows:
        cells.setdefault((r["set_id"], r["seed"]), {})[r["arm"]] = r
    meta = {r["set_id"]: r for r in csv.DictReader(open(os.path.join(REPO, "v3", "colab", "matrix.csv")))}
    bad = {k: v for k, v in cells.items() if any(failed(a) for a in v.values())}
    by = {}
    for (sid, seed), arms in bad.items():
        by.setdefault(sid, []).append((seed, arms))
    order = sorted(by, key=lambda s: min(min(fid(a) for a in arms.values()) for _, arms in by[s]))

    nV = sum(1 for v in bad.values() if "V" in v and failed(v["V"]))
    nB = sum(1 for v in bad.values() if "BC" in v and failed(v["BC"]))
    both = sum(1 for v in bad.values() if "V" in v and "BC" in v and failed(v["V"]) and failed(v["BC"]))
    o = [HEAD, "<div class='wrap'><h1>The v3.3 iron man &mdash; its failures, both arms</h1>",
         f"<p class='lede'>Every scored cell of the v3.3 run where either arm failed the proxy "
         f"(garment&le;2 or clean&le;2): <b>{len(bad)}</b> cells over <b>{len(by)}</b> pairs. "
         f"<b>V</b> = the v3.3 lock (failed {nV}); <b>BCA4</b> = the incumbent <i>as it was actually built</i> "
         f"&mdash; bald pass &rarr; A4 crop, <b>head never subtracted</b> (failed {nB}); both failed on {both}. "
         f"Worst pair first. Rates on this record: V <b>23.2%</b> of 396 cells, BCA4 <b>21.4%</b> of 388 "
         f"(the run is incomplete &mdash; seed 48 mostly missing). For contrast the v3.4 version scored "
         f"<b>29.7%</b> of a complete 600 &mdash; see <code>ironman2_failures.html</code>.</p>"]
    for sid in order:
        m = meta.get(sid, {}); p, g = m.get("person", "?"), m.get("garment", "?")
        o.append(f"<h2>{html.escape(p)} wears {html.escape(g)}<span class='ar'>{len(by[sid])} failing cell(s)</span></h2>")
        o.append("<div class='strip s4'>" + fig(os.path.join(RUN, "inputs", f"{p}.jpg"), "person")
                 + fig(os.path.join(RUN, "inputs", f"{g}.jpg"), "garment photograph")
                 + fig(os.path.join(RUN, "refs", f"{g}__V.jpg"), "V reference (head swapped, ankle cut)")
                 + fig(os.path.join(RUN, "refs", f"{g}__BC.jpg"), "BCA4 reference (bald &mdash; head NOT subtracted)")
                 + "</div>")
        for seed, arms in sorted(by[sid], key=lambda t: int(t[0])):
            o.append(f"<div class='lab'>seed {seed}</div><div class='pair'>")
            for arm, label in (("V", "V &mdash; the v3.3 lock"), ("BC", "BCA4 &mdash; the incumbent as built")):
                r = arms.get(arm)
                cls = "bad" if r is not None and failed(r) else ("ok" if r is not None else "")
                o.append("<div class='cell'>"
                         + fig(os.path.join(RUN, "gen", f"{sid}__{arm}__s{seed}.jpg"), label, cls)
                         + f"<div class='sc'>{scores_line(r)}</div>"
                         + (f"<p>{html.escape(r['note'])}</p>" if r is not None else "") + "</div>")
            o.append("</div>")
    o.append("<footer>Scores <code>v33_ironman_vlm_scores_bca4.csv</code>; run "
             "<code>v3/runs/ironman/20260830_0548/</code>; <code>prd/v3/v3.3/RESULTS.md</code> &sect;13&ndash;14."
             "</footer></div>" + LB + SCRIPT)
    dst = os.path.join(REPORT, "v33_failures.html")
    open(dst, "w").write("\n".join(o))
    print(dst, f"{os.path.getsize(dst)/1e6:.1f} MB · {len(bad)} failing cells · {len(by)} pairs · V {nV} · BCA4 {nB} · both {both}")


HEAD = """<title>v3.3 Iron Man — Failures</title><meta name='viewport' content='width=device-width,initial-scale=1'>
<style>:root{--bg:#0d0d10;--fg:#e8e8ea;--dim:#8a8a94;--line:#26262c;--acc:#7c5cff}*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.6 ui-sans-serif,-apple-system,"Segoe UI",Roboto,sans-serif}.wrap{max-width:1150px;margin:0 auto;padding:30px 26px}
h1{margin:0 0 6px;font-size:24px}h2{font-size:14px;margin:38px 0 6px;padding-top:12px;border-top:1px solid var(--line)}h2 .ar{font-size:12px;color:var(--dim);font-weight:400;margin-left:10px}
.lede{color:var(--dim);max-width:112ch;font-size:14px;margin:0 0 14px}.lede b{color:var(--fg)}
.lab{font-size:12px;color:var(--dim);margin:12px 0 4px}
.strip{display:grid;gap:6px}.s4{grid-template-columns:repeat(4,minmax(0,1fr));max-width:900px}
.pair{display:grid;grid-template-columns:1fr 1fr;gap:14px}
.cell{background:#15151b;border-radius:8px;padding:10px;display:grid;grid-template-columns:190px 1fr;gap:12px;align-items:start}
figure{margin:0}figure img{width:100%;display:block;background:#fff;border-radius:6px;cursor:zoom-in;aspect-ratio:3/4;object-fit:contain;border:3px solid transparent}
figure.bad img{border-color:#b43c3c}figure.ok img{border-color:#2c5c33}
figcaption{font-size:11px;color:var(--dim);text-align:center;padding:4px 2px}
.sc{font-size:11px;color:var(--dim)}.sc b{font-weight:600;color:#c9c9d2}.sc b.bad{color:#f0655a}.dim{color:var(--dim)}
.cell p{margin:6px 0 0;font-size:12.5px;color:#c9c9d2;grid-column:2}
.ph{background:#17171d;border:1px dashed var(--line);border-radius:6px;aspect-ratio:3/4;display:flex;align-items:center;justify-content:center;color:var(--dim)}
footer{margin:40px 0 20px;font-size:12px;color:var(--dim)}
#lb{position:fixed;inset:0;background:#000d;display:none;align-items:center;justify-content:center;z-index:9}#lb.on{display:flex}#lb img{max-width:96vw;max-height:92vh}#lbc{position:fixed;bottom:8px;color:#fff;font-size:13px}</style>"""
LB = "<div id='lb'><img id='lbi' alt=''><div id='lbc'></div></div>"
SCRIPT = """<script>document.addEventListener('click',e=>{const im=e.target.closest('figure img');if(!im)return;document.getElementById('lbi').src=im.getAttribute('src');document.getElementById('lbc').textContent=im.getAttribute('alt');document.getElementById('lb').classList.add('on');});
document.getElementById('lb').addEventListener('click',()=>document.getElementById('lb').classList.remove('on'));document.addEventListener('keydown',e=>{if(e.key==='Escape')document.getElementById('lb').classList.remove('on')});</script>"""

if __name__ == "__main__":
    main()
