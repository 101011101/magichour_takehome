"""Blinded four-arm comparison over the 200-pair matrix at seeds 46/47/48: the v3.4
version (VEi), the true incumbent (BC, head correctly subtracted), the v3.3 lock (V),
and the incumbent as it was actually mis-built (BCA4, bald head never subtracted).
Arms are shuffled per pair and labelled A/B/C/D; the key is written beside the page.
  python3 v3/build/ironman2_fourway_page.py  -> v3/report/ironman2_fourway.html
"""
import csv, hashlib, html, json, os, random
from PIL import Image

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
NEW = os.path.join(REPO, "v3", "runs", "v34", "ironman2")               # VEi, BC (correct)
OLD = os.path.join(REPO, "v3", "runs", "ironman", "20260830_0548")      # V, BCA4 (mis-built)
REPORT = os.path.join(REPO, "v3", "report"); IMG = os.path.join(REPORT, "img_im2four")
SEEDS = (46, 47, 48)
ARMS = ("VEi", "BC", "V", "BCA4")
WHAT = {"VEi": "the v3.4 version", "BC": "the true incumbent",
        "V": "the v3.3 lock", "BCA4": "the mis-built incumbent"}
# arm -> (gen dir, filename token).  The old run's files say __BC__ but that arm is BCA4.
SRC = {"VEi": (os.path.join(NEW, "gen"), "VEi"), "BC": (os.path.join(NEW, "gen"), "BC"),
       "V": (os.path.join(OLD, "gen"), "V"), "BCA4": (os.path.join(OLD, "gen"), "BC")}

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


VERDICT = {}   # the reviewer's audit of every VEi cell: CLEAN / MID / FAIL
try:
    import json as _j
    VERDICT = {tuple(k.split("|")): v for k, v in _j.load(open(os.path.join(REPO, "v34_im2_truth.json"))).items()}
except Exception:
    pass


def main():
    pairs = list(csv.DictReader(open(os.path.join(REPO, "v3", "colab", "matrix.csv"))))
    key_rows, key_js = [], {}
    o = [HEAD, "<div class='wrap'>", BAR, "<h1>Iron man 2 &mdash; blinded four-arm comparison</h1>",
         "<p class='lede'>Four arms on the same <b>200 pairs</b> at the same three seeds "
         "(<b>46 / 47 / 48</b>) &mdash; 600 cells each, 2400 in all: the <b>v3.4 version</b>, the "
         "<b>true incumbent</b> (head correctly subtracted), the <b>v3.3 lock</b>, and the "
         "<b>incumbent as it was actually mis-built</b> (the bald head was never subtracted). "
         "Which is which is hidden: within each pair the four are shuffled into a fixed, "
         "rebuild-stable order and labelled only <b>A B C D</b>, so the same letter means "
         "different arms in different pairs. Vote the winner of each seed row &mdash; "
         "<b>A / B / C / D</b>, or <b>tie</b> (the default) when nothing separates them. "
         "The bar keeps a live tally resolved back to the real arm names, and "
         "<b>Reveal arms</b> unmasks every caption. Export the CSV when done.</p>"]

    for r in pairs:
        sid, p, g = r["set_id"], r["person"], r["garment"]
        rng = random.Random(int(hashlib.sha1(sid.encode()).hexdigest(), 16))
        order = list(ARMS); rng.shuffle(order)
        for i, a in enumerate(order):
            key_rows.append({"set_id": sid, "position": chr(65 + i), "arm": a})
        key_js[sid] = order

        o.append(f"<h2 id='{html.escape(sid)}'>{html.escape(p)} wears {html.escape(g)}"
                 f"<span class='ar'>{html.escape(sid)}</span></h2>")
        o.append("<div class='strip s4'>"
                 + thumb(os.path.join(NEW, "inputs", f"{p}.jpg"), f"in_{p}.jpg", "person photograph")
                 + thumb(os.path.join(NEW, "inputs", f"{g}.jpg"), f"in_{g}.jpg", "garment photograph")
                 + thumb(os.path.join(NEW, "refs", f"{g}__VEi.jpg"), f"ref_{g}__VEi.jpg",
                         "reference 1<span class='rv'> (VEi)</span>")
                 + thumb(os.path.join(NEW, "refs", f"{g}__BC.jpg"), f"ref_{g}__BC.jpg",
                         "reference 2<span class='rv'> (BC)</span>")
                 + "</div>")

        for seed in SEEDS:
            cells = []
            for i, a in enumerate(order):
                d, tok = SRC[a]
                pos = chr(65 + i)
                vd = VERDICT.get((sid, str(seed)), "") if a == "VEi" else ""
                cells.append(f"<div class='cl{' vd-' + vd.lower() if vd else ''}' data-pos='{pos}'>" + thumb(
                    os.path.join(d, f"{sid}__{tok}__s{seed}.jpg"), f"{sid}__{a}__s{seed}.jpg",
                    f"{pos}<span class='rv'> &middot; {a}</span>") + "</div>")
            vote = ("<span class='vote' data-sid='" + html.escape(sid) + f"' data-seed='{seed}'>"
                    + "".join(f"<button data-v='{v}'>{v}</button>" for v in ("A", "B", "C", "D", "tie"))
                    + "</span>")
            o.append(f"<div class='sb' data-sid='{html.escape(sid)}' data-seed='{seed}'>"
                     f"<div class='sh'><span class='sn'>seed {seed}</span>{vote}</div>"
                     f"<div class='strip s4'>{''.join(cells)}</div></div>")

    with open(os.path.join(REPORT, "ironman2_fourway_key.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["set_id", "position", "arm"]); w.writeheader(); w.writerows(key_rows)

    o.append("<footer>Arms: VEi and BC from <code>v3/runs/v34/ironman2/</code>; V and BCA4 from "
             "<code>v3/runs/ironman/20260830_0548/</code> (whose <code>__BC__</code> files are the "
             "mis-built BCA4). Key: <code>v3/report/ironman2_fourway_key.csv</code>.</footer></div>")
    o.append(LB + "<script>const KEYMAP=" + json.dumps(key_js, separators=(",", ":")) + ";</script>" + SCRIPT)
    dst = os.path.join(REPORT, "ironman2_fourway.html")
    open(dst, "w").write("\n".join(o))

    doc = open(dst).read()
    print(dst, f"{os.path.getsize(dst)/1e6:.1f} MB")
    print("pair headers   :", doc.count("<h2 id="))
    print("vote widgets   :", doc.count("<span class='vote'"))
    print("placeholders   :", doc.count("class='ph'"))
    if missing:
        print("MISSING:", len(missing), missing[:10])
    print("key rows       :", len(key_rows), "->", os.path.join(REPORT, "ironman2_fourway_key.csv"))


HEAD = """<title>Iron man 2 — Four-arm blind</title><meta name='viewport' content='width=device-width,initial-scale=1'>
<style>:root{--bg:#0d0d10;--fg:#e8e8ea;--dim:#8a8a94;--line:#26262c;--acc:#7c5cff}*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.6 ui-sans-serif,-apple-system,"Segoe UI",Roboto,sans-serif}.wrap{max-width:1280px;margin:0 auto;padding:30px 26px}
h1{margin:0 0 6px;font-size:24px}h2{font-size:14px;margin:40px 0 8px;padding-top:12px;border-top:1px solid var(--line)}h2 .ar{font-size:11px;color:var(--dim);font-weight:400;margin-left:10px;font-family:ui-monospace,monospace}
.lede{color:var(--dim);max-width:110ch;font-size:14px;margin:0 0 14px}.lede b{color:var(--fg)}
.strip{display:grid;gap:8px;grid-template-columns:repeat(4,minmax(0,1fr))}
.sb{margin:10px 0 14px;padding:10px;background:#15151b;border-radius:8px}
.sh{display:flex;gap:12px;align-items:center;margin-bottom:8px}.sn{font-size:12px;color:var(--dim);font-family:ui-monospace,monospace}
figure{margin:0}figure img{width:100%;display:block;background:#fff;border-radius:6px;cursor:zoom-in;aspect-ratio:3/4;object-fit:contain;border:3px solid transparent}
.cl.win figure img{border-color:#3fb950}
figcaption{font-size:11px;color:var(--dim);text-align:center;padding:4px 2px}
.rv{display:none}body.reveal .rv{display:inline;color:#c9c9d2}\nbody.verdicts .vd-clean img{border-color:#3fb950!important}body.verdicts .vd-mid img{border-color:#c9862c!important}body.verdicts .vd-fail img{border-color:#f0655a!important}body.verdicts .vd-clean figcaption:after{content:' ✓ my verdict: clean';color:#3fb950}body.verdicts .vd-mid figcaption:after{content:' ~ my verdict: shippable';color:#c9862c}body.verdicts .vd-fail figcaption:after{content:' ✗ my verdict: failure';color:#f0655a}
.vote{display:inline-flex;gap:5px}.vote button{background:#1c1c24;color:var(--dim);border:1px solid var(--line);border-radius:5px;padding:3px 12px;font:inherit;font-size:11.5px;cursor:pointer}
.vote button:hover{color:var(--fg)}.vote button.on{background:#2a2a36;color:#fff;border-color:var(--acc)}
.bar{position:sticky;top:0;z-index:5;background:#0d0d10ee;backdrop-filter:blur(6px);border-bottom:1px solid var(--line);padding:10px 26px;margin:-30px -26px 16px;display:flex;gap:14px;align-items:center;flex-wrap:wrap;font-size:12.5px;color:var(--dim)}
.bar button{background:var(--acc);color:#fff;border:0;border-radius:6px;padding:6px 14px;font:inherit;cursor:pointer}
.bar button.sec{background:#1c1c24;color:var(--fg);border:1px solid var(--line)}
#tally{color:var(--fg);font-weight:600}
#csvbox{display:none;width:100%;height:120px;background:#15151b;color:var(--fg);border:1px solid var(--line);border-radius:6px;font:12px ui-monospace,monospace;padding:8px;margin-bottom:10px}
.ph{background:#17171d;border:1px dashed var(--line);border-radius:6px;aspect-ratio:3/4;display:flex;align-items:center;justify-content:center;color:var(--dim)}
footer{margin:40px 0 20px;font-size:12px;color:var(--dim)}
#lb{position:fixed;inset:0;background:#000d;display:none;align-items:center;justify-content:center;z-index:9}#lb.on{display:flex}#lb img{max-width:96vw;max-height:92vh}#lbc{position:fixed;bottom:8px;color:#fff;font-size:13px}</style>"""
LB = "<div id='lb'><img id='lbi' alt=''><div id='lbc'></div></div>"
BAR = ("<div class='bar'><button id='export'>Export CSV</button>"
       "<button id='reveal' class='sec'>Reveal arms</button>"
       "<button id='verdicts' class='sec'>Show my VEi verdicts</button>"
       "<span id='tally'></span></div><textarea id='csvbox'></textarea>")
SCRIPT = """<script>
document.addEventListener('click',e=>{const im=e.target.closest('figure img');if(!im)return;document.getElementById('lbi').src=im.getAttribute('src');document.getElementById('lbc').textContent=im.getAttribute('alt');document.getElementById('lb').classList.add('on');});
document.getElementById('lb').addEventListener('click',()=>document.getElementById('lb').classList.remove('on'));document.addEventListener('keydown',e=>{if(e.key==='Escape')document.getElementById('lb').classList.remove('on')});
document.getElementById('reveal').onclick=()=>{const on=document.body.classList.toggle('reveal');document.getElementById('reveal').textContent=on?'Hide arms':'Reveal arms';};\ndocument.getElementById('verdicts').onclick=()=>{const on=document.body.classList.toggle('verdicts');document.getElementById('verdicts').textContent=on?'Hide my VEi verdicts':'Show my VEi verdicts';if(on&&!document.body.classList.contains('reveal')){document.body.classList.add('reveal');document.getElementById('reveal').textContent='Hide arms';}};
const KEY='im2-fourway';let votes={};try{votes=JSON.parse(localStorage.getItem(KEY)||'{}')}catch(e){}
const ARMS=['VEi','BC','V','BCA4'];const blocks=[...document.querySelectorAll('.sb')];
function paint(){const t={VEi:0,BC:0,V:0,BCA4:0,tie:0};
 blocks.forEach(b=>{const sid=b.dataset.sid,seed=b.dataset.seed;const v=votes[sid+'|'+seed]||'tie';
  b.querySelectorAll('.vote button').forEach(x=>x.classList.toggle('on',x.dataset.v===v));
  b.querySelectorAll('.cl').forEach(c=>c.classList.toggle('win',v!=='tie'&&c.dataset.pos===v));
  if(v==='tie'){t.tie++;}else{const arm=(KEYMAP[sid]||[])[v.charCodeAt(0)-65];if(arm)t[arm]++;else t.tie++;}});
 document.getElementById('tally').textContent=ARMS.map(a=>a+' '+t[a]).join(' · ')+' · tie '+t.tie+' of '+blocks.length;}
document.addEventListener('click',e=>{const b=e.target.closest('.vote button');if(!b)return;const w=b.closest('.vote');
 votes[w.dataset.sid+'|'+w.dataset.seed]=b.dataset.v;try{localStorage.setItem(KEY,JSON.stringify(votes))}catch(x){}paint();});
document.getElementById('export').onclick=()=>{let csv='set_id,seed,pick_position,pick_arm\\n';
 blocks.forEach(b=>{const sid=b.dataset.sid,seed=b.dataset.seed;const v=votes[sid+'|'+seed]||'tie';
  const arm=v==='tie'?'tie':((KEYMAP[sid]||[])[v.charCodeAt(0)-65]||'');
  csv+=sid+','+seed+','+v+','+arm+'\\n';});
 const box=document.getElementById('csvbox');box.style.display='block';box.value=csv;box.select();
 try{const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([csv],{type:'text/csv'}));a.download='im2_fourway_votes.csv';a.click();}catch(x){}};
paint();</script>"""

if __name__ == "__main__":
    main()
