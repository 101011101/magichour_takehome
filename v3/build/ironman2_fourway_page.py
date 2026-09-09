"""Four-arm comparison over the 200-pair matrix at seeds 46/47/48, labelled and in a
fixed column order: the v3.4 version (VEi), the true incumbent (BC, head correctly
subtracted), the v3.3 lock (V), and the incumbent as it was actually mis-built (BCA4).

VEi carries the reviewer's own verdict as a border (green clean / amber shippable /
red failure, from v34_im2_truth.json). The working assumption is that VEi stands: a
row is only voted when VEi failed and another arm did better.
  python3 v3/build/ironman2_fourway_page.py  -> v3/report/ironman2_fourway.html
"""
import csv, html, json, os
from PIL import Image

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
NEW = os.path.join(REPO, "v3", "runs", "v34", "ironman2")               # VEi, BC (correct)
OLD = os.path.join(REPO, "v3", "runs", "ironman", "20260830_0548")      # V, BCA4 (mis-built)
REPORT = os.path.join(REPO, "v3", "report"); IMG = os.path.join(REPORT, "img_im2four")
SEEDS = (46, 47, 48)
ARMS = ("VEi", "BC", "V", "BCA4")          # fixed column order, left to right
WHAT = {"VEi": "the v3.4 version", "BC": "the true incumbent",
        "V": "the v3.3 lock", "BCA4": "the mis-built incumbent"}
# arm -> (gen dir, filename token).  The old run's files say __BC__ but that arm is BCA4.
SRC = {"VEi": (os.path.join(NEW, "gen"), "VEi"), "BC": (os.path.join(NEW, "gen"), "BC"),
       "V": (os.path.join(OLD, "gen"), "V"), "BCA4": (os.path.join(OLD, "gen"), "BC")}
VD = {"CLEAN": ("clean", "&#10003; clean"), "MID": ("mid", "~ shippable"), "FAIL": ("fail", "&#10007; failure")}

missing = []


def thumb(path, name, cap, box=(320, 440)):
    """Emit a figure; `name` is the output basename (arms collide on source basename)."""
    if not os.path.exists(path):
        missing.append(path)
        return f"<figure><div class='ph'>&mdash;</div><figcaption>{cap}</figcaption></figure>"
    os.makedirs(IMG, exist_ok=True)
    o = os.path.join(IMG, name)
    if not os.path.exists(o):
        im = Image.open(path).convert("RGB"); im.thumbnail(box); im.save(o, quality=85, optimize=True)
    return (f"<figure><img src='img_im2four/{name}' alt='{html.escape(cap)}' loading='lazy'>"
            f"<figcaption>{cap}</figcaption></figure>")


def load_verdicts():
    try:
        return {tuple(k.split("|")): v for k, v in json.load(open(os.path.join(REPO, "v34_im2_truth.json"))).items()}
    except Exception:
        return {}


def main():
    verdict = load_verdicts()
    pairs = list(csv.DictReader(open(os.path.join(REPO, "v3", "colab", "matrix.csv"))))
    counts = {"FAIL": 0, "MID": 0, "CLEAN": 0}
    o = [HEAD, "<div class='wrap'>", BAR, "<h1>Iron man 2 &mdash; the four arms, side by side</h1>",
         "<p class='lede'>Same <b>200 pairs</b>, same three seeds (<b>46 / 47 / 48</b>), 600 cells per arm. "
         "The columns are always in the same order, left to right: "
         "<b class='c-VEi'>VEi</b> the v3.4 version &middot; <b class='c-BC'>BC</b> the true incumbent "
         "(head correctly subtracted) &middot; <b class='c-V'>V</b> the v3.3 lock &middot; "
         "<b class='c-BCA4'>BCA4</b> the incumbent as it was mis-built (bald head never removed).<br>"
         "<b>VEi carries your own audit</b> as its border &mdash; green clean, amber shippable, red failure. "
         "<b>VEi is assumed to stand</b>: only vote a row where VEi is red (or amber and you disagree) and "
         "another arm actually does better. Use the filter to jump straight to those rows.</p>"]

    for r in pairs:
        sid, p, g = r["set_id"], r["person"], r["garment"]
        vds = [verdict.get((sid, str(s)), "") for s in SEEDS]
        worst = "FAIL" if "FAIL" in vds else ("MID" if "MID" in vds else "CLEAN")
        o.append(f"<div class='pair' data-worst='{worst.lower()}'>")
        o.append(f"<h2 id='{html.escape(sid)}'>{html.escape(p)} wears {html.escape(g)}"
                 f"<span class='ar'>{html.escape(sid)}</span>"
                 f"<span class='pv pv-{worst.lower()}'>VEi worst seed: {VD[worst][1]}</span></h2>")
        o.append("<div class='strip s4'>"
                 + thumb(os.path.join(NEW, "inputs", f"{p}.jpg"), f"in_{p}.jpg", "person photograph")
                 + thumb(os.path.join(NEW, "inputs", f"{g}.jpg"), f"in_{g}.jpg", "garment photograph")
                 + thumb(os.path.join(NEW, "refs", f"{g}__VEi.jpg"), f"ref_{g}__VEi.jpg", "reference &middot; VEi")
                 + thumb(os.path.join(NEW, "refs", f"{g}__BC.jpg"), f"ref_{g}__BC.jpg", "reference &middot; BC")
                 + "</div>")

        for seed in SEEDS:
            vd = verdict.get((sid, str(seed)), "")
            if vd:
                counts[vd] += 1
            cells = []
            for a in ARMS:
                d, tok = SRC[a]
                cls = f"cl c-{a}" + (f" vd-{VD[vd][0]}" if a == "VEi" and vd else "")
                tag = (f"<span class='vt vt-{VD[vd][0]}'>{VD[vd][1]}</span>" if a == "VEi" and vd else "")
                cells.append(f"<div class='{cls}' data-arm='{a}'>" + thumb(
                    os.path.join(d, f"{sid}__{tok}__s{seed}.jpg"), f"{sid}__{a}__s{seed}.jpg",
                    f"<b class='c-{a}'>{a}</b> &middot; {WHAT[a]}{tag}") + "</div>")
            vote = ("<span class='vote' data-sid='" + html.escape(sid) + f"' data-seed='{seed}'>"
                    + "<button data-v='VEi'>VEi stands</button>"
                    + "".join(f"<button data-v='{a}'>{a} better</button>" for a in ("BC", "V", "BCA4"))
                    + "<button data-v='none'>all fail</button></span>"
                    + f"<button class='feat' data-sid='{html.escape(sid)}' data-seed='{seed}'>&#9733; report example</button>")
            o.append(f"<div class='sb' data-sid='{html.escape(sid)}' data-seed='{seed}' data-vd='{vd.lower()}'>"
                     f"<div class='sh'><span class='sn'>seed {seed}</span>{vote}</div>"
                     f"<div class='strip s4'>{''.join(cells)}</div></div>")
        o.append("</div>")

    o.append("<footer>Arms: VEi and BC from <code>v3/runs/v34/ironman2/</code>; V and BCA4 from "
             "<code>v3/runs/ironman/20260830_0548/</code> (whose <code>__BC__</code> files are the "
             "mis-built BCA4). VEi verdicts from <code>v34_im2_truth.json</code> "
             "(RESULTS &sect;10.5).</footer></div>")
    o.append(LB + f"<script>const COUNTS={json.dumps(counts)};</script>" + SCRIPT)
    dst = os.path.join(REPORT, "ironman2_fourway.html")
    open(dst, "w").write("\n".join(o))

    doc = open(dst).read()
    print(dst, f"{os.path.getsize(dst)/1e6:.1f} MB")
    print("pair headers   :", doc.count("<h2 id="))
    print("vote widgets   :", doc.count("<span class='vote'"))
    print("placeholders   :", doc.count("class='ph'"))
    print("VEi verdicts   :", counts, "=", sum(counts.values()))
    if missing:
        print("MISSING:", len(missing), missing[:10])


HEAD = """<title>Iron man 2 — Four arms</title><meta name='viewport' content='width=device-width,initial-scale=1'>
<style>:root{--bg:#0d0d10;--fg:#e8e8ea;--dim:#8a8a94;--line:#26262c;--acc:#7c5cff;--ok:#3fb950;--mid:#c9862c;--bad:#f0655a}*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.6 ui-sans-serif,-apple-system,"Segoe UI",Roboto,sans-serif}.wrap{max-width:1280px;margin:0 auto;padding:30px 26px}
h1{margin:0 0 6px;font-size:24px}h2{font-size:14px;margin:40px 0 8px;padding-top:12px;border-top:1px solid var(--line);display:flex;gap:10px;align-items:center;flex-wrap:wrap}
h2 .ar{font-size:11px;color:var(--dim);font-weight:400;font-family:ui-monospace,monospace}
.pv{font-size:11px;font-weight:600;padding:1px 8px;border-radius:20px;border:1px solid}
.pv-clean{color:var(--ok);border-color:#28502f}.pv-mid{color:var(--mid);border-color:#5c4520}.pv-fail{color:var(--bad);border-color:#6d2f2a}
.lede{color:var(--dim);max-width:112ch;font-size:14px;margin:0 0 14px}.lede b{color:var(--fg)}
.c-VEi{color:#a78bfa}.c-BC{color:#5eead4}.c-V{color:#93c5fd}.c-BCA4{color:#fcd34d}
.strip{display:grid;gap:8px;grid-template-columns:repeat(4,minmax(0,1fr))}
.sb{margin:10px 0 14px;padding:10px;background:#15151b;border-radius:8px}
.sh{display:flex;gap:12px;align-items:center;margin-bottom:8px}.sn{font-size:12px;color:var(--dim);font-family:ui-monospace,monospace}
figure{margin:0}figure img{width:100%;display:block;background:#fff;border-radius:6px;cursor:zoom-in;aspect-ratio:3/4;object-fit:contain;border:3px solid transparent}
.vd-clean img{border-color:var(--ok)}.vd-mid img{border-color:var(--mid)}.vd-fail img{border-color:var(--bad)}
.cl.win figure img{outline:3px solid var(--acc);outline-offset:2px}
figcaption{font-size:11px;color:var(--dim);text-align:center;padding:4px 2px}figcaption b{font-weight:700}
.vt{display:block;font-weight:600}.vt-clean{color:var(--ok)}.vt-mid{color:var(--mid)}.vt-fail{color:var(--bad)}
.vote{display:inline-flex;gap:5px;flex-wrap:wrap}.vote button{background:#1c1c24;color:var(--dim);border:1px solid var(--line);border-radius:5px;padding:3px 10px;font:inherit;font-size:11.5px;cursor:pointer}
.vote button:hover{color:var(--fg)}.vote button.on{background:#2a2a36;color:#fff;border-color:var(--acc)}
.bar{position:sticky;top:0;z-index:5;background:#0d0d10ee;backdrop-filter:blur(6px);border-bottom:1px solid var(--line);padding:10px 26px;margin:-30px -26px 16px;display:flex;gap:10px;align-items:center;flex-wrap:wrap;font-size:12.5px;color:var(--dim)}
.bar button{background:var(--acc);color:#fff;border:0;border-radius:6px;padding:6px 14px;font:inherit;cursor:pointer}
.bar button.sec{background:#1c1c24;color:var(--fg);border:1px solid var(--line)}.bar button.sec.on{border-color:var(--acc);color:#fff}
#tally{color:var(--fg);font-weight:600}
#csvbox{display:none;width:100%;height:120px;background:#15151b;color:var(--fg);border:1px solid var(--line);border-radius:6px;font:12px ui-monospace,monospace;padding:8px;margin-bottom:10px}
.ph{background:#17171d;border:1px dashed var(--line);border-radius:6px;aspect-ratio:3/4;display:flex;align-items:center;justify-content:center;color:var(--dim)}
body.f-fail .pair:not([data-worst='fail']){display:none}body.f-fail .sb:not([data-vd='fail']){display:none}
body.f-bad .pair[data-worst='clean']{display:none}body.f-bad .sb[data-vd='clean']{display:none}
.feat{background:#1c1c24;color:var(--dim);border:1px solid var(--line);border-radius:5px;padding:3px 10px;font:inherit;font-size:11.5px;cursor:pointer;margin-left:auto}.feat:hover{color:var(--fg)}.feat.on{background:#3a2f10;color:#fcd34d;border-color:#fcd34d}.sb.featured{box-shadow:0 0 0 2px #fcd34d55}body.f-feat .pair:not(.has-feat){display:none}body.f-feat .sb:not(.featured){display:none}
footer{margin:40px 0 20px;font-size:12px;color:var(--dim)}
#lb{position:fixed;inset:0;background:#000d;display:none;align-items:center;justify-content:center;z-index:9}#lb.on{display:flex}#lb img{max-width:96vw;max-height:92vh}#lbc{position:fixed;bottom:8px;color:#fff;font-size:13px}</style>"""
LB = "<div id='lb'><img id='lbi' alt=''><div id='lbc'></div></div>"
BAR = ("<div class='bar'><span>show:</span>"
       "<button id='f-fail' class='sec'>VEi failures only</button>"
       "<button id='f-bad' class='sec'>failures + shippable</button>"
       "<button id='f-all' class='sec on'>all 600</button>"
       "<button id='f-feat' class='sec'>&#9733; report examples</button>"
       "<button id='export'>Export CSV</button>"
       "<span id='tally'></span></div><textarea id='csvbox'></textarea>")
SCRIPT = """<script>
document.addEventListener('click',e=>{const im=e.target.closest('figure img');if(!im)return;document.getElementById('lbi').src=im.getAttribute('src');document.getElementById('lbc').textContent=im.getAttribute('alt');document.getElementById('lb').classList.add('on');});
document.getElementById('lb').addEventListener('click',()=>document.getElementById('lb').classList.remove('on'));document.addEventListener('keydown',e=>{if(e.key==='Escape')document.getElementById('lb').classList.remove('on')});
const F={'f-fail':'f-fail','f-bad':'f-bad','f-all':'','f-feat':'f-feat'};
Object.keys(F).forEach(id=>{document.getElementById(id).onclick=()=>{
  document.body.classList.remove('f-fail','f-bad','f-feat');
  if(F[id])document.body.classList.add(F[id]);
  Object.keys(F).forEach(x=>document.getElementById(x).classList.toggle('on',x===id));};});
const KEY='im2-fourway-v2';let votes={};try{votes=JSON.parse(localStorage.getItem(KEY)||'{}')}catch(e){}
const FKEY='im2-fourway-feature';let feats={};try{feats=JSON.parse(localStorage.getItem(FKEY)||'{}')}catch(e){}
const ARMS=['VEi','BC','V','BCA4'];const blocks=[...document.querySelectorAll('.sb')];
function paint(){const t={VEi:0,BC:0,V:0,BCA4:0,none:0};
 blocks.forEach(b=>{const v=votes[b.dataset.sid+'|'+b.dataset.seed]||'VEi';
  b.querySelectorAll('.vote button').forEach(x=>x.classList.toggle('on',x.dataset.v===v));
  b.querySelectorAll('.cl').forEach(c=>c.classList.toggle('win',c.dataset.arm===v));
  t[v]=(t[v]||0)+1;
  const on=!!feats[b.dataset.sid+'|'+b.dataset.seed];
  b.classList.toggle('featured',on);const fb=b.querySelector('.feat');if(fb)fb.classList.toggle('on',on);});
 document.querySelectorAll('.pair').forEach(p=>p.classList.toggle('has-feat',!!p.querySelector('.sb.featured')));
 const nfeat=Object.values(feats).filter(Boolean).length;
 const rescued=t.BC+t.V+t.BCA4;
 document.getElementById('tally').textContent=
   'VEi stands '+t.VEi+' · rescued by another arm '+rescued+' (BC '+t.BC+' · V '+t.V+' · BCA4 '+t.BCA4+') · all fail '+t.none
   +'  |  ★ '+nfeat+' report examples'
   +'  |  your audit: '+COUNTS.CLEAN+' clean · '+COUNTS.MID+' shippable · '+COUNTS.FAIL+' failures';}
document.addEventListener('click',e=>{const f=e.target.closest('.feat');if(!f)return;
 const k=f.dataset.sid+'|'+f.dataset.seed;feats[k]=!feats[k];
 try{localStorage.setItem(FKEY,JSON.stringify(feats))}catch(x){}paint();});
document.addEventListener('click',e=>{const b=e.target.closest('.vote button');if(!b)return;const w=b.closest('.vote');
 votes[w.dataset.sid+'|'+w.dataset.seed]=b.dataset.v;try{localStorage.setItem(KEY,JSON.stringify(votes))}catch(x){}paint();});
document.getElementById('export').onclick=()=>{let csv='set_id,seed,vei_verdict,best_arm,report_example\\n';
 blocks.forEach(b=>{const k=b.dataset.sid+'|'+b.dataset.seed;
  csv+=b.dataset.sid+','+b.dataset.seed+','+(b.dataset.vd||'')+','+(votes[k]||'VEi')+','+(feats[k]?'yes':'')+'\\n';});
 const box=document.getElementById('csvbox');box.style.display='block';box.value=csv;box.select();
 try{const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([csv],{type:'text/csv'}));a.download='im2_fourway_votes.csv';a.click();}catch(x){}};
paint();</script>"""

if __name__ == "__main__":
    main()
