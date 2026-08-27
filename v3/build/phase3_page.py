"""Build the v3.1 phase-3 page: the minimum prompt, and cropping the input.

Every column carries its own prompt in full, above the images, because the whole point
of the ladder is that adjacent columns differ by one clause and that difference should be
readable without opening a file.
"""
import html
import json
import os
import sys

from PIL import Image

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RUN = os.path.join(REPO, "v3", "runs", "v3.0b")
REPORT = os.path.join(REPO, "v3", "report")
IMG = os.path.join(REPORT, "img_ph3")
sys.path.insert(0, os.path.join(REPO, "v3", "build"))
import run_p7n as P  # noqa: E402

LADDER = ["p7.3.1", "p7.3.1acc", "p7.3.1exact", "p7.3.2", "p7.3.3",
          "p7.3.4", "p7.3.5", "p7.3.6"]
CROPS = [("raw", "p7.3.6", "the raw photograph"),
         ("CROPB", "p7.3.CROPB", "background removed, head kept"),
         ("CROPH", "p7.3.CROPH", "background and head removed")]


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
    return "img_ph3/" + dst, "img_ph3/" + os.path.basename(full)


def fig(pair, cap, cls=""):
    src, full = pair
    if not src:
        return f"<figure class='miss'><div class='ph'>not run</div><figcaption>{cap}</figcaption></figure>"
    return (f"<figure class='{cls}'><img src='{src}' data-full='{full}' "
            f"alt='{html.escape(cap)}' loading='lazy'><figcaption>{cap}</figcaption></figure>")


def main():
    os.makedirs(IMG, exist_ok=True)
    log = json.load(open(os.path.join(RUN, "_phase3_prompts.json")))
    o = [HEAD, "<div class='wrap'>"]

    # ---------- 1. the prompt ladder ----------
    o.append("<h2>1 &middot; p7.3.n &mdash; how little does the prompt need to say?</h2>")
    o.append(LADDERNOTE)
    ref0 = P.PROBE[0]
    o.append("<div class='prow'>" + "<div class='pcol pad'></div>" + "".join(
        f"<div class='pcol{' ctrl' if t == 'p7.3.6' else ''}"
        f"{' win' if t == 'p7.3.1' else ''}"
        f"{' alt' if t in ('p7.3.1acc', 'p7.3.1exact') else ''}'>"
        f"<div class='pt'><b>{t}</b><span>{log[f'{ref0}|{t}']['words']} words</span></div>"
        f"<pre>{html.escape(log[f'{ref0}|{t}']['prompt'])}</pre></div>"
        for t in LADDER) + "</div>")
    o.append("<p class='note'>The prompts above are shown for "
             f"<code>{html.escape(ref0)}</code>; the colour word and the extent phrase are "
             "read per reference, so those two spans differ row to row. Everything else is "
             "identical down each column.</p>")
    for g in P.PROBE:
        e = log[f"{g}|p7.3.1"]
        o.append(f"<h3>{html.escape(g)}<span class='r'>colour <b>{e['colour']}</b> "
                 f"&middot; framing <b>{e['framing']}</b></span></h3>")
        cells = [fig(web(os.path.join(RUN, "inputs", f"{g}.jpg"), f"{g}__raw.jpg"),
                     "the photograph")]
        for t in LADDER:
            cells.append(fig(web(os.path.join(RUN, "refs", f"{g}__{t}.jpg"),
                                 f"{g}__{t}.jpg"),
                             f"{t}<span class='n'>{log[f'{g}|{t}']['words']} words</span>",
                             "ctrl" if t == "p7.3.6" else
                             ("win" if t == "p7.3.1" else
                              ("alt" if t in ("p7.3.1acc", "p7.3.1exact") else ""))))
        o.append("<div class='strip s7'>" + "".join(cells) + "</div>")

    # ---------- 2. cropping the input ----------
    o.append("<h2>2 &middot; Cropping the input before extraction</h2>")
    o.append(CROPNOTE)
    for g in P.PROBE:
        o.append(f"<h3>{html.escape(g)}<span class='r'>prompt held at "
                 "<b>p7.3</b> &mdash; only the input changes</span></h3>")
        o.append("<div class='lab'>what the model was given</div>")
        o.append("<div class='strip s3'>"
                 + fig(web(os.path.join(RUN, "inputs", f"{g}.jpg"), f"{g}__raw.jpg"),
                       "raw photograph")
                 + fig(web(os.path.join(RUN, "inputs", f"{g}__CROPB.jpg"),
                           f"{g}__inCROPB.jpg"), "CROPB &middot; background removed")
                 + fig(web(os.path.join(RUN, "inputs", f"{g}__CROPH.jpg"),
                           f"{g}__inCROPH.jpg"), "CROPH &middot; background + head removed")
                 + "</div>")
        o.append("<div class='lab'>what came back</div>")
        o.append("<div class='strip s3'>" + "".join(
            fig(web(os.path.join(RUN, "refs", f"{g}__{tag}.jpg"), f"{g}__{tag}.jpg"),
                f"{name}<span class='n'>{desc}</span>",
                "ctrl" if name == "raw" else "")
            for name, tag, desc in CROPS) + "</div>")

    # ---------- 3. the high-hair cohort ----------
    hlog = json.load(open(os.path.join(RUN, "_haircohort_prompts.json")))
    import run_haircohort as HC
    o.append("<h2>3 &middot; The high-hair-damage cohort</h2>")
    o.append(HAIRNOTE)
    for stem, hair, person in HC.COHORT:
        e = hlog[f"{stem}|hc.raw"]
        o.append(f"<h3>{html.escape(stem)}<span class='r'>V2 hair over garment "
                 f"<b>{hair}</b> &middot; colour <b>{e['colour']}</b> from "
                 f"<b>{html.escape(person)}</b></span></h3>")
        o.append("<div class='lab'>what the model was given</div>")
        o.append("<div class='strip s3'>" + "".join(
            fig(web(os.path.join(RUN, "inputs", f"{stem}{sfx}.jpg"),
                    f"hc_{stem}{sfx}_in.jpg"), lbl)
            for sfx, lbl in (("", "raw photograph"),
                             ("__CROPB", "CROPB &middot; background removed"),
                             ("__CROPH", "CROPH &middot; background + head removed")))
                 + "</div>")
        o.append("<div class='lab'>what came back</div>")
        o.append("<div class='strip s3'>" + "".join(
            fig(web(os.path.join(RUN, "refs", f"{stem}__hc.{t}.jpg"), f"hc_{stem}_{t}.jpg"),
                f"{t}<span class='n'>{hlog[f'{stem}|hc.{t}']['framing']}</span>",
                "ctrl" if t == "raw" else "")
            for t in ("raw", "CROPB", "CROPH")) + "</div>")

    o.append(FOOT + "</div>" + LB + SCRIPT)
    open(os.path.join(REPORT, "v31_phase3.html"), "w").write("\n".join(o))
    print(f"v3/report/v31_phase3.html  ({len(P.PROBE)} references, "
          f"{len(LADDER)} prompts + {len(CROPS)} inputs)")


HEAD = """<title>v3.1 phase 3</title>
<meta name='viewport' content='width=device-width,initial-scale=1'>
<style>
:root{--bg:#0d0d10;--fg:#e8e8ea;--dim:#8a8a94;--line:#26262c;--acc:#7c5cff;
 --good:#3fb950;--mid:#d29922}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
 font:15px/1.6 ui-sans-serif,-apple-system,"Segoe UI",Roboto,sans-serif}
.wrap{max-width:1720px;margin:0 auto;padding:30px 26px 0}
h1{margin:0 0 6px;font-size:25px}
h2{font-size:21px;margin:54px 0 8px;padding-top:16px;border-top:1px solid var(--line)}
h3{font-size:13px;margin:26px 0 6px;display:flex;gap:12px;align-items:baseline;flex-wrap:wrap}
h3 .r{font-size:11.5px;color:var(--dim);font-weight:400}
h3 .r b{color:var(--fg)}
.lede{color:var(--dim);max-width:96ch;font-size:14px;margin:0 0 14px}
.lede b{color:var(--fg)}
.q{border-left:3px solid var(--acc);padding:2px 0 2px 14px;margin:14px 0;max-width:98ch;
 font-size:13.5px;color:#c8c8d0}
.q b{color:var(--fg)}
.note{color:var(--dim);font-size:12.5px;max-width:98ch;margin:8px 0 4px}
.lab{font-size:11px;text-transform:uppercase;letter-spacing:1px;color:var(--dim);
 margin:14px 0 5px}
.prow{display:grid;grid-template-columns:repeat(8,1fr);gap:5px;margin:16px 0 4px;
 align-items:stretch}
.pcol{border:1px solid var(--line);border-radius:7px;background:#101014;overflow:hidden;
 display:flex;flex-direction:column}
.pcol.pad{border:0;background:none}
.pcol.ctrl{border-color:#5a4a2a}
.pcol.win{border-color:#2c5c33}
.pcol.alt{border-color:#3a4a6b}
.pcol.alt .pt b{color:#7fa6e8}
figure.alt img{outline:2px solid #3a4a6b;outline-offset:-2px}
.pcol.win .pt b{color:var(--good)}
figure.win img{outline:2px solid #2c5c33;outline-offset:-2px}
figure.win figcaption{color:var(--good);font-weight:700}
.pt{padding:6px 9px;background:#141419;border-bottom:1px solid var(--line);
 display:flex;justify-content:space-between;align-items:baseline;font-size:12px}
.pt b{color:var(--acc)}
.pcol.ctrl .pt b{color:var(--mid)}
.pt span{font-size:10px;color:var(--dim)}
.pcol pre{margin:0;padding:8px 10px;font:10.5px/1.5 ui-monospace,SFMono-Regular,monospace;
 white-space:pre-wrap;color:#b9b9c4;flex:1}
.strip{display:grid;gap:5px;margin-bottom:6px}
.s7{grid-template-columns:repeat(9,1fr)}
.s3{grid-template-columns:repeat(3,1fr);max-width:1100px}
@media(max-width:1400px){.s7{grid-template-columns:repeat(4,1fr)}
 .prow{grid-template-columns:repeat(3,1fr)}.pcol.pad{display:none}}
@media(max-width:900px){.s7,.s3{grid-template-columns:repeat(2,1fr)}
 .prow{grid-template-columns:1fr}}
figure{margin:0}
figure img{width:100%;display:block;background:#fff;border-radius:6px;cursor:zoom-in;
 aspect-ratio:3/4;object-fit:contain}
figure.ctrl img{outline:2px solid #5a4a2a;outline-offset:-2px}
figure.ctrl figcaption{color:var(--mid)}
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
<div class='wrap'><h1>v3.1 phase 3 &mdash; first principles</h1>
<p class='lede'>Phases 1 and 2 built the prompt by <b>accretion</b>: every clause was added
because removing it caused a failure. This phase inverts that &mdash; <b>start from
nothing and add only what earns its place</b> &mdash; and asks a question never asked
before: <b>should the model be given the raw photograph at all?</b> Click any image for
full size.</p></div>
"""

LADDERNOTE = """<div class='q'>Three requirements are irreducible: <b>the mannequin's
colour</b> (a white form under a white garment is the low-amplitude boundary that made
<code>HD_p023</code> return its input), <b>garment preservation</b> (the entire purpose),
and <b>extent</b> (a whole-body instruction against a waist-up photograph is satisfied by
inventing legs). Everything else in <code>p7.3</code> is a candidate for deletion until it
earns its place.</div>
<div class='q'><b>The ladder is negation-free except for the control.</b>
<code>p7.3</code> contains four negations and names four nouns it does not want rendered
&mdash; <i>bag, face, skin, hair</i>. Every first-party source says to write positives
instead, and Qwen's own prompt rewriter forbids negation words outright. <code>.3</code>
replaces <i>"no face, no skin, no hair"</i> with <i>"smooth and featureless"</i>;
<code>.5</code> is the whole of <code>p7.3</code> with every negation turned positive;
<code>.6</code> is the untouched control.</div>
<div class='q'><b>Reviewer verdict 2026-08-27: the fewest words wins.</b>
<code>p7.3.1</code> is adopted &mdash; roughly 20 words carrying only the three
irreducibles. Two modifier variants sit beside it in blue: <code>p7.3.1acc</code> adds
<i>&ldquo;entire outfit including accessories&rdquo;</i> and was judged <b>worse</b>;
<code>p7.3.1exact</code> replaces that with the single word <i>&ldquo;exact&rdquo;</i>
&mdash; one word instead of four, and a fidelity instruction rather than an inventory
one.</div>
<div class='q'><b>What to look for:</b> the ablation already showed 27 words matching 94 on
five of eight references, and the long version <i>losing garment colour</i> on a sixth.
The literature names that axis &mdash; compound instructions cost identity preservation
far more than instruction-following. <b>Every clause is paid for in fidelity, which is the
thing we are trying to keep.</b> So the question per column is not &ldquo;did it
obey&rdquo; but <b>&ldquo;is the garment still the garment&rdquo;</b>.</div>"""

CROPNOTE = """<div class='q'>Until now the model has been handed a <b>raw photograph</b>
&mdash; a person in a room, background included, in one case with 83% of the frame empty.
The mask stack V2 built has been sitting unused in this path, while the whole of v3.0 is
about the fact that <b>the reference given to a call determines what comes back</b>.</div>
<div class='q'>Two things a crop should buy: <b>less to attend to</b>, since a background
is content competing with the garment for attention; and <b>more garment per token</b>,
since a reference is tokenised at 16&times;16 pixels per token and subject fill runs as
low as 17%.</div>
<div class='q'><b>The two crops differ in one thing: the head.</b> <code>CROPH</code> is
the interesting one and it is not free &mdash; cutting the head reintroduces exactly the
cut boundary that v3.0 showed klein copies into its output. The hypothesis is that
<b>a regenerative consumer may not copy a boundary the way a subtractive one does</b>.
The mask stack and the regeneration arm have never been used together, so this has never
been tested. The prompt is held fixed at <code>p7.3</code>: the input is the only
variable.</div>"""

HAIRNOTE = """<div class='q'>These six are the references V2 measured as <b>worst for hair
falling over the garment</b> &mdash; the cohort BC_klein's entire bald pass exists to
handle. <b>None has ever been through the regeneration path</b>, because run B's fold put
them on the person side or left them out. Prompt held at <code>p7.3.1</code>, the adopted
minimum; the input is the only variable.</div>
<div class='q'><b><code>CROPH</code> is the direct question.</b> On a <i>subtractive</i>
consumer, cutting the head is what produces the jagged boundary v3.0 showed klein copies
into its output &mdash; it is the origin of the whole problem. On a <i>regenerative</i>
consumer it may simply remove the hair without that cost, because the model is not bound
to reproduce what it was shown. If <code>CROPH</code> is clean here, <b>the CPU mask stack
and the regeneration arm solve each other's problem</b>, and they have never been run
together.</div>"""

FOOT = """<footer>Prompts as sent: <code>v3/runs/v3.0b/_phase3_prompts.json</code> &middot;
crops: <code>v3/runs/v3.0b/inputs/{ref}__CROP{B,H}.jpg</code>, built by
<code>v3/build/run_phase3.py</code> from the unmodified V2 mask stack &middot; rebuild:
<code>python3 v3/build/phase3_page.py</code>. Everything here is a <b>reference</b>
&mdash; nothing on this page has been through a klein edit.</footer>"""

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
