"""Build the v3.5 link-C page: six arms per cell, on the pairs either record marks hard.

Per pair, one row per arm — the reference call 2 was given, then that arm's output at each
seed — so the reference and what it produced are never more than one glance apart. The two
failure records ride along on every card (`v3.4 lock` and `v3.3`, per seed), because a cell
that works here is a failure reached, not a fresh sample.

The page is a comparison instrument: arms toggle off so `VEic` and `M1qc` can sit adjacent,
the ankle-cut arms hide in one click, and the provenance and class filters isolate a
question. The per-seed vote exports as CSV for the readout in prd/v3/v3.5/RESULTS.md.

  python3 v3/build/v35_linkC_page.py [run_dir]      default v3/runs/v35/linkC

Unzip the Colab bundle into that directory first:
  mkdir -p v3/runs/v35/linkC && unzip -q ~/Downloads/v35_linkC_*.zip -d v3/runs/v35/linkC
"""
import csv
import html
import json
import os
import sys

from PIL import Image

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RUN = sys.argv[1] if len(sys.argv) > 1 else os.path.join(REPO, "v3", "runs", "v35", "linkC")
SET = os.path.join(REPO, "v3", "testsets", "v35_linkC.csv")
REPORT = os.path.join(REPO, "v3", "report")
IMG = os.path.join(REPORT, "img_v35c")
OUTP = os.path.join(REPORT, "v35_linkC.html")

# arm, label, the one line that says what it is, reference stem, default-on
ARMS = [
    ("VEi",    "VEi",    "the v3.4 lock, as shipped - head kept",         "VEi",    True),
    ("BC",     "BC",     "v3.1's incumbent - bald pass, V2 crop",         "BC",     True),
    ("VEic",   "VEic",   "the lock's reference, mannequin head cut off",  "VEic",   True),
    ("M1qbc",  "M1qbc",  "re-pose + bald, head cut off - the target",     "M1qbc",  True),
    ("VEica",  "VEica",  "VEic + the ankle cut",                          "VEica",  True),
    ("M1qbca", "M1qbca", "M1qbc + the ankle cut",                         "M1qbca", True),
    # the pre-bald re-pose arm: dropped as an arm (hair survives on the garment), kept
    # here so an earlier run's cells still render if its zip is extracted alongside
    ("M1qc",   "M1qc",   "re-pose without bald - superseded",             "M1qc",   False),
    ("M1qca",  "M1qca",  "M1qc + the ankle cut - superseded",             "M1qca",  False),
]
VOTE = [a[0] for a in ARMS] + ["none"]


def web(src, dst, width=460):
    if not os.path.exists(src):
        return None, None
    out, full = os.path.join(IMG, dst), os.path.join(IMG, dst.replace(".jpg", "@full.jpg"))
    im = None
    if not os.path.exists(out):
        im = Image.open(src).convert("RGB")
        t = im.resize((width, int(im.height * width / im.width)), Image.LANCZOS) if im.width > width else im
        t.save(out, quality=90, optimize=True)
    if not os.path.exists(full):
        im = im or Image.open(src).convert("RGB")
        im.save(full, quality=94, optimize=True)
    return "img_v35c/" + dst, "img_v35c/" + os.path.basename(full)


def main():
    gen = os.path.join(RUN, "gen")
    if not os.path.isdir(gen):
        raise SystemExit(f"no run at {RUN}\n  unzip the Colab bundle first:\n"
                         f"  mkdir -p {os.path.relpath(RUN, REPO)} && "
                         f"unzip -q ~/Downloads/v35_linkC_*.zip -d {os.path.relpath(RUN, REPO)}")
    os.makedirs(IMG, exist_ok=True)
    rows = {r["set_id"]: r for r in csv.DictReader(open(SET))}
    files = os.listdir(gen)
    seeds = sorted({int(f.rsplit("__s", 1)[1][:-4]) for f in files if "__s" in f})
    present = {f.split("__")[-2] for f in files if f.count("__") >= 2}
    arms = [a for a in ARMS if a[0] in present]
    made = [s for s in rows if any(f.startswith(s + "__") for f in files)]
    made.sort(key=lambda s: (rows[s]["source"] != "both", rows[s]["source"], s))

    mp = os.path.join(RUN, "meta", "prompts_v35.json")
    meta = json.load(open(mp)) if os.path.exists(mp) else {}
    rp = os.path.join(RUN, "meta", "run_v35.json")
    runmeta = json.load(open(rp)) if os.path.exists(rp) else {}

    cards, ncell = [], 0
    for sid in made:
        r = rows[sid]
        pt, pf = web(os.path.join(RUN, "inputs", f"{r['person']}.jpg"), f"{r['person']}__p.jpg", 300)
        ct, cf = web(os.path.join(RUN, "inputs", f"{r['garment']}__A4.jpg"), f"{r['garment']}__a4.jpg", 300)
        gmeta = meta.get(r["garment"], {})

        def badges(prefix, keys, label):
            got = [(k, r.get(k, "")) for k in keys if r.get(k, "")]
            if not got:
                return ""
            return (f"<span class='vd'><i>{label}</i>" + "".join(
                f"<span class='v v-{v.lower()}'>s{k[-2:]} {v}</span>" for k, v in got) + "</span>")

        arm_rows = []
        for arm, lab, ch, refstem, _ in arms:
            rt, rf = web(os.path.join(RUN, "refs", f"{r['garment']}__{refstem}.jpg"),
                         f"{r['garment']}__{refstem}__ref.jpg", 300)
            cells = []
            for s in seeds:
                ot, of = web(os.path.join(gen, f"{sid}__{arm}__s{s}.jpg"), f"{sid}__{arm}__s{s}.jpg")
                ncell += ot is not None
                cells.append(
                    f"<figure class='out' data-seed='{s}'><img src='{ot}' data-full='{of}' "
                    f"alt='{html.escape(sid)} {arm} s{s}' loading='lazy'>"
                    f"<figcaption>s{s}</figcaption></figure>" if ot else
                    f"<figure class='out' data-seed='{s}'><div class='miss'>—</div>"
                    f"<figcaption>s{s}</figcaption></figure>")
            ank = gmeta.get(f"{arm}_ankle_row")
            note = ("<span class='n'>ankle cut: no ankles in frame, no-op</span>"
                    if arm.endswith("a") and f"{arm}_ankle_row" in gmeta and ank is None else
                    f"<span class='n'>ankle row {ank}</span>" if ank else "")
            arm_rows.append(
                f"<div class='arm a-{arm}{' hero' if arm in ('VEic', 'M1qbc') else ''}'>"
                f"<div class='ah'><b>{lab}</b><span>{html.escape(ch)}</span>{note}</div>"
                + (f"<figure class='ref'><img src='{rt}' data-full='{rf}' "
                   f"alt='{html.escape(r['garment'])} {refstem}' loading='lazy'>"
                   "<figcaption>reference</figcaption></figure>"
                   if rt else "<figure class='ref'><div class='miss'>no ref</div>"
                              "<figcaption>reference</figcaption></figure>")
                + f"<div class='outs'>{''.join(cells)}</div></div>")

        votes = "".join(
            f"<span class='vote' data-sid='{html.escape(sid)}' data-seed='{s}' "
            f"data-lock='{r.get(f'lock{s}', '')}' data-v33='{r.get(f'v33_{s}', '')}'>s{s}"
            + "".join(f"<button data-v='{v}'>{v}</button>" for v in VOTE) + "</span>"
            for s in seeds)
        cards.append(
            f"<div class='card' data-sid='{html.escape(sid)}' data-source='{r['source']}' "
            f"data-class='{r['class'] or 'none'}'>"
            f"<div class='ch'><b>{html.escape(sid)}</b>"
            f"<span class='t s-{r['source']}'>{r['source']}</span>"
            + (f"<span class='t'>{r['class']}</span>" if r["class"] else "")
            + badges("lock", ["lock46", "lock47", "lock48"], "v3.4 lock")
            + badges("v33", ["v33_46", "v33_47", "v33_48"], "v3.3")
            + "</div>"
            f"<div class='body'><div class='src'>"
            f"<figure><img src='{pt}' data-full='{pf}' alt='{html.escape(r['person'])} person' "
            "loading='lazy'><figcaption>person (image 1)</figcaption></figure>"
            f"<figure><img src='{ct}' data-full='{cf}' alt='{html.escape(r['garment'])} crop' "
            "loading='lazy'><figcaption>A4 crop</figcaption></figure>"
            f"<div class='votes'>{votes}</div></div>"
            f"<div class='arms'>{''.join(arm_rows)}</div></div></div>")

    toggles = "".join(
        f"<label class='cb'><input type='checkbox' data-arm='{a}' checked>{a}</label>"
        for a, _, _, _, _ in arms)
    o = [HEAD, "<div class='wrap'>", LEDE,
         TOOLBAR.replace("{{ARMS}}", toggles),
         f"<div class='grid'>{''.join(cards)}</div>",
         f"<footer>{len(made)} of {len(rows)} pairs &middot; {len(arms)} arms &times; "
         f"{len(seeds)} seeds &middot; {ncell} cells &middot; "
         + (f"{runmeta.get('klein', {}).get('gpu', 'self-hosted klein')} &middot; "
            if runmeta else "")
         + f"order: <code>{html.escape(runmeta.get('order', 'call 1 -> re-crop -> head crop -> [ankle cut] -> SR -> call 2'))}</code>"
         f" &middot; set: <code>v3/testsets/v35_linkC.csv</code> &mdash; the union of the "
         "v3.4 lock's and v3.3's failure records &middot; <code>VEi</code> and <code>BC</code>"
         " cells are the iron-man 2 originals, not redraws &middot; rebuild: "
         "<code>python3 v3/build/v35_linkC_page.py</code>.</footer></div>", LB, SCRIPT]
    open(OUTP, "w").write("\n".join(o))
    print(f"v3/report/v35_linkC.html  ({len(made)} pairs x {len(arms)} arms x {len(seeds)} seeds, {ncell} cells)")


HEAD = """<title>v3.5 link C - six arms on the pairs that fail</title>
<meta name='viewport' content='width=device-width,initial-scale=1'>
<style>
:root{--bg:#0d0d10;--fg:#e8e8ea;--dim:#8a8a94;--line:#26262c;--acc:#7c5cff;--mid:#d29922}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
 font:15px/1.6 ui-sans-serif,-apple-system,"Segoe UI",Roboto,sans-serif}
.wrap{max-width:1900px;margin:0 auto;padding:26px 22px 0}
h1{margin:0 0 6px;font-size:25px}
.lede{color:var(--dim);max-width:96ch;font-size:14px;margin:0 0 12px}
.lede b{color:var(--fg)}
#bar{position:sticky;top:0;z-index:40;display:flex;gap:14px;align-items:center;flex-wrap:wrap;
 padding:9px 12px;margin:12px 0 0;background:#141419;border:1px solid var(--line);
 border-radius:9px;font-size:12.5px}
#bar .grp{display:flex;gap:6px;align-items:center;flex-wrap:wrap}
#bar .lbl{color:var(--dim);font-size:11.5px;text-transform:uppercase;letter-spacing:.05em}
.cb{display:inline-flex;gap:4px;align-items:center;padding:2px 8px;border:1px solid var(--line);
 border-radius:20px;background:#101014;cursor:pointer;font:12px ui-monospace,monospace}
#bar button{background:#101014;color:var(--fg);border:1px solid var(--line);border-radius:20px;
 padding:3px 11px;cursor:pointer;font:12px ui-sans-serif,sans-serif}
#bar button.on{background:var(--acc);border-color:var(--acc);color:#fff}
#tally{margin-left:auto;color:var(--dim);font-size:12px}
.grid{display:grid;grid-template-columns:1fr;gap:14px;margin-top:14px}
.card{border:1px solid var(--line);border-radius:9px;background:#101014;overflow:hidden}
.ch{display:flex;gap:8px;align-items:center;padding:7px 12px;background:#141419;
 border-bottom:1px solid var(--line);font-size:12px;flex-wrap:wrap}
.ch b{font-size:12.5px;word-break:break-all}
.t{font-size:9.5px;padding:1px 7px;border-radius:20px;background:#2a1a12;
 border:1px solid #6b4423;color:var(--mid)}
.t.s-both{background:#2a1030;border-color:#6b3a8a;color:#d9a9ff}
.t.s-v33{background:#101f2a;border-color:#2b5c7a;color:#9ad4ff}
.vd{display:flex;gap:4px;align-items:center;color:var(--dim);font-size:10.5px}
.vd i{font-style:normal;opacity:.75;margin-right:2px}
.vd+.vd{margin-left:6px}
.v{font:10px ui-monospace,monospace;padding:1px 6px;border-radius:20px;border:1px solid var(--line)}
.v-fail{background:#2d1418;border-color:#8a2b34;color:#ff9aa2}
.v-mid{background:#2a2110;border-color:#6b4423;color:var(--mid)}
.v-clean{background:#12240f;border-color:#2c5c33;color:#7ee787}
.v-bc{background:#101f2a;border-color:#2b5c7a;color:#9ad4ff}
.v-tie,.v-v{background:#17171d;color:var(--dim)}
.body{display:grid;grid-template-columns:230px 1fr;gap:10px;padding:8px}
@media(max-width:1000px){.body{grid-template-columns:1fr}}
.src{display:flex;flex-direction:column;gap:6px}
.src figure img{aspect-ratio:2/3}
.votes{display:flex;flex-direction:column;gap:3px;margin-top:2px}
.vote{display:flex;gap:3px;align-items:center;flex-wrap:wrap;color:var(--dim);font-size:10.5px}
.vote button{background:#101014;color:var(--dim);border:1px solid var(--line);border-radius:20px;
 padding:0 6px;cursor:pointer;font:10px ui-monospace,monospace}
.vote button.on{background:#2c5c33;border-color:#3fb950;color:#e8e8ea}
.arms{display:flex;flex-direction:column;gap:6px}
.arm{display:grid;grid-template-columns:150px 1fr;gap:8px;border:1px solid var(--line);
 border-radius:8px;background:#0b0b0e;padding:6px}
.arm.hero{border-color:#3b3160;background:#0e0c16}
.ah{grid-column:1/-1;display:flex;gap:8px;align-items:baseline;padding:1px 3px;font-size:12px}
.ah span{color:var(--dim);font-size:11px}
.ah .n{margin-left:auto;font-size:10.5px;color:var(--mid)}
.outs{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:5px}
figure{margin:0}
figure img{width:100%;display:block;background:#fff;border-radius:5px;cursor:zoom-in;
 aspect-ratio:3/4;object-fit:contain}
figure.ref img{aspect-ratio:2/3;outline:1px solid var(--line);outline-offset:-1px}
figcaption{font-size:10px;color:var(--dim);text-align:center;padding:3px 2px}
.miss{background:#17171d;border:1px dashed var(--line);border-radius:5px;aspect-ratio:3/4;
 display:flex;align-items:center;justify-content:center;color:var(--dim);font-size:11px}
#lb{display:none;position:fixed;inset:0;background:rgba(0,0,0,.95);z-index:99;
 align-items:center;justify-content:center;flex-direction:column;gap:10px;padding:20px}
#lb.on{display:flex}#lb img{max-width:95vw;max-height:90vh;object-fit:contain;background:#fff}
#lbc{color:var(--dim);font-size:13px}
footer{border-top:1px solid var(--line);margin-top:36px;padding:20px 0 30px;color:var(--dim);font-size:12.5px}
code{background:#1b1b22;padding:1px 5px;border-radius:4px;font-size:12px}
textarea{display:none;width:100%;height:160px;margin-top:10px;background:#0b0b0e;color:#c3c3ce;
 border:1px solid var(--line);border-radius:6px;font:12px ui-monospace,monospace;padding:8px}
</style>
<div class='wrap'><h1>v3.5 link C &mdash; six arms on the pairs that fail</h1></div>
"""

LEDE = """<p class='lede'>Every pair here is marked hard by at least one of the two failure
records, and <b>both records' per-seed verdicts sit on the card</b> &mdash; so a cell that
works is a failure reached, not a fresh sample. <b>VEi</b> and <b>BC</b> are the iron-man 2
originals at the same seeds, not redraws. The four new arms differ from them only in what
happened to the reference between call 1 and call 2: <b>VEic</b> and <b>M1qbc</b> have the
head cut off &mdash; the first replaces the head with a mannequin, the second re-poses the
wearer and balds them, which is what stops hair surviving on the garment &mdash; and the
<b>a</b> arms add v3.3's ankle cut. Turn arms off to put any two side by side. Click any
image for full size.</p>"""

TOOLBAR = """<div id='bar'>
<span class='grp'><span class='lbl'>arms</span>{{ARMS}}
<button id='only-two'>VEic vs M1qbc</button><button id='no-ankle'>hide ankle arms</button>
<button id='all-arms'>all</button></span>
<span class='grp'><span class='lbl'>from</span>
<button class='f on' data-f='all'>all</button><button class='f' data-f='both'>both records</button>
<button class='f' data-f='v34_lock'>v3.4 lock</button><button class='f' data-f='v33'>v3.3</button></span>
<span class='grp'><span class='lbl'>class</span>
<button class='c on' data-c='all'>all</button><button class='c' data-c='F1'>F1</button>
<button class='c' data-c='F2'>F2</button><button class='c' data-c='F3'>F3</button>
<button class='c' data-c='F4'>F4</button></span>
<button id='export'>Export CSV</button><span id='tally'></span>
</div><textarea id='csvbox'></textarea>"""

LB = "<div id='lb'><img id='lbi' alt=''><div id='lbc'></div></div>"
SCRIPT = """<script>
document.addEventListener('click',e=>{const im=e.target.closest('figure img');
  if(!im)return;document.getElementById('lbi').src=im.dataset.full||im.getAttribute('src');
  document.getElementById('lbc').textContent=im.getAttribute('alt');
  document.getElementById('lb').classList.add('on');});
document.getElementById('lb').addEventListener('click',()=>
  document.getElementById('lb').classList.remove('on'));
document.addEventListener('keydown',e=>{if(e.key==='Escape')
  document.getElementById('lb').classList.remove('on')});

const boxes=[...document.querySelectorAll('#bar input[data-arm]')];
function arms(){boxes.forEach(b=>document.querySelectorAll('.arm.a-'+b.dataset.arm)
  .forEach(a=>a.style.display=b.checked?'':'none'));}
boxes.forEach(b=>b.onchange=arms);
const set=f=>{boxes.forEach(b=>b.checked=f(b.dataset.arm));arms();};
document.getElementById('only-two').onclick=()=>set(a=>a==='VEic'||a==='M1qbc');
document.getElementById('no-ankle').onclick=()=>set(a=>!a.endsWith('a')||a==='VEi');
document.getElementById('all-arms').onclick=()=>set(()=>true);

function filt(){const s=document.querySelector('#bar .f.on').dataset.f;
 const c=document.querySelector('#bar .c.on').dataset.c;
 document.querySelectorAll('.card').forEach(k=>k.style.display=
  ((s==='all'||k.dataset.source===s)&&(c==='all'||k.dataset.class===c))?'':'none');}
document.querySelectorAll('#bar .f').forEach(b=>b.onclick=()=>{
 document.querySelectorAll('#bar .f').forEach(x=>x.classList.toggle('on',x===b));filt();});
document.querySelectorAll('#bar .c').forEach(b=>b.onclick=()=>{
 document.querySelectorAll('#bar .c').forEach(x=>x.classList.toggle('on',x===b));filt();});

const KEY='v35-linkC-best';let v={};try{v=JSON.parse(localStorage.getItem(KEY)||'{}')}catch(e){}
function paint(){const t={};
 document.querySelectorAll('.vote').forEach(w=>{const k=w.dataset.sid+'|'+w.dataset.seed;
  w.querySelectorAll('button').forEach(b=>b.classList.toggle('on',b.dataset.v===v[k]));
  if(v[k])t[v[k]]=(t[v[k]]||0)+1;});
 const n=Object.values(t).reduce((a,b)=>a+b,0);
 document.getElementById('tally').textContent=n?('marked '+n+' · '+
  Object.entries(t).sort((a,b)=>b[1]-a[1]).map(([k,c])=>k+' '+c).join(' · ')):'no marks yet';}
document.addEventListener('click',e=>{const b=e.target.closest('.vote button');if(!b)return;
 const w=b.closest('.vote'),k=w.dataset.sid+'|'+w.dataset.seed;
 v[k]=(v[k]===b.dataset.v)?undefined:b.dataset.v;
 try{localStorage.setItem(KEY,JSON.stringify(v))}catch(x){}paint();});
document.getElementById('export').onclick=()=>{
 let csv='set_id,seed,source,class,lock_verdict,v33_verdict,best_arm\\n';
 document.querySelectorAll('.vote').forEach(w=>{const k=w.dataset.sid+'|'+w.dataset.seed;
  const card=w.closest('.card');
  csv+=[w.dataset.sid,w.dataset.seed,card.dataset.source,card.dataset.class,
        w.dataset.lock||'',w.dataset.v33||'',v[k]||''].join(',')+'\\n';});
 const box=document.getElementById('csvbox');box.style.display='block';box.value=csv;box.select();
 try{const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([csv],{type:'text/csv'}));
  a.download='v35_linkC_votes.csv';a.click();}catch(x){}};
arms();paint();</script>"""

if __name__ == "__main__":
    main()
