# Crop Tuning — arms ordered by the corrected AMT finding, failures flagged, and one
# draggable frame per row to pick the best replacement.
#
# Standalone: no nav, no cross-links. Arm order is fixed by result rather than by
# family, so the eye starts at the current best candidate and moves outward:
#   BC_klein (67/67% best, never catastrophic) -> D3B (matches it, free once balded)
#   -> QX_qwen_p1 (0% failure on hard references) -> the rest.
# A red border marks any arm the reviewer previously cut on that row, so the frame is
# never dragged onto something already judged a failure.
import csv
import html
import json
import os

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
ART = os.path.join(REPO, "v2", "artifacts")
NL = chr(10)

ORDER = ["BC_klein", "D3B", "QX_qwen_p1", "D1hB", "D2B",
         "control", "D1hO", "D3O", "D2O", "BALD_raw"]
LAB = {"BC_klein": "1 · BC_klein — bald → crop", "D3B": "2 · D3B — pixelate, bald",
       "QX_qwen_p1": "3 · QX — Qwen extraction", "D1hB": "4 · D1h/B — blur, bald",
       "D2B": "5 · D2/B — twirl, bald", "control": "6 · control — C3.1 today",
       "D1hO": "7 · D1h/O — blur, hair kept", "D3O": "8 · D3/O — pixelate, hair kept",
       "D2O": "9 · D2/O — twirl, hair kept", "BALD_raw": "10 · BALD — no crop"}

CSS = """
:root{--bg:#0d0d10;--fg:#e8e8ea;--dim:#8a8a94;--line:#26262c;--acc:#7c5cff;
 --bad:#f85149;--ok:#3fb950}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
 font:14px/1.55 ui-sans-serif,-apple-system,"Segoe UI",Roboto,sans-serif}
header{padding:26px 30px 16px;border-bottom:1px solid var(--line)}
h1{margin:0 0 6px;font-size:20px}
.q{color:var(--acc);font-weight:600;margin:6px 0}
.sub{color:var(--dim);max-width:82ch}
.legend{padding:16px 30px 6px;color:var(--dim);font-size:12.5px}
.legend b{color:var(--fg)} .legend li{margin:3px 0}
.ref{margin:0 30px 26px;border:1px solid var(--line);border-radius:10px;overflow:hidden}
.rh{padding:10px 14px;background:#141419;border-bottom:1px solid var(--line);
 display:flex;gap:13px;align-items:baseline;flex-wrap:wrap}
.rh .m{color:var(--dim);font-size:12px}
.pill{font-size:11px;padding:2px 8px;border-radius:20px;border:1px solid var(--line)}
.pill.hd{border-color:#d29922;color:#d29922}
.strip{display:flex;overflow-x:auto;padding:4px}
.cell{flex:0 0 226px;padding:10px;position:relative;border:2px solid transparent;
 border-radius:9px;margin:4px 2px}
.cell img{width:100%;background:#fff;border-radius:4px;display:block;cursor:zoom-in}
.cell.in{background:#101418}
.cell.failed{border-color:var(--bad)}
.cell.failed img{opacity:.62}
.cell.sel{border-color:var(--acc);box-shadow:0 0 0 3px #7c5cff33,0 0 22px #7c5cff44}
.tag{font-weight:600;margin:7px 0 3px;font-size:12.5px}
.note{color:var(--dim);font-size:11.5px}
.note.bad{color:var(--bad);font-weight:600}
.fr{position:absolute;top:8px;left:8px;background:var(--acc);color:#fff;font-size:11px;
 font-weight:700;padding:4px 9px;border-radius:7px;cursor:grab;user-select:none;z-index:4;
 letter-spacing:.05em}
.fr:active{cursor:grabbing}
#save{position:fixed;right:20px;bottom:20px;z-index:40;background:var(--acc);color:#fff;
 border:0;border-radius:9px;padding:11px 17px;font-size:13px;font-weight:600;cursor:pointer;
 box-shadow:0 4px 18px #0008;font-family:inherit}
#save small{display:block;font-weight:400;opacity:.85;font-size:11px}
#lb{position:fixed;inset:0;background:#000000f2;display:none;z-index:50;
 align-items:center;justify-content:center;flex-direction:column;gap:12px}
#lb img{max-width:94vw;max-height:84vh;background:#fff;border-radius:6px}
#lbc{color:var(--fg);font-size:13px}
"""

JS = r"""
// One frame per row marks the chosen replacement. It starts on the first cell --
// BC_klein, the current best candidate -- so the default is the recommendation and
// every move away from it is a deliberate override.
var KEY = 'crop_tuning_v1';
var store = {};
try { store = JSON.parse(localStorage.getItem(KEY) || '{}'); } catch (e) { store = {}; }

function place(row, cell){
  var strip = row.querySelector('.strip');
  Array.prototype.slice.call(strip.querySelectorAll('.cell')).forEach(function(c){
    c.classList.remove('sel');
    var f = c.querySelector('.fr');
    if (f) f.remove();
  });
  cell.classList.add('sel');
  var chip = document.createElement('div');
  chip.className = 'fr';
  chip.draggable = true;
  chip.textContent = 'BEST ▸ drag';
  cell.appendChild(chip);
  store[row.dataset.sid] = cell.dataset.arm;
  try { localStorage.setItem(KEY, JSON.stringify(store)); } catch (e) { /* full */ }
}
Array.prototype.slice.call(document.querySelectorAll('.ref')).forEach(function(row){
  var cells = row.querySelectorAll('.cell');
  if (!cells.length) return;
  var want = store[row.dataset.sid], target = cells[0];
  Array.prototype.slice.call(cells).forEach(function(c){
    if (want && c.dataset.arm === want) target = c;
  });
  place(row, target);
});
var dragging = null;
document.body.addEventListener('dragstart', function(e){
  var f = e.target.closest('.fr');
  if (!f) return;
  dragging = f.closest('.ref');
  e.dataTransfer.effectAllowed = 'move';
  try { e.dataTransfer.setData('text/plain', ''); } catch (err) { /* firefox */ }
});
document.body.addEventListener('dragover', function(e){
  if (!dragging) return;
  var c = e.target.closest('.cell');
  if (c && dragging.contains(c)) e.preventDefault();
});
document.body.addEventListener('drop', function(e){
  if (!dragging) return;
  var c = e.target.closest('.cell');
  if (c && dragging.contains(c)){ e.preventDefault(); place(dragging, c); }
  dragging = null;
});
document.body.addEventListener('dragend', function(){ dragging = null; });
// clicking a cell also selects it -- dragging is fiddly on a long row
document.body.addEventListener('click', function(e){
  var c = e.target.closest('.cell');
  if (!c) return;
  if (e.target.tagName === 'IMG' && !e.altKey){
    var lb = document.getElementById('lb');
    document.getElementById('lbi').src = e.target.getAttribute('src');
    document.getElementById('lbc').textContent = e.target.getAttribute('alt');
    lb.style.display = 'flex';
    return;
  }
  place(c.closest('.ref'), c);
});
document.getElementById('lb').addEventListener('click', function(){
  this.style.display = 'none';
});
document.addEventListener('keydown', function(e){
  if (e.key === 'Escape') document.getElementById('lb').style.display = 'none';
});
document.getElementById('save').addEventListener('click', function(){
  var q = String.fromCharCode(34), nl = String.fromCharCode(10);
  var out = ['set_id,person,garment_source,condition,best_replacement,was_failed'];
  Array.prototype.slice.call(document.querySelectorAll('.ref')).forEach(function(row){
    var sel = row.querySelector('.cell.sel');
    if (!sel) return;
    out.push([row.dataset.sid, row.dataset.person, row.dataset.garment,
              row.dataset.cond, sel.dataset.arm,
              sel.classList.contains('failed') ? 'yes' : 'no']
      .map(function(v){ return q + String(v).replace(/"/g, '""') + q; }).join(','));
  });
  var b = new Blob([out.join(nl) + nl], {type: 'text/csv'});
  var a = document.createElement('a');
  a.href = URL.createObjectURL(b);
  a.download = 'v221_crop_tuning_selections.csv';
  document.body.appendChild(a); a.click();
  setTimeout(function(){ URL.revokeObjectURL(a.href); a.remove(); }, 400);
  var btn = document.getElementById('save');
  btn.firstChild.nodeValue = 'Saved ✓  ';
  setTimeout(function(){ btn.firstChild.nodeValue = 'Save selections CSV'; }, 1800);
});
"""


def build():
    run = json.load(open(os.path.join(REPO, "v2", "runs", "amt", "_run.json")))
    meta = {r["stem"]: r["src_path"] for r in csv.DictReader(
        open(os.path.join(REPO, "v2", "runs", "crop_screen", "crop_log.csv")))}
    # which (set, arm) the reviewer already cut
    failed = set()
    rp = os.path.join(REPO, "v221_attention_mod_rankings (1).csv")
    if os.path.exists(rp):
        for r in csv.DictReader(open(rp)):
            if r["tier"] == "out":
                failed.add((r["set_id"], r["arm"]))

    def rel(p):
        return os.path.relpath(os.path.join(REPO, p), ART)

    b = ["<div class='legend'><ul>"
         "<li><b>Arms are ordered by the corrected result, not by family.</b> "
         "<b>BC_klein</b> first (best or tied-best in 80% of low-damage and 67% of "
         "high-damage sets, never catastrophic), then <b>D3B</b> (matches it, and free "
         "once the bald frame exists), then <b>QX</b> (the only arm that <i>improves</i> "
         "on hard references &mdash; 0% failure there). <code>control</code> sits sixth "
         "because it collapses on damaged references: 75% &rarr; 28% best, "
         "10% &rarr; 61% failed</li>"
         "<li><b>A red border</b> marks an arm you already cut on that row, so the frame "
         "is never dragged onto something already judged a failure</li>"
         "<li><b>The purple frame is your pick for best replacement.</b> It starts on "
         "<b>BC_klein</b> in every row &mdash; the default is the recommendation, so every "
         "move away from it is a deliberate override. Drag it, or just click a cell. "
         "Click an image to zoom</li>"
         "<li><b>Save selections CSV</b> (bottom right) writes "
         "<code>set_id, person, garment_source, condition, best_replacement, "
         "was_failed</code></li>"
         "</ul></div>"]

    for sid, per, src in run["pairs"]:
        have = [a for a in ORDER if f"{sid}|{a}" in run["gen"]]
        if not have:
            continue
        hd = sid.startswith("HD_")
        b.append(f"<div class='ref' data-sid='{html.escape(sid)}' "
                 f"data-person='{html.escape(per)}' data-garment='{html.escape(src)}' "
                 f"data-cond='{'high' if hd else 'low'}'>"
                 f"<div class='rh'><b>{html.escape(sid)}</b>"
                 f"<span class='m'>person <b>{html.escape(per)}</b> &middot; garment "
                 f"<b>{html.escape(src)}</b></span>"
                 + ("<span class='pill hd'>HIGH-DAMAGE</span>" if hd else
                    "<span class='pill'>low-damage</span>")
                 + "</div><div class='strip'>")
        for who, lab in ((per, "INPUT — person"), (src, "INPUT — garment")):
            p = rel(meta.get(who, ""))
            if p and os.path.exists(os.path.normpath(os.path.join(ART, p))):
                b.append(f"<div class='cell in'><img src='{p}' alt='{html.escape(sid)} "
                         f"{lab}' loading='lazy'><div class='tag'>{lab}</div>"
                         "<div class='note'>raw, untouched</div></div>")
        for a in have:
            bad = (sid, a) in failed
            b.append(f"<div class='cell{' failed' if bad else ''}' data-arm='{a}'>"
                     f"<img src='../runs/amt/gen/{run['gen'][f'{sid}|{a}']}' "
                     f"alt='{html.escape(sid)} — {LAB[a]}' loading='lazy'>"
                     f"<div class='tag'>{LAB[a]}</div>"
                     f"<div class='note{' bad' if bad else ''}'>"
                     f"{'you cut this' if bad else ''}</div></div>")
        b.append("</div></div>")

    doc = NL.join(
        ["<title>Crop Tuning</title>", "<style>" + CSS + "</style>",
         "<header><h1>Crop Tuning</h1>"
         "<div class='q'>For each row, which reference should replace the one we ship?</div>"
         "<div class='sub'>Arms ordered by the corrected attention-modulation result. "
         "The frame starts on the recommended arm; move it only where you disagree. "
         "Red border = an arm you already cut.</div></header>"]
        + b
        + ["<button id='save'>Save selections CSV<small>then send me the file</small></button>",
           "<div id='lb'><img id='lbi' alt=''><div id='lbc'></div></div>",
           "<script>" + JS + "</script>"])
    p = os.path.join(ART, "v221_crop_tuning.html")
    open(p, "w", encoding="utf-8").write(doc)
    return p


if __name__ == "__main__":
    print(build())
