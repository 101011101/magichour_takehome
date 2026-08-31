"""Every cell the reviewer scored against v3.3 (V lost, or both failed), with the whole
chain: person, garment photograph, A4 crop, V reference, BC reference, V output, BC output.
Grouped by the failure classes of RESULTS §14.5.

  python3 v3/build/ironman_failures_page.py [--embed out.html]
"""
import base64, csv, html, io, os, sys
from PIL import Image
REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RUN = os.path.join(REPO, "v3", "runs", "ironman", "20260830_0548")
REPORT = os.path.join(REPO, "v3", "report"); IMG = os.path.join(REPORT, "img_imf")
EMBED = None

CLASSES = {
 "F1": ("The wearer's own clothing survives where the new garment exposes it", "person side, both arms"),
 "F2": ("Skirt / dress rendered as trousers on a male or legs-apart wearer", "person side, both arms"),
 "F3": ("V's regenerated reference drifts from the photograph (colour, dropped pieces, hem)", "reference side, V only"),
 "F4": ("Exposed-skin pairing (v3.1 §3c.31)", "person side, both arms"),
 "F5": ("Wearer's headwear / bag kept; scene", "by design / lighting"),
 "F?": ("Not classified", ""),
}
def classify(sid):
    p, g = sid.split("+", 1)
    if p in ("dualuse_lp_floral_kimono_set",) or sid in ("g004+g005", "p001+p014", "p011+p024", "p018+dualuse_lp_navy_quarterzip_knit_LOWRES", "p020+p021", "p020+dualuse_navy_peacoat_onmodel", "dualuse_navy_peacoat_onmodel+g012", "g014+g029"): return "F1"
    if g in ("dualuse_zendaya_white_blazer_skirt",) or sid in ("g005+g014", "dualuse_emma_watson_black_blazer_armscrossed+dualuse_scarlett_johansson_black_dress_backview_night", "p013+dualuse_scarlett_johansson_black_dress_backview_night", "g024+p002", "g029+p004"): return "F2"
    if sid in ("p003+p004", "dualuse_zendaya_white_blazer_skirt+dualuse_navy_peacoat_onmodel", "g018+g024", "dualuse_lp_plaid_overcoat_brown_suit+g029", "dualuse_navy_peacoat_onmodel+g030", "p028+g015", "p015+p016", "p011+p016", "p011+p012", "g027+g029", "p026+g013", "p030+g024", "p030+dualuse_queen_latifah_gown_stage", "dualuse_scarlett_johansson_black_dress_backview_night+dualuse_woman_top_denim_skirt_nonceleb", "p003+p026"): return "F3"
    if sid in ("p019+dualuse_gal_gadot_blue_dress_redcarpet", "g027+p003"): return "F4"
    if p in ("p011", "p013", "p018", "p020"): return "F5"
    return "F?"

def src(path, w=380):
    if not os.path.exists(path): return None
    im = Image.open(path).convert("RGB"); im.thumbnail((w, 520))
    if EMBED:
        b = io.BytesIO(); im.save(b, "JPEG", quality=74, optimize=True)
        return "data:image/jpeg;base64," + base64.b64encode(b.getvalue()).decode()
    os.makedirs(IMG, exist_ok=True); out = os.path.join(IMG, os.path.basename(path))
    if not os.path.exists(out): im.save(out, quality=86, optimize=True)
    return "img_imf/" + os.path.basename(path)

def fig(path, cap, cls=""):
    s = src(path)
    return (f"<figure class='{cls}'><img src='{s}' alt='{html.escape(cap)}' loading='lazy'><figcaption>{cap}</figcaption></figure>" if s
            else f"<figure class='miss'><div class='ph'>missing</div><figcaption>{cap}</figcaption></figure>")

def main(embed=None):
    global EMBED; EMBED = embed
    key = {(r["set_id"], r["label"]): r["arm"] for r in csv.DictReader(open(os.path.join(RUN, "key.csv")))}
    votes = list(csv.DictReader(open(os.path.join(REPO, "v33_ironman_votes_bca4.csv"))))
    scores = {(r["set_id"], r["arm"], r["seed"]): r for r in csv.DictReader(open(os.path.join(RUN, "meta", "vlm_scores.csv")))}
    cells = []
    for v in votes:
        w = key[(v["set_id"], v["vote"])] if v["vote"] in ("A", "B") else v["vote"]
        if w in ("BC", "fail"): cells.append({**v, "winner": w, "cls": classify(v["set_id"])})
    groups = {}
    for c in cells: groups.setdefault(c["cls"], []).append(c)
    o = [HEAD, "<div class='wrap'>", f"<h1>Where v3.3 fails</h1><p class='lede'>Every cell the reviewer scored against the version on the iron-man run &mdash; "
         f"<b>{sum(1 for c in cells if c['winner']=='BC')} BC-klein (BCA4) wins</b> and <b>{sum(1 for c in cells if c['winner']=='fail')} both-fail</b> cells "
         f"out of 599 &mdash; grouped by the failure classes of RESULTS &sect;14.5. Each row is the whole chain: the two inputs, the A4 crop, "
         f"the two references, the two outputs. Reference arm here is BCA4 (bald &rarr; A4 crop, head kept), not BC_klein proper.</p>"]
    for k in ("F1", "F2", "F3", "F4", "F5", "F?"):
        if k not in groups: continue
        t, side = CLASSES[k]
        o.append(f"<h2 class='sec'>{k} &mdash; {html.escape(t)}<span class='ar'>{html.escape(side)} &middot; {len(groups[k])} cells</span></h2>")
        for c in sorted(groups[k], key=lambda c: (c["set_id"], c["seed"])):
            sid, seed, p, g = c["set_id"], c["seed"], *c["set_id"].split("+", 1)
            verdict = "both fail" if c["winner"] == "fail" else "BC klein better"
            nud = f" &middot; nudge: {html.escape(c['nudge'])}" if c.get("nudge") else ""
            sv = scores.get((sid, "V", seed)); note = html.escape(sv["note"]) if sv else ""
            vs = (f"VLM V: garment {sv['garment']} identity {sv['identity']} scene {sv['scene']} clean {sv['clean']} hands {sv['hands']} realism {sv['realism']}" if sv else "VLM: not scored")
            o.append(f"<h2>{html.escape(p)} wears {html.escape(g)} &middot; seed {seed}<span class='t bad'>{verdict}{nud}</span></h2>")
            o.append(f"<div class='lab'>{vs}" + (f" &mdash; <i>{note}</i>" if note else "") + "</div>")
            o.append("<div class='strip s7'>"
                     + fig(os.path.join(RUN, "inputs", f"{p}.jpg"), "person &mdash; image 1")
                     + fig(os.path.join(RUN, "inputs", f"{g}.jpg"), "garment photograph")
                     + fig(os.path.join(RUN, "inputs", f"{g}__A4.jpg"), "A4 crop<span class='n'>BiRefNet, head kept</span>")
                     + fig(os.path.join(RUN, "refs", f"{g}__V.jpg"), "V reference<span class='n'>head swap + re-pose + hold, ankle cut</span>")
                     + fig(os.path.join(RUN, "refs", f"{g}__BC.jpg"), "BCA4 reference<span class='n'>bald pass, A4 crop</span>")
                     + fig(os.path.join(RUN, "gen", f"{sid}__V__s{seed}.jpg"), "<b>v3.3 output</b>", "bad" if c["winner"] != "tie" else "")
                     + fig(os.path.join(RUN, "gen", f"{sid}__BC__s{seed}.jpg"), "<b>BC klein output</b>", "ship" if c["winner"] == "BC" else ("bad" if c["winner"] == "fail" else ""))
                     + "</div>")
    o.append(FOOT + "</div>" + LB + SCRIPT)
    dst = embed or os.path.join(REPORT, "v33_ironman_failures.html")
    open(dst, "w").write("\n".join(o)); print(dst, len(cells), "cells", f"{os.path.getsize(dst)/1e6:.1f} MB")

HEAD = """<title>Where v3.3 Fails</title>
<meta name='viewport' content='width=device-width,initial-scale=1'>
<style>
:root{--bg:#0d0d10;--fg:#e8e8ea;--dim:#8a8a94;--line:#26262c;--acc:#7c5cff;--good:#3fb950;--bad:#f0655a}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.6 ui-sans-serif,-apple-system,"Segoe UI",Roboto,sans-serif}
.wrap{max-width:1700px;margin:0 auto;padding:30px 26px 0}h1{margin:0 0 6px;font-size:25px}
h2{font-size:14px;margin:34px 0 6px;padding-top:12px;border-top:1px solid var(--line);display:flex;gap:10px;align-items:center;flex-wrap:wrap}
h2.sec{font-size:20px;margin-top:56px;border-top:2px solid var(--acc)}h2 .ar{font-size:12px;color:var(--dim);font-weight:400}
.t{font-size:10px;padding:1px 8px;border-radius:20px;border:1px solid #7a3a33;background:#2a1512;color:var(--bad);font-weight:400}
.lede{color:var(--dim);max-width:100ch;font-size:14px;margin:0 0 14px}.lede b{color:var(--fg)}
.lab{font-size:11.5px;color:var(--dim);margin:0 0 6px}.lab i{color:#b0b0bb}
.strip{display:grid;gap:5px}.s7{grid-template-columns:repeat(7,minmax(0,1fr))}@media(max-width:1100px){.s7{grid-template-columns:repeat(4,minmax(0,1fr))}}
figure{margin:0}figure img{width:100%;display:block;background:#fff;border-radius:6px;cursor:zoom-in;aspect-ratio:3/4;object-fit:contain;border:3px solid transparent}
figure.ship img{border-color:var(--good)}figure.bad img{border-color:#7a3a33}
figcaption{font-size:11px;color:var(--dim);text-align:center;padding:5px 2px;line-height:1.4}figcaption .n{display:block;font-size:9.5px;opacity:.85}
.ph{background:#17171d;border:1px dashed var(--line);border-radius:6px;aspect-ratio:3/4;display:flex;align-items:center;justify-content:center;color:var(--dim);font-size:11px}
#lb{display:none;position:fixed;inset:0;background:rgba(0,0,0,.96);z-index:99;align-items:center;justify-content:center;flex-direction:column;gap:10px;padding:16px}
#lb.on{display:flex}#lb img{max-width:96vw;max-height:92vh;object-fit:contain;background:#fff}#lbc{color:var(--dim);font-size:13px}
footer{border-top:1px solid var(--line);margin-top:44px;padding:22px 0 30px;color:var(--dim);font-size:12.5px}code{background:#1b1b22;padding:1px 5px;border-radius:4px;font-size:12px}
</style>
"""
FOOT = """<footer>Cells from <code>v33_ironman_votes_bca4.csv</code> unblinded through <code>key.csv</code>; classes hand-assigned per
<code>prd/v3/v3.3/RESULTS.md</code> &sect;14.5; VLM notes from <code>meta/vlm_scores.csv</code> where scored. Rebuild
<code>python3 v3/build/ironman_failures_page.py</code>.</footer>"""
LB = "<div id='lb'><img id='lbi' alt=''><div id='lbc'></div></div>"
SCRIPT = """<script>
document.addEventListener('click',e=>{const im=e.target.closest('figure img');if(!im)return;
document.getElementById('lbi').src=im.getAttribute('src');document.getElementById('lbc').textContent=im.getAttribute('alt');document.getElementById('lb').classList.add('on');});
document.getElementById('lb').addEventListener('click',()=>document.getElementById('lb').classList.remove('on'));
document.addEventListener('keydown',e=>{if(e.key==='Escape')document.getElementById('lb').classList.remove('on')});
</script>"""

if __name__ == "__main__":
    main(sys.argv[sys.argv.index("--embed") + 1] if "--embed" in sys.argv else None)
