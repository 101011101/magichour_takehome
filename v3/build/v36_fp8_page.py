"""`ER` against `ERq` — the same prompt on two transformers, 74 cells.

Left is BFL's weights, right is Photoroom's fp8-derived bf16. Same prompt, same reference,
same seed, same canvas; the transformer is the only difference. Grouped by what `ER`'s
verdict already was, because a change means different things in each group.

One question per row: is the OUTCOME the same? The pixels never are - a ~2% weight
perturbation moves the sampling trajectory from the first step - so identity of output is
not the test and is not asked.

  python3 v3/build/v36_fp8_page.py    ->  v3/report/v36_fp8.html
"""
import csv
import html
import os
import sys

import cv2
import numpy as np

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import v36_report as R                # noqa: E402

RUN = os.path.join(REPO, "v3", "runs", "v36", "fp8")
REPORT = os.path.join(REPO, "v3", "report")
LABEL = {"both_clean": ("both arms clean", "a change here is a regression &mdash; the group that decides"),
         "er_repaired": ("ER repaired over BC", "a change here loses a win"),
         "er_fail": ("ER failed", "a change here could go either way")}


def main():
    os.makedirs(R.IMG, exist_ok=True)
    rows = list(csv.DictReader(open(os.path.join(RUN, "v36_fp8_set.csv"))))

    def strip(r):
        sid, sd = r["set_id"], r["seed"]
        a = os.path.join(RUN, "gen", f"{sid}__ER__s{sd}.jpg")
        b = os.path.join(RUN, "gen", f"{sid}__ERq__s{sd}.jpg")
        A, B = cv2.imread(a), cv2.imread(b)
        d = float(np.abs(A.astype(np.float32) - B.astype(np.float32)).mean())
        src = (R.fig(os.path.join(RUN, "inputs", f"{r['person']}.jpg"),
                     f"{r['person']}__p.jpg", "the person (image 1)", 300)
               + R.fig(os.path.join(RUN, "refs", f"{r['garment']}__BC.jpg"),
                       f"{r['garment']}__r.jpg", "the reference (image 2)", 300))
        outs = (R.fig(a, f"{sid}__ER__s{sd}.jpg", "ER &mdash; BFL weights")
                + R.fig(b, f"{sid}__ERq__s{sd}.jpg", "ERq &mdash; Photoroom fp8"))
        return (f"<div class='cellcard' data-sid='{html.escape(sid)}' data-seed='{sd}' "
                f"data-grp='{r['er_status']}'>"
                f"<div class='ch'><b>{html.escape(sid)}</b><span class='t'>seed {sd}</span>"
                f"<span class='note'>pixel diff {d:.2f}/255</span>"
                "<span class='marks'>"
                "<button class='v' data-v='same'>same outcome</button>"
                "<button class='v' data-v='differs'>outcome differs</button>"
                "</span></div>"
                f"<div class='cellbody'><div class='src'>{src}</div>"
                f"<div class='outs'>{outs}</div></div></div>")

    blocks = ""
    for g in ("both_clean", "er_repaired", "er_fail"):
        cells = [r for r in rows if r["er_status"] == g]
        t, note = LABEL[g]
        blocks += (f"<h2>{t} &mdash; {len(cells)}</h2><p class='sec'>{note}</p>"
                   + "".join(strip(r) for r in cells))

    page = f"""{R.HEAD.replace('TITLE', 'ER vs ERq - two transformers, one prompt')}
<div class='wrap'>
<p class='lede'><b>Left: BFL's transformer. Right: Photoroom's fp8-derived bf16.</b> Same
prompt, same reference, same seed, same canvas &mdash; the weights are the only difference.
The two files share an architecture config and a tensor layout, but 16 of 18 large matrices
differ, with the low-mantissa signature of an fp8 round trip and ~2% median relative error.
<b>The pixels always differ</b> (median 1.88/255 &mdash; a 2% weight perturbation moves the
trajectory from step one), so the question per row is only whether the <b>outcome</b> does.
<a href='v36_report.html'>&larr; the report</a></p>
{BAR}
{blocks}
<footer>74 cells &middot; 74 klein calls, 3.0 min, CAD 0.035 on an A100 &middot; transformer
<code>Photoroom/FLUX.2-klein-4b-fp8-diffusers/transformer_bf16</code>; text encoder, VAE,
scheduler and tokenizer from <code>black-forest-labs/FLUX.2-klein-4B</code> &middot; rebuild:
<code>python3 v3/build/v36_fp8_page.py</code></footer>
</div>{R.LB}{R.SCRIPT}{SCRIPT}"""
    open(os.path.join(REPORT, "v36_fp8.html"), "w").write(page)
    print(f"v3/report/v36_fp8.html  ({len(rows)} cells)")


BAR = """<div id='bar'>
<button id='jump'>next unmarked</button><button id='export'>Export CSV</button>
<button id='reset'>clear</button><span id='tally'></span></div><textarea id='csvbox'></textarea>"""

SCRIPT = """<style>
#bar{position:sticky;top:0;z-index:40;display:flex;gap:10px;align-items:center;
 padding:10px 13px;margin:8px 0 14px;background:#141419;border:1px solid var(--line);
 border-radius:9px;font-size:13px}
#bar button{background:#101014;color:var(--fg);border:1px solid var(--line);
 border-radius:20px;padding:4px 12px;cursor:pointer;font:12px ui-sans-serif,sans-serif}
#tally{margin-left:auto;font:12px ui-monospace,monospace;color:var(--dim)}
#tally b{color:var(--good)}
.marks{display:flex;gap:5px}
.note{color:var(--dim);font:11px ui-monospace,monospace;margin-left:auto}
.marks button{background:#101014;color:var(--dim);border:1px solid var(--line);
 border-radius:20px;padding:2px 11px;cursor:pointer;font:11px ui-sans-serif,sans-serif}
.marks button.on[data-v='same']{background:#12240f;border-color:#2c5c33;color:#7ee787}
.marks button.on[data-v='differs']{background:#2d1418;border-color:#8a2b34;color:#ff9aa2}
textarea{display:none;width:100%;height:160px;margin-top:10px;background:#0b0b0e;
 color:#c3c3ce;border:1px solid var(--line);border-radius:6px;
 font:12px ui-monospace,monospace;padding:8px}
</style>
<script>
const K='v36-fp8-v1';let m={};try{m=JSON.parse(localStorage.getItem(K)||'{}')}catch(e){}
const cards=[...document.querySelectorAll('.cellcard')];
const key=c=>c.dataset.sid+'|'+c.dataset.seed;
function paint(){
 const n={same:0,differs:0};
 cards.forEach(c=>{const v=m[key(c)];
  c.querySelectorAll('.marks button').forEach(b=>b.classList.toggle('on',v===b.dataset.v));
  if(v)n[v]++;});
 document.getElementById('tally').innerHTML='same outcome <b>'+n.same+'</b> - differs '
  +n.differs+' - of '+cards.length;}
document.addEventListener('click',e=>{const b=e.target.closest('.marks button');if(!b)return;
 const c=b.closest('.cellcard'),k=key(c);
 m[k]=(m[k]===b.dataset.v)?undefined:b.dataset.v; if(!m[k])delete m[k];
 try{localStorage.setItem(K,JSON.stringify(m))}catch(x){}paint();});
document.getElementById('jump').onclick=()=>{const c=cards.find(x=>!m[key(x)]);
 if(c)c.scrollIntoView({behavior:'smooth',block:'center'});else alert('all marked');};
document.getElementById('reset').onclick=()=>{if(!confirm('clear?'))return;m={};
 try{localStorage.removeItem(K)}catch(x){}paint();};
document.getElementById('export').onclick=()=>{
 let csv='set_id,seed,er_status,outcome\\n';
 cards.forEach(c=>{csv+=c.dataset.sid+','+c.dataset.seed+','+c.dataset.grp+','+(m[key(c)]||'')+'\\n';});
 const t=document.getElementById('csvbox');t.style.display='block';t.value=csv;t.select();
 try{const a=document.createElement('a');
  a.href=URL.createObjectURL(new Blob([csv],{type:'text/csv'}));
  a.download='v36_fp8.csv';a.click();}catch(x){}};
paint();</script>"""


if __name__ == "__main__":
    main()
