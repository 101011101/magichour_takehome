"""Build v3/report/artefacts.html from the v3/artefacts bundle.

Reads manifest.json, copies web-sized images into v3/report/img/, and writes the
side-by-side page: reference chain, four arms, and the defect region magnified.
Deterministic, no API calls, safe to re-run. Edit this, never the HTML.
"""
import json
import os

from PIL import Image

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
BUNDLE = os.path.join(REPO, "v3", "artefacts")
REPORT = os.path.join(REPO, "v3", "report")
IMG = os.path.join(REPORT, "img")

# Fractional (x0, y0, x1, y1) on the 832x1248 outputs — where the defect lives.
ZOOM = {
    "p015+p007": (0.00, 0.30, 0.40, 0.66),
    "dualuse_navy_peacoat_onmodel+p012": (0.25, 0.00, 0.76, 0.40),
    "HD_p023": (0.15, 0.05, 0.85, 0.82),
    "HD_p023+p019": (0.02, 0.02, 0.58, 0.66),
}

CASES = {
    "p015+p007": {
        "title": "p015 + p007",
        "hair": "4.5%",
        "klass": "render artefact",
        "zoom_note": "The armhole, same crop on all three. BC_klein dissolves the sleeve "
                     "edge into the shoulder as a soft translucent wedge; PHEAD ends it at a "
                     "defined edge and QX at a fold. This is the only one of the four that is a "
                     "render defect in the ordinary sense.",
        "body": """Hair damage is <b>4.5%</b> — low enough that the bald pass buys nothing, and
        <b>PHEAD, which is the same crop without that call, is perfect on this set</b>. The extra
        klein pass re-rendered the reference and softened its edges, and the softened edge is what
        was copied. BC_klein's cheapest failure is caused by a generation it did not need to
        make.""",
    },
    "dualuse_navy_peacoat_onmodel+p012": {
        "title": "navy peacoat model + p012",
        "hair": "14.0%",
        "klass": "garment geometry",
        "zoom_note": "The collar, on all three outputs at the same crop. BC_klein has "
                     "none and a stretched bare neck; PHEAD manages a shallow band; QX renders "
                     "the full stand collar. The three references differ in exactly that way — "
                     "BC's cuts flat through the neck just above the collar and leaves a stub.",
        "body": """The transfer happens; the garment is wrong. This is the over-cut V2 already
        logged — <i>&ldquo;head removal takes the collar on several worn references&rdquo;</i> — appearing
        in a shipped arm rather than in a discarded crop iteration. The boundary of the mask
        became a design feature of the clothing.""",
    },
    "HD_p023": {
        "title": "floral kimono model + p023",
        "hair": "16.9%",
        "klass": "no-op",
        "zoom_note": "Nothing to magnify — the output is the input. BC_klein and PHEAD both "
                     "leave her in her own kimono; QX, same person, same seed, transfers the "
                     "tank and skirt.",
        "body": """SSIM against the person input is <b>0.982</b>: klein returned the photograph it
        was given. After the head cut the reference is a seated figure in profile, mostly bare
        arm and thigh, garment a minority of a low-contrast frame — and the garment is
        <b>nude-coloured, the same value as the skin it is worn on</b>. There is no garment
        silhouette in it to find.""",
    },
    "HD_p023+p019": {
        "title": "p019 + p023",
        "hair": "16.9%",
        "klass": "near no-op",
        "zoom_note": "BC_klein and PHEAD both leave the person in her own cream turtleneck. "
                     "QX is the only arm that moves the neckline at all, and it still reaches "
                     "only ok — the one set in 38 no arm solves.",
        "body": """The same reference, a different person, the same outcome: the cream fleece
        jacket stays. <b>Failure is a property of the garment, not the pairing</b> — which is what
        makes it worth fixing at the reference rather than at the output.""",
    },
}

ORDER = ["p015+p007", "dualuse_navy_peacoat_onmodel+p012", "HD_p023", "HD_p023+p019"]
# (manifest key, arm key in human_tiers, label)
ARMS = [("10_out_BC_klein.jpg", "BC_klein", "BC_klein"),
        ("11_out_PHEAD.jpg", "PHEAD", "PHEAD"),
        ("12_out_QX.jpg", "QX_qwen_p1", "QX"),
        ("13_out_control.jpg", "control", "control")]
TIER_CLS = {"fail": "fail", "perfect": "win", "ok": ""}


def web(src, dst, box=None, w=760):
    im = Image.open(src).convert("RGB")
    if box:
        W, H = im.size
        im = im.crop((int(W * box[0]), int(H * box[1]), int(W * box[2]), int(H * box[3])))
    if im.width > w:
        im = im.resize((w, int(im.height * w / im.width)), Image.LANCZOS)
    im.save(os.path.join(IMG, dst), quality=88, optimize=True)
    return "img/" + dst


def fig(src, cap, cls=""):
    return (f"<figure class='{cls}'><img src='{src}' alt='{cap}'>"
            f"<figcaption>{cap}</figcaption></figure>")


def main():
    os.makedirs(IMG, exist_ok=True)
    man = json.load(open(os.path.join(BUNDLE, "manifest.json")))
    cases = {c["set_id"]: c for c in man["cases"]}

    out = [HEAD]
    out.append("<div class='wrap'>")
    out.append(SUMMARY)

    # Summary table, numbers straight from the manifest.
    rows = []
    for sid in ORDER:
        c, m = cases[sid], cases[sid]["metrics"]
        t = c["human_tiers"]
        rows.append(
            f"<tr><td><a href='#{slug(sid)}'>{CASES[sid]['title']}</a></td>"
            f"<td>{CASES[sid]['hair']}</td><td class='l'>{CASES[sid]['klass']}</td>"
            f"<td class='bad'>{t['BC_klein']}</td>"
            f"<td class='{'bad' if t['PHEAD'] == 'fail' else 'mid'}'>{t['PHEAD']}</td>"
            f"<td class='{'good' if t['QX_qwen_p1'] == 'perfect' else 'mid'}'>{t['QX_qwen_p1']}</td>"
            f"<td>{m['ssim_out_vs_person']['BC_klein']:.3f}</td></tr>")
    out.append("<table><tr><th>set</th><th>hair</th><th>defect class</th><th>BC_klein</th>"
               "<th>PHEAD</th><th>QX</th><th>SSIM vs person</th></tr>"
               + "".join(rows) + "</table>")
    out.append(MECHANISM)

    for sid in ORDER:
        c, meta = cases[sid], CASES[sid]
        p, m = c["paths"], c["metrics"]

        def cp(key, box=None, w=760):
            return web(os.path.join(REPO, p[key]), f"{slug(sid)}_{key}", box, w)

        out.append(f"<h2 id='{slug(sid)}'><span class='m'>{meta['klass']}</span>"
                   f"{meta['title']}<span class='sub'> · hair {meta['hair']} · "
                   f"BC_klein <b class='bad'>{c['human_tiers']['BC_klein']}</b></span></h2>")
        out.append(f"<p class='note'>{meta['body']}</p>")

        out.append("<div class='lab'>the reference chain — what call 2 was actually shown</div>")
        out.append("<div class='strip s5'>"
                   + fig(cp("01_person.jpg", w=420), "person (input)")
                   + fig(cp("02_garment_src.jpg", w=420), "garment reference")
                   + fig(cp("03_bald_call1.jpg", w=420), "call 1 — bald")
                   + fig(cp("04_ref_BC_klein.jpg", w=420),
                         f"BC_klein ref — call 2 saw this", "fail")
                   + fig(cp("06_ref_QX.jpg", w=420), "QX ref — regenerated", "win")
                   + "</div>")

        out.append("<div class='lab'>the four arms, same person, same seed</div>")
        out.append("<div class='strip s4'>" + "".join(
            fig(cp(key, w=460),
                f"{lbl} — {c['human_tiers'].get(arm, 'basic crop')}",
                TIER_CLS.get(c["human_tiers"].get(arm, ""), ""))
            for key, arm, lbl in ARMS) + "</div>")

        z = ZOOM[sid]
        out.append(f"<div class='lab'>magnified — {meta['zoom_note']}</div>")
        # Same box on all three outputs — identical 832x1248 canvases, so the
        # comparison is like for like. The person photo is not cropped with them.
        out.append("<div class='strip s3'>" + "".join(
            fig(web(os.path.join(REPO, p[key]), f"{slug(sid)}_z_{arm}.jpg", z, 620),
                f"{lbl} — {c['human_tiers'][arm]}", TIER_CLS[c["human_tiers"][arm]])
            for key, arm, lbl in ARMS[:3]) + "</div>")

        out.append(f"<div class='paths'>bundle: <code>v3/artefacts/cases/{sid}/</code></div>")

    out.append(TAIL)
    out.append("</div>" + LIGHTBOX)
    open(os.path.join(REPORT, "artefacts.html"), "w").write("\n".join(out))
    print(f"v3/report/artefacts.html  ({len(os.listdir(IMG))} images)")


def slug(s):
    return s.replace("+", "_").replace(".", "_")


HEAD = """<title>Why BC_klein needs QX</title>
<meta name='viewport' content='width=device-width,initial-scale=1'>
<style>
:root{--bg:#0d0d10;--fg:#e8e8ea;--dim:#8a8a94;--line:#26262c;--acc:#7c5cff;
 --good:#3fb950;--mid:#d29922;--bad:#f85149}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
 font:15px/1.6 ui-sans-serif,-apple-system,"Segoe UI",Roboto,sans-serif}
a{color:var(--acc)}
header{padding:36px 30px 24px;border-bottom:1px solid var(--line)}
.wrap{max-width:1180px;margin:0 auto;padding:0 30px}
h1{margin:0 0 8px;font-size:26px;letter-spacing:-.3px}
.lede{color:var(--dim);max-width:82ch;font-size:14px}
.lede b{color:var(--fg)}
h2{font-size:20px;margin:52px 0 6px;padding-top:16px;border-top:1px solid var(--line)}
h2 .m{font-size:12px;color:var(--dim);font-weight:400;text-transform:uppercase;
 letter-spacing:1px;display:block;margin-bottom:4px}
h2 .sub{font-size:13px;color:var(--dim);font-weight:400}
h3{font-size:16px;margin:38px 0 6px}
table{border-collapse:collapse;font-size:13px;margin:16px 0}
th,td{padding:6px 12px;border-bottom:1px solid #1d1d23;text-align:right}
th:first-child,td:first-child,td.l,th.l{text-align:left}
th{color:var(--dim);font-weight:600}
.bad{color:var(--bad);font-weight:700}.good{color:var(--good);font-weight:700}
.mid{color:var(--mid)}
.q{border-left:3px solid var(--acc);padding:2px 0 2px 14px;margin:18px 0;max-width:86ch}
.q b{color:#fff}
.note{max-width:86ch;font-size:14px;color:#c8c8d0;margin:10px 0 18px}
.note b{color:var(--fg)}
.lab{font-size:11px;text-transform:uppercase;letter-spacing:1.1px;color:var(--dim);
 margin:20px 0 7px;max-width:92ch;line-height:1.7;text-transform:none;
 font-size:12.5px;letter-spacing:0}
.strip{display:grid;gap:5px;margin-bottom:6px}
.s5{grid-template-columns:repeat(5,1fr)}
.s4{grid-template-columns:repeat(4,1fr)}
.s3{grid-template-columns:repeat(3,1fr)}
@media(max-width:900px){.s5,.s4{grid-template-columns:repeat(2,1fr)}
 .s3{grid-template-columns:1fr}}
figure{margin:0}
figure img{width:100%;display:block;background:#fff;border-radius:5px;cursor:zoom-in}
figcaption{font-size:11px;color:var(--dim);text-align:center;padding:5px 2px;
 line-height:1.35}
figure.fail img{outline:2px solid var(--bad);outline-offset:-2px}
figure.fail figcaption{color:var(--bad);font-weight:700}
figure.win img{outline:2px solid var(--good);outline-offset:-2px}
figure.win figcaption{color:var(--good);font-weight:700}
.paths{font-size:11.5px;color:var(--dim);margin:10px 0 0}
code{background:#1b1b22;padding:1px 5px;border-radius:4px;font-size:12.5px}
#lb{display:none;position:fixed;inset:0;background:rgba(0,0,0,.95);z-index:99;
 align-items:center;justify-content:center;flex-direction:column;gap:10px;padding:20px}
#lb.on{display:flex}#lb img{max-width:95vw;max-height:90vh;object-fit:contain;background:#fff}
#lbc{color:var(--dim);font-size:13px}
footer{border-top:1px solid var(--line);margin-top:48px;padding:24px 30px;
 color:var(--dim);font-size:12.5px}
</style>
<header><div class='wrap'><h1>Why BC_klein needs QX</h1>
<p class='lede'>The four sets in 38 where <b>BC_klein failed and QX rescued it</b> — the
scoreboard V3 is measured against. Each case shows the reference chain that produced the
failure, all four arms on the same person and seed, and the defect region magnified.
<b>The claim being shown: three of the four are not render artefacts at all, and every one
of them is the crop's cut boundary reappearing in the output.</b></p></div></header>
"""

SUMMARY = """<div class='q'><b>klein treats image 2 as a picture to imitate, not as a garment
to parse.</b> Whatever the subtractive crop leaves at its boundary is reproduced in the output —
a flat neck cut becomes a missing collar, an alpha fringe becomes a hem that dissolves, and a
crop with no garment silhouette left in it produces no edit at all. QX regenerates the garment
onto white, so its reference has no cut boundary to copy. That is the entire reason the two
arms have <b>zero overlapping failures</b>.</div>"""

MECHANISM = """<div class='q'>Read the SSIM column first, and then stop reading it.
<b>HD_p023 at 0.982 is klein handing back the photograph it was given</b> — not a bad edit, no
edit. That is the only thing this number separates: on the other three cases all four arms sit
within 0.01 of each other, failure and rescue alike. A global SSIM finds no-ops and nothing
else.</div>
<div class='q'>HD_p023 and HD_p023+p019 are the <b>same garment reference against two different
people</b> — the 02&ndash;07 files in those two bundles are byte-identical — and both fail the
same way. That is the evidence for the V2 finding that <b>failure is a property of the garment,
not the pairing</b>, which is why it is worth fixing at the reference rather than at the
output.</div>
<p class='note'>One measurement was tried here and did not survive, which is worth stating
rather than quietly dropping. The intuition was that a subtractive crop is mostly bare skin
where a regenerated reference is mostly garment, so a chroma skin test over the references
should separate them. It does not. On <code>p023</code> every reference scores 0.91&ndash;0.99
including QX's, because that garment is nude-coloured and a coarse YCrCb box cannot tell a
beige tank from the arm wearing it. On <code>p007</code> QX scores a clean 0% — but so would
anything, since its non-white pixels are near-achromatic cream. Only <code>p012</code>, a dark
navy, gives a number that means what it looks like. <b>The metric is in the manifest and carries
no signal; the argument on this page rests on the frames.</b> That <code>p023</code> defeats it
is itself the case restating itself — the garment is the same value as the skin it is worn on,
so after the head cut the crop is a low-contrast field with no silhouette in it.</p>"""

TAIL = """<h3>What QX costs, and why this is not simply &ldquo;use QX&rdquo;</h3>
<p class='note'>QX takes all four: perfect, perfect, perfect, ok. It is also
<b>20 perfect / 17 ok / 1 fail</b> over the same 38 sets — the lowest ceiling of any arm.
Regeneration invents detail: hue drifts <b>21&ndash;30&deg; on every reference</b> (worst
<code>p009</code> at <b>88&deg;</b>), pattern retention falls to <b>&times;0.23</b> on
<code>p030</code>, and only <code>p019</code> and <code>p028</code> come back clean.
&ldquo;No extraction arm currently returns the same garment.&rdquo; The reviewer preferred the
Qwen crops by eye <i>while they were losing half the pattern</i> — cleanest-looking and most
faithful pull apart. V3's shape&nbsp;1, klein as the extractor, inherits that trade, and
klein's own extraction quality has never been measured; the numbers above are Qwen's.</p>
<h3>Nothing caught any of these</h3>
<p class='note'>From <code>v223_vlm_eval.csv</code>, the gate's verdicts on these exact four
BC_klein outputs:</p>
<table><tr><th>set</th><th>artefact</th><th>usable</th><th>tryon</th><th>transfer</th>
<th>garment</th><th>human</th></tr>
<tr><td>p015+p007</td><td>CLEAN</td><td>OK</td><td class='good'>PERFECT</td><td>OK</td>
<td>OK</td><td class='bad'>fail</td></tr>
<tr><td>navy_peacoat+p012</td><td>CLEAN</td><td>OK</td><td class='good'>PERFECT</td>
<td class='bad'>FAIL</td><td class='bad'>FAIL</td><td class='bad'>fail</td></tr>
<tr><td>HD_p023</td><td>CLEAN</td><td>OK</td><td class='good'>PERFECT</td><td>OK</td>
<td class='bad'>FAIL</td><td class='bad'>fail</td></tr>
<tr><td>HD_p023+p019</td><td>CLEAN</td><td>OK</td><td class='good'>PERFECT</td><td>OK</td>
<td class='bad'>FAIL</td><td class='bad'>fail</td></tr></table>
<p class='note'>The <code>artefact</code> prompt returned <b>CLEAN on all 114 outputs in the
eval</b>, and <code>tryon</code> calls every one of these four perfect. Only
<code>garment</code> — the single prompt that is shown the reference — fires, on three of four.
The case it misses is <code>p015+p007</code>: <b>the one true render artefact is the one every
instrument is blindest to.</b> V3 ships no gate, so it would ship silently. One CPU SSIM against
the person input needs no model and catches <code>HD_p023</code> at 0.982.</p>"""

LIGHTBOX = """<div id='lb'><img id='lbi' alt=''><div id='lbc'></div></div>
<footer><div class='wrap'>Tiers are one reviewer's absolute judgement, unblinded, n=38, one
seed. Analysis: <code>prd/v3/INVESTIGATION.md</code>. Bundle and provenance:
<code>v3/artefacts/manifest.json</code>. Click any image for full resolution.</div></footer>
<script>
document.addEventListener('click',e=>{const im=e.target.closest('figure img');
  if(!im)return;document.getElementById('lbi').src=im.getAttribute('src');
  document.getElementById('lbc').textContent=im.getAttribute('alt');
  document.getElementById('lb').classList.add('on');});
document.getElementById('lb').addEventListener('click',()=>
  document.getElementById('lb').classList.remove('on'));
document.addEventListener('keydown',e=>{if(e.key==='Escape')
  document.getElementById('lb').classList.remove('on')});
</script>"""

if __name__ == "__main__":
    main()
