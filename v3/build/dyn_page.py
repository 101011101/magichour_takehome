"""Dynamic prompting page: one framing read drives both the extent and the pose clause.

Grouped by framing category, because the category IS the schema - what should be
readable at a glance is that everything in a group got the same clause, and that the
clause never names a body part the crop excludes.
"""
import collections
import html
import json
import os
import sys

from PIL import Image

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RUN = os.path.join(REPO, "v3", "runs", "v3.0b")
REPORT = os.path.join(REPO, "v3", "report")
IMG = os.path.join(REPORT, "img_dyn")
sys.path.insert(0, os.path.join(REPO, "v3", "build"))
import skin_tone as S  # noqa: E402

ORDER = ["chest_up", "waist_up", "knee_up", "full_body"]


def web(src, dst, width=420):
    if not os.path.exists(src):
        return None, None
    out, full = os.path.join(IMG, dst), os.path.join(IMG, dst.replace(".jpg", "@f.jpg"))
    im = None
    if not os.path.exists(out):
        im = Image.open(src).convert("RGB")
        t = im.resize((width, int(im.height * width / im.width)), Image.LANCZOS) \
            if im.width > width else im
        t.save(out, quality=90, optimize=True)
    if not os.path.exists(full):
        im = im or Image.open(src).convert("RGB")
        im.save(full, quality=94, optimize=True)
    return "img_dyn/" + dst, "img_dyn/" + os.path.basename(full)


def fig(pair, cap, cls=""):
    src, full = pair
    if not src:
        return f"<figure class='miss'><div class='ph'>not run</div><figcaption>{cap}</figcaption></figure>"
    return (f"<figure class='{cls}'><img src='{src}' data-full='{full}' "
            f"alt='{html.escape(cap.replace('&mdash;','-'))}' loading='lazy'>"
            f"<figcaption>{cap}</figcaption></figure>")


def main():
    os.makedirs(IMG, exist_ok=True)
    log = json.load(open(os.path.join(RUN, "_dyn_prompts.json")))
    o = [HEAD, "<div class='wrap'>", NOTE]

    o.append("<h2>The table</h2>")
    o.append("<p class='note'>One read, one lookup, both clauses. The pose half never "
             "names a part the extent half has cut off.</p>")
    rows = []
    for k in ORDER + ["unknown"]:
        c = S.FRAME_CLAUSE[k].strip()
        ext, _, pose = c.partition(". ")
        n = sum(1 for v in log.values() if v["framing"] == k)
        rows.append(f"<tr><td class='l'><b>{k}</b><span>{n} reference"
                    f"{'' if n == 1 else 's'}</span></td>"
                    f"<td class='l'>{html.escape(ext)}.</td>"
                    f"<td class='l pose'>{html.escape(pose)}</td></tr>")
    o.append("<table><tr><th>framing read</th><th>extent clause</th>"
             "<th>pose clause</th></tr>" + "".join(rows) + "</table>")

    by = collections.defaultdict(list)
    for g, v in log.items():
        by[v["framing"]].append(g)
    for cat in ORDER:
        gs = by.get(cat, [])
        if not gs:
            continue
        c = S.FRAME_CLAUSE[cat].strip()
        o.append(f"<h2>{cat}<span class='r'>{len(gs)} reference"
                 f"{'' if len(gs) == 1 else 's'}</span></h2>")
        o.append(f"<pre>{html.escape(c)}</pre>")
        o.append("<div class='lab'>the crop the reader saw &rarr; the mannequin it "
                 "produced &rarr; what klein made of it</div>")
        for g in gs:
            v = log[g]
            o.append(f"<h3>{html.escape(g)}<span class='r'>colour "
                     f"<b>{v['colour']}</b> &middot; person "
                     f"<b>{html.escape(v['person'])}</b></span></h3>")
            o.append("<div class='strip s4'>"
                     + fig(web(os.path.join(RUN, "inputs", f"{g}__A4.jpg"), f"{g}__A4.jpg"),
                           "A4 crop &mdash; what the reader saw")
                     + fig(web(os.path.join(RUN, "refs", f"{g}__MQ.jpg"), f"{g}__MQ.jpg"),
                           "before &mdash; extent clause only")
                     + fig(web(os.path.join(RUN, "refs", f"{g}__dyn.jpg"), f"{g}__dyn.jpg"),
                           "after &mdash; extent + pose from one table", "win")
                     + fig(web(os.path.join(RUN, "gen", f"{v['set_id']}__dyn.jpg"),
                               f"{v['set_id']}__dyn.jpg"), "klein output", "win")
                     + "</div>")
    o.append(FOOT + "</div>" + LB + SCRIPT)
    open(os.path.join(REPORT, "v31_dynamic.html"), "w").write("\n".join(o))
    print(f"v3/report/v31_dynamic.html  ({len(log)} references, {len(by)} categories)")


HEAD = """<title>Dynamic prompting</title>
<meta name='viewport' content='width=device-width,initial-scale=1'>
<style>
:root{--bg:#0d0d10;--fg:#e8e8ea;--dim:#8a8a94;--line:#26262c;--acc:#7c5cff;--good:#3fb950}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
 font:15px/1.6 ui-sans-serif,-apple-system,"Segoe UI",Roboto,sans-serif}
.wrap{max-width:1500px;margin:0 auto;padding:30px 26px 0}
h1{margin:0 0 6px;font-size:25px}
h2{font-size:19px;margin:52px 0 8px;padding-top:16px;border-top:1px solid var(--line);
 display:flex;gap:12px;align-items:baseline}
h2 .r{font-size:12px;color:var(--dim);font-weight:400}
h3{font-size:13px;margin:24px 0 6px;display:flex;gap:12px;align-items:baseline;flex-wrap:wrap}
h3 .r{font-size:11.5px;color:var(--dim);font-weight:400}
h3 .r b{color:var(--fg)}
.lede{color:var(--dim);max-width:96ch;font-size:14px;margin:0 0 14px}
.lede b{color:var(--fg)}
.note{color:var(--dim);font-size:13px;max-width:96ch;margin:6px 0}
.q{border-left:3px solid var(--acc);padding:2px 0 2px 14px;margin:14px 0;max-width:98ch;
 font-size:13.5px;color:#c8c8d0}
.q b{color:var(--fg)}
.lab{font-size:11px;text-transform:uppercase;letter-spacing:1px;color:var(--dim);
 margin:14px 0 5px}
pre{background:#0b0b0e;border:1px solid var(--line);border-radius:8px;padding:11px 15px;
 font:12.5px/1.7 ui-monospace,SFMono-Regular,monospace;white-space:pre-wrap;color:#b9b9c4;
 max-width:1100px;margin:8px 0 4px}
table{border-collapse:collapse;font-size:12.5px;margin:14px 0;width:100%;max-width:1400px}
th,td{padding:8px 13px;border-bottom:1px solid #1d1d23;text-align:left;vertical-align:top}
th{color:var(--dim);font-weight:600}
td.l b{display:block}
td.l span{font-size:11px;color:var(--dim)}
td.pose{color:var(--good)}
.strip{display:grid;gap:5px;margin-bottom:6px}
.s4{grid-template-columns:repeat(4,1fr)}
@media(max-width:900px){.s4{grid-template-columns:repeat(2,1fr)}}
figure{margin:0}
figure img{width:100%;display:block;background:#fff;border-radius:6px;cursor:zoom-in;
 aspect-ratio:3/4;object-fit:contain}
figure.win img{outline:2px solid #2c5c33;outline-offset:-2px}
figure.win figcaption{color:var(--good);font-weight:600}
figcaption{font-size:11px;color:var(--dim);text-align:center;padding:5px 3px;line-height:1.4}
.ph{background:#17171d;border:1px dashed var(--line);border-radius:6px;aspect-ratio:3/4;
 display:flex;align-items:center;justify-content:center;color:var(--dim);font-size:11px}
#lb{display:none;position:fixed;inset:0;background:rgba(0,0,0,.96);z-index:99;
 align-items:center;justify-content:center;flex-direction:column;gap:10px;padding:16px}
#lb.on{display:flex}#lb img{max-width:96vw;max-height:92vh;object-fit:contain;background:#fff}
#lbc{color:var(--dim);font-size:13px}
footer{border-top:1px solid var(--line);margin-top:44px;padding:22px 0 30px;
 color:var(--dim);font-size:12.5px}
code{background:#1b1b22;padding:1px 5px;border-radius:4px;font-size:12px}
</style>
<div class='wrap'><h1>Dynamic prompting</h1>
<p class='lede'>The extent clause and the pose clause were written separately and
contradicted each other: a fixed pose sentence saying <i>&ldquo;feet together&rdquo;</i>
told the model feet were in frame while the extent clause told it to cut above them
&mdash; and <b>the pose clause won</b>, reopening a waist-up crop to full length.
<b>Both clauses now come from one table, keyed on one framing read</b>, so they cannot
disagree by construction. Click any image for full size.</p></div>
"""

NOTE = """<div class='q'><b>How the framing is decided</b>, since it drives everything
here: MediaPipe Pose Landmarker runs on the crop (36&nbsp;ms, CPU) and reports which
joints are <b>confident and inside the frame</b> &mdash; shoulder, hip, knee, ankle. Ankle
present means <code>full_body</code>; knee but no ankle means <code>knee_up</code>; hip but
no knee means <code>waist_up</code>; shoulders only means <code>chest_up</code>. It reads a
coordinate the detector already returns, which is a far weaker question than the eight
head-detection heuristics V2 burned through trying to <i>find</i> a boundary.</div>
<div class='q'><b>The rule that makes the two clauses consistent:</b> never name a body
part the crop excludes. Below the hip there are no feet to put together, so neutrality has
to be expressed with something still in frame &mdash; <i>square to the camera, shoulders
level</i>. That is the whole schema, and it is why the pose column changes with the
category rather than being a constant.</div>"""

FOOT = """<footer>Table of record: <code>FRAME_CLAUSE</code> in
<code>v3/build/skin_tone.py</code> &middot; prompts as sent:
<code>v3/runs/v3.0b/_dyn_prompts.json</code> &middot; runner:
<code>v3/build/run_dyn.py</code> &middot; rebuild:
<code>python3 v3/build/dyn_page.py</code>. Eight references chosen to cover every category
the reader produces, so the schema is exercised rather than sampled.</footer>"""

LB = "<div id='lb'><img id='lbi' alt=''><div id='lbc'></div></div>"
SCRIPT = """<script>
document.addEventListener('click',e=>{const im=e.target.closest('figure img');
  if(!im)return;document.getElementById('lbi').src=im.dataset.full||im.getAttribute('src');
  document.getElementById('lbc').textContent=im.getAttribute('alt');
  document.getElementById('lb').classList.add('on');});
document.getElementById('lb').addEventListener('click',()=>
  document.getElementById('lb').classList.remove('on'));
document.addEventListener('keydown',e=>{if(e.key==='Escape')
  document.getElementById('lb').classList.remove('on')});
</script>"""

if __name__ == "__main__":
    main()
