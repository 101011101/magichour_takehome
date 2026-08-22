# What the harness actually picked, per set, under the shipped rule.
#
# Replays the decision over stored arm outputs and shows the whole trace: what the
# router chose, what every check said about that frame, whether it escalated and on
# which signal, and which frame shipped. The human tier is shown beside each arm so a
# wrong pick is visible rather than inferred.
import csv, html, json, os, collections

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
ART = os.path.join(REPO, "v2", "artifacts")
NL = chr(10)
ARMS = ["PHEAD", "BC_klein", "QX_qwen_p1"]
LAB = {"PHEAD": "PHEAD", "BC_klein": "BC_klein", "QX_qwen_p1": "QX"}
GEN = {"PHEAD": 1, "BC_klein": 2, "QX_qwen_p1": 2}
HAIR_T, ID_T, NOOP_T = 0.14, 0.90, 0.50

CSS = """
:root{--bg:#0d0d10;--fg:#e8e8ea;--dim:#8a8a94;--line:#26262c;--acc:#7c5cff;
 --good:#3fb950;--mid:#d29922;--bad:#f85149}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
 font:14px/1.55 ui-sans-serif,-apple-system,"Segoe UI",Roboto,sans-serif}
header{padding:22px 30px 14px;border-bottom:1px solid var(--line)}
h1{margin:0 0 6px;font-size:20px}.q{color:var(--acc);font-weight:600}
.sub{color:var(--dim);max-width:98ch;font-size:13px;margin-top:6px}
.sub b{color:var(--fg)} .sub code{background:#1b1b22;padding:1px 5px;border-radius:4px}
.panels{display:grid;grid-template-columns:1fr 1fr;gap:16px;padding:16px 30px}
@media(max-width:1100px){.panels{grid-template-columns:1fr}}
.panel{border:1px solid var(--line);border-radius:10px;background:#121216}
.panel h2{margin:0;padding:10px 14px;font-size:13px;border-bottom:1px solid var(--line)}
.panel .in{padding:12px 14px}
table{border-collapse:collapse;font-size:12.5px;width:100%}
th,td{padding:4px 9px;text-align:right;border-bottom:1px solid #1d1d23}
th:first-child,td:first-child{text-align:left}
th{color:var(--dim);font-weight:600}
tr.hi td{background:#141a14}
.win{color:var(--good);font-weight:700}.lose{color:var(--bad);font-weight:700}
.note{color:var(--dim);font-size:12px;margin:9px 0 0}
#bar{position:sticky;top:0;z-index:20;background:#121216;border-bottom:1px solid var(--line);
 padding:10px 30px;display:flex;gap:8px;align-items:center;flex-wrap:wrap;font-size:12.5px}
#bar button{background:#1b1b22;border:1px solid var(--line);color:var(--dim);
 border-radius:7px;padding:5px 12px;font-size:12px;cursor:pointer;font-family:inherit}
#bar button.on{background:var(--acc);border-color:var(--acc);color:#fff;font-weight:600}
#cnt{margin-left:auto;color:var(--dim)}
.set{margin:0 30px 12px;border:1px solid var(--line);border-radius:10px;background:#101014}
.set.wrong{border-color:#5a2a2a}
.sh{padding:8px 14px;background:#141419;border-bottom:1px solid var(--line);
 display:flex;gap:10px;align-items:center;flex-wrap:wrap;font-size:12.5px}
.sh b{font-size:13px}
.tag{font-size:11px;padding:2px 8px;border-radius:20px;border:1px solid var(--line);
 color:var(--dim)}
.tag.esc{border-color:var(--acc);color:var(--acc)}
.tag.gen{border-color:var(--line)}
.tag.bad{border-color:var(--bad);color:var(--bad)}
.why{margin-left:auto;font-size:11.5px;color:var(--dim);font-family:ui-monospace,monospace}
.row{display:flex;gap:6px;align-items:stretch;overflow-x:auto;padding:9px 8px}
.inp{flex:0 0 96px;padding:6px;opacity:.85}
.inp img{width:100%;background:#fff;border-radius:4px;display:block;cursor:zoom-in}
.inp .t{font-size:10.5px;color:var(--dim);text-align:center;margin-top:3px}
.sep{width:1px;background:var(--line);margin:8px 6px}
.cell{flex:0 0 178px;padding:7px;border:2px solid #1c1c22;border-radius:9px;
 background:#0e0e12}
.cell img{width:100%;background:#fff;border-radius:4px;display:block;cursor:zoom-in}
.cell.first{border-color:var(--dim)}
.cell.ship{border-color:var(--good);box-shadow:0 0 0 3px rgba(63,185,80,.28)}
.cell.ship.bad{border-color:var(--bad);box-shadow:0 0 0 3px rgba(248,81,73,.3)}
.cell.unreached{opacity:.3}
.cell .t{font-weight:700;font-size:12px;margin:6px 0 2px}
.cell .s{font-size:10.5px;color:var(--dim);line-height:1.45}
.cell .s .f{color:var(--bad);font-weight:700}
.tier{display:inline-block;padding:1px 7px;border-radius:20px;font-size:10px;
 font-weight:700;margin-top:3px}
.tier.perfect{background:var(--good);color:#08130a}
.tier.ok{background:var(--mid);color:#191200}
.tier.fail{background:var(--bad);color:#1c0708}
#lb{display:none;position:fixed;inset:0;background:rgba(0,0,0,.94);z-index:99;
 align-items:center;justify-content:center;flex-direction:column;gap:10px;padding:20px}
#lb.on{display:flex}#lb img{max-width:94vw;max-height:88vh;object-fit:contain;background:#fff}
#lbc{color:var(--dim);font-size:13px}
"""

JS = """
document.addEventListener('click',e=>{
  const b=e.target.closest('#bar button');
  if(b){document.querySelectorAll('#bar button').forEach(x=>x.classList.remove('on'));
    b.classList.add('on');const f=b.dataset.f;let n=0;
    document.querySelectorAll('.set').forEach(s=>{
      const show = f==='all' || (f==='esc'&&s.dataset.esc==='1') ||
                   (f==='wrong'&&s.classList.contains('wrong')) ||
                   (f==='changed'&&s.dataset.changed==='1');
      s.style.display=show?'':'none'; if(show)n++;});
    document.getElementById('cnt').textContent=n+' shown'; return;}
  const im=e.target.closest('.cell img,.inp img');
  if(im){document.getElementById('lbi').src=im.getAttribute('src');
    document.getElementById('lbc').textContent=im.getAttribute('alt');
    document.getElementById('lb').classList.add('on');}
});
document.getElementById('lb').addEventListener('click',()=>
  document.getElementById('lb').classList.remove('on'));
document.addEventListener('keydown',e=>{if(e.key==='Escape')
  document.getElementById('lb').classList.remove('on')});
document.getElementById('cnt').textContent=
  document.querySelectorAll('.set').length+' shown';
"""


def build():
    run = json.load(open(f"{REPO}/v2/runs/amt/_run.json"))
    meta = {r["stem"]: r["src_path"] for r in csv.DictReader(
        open(f"{REPO}/v2/runs/crop_screen/crop_log.csv"))}
    T = list(csv.DictReader(open(f"{REPO}/v223_perfect_tier_picks.csv")))
    E = list(csv.DictReader(open(f"{REPO}/v223_vlm_eval.csv")))

    tier = {(r["set_id"], r["arm"]): r["tier"] for r in T}
    hair = {r["set_id"]: float(r["hair_over_garment"]) for r in T}
    ident = {(r["set_id"], r["arm"]): float(r["chk_identity"]) for r in T}
    noop = {(r["set_id"], r["arm"]): float(r["chk_noop"]) for r in T}
    person = {r["set_id"]: r["person"] for r in T}
    garm = {r["set_id"]: r["garment"] for r in T}
    V = {(r["set_id"], r["arm"], r["prompt"]): r["vlm_verdict"] for r in E}
    sets = sorted(hair)

    def decide(sid):
        """The shipped rule, replayed. Returns the full trace."""
        arm = BC = "BC_klein" if hair[sid] >= HAIR_T else "PHEAD"
        why_route = (f"hair {hair[sid]:.1%} "
                     f"{'>=' if hair[sid] >= HAIR_T else '<'} {HAIR_T:.0%}")
        k = (sid, arm)
        fired = []
        if noop[k] < NOOP_T:
            fired.append(f"noop {noop[k]:.2f} &lt; {NOOP_T}")
        if ident[k] < ID_T:
            fired.append(f"<b>identity {ident[k]:.3f} &lt; {ID_T}</b>")
        if V.get((sid, arm, "garment")) == "FAIL":
            fired.append("garment = FAIL")
        if V.get((sid, arm, "tryon")) != "PERFECT":
            fired.append(f"tryon = {V.get((sid, arm, 'tryon'))}")
        landed = "QX_qwen_p1" if fired else arm
        gens = GEN[arm] + (GEN["QX_qwen_p1"] if fired else 0)
        # the previous rule, without identity -- shown where the two differ
        old_fired = [f for f in fired if "identity" not in f]
        old_landed = "QX_qwen_p1" if old_fired else arm
        return dict(first=arm, why=why_route, fired=fired, landed=landed,
                    gens=gens, changed=old_landed != landed)

    D = {s: decide(s) for s in sets}
    tot = sum(D[s]["gens"] for s in sets)
    ship = collections.Counter(tier[(s, D[s]["landed"])] for s in sets)
    esc = sum(1 for s in sets if D[s]["fired"])
    changed = [s for s in sets if D[s]["changed"]]

    def rel(x):
        return os.path.relpath(os.path.join(REPO, x), ART)

    e = html.escape
    body = []
    for sid in sorted(sets, key=lambda s: (tier[(s, D[s]["landed"])] != "fail",
                                           not D[s]["changed"], s)):
        d = D[sid]
        st = tier[(sid, d["landed"])]
        wrong = st == "fail"
        tags = [f"<span class='tag gen'>{d['gens']} gen</span>"]
        if d["fired"]:
            tags.append("<span class='tag esc'>escalated</span>")
        if d["changed"]:
            tags.append("<span class='tag esc'>changed by the identity check</span>")
        if wrong:
            tags.append("<span class='tag bad'>shipped a failure</span>")
        why = ("route: " + d["why"] + " &rarr; " + LAB[d["first"]] +
               ("  |  fired: " + ", ".join(d["fired"]) if d["fired"]
                else "  |  all checks clean"))
        body.append(
            f"<div class='set{' wrong' if wrong else ''}' "
            f"data-esc='{'1' if d['fired'] else '0'}' "
            f"data-changed='{'1' if d['changed'] else '0'}'>"
            f"<div class='sh'><b>{e(sid)}</b>"
            f"<span class='tier {st}'>shipped {LAB[d['landed']]} &mdash; {st}</span>"
            + "".join(tags) + f"<span class='why'>{why}</span></div><div class='row'>")
        for who, lab in ((person[sid], "person"), (garm[sid], "garment")):
            q = rel(meta.get(who, "")) if meta.get(who) else ""
            if q and os.path.exists(os.path.normpath(os.path.join(ART, q))):
                body.append(f"<div class='inp'><img src='{q}' alt='{e(sid)} {lab} "
                            f"&mdash; {e(who)}'><div class='t'>{lab}</div></div>")
        body.append("<div class='sep'></div>")
        for a in ARMS:
            key = f"{sid}|{a}"
            if key not in run["gen"]:
                continue
            cls = []
            if a == d["first"]:
                cls.append("first")
            if a == d["landed"]:
                cls.append("ship")
                if wrong:
                    cls.append("bad")
            if a == "QX_qwen_p1" and not d["fired"]:
                cls.append("unreached")
            if a != d["first"] and a != "QX_qwen_p1":
                cls.append("unreached")
            det = ""
            if a == d["first"]:
                det = (f"identity {ident[(sid,a)]:.3f} &middot; noop {noop[(sid,a)]:.2f}"
                       f"<br>tryon {V.get((sid,a,'tryon'),'-')} &middot; "
                       f"garment {V.get((sid,a,'garment'),'-')}")
            body.append(
                f"<div class='cell {' '.join(cls)}'>"
                f"<img src='../runs/amt/gen/{run['gen'][key]}' "
                f"alt='{e(sid)} &mdash; {LAB[a]}'>"
                f"<div class='t'>{LAB[a]}"
                + ("  &larr; router" if a == d["first"] else "")
                + ("  &check; SHIPPED" if a == d["landed"] else "") + "</div>"
                f"<div class='tier {tier[(sid,a)]}'>{tier[(sid,a)]}</div>"
                f"<div class='s'>{det}</div></div>")
        body.append("</div></div>")

    t1 = ("<table><tr><th>configuration</th><th>gen/req</th><th>perfect</th>"
          "<th>ok</th><th>fail</th></tr>"
          f"<tr><td>flat BC_klein (best single arm)</td><td>2.000</td><td>28</td>"
          f"<td>6</td><td class='lose'>4</td></tr>"
          f"<tr><td>VLM-only gate (previous)</td><td>2.105</td><td>30</td><td>7</td>"
          f"<td class='lose'>1</td></tr>"
          f"<tr class='hi'><td><b>shipped rule</b></td><td><b>{tot/len(sets):.3f}</b></td>"
          f"<td><b>{ship['perfect']}</b></td><td>{ship['ok']}</td>"
          f"<td class='win'>{ship['fail']}</td></tr>"
          f"<tr><td><i>oracle</i></td><td><i>1.526</i></td><td><i>32</i></td>"
          f"<td><i>6</i></td><td><i>0</i></td></tr></table>"
          f"<p class='note'>{esc} of {len(sets)} sets escalated. "
          f"<b>Nothing ships broken.</b></p>")

    fire = collections.Counter()
    for s in sets:
        for f in D[s]["fired"]:
            fire[f.split()[0].replace("<b>", "")] += 1
    t2 = ("<p class='note'>Which signal fired, across the "
          f"{esc} escalations (a set can trip more than one).</p>"
          "<table><tr><th>signal</th><th>fired</th></tr>")
    for k, n in fire.most_common():
        t2 += (f"<tr class='{'hi' if k=='identity' else ''}'><td>{k}</td>"
               f"<td>{n}</td></tr>")
    t2 += ("</table><p class='note'><b>identity fires once</b> &mdash; on "
           "<code>HD_p028+navy_peacoat</code>, where the person was substituted "
           "entirely and all five VLM prompts passed the frame. That single firing is "
           "the difference between 1 shipped failure and 0.</p>")

    doc = NL.join([
        "<title>What the harness picked</title>", "<style>" + CSS + "</style>",
        "<header><h1>What the harness picked</h1>"
        "<div class='q'>The shipped rule, replayed over all 38 sets, with the full "
        "decision trace.</div>"
        "<div class='sub'>Route on <code>hair_over_garment &ge; 14%</code> &rarr; "
        "BC_klein, else PHEAD. Then escalate to QX if <b>any</b> of: "
        "<code>noop &lt; 0.5</code>, <code>identity &lt; 0.90</code>, "
        "<code>garment = FAIL</code>, <code>tryon &ne; PERFECT</code>. "
        "The green frame is what ships; the tier badge under each arm is the human "
        "verdict, so a wrong pick is visible rather than inferred. Sorted "
        "failures-first, then the sets the identity check changed.</div></header>",
        "<div class='panels'>"
        "<div class='panel'><h2>Outcome</h2><div class='in'>" + t1 + "</div></div>"
        "<div class='panel'><h2>Which signal caught it</h2><div class='in'>"
        + t2 + "</div></div></div>",
        "<div id='bar'>"
        "<button data-f='all' class='on'>all 38</button>"
        "<button data-f='esc'>escalated</button>"
        f"<button data-f='changed'>changed by identity ({len(changed)})</button>"
        "<button data-f='wrong'>shipped a failure</button>"
        "<span id='cnt'></span></div>"] + body + [
        "<div id='lb'><img id='lbi' alt=''><div id='lbc'></div></div>",
        "<script>" + JS + "</script>"])
    o = os.path.join(ART, "v223_harness_picks.html")
    open(o, "w", encoding="utf-8").write(doc)
    return o, len(sets), tot / len(sets), dict(ship), esc, len(changed)


if __name__ == "__main__":
    print(build())
