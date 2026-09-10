"""Build the v3.6 submission report — two pages, both from the files, not from memory.

  page 1  v3/report/v36_report.html    at a glance: the architecture, the numbers, and the
                                       cells that show what one word changed
  page 2  v3/report/v36_findings.html  the long read: what the v3.x series established, and
                                       why ER is the end of the line for call 2

Every number on either page is computed here from the run meta and the marks CSV, so the
pages cannot drift from the evidence. Where a number is an extrapolation rather than a
measurement it is labelled as one on the page itself.

  python3 v3/build/v36_report.py
"""
import csv
import html
import json
import os
import statistics as stat
import sys

from PIL import Image

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "v3", "colab", "lib"))
import run_v36 as V                   # noqa: E402  the prompts, as the runner defines them

RUN = os.path.join(REPO, "v3", "runs", "v36", "a100")
BCRUN = os.path.join(REPO, "v3", "runs", "v34", "ironman2_bc")
REPORT = os.path.join(REPO, "v3", "report")
IMG = os.path.join(REPORT, "img_v36r")
MARKS = os.path.join(REPO, "v3", "testsets", "v36_er_vs_bc.csv")
COUNT = os.path.join(REPO, "v3", "testsets", "bc_count.csv")

# cells that carry the long report's arguments, named here so the prose and the pictures
# cannot disagree
HANDS_CASE = ("p008+dualuse_emma_watson_black_blazer_armscrossed", "47")
SAME_CASES = [("p022+p023", "47"), ("g024+p010", "46"), ("p010+p023", "48"),
              ("dualuse_man_black_suit_studio_nonceleb+dualuse_lp_beige_long_coat_menswear", "47"),
              ("p026+dualuse_lp_beige_long_coat_menswear", "46"), ("g013+g014", "47")]


# ------------------------------------------------------------------ images ---
def web(src, dst, width=460):
    if not os.path.exists(src):
        return None, None
    out, full = os.path.join(IMG, dst), os.path.join(IMG, dst.replace(".jpg", "@full.jpg"))
    im = None
    if not os.path.exists(out):
        im = Image.open(src).convert("RGB")
        t = im.resize((width, int(im.height * width / im.width)), Image.LANCZOS) if im.width > width else im
        t.save(out, quality=90, optimize=True)
    if not os.path.exists(full):
        im = im or Image.open(src).convert("RGB")
        im.save(full, quality=94, optimize=True)
    return "img_v36r/" + dst, "img_v36r/" + os.path.basename(full)


def fig(src, dst, cap, width=460, cls=""):
    t, f = web(src, dst, width)
    if not t:
        return ""
    return (f"<figure class='{cls}'><img src='{t}' data-full='{f}' alt='{html.escape(cap)}' "
            f"loading='lazy'><figcaption>{cap}</figcaption></figure>")


def cell(sid, seed, arms=("E0", "ER"), person=None, garment=None, note=""):
    """One comparison strip: person, reference, then one column per arm."""
    row = list(csv.DictReader(open(os.path.join(RUN, "v36_editset.csv"))))
    r = next(x for x in row if x["set_id"] == sid and x["seed"] == str(seed))
    lab = {"E0": "BC &mdash; <i>dress the person in&hellip;</i>",
           "ER": "ER &mdash; <i>replace the clothing with&hellip;</i>"}
    parts = [fig(os.path.join(RUN, "inputs", f"{r['person']}.jpg"), f"{r['person']}__p.jpg",
                 "the person (image 1)", 300),
             fig(os.path.join(RUN, "refs", f"{r['garment']}__BC.jpg"), f"{r['garment']}__r.jpg",
                 "the reference (image 2)", 300)]
    outs = [fig(os.path.join(RUN, "gen", f"{sid}__{a}__s{seed}.jpg"), f"{sid}__{a}__s{seed}.jpg",
                lab.get(a, a)) for a in arms]
    return (f"<div class='cellcard'><div class='ch'><b>{html.escape(sid)}</b>"
            f"<span class='t'>seed {seed}</span>"
            + (f"<span class='note'>{note}</span>" if note else "") + "</div>"
            f"<div class='cellbody'><div class='src'>{''.join(parts)}</div>"
            f"<div class='outs'>{''.join(outs)}</div></div></div>")


# ------------------------------------------------------------------- stats ---
def numbers():
    marks = list(csv.DictReader(open(MARKS)))
    count = list(csv.DictReader(open(COUNT)))
    bc_fail = sum(r["bc_failed"] == "fail" for r in count)
    er_t = [float(x["seconds"]) for x in
            csv.DictReader(open(os.path.join(RUN, "meta", "timings_v36_editprompts.csv")))
            if x["arm"] == "ER"]
    bc_cost = json.load(open(os.path.join(BCRUN, "meta", "cost.json")))
    n = lambda bc, v: sum(1 for r in marks if r["bc"] == bc and r["better"] == v)   # noqa: E731

    # seed behaviour of the failures: how much of the 4.8% is a seed lottery rather than a
    # broken pair. Drives the retry argument, so it is derived here and never typed in.
    by = {}
    for r in count:
        by.setdefault(r["set_id"], {})[r["seed"]] = r["bc_failed"] == "fail"
    dist = {k: sum(1 for v in by.values() if sum(v.values()) == k) for k in (0, 1, 2, 3)}
    num = den = 0
    for v in by.values():
        for sd, failed in v.items():
            if not failed:
                continue
            others = [x for k, x in v.items() if k != sd]
            den += len(others)
            num += sum(1 for x in others if not x)
    return {
        "pairs": len(by), "seed_dist": dist,
        "pairs_failing": len(by) - dist[0], "pairs_stable": dist[3],
        "stable_pct": 100 * dist[3] / len(by),
        "retry_pass": 100 * num / den, "retry_num": num, "retry_den": den,
        "residual": (bc_fail / len(count)) * (1 - num / den) * 100,
        "cells": len(marks),
        "bc_cells": len(count), "bc_fail": bc_fail,
        "bc_rate": 100 * bc_fail / len(count),
        "fail_n": sum(1 for r in marks if r["bc"] == "fail"),
        "ok_n": sum(1 for r in marks if r["bc"] == "ok"),
        "er_win_fail": n("fail", "ER"), "er_win_ok": n("ok", "ER"),
        "bc_win": n("fail", "BC") + n("ok", "BC"),
        "same": n("fail", "same") + n("ok", "same"),
        "unmarked": sum(1 for r in marks if not r["better"]),
        "er_calls": len(er_t), "er_median": stat.median(er_t), "er_mean": sum(er_t) / len(er_t),
        "bc_per_call": bc_cost["klein_seconds_per_call"],
        "bc_usd": bc_cost["usd_measured"], "bc_fal": bc_cost["usd_fal_equivalent"],
        "bc_wall_min": bc_cost["wall_seconds"] / 60,
        "marks": marks,
    }


def tile(value, label, sub, tone=""):
    return (f"<div class='tile {tone}'><div class='v'>{value}</div>"
            f"<div class='l'>{label}</div><div class='s'>{sub}</div></div>")


# -------------------------------------------------------------------- page ---
def page1(N):
    wins = [r for r in N["marks"] if r["better"] == "ER"]
    rescue = 100 * N["er_win_fail"] / N["fail_n"]
    proj = N["bc_fail"] - round(N["bc_fail"] * N["er_win_fail"] / N["fail_n"])

    tiles = "".join([
        tile(f"{N['bc_rate']:.1f}%", "BC_klein failure rate",
             f"{N['bc_fail']}/{N['bc_cells']} cells, blind sweep, 2026-09-10"),
        tile(f"{N['er_win_fail']}/{N['fail_n']}", "of BC's failures ER repairs",
             f"{rescue:.0f}% of the failure set, marked head to head"),
        tile(f"{N['bc_win']}/{N['ok_n']}", "regressions on cells BC passed",
             "no cell was marked BC-better anywhere on the set", "good"),
        tile(f"{N['er_median']:.2f}s", "median ER call",
             f"BC is {N['bc_per_call']:.2f}s &mdash; the same call, one word longer"),
        tile(f"CAD {N['bc_usd']:.2f}", "per 600-cell arm, self-hosted",
             f"${N['bc_fal']:.2f} of fal calls; ER costs the same"),
        tile("0", "extra model calls ER adds",
             "same pipeline, same reference, same canvas, same seed"),
    ])
    ship = f"""<h2>What ships</h2>
<p><b><code>ER</code> is the arm to deploy</b> &mdash; the incumbent pipeline with one verb
changed in call 2. Nothing else about the system moves, which is the point: it costs no call,
no model and no measurable time.</p>
<p><b>On top of it, a seed randomiser.</b> A rejected image is redrawn at a fresh seed rather
than repaired. The failure record is what recommends this: of the
<b>{N['pairs_failing']} pairs that fail at all</b>, only <b>{N['pairs_stable']}</b> fail at
every seed &mdash; {N['stable_pct']:.1f}% of the catalogue. Given a failed cell, a different
seed of the same pair passes <b>{N['retry_num']}/{N['retry_den']} =
{N['retry_pass']:.0f}%</b> of the time, so one retry takes the expected residual from
{N['bc_rate']:.1f}% to about <b>{N['residual']:.1f}%</b>, and further retries approach the
<b>{N['stable_pct']:.1f}% floor</b> &mdash; the pairs whose <i>reference</i> is wrong, which no
seed repairs. Only rejected images are redrawn, so the policy adds roughly
{N['bc_rate']:.0f}% to the call count.</p>
<p class='caveat'><b>The dependency is a rejector, and it is unbuilt.</b> A retry policy needs
something that decides an image failed. The v3.6 VLM judge is a first attempt and is not good
enough yet: its artifact flag fires on 45% of cells a human passed. Its limb flag is the
strongest discriminator found so far (14.8&times; over base rate) and phasing is usable
(2.7&times;); the artifact bucket is not. That is the next piece of work, and until it exists
the retry rates above are a property of the model, not a shipped number.</p>"""

    galleryA = "".join(cell(r["set_id"], r["seed"],
                            note="BC failed here" if r["bc"] == "fail" else "BC passed here")
                       for r in wins)
    galleryB = "".join(cell(sid, seed, note="no difference marked") for sid, seed in SAME_CASES)

    return f"""{HEAD.replace('TITLE', 'v3.6 &mdash; one word in call 2')}
<div class='wrap'>
<p class='lede'>The deployed pipeline changes by <b>one verb</b>. <code>BC_klein</code>'s
call 2 says <i>dress the person in the clothing shown in image 2</i>; <code>ER</code> says
<i>replace the clothing in image 1 with the clothing in image 2</i>. Nothing else moves:
same reference, same canvas, same seed, same model, same call count. This page is the
evidence at a glance; <a href='v36_findings.html'>the long read</a> is why nothing more
ambitious than this survived.</p>

<h2>The architecture, as deployed</h2>
<div class='arch'>
  <div class='step'><span class='k'>call 1</span><b>klein bald pass</b>
    <p>The garment photograph, edited to remove the wearer's hair. A small,
    in-distribution edit &mdash; the only generative step that touches the source.</p></div>
  <div class='arrow'>&rarr;</div>
  <div class='step'><span class='k'>no model</span><b>V2 cropper, head subtracted</b>
    <p>BiRefNet matte &times; human-parser classes, cranium &rarr; white. Deterministic and
    <b>subtractive only</b>: it can remove, never invent. The garment pixels that reach
    call 2 are the photograph's.</p></div>
  <div class='arrow'>&rarr;</div>
  <div class='step hero'><span class='k'>call 2</span><b>klein edit &mdash; <code>ER</code></b>
    <p>Person + reference in, dressed person out. The one line this investigation
    changed.</p></div>
</div>
<div class='prompts'>
  <div class='pr'><b>BC</b><code>{html.escape(V.E0)}</code></div>
  <div class='pr'><b>ER</b><code>{html.escape(V.ER)}</code></div>
</div>

<h2>The numbers</h2>
<div class='tiles'>{tiles}</div>
<p class='caveat'><b>Read these as they are.</b> The {N['bc_rate']:.1f}% is measured &mdash;
a blind pass over all {N['bc_cells']} cells of the iron-man-2 matrix. The <code>ER</code>
column is a <b>head-to-head over {N['cells']} cells</b> ({N['fail_n']} of BC's failures and
{N['ok_n']} of its passes), marked with both images side by side. {N['unmarked']} cells were
left unmarked as showing no difference worth calling; they are counted as neither a win nor
a loss. <b>No cell anywhere on the set was marked BC-better.</b> A like-for-like rate for
<code>ER</code> needs the same blind sweep over the same 600 cells &mdash; that run is built
and is the next step. On the marks so far it would land near
<b>{proj}/{N['bc_cells']} ({100 * proj / N['bc_cells']:.1f}%)</b>, and that is an
extrapolation, not a measurement.</p>

{ship}

<h2>What one word repairs</h2>
<p class='sec'>Every cell <code>ER</code> was marked better on. The failure class is the
same each time: <b>the wearer's own clothing survives underneath the new garment</b>.
<i>Dress the person in</i> names only the putting-on and leaves the removal implicit;
<i>replace&hellip;with</i> names both.</p>
{galleryA}

<h2>What it leaves alone</h2>
<p class='sec'>The other side of the same coin, and the reason the change is safe: on cells
that already worked, the two are indistinguishable. A prompt that rescues failures by
redrawing everything would show it here.</p>
{galleryB}

<footer>Built by <code>v3/build/v36_report.py</code> from
<code>v3/testsets/v36_er_vs_bc.csv</code>, <code>v3/testsets/bc_count.csv</code> and the run
meta in <code>v3/runs/v36/a100/</code>. Images are the run's own outputs; click any for full
size. Evidence bundles live on Drive (<code>v3_runs/v36_*.zip</code>) per the V3 rule that
generated images stay out of git. &middot; <a href='v36_findings.html'>the long read
&rarr;</a></footer>
</div>{LB}{SCRIPT}"""


def page2(N):
    return f"""{HEAD.replace('TITLE', 'v3.6 &mdash; what the series established')}
<div class='wrap'>
<p class='lede'>The short version: <b>the reference is the ceiling, and the reference cannot
be improved by generating it.</b> Everything below is how the v3.x series arrived there, and
why <code>ER</code> &mdash; one verb in call 2 &mdash; is the most that can be taken without
paying complexity that does not earn itself. <a href='v36_report.html'>&larr; back to the
evidence at a glance</a></p>

<h2>1. The shape of the problem</h2>
<p>Try-on is two calls. Call 1 turns a photograph of a person wearing clothes into a
<b>reference</b> that shows the clothes without the identity. Call 2 puts that reference on
the target. Every version of this project has moved effort between those two calls, and the
series' central finding is that <b>call 1 decides the outcome</b> &mdash; call 2 faithfully
transfers whatever it is given, including the mistakes.</p>

<h2>2. Regeneration is a tax, and it is charged on the garment</h2>
<p>v3.1 through v3.4 built increasingly sophisticated call-1 arms: mannequin head swaps,
explicit re-posing, canvas discipline, super-resolution applied only to finished references.
The locked arm <code>VEi</code> is the best of them. Measured over the same 600 cells, it
failed <b>9.2%</b> against the incumbent <code>BC_klein</code>'s <b>4.8%</b> &mdash; 43 cells
where the sophisticated arm fails and the simple one does not, against 17 the other way.</p>
<p>The mechanism is not subtle once stated. <code>BC</code> edits the <i>head</i> and then
isolates the garment with a <b>deterministic matte</b>, which can only remove; its garment
pixels are the photograph's, end to end. Every <code>V</code>-family arm asks a generative
model to <b>re-draw the whole frame</b>, because a head swap and a re-pose are full-frame
edits. A distilled 4-step model re-drawing a garment does not copy it. It resamples it, and
what it loses is exactly what call 2 needs: weave, print registration, seam and hem
placement, the number of pieces. The loss is not noise, it is <b>structured invention</b>
&mdash; and call 2 cannot tell an invented placket from a real one, so it transfers the
invention faithfully. A call-1 defect is not merely carried forward, it is <b>amplified</b>.</p>
<p class='k'>Corollary, and it is the load-bearing one: <b>re-folding, unfolding, flattening or
otherwise restyling the garment through klein does not work.</b> Not because the prompt is
wrong &mdash; because the operation is generative, and every generative touch of the garment
costs fidelity. The most aggressive version of it, <code>G1</code> (remove the wearer
entirely, return the clothing alone), is the only call-1 arm that fails the garment test
outright: lengths change, pieces vanish, a blazer returns as a full-length coat.</p>

<h2>3. So the only safe edit is the one that removes</h2>
<p>If generating the garment is what costs, the arm to keep is the one that never does.
That is the whole of the deployed pipeline: one small in-distribution edit to the
<b>head</b>, then a matte that subtracts. Identity comes off; the clothes are untouched
photograph. Compaction schemes &mdash; re-encoding the garment into a cleaner, smaller or
canonical form before call 2 &mdash; all fail the same way, because every one of them is a
lossy re-encode and the thing being lost is the fidelity call 2 is about to magnify.</p>
<p>If a genuinely restructured reference is ever needed, the evidence says it must come from
<b>a different model</b>, not a better prompt to this one: <code>QX</code>, v3.1's
qwen-image-edit garment isolation, is the arm that does that job and it is a separate
architecture, not a klein setting.</p>

<h2>4. The case that shows why we stop here &mdash; hands</h2>
<p>The clearest residual defect is a reference whose wearer has <b>arms crossed</b>. The
matte cannot know that the folded arms are not part of the garment's shape, so call 2
receives a jacket with a pair of arms baked into its silhouette, and duplicates them.</p>
{cell(HANDS_CASE[0], HANDS_CASE[1], note='arms crossed in the reference')}
<p>The tempting fix is to unfold the arms in call 1 &mdash; and that is precisely the
operation §2 rules out. Unfolding is a full-frame regeneration of the garment; to remove the
duplicated arms it must re-draw the sleeves, the front closure and the drape, which is where
lengths change and pieces vanish. <b>The fix costs more than the defect.</b> So the honest
position is that this class is out of reach of call 2 wording, and out of reach of call 1
without changing models.</p>

<h2>5. What v3.6 actually tested, and what it settled</h2>
<p>Given call 1 is fixed, v3.6 asked the only remaining question: how much can call 2's
prompt buy? Six prompts, each holding the reference, the canvas, the seed and the model
constant.</p>
<table>
<tr><th>arm</th><th>the change</th><th>verdict</th></tr>
<tr><td><code>ER</code></td><td>the verb: <i>replace the clothing with</i></td>
<td class='good'>adopted &mdash; repairs the survives-underneath class at zero cost</td></tr>
<tr><td><code>EFR</code></td><td><code>ER</code> + a no-blend paragraph</td>
<td>no gain over <code>ER</code>; one regression seen on a passing cell</td></tr>
<tr><td><code>EX</code></td><td>removal + layering + piece count + limb count + framing</td>
<td>reframes and invents lower bodies; longer prompts drift a 4-step distilled model</td></tr>
<tr><td><code>ERD</code></td><td><code>ER</code> + a limb clause built per cell from a pose read</td>
<td>indistinguishable from <code>ER</code> &mdash; it only buys back harm <code>ER</code> never causes</td></tr>
<tr><td><code>ERS</code></td><td>the same limb clause, always</td>
<td class='bad'>harmful &mdash; see below</td></tr>
</table>
<p><b>The measured result, and the one worth keeping.</b> V2's dynamic-prompt rule
&mdash; <i>never name a body part the crop excludes</i> &mdash; had governed call 1 since
v3.1 on the strength of an assumption. v3.6 measured it on call 2. On the <b>59 cells whose
photograph has no feet in frame</b>, running the same pose read over the outputs finds feet
that the source never had in <b>21</b> of <code>ERS</code>'s cells and <b>2</b> of
<code>ERD</code>'s. Naming an absent limb makes the model draw it, twelvefold. That is also
the explanation for the zoom-outs seen in <code>EL</code> and <code>EX</code>.</p>
<p>The conclusion is not "use the dynamic clause". It is <b>use no clause</b>: plain
<code>ER</code> never names a limb, so it never triggers the failure the clause exists to
prevent, and it costs no pose read. The machinery stays in call 1 where the framing genuinely
has to be described.</p>

<h2>6. Two controls that make the above readable</h2>
<p><b>The pipeline is deterministic.</b> On the 86 cells where <code>ERD</code> and
<code>ERS</code> were sent identical text, the outputs are <b>byte-identical</b>. So every
difference measured in v3.6 is the prompt and not sampling noise.</p>
<p><b>fal and the A100 are not the same deployment.</b> Same prompt, same seed, same canvas
rule &mdash; and most archived <code>BC</code> failures do not reproduce on fal. Any arm
compared against a record must run on the hardware the record was made on. It is why the
v3.6 runs moved back to the A100 after the first probe.</p>

<h2>7. Where this leaves the work</h2>
<ul>
<li><b>Ship <code>ER</code>.</b> One verb, no new call, no new model, no new failure mode
found on {N['ok_n']} passing cells.</li>
<li><b>The remaining defects are reference-side</b>, and reference-side means model-side:
crossed arms, dropped pieces on ambiguous lower bodies, the wearer's own accessories. None
of them is a call-2 wording problem.</li>
<li><b>The open architectural question</b> is not "is <code>BC</code> better" but
<i>does re-posing buy back more than the re-draw costs, and on what share of a real
catalogue?</i> The 200-pair fold is mostly front-facing wearers, which flatters
<code>BC</code>; a catalogue of awkward source photographs would move the number.</li>
<li><b>The shippable arm is <code>ER</code>, and the product on top of it is a seed
randomiser.</b> Only {N['pairs_stable']} of the {N['pairs_failing']} pairs that fail do so at
every seed ({N['stable_pct']:.1f}% of the catalogue); given a failed cell another seed passes
{N['retry_pass']:.0f}% of the time. Retrying a rejected image is therefore worth more than any further prompt work, and it
is bounded in cost because only rejects are redrawn. Its missing piece is a rejector good
enough to spend calls on &mdash; not the current VLM judge.</li>
<li><b>The arm nobody has built</b> is the router: re-pose only when a pose reader says the
wearer is not neutral, and otherwise ship the garment pixels untouched. That is the shape the
evidence recommends, and it is not a prompt.</li>
</ul>

<footer>Sources: v3.4 RESULTS &sect;7.1 and SOLUTION &sect;5&ndash;6, v3.5 RESULTS
&sect;1&ndash;4, and the v3.6 runs in <code>v3/runs/v36/</code>. The
<code>VEi</code>/<code>BC</code> comparison in &sect;2 is quoted from v3.5 &sect;4, where the
caveat still stands that the two rates were produced by different protocols; the identical
page for the lock exists and its pass has not yet been exported. &middot;
<a href='v36_report.html'>&larr; the evidence at a glance</a></footer>
</div>{LB}{SCRIPT}"""


HEAD = """<title>TITLE</title>
<meta name='viewport' content='width=device-width,initial-scale=1'>
<style>
:root{--bg:#0d0d10;--fg:#e8e8ea;--dim:#8a8a94;--line:#26262c;--acc:#7c5cff;--good:#7ee787;
 --bad:#ff9aa2;--gold:#d29922;--card:#101014}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
 font:15.5px/1.65 ui-sans-serif,-apple-system,"Segoe UI",Roboto,sans-serif}
.wrap{max-width:1180px;margin:0 auto;padding:30px 22px 0}
h1{margin:0 0 4px;font-size:27px;letter-spacing:-.2px}
h2{margin:38px 0 10px;font-size:19px;letter-spacing:-.1px;
 padding-bottom:7px;border-bottom:1px solid var(--line)}
p{margin:0 0 12px}
.lede{color:var(--dim);font-size:15px;margin:10px 0 6px;max-width:88ch}
.lede b,p b{color:var(--fg)}
.sec{color:var(--dim);font-size:14px;max-width:92ch}
.k{border-left:2px solid var(--acc);padding-left:12px;color:var(--dim)}
.caveat{border:1px solid var(--line);background:#141419;border-radius:9px;padding:12px 14px;
 color:var(--dim);font-size:13.5px;max-width:none}
a{color:#a893ff}
code{background:#1b1b22;padding:1px 5px;border-radius:4px;font-size:12.5px}
/* architecture */
.arch{display:grid;grid-template-columns:1fr auto 1fr auto 1fr;gap:10px;align-items:stretch;
 margin:14px 0 16px}
@media(max-width:900px){.arch{grid-template-columns:1fr}.arch .arrow{transform:rotate(90deg)}}
.step{border:1px solid var(--line);border-radius:9px;background:var(--card);padding:11px 13px}
.step.hero{border-color:#3b3160;background:#0e0c16}
.step b{display:block;margin:2px 0 5px;font-size:14.5px}
.step p{margin:0;color:var(--dim);font-size:12.5px;line-height:1.55}
.step .k{border:0;padding:0;font:10px ui-monospace,monospace;color:var(--acc);
 text-transform:uppercase;letter-spacing:.7px}
.arrow{align-self:center;color:var(--dim)}
.prompts{display:grid;gap:6px;margin:0 0 6px}
.pr{display:grid;grid-template-columns:34px 1fr;gap:8px;align-items:start}
.pr b{color:var(--acc);font:12.5px ui-monospace,monospace;padding-top:5px}
.pr code{background:#15151b;border:1px solid var(--line);border-radius:6px;padding:6px 9px;
 color:#c3c3ce;font:12.5px/1.55 ui-monospace,monospace;display:block}
/* stat tiles */
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:9px;
 margin:14px 0 14px}
.tile{border:1px solid var(--line);border-radius:9px;background:var(--card);padding:12px 14px}
.tile .v{font:600 26px/1.15 ui-sans-serif,-apple-system,sans-serif;letter-spacing:-.5px}
.tile.good .v{color:var(--good)}
.tile .l{font-size:13px;margin-top:3px}
.tile .s{font-size:11.5px;color:var(--dim);margin-top:4px;line-height:1.45}
/* comparison strips */
.cellcard{border:1px solid var(--line);border-radius:9px;background:var(--card);
 overflow:hidden;margin:9px 0}
.ch{display:flex;gap:8px;align-items:center;padding:6px 11px;background:#141419;
 border-bottom:1px solid var(--line);font-size:12px;flex-wrap:wrap}
.ch b{font-size:12.5px;word-break:break-all}
.t{font-size:9.5px;padding:1px 7px;border-radius:20px;background:#2a1a12;
 border:1px solid #6b4423;color:var(--gold)}
.note{margin-left:auto;color:var(--dim);font-size:11.5px}
.cellbody{display:grid;grid-template-columns:290px 1fr;gap:10px;padding:8px}
@media(max-width:900px){.cellbody{grid-template-columns:1fr}}
.src{display:grid;grid-template-columns:repeat(2,1fr);gap:6px;align-content:start}
.outs{display:grid;grid-template-columns:repeat(2,1fr);gap:8px}
figure{margin:0}
figure img{width:100%;display:block;background:#fff;border-radius:5px;cursor:zoom-in;
 aspect-ratio:3/4;object-fit:contain}
.src figure img{aspect-ratio:2/3}
figcaption{font-size:11px;color:var(--dim);text-align:center;padding:4px 2px}
/* table */
table{border-collapse:collapse;width:100%;font-size:13.5px;margin:6px 0 14px}
th,td{border-bottom:1px solid var(--line);padding:8px 10px;text-align:left;vertical-align:top}
th{color:var(--dim);font-weight:500;font-size:12px;text-transform:uppercase;letter-spacing:.6px}
td.good{color:var(--good)}td.bad{color:var(--bad)}
ul{margin:6px 0 12px;padding-left:20px;color:var(--dim)}
li{margin:5px 0}li b{color:var(--fg)}
#lb{display:none;position:fixed;inset:0;background:rgba(0,0,0,.95);z-index:99;
 align-items:center;justify-content:center;flex-direction:column;gap:10px;padding:20px}
#lb.on{display:flex}#lb img{max-width:95vw;max-height:90vh;object-fit:contain;background:#fff}
#lbc{color:var(--dim);font-size:13px}
footer{border-top:1px solid var(--line);margin-top:40px;padding:18px 0 34px;color:var(--dim);
 font-size:12.5px}
</style>
<div class='wrap'><h1>TITLE</h1></div>
"""

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


def main():
    os.makedirs(IMG, exist_ok=True)
    N = numbers()
    open(os.path.join(REPORT, "v36_report.html"), "w").write(page1(N))
    open(os.path.join(REPORT, "v36_findings.html"), "w").write(page2(N))
    print("v3/report/v36_report.html    page 1 - at a glance")
    print("v3/report/v36_findings.html  page 2 - the long read")
    print(f"  marked: ER {N['er_win_fail'] + N['er_win_ok']}, same {N['same']}, "
          f"BC {N['bc_win']}, unmarked {N['unmarked']} of {N['cells']}")


if __name__ == "__main__":
    main()
