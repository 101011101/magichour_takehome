"""Build the p7.1 / p7.2 probe page.

Two experiments on one page because they share a cohort and a baseline:

  p7.1  does the mannequin stop where the photograph stops?
  p7.2  does a colour word change whether the garment has an edge to be found at?

Both are built by concatenation - PREFIX + word + SUFFIX - so a difference between
columns is one word or one sentence and nothing else.
"""
import html
import json
import os
import sys

from PIL import Image

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RUN = os.path.join(REPO, "v3", "runs", "v3.0b")
REPORT = os.path.join(REPO, "v3", "report")
IMG = os.path.join(REPORT, "img_p7n")
sys.path.insert(0, os.path.join(REPO, "v3", "build"))
import run_p7n as P            # noqa: E402
import run_p72bplus as PP     # noqa: E402
import skin_tone as ST        # noqa: E402

FRAME_ARMS = [("QMB", "p7", "baseline"),
              ("p7.1.1", "p7.1.1", "self-limiting sentence"),
              ("p7.1.2", "p7.1.2", "mirror the crop"),
              ("p7.1.3", "p7.1.3", "CPU pose reader")]
COLOUR_ARMS = [("p7.2.white", "white", "fixed"), ("p7.2.grey", "grey", "fixed"),
               ("p7.2.matched", "matched", "CPU skin reader, paired person"),
               ("p7.2.contrast", "contrast", "furthest word from the garment")]
SKIN_ARMS = [("p7.2b.white", "white skin", ""), ("p7.2b.beige", "beige skin", ""),
             ("p7.2b.tan", "tan skin", ""), ("p7.2b.black", "black skin", ""),
             ("p7.2b.grey", "grey", "material, not a complexion")]


def web(src, dst, width=430):
    if not os.path.exists(src):
        return None, None
    out, full = os.path.join(IMG, dst), os.path.join(IMG, dst.replace(".jpg", "@full.jpg"))
    im = None
    if not os.path.exists(out):
        im = Image.open(src).convert("RGB")
        t = im.resize((width, int(im.height * width / im.width)), Image.LANCZOS) \
            if im.width > width else im
        t.save(out, quality=90, optimize=True)
    if not os.path.exists(full):
        im = im or Image.open(src).convert("RGB")
        im.save(full, quality=94, optimize=True)
    return "img_p7n/" + dst, "img_p7n/" + os.path.basename(full)


def fig(pair, cap, cls=""):
    src, full = pair
    if not src:
        return ("<figure class='miss'><div class='ph'>not run</div>"
                f"<figcaption>{cap}</figcaption></figure>")
    return (f"<figure class='{cls}'><img src='{src}' data-full='{full}' "
            f"alt='{html.escape(cap)}' loading='lazy'><figcaption>{cap}</figcaption></figure>")


def main():
    os.makedirs(IMG, exist_ok=True)
    log = json.load(open(os.path.join(RUN, "_p7n_prompts.json")))
    o = [HEAD, "<div class='wrap'>", STRUCT]

    o.append("<h2>p7.1 &mdash; does the mannequin stop where the photograph stops?</h2>")
    o.append(P71NOTE)
    for g in P.PROBE:
        fr = log[f"{g}|p7.1.3"]["framing_read"]
        o.append(f"<h3>{html.escape(g)}<span class='r'>pose reader: "
                 f"<b>{fr['framing']}</b> &middot; joints in frame: "
                 f"{', '.join(fr['present']) or 'none'}</span></h3>")
        cells = [fig(web(os.path.join(RUN, "inputs", f"{g}.jpg"), f"{g}__raw.jpg"),
                     "the photograph")]
        for tag, label, sub in FRAME_ARMS:
            cells.append(fig(web(os.path.join(RUN, "refs", f"{g}__{tag}.jpg"),
                                 f"{g}__{tag}.jpg"),
                             f"{label}<span class='n'>{sub}</span>",
                             "base" if tag == "QMB" else ""))
        o.append("<div class='strip s5'>" + "".join(cells) + "</div>")

    o.append("<h2>p7.2 &mdash; does a colour word give the garment an edge?</h2>")
    o.append(P72NOTE)
    for g in P.PROBE:
        e = log[f"{g}|p7.2.matched"]
        o.append(f"<h3>{html.escape(g)}<span class='r'>paired person "
                 f"<b>{html.escape(e['person'])}</b> reads <b>{e['matched_from']}</b> "
                 f"&middot; contrast pick <b>{e['contrast_pick']}</b></span></h3>")
        cells = [fig(web(os.path.join(RUN, "inputs", f"{g}.jpg"), f"{g}__raw.jpg"),
                     "the photograph")]
        for tag, label, sub in COLOUR_ARMS:
            word = log[f"{g}|{tag}"]["colour"]
            cells.append(fig(web(os.path.join(RUN, "refs", f"{g}__{tag}.jpg"),
                                 f"{g}__{tag}.jpg"),
                             f"{label} &rarr; &ldquo;{word}&rdquo;<span class='n'>{sub}</span>"))
        o.append("<div class='strip s5'>" + "".join(cells) + "</div>")

    o.append("<h2>p7.2b &mdash; does naming the colour as <i>skin</i> keep it on the "
             "mannequin?</h2>")
    o.append(P72BNOTE)
    for g in P.PROBE:
        o.append(f"<h3>{html.escape(g)}</h3>")
        cells = [fig(web(os.path.join(RUN, "inputs", f"{g}.jpg"), f"{g}__raw.jpg"),
                     "the photograph")]
        for tag, label, sub in SKIN_ARMS:
            cells.append(fig(web(os.path.join(RUN, "refs", f"{g}__{tag}.jpg"),
                                 f"{g}__{tag}.jpg"),
                             f"&ldquo;{label}&rdquo;"
                             + (f"<span class='n'>{sub}</span>" if sub else "")))
        o.append("<div class='strip s6'>" + "".join(cells) + "</div>")

    # ---- p7.2b+ : the wider ladder --------------------------------------
    plog = json.load(open(os.path.join(RUN, "_p72bplus_prompts.json")))
    o.append("<h2>p7.2b+ &mdash; how fine can the ladder be?</h2>")
    o.append(P72BPNOTE)
    o.append("<div class='swatches'><b>ten steps</b>"
             + "".join(f"<span><i style='background:{h}'></i>{n}</span>"
                       for n, _, h in ST.TONES) + "</div>")
    for g in PP.LADDER_REFS:
        o.append(f"<h3>{html.escape(g)}<span class='r'>every step of the ladder</span></h3>")
        cells = [fig(web(os.path.join(RUN, "inputs", f"{g}.jpg"), f"{g}__raw.jpg"),
                     "the photograph")]
        for word, _, _ in ST.TONES:
            tag = f"p7.2b+.{PP.slug(word)}"
            cells.append(fig(web(os.path.join(RUN, "refs", f"{g}__{tag}.jpg"),
                                 f"{g}__{tag}.jpg"), f"&ldquo;{word}&rdquo;"))
        o.append("<div class='strip s11'>" + "".join(cells) + "</div>")

    o.append("<h3 style='margin-top:34px'>the arm that would ship &mdash; the reader's "
             "own pick for the paired person</h3>")
    cells = []
    for g in P.PROBE:
        e = plog.get(f"{g}|p7.2b+.matched")
        if not e:
            continue
        cells.append(fig(web(os.path.join(RUN, "refs", f"{g}__p7.2b+.matched.jpg"),
                             f"{g}__p7.2b+.matched.jpg"),
                         f"{html.escape(g[:22])}<span class='n'>"
                         f"{html.escape(e['person'][:20])} &rarr; "
                         f"&ldquo;{e['colour']}&rdquo;</span>"))
    o.append("<div class='strip s8'>" + "".join(cells) + "</div>")

    o.append(FOOT + "</div>" + LB + SCRIPT)
    open(os.path.join(REPORT, "v31_p7n.html"), "w").write("\n".join(o))
    print(f"v3/report/v31_p7n.html  ({len(P.PROBE)} references x "
          f"{len(FRAME_ARMS) + len(COLOUR_ARMS)} arms)")


HEAD = """<title>p7.1 and p7.2</title>
<meta name='viewport' content='width=device-width,initial-scale=1'>
<style>
:root{--bg:#0d0d10;--fg:#e8e8ea;--dim:#8a8a94;--line:#26262c;--acc:#7c5cff;--good:#3fb950}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
 font:15px/1.6 ui-sans-serif,-apple-system,"Segoe UI",Roboto,sans-serif}
.wrap{max-width:1560px;margin:0 auto;padding:30px 26px 0}
h1{margin:0 0 6px;font-size:25px}
h2{font-size:20px;margin:52px 0 8px;padding-top:16px;border-top:1px solid var(--line)}
h3{font-size:13px;margin:26px 0 6px;display:flex;gap:12px;align-items:baseline;
 flex-wrap:wrap}
h3 .r{font-size:11.5px;color:var(--dim);font-weight:400}
h3 .r b{color:var(--fg)}
.lede{color:var(--dim);max-width:94ch;font-size:14px;margin:0 0 14px}
.lede b{color:var(--fg)}
.q{border-left:3px solid var(--acc);padding:2px 0 2px 14px;margin:14px 0;max-width:96ch;
 font-size:13.5px;color:#c8c8d0}
.q b{color:var(--fg)}
pre{background:#0b0b0e;border:1px solid var(--line);border-radius:8px;padding:12px 15px;
 font:12.5px/1.7 ui-monospace,SFMono-Regular,monospace;white-space:pre-wrap;color:#b9b9c4;
 max-width:1100px}
pre b{color:var(--good)}
.strip{display:grid;gap:5px;margin-bottom:6px}
.s5{grid-template-columns:repeat(5,1fr)}
.s6{grid-template-columns:repeat(6,1fr)}
.s8{grid-template-columns:repeat(8,1fr)}
.s11{grid-template-columns:repeat(11,1fr)}
.swatches{display:flex;gap:9px;align-items:center;flex-wrap:wrap;margin:12px 0;
 font-size:11.5px;color:var(--dim)}
.swatches b{color:var(--fg);font-size:11px;text-transform:uppercase;letter-spacing:1px}
.swatches span{display:inline-flex;gap:4px;align-items:center}
.swatches i{width:14px;height:14px;border-radius:4px;display:inline-block;border:1px solid #333}
@media(max-width:1400px){.s11{grid-template-columns:repeat(6,1fr)}
 .s8{grid-template-columns:repeat(4,1fr)}}
@media(max-width:1000px){.s5,.s6,.s8,.s11{grid-template-columns:repeat(2,1fr)}}
figure{margin:0}
figure img{width:100%;display:block;background:#fff;border-radius:6px;cursor:zoom-in;
 aspect-ratio:3/4;object-fit:contain}
figure.base img{outline:2px solid #3a3a46;outline-offset:-2px}
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
<div class='wrap'><h1>p7.1 and p7.2 &mdash; framing and colour</h1>
<p class='lede'>Eight references chosen because they carry the defects, not at random.
Every prompt on this page is the same sentence with <b>one word or one clause
changed</b>, so a difference between columns is attributable to that change and nothing
else. Click any image for full size.</p></div>
"""

STRUCT = """<div class='q'>Every prompt is built by concatenation:</div>
<pre>"Show this person's outfit on a " + <b>&lt;colour word&gt;</b> + " mannequin against pure white. …"  + <b>&lt;framing clause&gt;</b></pre>
<div class='q'><b>p7.1</b> holds the colour word empty and varies the framing clause.
<b>p7.2</b> holds the framing clause empty and varies the colour word. The two are not
combined yet &mdash; that is the next run, and only for whichever arms win here.</div>"""

P71NOTE = """<div class='q'><b>Re-run 2026-08-27 with a fixed prompt.</b> The first pass
of these three arms sent <code>"on a mannequin mannequin against pure white"</code> - the
colour slot was fed the literal word <i>mannequin</i> and the suffix already supplies the
noun. Those 24 frames are kept on disk as <code>__p7.1.n-dup.jpg</code>; everything shown
below is the clean re-run.</div>
<div class='q'>The defect: <code>p7</code> asks for a body
&ldquo;from head to feet&rdquo;, so a waist-up photograph gets legs invented. Three ways
to stop that, two of them free. <b>.1</b> and <b>.2</b> are pure prompt &mdash; the model
is told to limit itself and no code runs. <b>.3</b> reads the pose landmarks on CPU
(36&nbsp;ms) and injects the extent it found, so the model is told the answer rather than
asked to work it out. The pose reader's verdict is printed above each row: <b>if the
reader is wrong, .3 will be confidently wrong</b>, which is the risk of the CPU route and
the reason .1 and .2 are being tried at all.</div>"""

P72NOTE = """<div class='q'><b>This group failed.</b> A bare chromatic adjective does not
stay on the mannequin: <code>"tan"</code> turned <code>p029</code>'s white button-down
into a <b>tan polo shirt</b> and <code>emma_watson</code>'s black blazer <b>brown</b>.
White, grey and black leave the garment alone. The pattern is <b>achromatic versus
chromatic</b>, not matched versus unmatched. p7.2b below is the follow-up.</div>
<div class='q'>The defect: a white form under a white garment is a
low-amplitude boundary, and a low-amplitude boundary does not exist as a signal at the
timesteps where layout is decided &mdash; the same mechanism that made
<code>HD_p023</code> return its input in V2. Four colour words.
<b>white</b> is the current behaviour and the control. <b>grey</b> asks whether any
non-white value fixes it without needing to know anything about the person.
<b>matched</b> is the CPU skin reader run on the <i>paired person</i>.
<b>contrast</b> picks the tone word furthest in lightness from the garment itself.
<b>If grey does as well as matched, the skin reader is not needed</b> &mdash; that is the
result worth watching for, because it is the cheaper system.</div>"""

P72BNOTE = """<div class='q'>If <code>"tan"</code> leaks because the adjective is loose,
then <b>naming what the colour belongs to should keep it there</b>. Same slot, same
sentence, but the word is now <code>"tan skin"</code> rather than <code>"tan"</code> -
which says the colour is the mannequin's complexion and not the picture's palette.
<code>"grey"</code> stays bare, because a grey mannequin is a material rather than a
complexion, and it is the control that needs no reader at all.</div>
<div class='q'><b>What to check:</b> is the garment still its own colour, and is the
mannequin distinguishable from a pale garment. If <code>"grey"</code> does as well as any
skin word, the skin reader is unnecessary and the cheaper system wins.</div>"""

P72BPNOTE = """<div class='q'><b>p7.2b worked</b>, so the question becomes how fine the
ladder can usefully be. Ten steps instead of four, every one an ordinary phrase, every one
carrying the word <i>skin</i> because that is what stopped the leak.
<b>&ldquo;grey&rdquo; is deliberately absent from this ladder</b> &mdash; it is the
achromatic control and it is not a complexion.</div>
<div class='q'>The full ladder is run on <b>four references</b>: a light garment that bled
under a bare adjective, a dark garment that bled, a multi-piece that survived, and a dark
full-body control. The last strip is the arm that would actually ship &mdash; the CPU
reader's own pick, run on the <b>paired person</b> for all eight references, with the word
it chose printed under each.</div>
<div class='q'><b>What to judge:</b> whether ten steps are distinguishable at all, or
whether the model collapses them into three or four. If neighbouring steps are
indistinguishable the ladder is finer than the model, and the reader can be coarser and
cheaper.</div>"""

FOOT = """<footer>References <code>v3/runs/v3.0b/refs/{ref}__{arm}.jpg</code> &middot;
every prompt as sent: <code>v3/runs/v3.0b/_p7n_prompts.json</code> &middot; readers:
<code>v3/build/skin_tone.py</code> &middot; rebuild:
<code>python3 v3/build/p7n_page.py</code>. Nothing here has been through a klein edit yet:
these are references, not try-ons.</footer>"""

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
