# The long report. One leg per decision: what was tried, what failed, what it cost,
# what it led to. Negative results carry equal weight -- knowing the deterministic
# gate is a coin flip is most of what the 44 hours bought.
import csv, glob, html, json, os

import report_assets as A

REPO, OUT, NL = A.REPO, A.OUT, chr(10)
CROP = f"{REPO}/v2/runs/crop_screen"
GEN = f"{REPO}/v2/runs/amt/gen"

CSS = """
:root{--bg:#0d0d10;--fg:#e8e8ea;--dim:#8a8a94;--line:#26262c;--acc:#7c5cff;
 --good:#3fb950;--mid:#d29922;--bad:#f85149}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
 font:15px/1.65 ui-sans-serif,-apple-system,"Segoe UI",Roboto,sans-serif}
a{color:var(--acc)}
header{padding:40px 30px 26px;border-bottom:1px solid var(--line)}
.wrap{max-width:1060px;margin:0 auto;padding:0 30px}
h1{margin:0 0 8px;font-size:29px;letter-spacing:-.3px}
h2{font-size:22px;margin:52px 0 4px;padding-top:14px;border-top:1px solid var(--line)}
h2 .leg{color:var(--acc);font-size:12.5px;display:block;text-transform:uppercase;
 letter-spacing:1px;margin-bottom:5px}
h3{font-size:15.5px;margin:24px 0 4px;color:#cfcfd6}
p{max-width:80ch}
.lede{color:var(--dim);max-width:78ch}
.dim{color:var(--dim)}
.q{border-left:3px solid var(--acc);padding:2px 0 2px 14px;margin:16px 0;
 max-width:82ch}
.q b{color:#fff}
.kill{border-left:3px solid var(--bad);padding:2px 0 2px 14px;margin:16px 0;
 max-width:82ch}
table{border-collapse:collapse;font-size:13.5px;margin:16px 0}
th,td{padding:6px 13px;border-bottom:1px solid #1d1d23;text-align:right}
th:first-child,td:first-child{text-align:left}
th{color:var(--dim);font-weight:600}
tr.win td{background:#111a12}tr.lose td{background:#1a1112}
.good{color:var(--good);font-weight:700}.bad{color:var(--bad);font-weight:700}
.strip{display:flex;gap:6px;overflow-x:auto;padding:6px 0;margin:14px 0}
.strip figure{margin:0;flex:0 0 auto;width:150px}
.strip figure.w{width:230px}
.strip img{width:100%;display:block;background:#fff;border-radius:5px;cursor:zoom-in}
.strip figcaption{font-size:10.5px;color:var(--dim);text-align:center;padding:4px 2px;
 line-height:1.35}
.strip figcaption b{color:var(--fg)}
.fig{margin:18px 0}.fig img{width:100%;border-radius:8px;cursor:zoom-in}
.fig figcaption{font-size:12px;color:var(--dim);padding-top:6px}
.toc{columns:2;column-gap:36px;font-size:13.5px;margin:14px 0 0}
.toc a{display:block;padding:2px 0;text-decoration:none}
.nav{padding:12px 30px;text-align:center;border-bottom:1px solid var(--line);
 background:#121216;font-size:13px}
#lb{display:none;position:fixed;inset:0;background:rgba(0,0,0,.95);z-index:99;
 align-items:center;justify-content:center;flex-direction:column;gap:10px;padding:20px}
#lb.on{display:flex}#lb img{max-width:95vw;max-height:90vh;object-fit:contain;background:#fff}
#lbc{color:var(--dim);font-size:13px}
footer{border-top:1px solid var(--line);margin-top:50px;padding:26px 30px;
 color:var(--dim);font-size:12.5px}
code{background:#1b1b22;padding:1px 5px;border-radius:4px;font-size:12.5px}
"""
JS = """
document.addEventListener('click',e=>{const im=e.target.closest('.strip img,.fig img');
  if(!im)return;
  document.getElementById('lbi').src=im.dataset.full||im.getAttribute('src');
  document.getElementById('lbc').textContent=im.getAttribute('alt');
  document.getElementById('lb').classList.add('on');});
document.getElementById('lb').addEventListener('click',()=>
  document.getElementById('lb').classList.remove('on'));
document.addEventListener('keydown',e=>{if(e.key==='Escape')
  document.getElementById('lb').classList.remove('on')});
"""


def strip(items, wide=False):
    """items: (path, caption, maxw)"""
    out = []
    for p, cap, mw in items:
        a = A.asset(p, mw, hires=True)
        if a:
            full = a.replace(".jpg", "@2x.jpg")
            out.append(f"<figure class='{'w' if wide else ''}'><img src='{a}' "
                       f"data-full='{full}' alt='{html.escape(cap)}'>"
                       f"<figcaption>{cap}</figcaption></figure>")
    return "<div class='strip'>" + "".join(out) + "</div>" if out else ""


def fig(path, cap, mw=1100):
    a = A.asset(path, mw, hires=True)
    if not a:
        return ""
    full = a.replace(".jpg", "@2x.jpg")
    return (f"<div class='fig'><img src='{a}' data-full='{full}' "
            f"alt='{html.escape(cap)}'><figcaption>{cap}</figcaption></div>")


def build():
    run = json.load(open(f"{REPO}/v2/runs/amt/_run.json"))
    T = {(r["set_id"], r["arm"]): r for r in csv.DictReader(
        open(f"{REPO}/v223_perfect_tier_picks.csv"))}
    meta = {r["stem"]: r["src_path"] for r in csv.DictReader(
        open(f"{CROP}/../crop_screen/crop_log.csv"))}
    ps = A.pairs()
    g = lambda sid, arm: f"{GEN}/{run['gen'].get(f'{sid}|{arm}','')}"

    S = []   # sections

    # ---------------- 1 architecture -------------------------------------
    S.append(("1", "What ships", f"""
<p class='lede'>A person photo and a garment reference in; the person wearing that
garment out. Hard constraint: <b>open weights only in the deployed path</b>.</p>
<pre style='background:#111116;border:1px solid var(--line);border-radius:8px;
padding:14px;overflow-x:auto;font-size:12.5px;line-height:1.5'>
person + garment
   │
   ├─ 1 PREPROCESS   BiRefNet matte → SCHP parser → MediaPipe pose → crop
   │
   ├─ 2 ROUTE        hair over garment ≥ 14% → BC_klein  ·  else PHEAD
   │                 caller named a region  → QX
   │
   ├─ 3 GENERATE     FLUX.2 klein 4B distilled, normalised to ~1 MP
   │
   ├─ 4 SCREEN       no-op · identity · degenerate   (free, CPU)
   │                 VLM: garment == FAIL · tryon != PERFECT
   │                 any of these → escalate to QX, take QX
   │
   └─ 5 REALISM      optional. SeedVR2 ×2, Lanczos fallback on identity loss
</pre>
<table><tr><th>over 38 sets</th><th>gen/req</th><th>perfect</th><th>ok</th><th>fail</th></tr>
<tr><td>klein alone, uncropped reference</td><td>1.00</td><td colspan=2 class='dim'>—</td>
<td class='bad'>61% of sets failed</td></tr>
<tr><td>klein + shipped crop (what V1 would have)</td><td>1.00</td><td>23</td><td>5</td><td>10</td></tr>
<tr><td>best single arm, BC_klein</td><td>2.00</td><td>28</td><td>6</td><td>4</td></tr>
<tr class='win'><td><b>the harness</b></td><td><b>2.16</b></td><td class='good'>31</td>
<td>7</td><td class='good'>0</td></tr>
<tr><td class='dim'><i>oracle — a perfect gate</i></td><td class='dim'>1.53</td>
<td class='dim'>32</td><td class='dim'>6</td><td class='dim'>0</td></tr></table>
<div class='q'>Same cost as the best single arm, and <b>nothing ships broken</b>. The
gap to the oracle is 1 perfect frame and 0.6 generations — the harness is close to
the ceiling of what these three arms can do.</div>"""))

    # ---------------- 2 the problem --------------------------------------
    worst = [p for p in ps if len(p["faults"]) >= 3][:3]
    imgs = []
    for p in worst:
        imgs += [(p["garment"], "garment reference<br><b>contains a person</b>", 230),
                 (p["base"], "klein output — " +
                  ", ".join(A.__dict__ and f for f in p["faults"][:2]), 230)]
    S.append(("2", "The problem: the reference contains a person", f"""
<p><b>klein is a strong model, and that is the point.</b> On 13 of 33 reviewed sets
(39%) it produced a correct try-on from the raw reference with no help at all — the
<a href='index.html'>short report</a> shows those first. The 61% below are the edge
cases, not a weak base or a bad prompt: same model, same prompt, same seed
throughout.</p>
<p>Given a garment reference that is itself a photo of someone wearing the garment,
klein fails on <b>61% of sets</b>. Reviewed by eye over 33 sets:</p>
<table><tr><th>failure</th><th>share of sets</th></tr>
<tr><td>wrong clothes</td><td>36%</td></tr>
<tr><td>wrong person — the reference's face arrives in the output</td><td>33%</td></tr>
<tr><td>background repainted</td><td>33%</td></tr>
<tr><td>duplicated person</td><td>15%</td></tr>
<tr><td>no transfer at all</td><td>9%</td></tr></table>
<div class='q'>Those three leading categories at near-identical rates is the
signature of <b>one cause, not three</b>: the model attends to the whole reference
rather than the garment in it. Everything downstream follows from that reading.</div>
{strip(imgs, wide=True)}
<p class='dim'>Evidence: <a href='v221_review.html'>v221_review.html</a>
— 33 sets, per-category annotation.</p>"""))

    # ---------------- 3 choosing the base --------------------------------
    S.append(("3", "Leg 1 — choosing the editing base", """
<p>Five open-weights editors on 13 Testset2 pairs, judged blind. The brief was a
<b>hypothesis per arm</b>, not a leaderboard.</p>
<table><tr><th>arm</th><th>the bet</th><th>outcome</th></tr>
<tr class='win'><td><b>FLUX.2 klein 4B distilled</b></td>
<td>a strong generalist with no weak axis beats a specialist</td>
<td class='good'>chosen — fidelity 4.41, garment 4.08</td></tr>
<tr><td>FASHN VTON v1.5</td><td>pixel-space try-on → best identity</td>
<td>best preservation (id 0.971) but worst garment (3.33); kept as a fallback</td></tr>
<tr class='lose'><td>FireRed-Image-Edit v1.1</td>
<td>an explicit identity-consistency loss in training</td>
<td class='bad'>garment 2.00 — did not transfer at all</td></tr>
<tr class='lose'><td>HiDream-O1</td><td>pixel-native, no VAE round-trip</td>
<td class='bad'>re-renders rather than edits; the <b>only</b> arm to substitute the
reference's person</td></tr>
<tr><td>klein 4B <i>base</i></td><td>base beats distilled</td>
<td>ties on fidelity, loses on garment, ~10× the compute</td></tr></table>
<div class='kill'><b>What this leg actually cost, and bought.</b> Two hypotheses died
on contact — the identity-loss bet and the pixel-native bet. Neither is recoverable
by tuning, and both would have been plausible places to spend another week.</div>
<div class='kill'><b>A mistake worth recording.</b> The automated metric reported
<code>wrong_person = 0.00</code> across all 38 outputs. Human review later found
failures on <b>4 of 7</b> duo pairs — three missed by the metrics <i>and</i> by the
VLM judge. From v2.2 onward human review became the primary judge.</div>
<p class='dim'>Evidence: <a href='v20_arms_ts2.html'>v20_arms_ts2.html</a>,
<a href='v20_klein_variant.html'>v20_klein_variant.html</a>.</p>"""))

    # ---------------- 4 cropping ------------------------------------------
    ref = "p028"
    variants = [(f"{CROP}/{ref}__c1_bbox.jpg", "<b>C1</b> bbox<br>control", 190),
                (f"{CROP}/{ref}__c2_bbox_nobg.jpg", "<b>C2</b> no background<br>wearer kept — 45%", 190),
                (f"{CROP}/{ref}__c32_no_face_keep_hair.jpg", "<b>C3.2</b> face only<br>hair kept — 45%", 190),
                (f"{CROP}/{ref}__c3_no_face.jpg", "<b>C3.1</b> head removed<br><b>75% — shipped</b>", 190),
                (f"{CROP}/{ref}__c4_clothes_only.jpg", "<b>C4</b> clothes only<br>75%, conditional", 190)]
    S.append(("4", "Leg 2 — cropping the person out of the reference", f"""
<p>If the cause is attention, remove what competes for it. Four variants, same
model, same seed, one variable.</p>
{strip(variants)}
<table><tr><th>variant</th><th>solved of 20 baseline failures</th></tr>
<tr><td>C2 — background white, wearer kept</td><td>9 (45%)</td></tr>
<tr><td>C3.2 — face removed, hair kept</td><td>9 (45%)</td></tr>
<tr class='win'><td><b>C3.1 — head removed</b></td><td class='good'>15 (75%)</td></tr>
<tr><td>C4 — clothes only</td><td>15 (75%), only where the cut is clean</td></tr></table>
<div class='kill'><b>C3.2 failed in an instructive way.</b> Removing the face but
keeping the hair made klein read the white gap as fabric — it changed the garment and
in one case the gender. A partial cut is worse than none: it leaves something that
looks like cloth.</div>
<div class='kill'><b>C4 punches holes.</b> Taking only clothing classes drops
anything crossing the garment — hands, bags — leaving voids the model fills with
invention. Equal on rate, worse on failure mode.</div>
<div class='q'><b>Withdrawn.</b> An earlier pass reported ~94% for all four variants
and concluded the rate could not separate them. That counted unjudged annotation
cells as solved. The corrected figures are above.</div>
<p class='dim'>Evidence: <a href='v221_review.html'>v221_review.html</a>,
<a href='progression_grid.html'>progression_grid.html</a>.</p>"""))

    # ---------------- 5 the residual --------------------------------------
    hair = [(f"{CROP}/p021__c32_no_face_keep_hair.jpg", "p021 before the cut", 175),
            (f"{CROP}/p021__c3_no_face.jpg", "p021 after — <b>19.5% of the garment gone</b>", 175),
            (f"{REPO}/v2/runs/phase3/p021__PRE2raw.jpg", "bald first…", 175),
            (f"{CROP}/p016__c3_no_face.jpg", "p016 — 9.7% lost", 175),
            (f"{CROP}/p009__c3_no_face.jpg", "p009 — 7.2% lost", 175)]
    S.append(("5", "Leg 3 — the residual: cropping destroys the garment", f"""
<p>C3.1 solves 75%. The survivors fail for a reason the rate cannot show: <b>removing
the head removes garment with it</b> when hair falls over the clothing.</p>
{strip(hair)}
<table><tr><th>reference</th><th>garment lost</th><th>enclosed</th><th>open</th></tr>
<tr><td class='bad'>p021</td><td class='bad'>19.53%</td><td>0.00%</td><td>19.52%</td></tr>
<tr><td>p028</td><td>11.92%</td><td>0.00%</td><td>11.91%</td></tr>
<tr><td>p016</td><td>9.75%</td><td>1.51%</td><td>7.99%</td></tr>
<tr><td>p009</td><td>7.22%</td><td>0.00%</td><td>7.20%</td></tr></table>
<div class='q'><b>The damage is open, not enclosed</b> — 19.52 of p021's 19.53
points. An enclosed hole is surrounded by known fabric and inpainting is well posed;
an open notch has garment on one side and background on the other, so filling it
means inventing where the garment ends. <b>Treating this as an inpainting problem
would have been a category error</b>, and that observation killed a whole synthetic
test bed before it was built.</div>
<div class='kill'><b>Eight head-detection heuristics failed here.</b> A bald frame
has no hair class, so <code>head = hair + face</code> collapses and half the skull
survives. Each fix traded one reference for another: the pose ellipse missed a scalp
because p016's ears are 9 px apart; "cut above the chin" swept in raised arms, 36% of
the subject; a clothes guard protected 19.5% of p019's head because the parser called
it clothing. <b>Seven iterations each trading one reference for another is a
heuristic at its ceiling, not a tuning problem.</b></div>
<p>Replaced by a <b>human parser</b> (18-class ATR) for the head <i>shape</i>, pose
for the <i>extent</i>, and the nose-connected component to discard stray blobs.
Head removal improved <b>+5.0 points</b> against +0.8–1.2 for the best geometry.</p>"""))

    # ---------------- 6 attention arms ------------------------------------
    ex = "HD_p021"
    arms_imgs = [(meta.get("p021", ""), "the reference<br>19.5% hair damage", 175),
                 (g(ex, "control"), "<b>control</b> C3.1<br>" + T.get((ex, "control"), {}).get("tier", ""), 175),
                 (g(ex, "PHEAD"), "<b>PHEAD</b> free<br>" + T.get((ex, "PHEAD"), {}).get("tier", ""), 175),
                 (g(ex, "BC_klein"), "<b>BC_klein</b> bald→crop<br>" + T.get((ex, "BC_klein"), {}).get("tier", ""), 175),
                 (g(ex, "QX_qwen_p1"), "<b>QX</b> regenerate<br>" + T.get((ex, "QX_qwen_p1"), {}).get("tier", ""), 175)]
    S.append(("6", "Leg 4 — three arms, and why they need each other", f"""
<p>Ten arms were tested against the damaged references; three survived. They differ
by <b>mechanism</b>, and that is what makes them complementary.</p>
{strip(arms_imgs)}
<table><tr><th>arm</th><th>mechanism</th><th>perfect</th><th>ok</th><th>fail</th><th>cost</th></tr>
<tr><td>PHEAD</td><td>subtract — parser head removal</td><td>23</td><td>5</td><td>10</td><td>free</td></tr>
<tr class='win'><td><b>BC_klein</b></td><td>subtract — bald first, then crop</td>
<td class='good'>28</td><td>6</td><td>4</td><td>1 gen</td></tr>
<tr><td>QX</td><td><b>regenerate</b> — Qwen returns the clothing</td><td>20</td><td>17</td>
<td class='good'>1</td><td>1 gen</td></tr></table>
<div class='q'><b>QX has the lowest ceiling and by far the lowest floor</b> — 20
perfect but only 1 failure in 38. It is a safety net, not a quality arm, which is
exactly why it is the escalation target and never the default.</div>
<div class='q'><b>The finding the design rests on.</b> Subtraction cannot recover
what the crop never saw; regeneration cannot reproduce what it never captured. The
two have <b>no shared failure mode</b>, so of PHEAD's 13 hard cases QX rescues 11
where BC_klein rescues 6 — despite BC_klein being the stronger arm alone. <b>A better
arm can be a worse second step.</b></div>
<div class='kill'><b>Dropped:</b> <code>BALD_raw</code> (85% cut — the crop earns its
place), the six face-destruction arms (blur, twirl, pixelate — identity leaks), and
pairing BC_klein with D3B, which scored 13 points <i>below</i> an independence model
because both are bald-based subtraction.</div>
<p class='dim'>Evidence: <a href='failures.html'><b>every failure, per arm, with
what rescued it</b></a> &middot; <a href='v221_attention_mod.html'>v221_attention_mod.html</a>
— 38 sets × 10 arms.</p>"""))

    # ---------------- 7 the gate that failed ------------------------------
    S.append(("7", "Leg 5 — the failure gate that did not work", f"""
<p>With three arms that rescue each other, the remaining question is <b>when to
escalate</b>. The first answer was a deterministic gate: five CPU checks —
degenerate frame, no-op, duplicated people, identity, background.</p>
{fig(f"{REPO}/prd/v2/v2.2/images/gate_vs_human.png",
     "The deterministic gate against 114 blind reviewer judgements. "
     "AUC 0.506 — a coin flip — and no threshold beats accepting every frame.")}
<table><tr><th></th><th>value</th></tr>
<tr><td>mean score, frames judged usable</td><td>0.684</td></tr>
<tr><td>mean score, frames judged unusable</td><td>0.674</td></tr>
<tr class='lose'><td><b>AUC against the reviewer</b></td><td class='bad'>0.506</td></tr>
<tr><td>best agreement at any threshold</td><td>71.1%</td></tr>
<tr class='lose'><td>agreement from accepting everything unchecked</td>
<td class='bad'>71.9%</td></tr></table>
<div class='kill'><b>Not a calibration problem.</b> All 456 outputs are valid
photographs. The failures are semantic — wrong garment, wrong identity, repainted
scene — and pixel statistics cannot see them.</div>
<div class='q'><b>The control that makes it conclusive.</b> The same reviewer graded
the same outputs twice, months apart, under different questions. The two passes agree
95% / 44% / 0% across perfect / ok / fail. The target is stable and reproducible;
the instrument was the problem.</div>
<div class='q'><b>What survived.</b> Two of the five checks ship — not as a score but
as <b>detectors</b>. A no-op and an identity swap both produce a <i>competent,
coherent photograph of the wrong thing</i>, so a semantic judge has nothing to find;
only a numeric comparison against the input reveals them. Over 114 cells the VLM
caught 26 failures they missed, and they caught <b>1</b> the VLM missed — which was
the only frame that would have shipped broken.</div>"""))

    # ---------------- 8 the VLM -------------------------------------------
    S.append(("8", "Leg 6 — the VLM gate, and the question that works", """
<p>An open-weights VLM (Qwen3-VL-8B) was measured over the same 114 cells, in five
different phrasings.</p>
<table><tr><th>prompt</th><th>what it sees</th><th>fires</th><th>accuracy</th>
<th>catches fail</th></tr>
<tr class='lose'><td>artefact</td><td>output</td><td class='bad'>0</td><td>62.3%</td>
<td class='bad'>0%</td></tr>
<tr><td>usable</td><td>output</td><td>4</td><td>62.3%</td><td>13%</td></tr>
<tr><td>tryon</td><td>output</td><td>2</td><td>62.3%</td><td>7%</td></tr>
<tr class='win'><td><b>garment</b></td><td><b>reference + output</b></td><td>35</td>
<td class='good'>70.2%</td><td class='good'>53%</td></tr>
<tr><td>transfer</td><td>person + reference + output</td><td>8</td><td>64.0%</td><td>20%</td></tr>
<tr><td class='dim'><i>accept everything</i></td><td class='dim'>—</td><td>0</td>
<td class='dim'>62.3%</td><td>0%</td></tr></table>
<div class='kill'><b>Asking about artefacts does not work.</b> That prompt answered
CLEAN on all 114 outputs — including every frame marked fail. It never fired once.
Our failures are not artefacts: they are competent photographs of the wrong thing.
This is the same reason the pixel gate failed, arriving from a different
direction.</div>
<div class='q'><b>The architectural result:</b> only the prompt with a reference image
beat the do-nothing baseline. <b>The gate must see the garment reference, not just
the output.</b> Counter-intuitively, adding the <i>person</i> image as well made it
worse — at 8B, three images dilute attention.</div>
<div class='kill'><b>A pairwise "which is better" call was built and dropped.</b> It
agreed with itself on 34% of pairs when the two images were swapped — worse than
chance, so it reads position rather than content — and picked the already-failed arm
2 times in 5. Always taking QX scores 5/5.</div>
<p class='dim'>Evidence: <a href='v223_vlm_eval.html'>v223_vlm_eval.html</a>.</p>"""))

    # ---------------- 9 the harness ---------------------------------------
    S.append(("9", "Leg 7 — the assembled harness", f"""
<p>Router on the input, arm, free checks, VLM, escalate to QX.</p>
{fig(f"{REPO}/prd/v2/v2.2/images/harness_v223.png",
     "The shipped harness. Arm profiles, the cost/quality ladder, the router's "
     "AUC, and why no output-side check separates.")}
<div class='q'><b>Routing turned out to be the half that works and the gate the half
that does not</b> — the reverse of the assumption the workstream began with. A router
reads the <i>input</i>, where a physically meaningful measurement exists:
<code>hair over garment</code> predicts PHEAD failure at <b>AUC 0.862</b>, against
0.38–0.57 for every check that reads the output.</div>
<table><tr><th>configuration</th><th>gen/req</th><th>perfect</th><th>ok</th><th>fail</th></tr>
<tr><td>always PHEAD</td><td>1.00</td><td>23</td><td>5</td><td class='bad'>10</td></tr>
<tr><td>always BC_klein</td><td>2.00</td><td>28</td><td>6</td><td class='bad'>4</td></tr>
<tr><td>router only, no gate</td><td>1.26</td><td>28</td><td>5</td><td class='bad'>5</td></tr>
<tr><td>+ VLM gate</td><td>2.11</td><td>30</td><td>7</td><td>1</td></tr>
<tr class='win'><td><b>+ identity check (shipped)</b></td><td><b>2.16</b></td>
<td class='good'>31</td><td>7</td><td class='good'>0</td></tr></table>
<div class='kill'><b>The last failure was found by eye, not by a metric.</b> A
spot-check of one frame showed the person substituted entirely — a man with short
auburn hair in, a woman with long dark hair out. All five VLM prompts passed it. The
identity check had scored it 0.755 and the escalation rule was not consulting
identity, because an earlier analysis had measured it at the wrong threshold and
written it off. Adding it removed the last shipped failure.</div>
<p class='dim'>Evidence: <a href='v223_harness_picks.html'>v223_harness_picks.html</a>
— every set, with the full decision trace.</p>"""))

    # ---------------- 10 realism ------------------------------------------
    rl = json.load(open(f"{REPO}/v2/runs/realism/_realism.json"))
    k0 = sorted(rl)[0]
    S.append(("10", "Leg 8 — realism, made an option", f"""
<p>SeedVR2 ×2 upscale, chosen in v2.1, applied for the first time to a harness
output.</p>
{strip([(rl[k0]['src'], "before", 230),
        (os.path.join(REPO, rl[k0]['after']), "after — SeedVR2 ×2", 230)], wide=True)}
<table><tr><th></th><th>value</th></tr>
<tr><td>resolution</td><td>832×1248 → 1664×2496</td></tr>
<tr><td>mean absolute pixel change</td><td>2.28 / 255</td></tr>
<tr><td>high-frequency gain</td><td>×1.12</td></tr>
<tr class='lose'><td>frames below 0.90 identity</td><td class='bad'>7 of 38</td></tr>
<tr class='lose'><td>worst identity</td><td class='bad'>0.772</td></tr></table>
<div class='kill'><b>Run unconditionally it costs identity</b> — worst case 0.772,
inside the range that got Z-Image Turbo eliminated in v2.1, where this same
configuration measured 0.943.</div>
<div class='q'><b>The tell is free.</b> The frames that lose identity are the frames
SeedVR2 <i>failed to sharpen</i> — where the high-frequency ratio is below 1, mean
identity is 0.891 against 0.941 elsewhere. The failure announces itself, so a
post-hoc check suffices and no predictive model is needed.</div>
<p>Shipped as <b>off by default</b>, serving one request — <i>give me a
high-resolution image</i>. The identity floor decides <b>how</b> to upscale, never
whether: a failure falls back to a deterministic Lanczos ×2, which still delivers
the resolution asked for.</p>
<p class='dim'>Evidence: <a href='v223_realism_pass.html'>v223_realism_pass.html</a>
— 38 before/after wipes, zoom to 12×.</p>"""))

    # ---------------- 11 parity -------------------------------------------
    # Leg 9 (self-hosted parity) is deliberately NOT a section. The run happened
    # and it passed on the numbers that matter -- router agreed 8/8, shipped quality
    # identical -- but the images were produced with the realism stage falling back
    # to Lanczos x2 and klein running at ~28 steps with CFG instead of the 4 steps
    # and guidance 1.0 its card documents. They look worse than the model actually
    # is, and showing them would misrepresent the result in the wrong direction.
    # Re-verify, then restore. The claim is not dropped, only moved to section 12
    # under what is not done, so the report never implies parity it has not shown.

    # ---------------- 12 cost / licence -----------------------------------
    S.append(("11", "Cost, licences, run time", """
<h3>Licences — every component in the deploy path</h3>
<table><tr><th>role</th><th>model</th><th>licence</th><th>weights</th></tr>
<tr><td>subject matte</td><td>BiRefNet_lite</td><td>MIT</td><td>0.2 GB</td></tr>
<tr><td>human parser</td><td>SCHP ATR</td><td>MIT</td><td>0.3 GB</td></tr>
<tr><td>pose</td><td>MediaPipe Pose lite</td><td>Apache-2.0</td><td>6 MB</td></tr>
<tr><td>identity</td><td>AuraFace-v1</td><td>Apache-2.0</td><td>0.4 GB</td></tr>
<tr class='win'><td>editor</td><td><b>FLUX.2 klein 4B distilled</b></td>
<td class='good'>Apache-2.0</td><td>16 GB</td></tr>
<tr><td>gate</td><td>Qwen3-VL-8B-Instruct</td><td>Apache-2.0</td><td>17.5 GB</td></tr>
<tr><td>extractor</td><td>Qwen-Image-Edit-2511</td><td>Apache-2.0</td><td>57.7 GB</td></tr>
<tr><td>realism</td><td>SeedVR2-3B</td><td>Apache-2.0</td><td>14.6 GB</td></tr></table>
<div class='kill'><b>One dependency was non-commercial and was replaced.</b>
<code>mattmdjaga/segformer_b2_clothes</code>, the original human parser, carries
NVIDIA's SegFormer licence: <i>"only may be used… non-commercially."</i> The risk had
been recorded as a dataset question; the binding constraint was the model licence,
on the card the whole time. Swapped for SCHP (MIT), which emits the same 18 classes —
crop IoU 0.999 against the old references, so no number moved.</div>
<div class='q'>klein <b>4B</b> is Apache-2.0; the 9B sibling is <b>not</b>. Do not let
anyone upgrade it. Similarly, insightface's code is MIT but its default model packs
are non-commercial — the pipeline pins AuraFace explicitly.</div>
<h3>Run time and cost</h3>
<table><tr><th></th><th>value</th></tr>
<tr><td>generations per request</td><td>2.16</td></tr>
<tr><td>per generation, hosted</td><td>~$0.015</td></tr>
<tr><td>gate — two VLM calls</td><td>~$0.0006 (≈2% of pipeline cost)</td></tr>
<tr><td>deterministic stack</td><td>free, CPU</td></tr>
<tr><td>at 1M requests/month, hosted</td><td>~$19.5k</td></tr>
<tr><td>at 1M requests/month, self-hosted</td><td>~$3–11k <span class='dim'>(the
measured 75 s/generation is on a rented L4 with CPU offload, not serving
hardware — a real figure needs a resident model)</span></td></tr>
<tr><td colspan=2 class='dim'>Total spend building all of V2: <b>≈ $21 of fal</b> plus
~$3 of judging.</td></tr></table>
<h3>What is not done</h3>
<ul class='dim'>
<li><b>SeedVR2 self-hosted</b> — weights are Apache-2.0 and downloadable, but its
inference path needs apex, flash-attn and is documented video-only against an
H100-80G baseline. fal wraps it per-image. Alternatives with a clean single-image
path (Real-ESRGAN, AuraSR-v2) are the cheaper route. The stage is off by default, so
this blocks nothing.</li>
<li><b>BC_klein and QX reference-building for unseen garments</b> — wired, verified
for PHEAD, but the two generative preprocessing steps have not been exercised outside
the original run scripts. ~$0.06 to prove.</li>
<li><b>Self-hosted parity — run, and being re-verified.</b> The whole harness was
executed on weights downloaded from Hugging Face. The numbers that matter passed:
the router agreed on <b>8 of 8</b> sets and the shipped quality was identical
(7 perfect / 1 ok / 0 fail on both). But that run had the realism stage falling
back to a Lanczos ×2 upscale, and klein running at diffusers' ~28-step CFG default
rather than the <b>4 steps at guidance 1.0</b> its own model card documents — so
the images look worse than the model is. Both are fixed; the visual comparison is
being redone before it is published. <b>Every image in this report is a fal
output.</b></li>
<li><b>Throughput and concurrency</b> — untested.</li>
<li><b>n = 38, one reviewer, one seed.</b> Directional. Several thresholds are fitted
on the same data they are evaluated on, notably the 14% router cut.</li>
</ul>"""))

    toc = "".join(f"<a href='#s{i}'>{i} &middot; {t}</a>" for i, t, _ in S)
    body = "".join(
        f"<h2 id='s{i}'><span class='leg'>section {i}</span>{t}</h2>{c}" for i, t, c in S)
    doc = NL.join([
        "<title>V2 virtual try-on — full report</title>",
        "<meta name='viewport' content='width=device-width,initial-scale=1'>",
        "<style>" + CSS + "</style>",
        "<header><div class='wrap'><h1>V2 virtual try-on — how it was built</h1>"
        "<p class='lede'>Every decision, the evidence for it, and the things that did "
        "not work. The negative results are deliberate: knowing that a deterministic "
        "gate is a coin flip, and that asking a VLM about artefacts never fires, is "
        "most of what this cost.</p>"
        f"<div class='toc'>{toc}</div></div></header>",
        "<div class='nav'><a href='index.html'>&larr; the short version</a> "
        "&middot; the long version &middot; "
        "<a href='failures.html'>every failure &rarr;</a></div>",
        "<div class='wrap'>" + body + "</div>",
        "<div id='lb'><img id='lbi' alt=''><div id='lbc'></div></div>",
        "<footer><div class='wrap'>Human review is the verdict throughout. Five times "
        "an instrument said the opposite of the truth and a person looking at one "
        "image caught it — no-op outputs scoring perfectly on identity, a "
        "garment-lost metric collapsing by construction, furniture inside every crop, "
        "an identity check written off at the wrong threshold, and a parity run "
        "reporting 62% agreement that was measuring its own bugs.</div></footer>",
        "<script>" + JS + "</script>"])
    os.makedirs(OUT, exist_ok=True)
    o = os.path.join(OUT, "deep.html")
    open(o, "w", encoding="utf-8").write(doc)
    return o, len(S)


if __name__ == "__main__":
    print(build())
