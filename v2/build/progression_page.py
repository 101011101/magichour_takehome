# Progression grid — one page, three grids, y = input, x = iteration stage.
#
# Mock for the report: shows how each design decision moved the needle by
# lining up the same input across every iteration that touched it.
#   grid 1: the garment reference through every crop iteration
#   grid 2: Testset2 generations, base klein then the C1-C4 crop ladder
#   grid 3: the hard sets through the attention arms to the shipped composite
#
# Cells render only if the file exists; a missing stage shows an em dash so
# absent coverage reads as absent, not broken.
import html, os

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
ART = os.path.join(REPO, "v2", "artifacts")
OUT = os.path.join(ART, "progression_grid.html")
NL = chr(10)

CSS = """
:root{--bg:#0d0d10;--fg:#e8e8ea;--dim:#8a8a94;--line:#26262c;--acc:#7c5cff;
 --good:#3fb950;--mid:#d29922;--bad:#f85149}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
 font:14px/1.55 ui-sans-serif,-apple-system,"Segoe UI",Roboto,sans-serif}
header{padding:26px 30px 16px;border-bottom:1px solid var(--line)}
h1{margin:0 0 6px;font-size:20px}
h2{margin:34px 30px 4px;font-size:16px}
.sub{color:var(--dim);max-width:96ch}
.sec-sub{color:var(--dim);margin:0 30px 14px;max-width:96ch;font-size:13px}
.gridwrap{margin:0 30px 10px;border:1px solid var(--line);border-radius:10px;
 overflow-x:auto}
.grid{display:grid;gap:0;width:max-content}
.hcell,.rcell,.cell{padding:8px 10px;border-bottom:1px solid var(--line);
 border-right:1px solid var(--line)}
.hcell{position:sticky;top:0;background:#141419;z-index:3;font-size:12px;
 font-weight:600;min-height:64px}
.hcell .hn{color:var(--dim);font-weight:400;font-size:11px;display:block;margin-top:2px}
.rcell{position:sticky;left:0;background:#141419;z-index:2;width:190px;font-size:12px}
.rcell b{font-size:12.5px;word-break:break-word}
.rcell .rn{color:var(--dim);font-size:11px;display:block;margin-top:4px}
.corner{position:sticky;left:0;top:0;z-index:4;background:#141419}
.cell{background:var(--bg)}
.cell img{width:150px;background:#fff;border-radius:4px;display:block;cursor:zoom-in}
.cell .miss{width:150px;height:150px;display:flex;align-items:center;justify-content:center;
 color:#3a3a44;font-size:20px;border:1px dashed var(--line);border-radius:4px}
.badge{display:inline-block;font-size:10.5px;font-weight:600;border-radius:9px;
 padding:0 7px;margin-top:5px}
.badge.perfect{color:#06210d;background:var(--good)}
.badge.ok{color:#241a00;background:var(--mid)}
.badge.fail{color:#2a0505;background:var(--bad)}
.badge.info{color:var(--dim);background:#1b1b22;border:1px solid var(--line)}
footer{color:var(--dim);font-size:12px;padding:20px 30px 40px}
#lb{position:fixed;inset:0;background:#000000f2;display:none;z-index:50;
 align-items:center;justify-content:center;flex-direction:column;gap:12px}
#lb img{max-width:94vw;max-height:84vh;background:#fff;border-radius:6px}
#lb .cap{color:var(--dim);font-size:13px}
"""

JS = """
const lb=document.getElementById('lb'),lbi=lb.querySelector('img'),
      lbc=lb.querySelector('.cap');
document.querySelectorAll('.cell img').forEach(im=>{
  im.addEventListener('click',()=>{lbi.src=im.src;lbc.textContent=im.dataset.cap||'';
    lb.style.display='flex';});
});
lb.addEventListener('click',()=>lb.style.display='none');
document.addEventListener('keydown',e=>{if(e.key==='Escape')lb.style.display='none';});
"""


def find(*rels):
    """First existing candidate, as a path relative to the artifacts dir."""
    for rel in rels:
        if rel and os.path.exists(os.path.join(REPO, rel)):
            return os.path.relpath(os.path.join(REPO, rel), ART)
    return None


def cell(src, cap="", badge=None):
    b = ""
    if badge:
        cls, txt = badge
        b = f'<span class="badge {cls}">{html.escape(txt)}</span>'
    if src is None:
        return f'<div class="cell"><div class="miss">&mdash;</div>{b}</div>'
    e = html.escape(src)
    return (f'<div class="cell"><img loading="lazy" src="{e}" '
            f'data-cap="{html.escape(cap)}">{b}</div>')


def grid(cols, rows):
    """cols: [(title, note)]; rows: [(label, rownote, [cell-html])]"""
    n = len(cols) + 1
    out = [f'<div class="gridwrap"><div class="grid" '
           f'style="grid-template-columns:190px repeat({n - 1},170px)">']
    out.append('<div class="hcell corner"></div>')
    for t, note in cols:
        out.append(f'<div class="hcell">{html.escape(t)}'
                   f'<span class="hn">{html.escape(note)}</span></div>')
    for label, rnote, cells in rows:
        out.append(f'<div class="rcell"><b>{html.escape(label)}</b>'
                   f'<span class="rn">{html.escape(rnote)}</span></div>')
        out.extend(cells)
    out.append('</div></div>')
    return NL.join(out)


def ref_original(stem):
    return find(f"v2/runs/ts2/inputs/{stem}.jpg",
                f"test_set/people/{stem}.jpg",
                f"Testset2/people/{stem}.jpg",
                f"Testset2/people/{stem}.jpeg",
                f"Testset2/clothes/{stem}.jpg",
                f"Testset2/clothes/{stem}.webp")


# ---------------------------------------------------------------- grid 1
G1_COLS = [
    ("original", "the worn reference as shot"),
    ("C1 bbox", "control - background untouched"),
    ("C2 no-bg", "wearer kept - solved 45%"),
    ("C3.2 keep hair", "gender flips; white space read as cloth - 45%"),
    ("C3.1 no face", "shipped v2.2.1 - 75%, but the head cut eats garment"),
    ("fringe exposed", "hair pixels that survive the cut, highlighted"),
    ("C4 clothes only", "hands punch holes through the garment"),
    ("OC5 over-crop", "dead end - radius inverse to the defect"),
    ("PRE2 repair first", "bald the photo, then crop - damage never exists"),
    ("PHEAD parser", "SegFormer head removal, deterministic"),
    ("BC_klein bald-crop", "klein bald pass, then subtraction"),
    ("QX qwen extract", "regenerates the garment - drift risk"),
]
G1_ROWS = [
    ("p021", "worst hair damage: 19.5% of garment lost; chair counted as subject"),
    ("p023", "16.9% lost; stool in the matte; BC_klein's only failures"),
    ("dualuse_woman_top_denim_skirt_nonceleb",
     "17.0% lost; garment source of the one set no crop solved"),
    ("dualuse_zendaya_white_blazer_skirt",
     "14.4% lost yet fine everywhere - damage % is non-monotonic"),
    ("p016", "hard crop fail (mask 1.4%); worst fringe 4.69%; ears 9px apart"),
    ("p028", "11.9% lost; casualty of the geometric head heuristics"),
    ("p009", "only 7.2% lost but control fails on all three people"),
    ("p019", "clothes guard protected 19.5% of the head as clothes"),
]


def grid1():
    rows = []
    for stem, note in G1_ROWS:
        cells = [
            cell(ref_original(stem), f"{stem} - original"),
            cell(find(f"v2/runs/crop_screen/{stem}__c1_bbox.jpg"), f"{stem} - C1"),
            cell(find(f"v2/runs/crop_screen/{stem}__c2_bbox_nobg.jpg"), f"{stem} - C2"),
            cell(find(f"v2/runs/crop_screen/{stem}__c32_no_face_keep_hair.jpg"),
                 f"{stem} - C3.2"),
            cell(find(f"v2/runs/crop_screen/{stem}__c3_no_face.jpg"), f"{stem} - C3.1"),
            cell(find(f"v2/runs/phase3/{stem}__FRINGE.jpg"), f"{stem} - fringe"),
            cell(find(f"v2/runs/crop_screen/{stem}__c4_clothes_only.jpg"),
                 f"{stem} - C4"),
            cell(find(f"v2/runs/phase3/{stem}__OC5.jpg"), f"{stem} - OC5"),
            cell(find(f"v2/runs/phase3/{stem}__PRE2.jpg"), f"{stem} - PRE2"),
            cell(find(f"v2/runs/amt/{stem}__PHEAD.jpg"), f"{stem} - PHEAD"),
            cell(find(f"v2/runs/amt/{stem}__BC_klein.jpg"), f"{stem} - BC_klein"),
            cell(find(f"v2/runs/acab/{stem}__QX_qwen_p1.jpg"), f"{stem} - QX"),
        ]
        rows.append((stem, note, cells))
    return grid(G1_COLS, rows)


# ---------------------------------------------------------------- grid 2
G2_COLS = [
    ("person", "input"),
    ("garment ref", "input, uncropped"),
    ("base klein", "v2.0 - uncropped reference"),
    ("C1 bbox", "background untouched"),
    ("C2 no-bg", "wearer kept"),
    ("C3.1 no face", "the arm that shipped"),
    ("C3.2 keep hair", "identity leaks back"),
    ("C4 clothes only", "aggressive, conditional"),
]
G2_ROWS = [
    ("ts2_09", "dualuse_hugh_jackman_grey_suit_outdoor",
     "dualuse_lp_plaid_overcoat_brown_suit",
     "AI artefacts + reference-outfit bleed; det metric 0.865 missed it"),
    ("ts2_11", "dualuse_emma_watson_black_blazer_armscrossed",
     "dualuse_man_black_suit_studio_nonceleb",
     "no transfer at all - VLM scored the no-op 4/5"),
    ("ts2_12", "dualuse_man_black_suit_studio_nonceleb",
     "dualuse_hugh_jackman_grey_suit_outdoor",
     "worst klein output on record: wrong person + clothes + bg + duplication"),
]


def grid2():
    rows = []
    for sid, person, garment, note in G2_ROWS:
        cells = [
            cell(ref_original(person), f"{sid} - person"),
            cell(ref_original(garment), f"{sid} - garment"),
            cell(find(f"v2/runs/ts2/outputs/klein_4b_edit__{sid}.png"),
                 f"{sid} - base klein"),
            cell(find(f"v2/runs/v221/c1_bbox__{sid}.png"), f"{sid} - C1"),
            cell(find(f"v2/runs/v221/c2_bbox_nobg__{sid}.png"), f"{sid} - C2"),
            cell(find(f"v2/runs/v221/c31_no_face__{sid}.png"), f"{sid} - C3.1"),
            cell(find(f"v2/runs/v221/c32_keep_hair__{sid}.png"), f"{sid} - C3.2"),
            cell(find(f"v2/runs/v221/c4_clothes_only__{sid}.png"), f"{sid} - C4"),
        ]
        rows.append((sid, note, cells))
    return grid(G2_COLS, rows)


# ---------------------------------------------------------------- grid 3
G3_COLS = [
    ("base klein", "uncropped, where it was run"),
    ("BALD_raw", "head removed, no crop - 85% cut"),
    ("control C3.1", "the v2.2.1 ship - collapses on damaged refs"),
    ("PHEAD", "cascade position 1"),
    ("BC_klein", "cascade position 2"),
    ("QX qwen", "cascade position 3 - the escalation"),
    ("shipped + SeedVR2", "harness pick - gate: noop / identity / garment / tryon"),
]
# (set_id, combo base stem or None, rownote, {arm: (badge-class, text)})
# Sets whose realism __after.png predates the identity-escalation rule and is
# therefore the wrong frame; the shipped cell falls back to the arm output.
SHIP_OVERRIDE = {"HD_p028+dualuse_navy_peacoat_onmodel": "QX_qwen_p1"}
G3_ROWS = [
    ("dualuse_man_black_suit_studio_nonceleb+dualuse_woman_top_denim_skirt_nonceleb",
     "dualuse_man_black_suit_studio_nonceleb__wears__dualuse_woman_top_denim_skirt_nonceleb",
     "the set no crop arm ever solved - jagged hair edge read as garment",
     {"PHEAD": ("fail", "fail"), "QX_qwen_p1": ("ok", "ok"),
      "after": ("ok", "lands ok")}),
    ("p015+p007", "p015__wears__p007",
     "worst identity import: base margin -0.933 (source face rendered)",
     {"BC_klein": ("fail", "fail")}),
    ("p018+p016", "p018__wears__p016",
     "skin-tone leak + hair 9.7%, just under the 14% router cut",
     {"PHEAD": ("fail", "fail"), "BC_klein": ("ok", "ok"),
      "QX_qwen_p1": ("perfect", "perfect")}),
    ("HD_p021", None,
     "worst damage garment (19.5%) - excluded from the first AMT set entirely",
     {"PHEAD": ("fail", "fail"), "BC_klein": ("perfect", "rescue"),
      "QX_qwen_p1": ("ok", "ok")}),
    ("HD_p023", None,
     "both subtraction arms fail; only regeneration recovers it",
     {"PHEAD": ("fail", "fail"), "BC_klein": ("fail", "fail"),
      "QX_qwen_p1": ("perfect", "rescue")}),
    # PHEAD substituted the person entirely (caught by eye, not statistic);
    # identity 0.755 < 0.90 now fires the gate, so the corrected harness ships
    # QX. The on-disk realism __after.png is the superseded PHEAD frame, so
    # this row's shipped cell points at the QX arm output instead.
    ("HD_p028+dualuse_navy_peacoat_onmodel", None,
     "was the one shipped fail: PHEAD swapped the person entirely; "
     "identity 0.755 added to the gate - now escalates to QX",
     {"PHEAD": ("fail", "person swapped"), "QX_qwen_p1": ("perfect", "perfect"),
      "after": ("perfect", "ships QX")}),
]


def grid3():
    rows = []
    for sid, combo, note, badges in G3_ROWS:
        base = find(f"v2/runs/combo/{combo}__base.png") if combo else None
        cells = [cell(base, f"{sid} - base klein",
                      None if base else None)]
        for arm in ("BALD_raw", "control", "PHEAD", "BC_klein", "QX_qwen_p1"):
            cells.append(cell(find(f"v2/runs/amt/gen/{sid}__{arm}.jpg"),
                              f"{sid} - {arm}", badges.get(arm)))
        ship = SHIP_OVERRIDE.get(sid)
        if ship:
            cells.append(cell(find(f"v2/runs/amt/gen/{sid}__{ship}.jpg"),
                              f"{sid} - shipped ({ship}, realism rerun pending)",
                              badges.get("after")))
        else:
            cells.append(cell(find(f"v2/runs/realism/{sid}__after.png"),
                              f"{sid} - shipped", badges.get("after")))
        rows.append((sid, note, cells))
    return grid(G3_COLS, rows)


def main():
    page = f"""<!doctype html><meta charset="utf-8">
<title>V2 progression grid — mock</title>
<style>{CSS}</style>
<header>
<h1>V2 progression grid</h1>
<div class="sub">Mock for the report. Three grids, one per era: rows are inputs,
columns are iteration stages in the order they were tried. Read left to right to
watch each design decision land; the row notes say what was broken. Click any
image to zoom. Stage history: prd/v2/v2.2/EXPERIMENT.md; case index:
prd/v2/EDGE_CASE_INDEX.md.</div>
</header>

<h2>1 &middot; The garment reference — crop iterations</h2>
<div class="sec-sub">C1&rarr;C4 are the v2.2.1 ladder (crop_screen). The fringe
column makes the C3.1 defect visible. OC5 is the recorded dead end. PRE2, PHEAD,
BC_klein and QX are the repairs that replaced patching. The last three columns
are the arms the shipped cascade actually chooses between.</div>
{grid1()}

<h2>2 &middot; Early generations — base klein, then the crop ladder (Testset2)</h2>
<div class="sec-sub">What v2.0 shipped and what conditioning the reference did to
it. These three sets are the traceability pairs from EXPERIMENT.md &sect;2b: the
baseline failed 4 of 7 duo pairs and the instruments missed most of it.</div>
{grid2()}

<h2>3 &middot; Hard sets — attention arms to the shipped composite</h2>
<div class="sec-sub">The v2.2.2/v2.2.3 era on the sets that resisted. base klein
is shown where the uncropped run exists (combo study); HD_ sets were born after
cropping so they have none. Badges are the human tier where recorded
(v223_perfect_tier_picks.csv). The last column is the harness pick under the
corrected gate (escalate on noop &lt; 0.5, identity &lt; 0.90, garment FAIL, or
tryon not PERFECT &mdash; 31 perfect / 7 ok / 0 fail at 2.158 gen/request); the
HD_p028 row's realism frame predates the identity rule, so its shipped cell
shows the QX arm output pending the SeedVR2 rerun.</div>
{grid3()}

<footer>Generated by v2/build/progression_page.py &middot; images referenced in
place from v2/runs/ &mdash; nothing copied.</footer>
<div id="lb"><img><div class="cap"></div></div>
<script>{JS}</script>
"""
    with open(OUT, "w") as f:
        f.write(page)
    missing = page.count('class="miss"')
    total = page.count('<div class="cell">')
    print(f"wrote {OUT}")
    print(f"cells: {total}, missing: {missing}")


if __name__ == "__main__":
    main()
