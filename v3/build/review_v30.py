"""Build the v3.0 review page: 36 pairs x 2 arms, marked by hand.

Grouped by garment reference, because the matrix is garment-driven and the
question is which references fail for everyone. Verdicts and band tags are held
in localStorage and exported as v30_review.csv. Deterministic; rebuild any time
without losing marks (they key on set_id|arm, not on position).
"""
import csv
import html
import json
import os
import sys

from PIL import Image

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
LABEL = sys.argv[sys.argv.index("--run") + 1] if "--run" in sys.argv else "b"
RUN = os.path.join(REPO, "v3", "runs", f"v3.0{LABEL}")
REPORT = os.path.join(REPO, "v3", "report")
IMG = os.path.join(REPORT, f"img30{LABEL}")


ARMS = [("BC", "BC_klein"), ("QX", "QX")]


def web(src, dst, width):
    out = os.path.join(IMG, dst)
    if not os.path.exists(src):
        return None
    if not os.path.exists(out):
        im = Image.open(src).convert("RGB")
        if im.width > width:
            im = im.resize((width, int(im.height * width / im.width)), Image.LANCZOS)
        im.save(out, quality=86, optimize=True)
    return f"img30{LABEL}/" + dst


def fig(src, cap, cls=""):
    if not src:
        return ("<figure class='miss'><div class='ph'>not generated<br>"
                f"<span>fal balance</span></div><figcaption>{cap}</figcaption></figure>")
    return (f"<figure class='{cls}'><img src='{src}' alt='{html.escape(cap)}'>"
            f"<figcaption>{cap}</figcaption></figure>")


def main():
    os.makedirs(IMG, exist_ok=True)
    rows = list(csv.DictReader(open(os.path.join(
        REPO, f"v3/testsets/v30_matrix_{LABEL}.csv"))))
    run = json.load(open(os.path.join(RUN, "_run.json")))
    global ARMS
    # QQ (all-Qwen) is a closed side-branch; its frames stay on disk, off the page.
    # QMB is v3.1's ghost-mannequin arm and joins the comparison when it exists.
    if any(k.endswith("|QMB") for k in run.get("outputs", {})):
        ARMS = [("BC", "BC_klein &mdash; subtractive crop"),
                ("QX", "QX &mdash; isolated on white"),
                ("QMB", "QMB &mdash; ghost mannequin")]

    groups = {}
    for r in rows:
        groups.setdefault(r["garment"], []).append(r)

    done = len(run.get("outputs", {}))
    banner = ""
    if done < len(rows) * 2:
        banner = (f"<div class='warn'><b>{done} of {len(rows) * 2} outputs generated.</b> "
                  f"The run stopped on an exhausted fal balance; the remaining "
                  f"{len(rows) * 2 - done} cells are marked <i>not generated</i> and are "
                  "not failures of either arm. Re-running <code>run_v30.py --run b --only "
                  "edit</code> after a top-up fills only the gaps.</div>")
    body = [HEAD, TOOLBAR, "<div class='wrap'>", banner]
    n_cells = 0
    for g, rs in groups.items():
        meta = rs[0]
        if "garment_kind" in meta:            # run A: 12 references x 3 people
            tag = f"{meta['garment_kind']} · stresses {meta['stress']}"
            why = meta["why"]
        else:                                  # run B: the fold, one pair per reference
            tag = f"pair {meta['pair']} of 28 · {meta['garment_src']}"
            bits = [b for b in (meta["garment_category"], meta["garment_hard_case"]) if b]
            if meta["bald_pass_useful"] == "no":
                bits.append("no hair in frame — the bald pass has nothing to remove")
            why = " · ".join(bits) or "no metadata"
        body.append(f"<h2 id='{g}'><span class='m'>{html.escape(tag)}</span>{g}"
                    f"<span class='sub'> · {html.escape(why)}</span></h2>")
        body.append("<div class='lab'>the reference chain — raw, then what each arm handed to call 2</div>")
        strip = [fig(web(os.path.join(RUN, "inputs", f"{g}.jpg"), f"{g}__src.jpg", 400),
                     "garment reference (raw)")]
        bald = os.path.join(RUN, "refs", f"{g}__bald.jpg")
        strip.append(fig(web(bald, f"{g}__bald.jpg", 400), "call 1 — bald")
                     if os.path.exists(bald) else
                     "<figure class='na'><div class='ph'>not balded<br><span>no wearer</span></div>"
                     "<figcaption>call 1</figcaption></figure>")
        strip.append(fig(web(os.path.join(RUN, "refs", f"{g}__BC.jpg"), f"{g}__BC.jpg", 400),
                         "BC_klein ref — subtracted"))
        strip.append(fig(web(os.path.join(RUN, "refs", f"{g}__QX.jpg"), f"{g}__QX.jpg", 400),
                         "QX ref — regenerated"))
        body.append("<div class='strip s4'>" + "".join(strip) + "</div>")

        for r in rs:
            sid = r["set_id"]
            pills = [r.get("person_hair") and f"{r['person_hair']} hair",
                     r.get("person_tone"), r.get("person_view"),
                     r.get("person_pose"), r.get("person_gender"), r.get("person_framing")]
            body.append(f"<div class='pair'><div class='ph2'><b>{r['person']}</b>"
                        + "".join(f"<span class='pill'>{html.escape(p)}</span>"
                                  for p in pills if p) + "</div>")
            cells = [fig(web(os.path.join(RUN, "inputs", f"{r['person']}.jpg"),
                             f"{r['person']}__p.jpg", 420), "person (input)")]
            for arm, label in ARMS:
                src = web(os.path.join(RUN, "gen", f"{sid}__{arm}.jpg"),
                          f"{sid}__{arm}.jpg", 460)
                key = f"{sid}|{arm}"
                n_cells += 1
                cells.append(
                    f"<div class='cell' data-k=\"{html.escape(key)}\">"
                    + fig(src, label)
                    + "<div class='v'>"
                    + "".join(f"<button class='t' data-t='{t}'>{t}</button>"
                              for t in ("perfect", "ok", "fail"))
                    + "</div><div class='v b'>"
                    + "".join(f"<button class='bd' data-b='{b}' title='{ttl}'>{b}</button>"
                              for b, ttl in (("over", "over-attention — more arrived than the garment"),
                                             ("quest", "questionable — partial or drifted"),
                                             ("failed", "failed — nothing arrived")))
                    + "</div><input class='note' placeholder='note (optional)'></div>")
            body.append(f"<div class='strip {'s4c' if len(ARMS) == 3 else 's3'}'>"
                        + "".join(cells) + "</div></div>")

    body.append(f"<footer><div class='wrap'>{len(rows)} pairs &middot; {n_cells} cells &middot; "
                f"seed {run['seed']} &middot; prompt and conditions in "
                f"<code>prd/v3/v3.0/TEST.md</code>. Marks are stored in this browser; "
                f"<b>export before closing</b>.</div></footer></div>")
    body.append(LIGHTBOX + SCRIPT)
    open(os.path.join(REPORT, f"v30{LABEL}_review.html"), "w").write(
        "\n".join(body).replace("__LABEL__", LABEL))
    print(f"v3/report/v30{LABEL}_review.html  ({n_cells} cells, "
          f"{len(os.listdir(IMG))} images)")


HEAD = """<title>v3.0 review</title>
<meta name='viewport' content='width=device-width,initial-scale=1'>
<style>
:root{--bg:#0d0d10;--fg:#e8e8ea;--dim:#8a8a94;--line:#26262c;--acc:#7c5cff;
 --good:#3fb950;--mid:#d29922;--bad:#f85149}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
 font:15px/1.6 ui-sans-serif,-apple-system,"Segoe UI",Roboto,sans-serif}
a{color:var(--acc)}
.wrap{max-width:1240px;margin:0 auto;padding:0 26px}
h1{margin:0 0 6px;font-size:24px}
h2{font-size:19px;margin:46px 0 4px;padding-top:14px;border-top:1px solid var(--line)}
h2 .m{font-size:11px;color:var(--dim);font-weight:400;text-transform:uppercase;
 letter-spacing:1px;display:block;margin-bottom:4px}
h2 .sub{font-size:13px;color:var(--dim);font-weight:400}
.lab{font-size:12.5px;color:var(--dim);margin:16px 0 6px}
.strip{display:grid;gap:5px;margin-bottom:8px}
.s4{grid-template-columns:repeat(5,1fr)}
.s3{grid-template-columns:1fr 1.1fr 1.1fr}
.s4c{grid-template-columns:.85fr 1fr 1fr 1fr}
@media(max-width:1100px){.s4c{grid-template-columns:1fr 1fr}}
@media(max-width:900px){.s4,.s3{grid-template-columns:1fr 1fr}}
figure{margin:0}
figure img{width:100%;display:block;background:#fff;border-radius:5px;cursor:zoom-in}
figcaption{font-size:11px;color:var(--dim);text-align:center;padding:4px 2px}
.ph{background:#17171d;border:1px dashed var(--line);border-radius:5px;aspect-ratio:3/4;
 display:flex;align-items:center;justify-content:center;color:var(--dim);font-size:12px;
 text-align:center;line-height:1.4}
.ph span{font-size:10.5px}
.pair{border:1px solid var(--line);border-radius:9px;padding:9px;margin:9px 0;background:#101014}
.ph2{font-size:13px;padding:2px 4px 8px;display:flex;gap:7px;align-items:center;flex-wrap:wrap}
.pill{font-size:10.5px;padding:1px 8px;border-radius:20px;border:1px solid var(--line);color:var(--dim)}
.cell{display:flex;flex-direction:column;gap:4px}
.v{display:grid;grid-template-columns:repeat(3,1fr);gap:4px}
.v button{font:inherit;font-size:11.5px;padding:5px 2px;border-radius:5px;cursor:pointer;
 background:#16161c;color:var(--dim);border:1px solid var(--line)}
.v button:hover{color:var(--fg)}
.v.b button{font-size:10.5px;padding:3px 2px}
button.t.on[data-t=perfect]{background:var(--good);border-color:var(--good);color:#08210d}
button.t.on[data-t=ok]{background:var(--mid);border-color:var(--mid);color:#231a02}
button.t.on[data-t=fail]{background:var(--bad);border-color:var(--bad);color:#2a0707}
button.bd.on{background:var(--acc);border-color:var(--acc);color:#fff}
.note{font:inherit;font-size:11.5px;padding:4px 7px;border-radius:5px;background:#16161c;
 border:1px solid var(--line);color:var(--fg);width:100%}
.cell.done figure img{outline:2px solid var(--line);outline-offset:-2px}
#bar{position:sticky;top:0;z-index:30;background:#121216;border-bottom:1px solid var(--line);
 padding:10px 26px;display:flex;gap:12px;align-items:center;font-size:13px}
#bar button{font:inherit;font-size:12.5px;padding:5px 12px;border-radius:6px;cursor:pointer;
 background:#1c1c24;color:var(--fg);border:1px solid var(--line)}
#bar #go{background:var(--acc);border-color:var(--acc);color:#fff}
#prog{color:var(--dim)}#prog b{color:var(--fg)}
#lb{display:none;position:fixed;inset:0;background:rgba(0,0,0,.95);z-index:99;
 align-items:center;justify-content:center;flex-direction:column;gap:10px;padding:20px}
#lb.on{display:flex}#lb img{max-width:95vw;max-height:90vh;object-fit:contain;background:#fff}
#lbc{color:var(--dim);font-size:13px}
footer{border-top:1px solid var(--line);margin-top:44px;padding:22px 0;color:var(--dim);font-size:12.5px}
code{background:#1b1b22;padding:1px 5px;border-radius:4px;font-size:12px}
.warn{border:1px solid #6b4423;background:#1e1509;border-radius:8px;padding:11px 15px;
 margin:16px 0;font-size:13.5px;color:#e0cba8}
.warn b{color:var(--mid)}
figure.miss .ph{border-color:#4a3a1c}
</style>
<header class='wrap' style='padding-top:30px'><h1>v3.0 — review</h1>
<p style='color:var(--dim);max-width:82ch;font-size:14px;margin:0 0 14px'>36 pairs, two arms,
one seed. <b style='color:var(--fg)'>Mark the tier</b> (perfect / ok / fail) and, where it is
not perfect, <b style='color:var(--fg)'>which band</b> the failure is in: <i>over</i> =
more arrived than the garment (pose, cut line, invented detail); <i>quest</i> = some of the
garment, drifted or partial; <i>failed</i> = nothing arrived, the output is the input.
Grouped by garment reference, because the question is which references fail for everyone.</p>
</header>"""

TOOLBAR = """<div id='bar'><span id='prog'></span>
<span style='flex:1'></span>
<button id='go'>export CSV</button><button id='reset'>reset</button></div>"""

LIGHTBOX = "<div id='lb'><img id='lbi' alt=''><div id='lbc'></div></div>"

SCRIPT = """<script>
const KEY='v30__LABEL___review';
let V=JSON.parse(localStorage.getItem(KEY)||'{}');
const cells=[...document.querySelectorAll('.cell')];
function paint(){
  cells.forEach(c=>{
    const v=V[c.dataset.k]||{};
    c.querySelectorAll('button.t').forEach(b=>b.classList.toggle('on',v.tier===b.dataset.t));
    c.querySelectorAll('button.bd').forEach(b=>b.classList.toggle('on',v.band===b.dataset.b));
    const n=c.querySelector('.note'); if(document.activeElement!==n) n.value=v.note||'';
    c.classList.toggle('done',!!v.tier);
  });
  const done=cells.filter(c=>(V[c.dataset.k]||{}).tier).length;
  const bad=cells.filter(c=>['ok','fail'].includes((V[c.dataset.k]||{}).tier)).length;
  document.getElementById('prog').innerHTML=
    '<b>'+done+'</b> / '+cells.length+' marked &middot; <b>'+bad+'</b> flagged';
}
function set(k,patch){V[k]=Object.assign({},V[k],patch);
  localStorage.setItem(KEY,JSON.stringify(V));paint();}
document.addEventListener('click',e=>{
  const t=e.target.closest('button.t'), b=e.target.closest('button.bd');
  if(t){const k=t.closest('.cell').dataset.k;
    set(k,{tier:(V[k]||{}).tier===t.dataset.t?null:t.dataset.t});return;}
  if(b){const k=b.closest('.cell').dataset.k;
    set(k,{band:(V[k]||{}).band===b.dataset.b?null:b.dataset.b});return;}
  const im=e.target.closest('figure img');
  if(im){document.getElementById('lbi').src=im.getAttribute('src');
    document.getElementById('lbc').textContent=im.getAttribute('alt');
    document.getElementById('lb').classList.add('on');}
});
document.addEventListener('input',e=>{
  if(e.target.classList.contains('note'))
    set(e.target.closest('.cell').dataset.k,{note:e.target.value});
});
document.getElementById('lb').addEventListener('click',()=>
  document.getElementById('lb').classList.remove('on'));
document.addEventListener('keydown',e=>{if(e.key==='Escape')
  document.getElementById('lb').classList.remove('on')});
document.getElementById('go').addEventListener('click',()=>{
  const rows=[['set_id','arm','tier','band','note']];
  cells.forEach(c=>{const [sid,arm]=c.dataset.k.split('|');const v=V[c.dataset.k]||{};
    rows.push([sid,arm,v.tier||'',v.band||'',v.note||'']);});
  const csv=rows.map(r=>r.map(x=>'"'+String(x??'').replace(/"/g,'""')+'"').join(',')).join('\\n');
  const u=URL.createObjectURL(new Blob([csv],{type:'text/csv'}));
  const a=document.createElement('a');a.href=u;a.download='v30__LABEL___review.csv';a.click();
  URL.revokeObjectURL(u);
});
document.getElementById('reset').addEventListener('click',()=>{
  if(confirm('Clear all marks?')){V={};localStorage.removeItem(KEY);paint();}});
paint();
</script>"""

if __name__ == "__main__":
    main()
