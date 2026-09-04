"""v3.4 A100 run page: failure set and controls, per seed the new A100 output (no cut, seeds
49/50/51) beside the original scored A100 output (46/47/48) and fal's (no cut, 46/47/48).
Fail toggles on the new cells (default pass), CSV export.
  python3 v3/build/v34_a100_page.py <run_dir> [--embed out]"""
import base64, csv, html, io, os, sys
from PIL import Image
REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
IM = os.path.join(REPO, "v3", "runs", "ironman", "20260830_0548"); FA = os.path.join(REPO, "v3", "runs", "v34", "linkA"); FB = os.path.join(REPO, "v3", "runs", "v34", "linkB_controls")
REPORT = os.path.join(REPO, "v3", "report"); IMG = os.path.join(REPORT, "img_v34c"); EMBED = None
def src(path, w=300):
    if not os.path.exists(path): return None
    im = Image.open(path).convert("RGB"); im.thumbnail((w, 420))
    if EMBED:
        b = io.BytesIO(); im.save(b, "JPEG", quality=70, optimize=True); return "data:image/jpeg;base64," + base64.b64encode(b.getvalue()).decode()
    os.makedirs(IMG, exist_ok=True); o = os.path.join(IMG, os.path.basename(os.path.dirname(os.path.dirname(path)))[:6] + "_" + os.path.basename(path).replace("__", "_"))
    if not os.path.exists(o): im.save(o, quality=85, optimize=True)
    return "img_v34c/" + os.path.basename(o)
def fig(path, cap, cls=""):
    s = src(path); return f"<figure class='{cls}'><img src='{s}' alt='{html.escape(cap)}' loading='lazy'><figcaption>{cap}</figcaption></figure>" if s else f"<figure><div class='ph'>&mdash;</div><figcaption>{cap}</figcaption></figure>"
LC = os.path.join(REPO, "v3", "runs", "v34", "v34_a100_nocut_20260901_0323")   # link C (Vnc, 49/50/51)
LD = os.path.join(REPO, "v3", "runs", "v34", "v34_a100_v34_20260904_0458")     # link D (V34, 49/50/51)
LE = os.path.join(REPO, "v3", "runs", "v34", "v34_a100_ve_20260904_0611")      # link E (VE, 49/50/51)


def main(run, embed=None, arm="Vnc"):
    global EMBED; EMBED = embed
    o = [HEAD, "<div class='wrap'>", BAR, "<h1>v3.4 on the A100 &mdash; no ankle cut, new seeds</h1>",
         "<p class='lede'>The locked version with the ankle cut removed, seeds <b>49/50/51</b>, self-hosted klein 4B on an A100. Two matrices: the 31-pair v3.3 failure set and the 30 clean controls. "
         "Per seed row: <b>new A100</b> (this run) &middot; <b>original A100</b> (seed 46/47/48, the cell the reviewer scored) &middot; <b>fal</b> (no cut, same seed number, links A/B). "
         "Mark any new-A100 cell that fails; default pass.</p>"]
    if arm == "VA":
        o[-1] = o[-1].replace("Mark any new-A100 cell that fails; default pass.",
                              "Columns per seed row, newest first: <b>LATEST &mdash; VA</b> (algorithmic 1 MP inputs, this run) &middot; "
                              "<b>VE</b> (klein-upscaled ref, link E) &middot; <b>V34</b> (small ref, link D) &middot; "
                              "<b>original A100</b> (the scored cell) &middot; <b>fal</b> (the benchmark). Per row, vote the winner: "
                              "<b>LATEST</b> &middot; <b>VE</b> &middot; <b>V34</b> &middot; <b>ORIGINAL</b> &middot; <b>tie</b> (default) — the winner gets the green border.")
    elif arm == "VE":
        o[-1] = o[-1].replace("Mark any new-A100 cell that fails; default pass.",
                              "Columns per seed row, newest first: <b>LATEST &mdash; VE</b> (1 MP ref, fal canvas, this run) &middot; "
                              "<b>LAST &mdash; V34</b> (small ref, link D) &middot; <b>Vnc</b> (v3.3 canvas, link C) &middot; "
                              "<b>original A100</b> (the scored cell) &middot; <b>fal</b> (link A, the benchmark). Per row, vote the winner: "
                              "<b>LATEST</b> &middot; <b>LAST</b> &middot; <b>ORIGINAL</b> &middot; <b>tie</b> (default) — the winner gets the green border.")
    elif arm == "V34":
        o[-1] = o[-1].replace("Mark any new-A100 cell that fails; default pass.",
                              "Fourth column: <b>fal</b> (no cut, s46/47/48, link A) &mdash; the benchmark. Mark each V34 cell: "
                              "<b>&gt;fal &middot; pass</b> (default) &middot; <b>&gt;fal &middot; FAIL</b> (fails, but no worse than fal's) &middot; <b>worse than fal</b>.")
    for title, mat, fal in (("Failure set (31 pairs)", "v34_failures.csv", FA), ("Controls (30 pairs)", "v34_controls.csv", FB)):
        rows = list(csv.DictReader(open(os.path.join(REPO, "v3", "testsets", mat))))
        o.append(f"<h2 class='sec'>{title}</h2>")
        for r in rows:
            sid, p, g = r["set_id"], r["person"], r["garment"]
            if not any(os.path.exists(os.path.join(run, "gen", f"{sid}__{arm}__s{s}.jpg")) for s in (49, 50, 51)):
                continue   # a reference alone (shared garment) is not a row
            o.append(f"<h2>{html.escape(p)} wears {html.escape(g)}<span class='ar'>{html.escape(r.get('class',''))} &middot; original verdicts {r['v46']} / {r['v47']} / {r['v48']}</span></h2>")
            o.append("<div class='strip s3'>" + fig(os.path.join(IM, "inputs", f"{p}.jpg"), "person") + fig(os.path.join(IM, "inputs", f"{g}.jpg"), "garment photograph") + fig(os.path.join(run, "refs", f"{g}__{arm}.jpg"), "reference, uncut (this run)") + "</div>")
            for new, old in ((49, 46), (50, 47), (51, 48)):
                mine = fig(os.path.join(run, "gen", f"{sid}__{arm}__s{new}.jpg"),
                           {"VE": f"<b>LATEST &mdash; VE</b> s{new} &middot; 1 MP ref, fal canvas",
                            "VA": f"<b>LATEST &mdash; VA</b> s{new} &middot; algorithmic 1 MP inputs"}.get(
                               arm, f"<b>{arm}</b> s{new}" + (" &mdash; no cut, fal canvas" if arm == "V34" else " &mdash; no cut")), "ship")
                orig = fig(os.path.join(IM, "gen", f"{sid}__V__s{old}.jpg"), f"original A100 s{old} &mdash; scored {r[f'v{old}']}", "bad" if r[f"v{old}"] in ("BC", "fail") else "")
                bench = fig(os.path.join(fal, "gen", f"{sid}__Vnc__s{old}.jpg"), f"fal s{old} &mdash; the benchmark")
                if arm == "VA":
                    cells, cls = (mine
                                  + fig(os.path.join(LE, "gen", f"{sid}__VE__s{new}.jpg"), f"VE s{new} &middot; klein-upscaled ref (link E)")
                                  + fig(os.path.join(LD, "gen", f"{sid}__V34__s{new}.jpg"), f"V34 s{new} &middot; small ref (link D)")
                                  + orig + bench), "s5"
                elif arm == "VE":
                    cells, cls = (mine
                                  + fig(os.path.join(LD, "gen", f"{sid}__V34__s{new}.jpg"), f"<b>LAST &mdash; V34</b> s{new} &middot; small ref (link D)")
                                  + fig(os.path.join(LC, "gen", f"{sid}__Vnc__s{new}.jpg"), f"Vnc s{new} &middot; v3.3 canvas (link C)")
                                  + orig + bench), "s5"
                elif arm == "V34":
                    cells, cls = mine + orig + fig(os.path.join(LC, "gen", f"{sid}__Vnc__s{new}.jpg"), f"link C: no cut, v3.3 canvas, s{new}") + bench, "s4"
                else:
                    cells, cls = mine + orig + fig(os.path.join(fal, "gen", f"{sid}__Vnc__s{old}.jpg"), f"fal s{old}, no cut"), "s3"
                if arm == "VA":   # head-to-head across the history (data-fig = column to highlight)
                    mk = ("<button data-m='latest' data-fig='0'>LATEST</button><button data-m='ve' data-fig='1'>VE</button>"
                          "<button data-m='v34' data-fig='2'>V34</button><button data-m='original' data-fig='3'>ORIGINAL</button><button data-m='tie' class='on'>tie</button>")
                elif arm == "VE":   # head-to-head: which cell wins the row (data-fig = column to highlight)
                    mk = ("<button data-m='latest' data-fig='0'>LATEST</button><button data-m='last' data-fig='1'>LAST</button>"
                          "<button data-m='original' data-fig='3'>ORIGINAL</button><button data-m='tie' class='on'>tie</button>")
                elif arm == "V34":
                    mk = "<button data-m='pass' class='on'>&gt;fal &middot; pass</button><button data-m='fail_better'>&gt;fal &middot; FAIL</button><button data-m='worse'>worse than fal</button>"
                else:
                    mk = "<button data-m='pass' class='on'>pass</button><button data-m='fail'>FAIL</button>"
                dd = " data-def='tie'" if arm in ("VE", "VA") else ""
                o.append(f"<div class='lab'>seed {new} (new) &middot; {old} (original)<span class='mk' data-sid='{html.escape(sid)}' data-seed='{new}'{dd}>{mk}</span></div><div class='strip {cls}'>"
                         + cells + "</div>")
    o.append(FOOT + "</div>" + LB + SCRIPT)
    dst = embed or os.path.join(REPORT, "v34_a100.html" if arm == "Vnc" else f"v34_a100_{arm}.html"); open(dst, "w").write("\n".join(o)); print(dst, f"{os.path.getsize(dst)/1e6:.1f} MB")
BAR = """<div class='bar'><button id='export'>Export CSV</button><span id='count'></span></div><textarea id='csvbox'></textarea>"""
HEAD = """<title>A100, New Seeds, No Cut</title><meta name='viewport' content='width=device-width,initial-scale=1'>
<style>:root{--bg:#0d0d10;--fg:#e8e8ea;--dim:#8a8a94;--line:#26262c;--acc:#7c5cff;--good:#3fb950;--bad:#f0655a}*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.6 ui-sans-serif,-apple-system,"Segoe UI",Roboto,sans-serif}.wrap{max-width:1300px;margin:0 auto;padding:30px 26px 0}
h1{margin:0 0 6px;font-size:25px}h2{font-size:14px;margin:40px 0 6px;padding-top:12px;border-top:1px solid var(--line);display:flex;gap:10px;align-items:center;flex-wrap:wrap}h2.sec{font-size:20px;margin-top:56px;border-top:2px solid var(--acc)}h2 .ar{font-size:12px;color:var(--dim);font-weight:400}
.lede{color:var(--dim);max-width:100ch;font-size:14px;margin:0 0 14px}.lede b{color:var(--fg)}.lab{font-size:12px;color:var(--dim);margin:10px 0 4px;display:flex;gap:10px;align-items:center}
.strip{display:grid;gap:5px}.s3{grid-template-columns:repeat(3,minmax(0,1fr));max-width:900px}.s4{grid-template-columns:repeat(4,minmax(0,1fr));max-width:1200px}.s5{grid-template-columns:repeat(5,minmax(0,1fr));max-width:1300px}
figure{margin:0}figure img{width:100%;display:block;background:#fff;border-radius:6px;cursor:zoom-in;aspect-ratio:3/4;object-fit:contain;border:3px solid transparent}figure.ship img{border-color:#2c5c33}figure.bad img{border-color:#7a3a33}figure.failed img{border-color:#b43c3c}figure.warn img{border-color:#c9862c}
figcaption{font-size:11px;color:var(--dim);text-align:center;padding:5px 2px}.ph{background:#17171d;border:1px dashed var(--line);border-radius:6px;aspect-ratio:3/4;display:flex;align-items:center;justify-content:center;color:var(--dim)}
.bar{position:sticky;top:0;background:var(--bg);padding:8px 0;z-index:5;border-bottom:1px solid var(--line);display:flex;gap:10px;align-items:center}.bar button{background:#17171d;color:var(--fg);border:1px solid var(--acc);border-radius:5px;padding:5px 12px;cursor:pointer}
#count{color:var(--dim);font-size:12px}#csvbox{width:100%;height:50px;margin:6px 0 0;background:#17171d;color:var(--dim);border:1px solid var(--line);font:11px ui-monospace,monospace;display:none}
.mk button{background:#17171d;color:var(--fg);border:1px solid var(--line);border-radius:5px;padding:3px 9px;font-size:11px;cursor:pointer;margin-left:4px}.mk button.on{background:#3a3a55;border-color:#8a8ad0}.mk button[data-m='fail'].on{background:#4d1f1f;border-color:#b43c3c}
#lb{display:none;position:fixed;inset:0;background:rgba(0,0,0,.96);z-index:99;align-items:center;justify-content:center;flex-direction:column;gap:10px;padding:16px}#lb.on{display:flex}#lb img{max-width:96vw;max-height:92vh;object-fit:contain;background:#fff}#lbc{color:var(--dim);font-size:13px}
footer{border-top:1px solid var(--line);margin-top:44px;padding:22px 0 30px;color:var(--dim);font-size:12.5px}code{background:#1b1b22;padding:1px 5px;border-radius:4px;font-size:12px}</style>"""
FOOT = """<footer>Run <code>v3/colab/v34_a100.ipynb</code> (A100, seeds 49/50/51, no cut); outputs <code>v3/runs/v34/v34_a100_nocut_*/</code>; matrices <code>v34_failures.csv</code>, <code>v34_controls.csv</code>. <code>prd/v3/v3.4/RESULTS.md</code> &sect;3.</footer>"""
LB = "<div id='lb'><img id='lbi' alt=''><div id='lbc'></div></div>"
SCRIPT = """<script>document.addEventListener('click',e=>{const im=e.target.closest('figure img');if(!im)return;document.getElementById('lbi').src=im.getAttribute('src');document.getElementById('lbc').textContent=im.getAttribute('alt');document.getElementById('lb').classList.add('on');});
document.getElementById('lb').addEventListener('click',()=>document.getElementById('lb').classList.remove('on'));document.addEventListener('keydown',e=>{if(e.key==='Escape')document.getElementById('lb').classList.remove('on')});
const KEY='v34-a100-best-'+location.pathname;let marks={};try{marks=JSON.parse(localStorage.getItem(KEY)||'{}')}catch(e){}
const mks=[...document.querySelectorAll('.mk')];
function paint(){const tally={};mks.forEach(m=>{const k=m.dataset.sid+'|'+m.dataset.seed;const v=marks[k]||m.dataset.def||'pass';m.querySelectorAll('button').forEach(b=>b.classList.toggle('on',b.dataset.m===v));
 const figs=[...m.closest('.lab').nextElementSibling.querySelectorAll('figure')];figs.forEach(f=>f.classList.remove('ship','failed','warn'));
 const b=m.querySelector("button[data-m='"+v+"']");
 if(b&&b.dataset.fig!==undefined){figs[+b.dataset.fig].classList.add('ship');}
 else{figs[0].classList.toggle('failed',v==='fail'||v==='worse');figs[0].classList.toggle('warn',v==='fail_better');figs[0].classList.toggle('ship',v==='pass');}
 tally[v]=(tally[v]||0)+1;});
 document.getElementById('count').textContent=Object.entries(tally).map(([a,c])=>c+' '+a).join(' · ')+', of '+mks.length;}
document.addEventListener('click',e=>{const b=e.target.closest('.mk button');if(!b)return;const m=b.closest('.mk');marks[m.dataset.sid+'|'+m.dataset.seed]=b.dataset.m;try{localStorage.setItem(KEY,JSON.stringify(marks))}catch(x){}paint();});
document.getElementById('export').onclick=()=>{let csv='set_id,seed,verdict\\n';mks.forEach(m=>{const k=m.dataset.sid+'|'+m.dataset.seed;csv+=m.dataset.sid+','+m.dataset.seed+','+(marks[k]||m.dataset.def||'pass')+'\\n';});
 const box=document.getElementById('csvbox');box.style.display='block';box.value=csv;box.select();try{const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([csv],{type:'text/csv'}));a.download='v34_a100_marks.csv';a.click();}catch(x){}};
paint();</script>"""
if __name__ == "__main__":
    a = sys.argv
    main(a[1], a[a.index("--embed") + 1] if "--embed" in a else None, a[a.index("--arm") + 1] if "--arm" in a else "Vnc")
