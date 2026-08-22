# VLM gate evaluation review page.
#
# Five prompts against 114 human-tiered outputs, plus the production simulation.
# Rows are ordered worst-disagreement first, because the aggregate accuracy hides
# the thing that matters: which KIND of failure each prompt is blind to.
import csv, html, json, os, collections

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
ART = os.path.join(REPO, "v2", "artifacts")
NL = chr(10)
PROMPTS = ["artefact", "usable", "tryon", "garment", "transfer"]
BAD = {"FAIL", "BROKEN"}
GEN = {"PHEAD": 1, "BC_klein": 2, "QX_qwen_p1": 2}

CSS = """
:root{--bg:#0d0d10;--fg:#e8e8ea;--dim:#8a8a94;--line:#26262c;--acc:#7c5cff;
 --good:#3fb950;--mid:#d29922;--bad:#f85149}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
 font:14px/1.55 ui-sans-serif,-apple-system,"Segoe UI",Roboto,sans-serif}
header{padding:22px 30px 16px;border-bottom:1px solid var(--line)}
h1{margin:0 0 6px;font-size:20px}
.q{color:var(--acc);font-weight:600;font-size:14px}
.sub{color:var(--dim);max-width:96ch;font-size:13px;margin-top:6px}
.sub b{color:var(--fg)} .sub code{background:#1b1b22;padding:1px 5px;border-radius:4px}
.panels{display:grid;grid-template-columns:1fr 1fr;gap:16px;padding:16px 30px}
@media(max-width:1150px){.panels{grid-template-columns:1fr}}
.panel{border:1px solid var(--line);border-radius:10px;background:#121216;overflow:hidden}
.panel h2{margin:0;padding:10px 14px;font-size:13px;border-bottom:1px solid var(--line)}
.panel .in{padding:12px 14px}
table{border-collapse:collapse;font-size:12.5px;width:100%}
th,td{padding:4px 8px;text-align:right;border-bottom:1px solid #1d1d23}
th:first-child,td:first-child{text-align:left}
th{color:var(--dim);font-weight:600}
tr.hi td{background:#141a14}
.win{color:var(--good);font-weight:700}
.lose{color:var(--bad);font-weight:700}
.note{color:var(--dim);font-size:12px;margin:9px 0 0}
.key{margin:6px 30px 18px;border-left:3px solid var(--acc);padding:2px 0 2px 12px;
 max-width:110ch;font-size:13px}
.key b{color:#fff}
#bar{position:sticky;top:0;z-index:20;background:#121216;border-bottom:1px solid var(--line);
 padding:10px 30px;display:flex;gap:8px;align-items:center;flex-wrap:wrap;font-size:12.5px}
#bar button{background:#1b1b22;border:1px solid var(--line);color:var(--dim);
 border-radius:7px;padding:5px 12px;font-size:12px;cursor:pointer;font-family:inherit}
#bar button.on{background:var(--acc);border-color:var(--acc);color:#fff;font-weight:600}
#count{margin-left:auto;color:var(--dim)}
.row{display:flex;gap:12px;align-items:center;margin:0 30px 8px;padding:8px;
 border:1px solid var(--line);border-radius:9px;background:#101014}
.row.dis{border-color:#4a2a2a;background:#150f10}
.row img{height:118px;background:#fff;border-radius:4px;display:block;cursor:zoom-in}
.meta{flex:0 0 250px;font-size:12px}
.meta .sid{font-weight:700;font-size:12.5px;word-break:break-all}
.meta .m{color:var(--dim);font-size:11.5px;margin-top:3px}
.tier{display:inline-block;padding:1px 8px;border-radius:20px;font-size:11px;
 font-weight:700;margin-top:5px}
.tier.perfect{background:var(--good);color:#08130a}
.tier.ok{background:var(--mid);color:#191200}
.tier.fail{background:var(--bad);color:#1c0708}
.chips{display:flex;gap:6px;flex-wrap:wrap;flex:1}
.chip{border:1px solid var(--line);border-radius:7px;padding:5px 9px;min-width:96px}
.chip .p{font-size:10.5px;color:var(--dim);text-transform:uppercase;letter-spacing:.4px}
.chip .v{font-weight:700;font-size:12.5px;margin-top:2px}
.chip.agree{border-color:#24402a}.chip.agree .v{color:var(--good)}
.chip.miss{border-color:#4a2325}.chip.miss .v{color:var(--bad)}
.chip.over{border-color:#4a3f1e}.chip.over .v{color:var(--mid)}
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
    document.querySelectorAll('.row').forEach(r=>{
      const show = f==='all' || (f==='dis'&&r.classList.contains('dis')) ||
                   (f==='fail'&&r.dataset.tier==='fail') ||
                   (f==='esc'&&r.dataset.esc==='1');
      r.style.display=show?'':'none'; if(show)n++;});
    document.getElementById('count').textContent=n+' shown';return}
  const im=e.target.closest('.row img');
  if(im){document.getElementById('lbi').src=im.getAttribute('src');
    document.getElementById('lbc').textContent=im.getAttribute('alt');
    document.getElementById('lb').classList.add('on');}
});
document.getElementById('lb').addEventListener('click',()=>
  document.getElementById('lb').classList.remove('on'));
document.addEventListener('keydown',e=>{if(e.key==='Escape')
  document.getElementById('lb').classList.remove('on')});
document.getElementById('count').textContent=
  document.querySelectorAll('.row').length+' shown';
"""


def build():
    run = json.load(open(f"{REPO}/v2/runs/amt/_run.json"))
    meta = {r["stem"]: r["src_path"] for r in csv.DictReader(
        open(f"{REPO}/v2/runs/crop_screen/crop_log.csv"))}
    T = list(csv.DictReader(open(f"{REPO}/v223_perfect_tier_picks.csv")))
    E = list(csv.DictReader(open(f"{REPO}/v223_vlm_eval.csv")))
    P = list(csv.DictReader(open(f"{REPO}/v223_vlm_pairwise.csv")))

    tier = {(r["set_id"], r["arm"]): r["tier"] for r in T}
    hair = {r["set_id"]: float(r["hair_over_garment"]) for r in T}
    garm = {r["set_id"]: r["garment"] for r in T}
    noop = {(r["set_id"], r["arm"]): float(r["chk_noop"]) for r in T}
    V = {(r["set_id"], r["arm"], r["prompt"]): r["vlm_verdict"] for r in E}
    sets = sorted({s for s, _ in tier})
    first = {k: ("BC_klein" if hair[k] >= 0.14 else "PHEAD") for k in sets}
    model = E[0].get("model", "?")

    # ---- per-prompt metrics over all 114 cells
    rows_m, base = [], None
    for pid in PROMPTS:
        s = [r for r in E if r["prompt"] == pid]
        if not s:
            continue
        fires = [r["vlm_verdict"] in BAD for r in s]
        should = [r["human_tier"] != "perfect" for r in s]
        tp = sum(f and h for f, h in zip(fires, should))
        fp = sum(f and not h for f, h in zip(fires, should))
        fn = sum((not f) and h for f, h in zip(fires, should))
        tn = sum((not f) and (not h) for f, h in zip(fires, should))
        hard = [r for r in s if r["human_tier"] == "fail"]
        base = sum(1 for r in s if r["human_tier"] == "perfect") / len(s)
        rows_m.append((pid, sum(fires), (tp + tn) / len(s), tp / max(tp + fp, 1),
                       tp / max(tp + fn, 1),
                       sum(1 for r in hard if r["vlm_verdict"] in BAD) / max(len(hard), 1)))

    # ---- production simulation on the 38 first-arm outputs
    def sim(fire):
        tot, sh, e = 0, collections.Counter(), 0
        for k in sets:
            a = first[k]
            tot += GEN[a]
            if not fire(k, a):
                sh[tier[(k, a)]] += 1
                continue
            e += 1
            tot += 2
            sh[tier[(k, "QX_qwen_p1")]] += 1
        return tot / len(sets), sh, e

    sims = [("no gate — ship the first arm", lambda k, a: False),
            ("crash guard (no-op) only", lambda k, a: noop[(k, a)] < 0.5)]
    for pid in PROMPTS:
        sims.append((f"VLM · {pid}", (lambda p: lambda k, a: V.get((k, a, p)) in BAD)(pid)))
    sims.append(("ORACLE — a perfect gate", lambda k, a: tier[(k, a)] == "fail"))

    sim_rows = []
    for nm, f in sims:
        g, sh, e = sim(f)
        sim_rows.append((nm, g, sh["perfect"], sh["ok"], sh["fail"], e))

    # ---- did the hair router pick the right arm?
    RANK = {"perfect": 0, "ok": 1, "fail": 2}
    oth = {"PHEAD": "BC_klein", "BC_klein": "PHEAD"}
    rb = rw = rt = 0
    wrong = []
    for k in sets:
        a = first[k]
        d = RANK[tier[(k, a)]] - RANK[tier[(k, oth[a])]]
        if d < 0:
            rb += 1
        elif d > 0:
            rw += 1
            wrong.append((k, a, tier[(k, a)], tier[(k, oth[a])]))
        else:
            rt += 1

    def arm_only(pick):
        c = collections.Counter(tier[(k, pick(k))] for k in sets)
        g = sum(GEN[pick(k)] for k in sets) / len(sets)
        return g, c
    router_rows = [
        ("always PHEAD", *arm_only(lambda k: "PHEAD")),
        ("always BC_klein", *arm_only(lambda k: "BC_klein")),
        ("hair router at 14%", *arm_only(lambda k: first[k])),
        ("oracle (best of the two)", *arm_only(
            lambda k: min(("PHEAD", "BC_klein"), key=lambda a: RANK[tier[(k, a)]]))),
    ]

    # ---- vote across the five prompts
    votes = {}
    for (sid, arm) in tier:
        votes[(sid, arm)] = sum(1 for p in PROMPTS
                                if V.get((sid, arm, p)) in BAD)
    vote_rows = []
    for n in range(4):
        sel = [k for k in votes if votes[k] == n]
        c = collections.Counter(tier[k] for k in sel)
        vote_rows.append((n, len(sel), c["perfect"], c["ok"], c["fail"]))
    vote_rows.append((4, sum(1 for k in votes if votes[k] >= 4),
                      sum(1 for k in votes if votes[k] >= 4 and tier[k] == "perfect"),
                      sum(1 for k in votes if votes[k] >= 4 and tier[k] == "ok"),
                      sum(1 for k in votes if votes[k] >= 4 and tier[k] == "fail")))

    def gate_sim(fire):
        tot, sh, e = 0, collections.Counter(), 0
        for k in sets:
            a = first[k]
            tot += GEN[a]
            if fire((k, a)):
                e += 1
                tot += 2
                sh[tier[(k, "QX_qwen_p1")]] += 1
            else:
                sh[tier[(k, a)]] += 1
        return tot / len(sets), sh, e
    cmp_rows = []
    for nm, f in (("vote &ge; 1 of 5", lambda k: votes[k] >= 1),
                  ("vote &ge; 2 of 5", lambda k: votes[k] >= 2),
                  ("garment alone", lambda k: V.get((k[0], k[1], "garment")) in BAD)):
        g, sh, e = gate_sim(f)
        cmp_rows.append((nm, g, sh["perfect"], sh["ok"], sh["fail"], e))

    # ---- "only PERFECT ships": the reviewer's rule, and why the vocabulary blocks it
    vocab = {pid: collections.Counter(V.get((sid, arm, pid))
                                      for (sid, arm) in tier) for pid in PROMPTS}

    def gsim(fire):
        tot, sh, e = 0, collections.Counter(), 0
        for k in sets:
            a = first[k]
            tot += GEN[a]
            if fire((k, a)):
                e += 1
                tot += 2
                sh[tier[(k, "QX_qwen_p1")]] += 1
            else:
                sh[tier[(k, a)]] += 1
        return tot / len(sets), sh, e
    perf_rows = []
    for nm, f in (("garment == FAIL", lambda k: V.get((k[0], k[1], "garment")) == "FAIL"),
                  ("tryon != PERFECT", lambda k: V.get((k[0], k[1], "tryon")) != "PERFECT"),
                  ("tryon != PERFECT <b>or</b> garment == FAIL",
                   lambda k: V.get((k[0], k[1], "tryon")) != "PERFECT"
                   or V.get((k[0], k[1], "garment")) == "FAIL"),
                  ("<i>oracle &mdash; escalate every non-perfect</i>",
                   lambda k: tier[k] != "perfect")):
        g, sh, e = gsim(f)
        perf_rows.append((nm, g, sh["perfect"], sh["ok"], sh["fail"], e))

    # ---- tie-break by independent scoring, which has no position to be biased by
    escl = [k for k in sets if tier[(k, first[k])] == "fail"]
    def npass(k):
        return sum(1 for pid in PROMPTS
                   if V.get((k[0], k[1], pid)) in ("PERFECT", "CLEAN", "OK"))
    tb = []
    for k in escl:
        a = first[k]
        sa, sb = npass((k, a)), npass((k, "QX_qwen_p1"))
        pick = "QX" if sb > sa else (a.split("_")[0] if sa > sb else "tie &rarr; QX")
        tb.append((k, a, tier[(k, a)], sa, tier[(k, "QX_qwen_p1")], sb, pick,
                   not pick.startswith(a.split("_")[0])))

    # ---- pairwise summary
    cons = sum(1 for p in P if str(p["consistent"]).lower() == "true")
    esc = [p for p in P if str(p["escalates"]).lower() == "true"]
    harm = sum(1 for p in esc if p["pick_ab"] == "A")

    # ---- per-cell rows, worst disagreement first
    def rel(x):
        return os.path.relpath(os.path.join(REPO, x), ART)

    cells = []
    for (sid, arm), tv in tier.items():
        vs = {p: V.get((sid, arm, p), "-") for p in PROMPTS}
        should = tv != "perfect"
        miss = sum(1 for p in PROMPTS if should and vs[p] not in BAD)
        over = sum(1 for p in PROMPTS if not should and vs[p] in BAD)
        cells.append((sid, arm, tv, vs, miss, over,
                      arm == first[sid], tier[(sid, arm)] == "fail" and arm == first[sid]))
    cells.sort(key=lambda c: (-(c[2] == "fail") * 10 - c[4] - c[5], c[0]))

    e = html.escape
    body = []
    for sid, arm, tv, vs, miss, over, isfirst, isesc in cells:
        key = f"{sid}|{arm}"
        if key not in run["gen"]:
            continue
        gp = f"../runs/amt/gen/{run['gen'][key]}"
        ref = rel(meta.get(garm[sid], "")) if meta.get(garm[sid]) else ""
        chips = []
        for p in PROMPTS:
            v = vs[p]
            fired = v in BAD
            cls = ("agree" if fired == (tv != "perfect") else
                   ("miss" if (tv != "perfect") else "over"))
            chips.append(f"<div class='chip {cls}'><div class='p'>{p}</div>"
                         f"<div class='v'>{e(v)}</div></div>")
        body.append(
            f"<div class='row{' dis' if (miss or over) else ''}' data-tier='{tv}' "
            f"data-esc='{'1' if isesc else '0'}'>"
            + (f"<img src='{ref}' alt='{e(sid)} garment reference'>" if ref else "")
            + f"<img src='{gp}' alt='{e(sid)} — {arm}'>"
            f"<div class='meta'><div class='sid'>{e(sid)}</div>"
            f"<div class='m'>{arm}{' · FIRST ARM' if isfirst else ''} · hair "
            f"{hair[sid]:.1%}</div>"
            f"<div class='tier {tv}'>human: {tv}</div></div>"
            f"<div class='chips'>{''.join(chips)}</div></div>")

    t1 = ("<table><tr><th>prompt</th><th>fires</th><th>acc</th><th>prec</th>"
          "<th>recall</th><th>catches fail</th></tr>")
    for pid, nf, acc, pr, rc, cf in rows_m:
        w = "win" if acc > base else "lose"
        t1 += (f"<tr class='{'hi' if acc>base else ''}'><td>{pid}</td><td>{nf}</td>"
               f"<td class='{w}'>{acc:.1%}</td><td>{pr:.0%}</td><td>{rc:.0%}</td>"
               f"<td>{cf:.0%}</td></tr>")
    t1 += (f"<tr><td><i>accept everything</i></td><td>0</td><td><i>{base:.1%}</i></td>"
           "<td>&mdash;</td><td>0%</td><td>0%</td></tr></table>"
           "<p class='note'>A prompt only earns its place above the "
           "accept-everything row. <b>Only <code>garment</code> does.</b></p>")

    t2 = ("<table><tr><th>gate</th><th>gen/req</th><th>perfect</th><th>ok</th>"
          "<th>fail</th><th>esc</th></tr>")
    for nm, g, p_, o_, f_, ec in sim_rows:
        cl = "hi" if nm.endswith("garment") else ""
        t2 += (f"<tr class='{cl}'><td>{nm}</td><td>{g:.3f}</td><td>{p_}</td>"
               f"<td>{o_}</td><td class='{'win' if f_==0 else 'lose' if f_>3 else ''}'>"
               f"{f_}</td><td>{ec}</td></tr>")
    t3 = ("<p class='note'>Chose <b>BC_klein</b> above 14% hair-over-garment, "
          "<b>PHEAD</b> below.</p><table><tr><th>outcome vs the other arm</th>"
          "<th>sets</th></tr>"
          f"<tr><td>picked the strictly <b>better</b> arm</td><td class='win'>{rb}</td></tr>"
          f"<tr><td>tie &mdash; both the same tier</td><td>{rt}</td></tr>"
          f"<tr><td>picked the strictly <b>worse</b> arm</td><td class='lose'>{rw}</td></tr>"
          "</table>"
          f"<p class='note'><b>Never-worse on {(rb+rt)/len(sets):.0%} of sets.</b></p>"
          "<table><tr><th>strategy</th><th>gen/req</th><th>perfect</th><th>ok</th>"
          "<th>fail</th></tr>")
    for nm, g, c in router_rows:
        cl = "hi" if "router" in nm else ""
        t3 += (f"<tr class='{cl}'><td>{nm}</td><td>{g:.3f}</td><td>{c['perfect']}</td>"
               f"<td>{c['ok']}</td><td>{c['fail']}</td></tr>")
    t3 += "</table><p class='note'>The two it got wrong, both just under the cut:<br>"
    for wk, wa, w_mine, w_other in wrong:      # not `tb`: that name is the tie-break
        t3 += (f"<code>{e(wk[:40])}</code> hair {hair[wk]:.1%} &mdash; chose "
               f"{wa.split('_')[0]}={w_mine}, other={w_other}<br>")
    t3 += "</p>"

    t4 = ("<p class='note'>How many of the five prompts voted to escalate, against "
          "what you actually marked.</p><table><tr><th>votes</th><th>cells</th>"
          "<th>perfect</th><th>ok</th><th>fail</th></tr>")
    for n, tot_, p_, o_, f_ in vote_rows:
        lab = f"{n}+" if n == 4 else str(n)
        t4 += (f"<tr class='{'hi' if n>=2 and tot_ else ''}'><td>{lab}</td><td>{tot_}</td>"
               f"<td>{p_}</td><td>{o_}</td><td>{f_}</td></tr>")
    t4 += ("</table><p class='note'>Monotone, and <b>two or more votes is never "
           "<i>perfect</i></b> &mdash; but only 6 cells reach it.</p>"
           "<table><tr><th>gate</th><th>gen/req</th><th>perfect</th><th>ok</th>"
           "<th>fail</th><th>esc</th></tr>")
    for nm, g, p_, o_, f_, ec in cmp_rows:
        cl = "hi" if nm == "garment alone" else ""
        t4 += (f"<tr class='{cl}'><td>{nm}</td><td>{g:.3f}</td><td>{p_}</td><td>{o_}</td>"
               f"<td>{f_}</td><td>{ec}</td></tr>")
    t5 = ("<p class='note'>Only <code>PERFECT</code> ships; <code>OK</code> escalates. "
          "The obstacle is the model's own vocabulary &mdash; three of the five "
          "prompts <b>never once said PERFECT</b>, so for them the rule means "
          "escalate everything.</p><table><tr><th>prompt</th><th>verdicts it used</th>"
          "</tr>")
    for pid in PROMPTS:
        vv = ", ".join(f"{k} {n}" for k, n in vocab[pid].most_common())
        cls = "lose" if "PERFECT" not in vocab[pid] else "win"
        t5 += f"<tr><td>{pid}</td><td class='{cls}'>{vv}</td></tr>"
    t5 += ("</table><p class='note'><code>garment</code> &mdash; the only prompt that "
           "works &mdash; collapsed to binary on its own: its <code>OK</code> already "
           "<i>is</i> the pass verdict.</p>"
           "<table><tr><th>rule</th><th>gen/req</th><th>perfect</th><th>ok</th>"
           "<th>fail</th><th>esc</th></tr>")
    for nm, g, p_, o_, f_, ec in perf_rows:
        t5 += (f"<tr class='{'hi' if 'or' in nm else ''}'><td>{nm}</td><td>{g:.3f}</td>"
               f"<td>{p_}</td><td>{o_}</td>"
               f"<td class='{'win' if f_==0 else ''}'>{f_}</td><td>{ec}</td></tr>")
    t5 += ("</table><p class='note'>Escalating on <code>tryon</code>-not-perfect "
           "<b>or</b> <code>garment</code>-fail gets failures down to <b>1</b>, "
           "for +0.37 generations and one lost perfect.</p>")

    t6 = ("<p class='note'>Score each candidate <b>independently</b> &mdash; count "
          "the prompts that did not say FAIL &mdash; then take the higher. Because "
          "neither image is shown beside the other, there is no position for the "
          "model to be biased by, which is what sank the pairwise call.</p>"
          "<table><tr><th>set</th><th>first arm</th><th></th><th>QX</th><th></th>"
          "<th>picks</th></tr>")
    for k, a, ta, sa, tq, sb, pick, good in tb:
        t6 += (f"<tr><td><code>{e(k[:28])}</code></td><td>{ta}</td><td>{sa}</td>"
               f"<td>{tq}</td><td>{sb}</td>"
               f"<td class='{'win' if good else 'lose'}'>{pick}</td></tr>")
    nb = sum(1 for x in tb if x[7])
    t6 += (f"</table><p class='note'>Avoids the already-failed arm on "
           f"<b>{nb}/{len(tb)}</b>, against <b>3/5</b> for the pairwise call. "
           "But <b>always taking QX scores 5/5</b> here, so on this evidence the "
           "trivial rule still wins &mdash; n = 5.</p>")

    t4 += ("</table><p class='note'><b>The vote loses to <code>garment</code> alone</b> "
           "&mdash; same 31/5/2, but more escalations, because three of the five "
           "prompts contribute noise rather than signal.</p>")

    t2 += ("</table><p class='note'>The 38 first-arm outputs only &mdash; what VLM-A "
           "actually screens in production. Escalation always goes to QX.</p>")

    doc = NL.join([
        "<title>VLM gate evaluation</title>", "<style>" + CSS + "</style>",
        f"<header><h1>VLM gate evaluation &mdash; {e(model)}</h1>"
        "<div class='q'>Can an open-weights VLM do the job the deterministic gate "
        "could not?</div>"
        "<div class='sub'>Five prompts &times; 114 human-tiered outputs, 4-bit on a "
        "free T4. The gate's job: fire when a frame is <b>not perfect</b>, so the "
        "harness escalates to QX. The bar is the <b>accept-everything baseline</b> "
        f"({base:.1%}) &mdash; the deterministic gate never beat it "
        "(AUC 0.506).</div></header>",
        "<div class='panels'>"
        "<div class='panel'><h2>Per-prompt, all 114 cells</h2><div class='in'>"
        + t1 + "</div></div>"
        "<div class='panel'><h2>Production simulation, 38 first-arm outputs</h2>"
        "<div class='in'>" + t2 + "</div></div>"
        "<div class='panel'><h2>Did the hair router pick the right arm?</h2>"
        "<div class='in'>" + t3 + "</div></div>"
        "<div class='panel'><h2>Voting across the five prompts</h2>"
        "<div class='in'>" + t4 + "</div></div>"
        "<div class='panel'><h2>Only PERFECT ships &mdash; can the rule be applied?</h2>"
        "<div class='in'>" + t5 + "</div></div>"
        "<div class='panel'><h2>Tie-break by independent score, not pairwise</h2>"
        "<div class='in'>" + t6 + "</div></div></div>",
        "<div class='key'><b>The artefact prompt never fired once</b> &mdash; it "
        "answered CLEAN on all 114 outputs, including every frame you marked "
        "<i>fail</i>. Asking a VLM to spot AI artefacts does not work here, because "
        "these failures are not artefacts: the images are competent photographs of "
        "the wrong thing. <b><code>usable</code> and <code>tryon</code> are barely "
        "better</b>, firing 2&ndash;4 times in 114 and changing the production "
        "outcome not at all.</div>",
        "<div class='key'><b>Only <code>garment</code> works, and only because it "
        "sees the reference image.</b> 70.2% against a 62.3% baseline, catching 53% "
        "of failures. In production it takes 5 shipped failures down to 2, at 1.737 "
        "generations against the oracle's 1.526 &mdash; and it beats flat BC_klein "
        "(2.000 generations, 4 failures) on both axes. <b>The lesson is that VLM-A "
        "needs the garment reference as input, not just the output.</b></div>",
        f"<div class='key'><b>VLM-B is dropped.</b> Pairwise selection agreed with "
        f"itself on only <b>{cons}/{len(P)} ({cons/len(P):.0%})</b> of pairs when the "
        "two images were swapped &mdash; worse than chance, so it reads position "
        f"rather than content. On the {len(esc)} pairs that actually escalate it "
        f"picked <b>the arm that had already failed {harm} times</b>. Always taking "
        "QX scores perfectly on the same set.</div>",
        "<div class='key'><b>Caveat before this is treated as settled:</b> the model "
        "hedges heavily &mdash; 331 of 570 verdicts are <code>OK</code>, only 49 are "
        "<code>FAIL</code>. A binary forced choice with no middle option, and fp16 "
        "instead of 4-bit, are both untried and both plausibly worth several points. "
        "This measures <i>Qwen3-VL-8B at 4-bit with these five prompts</i>, not "
        "\"open VLMs\".</div>",
        "<div id='bar'>"
        "<button data-f='all' class='on'>all cells</button>"
        "<button data-f='dis'>disagreements</button>"
        "<button data-f='fail'>human said fail</button>"
        "<button data-f='esc'>the 5 that escalate</button>"
        "<span id='count'></span></div>"] + body + [
        "<div id='lb'><img id='lbi' alt=''><div id='lbc'></div></div>",
        "<script>" + JS + "</script>"])
    o = os.path.join(ART, "v223_vlm_eval.html")
    open(o, "w", encoding="utf-8").write(doc)
    return o, len(cells)


if __name__ == "__main__":
    print(build())
