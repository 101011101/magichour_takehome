"""v3.3 link 1: the v3.1 extraction call sent to klein. A4 crop | klein mannequin (MK) |
Qwen mannequin (MQ, v3.1, pre-dynamic) for every reference of the run-B fold.

  python3 v3/build/v33_page.py            -> v3/report/v33_klein_extract.html + img_v33/
  python3 v3/build/v33_page.py --embed X  -> self-contained copy at X (data URIs)
"""
import base64
import csv
import html
import json
import os
import sys

from PIL import Image

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RUN = os.path.join(REPO, "v3", "runs", "v3.0b")
REPORT = os.path.join(REPO, "v3", "report")
IMG = os.path.join(REPORT, "img_v33")
EMBED = False

# link 1 review verdicts (RESULTS.md §1.2). Everything else passed all five checks.
FLAG = {
    "dualuse_queen_latifah_gown_stage": "gold embroidery lost; belt added",
    "dualuse_scarlett_johansson_black_dress_backview_night": "dress became a jumpsuit",
    "dualuse_lp_beige_long_coat_menswear": "beige gone grey; inner strap invented",
    "g015": "satin skirt rendered sheer",
    "g030": "sequin rendered as smooth foil; front open",
    "dualuse_woman_top_denim_skirt_nonceleb": "skirt read as shorts (minor)",
    "g024": "pleats lost (minor)",
}


GCOHORT = ["dualuse_queen_latifah_gown_stage",
           "dualuse_scarlett_johansson_black_dress_backview_night",
           "dualuse_lp_beige_long_coat_menswear", "g015", "g030",
           "g027", "g018", "dualuse_gal_gadot_blue_dress_redcarpet"]
# link 1.1 verdicts (RESULTS.md §2.1). Absent = pass.
GVERDICT = {
    ("dualuse_scarlett_johansson_black_dress_backview_night", "k1_ghost"): "arm, legs, heels remain",
    ("g018", "k4_qx"): "trousers dropped",
    ("dualuse_scarlett_johansson_black_dress_backview_night", "k2_flat"): "dress split into two",
    ("g015", "k2_flat"): "dress split into two",
    ("dualuse_gal_gadot_blue_dress_redcarpet", "k2_flat"): "dress split into two",
    ("g027", "k2_flat"): "shorts invented",
    ("g018", "k2_flat"): "shorts invented",
    ("dualuse_queen_latifah_gown_stage", "k2_flat"): "coat cut into a jacket",
}
GVERDICT.update({(g, "k3_minimal"): "person returned, outfit turned white" for g in GCOHORT})
_leak = {"dualuse_gal_gadot_blue_dress_redcarpet": "legs, heels remain",
         "dualuse_woman_top_denim_skirt_nonceleb": "legs, shoes remain",
         "g005": "legs remain", "g014": "legs, heels remain", "g024": "legs, shoes remain",
         "dualuse_man_black_suit_studio_nonceleb": "hands remain", "g029": "hands remain"}
for g, v in _leak.items():
    GVERDICT[(g, "k1_ghost")] = v
    GVERDICT[(g, "k1_noext")] = v
GVERDICT[("dualuse_scarlett_johansson_black_dress_backview_night", "k1_noext")] = "hair, arm, legs remain"
GVERDICT[("p029", "k1_noext")] = "hands and phone remain"
GVERDICT[("dualuse_man_black_suit_studio_nonceleb", "k4_qx")] = "shirt and tie dropped"
GVERDICT[("g009", "k4_qx")] = "bag kept"
_ALL = ["p029", "p030", "dualuse_emma_watson_black_blazer_armscrossed",
        "dualuse_gal_gadot_blue_dress_redcarpet", "dualuse_hugh_jackman_grey_suit_outdoor",
        "dualuse_man_black_suit_studio_nonceleb", "dualuse_queen_latifah_gown_stage",
        "dualuse_scarlett_johansson_black_dress_backview_night",
        "dualuse_woman_top_denim_skirt_nonceleb", "dualuse_zendaya_white_blazer_skirt",
        "dualuse_lp_beige_long_coat_menswear", "dualuse_lp_floral_kimono_set",
        "dualuse_lp_navy_quarterzip_knit_LOWRES", "dualuse_lp_plaid_overcoat_brown_suit",
        "dualuse_navy_peacoat_onmodel", "g004", "g005", "g009", "g011", "g012", "g013",
        "g014", "g015", "g018", "g024", "g027", "g029", "g030"]
for g in _ALL:
    if g not in ("dualuse_lp_beige_long_coat_menswear",):
        GVERDICT[(g, "k5_form")] = "white mannequin rendered"
    if g not in ("dualuse_lp_beige_long_coat_menswear", "dualuse_lp_plaid_overcoat_brown_suit",
                 "dualuse_navy_peacoat_onmodel", "g013"):
        GVERDICT[(g, "k6_ghost2")] = "grey silhouette body rendered"


def web(src, dst, width=520):
    if not os.path.exists(src):
        return None, None
    out, full = os.path.join(IMG, dst), os.path.join(IMG, dst.replace(".jpg", "@f.jpg"))
    im = None
    if not os.path.exists(out):
        im = Image.open(src).convert("RGB")
        t = im.resize((width, int(im.height * width / im.width)), Image.LANCZOS) \
            if im.width > width else im
        t.save(out, quality=88, optimize=True)
    if not os.path.exists(full):
        im = im or Image.open(src).convert("RGB")
        im.save(full, quality=92, optimize=True)
    if EMBED:   # one smaller image for thumb and lightbox, to stay under the 16 MB cap
        e = os.path.join(IMG, dst.replace(".jpg", "@e.jpg"))
        if not os.path.exists(e):
            im = Image.open(out).convert("RGB")
            im.resize((240, int(im.height * 240 / im.width)), Image.LANCZOS).save(
                e, quality=72, optimize=True)
        u = "data:image/jpeg;base64," + base64.b64encode(open(e, "rb").read()).decode()
        return u, u
    return "img_v33/" + dst, "img_v33/" + os.path.basename(full)


def qwen(g):
    """v3.1's dynamic-prompt Qwen reference where link 14 made one, else the pre-dynamic
    MQ from link 10 - labelled, because the two are not the same experiment."""
    d = os.path.join(RUN, "refs", f"{g}__dyn.jpg")
    if os.path.exists(d):
        return web(d, f"{g}__dyn.jpg"), "Qwen mannequin<span class='n'>v3.1 link 14, DYNAMIC prompt</span>"
    return (web(os.path.join(RUN, "refs", f"{g}__MQ.jpg"), f"{g}__MQ.jpg"),
            "Qwen mannequin<span class='n'>v3.1 link 10, pre-dynamic, orientation only</span>")


def fig(pair, cap, cls=""):
    src, full = pair
    if not src:
        return f"<figure class='miss'><div class='ph'>not run</div><figcaption>{cap}</figcaption></figure>"
    return (f"<figure class='{cls}'><img src='{src}' data-full='{full}' "
            f"alt='{html.escape(cap)}' loading='lazy'><figcaption>{cap}</figcaption></figure>")


def main(embed_to=None, section="all"):
    global EMBED
    EMBED = bool(embed_to)
    os.makedirs(IMG, exist_ok=True)
    meta = json.load(open(os.path.join(RUN, "_v33_prompts.json")))
    rows = list(csv.DictReader(open(os.path.join(REPO, "v3/testsets/v30_matrix_b.csv"))))
    o = [HEAD, "<div class='wrap'>", NOTE]
    if section == "garment":
        o = [GHEAD, "<div class='wrap'>"]
    if section == "pose":
        return pose_page(embed_to, rows)
    if section == "phase2":
        return phase2_page(embed_to, rows)
    if section == "phase3":
        return phase3_page(embed_to, rows)
    if section == "phase4":
        return phase4_page(embed_to, rows)
    if section == "phase5":
        return phase5_page(embed_to, rows)
    if section == "phase6":
        return phase6_page(embed_to, rows)
    if section == "phase7":
        return phase7_page(embed_to, rows)
    if section == "version":
        return version_page(embed_to, rows)
    for r in (rows if section == "all" else []):
        g, p = r["garment"], r["person"]
        m = meta[f"{g}|{p}"]
        v = FLAG.get(g)
        tag = (f"<span class='t bad'>{html.escape(v)}</span>" if v
               else "<span class='t'>parity</span>")
        o.append(f"<h2>{r['pair']} &middot; {html.escape(g)}"
                 f"<span class='ar'>&larr; worn by {html.escape(p)}</span>{tag}</h2>")
        o.append(f"<div class='lab'>reader: colour <b>{html.escape(m['colour'])}</b> "
                 f"&middot; framing <b>{html.escape(m['framing'])}</b></div>")
        o.append("<div class='strip s5'>"
                 + fig(web(os.path.join(RUN, "inputs", f"{g}__A4.jpg"), f"{g}__A4.jpg"),
                       "A4 crop &mdash; the input")
                 + fig(web(os.path.join(RUN, "refs", f"{g}__MK__{p}.jpg"), f"{g}__MK__{p}.jpg"),
                       "klein mannequin<span class='n'>MK &mdash; link 1</span>",
                       "bad" if v else "")
                 + fig(web(os.path.join(RUN, "refs", f"{g}__MHraw.jpg"), f"{g}__MHraw.jpg"),
                       "klein head swap<span class='n'>MH raw &mdash; link 1.3, before the crop</span>")
                 + fig(web(os.path.join(RUN, "refs", f"{g}__MH.jpg"), f"{g}__MH.jpg"),
                       "MH<span class='n'>head swap &rarr; A4 crop, the reference</span>", "ship")
                 + fig(*qwen(g)) + "</div>")
        o.append(f"<details><summary>prompt as sent</summary><pre>{html.escape(m['prompt'])}</pre></details>")
    # ---- links 1.1 / 1.2: garment only, no mannequin ---------------------------
    gm = json.load(open(os.path.join(RUN, "_v33_garment_prompts.json")))
    o.append(GNOTE)
    KARMS = [("k1_ghost", "k1 ghost", "ship"), ("k1_noext", "k1 no extent", ""),
             ("k4_qx", "k4 qx", "ship"), ("k5_form", "k5 form", ""),
             ("k6_ghost2", "k6 ghost, parts named", ""),
             ("k2_flat", "k2 flat", ""), ("k3_minimal", "k3 minimal", "")]
    for r in rows:
        g, p = r["garment"], r["person"]
        o.append(f"<h2>{r['pair']} &middot; {html.escape(g)}<span class='ar'>MK verdict: "
                 f"{html.escape(FLAG.get(g, 'parity'))}</span></h2>")
        o.append(f"<div class='lab'>framing <b>{gm[f'{g}|k1_ghost']['framing']}</b> "
                 "&middot; same crop, same seed on every klein column</div>")
        cells = [fig(web(os.path.join(RUN, "inputs", f"{g}__A4.jpg"), f"{g}__A4.jpg"),
                     "A4 crop &mdash; the input"),
                 fig(web(os.path.join(RUN, "refs", f"{g}__MK__{p}.jpg"), f"{g}__MK__{p}.jpg"),
                     "MK mannequin<span class='n'>link 1</span>", "bad" if g in FLAG else "")]
        for k, lab, cls in KARMS:
            src = os.path.join(RUN, "refs", f"{g}__{k}.jpg")
            if not os.path.exists(src):
                continue
            v = GVERDICT.get((g, k), "")
            cells.append(fig(web(src, f"{g}__{k}.jpg"),
                             f"{lab}<span class='n'>{html.escape(v) or 'pass'}</span>",
                             "bad" if v else cls))
        cells.append(fig(*qwen(g)))
        o.append(f"<div class='strip {'g5' if section == 'garment' else 's' + str(len(cells))}'>"
                 + "".join(cells) + "</div>")
    g0 = rows[0]["garment"]
    o.append("<details><summary>the prompts as sent (extent sentence varies with the "
             "framing read; shown for the first reference)</summary><pre>"
             + "\n\n".join(k + "\n" + html.escape(gm[g0 + "|" + k]["prompt"])
                           for k, _, _ in KARMS if g0 + "|" + k in gm)
             + "</pre></details>")
    o.append(FOOT + "</div>" + LB + SCRIPT)
    page = "\n".join(o)
    dst = embed_to or os.path.join(
        REPORT, "v33_klein_extract.html" if section == "all" else "v33_garment_only.html")
    open(dst, "w").write(page)
    print(f"{dst}  ({len(rows)} references, {len(FLAG)} flagged, "
          f"{os.path.getsize(dst)/1e6:.1f} MB)")


PARMS = [("MH", "MH", "keeps the photograph's pose", "ship"),
         ("MH_pose", "MH pose", "constant pose sentence, names feet", ""),
         ("MH_posefr", "MH pose + framing", "pose and extent from one table", "ship"),
         ("MH_fr", "MH framing only", "no pose word", ""),
         ("MH_col", "MH colour", "head colour from the paired person", "")]
PVERDICT = {}
for g in ["p029", "p030", "dualuse_emma_watson_black_blazer_armscrossed",
          "dualuse_queen_latifah_gown_stage", "g018", "g027", "g029", "g030"]:
    PVERDICT[(g, "MH_pose")] = "whole body invented"
PVERDICT[("dualuse_emma_watson_black_blazer_armscrossed", "MH_pose")] = "two full-length figures invented"


def pose_page(embed_to, rows):
    pm = json.load(open(os.path.join(RUN, "_v33_pose_prompts.json")))
    o = [PHEAD, "<div class='wrap'>", PNOTE]
    for r in rows:
        g = r["garment"]
        e = pm[f"{g}|MH_col"]
        o.append(f"<h2>{r['pair']} &middot; {html.escape(g)}<span class='ar'>worn by "
                 f"{html.escape(e['person'])}</span></h2>")
        o.append(f"<div class='lab'>reader: framing <b>{e['framing']}</b> &middot; head colour "
                 f"<b>{html.escape(e['colour'])}</b></div>")
        cells = [fig(web(os.path.join(RUN, "inputs", f"{g}.jpg"), f"{g}__in.jpg"),
                     "photograph &mdash; the input")]
        for arm, lab, sub, cls in PARMS:
            crop = os.path.join(RUN, "refs", f"{g}__{arm}.jpg")
            raw = os.path.join(RUN, "refs", f"{g}__{arm}raw.jpg" if arm != "MH" else f"{g}__MHraw.jpg")
            src, tag = (crop, "after A4 crop") if os.path.exists(crop) else (raw, "raw klein frame, crop pending")
            v = PVERDICT.get((g, arm), "")
            cells.append(fig(web(src, os.path.basename(src)),
                             f"{lab}<span class='n'>{html.escape(v) or sub} &middot; {tag}</span>",
                             "bad" if v else cls))
        o.append("<div class='strip s6'>" + "".join(cells) + "</div>")
        o.append("<details><summary>prompts as sent</summary><pre>"
                 + "\n\n".join(a + "\n" + html.escape(pm[f"{g}|{a}"]["prompt"])
                               for a, _, _, _ in PARMS if a != "MH") + "</pre></details>")
    o.append(PFOOT + "</div>" + LB + SCRIPT)
    dst = embed_to or os.path.join(REPORT, "v33_pose.html")
    open(dst, "w").write("\n".join(o))
    print(f"{dst}  ({len(rows)} references, {os.path.getsize(dst)/1e6:.1f} MB)")


P2ARMS = [("P0", "P0 baseline", "template, crop-first", "ship"),
          ("P1_feet", "P1 feet", "toes at the camera", ""),
          ("P2_hips", "P2 hips", "hips square, legs straight", ""),
          ("P3_no", "P3 no-", "\"no turned feet, no bent knee\"", ""),
          ("M1_neckup", "M1 neck up", "replace from the neck up", ""),
          ("M2_faceonly", "M2 face only", "face + hair only, neck unchanged", ""),
          ("M3_skinkept", "M3 skin kept", "positive: neck, arms, hands as photographed", ""),
          ("M4_no", "M4 no-", "\"no mannequin material on ...\"", "")]
P2VERDICT = {   # RESULTS.md §6.3
    ("p029", "P2_hips"): "legs invented on a waist-up crop",
    ("dualuse_emma_watson_black_blazer_armscrossed", "P2_hips"): "full body invented on a waist-up crop",
    ("g029", "P2_hips"): "zoomed out past the crop", ("g030", "P2_hips"): "zoomed out past the crop",
    ("g013", "P0"): "sandals regenerated as bare feet",
    ("dualuse_scarlett_johansson_black_dress_backview_night", "P0"): "split hem re-rendered as trousers",
    ("g027", "M2_faceonly"): "facial features rendered", ("g029", "M2_faceonly"): "facial features rendered",
    ("p030", "M2_faceonly"): "facial features rendered",
    ("dualuse_scarlett_johansson_black_dress_backview_night", "P1_feet"): "seed 47 (46 gave a black frame)",
    ("dualuse_scarlett_johansson_black_dress_backview_night", "M1_neckup"): "seed 47 (46 gave a black frame)",
    ("dualuse_gal_gadot_blue_dress_redcarpet", "M2_faceonly"): "seed 47 (46 gave a black frame)",
}
P2CASES = {"g013": "link 3 case: legs and feet angled", "g009": "link 3 case: legs and feet angled",
           "g027": "link 4 case: neck and arms tinted", "g029": "link 4 case: neck tinted",
           "dualuse_emma_watson_black_blazer_armscrossed": "phase-1 duplication, full frame"}


def phase2_page(embed_to, rows):
    pm = json.load(open(os.path.join(RUN, "_v33_p2_prompts.json")))
    o = [P2HEAD, "<div class='wrap'>", P2NOTE]
    for r in rows:
        g = r["garment"]
        fr = pm[f"{g}|P0"]["framing"]
        case = P2CASES.get(g, "")
        o.append(f"<h2>{r['pair']} &middot; {html.escape(g)}"
                 + (f"<span class='t bad'>{html.escape(case)}</span>" if case else "") + "</h2>")
        o.append(f"<div class='lab'>framing <b>{fr}</b> &middot; input is the A4 crop &middot; "
                 "a cell identical in wording to P0 shows P0's frame</div>")
        cells = [fig(web(os.path.join(RUN, "inputs", f"{g}__A4.jpg"), f"{g}__A4.jpg"),
                     "A4 crop &mdash; the input")]
        for arm, lab, sub, cls in P2ARMS:
            same = pm[f"{g}|{arm}"]["same_as_P0"]
            src = os.path.join(RUN, "refs", f"{g}__p2_{'P0' if same else arm}.jpg")
            v = P2VERDICT.get((g, arm), "")
            cap = f"{lab}<span class='n'>{html.escape(v) or ('= P0 wording' if same else sub)}</span>"
            cells.append(fig(web(src, os.path.basename(src)), cap,
                             "bad" if v else ("" if same else cls)))
        o.append("<div class='strip s9'>" + "".join(cells) + "</div>")
        o.append("<details><summary>prompts as sent</summary><pre>"
                 + "\n\n".join(a + ("  (= P0)" if pm[f"{g}|{a}"]["same_as_P0"] else "") + "\n"
                               + html.escape(pm[f"{g}|{a}"]["prompt"]) for a, _, _, _ in P2ARMS)
                 + "</pre></details>")
    o.append(P2FOOT + "</div>" + LB + SCRIPT)
    dst = embed_to or os.path.join(REPORT, "v33_phase2.html")
    open(dst, "w").write("\n".join(o))
    print(f"{dst}  ({len(rows)} references, {os.path.getsize(dst)/1e6:.1f} MB)")


P3ARMS = [("Q0", "Q0 baseline", "M1 + pose+framing", ""),
          ("Q1_legs", "Q1 legs", "\"Legs straight.\"", ""),
          ("Q2_legsgarment", "Q2 legs + hem", "\"a dress stays a dress, a skirt stays a skirt\"", ""),
          ("Q3_garment", "Q3 garment held", "\"the clothing stays exactly the same\"", "ship"),
          ("Q4_feet", "Q4 feet", "\"Feet point towards the camera.\"", ""),
          ("Q5_all", "Q5 all", "legs + hem + feet", ""),
          ("Q6_feetstraight", "Q6 feet straight (on Q3)", "probe: \"Feet straight.\"", ""),
          ("A1_armsdown", "A1 arms down (on Q3)", "probe, p030 only", "ship"),
          ("A2_armssides", "A2 arms at sides (on Q3)", "probe, p030 only", "ship")]
P3VERDICT = {
    ("g012", "Q3_garment"): "third foot under the hem",
    ("dualuse_scarlett_johansson_black_dress_backview_night", "Q0"): "dress re-rendered as trousers",
    ("dualuse_scarlett_johansson_black_dress_backview_night", "Q1_legs"): "dress re-rendered as trousers",
    ("dualuse_scarlett_johansson_black_dress_backview_night", "Q4_feet"): "dress as trousers; seed 47",
    ("dualuse_gal_gadot_blue_dress_redcarpet", "Q1_legs"): "seed 47 (46 gave a black frame)",
    ("dualuse_gal_gadot_blue_dress_redcarpet", "Q2_legsgarment"): "slit closed into a wrap hem",
    ("dualuse_gal_gadot_blue_dress_redcarpet", "Q5_all"): "slit closed",
    ("dualuse_hugh_jackman_grey_suit_outdoor", "Q2_legsgarment"): "skirt invented over trousers",
    ("dualuse_hugh_jackman_grey_suit_outdoor", "Q5_all"): "skirt invented over trousers",
    ("dualuse_man_black_suit_studio_nonceleb", "Q2_legsgarment"): "skirt invented over trousers",
    ("dualuse_lp_navy_quarterzip_knit_LOWRES", "Q2_legsgarment"): "skirt invented over trousers",
    ("dualuse_lp_navy_quarterzip_knit_LOWRES", "Q5_all"): "skirt invented over trousers",
    ("dualuse_queen_latifah_gown_stage", "Q2_legsgarment"): "coat shortened",
    ("g013", "Q0"): "sandals regenerated as bare feet (all arms)",
}
P3CASES = {"dualuse_scarlett_johansson_black_dress_backview_night": "case: dress split into trousers",
           "g013": "case: sandals to bare feet", "g009": "case: residual foot angle",
           "g015": "case: skirt", "g024": "case: skirt", "dualuse_gal_gadot_blue_dress_redcarpet": "case: slit dress"}


def phase3_page(embed_to, rows):
    pm = json.load(open(os.path.join(RUN, "_v33_p3_prompts.json")))
    o = [P3HEAD, "<div class='wrap'>", P3NOTE]
    for r in rows:
        g = r["garment"]
        fr = pm[f"{g}|Q0"]["framing"]
        case = P3CASES.get(g, "")
        o.append(f"<h2>{r['pair']} &middot; {html.escape(g)}"
                 + (f"<span class='t bad'>{html.escape(case)}</span>" if case else "") + "</h2>")
        o.append(f"<div class='lab'>framing <b>{fr}</b> &middot; input is the A4 crop &middot; "
                 "a cell identical in wording to Q0 shows Q0's frame</div>")
        cells = [fig(web(os.path.join(RUN, "inputs", f"{g}__A4.jpg"), f"{g}__A4.jpg"),
                     "A4 crop &mdash; the input")]
        for arm, lab, sub, cls in P3ARMS:
            if f"{g}|{arm}" not in pm:
                continue
            same = pm[f"{g}|{arm}"]["same_as_Q0"]
            src = os.path.join(RUN, "refs", f"{g}__p3_{'Q0' if same else arm}.jpg")
            v = P3VERDICT.get((g, arm), "")
            cap = f"{lab}<span class='n'>{html.escape(v) or ('= Q0 wording' if same else sub)}</span>"
            cells.append(fig(web(src, os.path.basename(src)), cap,
                             "bad" if v else ("" if same else cls)))
        o.append(f"<div class='strip s{min(len(cells), 10)}'>" + "".join(cells) + "</div>")
        o.append("<details><summary>prompts as sent</summary><pre>"
                 + "\n\n".join(a + ("  (= Q0)" if pm[f"{g}|{a}"]["same_as_Q0"] else "") + "\n"
                               + html.escape(pm[f"{g}|{a}"]["prompt"]) for a, _, _, _ in P3ARMS if f"{g}|{a}" in pm)
                 + "</pre></details>")
    o.append(P3FOOT + "</div>" + LB + SCRIPT)
    dst = embed_to or os.path.join(REPORT, "v33_phase3.html")
    open(dst, "w").write("\n".join(o))
    print(f"{dst}  ({len(rows)} references, {os.path.getsize(dst)/1e6:.1f} MB)")


P4VERDICT = {   # RESULTS.md §8.1
    ("p008+dualuse_scarlett_johansson_black_dress_backview_night", "Q0"): "trousers: reference defect propagated",
    ("p008+dualuse_scarlett_johansson_black_dress_backview_night", "BC"): "trousers",
    ("p001+p029", "Q0"): "backpack transferred", ("p001+p029", "Q3"): "backpack transferred", ("p001+p029", "BC"): "backpack transferred",
    ("p018+g009", "Q0"): "bag strap transferred", ("p018+g009", "Q3"): "bag strap transferred", ("p018+g009", "BC"): "bag strap transferred",
    ("p019+g011", "Q0"): "cooked skin: pairing defect, all arms", ("p019+g011", "Q3"): "cooked skin: pairing defect, all arms",
    ("p019+g011", "BC"): "cooked skin: pairing defect, all arms", ("p019+g011", "MQ"): "cooked skin: pairing defect, all arms",
}
P4CASES = {"g013": "ref: bare feet", "g012": "ref: Q3 third foot",
           "dualuse_scarlett_johansson_black_dress_backview_night": "ref: Q0 trousers vs Q3 dress",
           "p030": "ref: arms up", "g011": "v3.1 hard pair: exposed skin",
           "dualuse_zendaya_white_blazer_skirt": "v3.1 hard pair: white on white"}


def phase4_page(embed_to, rows):
    o = [P4HEAD, "<div class='wrap'>", P4NOTE]
    for r in rows:
        sid, p, g = r["set_id"], r["person"], r["garment"]
        case = P4CASES.get(g, "")
        o.append(f"<h2>{r['pair']} &middot; {html.escape(p)} wears {html.escape(g)}"
                 + (f"<span class='t bad'>{html.escape(case)}</span>" if case else "") + "</h2>")
        o.append("<div class='lab'>inputs and references</div>")
        o.append("<div class='strip s6'>"
                 + fig(web(os.path.join(RUN, "inputs", f"{p}.jpg"), f"{p}__in.jpg"), "person &mdash; image 1, as photographed")
                 + fig(web(os.path.join(RUN, "inputs", f"{g}.jpg"), f"{g}__in.jpg"), "garment &mdash; original photograph, before any processing")
                 + fig(web(os.path.join(RUN, "refs", f"{g}__p3_Q0.jpg"), f"{g}__p3_Q0.jpg"), "Q0 reference<span class='n'>head swap + pose+framing</span>")
                 + fig(web(os.path.join(RUN, "refs", f"{g}__p3_Q3_garment.jpg"), f"{g}__p3_Q3_garment.jpg"), "Q3 reference<span class='n'>+ garment held &mdash; the version</span>", "ship")
                 + fig(web(os.path.join(RUN, "refs", f"{g}__BC.jpg"), f"{g}__BC.jpg"), "BC reference<span class='n'>v3.1 incumbent, bald pass</span>")
                 + fig(web(os.path.join(RUN, "refs", f"{g}__MQ.jpg"), f"{g}__MQ.jpg"), "MQ reference<span class='n'>v3.1 locked arm, Qwen mannequin</span>")
                 + "</div>")
        o.append("<div class='lab'>what klein made from each &mdash; <b>this row is the experiment</b></div>")
        cells = []
        for arm, lab, cls in [("Q0", "Q0", ""), ("Q3", "Q3 &mdash; the version", "ship"), ("BC", "BC", ""), ("MQ", "MQ", "")]:
            v = P4VERDICT.get((sid, arm), "")
            cells.append(fig(web(os.path.join(RUN, "gen", f"{sid}__{arm}.jpg"), f"{sid}__{arm}.jpg"),
                             f"{lab}<span class='n'>{html.escape(v) or 'edit output'}</span>", "bad" if v else cls))
        o.append("<div class='strip s4'>" + "".join(cells) + "</div>")
    o.append(P4FOOT + "</div>" + LB + SCRIPT)
    dst = embed_to or os.path.join(REPORT, "v33_phase4.html")
    open(dst, "w").write("\n".join(o))
    print(f"{dst}  ({len(rows)} pairs, {os.path.getsize(dst)/1e6:.1f} MB)")


P5ARMS = [("Q3", "Q3 control", "feet in"), ("R1_ankleafter", "R1 ankle, after", "CPU cut on the Q3 reference"),
          ("R2_hemafter", "R2 hem-or-ankle, after", "= R1 here: hem below the ankle line"),
          ("R3_anklebefore", "R3 ankle, before klein", "crop cut, then klein"),
          ("R4_prompt", "R4 prompt", "\"the feet are outside it\"")]


def phase5_page(embed_to, rows):
    o = [P5HEAD, "<div class='wrap'>", P5NOTE]
    for r in rows:
        if r["garment"] not in ("g013", "g012"): continue
        sid, p, g = r["set_id"], r["person"], r["garment"]
        o.append(f"<h2>{r['pair']} &middot; {html.escape(p)} wears {html.escape(g)}</h2>")
        o.append("<div class='lab'>references</div>")
        cells = [fig(web(os.path.join(RUN, "inputs", f"{p}.jpg"), f"{p}__in.jpg"), "person &mdash; image 1")]
        for arm, lab, sub in P5ARMS:
            src = os.path.join(RUN, "refs", f"{g}__p3_Q3_garment.jpg" if arm == "Q3" else f"{g}__p5_{arm}.jpg")
            v = "feet rendered anyway" if arm == "R4_prompt" else ""
            cells.append(fig(web(src, os.path.basename(src)), f"{lab}<span class='n'>{html.escape(v) or sub}</span>", "bad" if v else ""))
        o.append("<div class='strip s6'>" + "".join(cells) + "</div>")
        o.append("<div class='lab'>what the edit made from each &mdash; <b>this row is the experiment</b></div>")
        cells = []
        for arm, lab, sub in P5ARMS:
            cells.append(fig(web(os.path.join(RUN, "gen", f"{sid}__{arm}.jpg"), f"{sid}__{arm}.jpg"),
                             f"{lab}<span class='n'>{'control' if arm == 'Q3' else 'indistinguishable from the control'}</span>"))
        o.append("<div class='strip s5'>" + "".join(cells) + "</div>")
    o.append(P5FOOT + "</div>" + LB + SCRIPT)
    dst = embed_to or os.path.join(REPORT, "v33_phase5.html")
    open(dst, "w").write("\n".join(o))
    print(f"{dst}  ({os.path.getsize(dst)/1e6:.1f} MB)")


P6ARMS = [("Q3", "E0 control", "the edit prompt as since V2", ""),
          ("E1", "E1", "\"Do not add any body parts.\"", ""),
          ("E2", "E2", "\"exactly two legs and two feet\"", ""),
          ("E3", "E3", "\"body, limbs and feet exactly as in image 1\"", ""),
          ("E4", "E4", "\"drapes over the body as one garment\"", "")]
P6PASS = {("p021+g013", "E3")}
E3FOLD = {"p021+g013": "fix: fabric spans both knees, two legs"}   # filled after review
P6VERDICT = {("p021+g013", "Q3"): "three tubes", ("p021+g013", "E1"): "centre panel fainter, still there",
             ("p021+g013", "E2"): "two tubes, but the person re-rendered", ("p021+g013", "E3"): "PASS: fabric spans both knees, two legs",
             ("p021+g013", "E4"): "partial: fabric reads more as one piece",
             ("p022+g014", "E2"): "legs and feet re-drawn",
             ("p008+dualuse_scarlett_johansson_black_dress_backview_night", "E2"): "person re-framed, bag gone",
             ("p003+dualuse_emma_watson_black_blazer_armscrossed", "E2"): "blazer became a coat",
             ("p003+dualuse_emma_watson_black_blazer_armscrossed", "E4"): "lower body: her own skirt kept"}


def phase6_page(embed_to, rows):
    ed = json.load(open(os.path.join(RUN, "_v33_edit2.json")))
    o = [P6HEAD, "<div class='wrap'>", P6NOTE]
    for r in rows:
        sid, p, g = r["set_id"], r["person"], r["garment"]
        if sid not in ed["pairs"]: continue
        o.append(f"<h2>{r['pair']} &middot; {html.escape(p)} wears {html.escape(g)}"
                 + ("<span class='t bad'>the case</span>" if g == "g013" else "<span class='t'>clean under E0</span>") + "</h2>")
        o.append("<div class='strip s3'>"
                 + fig(web(os.path.join(RUN, "inputs", f"{p}.jpg"), f"{p}__in.jpg"), "person &mdash; image 1")
                 + fig(web(os.path.join(RUN, "refs", f"{g}__p3_Q3_garment.jpg"), f"{g}__p3_Q3_garment.jpg"), "Q3 reference &mdash; image 2, held fixed")
                 + "</div>")
        o.append("<div class='lab'>the same edit with each prompt &mdash; <b>this row is the experiment</b></div>")
        cells = []
        for arm, lab, sub, cls in P6ARMS:
            v = P6VERDICT.get((sid, arm), "")
            cells.append(fig(web(os.path.join(RUN, "gen", f"{sid}__{arm}.jpg"), f"{sid}__{arm}.jpg"),
                             f"{lab}<span class='n'>{html.escape(v) or sub}</span>",
                             "ship" if (sid, arm) in P6PASS else ("bad" if v and arm != "Q3" else "")))
        o.append("<div class='strip s5'>" + "".join(cells) + "</div>")
    o.append("<details><summary>the five edit prompts</summary><pre>"
             + "\n\n".join(k + "\n" + html.escape(v) for k, v in ed["prompts"].items()) + "</pre></details>")
    o.append("<h2 class='sec'>E3 on all 28 &mdash; the validation</h2>")
    o.append("<div class='q'>Every pair of the fold, E0 (the edit prompt as since V2) beside E3, same Q3 "
             "reference, same seed. Red where E3 differs for the worse; green where it fixes something; "
             "no outline where the two are indistinguishable.</div>")
    for r in rows:
        sid, p, g = r["set_id"], r["person"], r["garment"]
        if not os.path.exists(os.path.join(RUN, "gen", f"{sid}__E3.jpg")): continue
        v = E3FOLD.get(sid, "")
        o.append(f"<h2>{r['pair']} &middot; {html.escape(p)} wears {html.escape(g)}</h2>")
        o.append("<div class='strip s4'>"
                 + fig(web(os.path.join(RUN, "inputs", f"{p}.jpg"), f"{p}__in.jpg"), "person")
                 + fig(web(os.path.join(RUN, "refs", f"{g}__p3_Q3_garment.jpg"), f"{g}__p3_Q3_garment.jpg"), "Q3 reference")
                 + fig(web(os.path.join(RUN, "gen", f"{sid}__Q3.jpg"), f"{sid}__Q3.jpg"), "E0")
                 + fig(web(os.path.join(RUN, "gen", f"{sid}__E3.jpg"), f"{sid}__E3.jpg"),
                       f"E3<span class='n'>{html.escape(v) or 'indistinguishable from E0'}</span>",
                       "ship" if v.startswith("fix") else ("bad" if v else ""))
                 + "</div>")
    o.append(P6FOOT + "</div>" + LB + SCRIPT)
    dst = embed_to or os.path.join(REPORT, "v33_phase6.html")
    open(dst, "w").write("\n".join(o))
    print(f"{dst}  ({os.path.getsize(dst)/1e6:.1f} MB)")


def phase7_page(embed_to, rows):
    p7 = json.load(open(os.path.join(RUN, "_v33_p7.json")))
    o = [P7HEAD, "<div class='wrap'>", P7NOTE]
    for r in rows:
        g, p, sid = r["garment"], r["person"], r["set_id"]
        if g not in p7["changed"]: continue
        o.append(f"<h2>{r['pair']} &middot; {html.escape(g)}<span class='ar'>chest_up &middot; the only reference whose prompt changed</span></h2>")
        o.append("<div class='lab'>the reference, before and after the row edit</div>")
        o.append("<div class='strip s3'>"
                 + fig(web(os.path.join(RUN, "inputs", f"{g}__A4.jpg"), f"{g}__A4.jpg"), "A4 crop &mdash; the input")
                 + fig(web(os.path.join(RUN, "refs", f"{g}__p3_Q3_garment.jpg"), f"{g}__p3_Q3_garment.jpg"), "Q3 reference, old chest_up row<span class='n'>arms stay raised</span>", "bad")
                 + fig(web(os.path.join(RUN, "refs", f"{g}__p7_Q3.jpg"), f"{g}__p7_Q3.jpg"), "Q3 reference, arms row<span class='n'>arms down, bust clear</span>", "ship")
                 + "</div>")
        o.append(f"<div class='lab'>the edit (E3 prompt) on {html.escape(sid)} from each &mdash; <b>this row is the experiment</b></div>")
        o.append("<div class='strip s3'>"
                 + fig(web(os.path.join(RUN, "inputs", f"{p}.jpg"), f"{p}__in.jpg"), "person &mdash; image 1")
                 + fig(web(os.path.join(RUN, "gen", f"{sid}__E3.jpg"), f"{sid}__E3.jpg"), "from the old reference")
                 + fig(web(os.path.join(RUN, "gen", f"{sid}__P7E3.jpg"), f"{sid}__P7E3.jpg"), "from the new reference<span class='n'>identical: the wearer supplies his own arms</span>")
                 + "</div>")
        o.append("<details><summary>the new chest_up prompt as sent</summary><pre>" + html.escape(p7["meta"][g]["prompt"]) + "</pre></details>")
    o.append(P7FOOT + "</div>" + LB + SCRIPT)
    dst = embed_to or os.path.join(REPORT, "v33_phase7.html")
    open(dst, "w").write("\n".join(o))
    print(f"{dst}  ({os.path.getsize(dst)/1e6:.1f} MB)")


VVERDICT = {"p025+g024": "fix: wearer's own boots kept, reference shoes not transferred",
            "p019+g011": "pairing defect, all arms"}


def version_page(embed_to, rows):
    o = [VHEAD, "<div class='wrap'>", VNOTE]
    for r in rows:
        sid, p, g = r["set_id"], r["person"], r["garment"]
        v = VVERDICT.get(sid, "")
        o.append(f"<h2>{r['pair']} &middot; {html.escape(p)} wears {html.escape(g)}</h2>")
        o.append("<div class='strip s5'>"
                 + fig(web(os.path.join(RUN, "inputs", f"{p}.jpg"), f"{p}__in.jpg"), "person &mdash; image 1")
                 + fig(web(os.path.join(RUN, "inputs", f"{g}.jpg"), f"{g}__in.jpg"), "garment &mdash; original photograph")
                 + fig(web(os.path.join(RUN, "refs", f"{g}__V.jpg"), f"{g}__V.jpg"), "the version's reference<span class='n'>head swap, re-pose, hold, ankle cut</span>")
                 + fig(web(os.path.join(RUN, "gen", f"{sid}__E3.jpg"), f"{sid}__E3.jpg"), "control: E3, no ankle cut")
                 + fig(web(os.path.join(RUN, "gen", f"{sid}__V.jpg"), f"{sid}__V.jpg"),
                       f"the version<span class='n'>{html.escape(v) or 'indistinguishable from the control'}</span>",
                       "ship" if v.startswith("fix") else ("bad" if v else ""))
                 + "</div>")
    o.append(VFOOT + "</div>" + LB + SCRIPT)
    dst = embed_to or os.path.join(REPORT, "v33_version.html")
    open(dst, "w").write("\n".join(o))
    print(f"{dst}  ({os.path.getsize(dst)/1e6:.1f} MB)")


VHEAD = None
P7HEAD = None
P6HEAD = None
P5HEAD = None
P4HEAD = None
P3HEAD = None
P2HEAD = None
PHEAD = None  # set below
HEAD = """<title>Klein as the Extractor</title>
<meta name='viewport' content='width=device-width,initial-scale=1'>
<style>
:root{--bg:#0d0d10;--fg:#e8e8ea;--dim:#8a8a94;--line:#26262c;--acc:#7c5cff;--good:#3fb950;--bad:#f0655a}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
 font:15px/1.6 ui-sans-serif,-apple-system,"Segoe UI",Roboto,sans-serif}
.wrap{max-width:1620px;margin:0 auto;padding:30px 26px 0}
h1{margin:0 0 6px;font-size:25px}
h2{font-size:14px;margin:48px 0 8px;padding-top:14px;border-top:1px solid var(--line);
 display:flex;gap:10px;align-items:center;flex-wrap:wrap}
h2 .ar{font-size:12px;color:var(--dim);font-weight:400}
.t{font-size:9.5px;padding:1px 7px;border-radius:20px;background:#12211a;
 border:1px solid #2c5c33;color:var(--good);font-weight:400}
.t.bad{background:#2a1512;border-color:#7a3a33;color:var(--bad)}
.lede{color:var(--dim);max-width:96ch;font-size:14px;margin:0 0 14px}
.lede b{color:var(--fg)}
.q{border-left:3px solid var(--acc);padding:2px 0 2px 14px;margin:14px 0;max-width:98ch;
 font-size:13.5px;color:#c8c8d0}
.q b{color:var(--fg)}
.lab{font-size:11.5px;color:var(--dim);margin:14px 0 5px}
.lab b{color:var(--fg)}
.strip{display:grid;gap:5px;margin-bottom:6px}
.s3{grid-template-columns:repeat(3,minmax(0,1fr));max-width:1200px}
.s5{grid-template-columns:repeat(5,minmax(0,1fr));max-width:1500px}
.s6{grid-template-columns:repeat(6,minmax(0,1fr))}
.s4{grid-template-columns:repeat(4,minmax(0,1fr));max-width:1400px}
.s8{grid-template-columns:repeat(8,minmax(0,1fr))}
.s9{grid-template-columns:repeat(9,minmax(0,1fr))}
@media(max-width:1100px){.s9{grid-template-columns:repeat(3,minmax(0,1fr))}}
.s7{grid-template-columns:repeat(7,minmax(0,1fr))}
.s4{grid-template-columns:repeat(4,minmax(0,1fr));max-width:1400px}
.s8{grid-template-columns:repeat(8,minmax(0,1fr))}
.s10{grid-template-columns:repeat(10,minmax(0,1fr))}
.g5{grid-template-columns:repeat(5,minmax(0,1fr))}
@media(max-width:1100px){.s7,.s8,.s10{grid-template-columns:repeat(4,minmax(0,1fr))}}
h2.sec{font-size:20px;margin-top:70px;border-top:2px solid var(--acc)}
@media(max-width:700px){.s3{grid-template-columns:1fr}}
figure{margin:0}
figure img{width:100%;display:block;background:#fff;border-radius:6px;cursor:zoom-in;
 aspect-ratio:3/4;object-fit:contain}
figure.ship img{outline:2px solid #2c5c33;outline-offset:-2px}
figure.ship figcaption{color:var(--good);font-weight:700}
figure.bad img{outline:2px solid #7a3a33;outline-offset:-2px}
figure.bad figcaption{color:var(--bad);font-weight:700}
figcaption{font-size:11px;color:var(--dim);text-align:center;padding:5px 2px;line-height:1.4}
figcaption .n{display:block;font-size:9.5px;opacity:.85;font-weight:400}
.ph{background:#17171d;border:1px dashed var(--line);border-radius:6px;aspect-ratio:3/4;
 display:flex;align-items:center;justify-content:center;color:var(--dim);font-size:11px}
details{max-width:1200px;font-size:12px;color:var(--dim)}
summary{cursor:pointer;color:var(--acc)}
pre{white-space:pre-wrap;margin:6px 0 0;font-size:11.5px;line-height:1.5}
#lb{display:none;position:fixed;inset:0;background:rgba(0,0,0,.96);z-index:99;
 align-items:center;justify-content:center;flex-direction:column;gap:10px;padding:16px}
#lb.on{display:flex}#lb img{max-width:96vw;max-height:92vh;object-fit:contain;background:#fff}
#lbc{color:var(--dim);font-size:13px}
footer{border-top:1px solid var(--line);margin-top:44px;padding:22px 0 30px;
 color:var(--dim);font-size:12.5px}
code{background:#1b1b22;padding:1px 5px;border-radius:4px;font-size:12px}
</style>
<div class='wrap'><h1>Klein as the extractor</h1>
<p class='lede'>v3.3 link 1. The v3.1 extraction call &mdash; A4 crop in, the per-pair
mannequin prompt, seed 46 &mdash; sent to <code>flux-2/klein/4b/distilled/edit</code>
instead of <code>qwen-image-edit-2511</code>. <b>Nothing else changes.</b> Stage one only:
what comes back is the reference, before any try-on edit. All 28 references of the run-B
fold, 28 calls, 0 failures. Click any image for full size.</p></div>
"""
NOTE = """<div class='q'><b>A4 crop</b> is BiRefNet_lite at 1024&sup2;, background to white,
cropped to the subject, <b>head kept</b> &mdash; the files v3.1 link 10 made, reused not
recomputed. <b>Klein mannequin</b> is the candidate. <b>Qwen mannequin</b> is the v3.1
reference already on disk, generated <b>before dynamic prompting</b> (no pose clause),
so it is orientation and not a controlled comparison. The colour and framing the CPU
readers produced sit above every row, so a bad output traces to a bad read.</div>
<div class='q'><b>Link 1.3, added after review &mdash; MH, the head swap.</b> Reviewer's verdict on
everything below the mannequin: unusable. Klein is an editor, so ask it for an edit:
<i>"Replace this person's head with a smooth, featureless mannequin head of the same size, in
the same position and facing the same way &mdash; no face, no hair. Keep the clothing, the body,
the hands, the pose and the background exactly as they are."</i> Then the A4 crop. <b>28/28
clean; no garment pixel is regenerated.</b> It is BC with a mannequin head instead of a scalp
&mdash; the green column in each row.</div>
<div class='q'><b>Gate checks:</b> outfit complete &middot; person gone &middot; extent
matches the crop &middot; colour on the mannequin, not the garment &middot; fidelity.
The first four pass on <b>28/28</b>. Fidelity is where klein diverges: <b>7 flagged,
5 serious</b> &mdash; sequin, satin, embroidery and pleats come back as their nearest
smooth material, and two ambiguous hems became two legs. Flagged rows are outlined red
and the reason is in the heading.</div>"""
GHEAD = HEAD.replace("<title>Klein as the Extractor</title>", "<title>Klein, Clothes Only</title>") \
    .split("<div class='wrap'><h1>")[0] + """<div class='wrap'><h1>Klein, clothes only</h1>
<p class='lede'>v3.3 links 1.1 and 1.2. The same A4 crop and seed as link 1, and no mannequin
asked for: five wordings for "the outfit alone", each sent to
<code>flux-2/klein/4b/distilled/edit</code>. Red outline and a reason under the caption where
a column failed a gate check; green outline on the two usable candidates. Click any image
for full size.</p></div>"""
PHEAD = HEAD.replace("<title>Klein as the Extractor</title>", "<title>Klein Re-poses the Wearer</title>") \
    .split("<div class='wrap'><h1>")[0] + """<div class='wrap'><h1>Can klein pose the person?</h1>
<p class='lede'>v3.3 link 1.4. The head swap (<b>MH</b>, the most promising arm in v3.3) plus one
thing per column: a constant pose sentence, pose + extent from one table keyed on the framing
read (v3.1's rule: never name a body part the crop excludes), the extent sentence alone, and
a head colour from the tone reader on the paired person. All 28 references, same seed. Green
outline on the two candidates for link 2; red where a column failed. Click any image for full
size.</p></div>"""
P2HEAD = HEAD.replace("<title>Klein as the Extractor</title>", "<title>Feet, Hips, and Where the Mannequin Stops</title>") \
    .split("<div class='wrap'><h1>")[0] + """<div class='wrap'><h1>Phase 2 &mdash; the version on the crop</h1>
<p class='lede'>v3.3 links 3 and 4. For the first time the A4 crop goes in <b>before</b> klein, and
the prompt is the version's: head swap + the dynamic pose+framing clause, no colour word. <b>P0</b> is
that template. P1&ndash;P3 add one sentence about the legs and feet; M1&ndash;M4 change only the
head-swap sentence. Every added sentence is itself keyed on the framing read, so a cell whose
wording would equal P0's is not re-run and shows P0's frame. Click any image for full size.</p></div>"""
P2NOTE = """<div class='q'><b>Cases named by the reviewer:</b> <code>g013</code> and <code>g009</code>
for the legs and feet (link 3); <code>g027</code> and <code>g029</code> for mannequin material on
the neck and arms (link 4); <code>emma_watson</code>, which duplicated in phase 1 on the full frame
and should not on the crop. <b>P3</b> and <b>M4</b> are the reviewer's "no &hellip;" form &mdash;
v3.1 rule 1 predicts they name the slot they forbid.</div>
<div class='q'><b>Result.</b> Crop-first works: P0 holds the extent on 28/28 and emma_watson no longer
duplicates. <b>No pose sentence earns a place</b> &mdash; feet already near-straight on P0, the feet
sentence moves g009 marginally, and <b>P2's "legs straight" on a waist-up crop invents legs on 4 of 8</b>.
P3's negation did nothing either way: a negation fills its slot only when the slot is empty. <b>No
region wording reaches the neck</b> &mdash; it blends with the head under all four, and "face only"
renders a face. Two costs of the re-pose surfaced: g013's sandals became bare feet, scarlett's split
hem became trousers. Three cells were black at seed 46 (checker on or off) and were re-run at seed 47.</div>"""
P2FOOT = """<footer>Inputs <code>inputs/{garment}__A4.jpg</code>, outputs <code>refs/{garment}__p2_{arm}raw.jpg</code>
(klein) and <code>refs/{garment}__p2_{arm}.jpg</code> (bbox re-crop), prompts as sent
<code>_v33_p2_prompts.json</code>, run <code>v3/build/run_v33_phase2.py</code> &middot; rebuild
<code>python3 v3/build/v33_page.py --phase2</code>. Set-up and verdicts: <code>prd/v3/v3.3/RESULTS.md</code> &sect;6.</footer>"""
P3HEAD = HEAD.replace("<title>Klein as the Extractor</title>", "<title>Holding the Garment Through the Pose</title>") \
    .split("<div class='wrap'><h1>")[0] + """<div class='wrap'><h1>Phase 3 &mdash; pose words, garment held</h1>
<p class='lede'>v3.3 link 5. The version's template &mdash; A4 crop, head swap from the neck up (M1),
the dynamic pose+framing clause &mdash; plus one sentence per column. <b>Q0</b> is that template.
Q1 "legs straight"; Q2 legs straight + "a dress stays a dress, a skirt stays a skirt"; <b>Q3</b> "the
clothing stays exactly the same through the change of pose"; Q4 "feet point towards the camera";
Q5 all three. Each fires only where the part it names is in frame. Click any image for full size.</p></div>"""
P3NOTE = """<div class='q'><b>Result: Q3 is the fix and is now in the version's prompt.</b> It keeps
scarlett's dress a dress with the slit intact, on all 28, and invents nothing. <b>Q2 and Q5, which
name garment types, put a skirt over the trousers on three men</b> &mdash; rule 1 in its positive
form. Q1 and Q4 are indistinguishable from Q0; Q4 still splits scarlett. g013's sandals stay bare
feet under every arm &mdash; footwear is a cost of the re-pose that wording does not recover.
Two cells were black at seed 46 and re-run at seed 47.</div>
<div class='q'><b>After review:</b> g012 under Q3 grows a <b>third foot</b> (flagged). Two probes on the
Q3 prompt: <b>Q6 "Feet straight."</b> on the 19 full-body &mdash; indistinguishable from Q3 except g012,
which returns two feet (one case, not adopted); <b>A1/A2 arms sentences on p030</b> &mdash; both bring
the arms down (green), deferred to after call 2. <b>Q0 and Q3 go into call 2.</b></div>"""
P3FOOT = """<footer>Outputs <code>refs/{garment}__p3_{arm}raw.jpg</code> / <code>.jpg</code>, prompts
<code>_v33_p3_prompts.json</code>, run <code>v3/build/run_v33_phase3.py</code> &middot; rebuild
<code>python3 v3/build/v33_page.py --phase3</code>. Verdicts: <code>prd/v3/v3.3/RESULTS.md</code> &sect;7.</footer>"""
P4HEAD = HEAD.replace("<title>Klein as the Extractor</title>", "<title>One Model, Two Calls</title>") \
    .split("<div class='wrap'><h1>")[0] + """<div class='wrap'><h1>Phase 4 &mdash; the edit</h1>
<p class='lede'>v3.3 link 2. For the first time a v3.3 reference goes through call 2. Upper row of each
block: the person and four references &mdash; <b>Q0</b> (klein head swap + pose+framing, crop-first),
<b>Q3</b> (the version: + the garment-hold sentence), and the two incumbents <b>BC</b> (bald pass) and
<b>MQ</b> (v3.1's Qwen mannequin). Lower row: what the same klein edit, same prompt, same seed 46 made
from each. Q0 and Q3 make the pipeline <b>one model, two calls</b>; BC and MQ are what they have to
beat. Click any image for full size.</p></div>"""
P4NOTE = """<div class='q'><b>Cases to read first:</b> the pairs whose reference carries a known
re-pose cost &mdash; g013 (bare feet), g012 (Q3 third foot), scarlett (Q0 trousers vs Q3 dress), p030
(arms up) &mdash; and the v3.1 hard pairs g011/p019 (exposed skin) and zendaya (white on white).
</div>
<div class='q'><b>Result: at the output, Q3 is indistinguishable from BC and MQ on 24 of 28 pairs.</b> The
same edit makes the same try-on from a klein reference as from a Qwen one &mdash; one model, two calls,
at parity with v3.1's locked arm by eye. Every difference on the other four traces to the reference:
scarlett's hem comes through as whatever the reference made of it (Q0 trousers, Q3 dress &mdash; the
hold sentence pays here); bags in the reference are worn in the output on Q0/Q3/BC, and MQ alone is
without them because Qwen dropped them at extraction. g013's bare feet and g012's third foot did not
propagate &mdash; the person supplies those parts. p019 + g011 cooks on all four, as v3.1 predicted
for any reference. Unscored.</div>"""
P4FOOT = """<footer>Outputs <code>gen/{set_id}__Q0.jpg</code>, <code>gen/{set_id}__Q3.jpg</code> beside the
v3.1 <code>__BC</code> and <code>__MQ</code>; run <code>v3/build/run_v33_edit.py</code>, record
<code>_v33_edit.json</code> &middot; rebuild <code>python3 v3/build/v33_page.py --phase4</code>.
Set-up and verdicts: <code>prd/v3/v3.3/RESULTS.md</code> &sect;8.</footer>"""
P5HEAD = HEAD.replace("<title>Klein as the Extractor</title>", "<title>Feet Out of the Reference</title>") \
    .split("<div class='wrap'><h1>")[0] + """<div class='wrap'><h1>Phase 5 &mdash; feet out of the reference</h1>
<p class='lede'>v3.3 link 6, probe on the two references with known foot defects. Four ways of taking the
feet out of the Q3 reference &mdash; a CPU cut at the ankles after klein, the same cut but never through a
hem, the cut on the crop before klein so the clause never names feet, and a prompt sentence &mdash; each
through the edit on its own pair, beside the uncut control. Click any image for full size.</p></div>"""
P5NOTE = """<div class='q'><b>Result: null.</b> With the feet cut out by three different routes, both outputs
are indistinguishable from the control. The output's feet are the wearer's own; p021's "four legs" are two
trouser legs over spread knees plus her sneakers &mdash; a seated-pose property of the person, which no
reference edit reaches. The cut is safe (no boundary line came back) but buys nothing. R4 named the feet
to exclude them and rendered them. Not extended to the fold; feet stay in the reference.</div>"""
P5FOOT = """<footer>References <code>refs/{garment}__p5_{arm}.jpg</code>, outputs <code>gen/{set_id}__{arm}.jpg</code>,
cut rows and prompts <code>_v33_p5_prompts.json</code>, run <code>v3/build/run_v33_feet.py</code> &middot; rebuild
<code>python3 v3/build/v33_page.py --phase5</code>. <code>prd/v3/v3.3/RESULTS.md</code> &sect;9.</footer>"""
P6HEAD = HEAD.replace("<title>Klein as the Extractor</title>", "<title>Words in the Edit</title>") \
    .split("<div class='wrap'><h1>")[0] + """<div class='wrap'><h1>Phase 6 &mdash; the first change to call 2</h1>
<p class='lede'>v3.3 link 7. The edit prompt has been a constant since V2; p021's third tube comes from
image 1's layout, which only call 2 sees. Four sentences appended to the edit prompt &mdash; the
reviewer's "do not add any body parts", a positive count, a grounding in image 1, and a garment-side
drape &mdash; on the failing pair and three clean ones, with the Q3 reference held fixed. Click any image
for full size.</p></div>"""
P6NOTE = """<div class='q'><b>Result: yes &mdash; with the grounded positive, and only that.</b> <b>E3</b>,
"the person's body, limbs and feet are exactly as in image 1 &mdash; nothing added, nothing removed", removes
the third tube on p021 (read at full size: the fabric spans both knees as one width) and changes nothing on
the three clean pairs. E2's count removed it too, but by re-rendering the person with identity and pose
drift on all three. E1's negation does nothing either way; E4 is partial with a side effect. E3 is v3.1's
rule 2 &mdash; tell the model what is there &mdash; reaching call 2 for the first time. Validated on all 28
below before adoption.</div>"""
P6FOOT = """<footer>Outputs <code>gen/{set_id}__E{n}.jpg</code>, prompts <code>_v33_edit2.json</code>, run
<code>v3/build/run_v33_edit2.py</code> &middot; rebuild <code>python3 v3/build/v33_page.py --phase6</code>.
<code>prd/v3/v3.3/RESULTS.md</code> &sect;10.</footer>"""
P7HEAD = HEAD.replace("<title>Klein as the Extractor</title>", "<title>Arms Down</title>") \
    .split("<div class='wrap'><h1>")[0] + """<div class='wrap'><h1>Phase 7 &mdash; arms in partial crops</h1>
<p class='lede'>v3.3 link 8. The chest_up row of PERSON_CLAUSE was the only row that said nothing about
the arms, and p030's raised arms stayed raised under it. The row now reads "&hellip;shoulders level,
<b>arms down, relaxed at the sides</b>&hellip;". Because the clause is a table keyed on the framing read,
p030 is the only reference whose prompt changed; the other 27 are untouched. Click any image for full
size.</p></div>"""
P7NOTE = """<div class='q'><b>Result: the reference is fixed; the output is unchanged.</b> Arms down, bust
clear, chest-up framing held. The edit output is identical from either reference because the wearer
supplies his own arms &mdash; the same neutrality every reference-pose change has shown where the
person's pose dominates. Adopted as a row of the table.</div>"""
P7FOOT = """<footer>Reference <code>refs/p030__p7_Q3.jpg</code>, output <code>gen/p002+p030__P7E3.jpg</code>, record
<code>_v33_p7.json</code>, run <code>v3/build/run_v33_arms.py</code> &middot; rebuild
<code>python3 v3/build/v33_page.py --phase7</code>. <code>prd/v3/v3.3/RESULTS.md</code> &sect;11.</footer>"""
VHEAD = HEAD.replace("<title>Klein as the Extractor</title>", "<title>The v3.3 Version</title>") \
    .split("<div class='wrap'><h1>")[0] + """<div class='wrap'><h1>The v3.3 version, whole, on the fold</h1>
<p class='lede'>Every adopted piece run together on all 28 pairs: A4 crop &rarr; klein head swap from the neck
up + pose+framing clause (with the arms row) + garment-hold sentence &rarr; bbox re-crop &rarr; ankle cut
&rarr; klein edit with the E3 sentence. One model, two calls. Beside it, the control that differs only by
the ankle cut. Click any image for full size.</p></div>"""
VNOTE = """<div class='q'><b>Result: indistinguishable from the control on 27 of 28.</b> The one difference is
the cut doing what it was adopted for &mdash; on p025 + g024 the wearer keeps her own boots instead of the
reference's shoes. No identity, background, garment or accessory change anywhere else. p021 stays fixed;
scarlett stays a dress; p019 + g011 still cooks (a pairing defect no reference reaches). <b>Q3 and E3
approved by the reviewer; this is the version in SOLUTION.md.</b> Unscored.</div>"""
VFOOT = """<footer>References <code>refs/{garment}__V.jpg</code>, outputs <code>gen/{set_id}__V.jpg</code>, record
<code>_v33_version.json</code>, run <code>v3/build/run_v33_version.py</code> &middot; rebuild
<code>python3 v3/build/v33_page.py --version</code>. <code>prd/v3/v3.3/SOLUTION.md</code>; evidence
<code>RESULTS.md</code> &sect;12.</footer>"""
PNOTE = """<div class='q'><b>Result: klein re-poses the person, and only the framing-keyed
sentence keeps it honest.</b> <b>MH pose</b> and <b>MH pose + framing</b> say the same thing
about the pose; the first names feet regardless and invents a whole standing body on 8 of the
9 partial crops (emma_watson comes back as two), the second is keyed on the read and holds the
extent on 28/28. Prints, sequins, pleats and colour survive the re-pose. <b>MH colour</b> binds
the word to the head and nothing else, 28/28. <b>MH framing only</b> is indistinguishable from
MH.</div>
<div class='q'>A re-pose re-renders the garment wherever a limb moves; MH never does. The two
green columns are the link-2 pair: <i>does a neutral pose in the reference beat a faithful
one?</i></div>"""
PFOOT = """<footer>References <code>refs/{garment}__{arm}raw.jpg</code> (klein) and
<code>refs/{garment}__{arm}.jpg</code> (A4 crop), prompts as sent <code>_v33_pose_prompts.json</code>,
run <code>v3/build/run_v33_pose.py</code> &middot; rebuild <code>python3 v3/build/v33_page.py --pose</code>.
Verdicts: <code>prd/v3/v3.3/RESULTS.md</code> &sect;5.</footer>"""
GNOTE = """<h2 class='sec'>Links 1.1 and 1.2 &mdash; drop the mannequin</h2>
<div class='q'><b>Reviewer's verdict on link 1: the klein mannequins are poor.</b> Hypothesis:
a 4B distilled model cannot render a plausible body <i>and</i> hold the garment, so it trades
the garment away. So: ask for the clothes alone. Every klein column below is the same A4 crop
and seed. Extent is <b>dynamic</b> on every variant except <b>k4</b> (v3.1's QX prompt verbatim,
the control) and <b>k1 no extent</b> (the ablation); no colour word, there is no mannequin to
colour. k2 and k3 died on the 8-reference probe and were not run further.</div>
<div class='q'><b>k1 ghost</b> &mdash; the outfit as worn by an invisible body. <b>k4 qx</b>
&mdash; "the clothing, isolated, remove the person entirely". <b>k5 form</b> &mdash; an
<i>invisible mannequin</i> the clothes hold the shape of, with v3.1's own extent+pose clause.
<b>k6</b> &mdash; k1 plus the body's absence stated part by part. <b>Result over 28:</b>
k4 removes the person 28/28 but presents flat and drops a piece on 2; k1 keeps drape and every
piece but leaks skin on 9 &mdash; always legs, hands or a neckline the garment exposes; <b>k5's
"invisible mannequin" rendered a white mannequin on 27/28</b> (fidelity good, white-on-white
back); <b>k6's "no hand, no leg, no face" rendered a grey body with hands, legs and a face on
24/28</b>. Naming a slot fills it, even to say it is empty. The last column is Qwen &mdash;
v3.1's dynamic-prompt reference on the 8 references that have one, pre-dynamic elsewhere,
labelled per cell.</div>"""
FOOT = """<footer>References <code>refs/{garment}__MK__{person}.jpg</code>, prompts as sent
<code>_v33_prompts.json</code>, run <code>v3/build/run_v33_extract.py</code> &middot;
rebuild <code>python3 v3/build/v33_page.py</code>. Verdicts: <code>prd/v3/v3.3/RESULTS.md</code>.</footer>"""
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
    main(sys.argv[sys.argv.index("--embed") + 1] if "--embed" in sys.argv else None,
         "garment" if "--garment" in sys.argv else "pose" if "--pose" in sys.argv else "phase2" if "--phase2" in sys.argv else "phase3" if "--phase3" in sys.argv else "phase4" if "--phase4" in sys.argv else "phase5" if "--phase5" in sys.argv else "phase6" if "--phase6" in sys.argv else "phase7" if "--phase7" in sys.argv else "version" if "--version" in sys.argv else "all")
