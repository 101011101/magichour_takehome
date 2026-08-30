"""Turn an iron-man zip into a blinded review page with timing and cost tables.

  python3 v3/build/ironman_page.py v33_ironman_run_<stamp>.zip [--unblind] [--rate 0.689 --currency CAD]

--rate recomputes the measured cost from the recorded wall time at a corrected hourly
rate (the notebook's default was a placeholder); the recomputation is written back into
meta/cost.json with the original kept under "as_run".

Unpacks to v3/runs/ironman/<stamp>/, writes v3/report/v33_ironman.html and img_im/.
Per pair, per seed: the person, then the arms in a shuffled order labelled A/B; the
mapping is in key.csv beside the run, and on the page only with --unblind.
"""
import csv
import hashlib
import html
import json
import os
import random
import sys
import zipfile

from PIL import Image

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
REPORT = os.path.join(REPO, "v3", "report")
IMG = os.path.join(REPORT, "img_im")


def web(src, dst, width=420):
    if not os.path.exists(src):
        return None, None
    out, full = os.path.join(IMG, dst), os.path.join(IMG, dst.replace(".jpg", "@f.jpg"))
    if not os.path.exists(out):
        im = Image.open(src).convert("RGB")
        (im.resize((width, int(im.height * width / im.width)), Image.LANCZOS) if im.width > width else im).save(out, quality=88, optimize=True)
        im.save(full, quality=92, optimize=True)
    return "img_im/" + dst, "img_im/" + os.path.basename(full)


def fig(pair, cap, cls=""):
    src, full = pair
    if not src:
        return f"<figure class='miss'><div class='ph'>missing</div><figcaption>{cap}</figcaption></figure>"
    return (f"<figure class='{cls}'><img src='{src}' data-full='{full}' alt='{html.escape(cap)}' loading='lazy'>"
            f"<figcaption>{cap}</figcaption></figure>")


def main(zip_path, unblind=False, rate=None, currency="USD"):
    stamp = os.path.splitext(os.path.basename(zip_path))[0].replace("v33_ironman_run_", "")
    run = os.path.join(REPO, "v3", "runs", "ironman", stamp)
    if not os.path.isdir(run):
        os.makedirs(run, exist_ok=True)
        zipfile.ZipFile(zip_path).extractall(run)
    if os.path.isdir(os.path.join(run, "run")):
        run = os.path.join(run, "run")
    os.makedirs(IMG, exist_ok=True)
    meta = json.load(open(os.path.join(run, "meta", "run.json")))
    cost = json.load(open(os.path.join(run, "meta", "cost.json")))
    if rate is not None:
        cost.setdefault("as_run", {"gpu_usd_per_hour": cost.get("gpu_usd_per_hour"), "usd_measured": cost.get("usd_measured")})
        cost["gpu_rate_per_hour"], cost["currency"] = rate, currency
        cost["measured_cost"] = round(cost["wall_seconds"] / 3600 * rate, 3)
        cost["cost_per_pair_per_arm_per_seed"] = round(cost["measured_cost"] / max(cost["klein_calls"], 1), 4)
        json.dump(cost, open(os.path.join(run, "meta", "cost.json"), "w"), indent=1)
    cur = cost.get("currency", "USD"); rate_v = cost.get("gpu_rate_per_hour", cost.get("gpu_usd_per_hour"))
    measured = cost.get("measured_cost", cost.get("usd_measured"))
    rows = list(csv.DictReader(open(os.path.join(REPO, "v3", "testsets", "v3_full_matrix.csv"))))[: meta["pairs"]]
    arms, seeds = meta["arms"], meta["seeds"]
    rng = random.Random(int(hashlib.sha1(stamp.encode()).hexdigest(), 16) % 10**8)
    key = []
    o = [HEAD, "<div class='wrap'>"]
    o.append(f"<h1>Iron-man run {html.escape(stamp)}</h1>")
    o.append(f"<p class='lede'>{meta['pairs']} pairs &middot; arms {' / '.join(arms)} (blinded below) &middot; seeds {seeds} "
             f"&middot; self-hosted <code>{html.escape(str(meta['klein'].get('repo')))}</code> on "
             f"<code>{html.escape(str(meta['klein'].get('gpu')))}</code>.</p>")
    # timing + cost
    t = cost
    o.append("<h2 class='sec'>Time and cost</h2><table class='t'>")
    for k, v in [("klein calls", t["klein_calls"]), ("seconds per klein call (mean)", t["klein_seconds_per_call"]),
                 ("klein seconds, total", t["klein_seconds"]), ("model load, seconds", t.get("model_load_seconds")),
                 ("wall time, minutes", round(t["wall_seconds"] / 60, 1)),
                 (f"GPU rate, {cur}/hour", rate_v), (f"<b>{cur}, measured (wall time × rate)</b>", measured),
                 (f"{cur} per klein call, measured", t.get("cost_per_pair_per_arm_per_seed")),
                 ("USD, fal-equivalent at $0.015/call", t["usd_fal_equivalent"])]:
        o.append(f"<tr><td>{k}</td><td>{html.escape(str(v))}</td></tr>")
    o.append("</table><table class='t'><tr><th>arm</th><th>klein calls</th><th>klein seconds</th></tr>")
    for a, v in t["per_arm"].items():
        o.append(f"<tr><td>{a}</td><td>{v['klein_calls']}</td><td>{v['klein_seconds']}</td></tr>")
    o.append("</table><table class='t'><tr><th>stage / arm</th><th>mean seconds</th></tr>")
    for k, v in sorted(t["per_stage_mean_seconds"].items()):
        o.append(f"<tr><td>{html.escape(k)}</td><td>{v}</td></tr>")
    o.append("</table>")
    o.append("<div class='q'>Arm names are hidden and the order is shuffled per pair; the key is <code>key.csv</code> beside the run. "
             "Under each pair, click <b>A better / B better / tie / both fail</b> for every seed. Votes save in this browser as you go. "
             "<b>Export CSV</b> downloads <code>votes.csv</code> (set_id, seed, vote); if the download is blocked, the same CSV appears in the box to copy.</div>"
             "<div class='bar'><button id='export'>Export CSV</button> <button id='clear'>Clear votes</button> "
             "<span id='count'></span></div><textarea id='csvbox' placeholder='CSV appears here on export'></textarea>")
    for r in rows:
        sid, p, g = r["set_id"], r["person"], r["garment"]
        order = list(arms); rng.shuffle(order)
        labels = {a: chr(65 + i) for i, a in enumerate(order)}
        for a in arms:
            key.append({"set_id": sid, "arm": a, "label": labels[a]})
        o.append(f"<h2>{r['pair']} &middot; {html.escape(p)} wears {html.escape(g)}</h2>")
        cells = [fig(web(os.path.join(run, "inputs", f"{p}.jpg"), f"{p}__in.jpg"), "person"),
                 fig(web(os.path.join(run, "inputs", f"{g}.jpg"), f"{g}__in.jpg"), "garment photograph")]
        for seed in seeds:
            for a in order:
                lab = f"{labels[a]}" + (f" &middot; {a}" if unblind else "") + f"<span class='n'>seed {seed}</span>"
                cells.append(fig(web(os.path.join(run, "gen", f"{sid}__{a}__s{seed}.jpg"), f"{sid}__{a}__s{seed}.jpg"), lab))
        o.append(f"<div class='strip' style='grid-template-columns:repeat({min(len(cells), 8)},minmax(0,1fr))'>" + "".join(cells) + "</div>")
        btns = "".join(f"<div class='vote' data-sid='{html.escape(sid)}' data-seed='{seed}'><span class='vs'>seed {seed}:</span>"
                       + "".join(f"<button data-v='{v}'>{t}</button>" for v, t in [("A", "A better"), ("B", "B better"), ("tie", "tie"), ("fail", "both fail")])
                       + "</div>" for seed in seeds)
        o.append(f"<div class='votes'>{btns}</div>")
    o.append(FOOT + "</div>" + LB + SCRIPT)
    with open(os.path.join(os.path.dirname(run.rstrip('/')) if run.endswith('run') else run, "key.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["set_id", "arm", "label"]); w.writeheader(); w.writerows(key)
    dst = os.path.join(REPORT, "v33_ironman.html")
    open(dst, "w").write("\n".join(o))
    print(dst, f"({len(rows)} pairs, {len(key)} labelled cells; key beside the run)")


HEAD = """<title>Iron-man</title>
<meta name='viewport' content='width=device-width,initial-scale=1'>
<style>
:root{--bg:#0d0d10;--fg:#e8e8ea;--dim:#8a8a94;--line:#26262c;--acc:#7c5cff;--good:#3fb950}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.6 ui-sans-serif,-apple-system,"Segoe UI",Roboto,sans-serif}
.wrap{max-width:1620px;margin:0 auto;padding:30px 26px 0}
h1{margin:0 0 6px;font-size:25px}
h2{font-size:14px;margin:48px 0 8px;padding-top:14px;border-top:1px solid var(--line)}
h2.sec{font-size:20px;margin-top:40px;border-top:2px solid var(--acc)}
.lede{color:var(--dim);max-width:96ch;font-size:14px;margin:0 0 14px}
.q{border-left:3px solid var(--acc);padding:2px 0 2px 14px;margin:14px 0;max-width:98ch;font-size:13.5px;color:#c8c8d0}
table.t{border-collapse:collapse;margin:8px 0 14px;font-size:13px}table.t td,table.t th{border:1px solid var(--line);padding:4px 12px;text-align:left}
.strip{display:grid;gap:5px;margin-bottom:6px}
figure{margin:0}figure img{width:100%;display:block;background:#fff;border-radius:6px;cursor:zoom-in;aspect-ratio:3/4;object-fit:contain}
figcaption{font-size:11px;color:var(--dim);text-align:center;padding:5px 2px;line-height:1.4}
figcaption .n{display:block;font-size:9.5px;opacity:.85}
.ph{background:#17171d;border:1px dashed var(--line);border-radius:6px;aspect-ratio:3/4;display:flex;align-items:center;justify-content:center;color:var(--dim);font-size:11px}
#lb{display:none;position:fixed;inset:0;background:rgba(0,0,0,.96);z-index:99;align-items:center;justify-content:center;flex-direction:column;gap:10px;padding:16px}
#lb.on{display:flex}#lb img{max-width:96vw;max-height:92vh;object-fit:contain;background:#fff}
#lbc{color:var(--dim);font-size:13px}
footer{border-top:1px solid var(--line);margin-top:44px;padding:22px 0 30px;color:var(--dim);font-size:12.5px}
.votes{display:flex;flex-wrap:wrap;gap:14px;margin:4px 0 0}.vote{display:flex;gap:4px;align-items:center}.vs{font-size:11px;color:var(--dim);margin-right:4px}
.vote button{background:#17171d;color:var(--fg);border:1px solid var(--line);border-radius:5px;padding:3px 9px;font-size:12px;cursor:pointer}
.vote button.on{background:var(--acc);border-color:var(--acc);color:#fff}
.bar{position:sticky;top:0;background:var(--bg);padding:8px 0;z-index:5;border-bottom:1px solid var(--line)}
.bar button{background:#17171d;color:var(--fg);border:1px solid var(--acc);border-radius:5px;padding:5px 12px;font-size:13px;cursor:pointer}
#count{color:var(--dim);font-size:12px;margin-left:10px}
#csvbox{width:100%;height:70px;margin:8px 0 0;background:#17171d;color:var(--dim);border:1px solid var(--line);font:11px ui-monospace,monospace;display:none}
code{background:#1b1b22;padding:1px 5px;border-radius:4px;font-size:12px}
</style>
"""
FOOT = """<footer>Built by <code>v3/build/ironman_page.py</code> from the run zip; timings <code>meta/timings.csv</code>,
cost <code>meta/cost.json</code>, prompts <code>meta/run.json</code>. Protocol: <code>prd/v3/v3.3/SOLUTION.md</code> &sect;7.</footer>"""
LB = "<div id='lb'><img id='lbi' alt=''><div id='lbc'></div></div>"
SCRIPT = """<script>
document.addEventListener('click',e=>{const im=e.target.closest('figure img');if(!im)return;
document.getElementById('lbi').src=im.dataset.full||im.getAttribute('src');document.getElementById('lbc').textContent=im.getAttribute('alt');
document.getElementById('lb').classList.add('on');});
document.getElementById('lb').addEventListener('click',()=>document.getElementById('lb').classList.remove('on'));
document.addEventListener('keydown',e=>{if(e.key==='Escape')document.getElementById('lb').classList.remove('on')});
// ---- votes ----
const KEY='ironman-votes-'+location.pathname; let votes={}; try{votes=JSON.parse(localStorage.getItem(KEY)||'{}')}catch(e){}
const total=document.querySelectorAll('.vote').length;
function paint(){document.querySelectorAll('.vote').forEach(d=>{const k=d.dataset.sid+'|'+d.dataset.seed;
  d.querySelectorAll('button').forEach(b=>b.classList.toggle('on',votes[k]===b.dataset.v));});
  document.getElementById('count').textContent=Object.keys(votes).length+' / '+total+' scored';}
document.addEventListener('click',e=>{const b=e.target.closest('.vote button');if(!b)return;const d=b.closest('.vote');
  votes[d.dataset.sid+'|'+d.dataset.seed]=b.dataset.v;try{localStorage.setItem(KEY,JSON.stringify(votes))}catch(x){}paint();});
document.getElementById('export').onclick=()=>{let csv='set_id,seed,vote\\n';Object.keys(votes).sort().forEach(k=>{const [s,d]=k.split('|');csv+=s+','+d+','+votes[k]+'\\n';});
  const box=document.getElementById('csvbox');box.style.display='block';box.value=csv;box.select();
  try{const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([csv],{type:'text/csv'}));a.download='votes.csv';a.click();}catch(x){}};
document.getElementById('clear').onclick=()=>{if(confirm('Clear all votes?')){votes={};try{localStorage.removeItem(KEY)}catch(x){}paint();}};
paint();
</script>"""

if __name__ == "__main__":
    a = sys.argv
    rate = float(a[a.index("--rate") + 1]) if "--rate" in a else None
    cur = a[a.index("--currency") + 1] if "--currency" in a else "USD"
    main(a[1], "--unblind" in a, rate, cur)
