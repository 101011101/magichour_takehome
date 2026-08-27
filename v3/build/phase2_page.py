"""Build the v3.1 phase-2 page: colour audit, p7.3 combination, accessory toggle.

Three questions that links 1-3 did not ask, on one page because they are one phase:
is the reader right, do the two accepted components compose, and can accessories be
turned on and off deliberately.
"""
import html
import json
import os
import sys

from PIL import Image

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RUN = os.path.join(REPO, "v3", "runs", "v3.0b")
REPORT = os.path.join(REPO, "v3", "report")
IMG = os.path.join(REPORT, "img_ph2")
sys.path.insert(0, os.path.join(REPO, "v3", "build"))
import run_p7n as P          # noqa: E402
import run_phase2 as R2      # noqa: E402
import skin_tone as S        # noqa: E402


def web(src, dst, width=430):
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
    return "img_ph2/" + dst, "img_ph2/" + os.path.basename(full)


def fig(pair, cap, cls=""):
    src, full = pair
    if not src:
        return f"<figure class='miss'><div class='ph'>not run</div><figcaption>{cap}</figcaption></figure>"
    return (f"<figure class='{cls}'><img src='{src}' data-full='{full}' "
            f"alt='{html.escape(cap)}' loading='lazy'><figcaption>{cap}</figcaption></figure>")


def main():
    os.makedirs(IMG, exist_ok=True)
    audit = json.load(open(os.path.join(REPO, "v3", "runs", "colour_audit.json")))
    log = json.load(open(os.path.join(RUN, "_phase2_prompts.json")))
    o = [HEAD, "<div class='wrap'>"]

    # ---- 1. colour audit ------------------------------------------------
    ok = [d for d in audit if d["tone"]]
    de = sorted(d["tone"]["deltaE"] for d in ok)
    o.append("<h2>1 &middot; Is the colour reader extracting correctly?</h2>")
    o.append(AUDITNOTE)
    o.append("<div class='swatches'><b>the ladder</b>"
             + "".join(f"<span><i style='background:{h}'></i>{n.replace(' skin','')}</span>"
                       for n, _, h in S.TONES) + "</div>")
    o.append(f"<div class='stat'><span><b>{len(ok)}</b>/{len(audit)} read</span>"
             f"<span>&Delta;E median <b>{de[len(de)//2]:.1f}</b></span>"
             f"<span>max <b>{de[-1]:.1f}</b></span>"
             f"<span>over 20: <b>{sum(1 for x in de if x > 20)}</b></span></div>")
    cards = []
    for d in sorted(audit, key=lambda x: -(x["tone"]["deltaE"] if x["tone"] else 999)):
        t = d["tone"]
        thumb = web(os.path.join(REPO, d["path"]), f"aud_{d['id']}.jpg", 240)
        if not t:
            cards.append(f"<div class='ac bad'><div class='an'>{html.escape(d['id'])}</div>"
                         f"<img src='{thumb[0]}' loading='lazy' alt=''>"
                         "<div class='no'>no skin found</div></div>")
            continue
        hot = t["deltaE"] > 20
        cards.append(
            f"<div class='ac{' warn' if hot else ''}'>"
            f"<div class='an'>{html.escape(d['id'])}</div>"
            f"<img src='{thumb[0]}' loading='lazy' alt='{html.escape(d['id'])}'>"
            "<div class='pair'>"
            f"<span class='sw' style='background:{t['measured_hex']}' "
            f"title='measured'></span>"
            f"<span class='sw' style='background:{t['assigned_hex']}' "
            f"title='assigned'></span></div>"
            f"<div class='lbl'>{t['name'].replace(' skin','')}</div>"
            f"<div class='num'>{t['measured_hex']} &rarr; {t['assigned_hex']}<br>"
            f"&Delta;E {t['deltaE']} &middot; ITA {t['ITA']:.0f}&deg; &middot; "
            f"from {t['from']}</div></div>")
    o.append("<div class='agrid'>" + "".join(cards) + "</div>")

    # ---- 2. p7.3 --------------------------------------------------------
    o.append("<h2>2 &middot; p7.3 &mdash; do the two components compose?</h2>")
    o.append(P73NOTE)
    for g in P.PROBE:
        e = log.get(f"{g}|p7.3", {})
        o.append(f"<h3>{html.escape(g)}<span class='r'>colour "
                 f"<b>{e.get('colour','?')}</b> &middot; framing "
                 f"<b>{e.get('framing','?')}</b></span></h3>")
        o.append("<div class='strip s5'>"
                 + fig(web(os.path.join(RUN, "inputs", f"{g}.jpg"), f"{g}__raw.jpg"),
                       "the photograph")
                 + fig(web(os.path.join(RUN, "refs", f"{g}__QMB.jpg"), f"{g}__QMB.jpg"),
                       "p7<span class='n'>neither fix</span>")
                 + fig(web(os.path.join(RUN, "refs", f"{g}__p7.1.3.jpg"), f"{g}__p713.jpg"),
                       "p7.1.3<span class='n'>framing only</span>")
                 + fig(web(os.path.join(RUN, "refs", f"{g}__p7.2b+.matched.jpg"),
                           f"{g}__p72bpm.jpg"), "p7.2b+<span class='n'>colour only</span>")
                 + fig(web(os.path.join(RUN, "refs", f"{g}__p7.3.jpg"), f"{g}__p73.jpg"),
                       "p7.3<span class='n'>both</span>", "best")
                 + "</div>")

    # ---- 3. accessories -------------------------------------------------
    o.append("<h2>3 &middot; p7.1.3.n &mdash; can accessories be turned on and off?</h2>")
    o.append(ACCNOTE)
    o.append(CATNOTE)
    o.append("<div class='clauses'>" + "".join(
        f"<div class='cl{' drop' if label.startswith('drop') else ''}"
        f"{' cat' if k in 'efg' else ''}'><b>{k}</b>"
        f"<span>{label}</span><pre>{html.escape(extra.strip())}</pre></div>"
        for k, (label, extra) in R2.ACCESSORY.items()) + "</div>")
    for g in P.PROBE:
        o.append(f"<h3>{html.escape(g)}</h3>")
        cells = [fig(web(os.path.join(RUN, "inputs", f"{g}.jpg"), f"{g}__raw.jpg"),
                     "the photograph"),
                 fig(web(os.path.join(RUN, "refs", f"{g}__p7.1.3.jpg"), f"{g}__p713.jpg"),
                     "p7.1.3<span class='n'>no accessory clause</span>")]
        for k, (label, _) in R2.ACCESSORY.items():
            cells.append(fig(web(os.path.join(RUN, "refs", f"{g}__p7.1.3.{k}.jpg"),
                                 f"{g}__p713{k}.jpg"),
                             f"{k} &middot; {label}",
                             "drop" if label.startswith("drop") else
                             ("cat" if k in "ef" else "")))
        o.append("<div class='strip s9'>" + "".join(cells) + "</div>")

    o.append(FOOT + "</div>" + LB + SCRIPT)
    open(os.path.join(REPORT, "v31_phase2.html"), "w").write("\n".join(o))
    print(f"v3/report/v31_phase2.html  ({len(audit)} audited, {len(P.PROBE)} references)")


HEAD = """<title>v3.1 phase 2</title>
<meta name='viewport' content='width=device-width,initial-scale=1'>
<style>
:root{--bg:#0d0d10;--fg:#e8e8ea;--dim:#8a8a94;--line:#26262c;--acc:#7c5cff;
 --good:#3fb950;--mid:#d29922;--bad:#f85149}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
 font:15px/1.6 ui-sans-serif,-apple-system,"Segoe UI",Roboto,sans-serif}
.wrap{max-width:1620px;margin:0 auto;padding:30px 26px 0}
h1{margin:0 0 6px;font-size:25px}
h2{font-size:21px;margin:54px 0 8px;padding-top:16px;border-top:1px solid var(--line)}
h3{font-size:13px;margin:24px 0 6px;display:flex;gap:12px;align-items:baseline;flex-wrap:wrap}
h3 .r{font-size:11.5px;color:var(--dim);font-weight:400}
h3 .r b{color:var(--fg)}
.lede{color:var(--dim);max-width:94ch;font-size:14px;margin:0 0 14px}
.lede b{color:var(--fg)}
.q{border-left:3px solid var(--acc);padding:2px 0 2px 14px;margin:14px 0;max-width:96ch;
 font-size:13.5px;color:#c8c8d0}
.q b{color:var(--fg)}
pre{margin:0;font:12px/1.6 ui-monospace,SFMono-Regular,monospace;white-space:pre-wrap;
 color:#b9b9c4}
.swatches{display:flex;gap:9px;align-items:center;flex-wrap:wrap;margin:12px 0;
 font-size:11.5px;color:var(--dim)}
.swatches b{color:var(--fg);font-size:11px;text-transform:uppercase;letter-spacing:1px}
.swatches span{display:inline-flex;gap:4px;align-items:center}
.swatches i{width:14px;height:14px;border-radius:4px;display:inline-block;border:1px solid #333}
.stat{display:flex;gap:20px;font-size:12.5px;color:var(--dim);margin:10px 0 4px}
.stat b{color:var(--fg)}
.agrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:8px;
 margin-top:14px}
.ac{border:1px solid var(--line);border-radius:8px;background:#101014;overflow:hidden;
 padding-bottom:7px}
.ac.warn{border-color:#6b4423}.ac.bad{border-color:var(--bad)}
.ac img{width:100%;aspect-ratio:1/1;object-fit:cover;object-position:top center;display:block}
.an{font-size:9.5px;padding:5px 7px 4px;color:var(--fg);word-break:break-all;
 background:#141419;border-bottom:1px solid var(--line)}
.ac .pair{display:flex;gap:0;margin:6px 7px 4px}
.sw{flex:1;height:26px;border:1px solid #333}
.sw:first-child{border-radius:5px 0 0 5px}.sw:last-child{border-radius:0 5px 5px 0;border-left:0}
.lbl{font-size:11px;text-align:center;color:var(--fg);font-weight:600}
.num{font-size:9px;color:var(--dim);text-align:center;line-height:1.4;padding:2px 4px 0}
.no{color:var(--bad);font-size:11px;text-align:center;padding:8px}
.clauses{display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:9px;
 margin:14px 0}
.cl{border:1px solid var(--line);border-radius:8px;background:#101014;padding:9px 12px}
.cl.drop{border-color:#5a3a3a}
.cl b{font-size:14px;color:var(--acc);margin-right:8px}
.cl.drop b{color:var(--bad)}
.cl span{font-size:11.5px;color:var(--dim)}
.cl pre{margin-top:6px}
.strip{display:grid;gap:5px;margin-bottom:6px}
.s5{grid-template-columns:repeat(5,1fr)}
.s6{grid-template-columns:repeat(6,1fr)}
.s9{grid-template-columns:repeat(9,1fr)}
.cl.cat{border-color:#3a4a6b}
.cl.cat b{color:#7fa6e8}
figure.cat img{outline:2px solid #3a4a6b;outline-offset:-2px}
@media(max-width:1400px){.s9{grid-template-columns:repeat(5,1fr)}}
@media(max-width:1100px){.s5,.s6,.s9{grid-template-columns:repeat(3,1fr)}}
@media(max-width:700px){.s5,.s6,.s9{grid-template-columns:repeat(2,1fr)}}
figure{margin:0}
figure img{width:100%;display:block;background:#fff;border-radius:6px;cursor:zoom-in;
 aspect-ratio:3/4;object-fit:contain}
figure.best img{outline:2px solid #2c5c33;outline-offset:-2px}
figure.best figcaption{color:var(--good);font-weight:700}
figure.drop img{outline:2px solid #5a3a3a;outline-offset:-2px}
figcaption{font-size:11px;color:var(--dim);text-align:center;padding:5px 2px;line-height:1.4}
figcaption .n{display:block;font-size:9.5px;opacity:.8}
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
<div class='wrap'><h1>v3.1 phase 2 &mdash; audit, combine, toggle</h1>
<p class='lede'>Links 1&ndash;3 ran one variable at a time and produced two accepted
components. This phase <b>verifies the reader that feeds the prompt</b>, <b>combines</b>
the two components, and <b>stresses the framing component</b> on the one thing it has no
words for. Click any image for full size.</p></div>
"""

AUDITNOTE = """<div class='q'>The enum structure is adopted, which makes <b>the ladder the
interface</b>: everything downstream sees a named phrase and nothing else. That makes the
reader the one component whose errors are invisible later &mdash; a wrong phrase produces
a well-formed prompt and a plausible mannequin of the wrong colour. So it is audited over
<b>every image, not a sample</b>.</div>
<div class='q'>Each card: the photograph, then <b>two swatches side by side &mdash; left is
the measured median, right is the ladder step it was assigned</b> &mdash; then the label,
the two hex values, &Delta;E between them, the ITA, and whether the median came from the
face or fell back to body skin. Sorted worst &Delta;E first. Amber above &Delta;E 20.</div>
<div class='q'><b>Three different ways this can be wrong, and they have different fixes.</b>
A measured hex that is not skin at all means the mask grabbed background, hair or garment.
A large &Delta;E with a sensible hex means the ladder has no step near this person. A
drift all in one direction means the thresholds are misplaced. The audit separates
them.</div>"""

P73NOTE = """<div class='q'><code>p7.1.3</code> and <code>p7.2b+</code> were each run with
the other variable held empty, on purpose. <b>Two fixes that work alone are not thereby a
fix that works together</b> &mdash; the framing clause and the colour phrase sit in
different slots of the same sentence and could interact. Four columns on identical
references: neither fix, framing only, colour only, both.</div>
<div class='q'>The reader's outputs for each row are printed above it, so a bad
combination can be traced to a bad read rather than to the combination itself.</div>"""

ACCNOTE = """<div class='q'><code>p7</code> says one thing about accessories and it points
one way: <i>&ldquo;the mannequin wears only what the person is wearing and nothing else:
if they are not carrying a bag, there is no bag.&rdquo;</i> That <b>forbids addition</b>
and says nothing about <b>retention</b> &mdash; so a bag that does exist has no
instruction protecting it, and bags, belts and jewellery are dropped in most references.
</div>
<div class='q'>The goal is not &ldquo;always keep&rdquo;. It is <b>a reliable toggle</b>:
wording that keeps accessories when wanted and drops them when not, so the behaviour is
chosen rather than accidental. <b>Variant <code>b</code> is a deliberate risk</b> &mdash;
it enumerates, which is exactly what made <code>p4</code>/<code>p5</code> invent hats and
bags. It is here to find out whether the &ldquo;only what the person is wearing&rdquo;
guard is now strong enough to make enumeration safe. <b>A negative result there is worth
as much as a positive one.</b></div>
<div class='q'><b>Judge against the photograph:</b> was each accessory in the photograph
retained, and is anything present that was not. <code>b</code> and <code>c</code> are the
informative pair &mdash; if <code>b</code> invents and <code>c</code> reliably strips,
enumeration is unsafe in the positive direction and safe in the negative one, which is a
usable rule rather than a preference.</div>"""

CATNOTE = """<div class='q'><b>Three kinds of clause, not two.</b>
<code>a</code> and <code>d</code> describe a <b>rule</b> and name nothing.
<code>b</code> and <code>c</code> <b>enumerate instances</b> &mdash; bag, hat, belt
&mdash; and each noun is individually producible, which is what makes a list a licence in
the positive direction. <b><code>e</code>, <code>f</code> and <code>g</code> name the
class instead</b>: &ldquo;accessories&rdquo; has no canonical instantiation, so there is
no default object the model can generate to satisfy the word. If the licence effect is
about producible nouns, a category term should keep without inventing &mdash; and
<code>f</code>, which is the category term <i>grounded in the photograph</i>, should be
the safest keep-instruction of all seven.</div>"""

FOOT = """<footer>Audit: <code>v3/runs/colour_audit.json</code> &middot; prompts as sent:
<code>v3/runs/v3.0b/_phase2_prompts.json</code> &middot; reader:
<code>v3/build/skin_tone.py</code> &middot; runner:
<code>v3/build/run_phase2.py</code> &middot; rebuild:
<code>python3 v3/build/phase2_page.py</code>. Everything here is a <b>reference</b>, not a
try-on &mdash; nothing on this page has been through a klein edit.</footer>"""

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
