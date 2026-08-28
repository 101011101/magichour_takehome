"""Phase 6 page: the pose word, and what is actually wrong with g011.

Two experiments that answered cleanly, so the page is built to make the answers
readable rather than to invite a verdict. Section 1 varies one clause. Section 2 is a
stage-isolation: person alone, other references, other prompts - laid out so the column
that differs names the cause.
"""
import html
import json
import os
import sys

from PIL import Image

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RUN = os.path.join(REPO, "v3", "runs", "v3.0b")
REPORT = os.path.join(REPO, "v3", "report")
IMG = os.path.join(REPORT, "img_ph6")
sys.path.insert(0, os.path.join(REPO, "v3", "build"))
import run_pose_g011 as PG  # noqa: E402

POSE_REFS = ["g013", "g014", "g011", "g030"]
POSE_COLS = [("ck.matched", "no pose word", "the shipped prompt"),
             ("pose.neutral", "+ neutral upright", "&ldquo;stands in a neutral upright pose, feet together&rdquo;"),
             ("pose.forward", "+ faces forward", "&ldquo;stands straight and faces forward, weight even on both feet&rdquo;")]
B1 = [("p019__b1_black_tee", "black t-shirt"), ("p019__b1_red_dress", "red dress"),
      ("p019__b1_blue_shirt", "blue button-down")]
B2 = [("p019__b2_g014", "g014 &mdash; sleeveless blue dress", True),
      ("p019__b2_g030", "g030 &mdash; long-sleeved gold jacket", False),
      ("p019__b2_dualuse_man_black_", "black suit &mdash; long sleeves", False)]
B3 = [("p019__b3_standard", "the shipped prompt"),
      ("p019__b3_garment_only", "&ldquo;replace only the clothing&rdquo;"),
      ("p019__b3_terse", "terse: &ldquo;put the outfit onto the person&rdquo;"),
      ("p019__b3_skin", "&ldquo;skin tone and texture unchanged everywhere visible&rdquo;")]


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
    return "img_ph6/" + dst, "img_ph6/" + os.path.basename(full)


def fig(pair, cap, cls=""):
    src, full = pair
    if not src:
        return f"<figure class='miss'><div class='ph'>not run</div><figcaption>{cap}</figcaption></figure>"
    return (f"<figure class='{cls}'><img src='{src}' data-full='{full}' "
            f"alt='{html.escape(cap.replace('&mdash;','-'))}' loading='lazy'>"
            f"<figcaption>{cap}</figcaption></figure>")


def gen(name, dst):
    return web(os.path.join(RUN, "gen", f"{name}.jpg"), dst)


def main():
    os.makedirs(IMG, exist_ok=True)
    o = [HEAD, "<div class='wrap'>"]

    # ---- 1. pose ----
    o.append("<h2>1 &middot; Can a pose word remove the stride?</h2>")
    o.append(POSENOTE)
    for g in POSE_REFS:
        o.append(f"<h3>{html.escape(g)}"
                 + ("<span class='r'>the reference behind the &ldquo;extra leg&rdquo; "
                    "failure</span>" if g == "g013" else
                    "<span class='r'>already neutral &mdash; the control</span>"
                    if g in ("g011", "g030") else "") + "</h3>")
        o.append("<div class='strip s3'>" + "".join(
            fig(web(os.path.join(RUN, "refs", f"{g}__{t}.jpg"), f"{g}__{t}.jpg"),
                f"{lab}<span class='n'>{sub}</span>", "win" if t == "pose.neutral" else "")
            for t, lab, sub in POSE_COLS) + "</div>")
    o.append(POSECAVEAT)

    # ---- 2. g011 ----
    o.append("<h2>2 &middot; What is actually wrong with <code>g011</code></h2>")
    o.append(G011NOTE)

    o.append("<h3>B1 &mdash; is it the person? <span class='r'>klein on <b>p019 alone</b>, "
             "text-only clothing edits, <b>no garment reference at all</b></span></h3>")
    o.append("<div class='strip s4'>"
             + fig(web(os.path.join(RUN, "inputs", "p019.jpg"), "p019.jpg"),
                   "p019 &mdash; the person<span class='n'>long-sleeved coat</span>")
             + "".join(fig(gen(k, k + ".jpg"), f"&ldquo;{lab}&rdquo;", "clean")
                       for k, lab in B1) + "</div>")
    o.append("<div class='verdict good'><b>Clean.</b> Given no reference, klein renders "
             "her arms perfectly well. <b>The person is not the problem.</b></div>")

    o.append("<h3>B2 &mdash; is it the reference? <span class='r'>the shipped prompt, "
             "other mannequin references</span></h3>")
    o.append("<div class='strip s4'>"
             + fig(gen("p019__b3_standard", "b3_standard.jpg"),
                   "g011 &mdash; sleeveless black dress<span class='n'>the original failure</span>",
                   "bad")
             + "".join(fig(gen(k, k + ".jpg"), lab, "bad" if bad else "clean")
                       for k, lab, bad in B2) + "</div>")
    o.append("<div class='verdict good'><b>The variable is sleeves.</b> Every reference "
             "that leaves the arms bare cooks. The two that cover them do not.</div>")

    o.append("<h3>B3 &mdash; is it the prompt? <span class='r'>same person, same "
             "<code>g011</code> reference, four different edit instructions</span></h3>")
    o.append("<div class='strip s4'>" + "".join(
        fig(gen(k, k + ".jpg"), lab, "bad") for k, lab in B3) + "</div>")
    o.append("<div class='verdict bad'><b>All four cook</b> &mdash; including the one that "
             "explicitly says her skin tone and texture are unchanged everywhere they are "
             "visible. <b>The prompt is not a lever.</b></div>")

    o.append(MECH)
    o.append(FOOT + "</div>" + LB + SCRIPT)
    open(os.path.join(REPORT, "v31_phase6.html"), "w").write("\n".join(o))
    print(f"v3/report/v31_phase6.html  ({len(POSE_REFS)} pose refs, 3 g011 tests)")


HEAD = """<title>v3.1 phase 6 — pose, and the cooked texture</title>
<meta name='viewport' content='width=device-width,initial-scale=1'>
<style>
:root{--bg:#0d0d10;--fg:#e8e8ea;--dim:#8a8a94;--line:#26262c;--acc:#7c5cff;
 --good:#3fb950;--bad:#f85149;--mid:#d29922}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
 font:15px/1.6 ui-sans-serif,-apple-system,"Segoe UI",Roboto,sans-serif}
.wrap{max-width:1500px;margin:0 auto;padding:30px 26px 0}
h1{margin:0 0 6px;font-size:25px}
h2{font-size:21px;margin:56px 0 8px;padding-top:16px;border-top:1px solid var(--line)}
h3{font-size:14px;margin:30px 0 7px;display:flex;gap:12px;align-items:baseline;flex-wrap:wrap}
h3 .r{font-size:11.5px;color:var(--dim);font-weight:400}
h3 .r b{color:var(--fg)}
.lede{color:var(--dim);max-width:96ch;font-size:14px;margin:0 0 14px}
.lede b{color:var(--fg)}
.q{border-left:3px solid var(--acc);padding:2px 0 2px 14px;margin:14px 0;max-width:98ch;
 font-size:13.5px;color:#c8c8d0}
.q b{color:var(--fg)}
.verdict{border-radius:8px;padding:9px 15px;margin:8px 0 4px;font-size:13.5px;
 max-width:98ch;border:1px solid var(--line);background:#101014}
.verdict.good{border-color:#2c5c33}
.verdict.bad{border-color:#5a2a2a}
.verdict b{color:var(--fg)}
.strip{display:grid;gap:5px;margin-bottom:6px}
.s3{grid-template-columns:repeat(3,1fr);max-width:1080px}
.s4{grid-template-columns:repeat(4,1fr)}
@media(max-width:900px){.s3,.s4{grid-template-columns:repeat(2,1fr)}}
figure{margin:0}
figure img{width:100%;display:block;background:#fff;border-radius:6px;cursor:zoom-in;
 aspect-ratio:3/4;object-fit:contain}
figure.win img{outline:2px solid #2c5c33;outline-offset:-2px}
figure.win figcaption{color:var(--good);font-weight:700}
figure.clean img{outline:2px solid #2c5c33;outline-offset:-2px}
figure.bad img{outline:2px solid var(--bad);outline-offset:-2px}
figure.bad figcaption{color:var(--bad)}
figcaption{font-size:11px;color:var(--dim);text-align:center;padding:5px 3px;line-height:1.4}
figcaption .n{display:block;font-size:9.5px;opacity:.85}
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
<div class='wrap'><h1>Phase 6 &mdash; a pose word, and the cooked texture</h1>
<p class='lede'>Two experiments that answered cleanly. The first asks whether the stride
can be removed with words instead of by giving up the skin-tone colour. The second stops
guessing at <code>g011</code> and isolates the stage: <b>the person, the reference, and
the prompt, each varied alone.</b> Click any image for full size.</p></div>
"""

POSENOTE = """<div class='q'>The colour word decides <b>what kind of object</b> gets
rendered: <i>grey</i>, <i>white skin</i> and <i>black skin</i> name plausible mannequin
materials and produce a static form, while <i>light brown skin</i> names something that is
not a manufactured object, so the model renders <b>a person</b> &mdash; and people have
strides. <code>p021</code>'s &ldquo;extra leg&rdquo; is downstream of a colour word.</div>
<div class='q'>Rather than give up the skin tone, <b>ask for the pose directly</b> &mdash; a
positive instruction naming what is wanted, which is the form that has worked throughout
this investigation.</div>"""

POSECAVEAT = """<div class='verdict good'><b>It works, and it costs eight words.</b>
<code>g013</code> comes back feet-together and neutral. Both phrasings behave the same, so
the shorter one wins.</div>
<div class='verdict bad'><b>It is not free.</b> On <code>g030</code> the pose sentence also
changed the <b>framing</b> &mdash; without it the mannequin was cropped near the waist,
with it the full length appears. <i>&ldquo;Feet together&rdquo;</i> implies feet are in
frame, which contradicts the extent clause telling it to cut above them. <b>Two clauses in
the same prompt now disagree about how much body to show, and the pose clause wins</b>
&mdash; so the pose word can silently undo the framing fix. Either the phrasing avoids
naming feet, or the two clauses become one.</div>"""

G011NOTE = """<div class='q'><code>p019+g011</code> is the only pair no arm gets perfect,
and its output has a &ldquo;cooked&rdquo; skin texture on the arms that the colour sweep did
not fix. Colour was the leading hypothesis and it is now weakened, so rather than guess
again: <b>vary one stage at a time and let the column that differs name the cause.</b></div>"""

MECH = """<div class='q'><b>The mechanism, and it is V2's own finding inverted.</b>
<code>p019</code> wears a <b>long-sleeved coat</b> &mdash; her arms have never been
photographed, and those pixels do not exist in the input. A sleeveless garment demands arm
skin the photograph never contained.<br><br>
V2: <i>&ldquo;subtraction cannot recover a garment region that hair was covering &mdash;
the pixels were never observed.&rdquo;</i><br>
Here: <b>the edit cannot recover skin that clothing was covering.</b> Same missing-pixel
problem, on the person's side instead of the garment's.</div>
<div class='q'><b>And the reference decides what fills the gap.</b> Given no reference,
klein invents plausible skin from its prior and gets it right. Given one, it fills from the
nearest available content in the attention sequence &mdash; <b>the mannequin's arm</b>
&mdash; a manufactured surface tinted from her face. Skin-shaped, wrong tone, wrong
texture. That is why changing the colour did not help: <b>recolouring the thing being
copied from does not stop it being copied from.</b></div>
<div class='q'><b>This is bigger than one reference.</b> It should fire whenever the target
garment <b>exposes a region the source photograph covered</b> &mdash; bare arms under long
sleeves, bare legs under trousers, an open neck under a high collar. <b>It is a property of
the pairing, not of either image, and nothing in the pipeline detects it.</b> The CPU stack
reads the garment reference; it has never been asked what the person's photograph
hides.</div>"""

FOOT = """<footer>Prompts as sent: <code>v3/runs/v3.0b/_pose_g011.json</code> &middot;
runner: <code>v3/build/run_pose_g011.py</code> &middot; rebuild:
<code>python3 v3/build/phase6_page.py</code>. Section 1 is references; section 2 is klein
outputs. One seed throughout.</footer>"""

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
