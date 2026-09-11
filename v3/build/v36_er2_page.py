"""`ER2` beside `ER` and `BC`, on the 53 cells that currently fail.

`ER2` is `ER`'s first sentence with the hold clause dropped - the clause every call-2 prompt
has carried since V2. Two questions per row, and they are separate because a prompt can pass
one and fail the other:

  the garment   does ER2 fix the failure, match it, or make it worse?
  the hold      did the face, pose or background move without the clause telling them not to?

Selected on failure, so nothing here is a rate. Left to right: BC, ER, ER2, so the incumbent
and the shipped candidate are both in view.

  python3 v3/build/v36_er2_page.py    ->  v3/report/v36_er2.html
"""
import csv
import html
import os
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import v36_report as R                # noqa: E402  strip images, styles, lightbox

RUN = os.path.join(REPO, "v3", "runs", "v36", "er2")
REPORT = os.path.join(REPO, "v3", "report")


def main():
    os.makedirs(R.IMG, exist_ok=True)
    rows = list(csv.DictReader(open(os.path.join(RUN, "v36_er2_set.csv"))))

    cards = []
    for r in rows:
        sid, sd = r["set_id"], r["seed"]
        src = (R.fig(os.path.join(RUN, "inputs", f"{r['person']}.jpg"),
                     f"{r['person']}__p.jpg", "the person (image 1)", 300)
               + R.fig(os.path.join(RUN, "refs", f"{r['garment']}__BC.jpg"),
                       f"{r['garment']}__r.jpg", "the reference (image 2)", 300))
        outs = (R.fig(os.path.join(R.BCRUN, "gen", f"{sid}__BC__s{sd}.jpg"),
                      f"{sid}__BC__s{sd}.jpg", "BC")
                + R.fig(os.path.join(RUN, "gen", f"{sid}__ER__s{sd}.jpg"),
                        f"{sid}__ER__s{sd}.jpg", "ER")
                + R.fig(os.path.join(RUN, "gen", f"{sid}__ER2__s{sd}.jpg"),
                        f"{sid}__ER2__s{sd}.jpg", "ER2 &mdash; no hold clause"))
        tags = "".join(f"<span class='b b-fail'>{k} failed</span>"
                       for k in ("BC", "ER") if r[{"BC": "bc2", "ER": "er"}[k]] == "fail")
        cards.append(
            f"<div class='cellcard' data-sid='{html.escape(sid)}' data-seed='{sd}'>"
            f"<div class='ch'><b>{html.escape(sid)}</b><span class='t'>seed {sd}</span>{tags}"
            "<span class='marks'>"
            "<span class='grp'>garment"
            "<button class='v' data-g='fixed'>ER2 fixes it</button>"
            "<button class='v' data-g='same'>same as ER</button>"
            "<button class='v' data-g='worse'>worse</button></span>"
            "<span class='grp'>hold"
            "<button class='h' data-h='held'>held</button>"
            "<button class='h' data-h='drift'>drifted</button></span>"
            "</span></div>"
            f"<div class='cellbody'><div class='src'>{src}</div>"
            f"<div class='outs three'>{outs}</div></div></div>")

    page = f"""{R.HEAD.replace('TITLE', 'ER2 &mdash; the hold clause, dropped')}
<div class='wrap'>
<p class='lede'><code>ER2</code> is <code>ER</code>'s first sentence alone:
<i>Replace the clothing in image 1 with the clothing in image 2.</i> The clause every call-2
prompt has carried since V2 &mdash; <i>keep the person's face, identity, body and the
background exactly as they are</i> &mdash; is gone. Two marks per row: whether the
<b>garment</b> outcome changed, and whether the <b>hold</b> survived without being asked for.
The {len(rows)} cells are the ones that currently fail under either arm, so this is a
diagnostic, not a rate. <a href='v36_report.html'>&larr; the result</a></p>
{BAR}
{''.join(cards)}
<footer>{len(rows)} cells &middot; 53 klein calls, 2.2 min, CAD 0.03 on an A100 &middot; set
<code>v3/colab/v36_er2_set.csv</code> &middot; rebuild:
<code>python3 v3/build/v36_er2_page.py</code></footer>
</div>{R.LB}{R.SCRIPT}{SCRIPT}"""
    open(os.path.join(REPORT, "v36_er2.html"), "w").write(page)
    print(f"v3/report/v36_er2.html  ({len(rows)} cells, BC | ER | ER2)")


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
.marks{margin-left:auto;display:flex;gap:12px;align-items:center}
.grp{display:flex;gap:4px;align-items:center;font-size:10px;color:var(--dim);
 text-transform:uppercase;letter-spacing:.5px}
.marks button{background:#101014;color:var(--dim);border:1px solid var(--line);
 border-radius:20px;padding:2px 10px;cursor:pointer;font:11px ui-sans-serif,sans-serif;
 text-transform:none;letter-spacing:0}
.marks button.on[data-g='fixed'],.marks button.on[data-h='held']{background:#12240f;
 border-color:#2c5c33;color:#7ee787}
.marks button.on[data-g='worse'],.marks button.on[data-h='drift']{background:#2d1418;
 border-color:#8a2b34;color:#ff9aa2}
.marks button.on[data-g='same']{background:#1b1b22;border-color:#4a4a55;color:var(--fg)}
.outs.three{grid-template-columns:repeat(3,1fr)}
textarea{display:none;width:100%;height:160px;margin-top:10px;background:#0b0b0e;
 color:#c3c3ce;border:1px solid var(--line);border-radius:6px;
 font:12px ui-monospace,monospace;padding:8px}
</style>
<script>
const K='v36-er2-v1';let m={};try{m=JSON.parse(localStorage.getItem(K)||'{}')}catch(e){}
const cards=[...document.querySelectorAll('.cellcard')];
const key=c=>c.dataset.sid+'|'+c.dataset.seed;
function paint(){
 const g={fixed:0,same:0,worse:0},h={held:0,drift:0};
 cards.forEach(c=>{const v=m[key(c)]||{};
  c.querySelectorAll('.marks button').forEach(b=>b.classList.toggle('on',
   b.dataset.g?v.g===b.dataset.g:v.h===b.dataset.h));
  if(v.g)g[v.g]++; if(v.h)h[v.h]++;});
 document.getElementById('tally').innerHTML=
  'garment: fixes <b>'+g.fixed+'</b> - same '+g.same+' - worse '+g.worse
  +' &nbsp;|&nbsp; hold: held <b>'+h.held+'</b> - drifted '+h.drift;}
document.addEventListener('click',e=>{const b=e.target.closest('.marks button');if(!b)return;
 const c=b.closest('.cellcard'),k=key(c);m[k]=m[k]||{};
 const f=b.dataset.g?'g':'h',v=b.dataset.g||b.dataset.h;
 m[k][f]=(m[k][f]===v)?undefined:v;
 try{localStorage.setItem(K,JSON.stringify(m))}catch(x){}paint();});
document.getElementById('jump').onclick=()=>{
 const c=cards.find(x=>!(m[key(x)]||{}).g);
 if(c)c.scrollIntoView({behavior:'smooth',block:'center'});else alert('all marked');};
document.getElementById('reset').onclick=()=>{if(!confirm('clear?'))return;m={};
 try{localStorage.removeItem(K)}catch(x){}paint();};
document.getElementById('export').onclick=()=>{
 let csv='set_id,seed,bc_failed,er_failed,garment,hold\\n';
 cards.forEach(c=>{const v=m[key(c)]||{};
  const t=[...c.querySelectorAll('.b-fail')].map(x=>x.textContent.split(' ')[0]);
  csv+=c.dataset.sid+','+c.dataset.seed+','+(t.includes('BC')?'fail':'')+','
   +(t.includes('ER')?'fail':'')+','+(v.g||'')+','+(v.h||'')+'\\n';});
 const t=document.getElementById('csvbox');t.style.display='block';t.value=csv;t.select();
 try{const a=document.createElement('a');
  a.href=URL.createObjectURL(new Blob([csv],{type:'text/csv'}));
  a.download='v36_er2.csv';a.click();}catch(x){}};
paint();</script>"""


if __name__ == "__main__":
    main()
