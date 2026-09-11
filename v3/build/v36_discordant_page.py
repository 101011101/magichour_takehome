"""The cells the two blind sweeps disagree on, judged blind and side by side.

`BC` and `ER` were marked in separate sittings, so a cell that changed verdict might have
changed because the arms differ or because the reviewer's threshold did. This page removes
the second possibility: the 25 discordant cells, both outputs in front of one eye at once,
**arm labels hidden and left/right randomised per cell** (fixed seed, so the key is
reproducible). One question - which would you ship.

Export writes the unblinding key beside each answer, so nothing has to be remembered.

  python3 v3/build/v36_discordant_page.py    ->  v3/report/v36_discordant.html
"""
import csv
import html
import os
import random
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import v36_report as R                # noqa: E402  strip images, styles, lightbox

REPORT = os.path.join(REPO, "v3", "report")
SEED = 46


def main():
    os.makedirs(R.IMG, exist_ok=True)
    er = {(r["set_id"], r["seed"]): r["bc_failed"] == "fail"
          for r in csv.DictReader(open(R.ERCOUNT))}
    bc = {(r["set_id"], r["seed"]): r["bc_failed"] == "fail"
          for r in csv.DictReader(open(R.COUNT))}
    disc = sorted(c for c in er if er[c] != bc.get(c))
    rng = random.Random(SEED)

    cards = []
    for sid, sd in disc:
        r = R.MATRIX[sid]
        left, right = ("BC", "ER") if rng.random() < 0.5 else ("ER", "BC")
        img = {"BC": os.path.join(R.BCRUN, "gen", f"{sid}__BC__s{sd}.jpg"),
               "ER": os.path.join(R.ERRUN, "gen", f"{sid}__ER__s{sd}.jpg")}
        src = (R.fig(os.path.join(R.IRON, "inputs", f"{r['person']}.jpg"),
                     f"{r['person']}__p.jpg", "the person (image 1)", 300)
               + R.fig(os.path.join(R.BCRUN, "refs", f"{r['garment']}__BC.jpg"),
                       f"{r['garment']}__r.jpg", "the reference (image 2)", 300))
        outs = (R.fig(img[left], f"{sid}__{left}__s{sd}.jpg", "A")
                + R.fig(img[right], f"{sid}__{right}__s{sd}.jpg", "B"))
        cards.append(
            f"<div class='cellcard' data-sid='{html.escape(sid)}' data-seed='{sd}' "
            f"data-a='{left}' data-b='{right}'>"
            f"<div class='ch'><b>{html.escape(sid)}</b><span class='t'>seed {sd}</span>"
            "<span class='marks'>"
            "<button class='v' data-v='A'>A</button>"
            "<button class='v' data-v='both'>both fine</button>"
            "<button class='v' data-v='neither'>both bad</button>"
            "<button class='v' data-v='B'>B</button>"
            "</span></div>"
            f"<div class='cellbody'><div class='src'>{src}</div>"
            f"<div class='outs'>{outs}</div></div></div>")

    page = f"""{R.HEAD.replace('TITLE', 'The disagreements, judged blind')}
<div class='wrap'>
<p class='lede'>The <b>{len(disc)} cells</b> the two sweeps disagree on, both outputs in
front of you at once. <b>Which arm is which is hidden</b> and the sides are shuffled per
cell, so a threshold that drifted between two sittings cannot survive this. Mark the one you
would ship &mdash; or that both are fine, or neither is.
<a href='v36_report.html'>&larr; the result</a></p>
{BAR}
{''.join(cards)}
<footer>The discordant cells of <code>bc_count.csv</code> &times; <code>er_count.csv</code>
&middot; sides shuffled with seed {SEED} &middot; Export writes the unblinding key beside
each answer &middot; rebuild:
<code>python3 v3/build/v36_discordant_page.py</code></footer>
</div>{R.LB}{R.SCRIPT}{SCRIPT}"""
    open(os.path.join(REPORT, "v36_discordant.html"), "w").write(page)
    print(f"v3/report/v36_discordant.html  ({len(disc)} cells: "
          f"{sum(1 for c in disc if bc.get(c))} BC-fail, {sum(1 for c in disc if er[c])} ER-fail)")


BAR = """<div id='bar'>
<button id='export'>Export CSV</button><button id='reset'>clear</button>
<span id='tally'></span></div><textarea id='csvbox'></textarea>"""

SCRIPT = """<style>
#bar{position:sticky;top:0;z-index:40;display:flex;gap:10px;align-items:center;
 padding:10px 13px;margin:8px 0 14px;background:#141419;border:1px solid var(--line);
 border-radius:9px;font-size:13px}
#bar button{background:#101014;color:var(--fg);border:1px solid var(--line);
 border-radius:20px;padding:4px 12px;cursor:pointer;font:12px ui-sans-serif,sans-serif}
#tally{margin-left:auto;font:12px ui-monospace,monospace;color:var(--dim)}
.marks{margin-left:auto;display:flex;gap:5px}
.marks button{background:#101014;color:var(--dim);border:1px solid var(--line);
 border-radius:20px;padding:2px 11px;cursor:pointer;font:11px ui-sans-serif,sans-serif}
.marks button.on{background:var(--acc);border-color:var(--acc);color:#fff}
textarea{display:none;width:100%;height:160px;margin-top:10px;background:#0b0b0e;
 color:#c3c3ce;border:1px solid var(--line);border-radius:6px;
 font:12px ui-monospace,monospace;padding:8px}
</style>
<script>
const K='v36-discordant-v1';let m={};try{m=JSON.parse(localStorage.getItem(K)||'{}')}catch(e){}
const cards=[...document.querySelectorAll('.cellcard')];
const key=c=>c.dataset.sid+'|'+c.dataset.seed;
function paint(){
 let n={BC:0,ER:0,both:0,neither:0};
 cards.forEach(c=>{const v=m[key(c)];
  c.querySelectorAll('.marks button').forEach(b=>b.classList.toggle('on',v===b.dataset.v));
  if(!v)return;
  if(v==='A')n[c.dataset.a]++;else if(v==='B')n[c.dataset.b]++;else n[v]++;});
 const done=Object.keys(m).length;
 document.getElementById('tally').textContent=
  done+'/'+cards.length+' judged - BC '+n.BC+' - ER '+n.ER+' - both fine '+n.both
  +' - both bad '+n.neither;}
document.addEventListener('click',e=>{const b=e.target.closest('.marks button');if(!b)return;
 const c=b.closest('.cellcard'),k=key(c);
 m[k]=(m[k]===b.dataset.v)?undefined:b.dataset.v;
 if(!m[k])delete m[k];
 try{localStorage.setItem(K,JSON.stringify(m))}catch(x){}paint();});
document.getElementById('reset').onclick=()=>{if(!confirm('clear?'))return;m={};
 try{localStorage.removeItem(K)}catch(x){}paint();};
document.getElementById('export').onclick=()=>{
 let csv='set_id,seed,shown_A,shown_B,answer,better_arm\\n';
 cards.forEach(c=>{const v=m[key(c)]||'';
  const arm=v==='A'?c.dataset.a:v==='B'?c.dataset.b:v;
  csv+=c.dataset.sid+','+c.dataset.seed+','+c.dataset.a+','+c.dataset.b+','+v+','+arm+'\\n';});
 const t=document.getElementById('csvbox');t.style.display='block';t.value=csv;t.select();
 try{const a=document.createElement('a');
  a.href=URL.createObjectURL(new Blob([csv],{type:'text/csv'}));
  a.download='v36_discordant.csv';a.click();}catch(x){}};
paint();</script>"""


if __name__ == "__main__":
    main()
