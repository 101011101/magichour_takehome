# PCROP review — one arm, three verdicts.
#
# perfect = as good as the best arm on that row (a tie for first, not a rank)
# ok      = usable, would sit in the ranked middle
# fail    = unusable
#
# Standalone. Each row shows both raw inputs, the reference PCROP produced, and the
# klein output, so a bad result can be attributed to the crop or to the model without
# leaving the row.
import csv, html, json, os

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
ART = os.path.join(REPO, "v2", "artifacts")
NL = chr(10)

CSS = """
:root{--bg:#0d0d10;--fg:#e8e8ea;--dim:#8a8a94;--line:#26262c;--acc:#7c5cff;
 --good:#3fb950;--mid:#d29922;--bad:#f85149}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
 font:14px/1.55 ui-sans-serif,-apple-system,"Segoe UI",Roboto,sans-serif}
header{padding:26px 30px 16px;border-bottom:1px solid var(--line)}
h1{margin:0 0 6px;font-size:20px}
.q{color:var(--acc);font-weight:600;margin:6px 0}
.sub{color:var(--dim);max-width:82ch}
.legend{padding:16px 30px 6px;color:var(--dim);font-size:12.5px}
.legend b{color:var(--fg)} .legend li{margin:3px 0}
.ref{margin:0 30px 22px;border:1px solid var(--line);border-radius:10px;overflow:hidden}
.ref.v-perfect{border-color:var(--good)} .ref.v-ok{border-color:var(--mid)}
.ref.v-fail{border-color:var(--bad)}
.rh{padding:10px 14px;background:#141419;border-bottom:1px solid var(--line);
 display:flex;gap:12px;align-items:center;flex-wrap:wrap}
.rh .m{color:var(--dim);font-size:12px}
.pill{font-size:11px;padding:2px 8px;border-radius:20px;border:1px solid var(--line)}
.pill.hd{border-color:var(--mid);color:var(--mid)}
.btns{margin-left:auto;display:flex;gap:6px}
.btns button{background:#1b1b22;border:1px solid var(--line);color:var(--dim);
 border-radius:7px;padding:6px 13px;font-size:12px;font-weight:600;cursor:pointer;
 font-family:inherit}
.btns button:hover{color:var(--fg)}
.btns button.on[data-v=perfect]{background:var(--good);border-color:var(--good);color:#06210d}
.btns button.on[data-v=ok]{background:var(--mid);border-color:var(--mid);color:#241a00}
.btns button.on[data-v=fail]{background:var(--bad);border-color:var(--bad);color:#2a0505}
.strip{display:flex;overflow-x:auto;padding:4px}
.cell{flex:0 0 236px;padding:10px}
.cell img{width:100%;background:#fff;border-radius:5px;display:block;cursor:zoom-in}
.cell.in img{opacity:.9}
.cell.out{flex:0 0 280px}
.tag{font-weight:600;margin:7px 0 3px;font-size:12.5px}
.tag.o{color:var(--acc)} .tag.r{color:var(--good)}
.note{color:var(--dim);font-size:11.5px}
#save{position:fixed;right:20px;bottom:20px;z-index:40;background:var(--acc);color:#fff;
 border:0;border-radius:9px;padding:11px 17px;font-size:13px;font-weight:600;cursor:pointer;
 box-shadow:0 4px 18px #0008;font-family:inherit}
#save small{display:block;font-weight:400;opacity:.85;font-size:11px}
#prog{position:fixed;left:20px;bottom:20px;z-index:40;color:var(--dim);font-size:12.5px;
 background:#141419cc;border:1px solid var(--line);border-radius:8px;padding:8px 13px}
#lb{position:fixed;inset:0;background:#000000f2;display:none;z-index:50;
 align-items:center;justify-content:center;flex-direction:column;gap:12px}
#lb img{max-width:94vw;max-height:84vh;background:#fff;border-radius:6px}
#lbc{color:var(--fg);font-size:13px}
"""

JS = r"""
var KEY = 'phead_v1';
var store = {};
try { store = JSON.parse(localStorage.getItem(KEY) || '{}'); } catch (e) { store = {}; }

function progress(){
  var rows = document.querySelectorAll('.ref').length;
  var done = Object.keys(store).length;
  var c = {perfect: 0, ok: 0, fail: 0};
  Object.keys(store).forEach(function(k){ c[store[k]]++; });
  document.getElementById('prog').textContent =
    done + ' / ' + rows + ' judged  ·  perfect ' + c.perfect +
    '  ok ' + c.ok + '  fail ' + c.fail;
}
function mark(row, v){
  store[row.dataset.sid] = v;
  try { localStorage.setItem(KEY, JSON.stringify(store)); } catch (e) { /* full */ }
  row.className = 'ref v-' + v;
  Array.prototype.slice.call(row.querySelectorAll('.btns button')).forEach(function(b){
    b.classList.toggle('on', b.dataset.v === v);
  });
  progress();
}
Array.prototype.slice.call(document.querySelectorAll('.ref')).forEach(function(row){
  var v = store[row.dataset.sid];
  if (v) mark(row, v);
});
progress();
document.body.addEventListener('click', function(e){
  var b = e.target.closest('.btns button');
  if (b){ mark(b.closest('.ref'), b.dataset.v); return; }
  var im = e.target.closest('.cell img');
  if (im){
    var lb = document.getElementById('lb');
    document.getElementById('lbi').src = im.getAttribute('src');
    document.getElementById('lbc').textContent = im.getAttribute('alt');
    lb.style.display = 'flex';
  }
});
document.getElementById('lb').addEventListener('click', function(){
  this.style.display = 'none';
});
document.addEventListener('keydown', function(e){
  if (e.key === 'Escape') document.getElementById('lb').style.display = 'none';
});
document.getElementById('save').addEventListener('click', function(){
  var q = String.fromCharCode(34), nl = String.fromCharCode(10);
  var out = ['set_id,person,garment_source,condition,arm,verdict'];
  Array.prototype.slice.call(document.querySelectorAll('.ref')).forEach(function(r){
    out.push([r.dataset.sid, r.dataset.person, r.dataset.garment, r.dataset.cond,
              'PHEAD', store[r.dataset.sid] || 'unjudged']
      .map(function(v){ return q + String(v).replace(/"/g, '""') + q; }).join(','));
  });
  var b = new Blob([out.join(nl) + nl], {type: 'text/csv'});
  var a = document.createElement('a');
  a.href = URL.createObjectURL(b);
  a.download = 'v221_phead_verdicts.csv';
  document.body.appendChild(a); a.click();
  setTimeout(function(){ URL.revokeObjectURL(a.href); a.remove(); }, 400);
  var s = document.getElementById('save');
  s.firstChild.nodeValue = 'Saved ✓  ';
  setTimeout(function(){ s.firstChild.nodeValue = 'Save verdicts CSV'; }, 1800);
});
"""


def build():
    run = json.load(open(os.path.join(REPO, "v2", "runs", "amt", "_run.json")))
    meta = {r["stem"]: r["src_path"] for r in csv.DictReader(
        open(os.path.join(REPO, "v2", "runs", "crop_screen", "crop_log.csv")))}

    def rel(p):
        return os.path.relpath(os.path.join(REPO, p), ART)

    b = ["<div class='legend'><ul>"
         "<li><b>PHEAD is fully deterministic &mdash; no generative call at all.</b> It removes "
         "<b>only the head</b>, using the human parser&rsquo;s head classes, and keeps everything "
         "else: arms, legs, torso. Subtractive like <code>control</code> (C3.1), but the head mask "
         "comes from the parser rather than from MediaPipe HAIR+FACE</li>"
         "<li><b>PCROP is shown faded, for contrast, and is not judged.</b> It took the garment "
         "classes directly and therefore dropped the body with them &mdash; the same over-crop C4 "
         "had. A garment with no body loses the drape and fit context that makes it legible</li>"
         "<li><b>Why this arm exists.</b> Every arm that survived high-damage references needs a "
         "generative preprocessing step, which doubles the klein calls. If PCROP holds up it "
         "gives that robustness at <b>zero marginal cost per request</b></li>"
         "<li><b>Measured first, so the cheaper idea was ruled out:</b> merely swapping the better "
         "head detector into C3.1 moves it by only <b>+0.5&ndash;1 point</b> on haired originals "
         "&mdash; MediaPipe&rsquo;s HAIR class already covers a haired head. That swap reproduces "
         "<code>control</code>. Taking the garment class directly is the change that is actually "
         "different</li>"
         "<li style='margin-top:8px'><b>Three verdicts.</b> "
         "<span style='color:#3fb950;font-weight:700'>perfect</span> = as good as the best arm on "
         "that row, i.e. it would have been <i>tied first</i> &mdash; not a rank &middot; "
         "<span style='color:#d29922;font-weight:700'>ok</span> = usable, would sit in the ranked "
         "middle &middot; <span style='color:#f85149;font-weight:700'>fail</span> = unusable</li>"
         "<li><b>Each row shows PHEAD next to the arms it has to beat</b> &mdash; "
         "<code>control</code> (the incumbent, cut 61% of the time on high-damage), "
         "<code>BC_klein</code> and <code>D3B</code> (the two best arms, each costing a "
         "generative call), and <code>PCROP</code> faded for contrast. Judge PHEAD, but judge it "
         "<i>against these</i>: the question is whether a free arm reaches what the paid ones "
         "reach</li>"
         "<li>The <b>PHEAD reference</b> is shown too, so a bad result can be blamed on the crop "
         "or on the model without leaving the row. Verdicts save to your browser; "
         "<b>Save verdicts CSV</b> writes the file to send back</li>"
         "</ul></div>"]

    n = 0
    for sid, per, src in run["pairs"]:
        if f"{sid}|PHEAD" not in run["gen"]:
            continue
        n += 1
        hd = sid.startswith("HD_")
        b.append(f"<div class='ref' data-sid='{html.escape(sid)}' "
                 f"data-person='{html.escape(per)}' data-garment='{html.escape(src)}' "
                 f"data-cond='{'high' if hd else 'low'}'>"
                 f"<div class='rh'><b>{html.escape(sid)}</b>"
                 f"<span class='m'>garment <b>{html.escape(src)}</b></span>"
                 + ("<span class='pill hd'>HIGH-DAMAGE</span>" if hd else
                    "<span class='pill'>low-damage</span>")
                 + "<span class='btns'>"
                   "<button data-v='perfect'>perfect</button>"
                   "<button data-v='ok'>ok</button>"
                   "<button data-v='fail'>fail</button></span>"
                 + "</div><div class='strip'>")
        for who, lab in ((per, "INPUT — person"), (src, "INPUT — garment")):
            p = rel(meta.get(who, ""))
            if p and os.path.exists(os.path.normpath(os.path.join(ART, p))):
                b.append(f"<div class='cell in'><img src='{p}' alt='{html.escape(sid)} {lab}' "
                         f"loading='lazy'><div class='tag'>{lab}</div>"
                         "<div class='note'>raw</div></div>")
        rh = run["refs"].get(f"{src}|PHEAD")
        if rh:
            b.append(f"<div class='cell'><img src='../runs/amt/{rh}' "
                     f"alt='{html.escape(sid)} — PHEAD reference' loading='lazy'>"
                     "<div class='tag r'>PHEAD reference</div>"
                     "<div class='note'>head removed, body kept</div></div>")
        if f"{sid}|PHEAD" in run["gen"]:
            b.append(f"<div class='cell out'><img "
                     f"src='../runs/amt/gen/{run['gen'][f'{sid}|PHEAD']}' "
                     f"alt='{html.escape(sid)} — PHEAD output' loading='lazy'>"
                     "<div class='tag o'>PHEAD output &mdash; JUDGE THIS</div>"
                     "<div class='note'>head-only removal</div></div>")
        # the arms to beat, so PHEAD is judged against something rather than alone
        for arm, lab, note in (
                ("control", "control &mdash; C3.1 today",
                 "the incumbent · 61% cut on high-damage"),
                ("BC_klein", "BC_klein &mdash; bald &rarr; crop",
                 "best overall · costs a generative call"),
                ("D3B", "D3B &mdash; pixelate on bald",
                 "ties BC_klein · costs a generative call"),
                ("PCROP", "PCROP &mdash; garment only",
                 "over-cropped, shown for contrast")):
            if f"{sid}|{arm}" not in run["gen"]:
                continue
            dim = " style='opacity:.62'" if arm == "PCROP" else ""
            b.append(f"<div class='cell'{dim}><img "
                     f"src='../runs/amt/gen/{run['gen'][f'{sid}|{arm}']}' "
                     f"alt='{html.escape(sid)} — {lab}' loading='lazy'>"
                     f"<div class='tag'>{lab}</div>"
                     f"<div class='note'>{note}</div></div>")
        b.append("</div></div>")

    doc = NL.join(
        ["<title>Crop Tuning — PCROP</title>", "<style>" + CSS + "</style>",
         "<header><h1>Crop Tuning &mdash; PHEAD</h1>"
         "<div class='q'>Can a fully deterministic crop match the arms that cost a "
         "generative call?</div>"
         f"<div class='sub'>{n} rows. PHEAD&rsquo;s reference costs <b>no generative call</b> "
         "&mdash; only the klein try-on itself, same as every other arm. Shown beside the arms "
         "it has to beat. Mark each row perfect / ok / fail.</div>"
         "</header>"]
        + b
        + ["<div id='prog'></div>",
           "<button id='save'>Save verdicts CSV<small>then send me the file</small></button>",
           "<div id='lb'><img id='lbi' alt=''><div id='lbc'></div></div>",
           "<script>" + JS + "</script>"])
    p = os.path.join(ART, "v221_crop_tuning_phead.html")
    open(p, "w", encoding="utf-8").write(doc)
    return p, n


if __name__ == "__main__":
    print(build())
