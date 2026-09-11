"""Every cell BC fails, with ER beside it. One question: does ER have the same problem?

BC was marked twice and the passes disagree sharply on failures (29 then 50 of 600, Jaccard
0.44), so a rate measured in one sitting cannot be compared with a rate measured in another.
This page sidesteps that entirely: it judges ER **only against BC's own failures, in one
sitting, with both images side by side**. Left is always BC, right is always ER.

The second block is the other direction - cells BC passes and the ER sweep failed - so the
pass produces a complete pair rather than a rescue rate with no cost beside it.

  python3 v3/build/v36_bcfail_page.py [BC_COUNT_CSV]   ->  v3/report/v36_bcfail.html
"""
import csv
import html
import os
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import v36_report as R                # noqa: E402  strip images, styles, lightbox

REPORT = os.path.join(REPO, "v3", "report")
BCCSV = sys.argv[1] if len(sys.argv) > 1 else os.path.join(REPO, "v3", "testsets", "bc2_count.csv")


def strip(sid, sd, cls=""):
    r = R.MATRIX[sid]
    src = (R.fig(os.path.join(R.IRON, "inputs", f"{r['person']}.jpg"),
                 f"{r['person']}__p.jpg", "the person (image 1)", 300)
           + R.fig(os.path.join(R.BCRUN, "refs", f"{r['garment']}__BC.jpg"),
                   f"{r['garment']}__r.jpg", "the reference (image 2)", 300))
    outs = (R.fig(os.path.join(R.BCRUN, "gen", f"{sid}__BC__s{sd}.jpg"),
                  f"{sid}__BC__s{sd}.jpg", "BC")
            + R.fig(os.path.join(R.ERRUN, "gen", f"{sid}__ER__s{sd}.jpg"),
                    f"{sid}__ER__s{sd}.jpg", "ER"))
    return (f"<div class='cellcard {cls}' data-sid='{html.escape(sid)}' data-seed='{sd}' "
            f"data-block='{cls}'>"
            f"<div class='ch'><b>{html.escape(sid)}</b><span class='t'>seed {sd}</span>"
            "<span class='marks'>"
            "<button class='v' data-v='same'>ER has it too</button>"
            "<button class='v' data-v='clean'>ER is fine</button>"
            "</span></div>"
            f"<div class='cellbody'><div class='src'>{src}</div>"
            f"<div class='outs'>{outs}</div></div></div>")


def main():
    os.makedirs(R.IMG, exist_ok=True)
    bc = {(r["set_id"], r["seed"]): r["bc_failed"] == "fail"
          for r in csv.DictReader(open(BCCSV))}
    er = {(r["set_id"], r["seed"]): r["bc_failed"] == "fail"
          for r in csv.DictReader(open(R.ERCOUNT))}
    fails = sorted(c for c in bc if bc[c])
    eronly = sorted(c for c in er if er[c] and not bc.get(c))

    page = f"""{R.HEAD.replace('TITLE', 'BC fails &mdash; does ER fail too?')}
<div class='wrap'>
<p class='lede'><b>Left is BC, right is ER</b>, every cell BC failed in
<code>{html.escape(os.path.basename(BCCSV))}</code>. One question per row: does ER have the
same problem? Judged in one sitting against one bar, so nothing here depends on two sweeps
agreeing. <a href='v36_report.html'>&larr; the result</a></p>
{BAR}
<h2>BC failed &mdash; {len(fails)} cells</h2>
{''.join(strip(sid, sd, 'bcfail') for sid, sd in fails)}
<h2>The other direction &mdash; {len(eronly)} cells BC passes and the ER sweep failed</h2>
<p class='sec'>Marked the same way, so the pass ends with a cost beside the rescue rather
than a rescue alone.</p>
{''.join(strip(sid, sd, 'eronly') for sid, sd in eronly)}
<footer>BC failures from <code>{html.escape(os.path.relpath(BCCSV, REPO))}</code>; the other
direction from <code>v3/testsets/er_count.csv</code> &middot; rebuild:
<code>python3 v3/build/v36_bcfail_page.py</code></footer>
</div>{R.LB}{R.SCRIPT}{SCRIPT}"""
    open(os.path.join(REPORT, "v36_bcfail.html"), "w").write(page)
    print(f"v3/report/v36_bcfail.html  ({len(fails)} BC failures + {len(eronly)} the other way)")


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
.marks{margin-left:auto;display:flex;gap:5px}
.marks button{background:#101014;color:var(--dim);border:1px solid var(--line);
 border-radius:20px;padding:2px 11px;cursor:pointer;font:11px ui-sans-serif,sans-serif}
.marks button.on[data-v='same']{background:#2d1418;border-color:#8a2b34;color:#ff9aa2}
.marks button.on[data-v='clean']{background:#12240f;border-color:#2c5c33;color:#7ee787}
.outs figure:first-child figcaption{color:#ff9aa2}
textarea{display:none;width:100%;height:160px;margin-top:10px;background:#0b0b0e;
 color:#c3c3ce;border:1px solid var(--line);border-radius:6px;
 font:12px ui-monospace,monospace;padding:8px}
</style>
<script>
const K='v36-bcfail-v1';let m={};try{m=JSON.parse(localStorage.getItem(K)||'{}')}catch(e){}
const cards=[...document.querySelectorAll('.cellcard')];
const key=c=>c.dataset.sid+'|'+c.dataset.seed;
function paint(){
 const n={same:0,clean:0};
 cards.forEach(c=>{const v=m[key(c)];
  c.querySelectorAll('.marks button').forEach(b=>b.classList.toggle('on',v===b.dataset.v));
  if(v&&c.dataset.block==='bcfail')n[v]++;});
 const tot=cards.filter(c=>c.dataset.block==='bcfail').length;
 const done=n.same+n.clean;
 document.getElementById('tally').innerHTML='of BC\\u2019s '+tot+' failures: ER also fails '
  +n.same+', ER is fine <b>'+n.clean+'</b>'+(done?' ('+(100*n.clean/done).toFixed(0)+'% rescued of '+done+' judged)':'');}
document.addEventListener('click',e=>{const b=e.target.closest('.marks button');if(!b)return;
 const c=b.closest('.cellcard'),k=key(c);
 m[k]=(m[k]===b.dataset.v)?undefined:b.dataset.v;
 if(!m[k])delete m[k];
 try{localStorage.setItem(K,JSON.stringify(m))}catch(x){}paint();});
document.getElementById('jump').onclick=()=>{const c=cards.find(x=>!m[key(x)]);
 if(c)c.scrollIntoView({behavior:'smooth',block:'center'});else alert('all marked');};
document.getElementById('reset').onclick=()=>{if(!confirm('clear?'))return;m={};
 try{localStorage.removeItem(K)}catch(x){}paint();};
document.getElementById('export').onclick=()=>{
 let csv='set_id,seed,block,er_verdict\\n';
 cards.forEach(c=>{csv+=c.dataset.sid+','+c.dataset.seed+','+c.dataset.block+','+(m[key(c)]||'')+'\\n';});
 const t=document.getElementById('csvbox');t.style.display='block';t.value=csv;t.select();
 try{const a=document.createElement('a');
  a.href=URL.createObjectURL(new Blob([csv],{type:'text/csv'}));
  a.download='v36_bcfail.csv';a.click();}catch(x){}};
paint();</script>"""


if __name__ == "__main__":
    main()
