"""Every generated cell of the v3.10 canvas run, one image per card: does it fail?

Not an A/B. The reviewer clicks the images that failed and the page counts them, so each
arm gets a rate of its own rather than a preference. Only the 456 cells that exist under
BOTH rules are shown, twice each - once per arm - so the two rates are counted over the
same cells by the same eye in one sitting.

The arm is not printed on the card. Nothing is hidden for its own sake; it costs nothing
and keeps the count from drifting toward whichever rule the reviewer expects to win. It is
in the export beside every row.

  python3 v3/build/v310_count_page.py   ->  v3/report/v310_count.html
"""
import csv
import html
import os
import random

from PIL import Image

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RUN = os.path.join(REPO, "v3", "runs", "v310", "a100")
GEN = os.path.join(RUN, "gen")
REPORT = os.path.join(REPO, "v3", "report")
SET = os.path.join(REPO, "v3", "colab", "v310_set.csv")
IMG = os.path.join(REPORT, "img_v310count")
WIDTH = 460


def web(src, dst):
    out = os.path.join(IMG, dst)
    if not os.path.exists(out):
        im = Image.open(src).convert("RGB")
        if im.width > WIDTH:
            im = im.resize((WIDTH, int(im.height * WIDTH / im.width)), Image.LANCZOS)
        im.save(out, quality=88, optimize=True)
    return "img_v310count/" + dst


def main():
    os.makedirs(IMG, exist_ok=True)
    rows = list(csv.DictReader(open(SET)))
    cards = []
    for r in rows:
        if r.get("noscale_noop") == "1":
            continue
        for arm in ("SCALE", "NOSCALE"):
            f = f"{r['set_id']}__{arm}__s{r['seed']}.jpg"
            src = os.path.join(GEN, f)
            if os.path.exists(src):
                cards.append({"set_id": r["set_id"], "seed": r["seed"], "arm": arm,
                              "prior": r.get("prior", ""), "src": src, "file": f})
    random.Random(46).shuffle(cards)
    for c in cards:
        c["web"] = web(c["src"], c["file"])
    n_by_arm = {}
    for c in cards:
        n_by_arm[c["arm"]] = n_by_arm.get(c["arm"], 0) + 1

    items = "\n".join(
        f'<div class=c data-i="{i}" data-sid="{html.escape(c["set_id"])}" data-seed="{c["seed"]}"'
        f' data-arm="{c["arm"]}" data-prior="{c["prior"]}">'
        f'<img loading=lazy src="{c["web"]}"><div class=n>{i + 1}</div></div>'
        for i, c in enumerate(cards))

    doc = f"""<!doctype html><meta charset=utf-8><title>v3.10 &mdash; count the failures</title>
<style>
body{{background:#111;color:#eee;font:14px/1.5 system-ui,sans-serif;margin:0;padding:0 16px 120px}}
h1{{font-size:18px;font-weight:600;margin:18px 0 4px}}
p.lede{{color:#9aa;margin:0 0 16px;max-width:60em}}
#bar{{position:sticky;top:0;background:#111;padding:10px 0;border-bottom:1px solid #333;z-index:9;
display:flex;gap:18px;align-items:center;flex-wrap:wrap}}
button{{background:#222;color:#eee;border:1px solid #444;border-radius:6px;padding:7px 12px;font:inherit;cursor:pointer}}
button:hover{{background:#2c2c2c}}
#grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:10px;margin-top:14px}}
.c{{position:relative;cursor:pointer;border:2px solid transparent;border-radius:6px;overflow:hidden;background:#000}}
.c img{{width:100%;display:block}}
.c.fail{{border-color:#e5484d}}
.c.fail img{{opacity:.45}}
.c.fail:after{{content:"FAIL";position:absolute;top:8px;left:8px;background:#e5484d;color:#fff;
font-weight:700;font-size:12px;padding:2px 7px;border-radius:4px}}
.n{{position:absolute;bottom:6px;right:8px;color:#fff;background:#0008;border-radius:4px;padding:1px 6px;font-size:11px}}
b{{color:#fff}}
</style>
<h1>v3.10 &mdash; count the failures</h1>
<p class=lede>{len(cards)} images, one per card, shuffled. Click every image you would not ship.
Click again to undo. Nothing else to decide &mdash; the rates are counted from these clicks.
{n_by_arm.get('SCALE', 0)} are one rule and {n_by_arm.get('NOSCALE', 0)} the other; which is which is in the export.</p>
<div id=bar>
  <span>marked <b id=cnt>0</b> of {len(cards)}</span>
  <span>seen <b id=seen>0</b></span>
  <button onclick="exportCsv()">export CSV</button>
  <button onclick="if(confirm('clear all marks?')){{localStorage.removeItem(KEY);location.reload()}}">reset</button>
</div>
<div id=grid>
{items}
</div>
<script>
const KEY="v310-count-v1";
const marks=JSON.parse(localStorage.getItem(KEY)||"{{}}");
const cards=[...document.querySelectorAll('.c')];
function id(el){{return el.dataset.sid+"|"+el.dataset.seed+"|"+el.dataset.arm}}
function paint(){{
  cards.forEach(el=>el.classList.toggle('fail',!!marks[id(el)]));
  document.getElementById('cnt').textContent=Object.values(marks).filter(Boolean).length;
}}
cards.forEach(el=>el.addEventListener('click',()=>{{
  const k=id(el); marks[k]?delete marks[k]:marks[k]=1;
  localStorage.setItem(KEY,JSON.stringify(marks)); paint();
}}));
const io=new IntersectionObserver(es=>{{es.forEach(e=>{{if(e.isIntersecting)e.target.dataset.seen=1}});
  document.getElementById('seen').textContent=cards.filter(c=>c.dataset.seen).length;}},{{threshold:.5}});
cards.forEach(c=>io.observe(c));
function exportCsv(){{
  const out=[["set_id","seed","arm","prior","fail"]];
  cards.forEach(el=>out.push([el.dataset.sid,el.dataset.seed,el.dataset.arm,el.dataset.prior,marks[id(el)]?1:0]));
  const csv=out.map(r=>r.map(v=>/[",]/.test(v)?'"'+String(v).replace(/"/g,'""')+'"':v).join(",")).join("\\n");
  const a=document.createElement('a');
  a.href=URL.createObjectURL(new Blob([csv],{{type:"text/csv"}}));
  a.download="v310_count.csv"; a.click();
}}
paint();
</script>
"""
    os.makedirs(REPORT, exist_ok=True)
    out = os.path.join(REPORT, "v310_count.html")
    open(out, "w").write(doc)
    print(f"{out}  ({len(cards)} cards: {n_by_arm})")


if __name__ == "__main__":
    main()
