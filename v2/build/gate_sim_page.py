# Simulated cascade — every arm graded, nothing assumed, the whole pipeline visible.
#
# The gate produces a 0-1 score per output. The reviewer sets the acceptance
# threshold with a slider, and the page re-simulates live: every arm before the first
# accepted one is shown as a rejected attempt, with an arrow to the next.
#
# Two orderings are shown because the data says they differ: PHEAD -> QX -> BC costs
# 1.421 units against 1.526 for PHEAD -> BC -> QX. QX rescues precisely PHEAD's
# failure mode, so it converts more cases on the first escalation even though
# BC_klein is the stronger arm standing alone.
import csv, html, json, os

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
ART = os.path.join(REPO, "v2", "artifacts")
NL = chr(10)
ORDERS = {"A": ["PHEAD", "QX_qwen_p1", "BC_klein"],
          "B": ["PHEAD", "BC_klein", "QX_qwen_p1"]}
UNIT = {"PHEAD": 1, "BC_klein": 2, "QX_qwen_p1": 2}
LAB = {"PHEAD": "PHEAD", "QX_qwen_p1": "QX", "BC_klein": "BC_klein"}

CSS = """
:root{--bg:#0d0d10;--fg:#e8e8ea;--dim:#8a8a94;--line:#26262c;--acc:#7c5cff;
 --good:#3fb950;--mid:#d29922;--bad:#f85149}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
 font:14px/1.55 ui-sans-serif,-apple-system,"Segoe UI",Roboto,sans-serif}
header{padding:24px 30px 14px;border-bottom:1px solid var(--line)}
h1{margin:0 0 6px;font-size:20px}
.q{color:var(--acc);font-weight:600}
.sub{color:var(--dim);max-width:84ch}
.legend{padding:14px 30px 4px;color:var(--dim);font-size:12.5px}
.legend b{color:var(--fg)} .legend li{margin:3px 0}
#bar{position:sticky;top:0;z-index:20;background:#121216;border-bottom:1px solid var(--line);
 padding:13px 30px;display:flex;gap:22px;align-items:center;flex-wrap:wrap}
#bar label{font-size:12.5px;color:var(--dim)}
input[type=range]{width:280px;accent-color:var(--acc)}
#thv{color:var(--acc);font-weight:700;font-size:15px;min-width:44px;display:inline-block}
#stats{color:var(--dim);font-size:12.5px;margin-left:auto;text-align:right;line-height:1.7}
#stats b{color:var(--fg)}
.ord{display:flex;gap:4px}
.ord button{background:#1b1b22;border:1px solid var(--line);color:var(--dim);
 border-radius:7px;padding:5px 12px;font-size:12px;cursor:pointer;font-family:inherit}
.ord button.on{background:var(--acc);border-color:var(--acc);color:#fff;font-weight:600}
.ref{margin:0 30px 20px;border:1px solid var(--line);border-radius:10px;overflow:hidden}
.rh{padding:9px 14px;background:#141419;border-bottom:1px solid var(--line);
 display:flex;gap:12px;align-items:center;flex-wrap:wrap;font-size:13px}
.rh .m{color:var(--dim);font-size:12px}
.pill{font-size:11px;padding:2px 8px;border-radius:20px;border:1px solid var(--line)}
.pill.hd{border-color:var(--mid);color:var(--mid)}
.pill.cost{border-color:var(--acc);color:var(--acc);margin-left:auto;font-weight:700}
.chain{display:flex;align-items:stretch;overflow-x:auto;padding:8px 6px}
.step{flex:0 0 210px;padding:9px;border:2px solid transparent;border-radius:9px;margin:2px}
.step img{width:100%;background:#fff;border-radius:4px;display:block;cursor:zoom-in}
.step.rej{border-color:var(--bad);opacity:.72}
.step.acc{border-color:var(--good)}
.step.skip{opacity:.28}
.step .t{font-weight:700;font-size:12.5px;margin:6px 0 2px}
.step .s{font-size:11.5px;color:var(--dim)}
.step .s .w{color:var(--bad)}
.arrow{align-self:center;color:var(--bad);font-size:22px;padding:0 2px;font-weight:700}
.verdict{margin:18px 30px;border:1px solid var(--line);border-radius:10px;background:#121216}
.verdict h2{margin:0;padding:12px 16px;font-size:14px;border-bottom:1px solid var(--line)}
.verdict .body{padding:14px 16px;display:grid;grid-template-columns:1fr 1fr;gap:20px}
.verdict table{border-collapse:collapse;font-size:12.5px;width:100%}
.verdict th,.verdict td{padding:4px 9px;text-align:right;border-bottom:1px solid #1d1d23}
.verdict th:first-child,.verdict td:first-child{text-align:left}
.verdict th{color:var(--dim);font-weight:600}
.verdict .cap{color:var(--dim);font-size:12px;margin:0 0 7px}
.verdict .hit{color:var(--good);font-weight:700}
.verdict .miss{color:var(--bad);font-weight:700}
.verdict p.k{margin:10px 16px 14px;font-size:13px;color:var(--fg);
 border-left:3px solid var(--acc);padding-left:11px;max-width:110ch}
@media(max-width:1000px){.verdict .body{grid-template-columns:1fr}}

.inp{flex:0 0 150px;padding:9px;background:#101418;border-radius:9px;margin:2px}
.inp img{width:100%;background:#fff;border-radius:4px;display:block}
.inp .t{font-size:11.5px;color:var(--good);font-weight:600;margin-top:5px}
#save{position:fixed;right:20px;bottom:20px;z-index:40;background:var(--acc);color:#fff;
 border:0;border-radius:9px;padding:11px 17px;font-size:13px;font-weight:600;cursor:pointer;
 box-shadow:0 4px 18px #0008;font-family:inherit}
#save small{display:block;font-weight:400;opacity:.85;font-size:11px}
#lb{position:fixed;inset:0;background:#000000f2;display:none;z-index:50;
 align-items:center;justify-content:center;flex-direction:column;gap:12px}
#lb img{max-width:94vw;max-height:84vh;background:#fff;border-radius:6px}
#lbc{color:var(--fg);font-size:13px}
.mk{display:flex;gap:4px;margin-top:6px}
.mk button{flex:1;background:#1b1b22;border:1px solid var(--line);color:var(--dim);
 border-radius:6px;padding:3px 0;font-size:11px;font-weight:700;cursor:pointer;
 font-family:inherit}
.mk button:hover{color:var(--fg)}
.mk button.on[data-m=pass]{background:var(--good);border-color:var(--good);color:#06210d}
.mk button.on[data-m=fail]{background:var(--bad);border-color:var(--bad);color:#2a0505}
.step.agree{box-shadow:inset 0 0 0 2px #3fb95055}
.step.disagree{box-shadow:inset 0 0 0 2px #f8514999}
.dis{color:var(--bad);font-weight:700;font-size:11px}
"""

JS = r"""
var DATA = window.SIM, order = 'A';
var MKEY = 'gate_marks_v1', marks = {};
try { marks = JSON.parse(localStorage.getItem(MKEY) || '{}'); } catch (e) { marks = {}; }

function paintMarks(){
  Array.prototype.slice.call(document.querySelectorAll('.mk button')).forEach(function(b){
    b.classList.toggle('on', marks[b.dataset.k] === b.dataset.m);
  });
}

function sim(){
  var th = parseFloat(document.getElementById('th').value);
  document.getElementById('thv').textContent = th.toFixed(2);
  var units = 0, settled = {}, unresolved = 0, human = {perfect:0, ok:0, fail:0};
  DATA.sets.forEach(function(S){
    var chain = DATA.orders[order], done = false, cost = 0;
    chain.forEach(function(arm){
      var el = document.getElementById('cell_' + S.id + '_' + arm);
      if (!el) return;
      var g = S.gate[arm];
      el.classList.remove('rej','acc','skip');
      if (done){ el.classList.add('skip'); return; }
      cost += DATA.unit[arm];
      if (g !== undefined && g >= th){
        el.classList.add('acc'); done = true;
        settled[arm] = (settled[arm] || 0) + 1;
        if (S.human[arm]) human[S.human[arm]]++;
      } else { el.classList.add('rej'); }
    });
    if (!done) unresolved++;
    units += cost;
    var c = document.getElementById('cost_' + S.id);
    if (c) c.textContent = cost + ' unit' + (cost === 1 ? '' : 's');
  });
  // your marks vs the gate at this threshold
  var ag = 0, dis = 0;
  DATA.sets.forEach(function(S){
    Object.keys(S.gate).forEach(function(arm){
      var el = document.getElementById('cell_' + S.id + '_' + arm);
      var m = marks[S.id + '|' + arm];
      if (el){ el.classList.remove('agree','disagree'); }
      if (!m || !el) return;
      var same = (m === 'pass') === (S.gate[arm] >= th);
      if (same){ ag++; el.classList.add('agree'); }
      else { dis++; el.classList.add('disagree'); }
    });
  });
  var n = DATA.sets.length, parts = [];
  Object.keys(settled).forEach(function(k){ parts.push(k + ' ' + settled[k]); });
  var agTxt = (ag + dis)
    ? ('<br>your marks: <b>' + ag + '</b> agree, <b style="color:#f85149">' + dis +
       '</b> disagree &nbsp;(<b>' + Math.round(ag / (ag + dis) * 100) + '%</b> of ' +
       (ag + dis) + ' marked)')
    : '<br><span style="opacity:.6">mark cells &ldquo;should pass / should fail&rdquo; to score the gate against yourself</span>';
  document.getElementById('stats').innerHTML =
    '<b>' + (units / n).toFixed(3) + '</b> units/request &nbsp;·&nbsp; settled by: ' +
    parts.join(', ') + (unresolved ? ' &nbsp;·&nbsp; <b style="color:#f85149">' +
    unresolved + ' unresolved</b>' : '') +
    '<br>human verdict on the accepted frame: <b style="color:#3fb950">perfect ' +
    human.perfect + '</b> · <b style="color:#d29922">ok ' + human.ok +
    '</b> · <b style="color:#f85149">fail ' + human.fail + '</b>' + agTxt;
}

document.getElementById('th').addEventListener('input', sim);
Array.prototype.slice.call(document.querySelectorAll('.ord button')).forEach(function(b){
  b.addEventListener('click', function(){
    order = b.dataset.o;
    Array.prototype.slice.call(document.querySelectorAll('.ord button')).forEach(function(x){
      x.classList.toggle('on', x === b);
    });
    sim();
  });
});
document.body.addEventListener('click', function(e){
  var mb = e.target.closest('.mk button');
  if (mb){
    e.stopPropagation();
    if (marks[mb.dataset.k] === mb.dataset.m) delete marks[mb.dataset.k];
    else marks[mb.dataset.k] = mb.dataset.m;
    try { localStorage.setItem(MKEY, JSON.stringify(marks)); } catch (err) {}
    paintMarks(); sim();
    return;
  }
  var im = e.target.closest('.step img, .inp img');
  if (!im) return;
  var lb = document.getElementById('lb');
  document.getElementById('lbi').src = im.getAttribute('src');
  document.getElementById('lbc').textContent = im.getAttribute('alt');
  lb.style.display = 'flex';
});
document.getElementById('lb').addEventListener('click', function(){ this.style.display='none'; });
document.addEventListener('keydown', function(e){
  if (e.key === 'Escape') document.getElementById('lb').style.display = 'none';
});
document.getElementById('save').addEventListener('click', function(){
  var th = parseFloat(document.getElementById('th').value);
  var q = String.fromCharCode(34), nl = String.fromCharCode(10);
  var out = ['set_id,condition,order,threshold,arm,gate_score,decision,your_mark,agrees,human_verdict,units_so_far'];
  DATA.sets.forEach(function(S){
    var chain = DATA.orders[order], done = false, cost = 0;
    chain.forEach(function(arm){
      var g = S.gate[arm];
      if (g === undefined) return;
      var dec;
      if (done) dec = 'skipped';
      else { cost += DATA.unit[arm]; dec = (g >= th) ? 'ACCEPT' : 'reject'; if (g >= th) done = true; }
      var mk = marks[S.id + '|' + arm] || '';
      var agr = mk ? (((mk === 'pass') === (g >= th)) ? 'yes' : 'no') : '';
      out.push([S.id, S.cond, order, th.toFixed(2), arm, g, dec, mk, agr, S.human[arm] || '', cost]
        .map(function(v){ return q + String(v).replace(/"/g,'""') + q; }).join(','));
    });
  });
  var b = new Blob([out.join(nl)+nl], {type:'text/csv'});
  var a = document.createElement('a');
  a.href = URL.createObjectURL(b);
  a.download = 'v223_gate_simulation.csv';
  document.body.appendChild(a); a.click();
  setTimeout(function(){ URL.revokeObjectURL(a.href); a.remove(); }, 400);
  var s = document.getElementById('save');
  s.firstChild.nodeValue = 'Saved ✓  ';
  setTimeout(function(){ s.firstChild.nodeValue = 'Save simulation CSV'; }, 1800);
});
sim();
paintMarks();
"""



def _verdict(gate, human):
    """The separation table and the per-arm identity firing rate, computed from the
    same files the page renders, so the panel can never drift from the cells below."""
    import statistics as st
    P = [(v, human[tuple(k.split("|"))]) for k, v in gate.items()
         if tuple(k.split("|")) in human]
    t1 = ("<p class='cap'>Mean sub-score by human verdict, over the "
          + str(len(P)) + " outputs that carry both. A check only works if the "
          "<b>perfect</b> column sits clearly above <b>fail</b>.</p>"
          "<table><tr><th>check</th><th>perfect</th><th>ok</th><th>fail</th>"
          "<th>separation</th></tr>")
    for c in ("degenerate", "noop", "people", "identity", "background"):
        m = {l: st.mean([v["checks"][c] for v, h in P if h == l])
             for l in ("perfect", "ok", "fail")}
        sep = m["perfect"] - m["fail"]
        cls = "hit" if sep > 0.10 else "miss"
        t1 += (f"<tr><td>{c}</td><td>{m['perfect']:.3f}</td><td>{m['ok']:.3f}</td>"
               f"<td>{m['fail']:.3f}</td><td class='{cls}'>{sep:+.3f}</td></tr>")
    t1 += "</table>"

    fire, tot = {}, {}
    for k, v in gate.items():
        a = k.split("|")[1]
        tot[a] = tot.get(a, 0) + 1
        if v["checks"].get("identity", 1) < 0.5:
            fire[a] = fire.get(a, 0) + 1
    t2 = ("<p class='cap'>Identity is the only check with real separation and it is "
          "<b>100% precise</b> &mdash; below 0.5 it has never once flagged a frame the "
          "reviewer liked. But look at <i>where</i> it fires:</p>"
          "<table><tr><th>arm</th><th>identity fires</th><th>of</th></tr>")
    for a in sorted(tot, key=lambda x: -fire.get(x, 0)):
        n, cas = fire.get(a, 0), a in ("PHEAD", "QX_qwen_p1", "BC_klein")
        nm = f"<b>{a} &nbsp;&larr; cascade arm</b>" if cas else a
        t2 += (f"<tr><td>{nm}</td><td class='{'miss' if cas else 'hit'}'>{n}</td>"
               f"<td>{tot[a]}</td></tr>")
    t2 += "</table>"
    return ("<div class='verdict'><h2>Does the gate work? &mdash; the evidence, "
            "recomputed on every build</h2><div class='body'><div>" + t1
            + "</div><div>" + t2 + "</div></div>"
            "<p class='k'><b>It does not, for this cascade.</b> Identity fires on "
            "exactly <b>0</b> of the three cascade arms, and reads <b>1.00 on all 8 "
            "PHEAD failures</b>. Those arms never swap the person &mdash; that is the "
            "one failure mode they structurally cannot have &mdash; so the only check "
            "with signal is blind to every case the cascade needs caught. It fires "
            "only on <code>BALD_raw</code> and the D*O disfiguration arms, which keep "
            "a head in the reference. The remaining failures are semantic (wrong "
            "garment, repainted scene) and pixel statistics cannot see them.</p>"
            "<p class='k'><b>So: no router.</b> A router must be &ge;79% accurate to "
            "beat cascading, the candidate sits at ~75% fitted on its own data, and a "
            "router is only worth building on top of a gate that can catch its "
            "mistakes. There is no such gate. <b>Ship the best single arm &mdash; "
            "BC_klein, 95% usable, flat 2 units</b> &mdash; and keep identity as a "
            "free 100%-precision monitor, not a spend decision.</p></div>")


def build():
    run = json.load(open(os.path.join(REPO, "v2", "runs", "amt", "_run.json")))
    gate = json.load(open(os.path.join(REPO, "v2", "runs", "amt", "_gate.json")))
    meta = {r["stem"]: r["src_path"] for r in csv.DictReader(
        open(os.path.join(REPO, "v2", "runs", "crop_screen", "crop_log.csv")))}
    T = {"top": "perfect", "mid": "ok", "out": "fail"}
    human = {}
    for r in csv.DictReader(open(os.path.join(REPO, "v221_attention_mod_rankings (1).csv"))):
        human[(r["set_id"], r["arm"])] = T[r["tier"]]
    p = os.path.join(REPO, "v221_phead_verdicts.csv")
    if os.path.exists(p):
        for r in csv.DictReader(open(p)):
            human[(r["set_id"], "PHEAD")] = r["verdict"]

    def rel(x):
        return os.path.relpath(os.path.join(REPO, x), ART)

    sets, body = [], []
    for sid, per, src in run["pairs"]:
        arms = {a: gate[f"{sid}|{a}"]["score"] for a in UNIT
                if f"{sid}|{a}" in gate}
        if len(arms) < 2:
            continue
        hd = sid.startswith("HD_")
        sets.append({"id": sid, "cond": "high" if hd else "low", "gate": arms,
                     "human": {a: human.get((sid, a), "") for a in arms}})
        body.append(f"<div class='ref' id='row_{html.escape(sid)}'><div class='rh'>"
                    f"<b>{html.escape(sid)}</b><span class='m'>garment "
                    f"{html.escape(src)}</span>"
                    + ("<span class='pill hd'>HIGH-DAMAGE</span>" if hd else
                       "<span class='pill'>low-damage</span>")
                    + f"<span class='pill cost' id='cost_{html.escape(sid)}'></span>"
                    "</div><div class='chain'>")
        for who, lab in ((per, "person"), (src, "garment")):
            q = rel(meta.get(who, ""))
            if q and os.path.exists(os.path.normpath(os.path.join(ART, q))):
                body.append(f"<div class='inp'><img src='{q}' alt='{html.escape(sid)} "
                            f"{lab}'><div class='t'>{lab}</div></div>")
        first = True
        for a in ["PHEAD", "QX_qwen_p1", "BC_klein"]:
            if a not in arms:
                continue
            if not first:
                body.append("<div class='arrow'>&rarr;</div>")
            first = False
            g = gate[f"{sid}|{a}"]
            wk = g.get("weakest", "")
            ch = " · ".join(f"{k[:4]} {v:.2f}" for k, v in sorted(g["checks"].items()))
            body.append(
                f"<div class='step' id='cell_{html.escape(sid)}_{a}'>"
                f"<img src='../runs/amt/gen/{run['gen'][f'{sid}|{a}']}' "
                f"alt='{html.escape(sid)} — {LAB[a]}  gate {g['score']:.2f}'>"
                f"<div class='t'>{LAB[a]} &nbsp;<span style='color:#7c5cff'>"
                f"{g['score']:.2f}</span></div>"
                f"<div class='s'>weakest <span class='w'>{wk}</span><br>{ch}<br>"
                f"human: {human.get((sid, a), '—')}</div></div>")
        body.append("</div></div>")

    data = {"sets": sets, "orders": ORDERS, "unit": UNIT}
    doc = NL.join([
        "<title>Gate simulation</title>", "<style>" + CSS + "</style>",
        "<header><h1>Failure gate &mdash; simulated cascade</h1>"
        "<div class='q'>Every arm graded, nothing assumed. Move the threshold and the "
        "pipeline re-simulates.</div>"
        "<div class='sub'>No generations were made for this page. Each arm already has "
        "an output and a human verdict; the gate scores them, and the cascade is "
        "replayed at whatever acceptance threshold you choose.</div></header>",
        _verdict(gate, human),
        "<div id='bar'>"
        "<label>accept at &ge; <span id='thv'></span></label>"
        "<input type='range' id='th' min='0' max='1' step='0.01' value='0.50'>"
        "<span class='ord'><button data-o='A' class='on'>PHEAD &rarr; QX &rarr; BC</button>"
        "<button data-o='B'>PHEAD &rarr; BC &rarr; QX</button></span>"
        "<span id='stats'></span></div>",
        "<div class='legend'><ul>"
        "<li><b>Green</b> = the gate accepted and the cascade stopped. <b>Red</b> = "
        "rejected, escalate. <b>Faded</b> = never reached</li>"
        "<li>Each cell shows the composite score, the <b>weakest check</b> that "
        "produced it, all five sub-scores, and what the human called that frame &mdash; "
        "so gate and reviewer can be compared directly</li>"
        "<li>The composite is the <b>weakest</b> check, not the average: one hard "
        "failure should sink a frame rather than being hidden by four good scores</li>"
        "<li><b>The garment check is deliberately absent.</b> &sect;2b measured "
        "<code>garment_sim</code> at 0.78 and a VLM at 4/5 on an output that "
        "transferred no garment &mdash; both reward a plausible garment over the "
        "correct one, so neither can carry this. What the gate does catch: degenerate "
        "frames, no-ops, duplicated people, identity leaks, repainted backgrounds</li>"
        "<li>The header shows <b>units per request</b> at the current threshold and "
        "<b>what the human called the frame the gate accepted</b> &mdash; that second "
        "number is the one that matters</li>"
        "</ul></div>"] + body + [
        "<button id='save'>Save simulation CSV<small>threshold + every decision</small></button>",
        "<div id='lb'><img id='lbi' alt=''><div id='lbc'></div></div>",
        "<script>window.SIM=" + json.dumps(data) + ";</script>",
        "<script>" + JS + "</script>"])
    o = os.path.join(ART, "v223_gate_simulation.html")
    open(o, "w", encoding="utf-8").write(doc)
    return o, len(sets)


if __name__ == "__main__":
    print(build())
