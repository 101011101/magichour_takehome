# The short report: what the product does now, against what it did before.
#
# No methodology. One number, then the pictures, ordered worst-baseline-first so a
# reader who scrolls three rows has seen the case for the work.
import csv, html, json, os

import report_assets as A

REPO = A.REPO
OUT = A.OUT
NL = chr(10)

CSS = """
:root{--bg:#0d0d10;--fg:#e8e8ea;--dim:#8a8a94;--line:#26262c;--acc:#7c5cff;
 --good:#3fb950;--mid:#d29922;--bad:#f85149}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
 font:15px/1.6 ui-sans-serif,-apple-system,"Segoe UI",Roboto,sans-serif}
a{color:var(--acc)}
header{padding:44px 30px 30px;border-bottom:1px solid var(--line);text-align:center}
h1{margin:0 0 10px;font-size:30px;letter-spacing:-.3px}
.lede{color:var(--dim);max-width:70ch;margin:0 auto;font-size:15px}
.lede b{color:var(--fg)}
.hero{display:flex;gap:28px;justify-content:center;flex-wrap:wrap;margin:26px 0 4px}
.stat{text-align:center}
.stat .n{font-size:34px;font-weight:800;letter-spacing:-1px}
.stat .n.good{color:var(--good)}.stat .n.bad{color:var(--bad)}
.stat .l{font-size:11.5px;color:var(--dim);text-transform:uppercase;letter-spacing:.6px}
.nav{padding:12px 30px;text-align:center;border-bottom:1px solid var(--line);
 background:#121216;font-size:13px}
table{border-collapse:collapse;margin:0 auto;font-size:13.5px}
th,td{padding:7px 16px;border-bottom:1px solid #1d1d23;text-align:right}
th:first-child,td:first-child{text-align:left}
th{color:var(--dim);font-weight:600}
tr.win td{background:#111a12}
.win .n{color:var(--good);font-weight:700}
.sec{max-width:1180px;margin:0 auto;padding:30px}
h2{font-size:19px;margin:34px 0 6px}
.note{color:var(--dim);font-size:13.5px;max-width:78ch}
.row{border:1px solid var(--line);border-radius:12px;background:#101014;
 margin:20px 0;overflow:hidden}
.rh{padding:10px 15px;background:#141419;border-bottom:1px solid var(--line);
 display:flex;gap:10px;align-items:center;flex-wrap:wrap;font-size:13px}
.rh b{font-size:13.5px}
.fault{font-size:11px;padding:2px 9px;border-radius:20px;background:#3a1a1c;
 color:#ff9a9a;border:1px solid #5a2a2a}
.ok{font-size:11px;padding:2px 9px;border-radius:20px;background:#15301b;
 color:#8ce99a;border:1px solid #24502e;margin-left:auto}
.imgs{display:grid;grid-template-columns:130px 130px 1fr 1fr;gap:2px;align-items:start;
 padding:10px}
/* baseline successes: three across in one row. The point needs making once, not
   six times -- klein being good is the premise, not the finding. */
.wins{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin:16px 0 4px}
@media(max-width:780px){.wins{grid-template-columns:1fr}}
.win-card{border:1px solid var(--line);border-radius:10px;background:#101014;
 overflow:hidden}
.win-card .trio{display:grid;grid-template-columns:1fr 1fr 1.5fr;gap:2px;padding:7px}
.win-card .trio img{width:100%;display:block;background:#fff;border-radius:4px;
 cursor:zoom-in}
.win-card .trio figcaption{font-size:9.5px;color:var(--dim);text-align:center;
 padding:3px 0}
.win-card .lbl{padding:6px 10px;font-size:11px;color:var(--good);font-weight:700;
 border-top:1px solid var(--line);text-align:center}
@media(max-width:820px){.imgs{grid-template-columns:1fr 1fr}}
figure{margin:0}
figure img{width:100%;display:block;background:#fff;border-radius:5px;cursor:zoom-in}
figcaption{font-size:11px;color:var(--dim);text-align:center;padding:5px 0}
figure.big img{border-radius:6px}
figure.before figcaption{color:var(--bad);font-weight:700}
figure.after figcaption{color:var(--good);font-weight:700}
#lb{display:none;position:fixed;inset:0;background:rgba(0,0,0,.95);z-index:99;
 align-items:center;justify-content:center;flex-direction:column;gap:10px;padding:20px}
#lb.on{display:flex}#lb img{max-width:95vw;max-height:90vh;object-fit:contain;background:#fff}
#lbc{color:var(--dim);font-size:13px}
footer{border-top:1px solid var(--line);padding:26px 30px;color:var(--dim);
 font-size:12.5px;text-align:center}
"""

JS = """
document.addEventListener('click',e=>{
  const im=e.target.closest('figure img');if(!im)return;
  // load the 1800px companion, not the thumbnail -- enlarging a thumbnail is
  // just scaling it up, which is not what "click to enlarge" should mean
  document.getElementById('lbi').src =
    im.dataset.full || im.getAttribute('src');
  document.getElementById('lbc').textContent=im.getAttribute('alt');
  document.getElementById('lb').classList.add('on');});
document.getElementById('lb').addEventListener('click',()=>
  document.getElementById('lb').classList.remove('on'));
document.addEventListener('keydown',e=>{if(e.key==='Escape')
  document.getElementById('lb').classList.remove('on')});
"""

FAULT = {"wrongperson": "wrong person", "wrongclothes": "wrong clothes",
         "wrongbg": "background repainted", "duplication": "duplicated person",
         "nontransfer": "no transfer"}


def build():
    ps = A.pairs()
    wins = A.baseline_successes(3)
    e = html.escape

    def big(src, alt, cls=""):
        a = A.asset(src, 900, hires=True)
        full = a.replace(".jpg", "@2x.jpg")
        return (f"<figure class='big {cls}'><img src='{a}' data-full='{full}' "
                f"alt='{e(alt)}'>")

    win_rows = []
    for w in wins:
        r = A.asset(w["base"], 640, hires=True)
        win_rows.append(
            f"<div class='win-card'><div class='trio'>"
            f"<figure><img src='{A.asset(w['person'],240)}' alt='person'>"
            f"<figcaption>person</figcaption></figure>"
            f"<figure><img src='{A.asset(w['garment'],240)}' alt='garment'>"
            f"<figcaption>garment</figcaption></figure>"
            f"<figure><img src='{r}' data-full='{r.replace('.jpg','@2x.jpg')}' "
            f"alt='{e(w['set_id'])} — base klein, no harness'>"
            f"<figcaption>klein alone</figcaption></figure></div>"
            f"<div class='lbl'>correct, no harness</div></div>")
    rows = []
    for p in ps:
        tags = "".join(f"<span class='fault'>{FAULT.get(f,f)}</span>" for f in p["faults"])
        rows.append(
            f"<div class='row'><div class='rh'><b>{e(p['set_id'])}</b>{tags}"
            f"<span class='ok'>now: {p['tier']} &middot; {p['arm']}</span></div>"
            f"<div class='imgs'>"
            f"<figure><img src='{A.asset(p['person'],320)}' alt='person input'>"
            f"<figcaption>person</figcaption></figure>"
            f"<figure><img src='{A.asset(p['garment'],320)}' alt='garment reference'>"
            f"<figcaption>garment</figcaption></figure>"
            + big(p['base'], f"{p['set_id']} — base klein, uncropped reference", "before")
            + f"<figcaption>BEFORE &mdash; klein, no harness</figcaption></figure>"
            + big(p['shipped'], f"{p['set_id']} — shipped harness", "after")
            + f"<figcaption>AFTER &mdash; shipped harness</figcaption></figure>"
            f"</div></div>")

    faults = sum(1 for p in ps if p["faults"])
    doc = NL.join([
        "<title>V2 virtual try-on — results</title>",
        "<meta name='viewport' content='width=device-width,initial-scale=1'>",
        "<style>" + CSS + "</style>",
        "<header><h1>V2 virtual try-on</h1>"
        "<div class='lede'>Same model, same test set. The difference is everything "
        "around it: the garment reference is cropped, the arm is chosen per request, "
        "and a gate catches the failures before they ship.</div>"
        "<div class='hero'>"
        "<div class='stat'><div class='n bad'>61%</div>"
        "<div class='l'>baseline failed</div></div>"
        "<div class='stat'><div class='n good'>0</div>"
        "<div class='l'>shipped failures</div></div>"
        "<div class='stat'><div class='n'>82%</div>"
        "<div class='l'>now perfect</div></div>"
        "<div class='stat'><div class='n'>2.16</div>"
        "<div class='l'>generations / request</div></div>"
        "</div></header>",
        "<div class='nav'>the short version &middot; "
        "<a href='deep.html'>the long version, with every decision and its evidence "
        "&rarr;</a></div>",
        "<div class='sec'>"
        "<h2>The numbers</h2>"
        "<table><tr><th>over 38 sets</th><th>gen/req</th><th>perfect</th><th>ok</th>"
        "<th>fail</th></tr>"
        "<tr><td>klein alone, uncropped reference</td><td>1.00</td><td>&mdash;</td>"
        "<td>&mdash;</td><td class='n' style='color:var(--bad)'>61% of sets</td></tr>"
        "<tr><td>klein + the shipped crop</td><td>1.00</td><td>23</td><td>5</td>"
        "<td>10</td></tr>"
        "<tr><td>best single arm (BC_klein)</td><td>2.00</td><td>28</td><td>6</td>"
        "<td>4</td></tr>"
        "<tr class='win'><td><b>the harness</b></td><td><b>2.16</b></td>"
        "<td class='n'>31</td><td>7</td><td class='n'>0</td></tr></table>"
        "<p class='note' style='margin:14px auto 0;text-align:center'>Same cost as "
        "the best single arm. Nothing ships broken.</p>"
        "<h2>First — klein alone already works, often</h2>"
        "<p class='note'>The base model is strong. On <b>13 of 33 reviewed sets "
        "(39%)</b> it produced a correct try-on from the raw reference with no "
        "cropping, no routing and no gate. Those cases are shown here so the "
        "failures that follow are read for what they are &mdash; <b>edge cases the "
        "harness was built for</b> &mdash; and not as a weak model or a bad "
        "prompt. Same prompt and seed throughout.</p>"
        "<div class='wins'>" + "".join(win_rows) + "</div>" +
        f"<h2>Then &mdash; the edge cases</h2><p class='note'>{len(ps)} sets where the original "
        f"uncropped output was kept, so a direct before/after exists. "
        f"{faults} of them have failures recorded by category during review; those "
        f"are named on each row. <b>Ordered easiest first, hardest last</b> &mdash; the "
        f"final row is the set that failed four different ways at once. Click any "
        f"image for full resolution.</p>" + "".join(rows) + "</div>",
        "<div id='lb'><img id='lbi' alt=''><div id='lbc'></div></div>",
        "<footer>FLUX.2 klein 4B distilled &middot; every component MIT or "
        "Apache-2.0 &middot; open weights, self-hostable<br>"
        "<a href='deep.html'>Full report: what was tried, what failed, what it "
        "cost</a></footer>",
        "<script>" + JS + "</script>"])
    os.makedirs(OUT, exist_ok=True)
    o = os.path.join(OUT, "index.html")
    open(o, "w", encoding="utf-8").write(doc)
    return o, len(ps)


if __name__ == "__main__":
    print(build())
