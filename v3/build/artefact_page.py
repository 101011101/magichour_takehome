"""Build v3/report/artefacts.html from the v3/artefacts bundle.

Reads manifest.json, copies web-sized images into v3/report/img/, and writes the
side-by-side page: reference chain, four arms, and the defect region magnified.
Deterministic, no API calls, safe to re-run. Edit this, never the HTML.
"""
import json
import os
import sys

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
        "klass": "over-attention · render artefact",
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
        "klass": "over-attention · garment geometry",
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
        "klass": "failed attention · returns the input",
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
        "klass": "failed attention · near-unchanged",
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
    out.append(VOCAB)
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

    out.append(qx_section(man))
    out.append(TAIL)
    out.append("</div>" + LIGHTBOX)
    open(os.path.join(REPORT, "artefacts.html"), "w").write("\n".join(out))
    print(f"v3/report/artefacts.html  ({len(os.listdir(IMG))} images)")


def slug(s):
    return s.replace("+", "_").replace(".", "_")


# QX's own failure surface. The one outright fail, then the drift cohort.
QX_FAIL = {"set_id": "p017+p002", "person": "p017", "garment": "p002"}
DRIFT_SHOW = [
    ("p009", "worst recolour of the cohort — the garment comes back a different hue"),
    ("p030", "worst texture loss — the pattern is smoothed away by every arm"),
    ("p021", "the opposite failure — chroma and pattern are <i>invented</i>, not lost"),
    ("p012", "one of the four rescues: QX took this to perfect while losing half the pattern"),
]


def drift_table():
    """Live from v2/runs/acab via the V2 triage script. Not a verdict — a rank."""
    import glob
    sys.path.insert(0, os.path.join(REPO, "v2", "build"))
    import extraction_drift as D
    import cv2
    rows, agg = [], {}
    stems = sorted({os.path.basename(f).split("__")[0]
                    for f in glob.glob(os.path.join(REPO, "v2/runs/acab/*__CTRL.jpg"))})
    for st in stems:
        ctrl = cv2.imread(os.path.join(REPO, f"v2/runs/acab/{st}__CTRL.jpg"))
        row = {"ref": st}
        for arm in ("QX_qwen_p1", "QX_kleind", "QX_kleinb"):
            f = os.path.join(REPO, f"v2/runs/acab/{st}__{arm}.jpg")
            if not os.path.exists(f):
                continue
            d = D.compare(ctrl, cv2.imread(f))
            if d:
                row[arm] = d
                agg.setdefault(arm, []).append(d)
        rows.append(row)
    return rows, agg


def qx_section(man):
    """QX's own failure surface: the one outright fail, then extraction drift."""
    import csv as _csv
    meta = {r["stem"]: r["src_path"] for r in _csv.DictReader(
        open(os.path.join(REPO, "v2/runs/crop_screen/crop_log.csv")))}
    o = [QX_HEAD]

    # 1. The single outright failure.
    sid, per, g = QX_FAIL["set_id"], QX_FAIL["person"], QX_FAIL["garment"]
    src = {"person": meta[per], "garment": meta[g],
           "qxref": f"v2/runs/acab/{g}__QX_qwen_p1.jpg",
           "bcref": f"v2/runs/amt/{g}__BC_klein.jpg",
           "qxout": f"v2/runs/amt/gen/{sid}__QX_qwen_p1.jpg",
           "bcout": f"v2/runs/amt/gen/{sid}__BC_klein.jpg",
           "pheadout": f"v2/runs/amt/gen/{sid}__PHEAD.jpg"}

    def w(k, box=None, width=440):
        return web(os.path.join(REPO, src[k]), f"qxfail_{k}.jpg", box, width)

    o.append("<h2 id='qxfail'><span class='m'>invented detail</span>p017 + p002"
             "<span class='sub'> · hair 1.9% · QX <b class='bad'>fail</b>, "
             "both subtractive arms <b class='good'>perfect</b></span></h2>")
    o.append("<p class='note'>QX's only outright failure in 38 sets, and it is on a set "
             "neither subtractive arm has any trouble with. The garment is a plain black "
             "tee. <b>QX's reference invents a whole ghost figure — tee, jeans and "
             "sneakers — and the output arrives covered in white speckle and scratch marks "
             "that exist nowhere in the input.</b> This is the arm the V2 harness escalated "
             "to <i>in order to route around AI artefacts</i>, and it produced the only "
             "true speckle artefact in the evaluation.</p>")
    o.append("<div class='lab'>the reference chain</div>")
    o.append("<div class='strip s4'>"
             + fig(w("person"), "person (input)")
             + fig(w("garment"), "garment reference")
             + fig(w("bcref"), "BC_klein ref — subtracted", "win")
             + fig(w("qxref"), "QX ref — regenerated", "fail") + "</div>")
    o.append("<div class='lab'>the three arms</div>")
    o.append("<div class='strip s3'>"
             + fig(w("qxout"), "QX — fail", "fail")
             + fig(w("bcout"), "BC_klein — perfect", "win")
             + fig(w("pheadout"), "PHEAD — perfect", "win") + "</div>")
    z = (0.25, 0.20, 0.85, 0.62)
    o.append("<div class='lab'>magnified — the chest. The speckle is not in the garment, "
             "not in the person, and not in the reference. It was invented at the edit "
             "call, on a garment with nothing in it to invent from.</div>")
    o.append("<div class='strip s3'>"
             + fig(web(os.path.join(REPO, src["qxout"]), "qxfail_z_qx.jpg", z, 620),
                   "QX — fail", "fail")
             + fig(web(os.path.join(REPO, src["bcout"]), "qxfail_z_bc.jpg", z, 620),
                   "BC_klein — perfect", "win")
             + fig(web(os.path.join(REPO, src["qxref"]), "qxfail_z_ref.jpg",
                       (0.15, 0.05, 0.85, 0.45), 620), "QX reference, same region") + "</div>")

    # 2. Extraction drift across the cohort.
    rows, agg = drift_table()
    o.append(DRIFT_HEAD)
    hdr = ("<tr><th>reference</th><th>dL</th><th>dC</th><th>dHue</th><th>pattern</th>"
           "<th>dL</th><th>dC</th><th>dHue</th><th>pattern</th>"
           "<th>dL</th><th>dC</th><th>dHue</th><th>pattern</th></tr>")
    body = []
    for r in rows:
        cells = []
        for arm in ("QX_qwen_p1", "QX_kleind", "QX_kleinb"):
            d = r.get(arm)
            if not d:
                cells.append("<td colspan='4' class='dim'>—</td>")
                continue
            cells.append(
                f"<td class='{'bad' if abs(d['dL']) > 12 else ''}'>{d['dL']:+.0f}</td>"
                f"<td class='{'bad' if abs(d['dC']) > 10 else ''}'>{d['dC']:+.0f}</td>"
                f"<td class='{'bad' if d['dHue'] > 25 else ''}'>{d['dHue']:.0f}&deg;</td>"
                f"<td class='{'bad' if d['dEdge'] < 0.5 or d['dEdge'] > 1.9 else ''}'>"
                f"&times;{d['dEdge']:.2f}</td>")
        body.append(f"<tr><td>{r['ref'][:38]}</td>" + "".join(cells) + "</tr>")
    means = []
    for arm in ("QX_qwen_p1", "QX_kleind", "QX_kleinb"):
        ds = agg.get(arm, [])
        n = len(ds) or 1
        means.append(
            f"<td><b>{sum(abs(d['dL']) for d in ds)/n:.0f}</b></td>"
            f"<td><b>{sum(abs(d['dC']) for d in ds)/n:.0f}</b></td>"
            f"<td><b>{sum(d['dHue'] for d in ds)/n:.0f}&deg;</b></td>"
            f"<td><b>&times;{sum(d['dEdge'] for d in ds)/n:.2f}</b></td>")
    o.append("<table class='drift'><tr><th></th>"
             "<th colspan='4'>QX_qwen_p1 (shipped)</th>"
             "<th colspan='4'>klein distilled</th>"
             "<th colspan='4'>klein base</th></tr>"
             + hdr + "".join(body)
             + "<tr class='tot'><td>mean |drift|</td>" + "".join(means) + "</tr></table>")
    o.append(DRIFT_NOTE)

    # 3. Drift, shown.
    for ref, why in DRIFT_SHOW:
        o.append(f"<div class='lab'><b>{ref}</b> — {why}</div>")
        panels = [("v2/runs/acab/%s__CTRL.jpg" % ref, "control crop — the truth", ""),
                  ("v2/runs/acab/%s__QX_qwen_p1.jpg" % ref, "QX (Qwen)", "fail"),
                  ("v2/runs/acab/%s__QX_kleind.jpg" % ref, "klein distilled", ""),
                  ("v2/runs/acab/%s__QX_kleinb.jpg" % ref, "klein base", "")]
        strip = []
        for path, cap, cls in panels:
            if not os.path.exists(os.path.join(REPO, path)):
                continue
            strip.append(fig(web(os.path.join(REPO, path),
                                 f"drift_{ref}_{cap.split()[0]}.jpg", None, 430), cap, cls))
        o.append("<div class='strip s4'>" + "".join(strip) + "</div>")
    return "\n".join(o)

VOCAB = """<h3 style='margin-top:34px'>Three bands, named by what reached the output</h3>
<p class='note'>Working vocabulary, extending V2's &ldquo;attention deficit&rdquo;. The
bands are defined by <b>what arrived in the output relative to the garment</b>, which is
observable, rather than by attention, which we have never looked at.</p>
<div class='band'>
<div><b>Over-attention</b>More arrived than the garment. Content that is not the garment
survives into the output: the reference's <i>pose</i>, its cut boundary, its matte fringe,
its wearer's identity, its background.<span class='who'>p012 collar · p007 hem · V2's
identity import at &minus;0.933 margin</span></div>
<div><b>Questionable attention</b>Some of the garment arrived, incompletely. The right
region is attended and resolved wrong or half — a shallow collar where a stand collar
belongs, a hue that shifted, a pattern that smoothed.<span class='who'>most of the 6 BC
and 17 QX <i>ok</i> verdicts · the whole drift table</span></div>
<div><b>Failed attention</b>None of the garment arrived. The reference contributed no
usable signal at the timesteps that decide layout, and the output is the input.
<span class='who'>HD_p023, both pairings</span></div>
</div>
<div class='q'><b>Over-attention has two sources, and they are the subtract/regenerate
split.</b> A subtractive arm gets more than the garment by <i>copying</i> what was beside
it. A regenerative arm gets more than the garment by <i>inventing</i> what was not there —
QX's speckle on a plain black tee. Same band, opposite mechanism, which is exactly why the
two arms have no shared failures.</div>
<div class='q'><b>The open question this vocabulary makes askable.</b> QX raises the floor
by forcing the reference into a canonical view, and in doing so discards drape, rotation
and pattern — <b>&times;0.51 of the edge detail on average</b>. So: is the original context
worth more than the interference it causes? The literature has the same tension on record —
MV-VTON finds a single garment view &ldquo;insufficient&rdquo; and uses two; RefTon argues
a worn reference reveals drape and translucency a flat shot cannot. Nobody has measured the
trade for a reference like ours.</div>"""

QX_HEAD = """<h2 style='border-top-width:3px;border-top-color:var(--acc)'>
<span class='m'>the other side</span>QX's own failures
<span class='sub'> · 20 perfect / 17 ok / 1 fail</span></h2>
<p class='note'>Everything above is an argument for QX. This section is the argument
against it, because <b>V3 proposes to fold QX's mechanism into the single path, and it
would inherit this too.</b> QX has the highest floor of any arm and the lowest ceiling,
and the two facts have the same cause: it does not subtract the context, it <i>replaces</i>
the garment. What comes back is a garment that is cleaner than the crop and is not
necessarily the same garment.</p>"""

DRIFT_HEAD = """<h2 id='drift'><span class='m'>the ceiling</span>Extraction drift
<span class='sub'> · 11 references, recomputed live from <code>v2/runs/acab/</code></span></h2>
<p class='note'>Median lightness, chroma and circular hue shift of the garment pixels
against the control crop, plus an edge-density ratio that catches a pattern being smoothed
away or invented. Deliberately dumb statistics, because V2 established that no embedding
metric can be trusted here — <code>garment_sim</code> scored 0.78 on an output that
transferred no garment at all. Red is past the flag threshold. <b>This is a rank, not a
verdict:</b> a changed collar or a moved seam does not show up in any of these columns.</p>
<p class='note'><b>The third and fourth column groups are V3's shape 1, already run.</b>
klein was measured as an extractor during V2's AC-A phase and the numbers were never used.
They do not say what you would expect.</p>"""

DRIFT_NOTE = """<div class='q'><b>klein is the better extractor on hue and pattern, and
much worse on lightness.</b> Averaged over the cohort: Qwen holds lightness to 12 but
returns <b>half the edge detail</b> (&times;0.51) and drifts hue 29&deg;; klein distilled
drifts lightness 27 and hue 27 but keeps &times;0.80 of the detail; klein base keeps
&times;1.01 — the only arm that neither loses nor invents texture on average — at hue
21&deg;. Every arm is flagged on 9 or more of 11 references. <b>No extraction arm returns
the same garment.</b></div>
<div class='q'>Two failures pull in opposite directions and both matter.
<code>p030</code> comes back at <b>&times;0.23</b> of its pattern from Qwen — the texture
is gone. <code>p021</code> comes back from klein base at <b>&times;2.70</b> with chroma
<b>+42</b> — texture and saturation that were never there. A floor-raiser that invents is
not obviously safer than a crop that subtracts; it fails somewhere else.</div>"""


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
table.drift{font-size:11.5px;width:100%}
table.drift td,table.drift th{padding:4px 6px}
table.drift th[colspan]{text-align:center;border-bottom:1px solid var(--line);
 color:var(--fg);font-size:12px}
table.drift tr.tot td{border-top:1px solid var(--line);color:var(--fg)}
td.dim{color:var(--dim)}
.band{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin:18px 0}
@media(max-width:860px){.band{grid-template-columns:1fr}}
.band div{border:1px solid var(--line);border-radius:8px;padding:12px 14px;background:#101014}
.band b{display:block;font-size:14px;margin-bottom:5px}
.band .who{font-size:11.5px;color:var(--dim);margin-top:7px}
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
<p class='note'>Shown in full above: <a href='#qxfail'>QX's one outright failure</a> and
<a href='#drift'>the drift table</a>.</p>
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
seed. Analysis: <code>prd/v3/v3.0/RESULTS.md</code>. Bundle and provenance:
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
