# One review page per phase-3 component. Three pages rather than one, because the
# three ask different questions and mixing them makes the review harder:
#   M   does the mannequin read as a neutral form?
#   BG  did the DETECTOR decide correctly? (the call and its margin are printed)
#   AC  is the garment whole -- and on the synthetic bed, is it RIGHT as well as
#       plausible, since the truth panel is available there
#
# Everything in phase 3 is judged by eye (EXPERIMENT.md 2c), so these pages are the
# deliverable, not a summary of one.
#
# JS uses event delegation and carries no nested quotes in attributes; both of those
# broke an earlier review page. `node --check` is run on the emitted script.
import html
import os

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
ART = os.path.join(REPO, "v2", "artifacts")
NL = chr(10)

CSS = """
:root{--bg:#0d0d10;--fg:#e8e8ea;--dim:#8a8a94;--line:#26262c;--acc:#7c5cff;
 --ok:#3fb950;--warn:#d29922}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
 font:14px/1.55 ui-sans-serif,-apple-system,"Segoe UI",Roboto,sans-serif}
header{padding:26px 30px 16px;border-bottom:1px solid var(--line)}
nav{display:flex;gap:6px;padding:10px 30px;border-bottom:1px solid var(--line);
 background:#101014;position:sticky;top:0;z-index:6;flex-wrap:wrap;align-items:center}
nav a{color:var(--dim);text-decoration:none;padding:6px 13px;border-radius:7px;
 border:1px solid transparent;font-size:12.5px;white-space:nowrap}
nav a:hover{color:var(--fg);border-color:var(--line)}
nav a.here{color:var(--fg);border-color:var(--acc);background:#17141f;font-weight:600}
nav .sep{color:#3a3a44;padding:0 2px}
h1{margin:0 0 6px;font-size:20px;letter-spacing:-.01em}
.q{color:var(--acc);font-weight:600;margin:6px 0}
.sub{color:var(--dim);max-width:80ch}
.legend{padding:16px 30px 6px;color:var(--dim);font-size:12.5px}
.legend b{color:var(--fg)}
.legend li{margin:3px 0}
.ref{margin:0 30px 26px;border:1px solid var(--line);border-radius:10px;overflow:hidden}
.rh{padding:10px 14px;background:#141419;border-bottom:1px solid var(--line);
 display:flex;gap:13px;align-items:baseline;flex-wrap:wrap}
.rh b{font-size:13.5px}
.rh .m{color:var(--dim);font-size:12px}
.pill{font-size:11px;padding:2px 8px;border-radius:20px;border:1px solid var(--line)}
.pill.fire{border-color:var(--warn);color:var(--warn)}
.pill.keep{border-color:var(--ok);color:var(--ok)}
.strip{display:flex;overflow-x:auto}
.cell{flex:0 0 226px;border-right:1px solid var(--line);padding:10px}
.cell:last-child{border-right:0}
.cell.truth{background:#101418}
.cell img{width:100%;background:#fff;border-radius:4px;display:block;cursor:zoom-in}
.tag{font-weight:600;margin:7px 0 3px;font-size:12.5px}
.tag.t{color:var(--ok)}
.note{color:var(--dim);font-size:11.5px;line-height:1.45}
.sec{padding:8px 30px 4px;color:var(--fg);font-weight:600;font-size:14px}
table{border-collapse:collapse;margin:6px 30px 22px;font-size:12.5px}
td,th{border:1px solid var(--line);padding:5px 10px;text-align:left}
th{background:#141419}
#lb{position:fixed;inset:0;background:#000000f2;display:none;z-index:50;
 align-items:center;justify-content:center;flex-direction:column;gap:12px}
#lb img{max-width:94vw;max-height:84vh;background:#fff;border-radius:6px}
#lbc{color:var(--fg);font-size:13px}
.cell{position:relative}
.ib{position:absolute;top:16px;right:16px;width:23px;height:23px;border-radius:50%;
 background:#0d0d10cc;border:1px solid var(--line);color:var(--dim);font-size:12.5px;
 font-weight:700;line-height:21px;text-align:center;cursor:pointer;user-select:none;
 font-family:Georgia,serif;font-style:italic;-webkit-user-drag:none;user-drag:none;
 z-index:3}
.ib:hover{color:var(--fg);border-color:var(--acc);background:#17141fee}
#ic{position:fixed;inset:0;background:#000000e8;display:none;z-index:60;
 align-items:center;justify-content:center;padding:24px}
#icb{background:#141419;border:1px solid var(--line);border-radius:12px;max-width:min(92vw,980px);
 max-height:90vh;overflow:auto;padding:20px 22px}
#icb h3{margin:0 0 4px;font-size:16px}
#icb .who{color:var(--dim);font-size:12.5px;margin-bottom:14px}
.icrow{display:flex;gap:14px;flex-wrap:wrap}
.icc{flex:0 0 200px}
.icc img{width:100%;background:#fff;border-radius:6px;display:block}
.icc .cap{font-size:12px;font-weight:600;margin-top:6px}
.icc .sub{font-size:11.5px;color:var(--dim);line-height:1.4}
.icc.fin{flex:0 0 232px}
.icc.fin .cap{color:var(--acc)}
.arrow{align-self:center;color:var(--dim);font-size:20px}
#icx{float:right;color:var(--dim);cursor:pointer;font-size:20px;line-height:1;margin-left:12px}
#icx:hover{color:var(--fg)}
.cell[draggable=true]{cursor:grab}
.cell.drag{opacity:.35}
.cell .rk{-webkit-user-drag:none;user-drag:none;position:absolute;top:16px;left:16px;min-width:22px;height:22px;border-radius:6px;
 background:var(--acc);color:#fff;font-size:12px;font-weight:700;line-height:22px;
 text-align:center;padding:0 5px}
.cell.out .rk{background:#2a2a33;color:var(--dim)}
.cut{flex:0 0 30px;align-self:stretch;margin:8px 0;border-left:3px dashed var(--warn);
 cursor:grab;position:relative;background:linear-gradient(90deg,#d2992218,transparent)}
.cut span{position:absolute;top:50%;left:6px;transform:translateY(-50%) rotate(180deg);
 writing-mode:vertical-rl;color:var(--warn);font-size:10.5px;font-weight:700;
 letter-spacing:.09em;white-space:nowrap}
.cell.out img{filter:grayscale(.75) opacity(.5)}
.tier{flex:0 0 30px;align-self:stretch;margin:8px 0;border-left:3px solid var(--ok);
 cursor:grab;position:relative;background:linear-gradient(90deg,#3fb95022,transparent)}
.tier span{position:absolute;top:50%;left:6px;transform:translateY(-50%) rotate(180deg);
 writing-mode:vertical-rl;color:var(--ok);font-size:10.5px;font-weight:700;
 letter-spacing:.09em;white-space:nowrap}
.cell.topt{background:#0f1a12}
.cell.topt .rk{background:var(--ok)}
#save{position:fixed;right:20px;bottom:20px;z-index:40;background:var(--acc);color:#fff;
 border:0;border-radius:9px;padding:11px 17px;font-size:13px;font-weight:600;cursor:pointer;
 box-shadow:0 4px 18px #0008;font-family:inherit}
#save:hover{filter:brightness(1.12)}
#save small{display:block;font-weight:400;opacity:.85;font-size:11px}
"""

JS = """

// ---- ranking: drag cells to reorder, two bars decide tier and cut-off --------
// Order within a row IS the ranking. Two draggable bars split it:
//   TOP TIES  -- everything before it is the top tier, treated as equally good
//   CUT OFF   -- everything after it does not count at all
// NOTE: this function is paintRanks, not paint. An earlier version called it
// `paint`, colliding with the lightbox's paint(); the lightbox declaration hoisted
// over it, so restore() called the wrong one, hit `shots.length` before `shots`
// was assigned, and threw at load -- which silently killed every listener
// registered after it, including the info card and the CSV button.
var KEY = 'amt_rank_v2';
var store = {};
try { store = JSON.parse(localStorage.getItem(KEY) || '{}'); } catch (err) { store = {}; }

function paintRanks(strip){
  var tier = 'top', n = 0;
  Array.prototype.slice.call(strip.children).forEach(function(c){
    if (c.classList.contains('tier')) { if (tier === 'top') tier = 'mid'; return; }
    if (c.classList.contains('cut')) { tier = 'out'; return; }
    if (!c.classList.contains('cell') || c.classList.contains('truth')) return;
    var b = c.querySelector('.rk');
    if (!b) return;
    c.classList.remove('out', 'topt');
    if (tier === 'out') { c.classList.add('out'); b.textContent = '–'; }
    else { n++; b.textContent = n; if (tier === 'top') c.classList.add('topt'); }
  });
}
function readRow(strip){
  var tier = 'top', n = 0, rows = [];
  Array.prototype.slice.call(strip.children).forEach(function(c){
    if (c.classList.contains('tier')) { if (tier === 'top') tier = 'mid'; return; }
    if (c.classList.contains('cut')) { tier = 'out'; return; }
    if (!c.classList.contains('cell') || c.classList.contains('truth')) return;
    n++;
    rows.push({ arm: c.dataset.arm, rank: n, tier: tier });
  });
  return rows;
}
function save(strip){
  var sid = strip.parentNode.dataset.sid;
  store[sid] = readRow(strip);
  try { localStorage.setItem(KEY, JSON.stringify(store)); } catch (err) { /* full */ }
}
function restore(strip){
  var ref = strip.parentNode;
  if (!ref || !ref.dataset || !ref.dataset.sid) return;
  var s = store[ref.dataset.sid];
  if (!s || !s.length) { paintRanks(strip); return; }
  var tierBar = strip.querySelector('.tier'), cutBar = strip.querySelector('.cut');
  if (!tierBar || !cutBar) { paintRanks(strip); return; }
  var byArm = {};
  Array.prototype.slice.call(strip.children).forEach(function(c){
    if (c.dataset && c.dataset.arm) byArm[c.dataset.arm] = c;
  });
  var placedTier = false, placedCut = false;
  s.forEach(function(r){
    if (r.tier !== 'top' && !placedTier) { strip.appendChild(tierBar); placedTier = true; }
    if (r.tier === 'out' && !placedCut) { strip.appendChild(cutBar); placedCut = true; }
    var c = byArm[r.arm];
    if (c) strip.appendChild(c);
  });
  if (!placedTier) strip.appendChild(tierBar);
  if (!placedCut) strip.appendChild(cutBar);
  paintRanks(strip);
}
var dragEl = null;
document.body.addEventListener('dragstart', function(e){
  // the info button lives inside a draggable cell; without this, mousedown on it
  // starts a drag and the click never fires
  if (e.target.closest('.ib')) { e.preventDefault(); return; }
  var el = e.target.closest('.cell:not(.truth), .cut, .tier');
  if (!el) return;
  dragEl = el;
  el.classList.add('drag');
  e.dataTransfer.effectAllowed = 'move';
  try { e.dataTransfer.setData('text/plain', ''); } catch (err) { /* firefox */ }
});
document.body.addEventListener('dragend', function(){
  if (dragEl) dragEl.classList.remove('drag');
  dragEl = null;
});
document.body.addEventListener('dragover', function(e){
  if (!dragEl) return;
  var strip = e.target.closest('.strip');
  if (!strip || !strip.contains(dragEl)) return;
  e.preventDefault();
  var over = e.target.closest('.cell, .cut, .tier');
  if (!over || over === dragEl || over.classList.contains('truth')) return;
  var r = over.getBoundingClientRect();
  strip.insertBefore(dragEl, ((e.clientX - r.left) > r.width / 2) ? over.nextSibling : over);
});
document.body.addEventListener('drop', function(e){
  if (!dragEl) return;
  var strip = e.target.closest('.strip');
  if (!strip) return;
  e.preventDefault();
  paintRanks(strip);
  save(strip);
});
Array.prototype.slice.call(document.querySelectorAll('.strip')).forEach(function(s){
  restore(s);
});

var btn = document.getElementById('save');
if (btn) btn.addEventListener('click', function(){
  var q = String.fromCharCode(34), nl = String.fromCharCode(10);
  var rows = ['set_id,person,garment_source,arm,rank,tier,counted'];
  Array.prototype.slice.call(document.querySelectorAll('.ref[data-sid]')).forEach(function(ref){
    var strip = ref.querySelector('.strip');
    if (!strip) return;
    readRow(strip).forEach(function(r){
      rows.push([ref.dataset.sid, ref.dataset.person, ref.dataset.garment,
                 r.arm, r.rank, r.tier, r.tier === 'out' ? 'no' : 'yes']
        .map(function(v){ return q + String(v).replace(/"/g, '""') + q; }).join(','));
    });
  });
  var blob = new Blob([rows.join(nl) + nl], {type: 'text/csv'});
  var a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'v221_attention_mod_rankings.csv';
  document.body.appendChild(a);
  a.click();
  setTimeout(function(){ URL.revokeObjectURL(a.href); a.remove(); }, 400);
  btn.firstChild.nodeValue = 'Saved ✓  ';
  setTimeout(function(){ btn.firstChild.nodeValue = 'Save rankings CSV'; }, 1800);
});

var shots = [], at = -1;
var lb = document.getElementById('lb');
var lbi = document.getElementById('lbi');
var lbc = document.getElementById('lbc');
function paint(){
  if (at < 0 || at >= shots.length) return;
  lbi.src = shots[at].getAttribute('src');
  lbc.textContent = shots[at].getAttribute('alt');
}
var ic = document.getElementById('ic');
document.body.addEventListener('click', function(e){
  var ib = e.target.closest('.ib');
  if (ib && ic){
    document.getElementById('ictitle').textContent = ib.dataset.arm || '';
    document.getElementById('icwho').textContent = ib.dataset.who || '';
    document.getElementById('icsteps').innerHTML = ib.dataset.steps || '';
    ic.style.display = 'flex';
    e.stopPropagation();
    return;
  }
  if (ic && (e.target.id === 'ic' || e.target.id === 'icx')){ ic.style.display = 'none'; return; }
  if (ic && ic.style.display === 'flex') return;
  var im = e.target.closest('.cell img');
  if (!im) return;
  var row = im.closest('.strip');
  shots = Array.prototype.slice.call(row.querySelectorAll('img'));
  at = shots.indexOf(im);
  lb.style.display = 'flex';
  paint();
});
lb.addEventListener('click', function(){ lb.style.display = 'none'; });
document.addEventListener('keydown', function(e){
  if (e.key === 'Escape' && ic && ic.style.display === 'flex'){ ic.style.display = 'none'; return; }
  if (lb.style.display !== 'flex') return;
  if (e.key === 'Escape'){ lb.style.display = 'none'; return; }
  if (e.key === 'ArrowRight' && at < shots.length - 1){ at++; paint(); e.preventDefault(); }
  if (e.key === 'ArrowLeft'  && at > 0){ at--; paint(); e.preventDefault(); }
});
"""


# Ordered so the reviewer can work top to bottom: the crops page gates the AC
# decision, so it comes first.
PAGES = [("v221_attention_mod.html", "&#9733; Attention Modulation"),
         ("v221_phase3_acc.html", "0 &middot; AC-C destroy"),
         ("v221_phase3_acab.html", "1 &middot; AC-A / AC-B"),
         ("v221_phase3_crops.html", "2 &middot; Crops + PRE"),
         ("v221_phase3_fashn.html", "3 &middot; FASHN"),
         ("v221_phase3_ac.html", "4 &middot; AC arms"),
         ("v221_phase3_bg.html", "5 &middot; BG"),
         ("v221_phase3_m.html", "6 &middot; M")]


def _nav(current):
    out = ["<nav>"]
    for i, (f, lab) in enumerate(PAGES):
        if i:
            out.append("<span class='sep'>/</span>")
        cls = " class='here'" if f == current else ""
        out.append(f"<a href='{f}'{cls}>{lab}</a>")
    out.append("</nav>")
    return "".join(out)


def _shell(title, question, sub, body, current=""):
    return NL.join(
        [f"<title>{title}</title>", "<style>" + CSS + "</style>",
         f"<header><h1>{title}</h1><div class='q'>{question}</div>"
         f"<div class='sub'>{sub}</div></header>", _nav(current)]
        + body
        + ["<button id='save'>Save rankings CSV<small>then send me the file</small></button>",
           "<div id='ic'><div id='icb'><span id='icx'>&times;</span>"
           "<h3 id='ictitle'></h3><div class='who' id='icwho'></div>"
           "<div class='icrow' id='icsteps'></div></div></div>",
           "<div id='lb'><img id='lbi' alt=''><div id='lbc'></div></div>",
           "<script>" + JS + "</script>"])


def _cell(stem, tag, label, note, cls=""):
    rel = f"../runs/phase3/{stem}__{tag}.jpg"
    return (f"<div class='cell {cls}'><img src='{rel}' "
            f"alt='{html.escape(stem)} &mdash; {label}' loading='lazy'>"
            f"<div class='tag{' t' if cls == 'truth' else ''}'>{label}</div>"
            f"<div class='note'>{html.escape(str(note))}</div></div>")


def _write(name, text):
    os.makedirs(ART, exist_ok=True)
    p = os.path.join(ART, name)
    open(p, "w", encoding="utf-8").write(text)
    return p


# --------------------------------------------- ATTENTION MODULATION TEST ----
def page_amt(pairs, arms, gen, refs, meta):
    """The klein run. Ten ways of controlling what the model attends to in the
    garment reference, on the 20 pairs whose uncropped baseline failed.

    Each row leads with the two RAW inputs -- the untouched person and garment
    photographs -- so the eye starts from what was actually asked for. Every output
    then carries an info card showing the pipeline that produced its reference, so a
    wrong result can be traced to the reference or to klein without leaving the row."""
    LAB = {"control": "control &mdash; C3.1 today", "QX_qwen_p1": "QX &mdash; Qwen extraction",
           "BC_klein": "BC &mdash; bald &rarr; crop", "BALD_raw": "BALD &mdash; bald, uncropped",
           "D1hO": "D1h/O &mdash; blur, hair kept", "D2O": "D2/O &mdash; twirl, hair kept",
           "D3O": "D3/O &mdash; pixelate, hair kept", "D1hB": "D1h/B &mdash; blur, bald",
           "D2B": "D2/B &mdash; twirl, bald", "D3B": "D3/B &mdash; pixelate, bald"}
    FAM = {"control": "baseline", "QX_qwen_p1": "AC-A remove the person",
           "BC_klein": "AC-B remove the head", "BALD_raw": "AC-B remove nothing",
           "D1hO": "AC-C destroy identity", "D2O": "AC-C destroy identity",
           "D3O": "AC-C destroy identity", "D1hB": "AC-C destroy identity",
           "D2B": "AC-C destroy identity", "D3B": "AC-C destroy identity"}
    # the pipeline behind each arm, newest step last
    STEPS = {
        "control": [("raw", "raw garment photo"),
                    ("crop", "C3.1 crop &mdash; hair and face removed, white ground")],
        "QX_qwen_p1": [("raw", "raw garment photo"),
                       ("ref", "Qwen 2511 asked to return only the clothing")],
        "BC_klein": [("raw", "raw garment photo"), ("bald", "klein: &ldquo;make bald&rdquo;"),
                     ("ref", "then the cranium-fixed crop")],
        "BALD_raw": [("raw", "raw garment photo"), ("ref", "klein: &ldquo;make bald&rdquo; &mdash; no crop at all")],
        "D1hO": [("raw", "raw garment photo"), ("ref", "face blurred in place, hair kept, nothing cut")],
        "D2O": [("raw", "raw garment photo"), ("ref", "face twirled in place, hair kept")],
        "D3O": [("raw", "raw garment photo"), ("ref", "face pixelated in place, hair kept")],
        "D1hB": [("raw", "raw garment photo"), ("bald", "klein: &ldquo;make bald&rdquo;"),
                 ("ref", "then the head region blurred")],
        "D2B": [("raw", "raw garment photo"), ("bald", "klein: &ldquo;make bald&rdquo;"),
                ("ref", "then the head region twirled")],
        "D3B": [("raw", "raw garment photo"), ("bald", "klein: &ldquo;make bald&rdquo;"),
                ("ref", "then the head region pixelated")],
    }

    def rel(p):
        return os.path.relpath(os.path.join(REPO, p), ART) if p else None

    def card(src, arm):
        """HTML for the info modal: every step that produced this arm's reference."""
        out = []
        for kind, cap in STEPS[arm]:
            if kind == "raw":
                p = rel(meta.get(src, ""))
            elif kind == "bald":
                p = f"../runs/phase3/{src}__PRE2raw.jpg"
            else:
                r = refs.get(f"{src}|{arm}")
                p = f"../runs/amt/{r}" if r else None
            if not p or not os.path.exists(os.path.normpath(os.path.join(ART, p))):
                continue
            fin = " fin" if kind == "ref" else ""
            tag = "SENT TO KLEIN" if kind == "ref" else ("raw" if kind == "raw" else "intermediate")
            if out:
                out.append("<div class='arrow'>&rarr;</div>")
            out.append(f"<div class='icc{fin}'><img src='{p}' alt=''>"
                       f"<div class='cap'>{tag}</div><div class='sub'>{cap}</div></div>")
        return "".join(out).replace("'", "&#39;")

    b = ["<div class='legend'><ul>"
         "<li><b>One question, four mechanisms.</b> Every arm changes what klein attends to in the "
         "garment reference: <b>remove the person</b> (control, QX), <b>remove only the head</b> "
         "(BC), <b>remove nothing but destroy identity</b> (D1h/D2/D3 on both bases), or "
         "<b>remove nothing at all</b> (BALD). The run asks which mechanism klein responds to</li>"
         "<li>Each row starts with the <b>two raw inputs</b>, untouched. Every output carries an "
         "<b>&#9432; card</b> showing the pipeline that produced its reference, ending with the "
         "exact image sent to klein &mdash; so a wrong result traces to the reference or to klein "
         "without leaving the row</li>"
         "<li><b>/O arms cost nothing to produce</b> &mdash; no generative step, deterministic, no "
         "licence question. <b>/B arms need a bald frame first.</b> If an /O arm matches its /B "
         "twin, the whole bald pipeline is unnecessary</li>"
         "<li><b>BALD is the arm to watch.</b> The bald photograph with <b>no cropping at all</b>. "
         "If it holds up, the cropper &mdash; BiRefNet, the parser, every variant in this phase "
         "&mdash; is not earning its place</li>"
         "<li>Person image, prompt and seed (46) fixed; the <b>only</b> variable is the garment "
         "reference. Same 20 pairs whose uncropped baseline failed, so this compares directly "
         "against phase 2&rsquo;s 75% / 45% split</li>"
         "<li style='margin-top:8px'><b>Judge the garment, not the tidiness.</b> &sect;2b showed "
         "both instruments rewarding a plausible garment over the correct one &mdash; which is why "
         "this is an eye test</li>"
         "<li style='margin-top:8px'><b>Ranking.</b> Drag any output left or right &mdash; its "
         "position in the row <b>is</b> its rank, shown in the badge. Two bars split the row:</li>"
         "<li style='margin-left:14px'><span style='color:#3fb950;font-weight:700'>&#9650; TOP "
         "TIES</span> &mdash; everything before it is the <b>top tier</b>, all treated as "
         "equally good rather than forced into a false order. Those cells turn green</li>"
         "<li style='margin-left:14px'><span style='color:#d29922;font-weight:700'>&#9660; CUT "
         "OFF</span> &mdash; everything after it <b>does not count</b>: greyed out, recorded as "
         "the discard pile</li>"
         "<li style='margin-left:14px'>Both bars start <b>out of the way</b> &mdash; TOP TIES at "
         "the far left, CUT OFF at the far end &mdash; so every row opens as one plain ranked "
         "list with nothing discarded. Drag them inward as you decide. Everything between them is the "
         "ranked middle. Order saves to your browser as you go, so a refresh will not lose it. "
         "<b>Save rankings CSV</b> (bottom right) writes the file to send back &mdash; columns "
         "<code>set_id, person, garment_source, arm, rank, tier, counted</code></li>"
         "<li style='margin-top:8px'><b>Two conditions, and the split is the point.</b> The "
         "original 20 pairs were chosen because the <i>uncropped baseline</i> failed &mdash; an "
         "attention criterion. The <b>HIGH-DAMAGE</b> rows were chosen by a different one: "
         "<i>measured garment loss to the head cut</i>. Only 5 of 11 damage references appeared "
         "in the original set, and <b>the worst (p021, 19.5% lost) was never tested</b>, so plain "
         "C3.1 was winning on pairs where its own known weakness was largely absent. These six "
         "close that hole. Judge them as their own group: <b>does C3.1 fail here, and do the "
         "bald or pixelate arms rescue it?</b></li>"
         "<li style='margin-left:14px'><b>Each damaged garment is now worn by three "
         "different people.</b> With one person per garment a failure cannot be attributed "
         "&mdash; it could be the damage or the pairing. With three, the distinction is "
         "readable: <b>fails on all three &rarr; the damage is the cause; fails on one &rarr; "
         "the pairing is.</b> Rows carry a purple badge showing which replicate they are</li>"
         "<li style='opacity:.8'>QX covers 13 of 20 pairs; the fal balance ran out during "
         "reference prep. Weigh it as a smaller sample, not necessarily a weaker arm</li>"
         "</ul></div>"]
    for sid, per, src in pairs:
        have = [a for a in arms if f"{sid}|{a}" in gen]
        if not have:
            continue
        hd = sid.startswith("HD_")
        tag = ("<span class='pill fire'>HIGH-DAMAGE crop</span>" if hd else
               "<span class='pill keep'>low-damage crop</span>")
        if hd:
            # replicates of one damaged garment across different people: if a garment
            # fails on all its people the damage is the cause; if it fails on one, the
            # pairing is
            n = sum(1 for x in pairs if x[2] == src and x[0].startswith("HD_"))
            if n > 1:
                tag += (f"<span class='pill' style='border-color:#7c5cff;color:#7c5cff'>"
                        f"1 of {n} people wearing this garment</span>")
        b.append(f"<div class='ref' data-sid='{html.escape(sid)}' "
                 f"data-person='{html.escape(per)}' data-garment='{html.escape(src)}'>"
                 f"<div class='rh'><b>{html.escape(sid)}</b>"
                 f"<span class='m'>person <b>{html.escape(per)}</b> &middot; garment from "
                 f"<b>{html.escape(src)}</b></span>{tag}</div><div class='strip'>")
        for who, lab, note in ((per, "INPUT 1 &mdash; person", "who gets dressed"),
                               (src, "INPUT 2 &mdash; garment", "whose clothes")):
            p = rel(meta.get(who, ""))
            if p and os.path.exists(os.path.normpath(os.path.join(ART, p))):
                b.append(f"<div class='cell truth'><img src='{p}' alt='{html.escape(sid)} {lab}' "
                         f"loading='lazy'><div class='tag t'>{lab}</div>"
                         f"<div class='note'>{note} &mdash; raw, untouched</div></div>")
        b.append("<div class='tier' draggable='true'><span>&#9650; TOP TIES</span></div>")
        for a in have:
            b.append(f"<div class='cell' draggable='true' data-arm='{a}'>"
                     f"<span class='rk' draggable='false'></span>"
                     f"<span class='ib' draggable='false' data-arm='{LAB[a]}' "
                     f"data-who='{html.escape(sid)} &mdash; how this reference was made' "
                     f"data-steps=\"{card(src, a)}\">i</span>"
                     f"<img src='../runs/amt/gen/{gen[f'{sid}|{a}']}' draggable='false' "
                     f"alt='{html.escape(sid)} &mdash; {LAB[a]}' loading='lazy'>"
                     f"<div class='tag'>{LAB[a]}</div>"
                     f"<div class='note'>{FAM[a]}</div></div>")
        b.append("<div class='cut' draggable='true'><span>&#9660; CUT OFF</span></div>")
        b.append("</div></div>")
    return _write("v221_attention_mod.html", _shell(
        "AC &mdash; Attention Modulation Test",
        "Which way of controlling the garment reference does klein actually respond to?",
        "Ten arms across four mechanisms, on the 20 pairs whose uncropped baseline failed. "
        "Raw inputs first, then every arm&rsquo;s output &mdash; click &#9432; on any output to "
        "see the pipeline behind its reference. Click an image to zoom, &larr; &rarr; to step.", b,
        "v221_attention_mod.html"))


# ------------------------------------------------------------------- AC-C ----
def page_acc(cohort, files, notes):
    """Destroy the head instead of removing it."""
    b = ["<div class='legend' style='padding-top:20px'><b style='color:#7c5cff'>"
         "What happens to whatever you approve here:</b> it joins the klein batch "
         "already agreed &mdash; <b>control</b> (C3.1 as it ships), <b>QX_qwen_p1</b> "
         "(Qwen 2511 extraction), <b>BC_klein</b> (klein-bald &rarr; crop) and "
         "<b>bald uncropped</b>. Nothing goes to klein until you say which.</div>",
         "<div class='legend'><ul>"
         "<li><b>The idea.</b> Eight iterations went into head <i>removal</i> and each traded "
         "precision in one place for damage in another, because removal needs an exact boundary "
         "and an error leaves a white notch that gets read as garment. But removal was never the "
         "goal &mdash; the goal is that the model stops attending to a competing identity, and "
         "<b>destruction achieves that without an exact boundary</b>. Over-covering costs a little "
         "extra blurred skin: no identity, no garment, and the reference stays a photograph rather "
         "than an image with a hole in it</li>"
         "</ul></div>",
         "<div class='sec'>AC-C/O &mdash; original photo, hair kept, face destroyed</div>",
         "<div class='legend'><ul>"
         "<li><b>The cheaper branch, and probably the stronger one.</b> No generative call, fully "
         "deterministic, no licence question, no hallucination risk, milliseconds to run. If it "
         "works the entire bald pipeline is unnecessary</li>"
         "<li>It has a measured precedent: <b>C3.2 was &ldquo;keep the hair, remove the face&rdquo; "
         "and scored 45%</b>, and its recorded failure was <i>&ldquo;interpreted the white space as "
         "cloth&rdquo;</i> &mdash; the hole left by cutting the face out. This is C3.2 with the face "
         "destroyed <b>in place</b>: same information removed, no hole created</li>"
         "<li><b>What to judge:</b> is the identity actually gone? A blurred face that still reads "
         "as a specific person has not done its job</li>"
         "<li><b>Three blur tiers.</b> Radius scales with the region, not the image, so a small "
         "face in a wide frame is destroyed as thoroughly as a large one. Beyond a point "
         "<b>repeated passes matter more than radius</b> &mdash; n passes at sigma equals one at "
         "sigma&radic;n and flattens the region far faster, where simply widening one kernel just "
         "grows the halo. light = 1 pass &middot; <b>HEAVY = 3 passes, 2&times; radius</b> &middot; "
         "<b>EXTREME = 5 passes, 3.4&times; radius</b>, each with a wider feather</li>"
         "</ul></div>"]
    LO = {"D0O": "D0 &mdash; C3.1 control", "D1O": "D1 &mdash; blur (light)",
          "D1hO": "D1h &mdash; blur HEAVY", "D1xO": "D1x &mdash; blur EXTREME",
          "D2O": "D2 &mdash; twirl", "D3O": "D3 &mdash; pixelate"}
    LB = {"D0B": "D0 &mdash; AC-B control", "D1B": "D1 &mdash; blur (light)",
          "D1hB": "D1h &mdash; blur HEAVY", "D1xB": "D1x &mdash; blur EXTREME",
          "D2B": "D2 &mdash; twirl", "D3B": "D3 &mdash; pixelate",
          "D4B": "D4 &mdash; crop fix"}
    def rows(tags, labels):
        out = []
        for s in cohort:
            have = [t_ for t_ in tags if f"{s}|{t_}" in files]
            if not have:
                continue
            out.append(f"<div class='ref'><div class='rh'><b>{html.escape(s)}</b></div>"
                       "<div class='strip'>")
            for t_ in have:
                rel = f"../runs/acc/{files[f'{s}|{t_}']}"
                nt = notes.get(f"{s}|{t_}", "")
                warn = " style='color:#d29922'" if str(nt).startswith("FALLBACK") else ""
                out.append(f"<div class='cell'><img src='{rel}' alt='{html.escape(s)} "
                           f"&mdash; {labels[t_]}' loading='lazy'><div class='tag'>"
                           f"{labels[t_]}</div><div class='note'{warn}>"
                           f"{html.escape(str(nt))}</div></div>")
            out.append("</div></div>")
        return out
    b += rows(list(LO), LO)
    b.append("<div class='sec'>AC-C/B &mdash; bald frame, head region destroyed</div>"
             "<div class='legend'><ul>"
             "<li>Same operations on the AC-B bald crops. Costs a generative call the /O branch "
             "does not</li>"
             "<li><b>D4 is the crop fix</b>, run alongside rather than instead, so removal and "
             "destruction are compared directly. It uses morphological <b>opening</b> to sever the "
             "neck at its own constriction rather than at a guessed line &mdash; but that only "
             "works when a kernel exists <i>between</i> neck width and head width. "
             "<b>It applies on 2 of 11 references and falls back on 9</b>, marked in amber. "
             "Predicted in advance that it would not generalise; the prediction was right about "
             "the rate and wrong about which &mdash; p023 was called the worst case and is one of "
             "the two it works on</li>"
             "<li><b>Also visible here:</b> the subject matte includes <b>furniture</b> &mdash; a "
             "stool and a chair &mdash; on several references, and has done in every crop made so "
             "far. Found by rendering the masks and looking, not by any measurement</li>"
             "</ul></div>")
    b += rows(list(LB), LB)
    return _write("v221_phase3_acc.html", _shell(
        "Phase 3 &mdash; AC-C, destroy the head",
        "Is destroying the identity enough, without removing the head at all?",
        "All local, all free. Two bases: the original photo with hair kept, and the bald "
        "frame. Click to zoom, &larr; &rarr; to step across.", b, "v221_phase3_acc.html"))


# ------------------------------------------------------------- AC-A / AC-B ----
def page_acab(cohort, files, arms_a, prompts, drift=None):
    """The two candidate garment-reference pipelines, side by side.

    Neither has been sent to klein. This page is the gate: if the references look
    right, both go to klein on the failure pairs; if not, they get fixed first."""
    drift = drift or {}
    b = ["<div class='sec'>AC-A &mdash; garment extraction: &ldquo;return only the clothing&rdquo;</div>",
         "<div class='legend'><ul>"
         "<li>The <b>whole garment is regenerated</b>. That is the risk and the appeal: the output "
         "can be cleaner than anything subtractive, and nothing constrains it to the true garment</li>"
         "<li><b>Judge fidelity, not tidiness.</b> Compare each output against CONTROL at zoom, on "
         "pattern and colour. A beautiful crop of the wrong garment is the failure mode, and "
         "&sect;2b showed both our instruments reward a plausible garment over the correct one</li>"
         "<li><b>The amber note under each cell is a drift check</b> "
         "(<code>v2/build/extraction_drift.py</code>): median lightness, chroma and hue shift of "
         "the garment pixels against CONTROL, plus an edge-density ratio as a pattern proxy, with "
         "both images rescaled to the same garment height first. It is <b>triage, not a verdict</b> "
         "&mdash; it catches gross recolouring and smoothed-away texture, and cannot see a changed "
         "collar or a moved seam. Nothing flagged is automatically bad; nothing unflagged is "
         "automatically right</li>"
         "<li>Models: Qwen-Image-Edit-<b>2511</b> (Apache), Qwen-Image-Edit-<b>Plus</b>, "
         "klein 4B distilled, klein 4B base. Qwen 2511 gets three prompt variants, so "
         "<b>model and prompt are separable</b> rather than confounded</li>"
         "<li><b>2511 vs Plus.</b> 2511 is the newest <i>numbered</i> release and is explicitly the "
         "successor to 2509 &mdash; reduced identity drift, better character consistency, stronger "
         "geometric reasoning. &ldquo;Plus&rdquo; could not be settled by naming: it was the "
         "community nickname for 2509, yet one source dates it to 2026. The fal schemas differ "
         "materially (50 steps / guidance 4 versus 28 / 4.5), so they are different models and the "
         "question is answered by running both. Plus defaults to a square output, which would "
         "squash a portrait reference, so aspect is passed explicitly</li>"
         f"<li><b>p1</b> &ldquo;{html.escape(prompts['p1'][:88])}&hellip;&rdquo;</li>"
         f"<li><b>p2</b> &ldquo;{html.escape(prompts['p2'][:88])}&hellip;&rdquo;</li>"
         f"<li><b>p3</b> &ldquo;{html.escape(prompts['p3'][:88])}&hellip;&rdquo; (ghost-mannequin framing)</li>"
         "</ul></div>"]
    def row(stem, tags, labels, notes=None):
        notes = notes or {}
        have = [(t_, labels[t_]) for t_ in tags if f"{stem}|{t_}" in files]
        if not have:
            return []
        out = [f"<div class='ref'><div class='rh'><b>{html.escape(stem)}</b>"
               "</div><div class='strip'>"]
        for t_, lab in have:
            rel = f"../runs/acab/{files[f'{stem}|{t_}']}"
            cls = "truth" if t_ == "CTRL" else ""
            nt = notes.get(f"{stem}|{t_}", "")
            warn = " style='color:#d29922'" if str(nt).startswith("DRIFT") else ""
            out.append(f"<div class='cell {cls}'><img src='{rel}' alt='{html.escape(stem)} "
                       f"&mdash; {lab}' loading='lazy'><div class='tag{' t' if cls else ''}'>"
                       f"{lab}</div><div class='note'{warn}>{html.escape(str(nt))}</div></div>")
        out.append("</div></div>")
        return out
    LA = {"CTRL": "CONTROL &mdash; C3.1 today", "QX_qwen_p1": "Qwen 2511 p1",
          "QX_qwen_p2": "Qwen 2511 p2", "QX_qwen_p3": "Qwen 2511 p3 (ghost)",
          "QX_plus_p1": "Qwen PLUS p1", "QX_plus_p3": "Qwen PLUS p3 (ghost)",
          "QX_kleind": "klein distilled", "QX_kleinb": "klein base"}
    for stem in cohort:
        b += row(stem, ["CTRL"] + list(arms_a), LA, drift)

    b.append("<div class='sec'>AC-B &mdash; bald, then crop (cranium fix on)</div>"
             "<div class='legend'><ul>"
             "<li><b>Only the hair is regenerated</b>; the garment pixels are real, straight from "
             "the photograph. Low hallucination risk by construction &mdash; the crop can only "
             "remove, never invent</li>"
             "<li><b>The head now comes from a human parser</b> (SegFormer-B2 on ATR, 18 "
             "human-part classes). It replaces a geometric heuristic patched seven times that was "
             "still trading references against each other &mdash; grow the ellipse and it catches "
             "the scalp but eats collars, shrink it and the reverse. An ellipse cannot know where "
             "a head ends and a collar begins. ATR's Face class covers the <b>head region</b> "
             "rather than facial skin, which is exactly what the bald case needs. Head removal is "
             "up <b>+5.0 points on average</b>; p016 went 3.5% &rarr; 11.9%, p023 10.6% &rarr; "
             "23.4%. Head, garment and skin now all come from <b>one</b> model, so they are "
             "disjoint by construction</li>"
             "<li><b>The parser alone was not enough either.</b> ATR&rsquo;s <code>face</code> "
             "class <b>bleeds down the body</b> on bald frames &mdash; the model was trained on "
             "people with hair, so a bald head above a bare neck and chest reads as one continuous "
             "face region. Measured: the head class reached 134% of the ear-to-shoulder span on "
             "p021, 292% on zendaya and <b>499% &mdash; the bottom of the frame &mdash; on p023</b>. "
             "So each model now does only what it is good at: the <b>parser supplies the shape</b> "
             "(the scalp boundary, which no heuristic could get) and <b>pose supplies the extent</b> "
             "(where a head stops), then only the component containing the nose is kept. Head "
             "extent is now ~70% of ear-to-shoulder on every reference and 7&ndash;17% of the "
             "subject &mdash; the correct anatomical proportion</li>"
             "<li style='opacity:.75'>Superseded, kept as fallbacks: pose ellipse, then the "
             "face-anchored band. Neither fired on any reference here. The old mask was "
             "HAIR + FACE, so on a bald frame the head signal vanished with the hair signal and "
             "<b>half the skull survived the cut</b> (head removal fell from 17.6% of the subject "
             "to 8.6%). Anatomy and appearance are now separate: a skull ellipse from ear "
             "landmarks fires <b>always</b>, and the HAIR class only adds what lies outside it. "
             "One rule covers bald, short hair and long hair</li>"
             "<li>Three constraints, each measured rather than tuned &mdash; the ellipse is sized "
             "from <b>ear separation</b> (skull width at ear level), <b>clipped at the neck</b> "
             "(between the ear and shoulder landmarks), and the <b>clothes class is protected</b>, "
             "so a high collar or hood inside the ellipse survives. Result: <b>0 of 11 references "
             "lose garment area</b>, down from 2, and p030 went from &minus;3.4 points to "
             "&minus;0.1. MediaPipe Pose lite, Apache-2.0, 5.8MB</li>"
             "<li><b>What to check by eye:</b> the numbers show no garment lost and more head "
             "removed, but they cannot prove the <b>whole skull is gone</b>. Look at the top of "
             "each crop &mdash; that is the one thing this fix was for, and the only thing that "
             "settles it</li>"
             "</ul></div>")
    LB = {"CTRL": "CONTROL &mdash; C3.1 today", "BC_klein": "bald(klein) &rarr; crop",
          "BC_qwen": "bald(Qwen) &rarr; crop"}
    for stem in cohort:
        b += row(stem, ["CTRL", "BC_klein", "BC_qwen"], LB)

    return _write("v221_phase3_acab.html", _shell(
        "Phase 3 &mdash; AC-A extraction vs AC-B bald+crop",
        "Do either of these produce a garment reference good enough to send to klein?",
        "Both descend from the AC section: AC-A from AC8 (generative crop), AC-B from PRE "
        "(repair before cropping). Nothing here has been sent to klein &mdash; this page is "
        "the gate.", b, "v221_phase3_acab.html"))


# ------------------------------------------------------------------ FASHN ----
def page_fashn(pairs, files, klein=None):
    """FASHN v1.5 against the same 20 pairs whose klein baseline failed.

    v1.5 is PINNED -- fal's v1.6 is FASHN's CLOSED commercial model, outside the
    open-weights deploy path.

    The question is NOT which model is better. FASHN does its own garment
    segmentation (`garment_photo_type`, `segmentation_free`), so this asks whether
    our preprocessing helps a purpose-built VTO model, is redundant for it, or
    destroys drape information it was using."""
    klein = klein or {}
    b = ["<div class='legend'><ul>"
         "<li><b>FA_base</b> &mdash; the raw on-model photograph as the garment reference</li>"
         "<li><b>FA_c31</b> &mdash; our C3.1 crop instead</li>"
         "<li><b>FA_pre3</b> &mdash; the Qwen bald frame, where one exists</li>"
         "<li style='margin-top:8px'>Person image, seed (46) and mode (quality) are held fixed; "
         "the only variable is the garment reference. Same 20 pairs that produced klein's "
         "75% / 45% arm split, so the comparison is direct</li>"
         "<li><b>base &asymp; c31</b> &rarr; FASHN's internal segmentation already handles worn "
         "references and cropping is redundant <i>for it</i> &mdash; an argument about FASHN, not "
         "against the cropper, since klein demonstrably needs the help</li>"
         "<li><b>c31 &gt; base</b> &rarr; the attention deficit is <b>not klein-specific</b> and "
         "cropping is a general preprocessing win</li>"
         "<li><b>base &gt; c31</b> &rarr; our crops are <b>destroying drape and fit information</b> "
         "a VTO model uses &mdash; the strongest argument yet for the mannequin over pure "
         "subtraction</li>"
         "<li style='margin-top:8px'>This is a diagnostic on the <b>cropper</b>, not a leaderboard. "
         "One comparison on 20 adversarially-chosen failure pairs cannot overturn a base-model "
         "decision made on breadth as well as transfer quality.</li>"
         "</ul></div>"]
    for sid, per, src in pairs:
        have = [(t_, lab) for t_, lab in (("FA_base", "FASHN &mdash; uncropped ref"),
                                          ("FA_c31", "FASHN &mdash; C3.1 crop"),
                                          ("FA_pre3", "FASHN &mdash; bald ref"))
                if f"{sid}|{t_}" in files]
        if not have:
            continue
        b.append(f"<div class='ref'><div class='rh'><b>{html.escape(sid)}</b>"
                 f"<span class='m'>person <b>{html.escape(per)}</b> &middot; garment from "
                 f"<b>{html.escape(src)}</b></span></div><div class='strip'>")
        for tag, rel, lab, note in [("in_p", f"../runs/crop_screen/{per}__c1_bbox.jpg",
                                     "INPUT 1 &mdash; person", "who gets dressed"),
                                    ("in_g", f"../runs/crop_screen/{src}__c1_bbox.jpg",
                                     "INPUT 2 &mdash; garment source", "whose clothes")]:
            if os.path.exists(os.path.normpath(os.path.join(ART, rel))):
                b.append(f"<div class='cell'><img src='{rel}' alt='{html.escape(sid)} {lab}' "
                         f"loading='lazy'><div class='tag'>{lab}</div>"
                         f"<div class='note'>{note}</div></div>")
        for t_, lab in have:
            rel = f"../runs/fashn/{files[f'{sid}|{t_}']}"
            b.append(f"<div class='cell'><img src='{rel}' alt='{html.escape(sid)} &mdash; {lab}' "
                     f"loading='lazy'><div class='tag'>{lab}</div><div class='note'></div></div>")
        b.append("</div></div>")
    return _write("v221_phase3_fashn.html", _shell(
        "Phase 3 &mdash; FASHN cross-check",
        "Does our cropping help a purpose-built try-on model, or is it solving a problem "
        "FASHN does not have?",
        "FASHN v1.5, pinned &mdash; v1.6 is the closed commercial model and is outside the "
        "open-weights deploy path. Click to zoom, &larr; &rarr; to step across.", b, "v221_phase3_fashn.html"))


# ------------------------------------------------------------------ CROPS ----
def page_crops(stems, rows, pre=None):
    """Shown BEFORE the AC arms re-run, because both the over-crop and PRE change
    their input. If the wider cut or the repaired frame looks wrong here, nothing
    downstream is worth running."""
    pre = pre or {}
    by = {r["stem"]: r for r in rows}
    b = ["<div class='sec'>1 &mdash; the defect, and cutting wider to escape it</div>",
         "<div class='legend'><ul>"
         "<li><b>C3.1</b> &mdash; the cut as it ships today</li>"
         "<li><b>fringe</b> &mdash; hair-contaminated pixels that <b>survive</b> the cut, "
         "highlighted. 0.08&ndash;4.69% of garment area and <b>darker than the garment in every "
         "reference</b>, so it reads as a dark rim tracing the cut line</li>"
         "<li><b>OC5</b> &mdash; over-crop to an <b>area target</b> (5% of garment). The solved "
         "radius turned out <b>inversely related to the defect</b>: p016 has the largest fringe "
         "and solved to 5px, p023 has almost none and solved to 60px, because an area target is "
         "driven by head-mask perimeter rather than by contamination</li>"
         "<li><b>OCF</b> &mdash; over-crop to the <b>measured fringe</b> instead. Scales with the "
         "defect, lands near-constant. Judge whether either eats something structural &mdash; a "
         "collar, a shoulder seam, a hem</li>"
         "</ul></div>"]
    for s in stems:
        r = by.get(s, {})
        b.append(f"<div class='ref'><div class='rh'><b>{html.escape(s)}</b>"
                 f"<span class='m'>fringe {r.get('fringe_pct', '?')}% &middot; "
                 f"OC5 {r.get('oc_radius', '?')}px, removed {r.get('oc_before', '?')}% &rarr; "
                 f"{r.get('oc_after', '?')}%</span></div><div class='strip'>")
        for t_, lab, note in (("AC0", "C3.1 &mdash; current", "ships today"),
                              ("FRINGE", "fringe highlighted", "hair surviving the cut"),
                              ("OC5", "OC5 &mdash; area-targeted", r.get("oc_note", "")),
                              ("OCF", "OCF &mdash; fringe-targeted", pre.get(f"{s}|OCF", ""))):
            if os.path.exists(os.path.join(REPO, "v2", "runs", "phase3", f"{s}__{t_}.jpg")):
                b.append(_cell(s, t_, lab, note))
        b.append("</div></div>")

    b.append("<div class='sec'>2 &mdash; PRE: repair the raw photo, then crop normally</div>"
             "<div class='legend'><ul>"
             "<li>A <b>different architecture</b>, not another arm. AC crops and then fills the "
             "damage; PRE repairs the raw frame so the damage is never created</li>"
             "<li><b>PRE1</b> LaMa over the hair region, no prompt &middot; <b>PRE2</b> klein and "
             "<b>PRE3</b> Qwen, both prompted <i>&ldquo;make this person completely bald&rdquo;</i></li>"
             "<li>All three then run the <b>unchanged cropper</b>, so the only variable is the raw "
             "image it receives. Each caption reports what the head cut took and how much fringe "
             "survived &mdash; compare against PRE0</li>"
             "<li style='margin-top:8px'>The prediction, recorded before the run: PRE should beat "
             "AC because filling a <b>white hole in a crop</b> is out of distribution with no "
             "context, while <b>hair removal on a whole portrait</b> is a routine edit with the "
             "entire body as context. <b>PRE1 vs AC6 is the clean test</b> &mdash; same LaMa "
             "weights, different position in the pipeline</li>"
             "</ul></div>")
    for s in stems:
        have = [t_ for t_ in ("AC0", "PRE1", "PRE2", "PRE3")
                if os.path.exists(os.path.join(REPO, "v2", "runs", "phase3", f"{s}__{t_}.jpg"))]
        if len(have) < 2:
            continue
        b.append(f"<div class='ref'><div class='rh'><b>{html.escape(s)}</b>"
                 "<span class='m'>cropped result after each repair</span>"
                 "</div><div class='strip'>")
        for t_ in have:
            lab = {"AC0": "PRE0 &mdash; control", "PRE1": "PRE1 &mdash; LaMa",
                   "PRE2": "PRE2 &mdash; klein bald", "PRE3": "PRE3 &mdash; Qwen bald"}[t_]
            key = "PRE0" if t_ == "AC0" else t_
            b.append(_cell(s, t_, lab, pre.get(f"{s}|{key}", "")))
        b.append("</div></div>")

    b.append("<div class='sec'>3 &mdash; the repaired raw frames themselves</div>"
             "<div class='legend'>What the cropper actually received. A bald edit that changed the "
             "clothing, the pose or the body is a failure even if the crop downstream looks "
             "clean.</div>")
    for s in stems:
        have = [t_ for t_ in ("PRE1raw", "PRE2raw", "PRE3raw")
                if os.path.exists(os.path.join(REPO, "v2", "runs", "phase3", f"{s}__{t_}.jpg"))]
        if not have:
            continue
        b.append(f"<div class='ref'><div class='rh'><b>{html.escape(s)}</b>"
                 "<span class='m'>raw frame after repair, before any cropping</span>"
                 "</div><div class='strip'>")
        for t_ in have:
            b.append(_cell(s, t_, t_.replace("raw", " raw"), ""))
        b.append("</div></div>")

    return _write("v221_phase3_crops.html", _shell(
        "Phase 3 &mdash; over-crop and PRE",
        "Remove the hair rim by cutting wider, or by repairing the photo before cropping at all?",
        "Free except the two bald arms. The AC arms are not re-run until this passes, "
        "because both approaches change their input.", b, "v221_phase3_crops.html"))


# ---------------------------------------------------------------------- M ----
def page_m(stems, rows):
    by = {r["stem"]: r for r in rows}
    b = ["<div class='legend'><ul>"
         "<li><b>M0</b> &mdash; C3.1 as it ships today, the wearer's body untouched. Control</li>"
         "<li><b>M1</b> &mdash; flat mid-grey fill. No shading, so an arm stops reading as a "
         "cylinder &mdash; bounds what the colour alone buys</li>"
         "<li><b>M2</b> &mdash; shaded grey: LAB, a/b zeroed, L compressed to [116,196]. "
         "Keeps 3D form, destroys hue. Expected winner</li>"
         "<li style='margin-top:8px'>Two failure risks pull opposite ways &mdash; being read as "
         "<b>clothing</b> wants contrast, <b>attracting attention</b> wants none. They resolve "
         "because they are contrasts against different things: the mannequin should sit close to "
         "the <b>ground</b> and stay separable from the <b>garment</b>.</li>"
         "</ul></div>"]
    for s in stems:
        r = by.get(s, {})
        b.append(f"<div class='ref'><div class='rh'><b>{html.escape(s)}</b>"
                 f"<span class='m'>visible body = {r.get('body_pct', '?')}% of the crop</span>"
                 "</div><div class='strip'>")
        b.append(_cell(s, "M0", "M0 &mdash; control", "wearer's body as-is"))
        b.append(_cell(s, "M1", "M1 &mdash; flat grey", "no shading"))
        b.append(_cell(s, "M2", "M2 &mdash; shaded grey", "achromatic, form kept"))
        b.append("</div></div>")
    return _write("v221_phase3_m.html", _shell(
        "Phase 3 &mdash; M, mannequin",
        "Does the mannequin read as a neutral form &mdash; not as clothing, and not as "
        "something worth attending to?",
        "Click an image to zoom, &larr; &rarr; to step across the row. Nothing here has "
        "been sent to klein.", b, "v221_phase3_m.html"))


# --------------------------------------------------------------------- BG ----
def page_bg(stems, rows, ranked):
    by = {r["stem"]: r for r in rows}
    b = ["<div class='legend'><ul>"
         "<li><b>BG1</b> #FFFFFF &mdash; control, what ships today</li>"
         "<li><b>BG2</b> flat #F1F1F1 &mdash; the shop-imagery <i>model-shot</i> spec; "
         "#FFFFFF is the <i>packshot</i> spec, and these crops are model shots</li>"
         "<li><b>BG3</b> adaptive &mdash; a neutral ramp value chosen per reference to clear "
         "&ge;15 &Delta;L* at the garment edge. Brown garment keeps white; white garment gets grey</li>"
         "<li><b>BG4</b> BG3 + radial falloff + contact shadow &mdash; real packshot white is "
         "<i>photographed</i>, and flat synthetic #FFFFFF deletes exactly the separability cue "
         "the falloff provides</li>"
         "<li><b>BG5</b> <b>#FFFFFF + contact shadow, nothing else</b> &mdash; isolates the shadow "
         "from the colour change. BG4 moves the ground <i>and</i> adds falloff <i>and</i> adds a "
         "shadow, so if BG4 wins we cannot say which part did the work. Here the ground stays "
         "white: packshot convention untouched, no way to tint the garment, and the cue is created "
         "<b>locally at the silhouette</b> &mdash; which works at any garment colour, "
         "white-on-white included</li>"
         "<li style='margin-top:8px'>The question here is <b>whether the detector called it "
         "right</b>, not which image looks nicest. Each row prints the measured edge L*, the "
         "margin against white, and the resulting call.</li>"
         "<li>The measure is an <b>area share</b>, not a median. A first version used the "
         "median luminance in a band inside the boundary and <b>failed its own test case</b>: "
         "p014, the one reference with a documented white-garment failure, is a white t-shirt "
         "over dark trousers &mdash; median L*=57 but 22% of the garment near-white, so a "
         "central statistic averaged the collision away. The table below ranks every reference "
         "by pale share so the 15% bar can be moved on evidence.</li>"
         "</ul></div>"]
    for s in stems:
        r = by.get(s, {})
        fires = r.get("fires")
        pill = ("<span class='pill fire'>switches ground</span>" if fires
                else "<span class='pill keep'>keeps white</span>")
        b.append(f"<div class='ref'><div class='rh'><b>{html.escape(s)}</b>"
                 f"<span class='m'>{r.get('pale_pct', '?')}% of garment near-white &middot; "
                 f"median L* {r.get('pale_median_L', '?')}</span>{pill}"
                 "</div><div class='strip'>")
        for t in ("BG1", "BG2", "BG3", "BG4", "BG5"):
            b.append(_cell(s, t, t, r.get(f"note_{t}", "")))
        b.append("</div></div>")
    b.append("<div class='sec'>All 48 references ranked by margin against white "
             "(largest share = hardest to separate from white)</div><table>"
             "<tr><th>#</th><th>reference</th><th>% near-white</th><th>call at 15%</th></tr>")
    for i, (m, s) in enumerate(ranked, 1):
        call = "switch" if m >= 15 else "white"
        b.append(f"<tr><td>{i}</td><td>{html.escape(s)}</td><td>{m:.1f}</td><td>{call}</td></tr>")
    b.append("</table>")
    return _write("v221_phase3_bg.html", _shell(
        "Phase 3 &mdash; BG, ground selection",
        "Did the detector decide correctly?",
        "The deliverable of this component is the <b>decision rule</b>, not a ground colour. "
        "Click an image to zoom, &larr; &rarr; to step across the row.", b, "v221_phase3_bg.html"))


# --------------------------------------------------------------------- AC ----
def page_ac(stems, rows, fal=None):
    import json
    by = {r["stem"]: r for r in rows}
    fal = fal or {}
    b = ["<div class='legend'><ul>"
         "<li><b>AC0</b> unrepaired &mdash; control</li>"
         "<li><b>AC1</b> <b>algebra</b> &mdash; un-composite B = (I &minus; &alpha;F)/(1 &minus; &alpha;). "
         "Reconstruction, not hallucination; blows up as &alpha;&rarr;1, so it shrinks the damage to "
         "the opaque core rather than removing it</li>"
         "<li><b>AC2</b> Telea PDE &middot; <b>AC3</b> xphoto FSR &middot; <b>AC4</b> xphoto SHIFTMAP "
         "patch search &mdash; all three zero-weight, so <b>no licence exposure at all</b></li>"
         "<li><b>feather</b> &mdash; orthogonal preprocessing, not an arm: erode the head mask and "
         "keep thin strands. The measured damage is an <b>open boundary notch</b>, not an enclosed "
         "hole, so not creating it beats repairing it</li>"
         "<li><b>AC5</b> MI-GAN &middot; <b>AC6</b> LaMa &mdash; learned fillers, CPU TorchScript. "
         "Apache/MIT code but <b>Places2-trained weights</b>, whose data terms say non-commercial: "
         "these exist to find out whether a learned filler is needed at all</li>"
         "<li><b>AC7.1</b> klein &middot; <b>AC7.2</b> Qwen-Image-Edit &middot; <b>AC7.3</b> Z-Image Turbo "
         "&mdash; generative <b>repair</b> of the existing crop. 7.2 and 7.3 are <b>mask-native</b> "
         "(true inpainting); 7.1 has no mask input so it is generate-then-composite</li>"
         "<li><b>AC8.1</b> klein &middot; <b>AC8.2</b> Qwen-Image-Edit &mdash; generative <b>crop</b>: "
         "the raw photo goes in and the garment comes out, with <b>no cropper involved at all</b>. "
         "This is the control on whether the deterministic stack earns its complexity &mdash; and "
         "the one family that can <b>hallucinate</b> the garment, which a subtractive crop cannot</li>"
         "<li><b>AC9</b> SeedVR2 restore over the Telea fill. No prompt parameter exists on that "
         "endpoint, so it is image-only by necessity</li>"
         "<li style='margin-top:8px'>For AC8, judge <b>fidelity to the real garment</b>, not just "
         "how clean the cutout is. Section 2b showed both instruments reward a plausible garment "
         "over the correct one, so a beautiful crop of the wrong clothes is the failure to watch for.</li>"
         "</ul></div>"]
    for s in stems:
        r = by.get(s, {})
        b.append(f"<div class='ref'><div class='rh'><b>{html.escape(s)}</b>"
                 f"<span class='m'>head cut took {r.get('lost_pct', '?')}% of the garment</span>"
                 "</div><div class='strip'>")
        for t, lab in (("AC0", "AC0 &mdash; control"), ("ACfeather", "feather (preproc)"),
                       ("AC1", "AC1 &mdash; algebra"), ("AC2", "AC2 &mdash; Telea"),
                       ("AC3", "AC3 &mdash; FSR"), ("AC4", "AC4 &mdash; SHIFTMAP"),
                       ("AC5", "AC5 &mdash; MI-GAN"), ("AC6", "AC6 &mdash; LaMa"),
                       ("AC7.1", "AC7.1 &mdash; klein"), ("AC7.2", "AC7.2 &mdash; Qwen inpaint"),
                       ("AC7.3", "AC7.3 &mdash; Z-Image inpaint"), ("AC9", "AC9 &mdash; SeedVR2")):
            key = "AC0" if t == "ACfeather" else t
            note = ("head mask eroded + feathered" if t == "ACfeather"
                    else fal.get(f"{s}|{t}") or r.get(f"note_{key}", ""))
            if not os.path.exists(os.path.join(REPO, "v2", "runs", "phase3", f"{s}__{t}.jpg")):
                continue
            b.append(_cell(s, t, lab, note))
        b.append("</div></div>")

    b.append("<div class='sec'>AC8 &mdash; generative crop, no cropper involved</div>"
             "<div class='legend'>Raw photo in, garment out, one call. If this matches the "
             "deterministic stack then BiRefNet, MediaPipe, subtractive composition, M, BG and AC "
             "itself all stop being necessary. <b>Judge fidelity, not tidiness</b>: this is the only "
             "family that can invent garment content, where a subtractive crop can only ever "
             "remove pixels.</div>")
    for s in stems:
        have = [t for t in ("AC0", "AC8.1", "AC8.2")
                if os.path.exists(os.path.join(REPO, "v2", "runs", "phase3", f"{s}__{t}.jpg"))]
        if len(have) < 2:
            continue
        b.append(f"<div class='ref'><div class='rh'><b>{html.escape(s)}</b>"
                 "<span class='m'>deterministic C3.1 vs one-call generative crop</span>"
                 "</div><div class='strip'>")
        for t in have:
            lab = {"AC0": "C3.1 &mdash; deterministic", "AC8.1": "AC8.1 &mdash; klein",
                   "AC8.2": "AC8.2 &mdash; Qwen"}[t]
            b.append(_cell(s, t, lab, fal.get(f"{s}|{t}", "current pipeline" if t == "AC0" else "")))
        b.append("</div></div>")

    return _write("v221_phase3_ac.html", _shell(
        "Phase 3 &mdash; AC, auto-complete",
        "Is the garment whole again &mdash; and on the synthetic bed, is it right as well as "
        "plausible?",
        "Click an image to zoom, &larr; &rarr; to step across the row. Nothing here has been "
        "sent to klein.", b, "v221_phase3_ac.html"))
