# Every failure, per arm, with what rescued it.
#
# This is the complementarity claim shown rather than asserted: three of BC_klein's
# four failures are also PHEAD failures, because both subtract. QX fails once, on a
# set the other two both get perfect.
import csv, glob, html, json, os

import report_assets as A

REPO, OUT, NL = A.REPO, A.OUT, chr(10)
ARMS = ["PHEAD", "BC_klein", "QX_qwen_p1"]
LAB = {"PHEAD": "PHEAD", "BC_klein": "BC_klein", "QX_qwen_p1": "QX"}
MECH = {"PHEAD": "subtract", "BC_klein": "subtract", "QX_qwen_p1": "regenerate"}

CSS = """
:root{--bg:#0d0d10;--fg:#e8e8ea;--dim:#8a8a94;--line:#26262c;--acc:#7c5cff;
 --good:#3fb950;--mid:#d29922;--bad:#f85149}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
 font:15px/1.6 ui-sans-serif,-apple-system,"Segoe UI",Roboto,sans-serif}
a{color:var(--acc)}
header{padding:36px 30px 24px;border-bottom:1px solid var(--line)}
.wrap{max-width:1120px;margin:0 auto;padding:0 30px}
h1{margin:0 0 8px;font-size:26px;letter-spacing:-.3px}
.lede{color:var(--dim);max-width:80ch;font-size:14px}
.lede b{color:var(--fg)}
h2{font-size:19px;margin:44px 0 4px;padding-top:14px;border-top:1px solid var(--line)}
h2 .m{font-size:12px;color:var(--dim);font-weight:400;text-transform:uppercase;
 letter-spacing:1px;display:block;margin-bottom:4px}
.nav{padding:12px 30px;text-align:center;border-bottom:1px solid var(--line);
 background:#121216;font-size:13px}
table{border-collapse:collapse;font-size:13px;margin:14px 0}
th,td{padding:6px 12px;border-bottom:1px solid #1d1d23;text-align:right}
th:first-child,td:first-child{text-align:left}
th{color:var(--dim);font-weight:600}
.bad{color:var(--bad);font-weight:700}.good{color:var(--good);font-weight:700}
.mid{color:var(--mid)}
.q{border-left:3px solid var(--acc);padding:2px 0 2px 14px;margin:16px 0;max-width:84ch}
.q b{color:#fff}
.case{border:1px solid var(--line);border-radius:10px;background:#101014;
 margin:14px 0;overflow:hidden}
.case.unsolved{border-color:#5a2a2a}
.ch{padding:8px 14px;background:#141419;border-bottom:1px solid var(--line);
 display:flex;gap:10px;align-items:center;flex-wrap:wrap;font-size:12.5px}
.ch b{font-size:13px}
.pill{font-size:10.5px;padding:2px 8px;border-radius:20px;border:1px solid var(--line);
 color:var(--dim)}
.pill.r{border-color:var(--good);color:var(--good);margin-left:auto}
.pill.x{border-color:var(--bad);color:var(--bad);margin-left:auto}
.strip{display:grid;grid-template-columns:110px 110px repeat(3,1fr);gap:3px;padding:9px}
@media(max-width:860px){.strip{grid-template-columns:1fr 1fr 1fr}}
figure{margin:0}
figure img{width:100%;display:block;background:#fff;border-radius:5px;cursor:zoom-in}
figcaption{font-size:10.5px;color:var(--dim);text-align:center;padding:4px 2px;
 line-height:1.35}
figure.fail img{outline:2px solid var(--bad);outline-offset:-2px}
figure.fail figcaption{color:var(--bad);font-weight:700}
figure.win img{outline:2px solid var(--good);outline-offset:-2px}
figure.win figcaption{color:var(--good);font-weight:700}
#lb{display:none;position:fixed;inset:0;background:rgba(0,0,0,.95);z-index:99;
 align-items:center;justify-content:center;flex-direction:column;gap:10px;padding:20px}
#lb.on{display:flex}#lb img{max-width:95vw;max-height:90vh;object-fit:contain;background:#fff}
#lbc{color:var(--dim);font-size:13px}
footer{border-top:1px solid var(--line);margin-top:44px;padding:24px 30px;
 color:var(--dim);font-size:12.5px}
code{background:#1b1b22;padding:1px 5px;border-radius:4px;font-size:12.5px}
"""
JS = """
document.addEventListener('click',e=>{const im=e.target.closest('figure img');
  if(!im)return;document.getElementById('lbi').src=im.dataset.full||im.getAttribute('src');
  document.getElementById('lbc').textContent=im.getAttribute('alt');
  document.getElementById('lb').classList.add('on');});
document.getElementById('lb').addEventListener('click',()=>
  document.getElementById('lb').classList.remove('on'));
document.addEventListener('keydown',e=>{if(e.key==='Escape')
  document.getElementById('lb').classList.remove('on')});
"""


def build():
    run = json.load(open(f"{REPO}/v2/runs/amt/_run.json"))
    T = list(csv.DictReader(open(f"{REPO}/v223_perfect_tier_picks.csv")))
    meta = {r["stem"]: r["src_path"] for r in csv.DictReader(
        open(f"{REPO}/v2/runs/crop_screen/crop_log.csv"))}
    tier = {(r["set_id"], r["arm"]): r["tier"] for r in T}
    info = {r["set_id"]: r for r in T}
    sets = sorted(info)
    e = html.escape

    def im(src, alt, cls="", mw=420):
        a = A.asset(src, mw, hires=True)
        if not a:
            return ""
        return (f"<figure class='{cls}'><img src='{a}' "
                f"data-full='{a.replace('.jpg','@2x.jpg')}' alt='{e(alt)}'>"
                f"<figcaption>{alt}</figcaption></figure>")

    secs = []
    for arm in ARMS:
        fails = [s for s in sets if tier.get((s, arm)) == "fail"]
        cases = []
        for s in fails:
            r = info[s]
            others = [o for o in ARMS if o != arm]
            resc = [o for o in others if tier.get((s, o)) == "perfect"]
            shared = [o for o in others if tier.get((s, o)) == "fail"]
            tag = (f"<span class='pill r'>rescued by {LAB[resc[0]]}</span>" if resc
                   else "<span class='pill x'>no arm reaches perfect</span>")
            body = (im(meta.get(r["person"], ""), "person", "", 200)
                    + im(meta.get(r["garment"], ""), "garment", "", 200))
            for o in [arm] + others:
                k = f"{s}|{o}"
                if k not in run["gen"]:
                    continue
                t = tier.get((s, o), "")
                cls = "fail" if t == "fail" else ("win" if t == "perfect" else "")
                body += im(f"{REPO}/v2/runs/amt/gen/{run['gen'][k]}",
                           f"{LAB[o]} — {t}", cls)
            cases.append(
                f"<div class='case{' unsolved' if not resc else ''}'>"
                f"<div class='ch'><b>{e(s)}</b>"
                f"<span class='pill'>hair {float(r['hair_over_garment']):.1%}</span>"
                + (f"<span class='pill'>also fails {LAB[shared[0]]}</span>" if shared else "")
                + tag + f"</div><div class='strip'>{body}</div></div>")
        c = {t: sum(1 for s in sets if tier.get((s, t and arm)) == t) for t in
             ("perfect", "ok", "fail")}
        secs.append((arm, len(fails), c, "".join(cases)))

    # overlap: the claim that subtract-arms share failures
    pf = {s for s in sets if tier.get((s, "PHEAD")) == "fail"}
    bf = {s for s in sets if tier.get((s, "BC_klein")) == "fail"}
    qf = {s for s in sets if tier.get((s, "QX_qwen_p1")) == "fail"}
    unsolved = [s for s in sets if all(tier.get((s, a)) != "perfect" for a in ARMS)]

    body = "".join(
        f"<h2 id='{arm}'><span class='m'>{MECH[arm]}</span>{LAB[arm]} — "
        f"{n} failure{'s' if n != 1 else ''} of 38"
        f"<span style='font-size:13px;color:var(--dim);font-weight:400'> · "
        f"{c['perfect']} perfect / {c['ok']} ok</span></h2>{cases}"
        for arm, n, c, cases in secs)

    doc = NL.join([
        "<title>Every failure, and what rescued it</title>",
        "<meta name='viewport' content='width=device-width,initial-scale=1'>",
        "<style>" + CSS + "</style>",
        "<header><div class='wrap'><h1>Every failure, and what rescued it</h1>"
        "<p class='lede'>All 15 arm failures across the 38 evaluation sets. Each row "
        "shows the inputs, the arm that failed, and what the other two produced on "
        "the same set. <b>The failing frame is outlined red, a perfect one "
        "green.</b> This is the complementarity claim shown rather than asserted.</p>"
        "</div></header>",
        "<div class='nav'><a href='index.html'>&larr; short report</a> &middot; "
        "<a href='deep.html'>full report</a> &middot; every failure</div>",
        "<div class='wrap'>"
        "<table><tr><th>arm</th><th>mechanism</th><th>perfect</th><th>ok</th>"
        "<th>fail</th></tr>"
        + "".join(f"<tr><td><a href='#{a}'>{LAB[a]}</a></td><td>{MECH[a]}</td>"
                  f"<td class='good'>{c['perfect']}</td><td class='mid'>{c['ok']}</td>"
                  f"<td class='bad'>{n}</td></tr>" for a, n, c, _ in secs)
        + "</table>"
        f"<div class='q'><b>{len(pf & bf)} of BC_klein's {len(bf)} failures are also "
        f"PHEAD failures.</b> Both arms <i>subtract</i> — they cut the head out of "
        "the reference — so when the crop destroys the garment, neither can recover "
        "what it never saw. QX <i>regenerates</i>, and its single failure "
        f"(<code>p017+p002</code>) is on a set both subtractive arms get perfect. "
        "The mechanisms fail on different things, which is the whole reason the "
        "escalation works.</div>"
        f"<div class='q'><b>14 of 15 failures are rescued by another arm.</b> The "
        f"exception is <code>{e(unsolved[0]) if unsolved else '—'}</code>, where no "
        "arm reaches perfect and QX's <i>ok</i> is the ceiling — the one case in 38 "
        "the three arms cannot solve between them.</div>"
        + body + "</div>",
        "<div id='lb'><img id='lbi' alt=''><div id='lbc'></div></div>",
        "<footer><div class='wrap'>Tiers are one reviewer's absolute judgement over "
        "114 cells: <b>perfect</b> = ship unchanged, <b>ok</b> = acceptable but "
        "improvable, <b>fail</b> = unusable. Click any image for full "
        "resolution.</div></footer>",
        "<script>" + JS + "</script>"])
    os.makedirs(OUT, exist_ok=True)
    o = os.path.join(OUT, "failures.html")
    open(o, "w", encoding="utf-8").write(doc)
    return o, sum(n for _, n, _, _ in secs)


if __name__ == "__main__":
    print(build())
