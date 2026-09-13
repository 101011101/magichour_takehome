"""Build the v3.7 page: can klein re-pose the wearer from a photograph of the target?

One question, shown rather than asserted. Per pair the card carries the two things call 1
was given - the garment photo and the target person - and then, per arm, the three images
that follow from them: what call 1 returned, the reference the V2 cropper made of it, and
the cell call 2 produced. `BC`, v3.1's incumbent, rides along on every card with its own
reference and cell, because the arm is BC with one input added and its value is whatever it
buys over BC, not whatever it looks like alone.

Two wordings are shown side by side (`BCp` asks for the pose third, `BCp2` declares image 2
a pose reference and asks first) so a failure reads as the model's rather than the prompt's.

Beside each arm sit the two measurements from `v37_pose_metrics.py`. `shift` is 0 when call 1
returned the source pose untouched and 1 when it reached the target's - but it is read
together with `base`, which says which input the output resembles globally, because the arm's
loudest failure is klein returning the TARGET's photograph with the garment swapped in, and
that scores `shift` near 1 while being no re-pose at all. `shift` is greyed out on pairs whose
source and target poses are too alike to tell apart. The eye and the detector are both on the
page, and they should agree.

The vote widget records what the images show that no metric does - whether image 2 leaked
into the output as clothing, face or background - and exports as CSV.

  python3 v3/build/v37_page.py [run_dir]        default v3/runs/v37/run
"""
import csv
import html
import json
import os
import sys

from PIL import Image

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RUN = sys.argv[1] if len(sys.argv) > 1 else os.path.join(REPO, "v3", "runs", "v37", "run")
SET = os.path.join(REPO, "v3", "testsets", "v35_linkC.csv")
REPORT = os.path.join(REPO, "v3", "report")
IMG = os.path.join(REPORT, "img_v37")
OUTP = os.path.join(REPORT, "v37.html")
SEED = 46

# arm, label, what it is, has a call-1 frame of its own
ARMS = [
    ("BCp",  "BCp",  "bald + &ldquo;re-pose to match image 2&rdquo;, asked third", True),
    ("BCp2", "BCp2", "image 2 declared a pose reference, pose asked first", True),
    ("BC",   "BC",   "the incumbent - bald only, one image in call 1", False),
]


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
    return "img_v37/" + dst, "img_v37/" + os.path.basename(full)


def fig(src, dst, cap, cls="", width=460):
    t, f = web(src, dst, width)
    if not t:
        return f"<div class='miss'>{cap}</div>"
    return (f"<figure class='{cls}'><img src='{t}' data-full='{f}' data-cap=\"{html.escape(cap)}\" "
            f"loading='lazy'><figcaption>{cap}</figcaption></figure>")


def main():
    if not os.path.isdir(os.path.join(RUN, "refs")):
        raise SystemExit(f"no run at {RUN}")
    os.makedirs(IMG, exist_ok=True)
    rows = {r["set_id"]: r for r in csv.DictReader(open(SET))}
    refs = os.listdir(os.path.join(RUN, "refs"))
    gen = os.listdir(os.path.join(RUN, "gen"))

    def load(name):
        p = os.path.join(RUN, "meta", name)
        return json.load(open(p)) if os.path.exists(p) else {}

    metrics = load("pose_metrics.json").get("pairs", {})
    runmeta = load("run_v37.json")
    prompts = runmeta.get("prompts", {})

    made = [s for s in rows if f"{s}__BCp_raw.jpg" in refs]
    # Call 1 ran on every pair - it is the cheap half and the half the question lives in.
    # The V2 crop that call 2 needs costs a minute of CPU per reference, so it was run on a
    # subset; those pairs sort first and the rest are marked, rather than quietly mixed in.
    full = {s for s in made if f"{s}__BCp__s{SEED}.jpg" in gen}
    made.sort(key=lambda s: (s not in full, s))
    arms = [a for a in ARMS if any(f.startswith(a[0]) for f in
                                   [x.split("__", 1)[1] for x in refs if "__" in x])
            or a[0] == "BC"]

    # ---- the headline, computed not asserted ----------------------------------
    band = []
    for a, lab, _, _ in ARMS[:2]:
        allb = [metrics[s][a] for s in made
                if metrics.get(s, {}).get(a) and metrics[s][a].get("base")]
        if not allb:
            continue
        n = len(allb)
        coll = [m for m in allb if m["base"] == "target"]
        src = [m for m in allb if m["base"] == "source"]
        # The pairs the pose detector could not read are their own bucket, not silently
        # added to "kept" by subtraction - that overstated the no-op count by two.
        nolm = [m for m in src if m.get("d_source") is None]
        kept = [m for m in src if m.get("d_source") is not None and m["d_source"] <= m["d_target"]]
        rep = [m for m in src if m.get("d_source") is not None and m["d_source"] > m["d_target"]]
        sep = [m for m in allb if m.get("separable") and m.get("shift") is not None]
        sh = sorted(m["shift"] for m in sep)
        px = sorted(m["px_changed"] for m in kept if m.get("px_changed") is not None)
        pxc = sorted(m["px_changed"] for m in coll if m.get("px_changed") is not None)
        band.append((lab, f"{len(kept)}/{n}", f"{len(coll)}/{n}", f"{len(rep)}/{n}",
                     f"{len(nolm)}", f"{sh[len(sh) // 2]:.2f}" if sh else "-", f"{len(sep)}/{n}",
                     f"{px[len(px) // 2]:.0%}" if px else "-",
                     f"{pxc[len(pxc) // 2]:.0%}" if pxc else "-"))

    cards = []
    for sid in made:
        r = rows[sid]
        m = metrics.get(sid, {})
        fram = m.get("framing", {})
        src_col = (fig(os.path.join(RUN, "inputs", f"{r['garment']}.jpg"),
                       f"{r['garment']}__g.jpg",
                       f"garment photo &middot; {fram.get('source') or '?'}", "src", 300)
                   + fig(os.path.join(RUN, "inputs", f"{r['person']}.jpg"),
                         f"{r['person']}__p.jpg",
                         f"target person &middot; {fram.get('target') or '?'}", "src", 300))

        arm_html = []
        for a, lab, note, has_raw in arms:
            mm = m.get(a) or {}
            shift, sep_ok, base = mm.get("shift"), mm.get("separable"), mm.get("base")
            badge = ""
            if shift is not None and a != "BC":
                if not sep_ok:
                    cls, tip = "sh-na", "poses too alike to judge"
                elif base == "target":
                    cls, tip = "sh-bad", "output collapsed onto image 2"
                elif shift > .5:
                    cls, tip = "sh-hi", "re-posed toward the target"
                elif shift > .25:
                    cls, tip = "sh-mid", "moved a little"
                else:
                    cls, tip = "sh-lo", "source pose returned"
                bcls = "sh-bad" if base == "target" else "sh-na"
                bname = base or "?"
                badge = (f"<span class='sh {cls}' title='{tip}'>shift {shift:.2f}</span>"
                         f"<span class='sh {bcls}'>base {bname}</span>")
            if a != "BC":
                ok = "ok" if mm.get("framing_reached") else "no"
                badge += (f"<span class='fr {ok}'>framing {fram.get(a) or '?'}</span>")
            cells = []
            if has_raw:
                cells.append(fig(os.path.join(RUN, "refs", f"{sid}__{a}_raw.jpg"),
                                 f"{sid}__{a}_raw.jpg", "call 1 &mdash; bald + re-pose"))
            else:
                cells.append("<div class='miss'>call 1 &mdash; bald only</div>")
            ref = (os.path.join(RUN, "refs", f"{sid}__{a}.jpg") if a != "BC"
                   else os.path.join(RUN, "refs", f"{r['garment']}__BC.jpg"))
            cells.append(fig(ref, f"{sid}__{a}_ref.jpg" if a != "BC" else f"{r['garment']}__BC.jpg",
                             "reference (V2 crop)", "ref"))
            cells.append(fig(os.path.join(RUN, "gen", f"{sid}__{a}__s{SEED}.jpg"),
                             f"{sid}__{a}__s{SEED}.jpg", f"call 2 &mdash; s{SEED}"))
            arm_html.append(
                f"<div class='arm' data-arm='{a}'>"
                f"<div class='ah'><b>{lab}</b><span>{note}</span>{badge}</div>"
                f"<div class='outs'>{''.join(cells)}</div>"
                f"<div class='vote' data-sid=\"{html.escape(sid)}\" data-arm='{a}'>"
                f"<i>pose</i>" + "".join(
                    f"<button data-k='pose' data-v='{v}'>{v}</button>"
                    for v in ("moved", "partial", "ignored"))
                + "<i>image 2 leaked</i>" + "".join(
                    f"<button data-k='leak' data-v='{v}'>{v}</button>"
                    for v in ("clothing", "face/body", "background", "no"))
                + "</div></div>")

        cards.append(
            f"<section class='card' data-sid=\"{html.escape(sid)}\" "
            f"data-full='{1 if sid in full else 0}'>"
            f"<div class='ch' data-full='{1 if sid in full else 0}'><b>{html.escape(sid)}</b>"
            f"<span class='t'>{html.escape(r.get('class') or r.get('source') or '')}</span>"
            + ("" if sid in full else "<span class='t partial'>call 1 only</span>") + "</div>"
            f"<div class='body'><div class='srcs'>{src_col}</div>"
            f"<div class='arms'>{''.join(arm_html)}</div></div></section>")

    o = [HEAD]
    o.append("<div class='wrap'><h1>v3.7 &mdash; handing klein the target photograph</h1>")
    o.append("<p class='failed'><b>FAILED &middot; concluded 2026-09-10, negative.</b> "
             "This arm is not shipping. klein does not re-pose a wearer from a reference "
             "photograph, and where it tries it returns the target's own photo re-dressed, "
             "which is worse than the incumbent it modifies. Record: "
             "<code>prd/v3/v3.7/EXPERIMENT.md</code>. The page is kept as the evidence.</p>")
    o.append(
        "<p class='lede'>One change to <b>BC</b>. Call 1 still balds the wearer of the garment; "
        "it is now also given the <b>target person's photograph as a second image</b> and asked to "
        "put the wearer into that person's pose. Call 2 is BC's, unchanged, at seed "
        f"{SEED}. Two wordings are run so a failure is the model's and not one sentence's: "
        "<b>BCp</b> asks for the pose third, after the bald instruction; <b>BCp2</b> declares "
        "image 2 a pose reference and asks for the pose first. <b>shift</b> is a landmark "
        "measurement, not a judgement &mdash; 0 means call 1 returned the source pose untouched, "
        "1 means it reached the target's.</p>"
        f"<p class='lede'>Call 1 ran on all <b>{len(made)}</b> pairs of the link&nbsp;C fold; the "
        f"V2 crop and call 2 that follow it ran on <b>{len(full)}</b> of them, because the crop "
        "costs about a minute of CPU per reference and the question is settled in call 1. "
        "Cards without an end-to-end cell are marked <code>call 1 only</code> and sort last.</p>"
        "<p class='lede verdict'><b>What it shows.</b> klein does not re-pose a wearer from a "
        "reference photograph. Of 51 pairs, <b>30 come back in the source pose</b> - balded and "
        "otherwise untouched - and <b>18 collapse onto image 2</b>, returning the target's own "
        "photograph with the garment swapped in and the head balded, which is not a re-pose but "
        "a try-on run backwards. <b>One</b> is a genuine transfer (<code>p028+g015</code>: the "
        "slip dress, arms raised overhead, in its own studio). Re-ordering the request and "
        "declaring image 2 a pose reference (<code>BCp2</code>) moves nothing: 29 / 19 / 1. "
        "Two pairs are in neither column: the pose detector reads nobody in their "
        "call-1 frame. The second image is read as a source of clothing and scene, not of "
        "pose.</p>"
        "<p class='lede'>The two halves of that split look nothing alike and it matters which "
        "one a card is showing. Where the source pose is kept, call 1 changes only the hair: the "
        "median such card differs from the garment photo in <b>8.9%</b> of its pixels, the "
        "quietest in <b>1.8%</b>. Where it collapses, the median differs in <b>90.5%</b>. "
        "So &ldquo;I can&rsquo;t "
        "see a difference&rdquo; is the correct reading of the first group and the wrong one for "
        "the second.</p>")
    if band:
        o.append("<div class='band'>" + "".join(
            f"<div class='stat'><b>{lab}</b>"
            f"<span>source pose kept <em>{kept}</em></span>"
            f"<span>collapsed onto image 2 <em>{coll}</em></span>"
            f"<span>re-posed toward the target <em>{rep}</em></span>"
            f"<span>no landmark read <em>{nolm}</em></span>"
            f"<span class='sub'>pixels changed: kept <em>{pxk}</em> &middot; "
            f"collapsed <em>{pxc}</em></span>"
            f"<span class='sub'>median shift <em>{med}</em> over the "
            f"<em>{sep}</em> pairs whose poses differ enough to judge</span></div>"
            for lab, kept, coll, rep, nolm, med, sep, pxk, pxc in band) + "</div>")
    if prompts:
        o.append("<details class='pr'><summary>the prompts, verbatim</summary>" + "".join(
            f"<p><b>{html.escape(k)}</b><br><code>{html.escape(v)}</code></p>"
            for k, v in prompts.items()) + "</details>")
    o.append("<div id='bar'><div class='grp'><span class='lbl'>arms</span>" + "".join(
        f"<label class='cb'><input type='checkbox' checked data-arm='{a}'>{lab}</label>"
        for a, lab, _, _ in arms) + "</div>"
        "<div class='grp'><span class='lbl'>show</span>"
        "<button id='fonly'>end-to-end pairs only</button></div>"
        "<button id='exp'>export votes CSV</button>"
        f"<span id='tally'>{len(made)} pairs &middot; {len(full)} run end to end</span></div>")
    o.append("<div class='grid'>" + "".join(cards) + "</div>")
    o.append("<footer>Model <code>" + html.escape(runmeta.get("model", "")) + "</code> &middot; "
             f"{runmeta.get('cost_usd', {}).get('this_run', '?')} USD of fal calls &middot; "
             "references cropped by the V2 cropper of record "
             "(<code>phase3_variants.masks(cranium=True)</code>) &middot; "
             "rebuild: <code>python3 v3/build/v37_page.py</code>.</footer></div>")
    o.append(LB + SCRIPT)
    open(OUTP, "w").write("\n".join(o))
    print(f"v3/report/v37.html  ({len(made)} pairs x {len(arms)} arms)")


HEAD = """<title>v3.7 - handing klein the target photograph</title>
<meta name='viewport' content='width=device-width,initial-scale=1'>
<style>
:root{--bg:#0d0d10;--fg:#e8e8ea;--dim:#8a8a94;--line:#26262c;--acc:#7c5cff;--mid:#d29922}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
 font:15px/1.6 ui-sans-serif,-apple-system,"Segoe UI",Roboto,sans-serif}
.wrap{max-width:1750px;margin:0 auto;padding:26px 22px 0}
h1{margin:0 0 6px;font-size:25px}
.lede{color:var(--dim);max-width:100ch;font-size:14px;margin:0 0 14px}
.lede b{color:var(--fg)}
.verdict{border-left:2px solid var(--acc);padding:2px 0 2px 12px}
.failed{border:1px solid #8a2b34;background:#2d1418;color:#ff9aa2;border-radius:9px;
 padding:10px 14px;margin:0 0 14px;font-size:13.5px;max-width:100ch}
.failed b{color:#ffd7db;letter-spacing:.02em}
.band{display:flex;gap:10px;flex-wrap:wrap;margin:0 0 12px}
.stat{border:1px solid var(--line);border-radius:9px;background:#101014;padding:9px 14px;
 display:flex;gap:14px;align-items:baseline;flex-wrap:wrap;font-size:12px;color:var(--dim)}
.stat b{color:var(--fg);font:13px ui-monospace,monospace}
.stat em{font-style:normal;color:var(--fg);font-family:ui-monospace,monospace}
.stat .sub{opacity:.72;border-left:1px solid var(--line);padding-left:14px}
.pr{border:1px solid var(--line);border-radius:9px;background:#101014;padding:8px 14px;
 margin:0 0 12px;font-size:12.5px;color:var(--dim)}
.pr summary{cursor:pointer;color:var(--fg)}
.pr code{display:inline-block;margin-top:3px;line-height:1.7}
#bar{position:sticky;top:0;z-index:40;display:flex;gap:14px;align-items:center;flex-wrap:wrap;
 padding:9px 12px;margin:12px 0 0;background:#141419;border:1px solid var(--line);
 border-radius:9px;font-size:12.5px}
#bar .grp{display:flex;gap:6px;align-items:center;flex-wrap:wrap}
#bar .lbl{color:var(--dim);font-size:11.5px;text-transform:uppercase;letter-spacing:.05em}
.cb{display:inline-flex;gap:4px;align-items:center;padding:2px 8px;border:1px solid var(--line);
 border-radius:20px;background:#101014;cursor:pointer;font:12px ui-monospace,monospace}
#bar button{background:#101014;color:var(--fg);border:1px solid var(--line);border-radius:20px;
 padding:3px 11px;cursor:pointer;font:12px ui-sans-serif,sans-serif}
#tally{margin-left:auto;color:var(--dim);font-size:12px}
.grid{display:grid;gap:14px;margin-top:14px}
.card{border:1px solid var(--line);border-radius:9px;background:#101014;overflow:hidden}
.ch{display:flex;gap:8px;align-items:center;padding:7px 12px;background:#141419;
 border-bottom:1px solid var(--line);font-size:12px;flex-wrap:wrap}
.ch b{font-size:12.5px;word-break:break-all}
.t{font-size:9.5px;padding:1px 7px;border-radius:20px;background:#2a1a12;
 border:1px solid #6b4423;color:var(--mid)}
.t.partial{background:#17171d;border-color:var(--line);color:var(--dim)}
#bar button.on{background:var(--acc);border-color:var(--acc);color:#fff}
.body{display:grid;grid-template-columns:250px 1fr;gap:10px;padding:8px}
@media(max-width:1000px){.body{grid-template-columns:1fr}}
.srcs{display:flex;flex-direction:column;gap:6px}
.arms{display:flex;flex-direction:column;gap:6px}
.arm{border:1px solid var(--line);border-radius:8px;background:#0b0b0e;padding:6px}
.ah{display:flex;gap:9px;align-items:baseline;padding:1px 3px 5px;font-size:12.5px;flex-wrap:wrap}
.ah b{font-family:ui-monospace,monospace}
.ah span{color:var(--dim);font-size:11px}
.sh{font:10px ui-monospace,monospace;padding:1px 7px;border-radius:20px;margin-left:auto;
 border:1px solid var(--line)}
.sh-lo{background:#2d1418;border-color:#8a2b34;color:#ff9aa2}
.sh-bad{background:#2d1030;border-color:#7a3a8a;color:#e0a9ff}
.sh-na{background:#17171d;color:var(--dim)}
.ah .sh:first-of-type{margin-left:auto}
.ah .sh~.sh{margin-left:0}
.sh-mid{background:#2a2110;border-color:#6b4423;color:var(--mid)}
.sh-hi{background:#12240f;border-color:#2c5c33;color:#7ee787}
.fr{font:10px ui-monospace,monospace;padding:1px 7px;border-radius:20px;border:1px solid var(--line)}
.fr.ok{background:#12240f;border-color:#2c5c33;color:#7ee787}
.fr.no{background:#17171d;color:var(--dim)}
.outs{display:grid;grid-template-columns:repeat(3,1fr);gap:5px}
@media(max-width:700px){.outs{grid-template-columns:1fr}}
figure{margin:0}
figure img{width:100%;display:block;background:#fff;border-radius:5px;cursor:zoom-in;
 aspect-ratio:3/4;object-fit:contain}
figure.src img,figure.ref img{aspect-ratio:2/3;outline:1px solid var(--line);outline-offset:-1px}
figcaption{font-size:10px;color:var(--dim);text-align:center;padding:3px 2px}
.miss{background:#17171d;border:1px dashed var(--line);border-radius:5px;aspect-ratio:3/4;
 display:flex;align-items:center;justify-content:center;color:var(--dim);font-size:11px;
 text-align:center;padding:6px}
.vote{display:flex;gap:4px;align-items:center;flex-wrap:wrap;color:var(--dim);
 font-size:10.5px;padding-top:5px}
.vote i{font-style:normal;opacity:.7;margin:0 2px 0 6px}
.vote button{background:#101014;color:var(--dim);border:1px solid var(--line);border-radius:20px;
 padding:0 7px;cursor:pointer;font:10px ui-monospace,monospace}
.vote button.on{background:#2c5c33;border-color:#3fb950;color:#e8e8ea}
#lb{display:none;position:fixed;inset:0;background:rgba(0,0,0,.95);z-index:99;
 align-items:center;justify-content:center;flex-direction:column;gap:10px;padding:20px}
#lb.on{display:flex}#lb img{max-width:95vw;max-height:90vh;object-fit:contain;background:#fff}
#lbc{color:var(--dim);font-size:13px}
footer{border-top:1px solid var(--line);margin-top:36px;padding:20px 0 30px;color:var(--dim);font-size:12.5px}
code{background:#1b1b22;padding:1px 5px;border-radius:4px;font-size:12px}
</style>"""

LB = "<div id='lb'><img><div id='lbc'></div></div>"

SCRIPT = """<script>
const lb=document.getElementById('lb'),lbi=lb.querySelector('img'),lbc=document.getElementById('lbc');
document.addEventListener('click',e=>{
  const img=e.target.closest('figure img');
  if(img){lbi.src=img.dataset.full||img.src;lbc.textContent=(img.dataset.cap||'').replace(/&\\w+;/g,' ');lb.classList.add('on');return;}
  if(e.target.closest('#lb')){lb.classList.remove('on');}
});
addEventListener('keydown',e=>{if(e.key==='Escape')lb.classList.remove('on')});

const KEY='v37votes';
const votes=JSON.parse(localStorage.getItem(KEY)||'{}');
function paint(){
  document.querySelectorAll('.vote').forEach(v=>{
    const k=v.dataset.sid+'|'+v.dataset.arm, rec=votes[k]||{};
    v.querySelectorAll('button').forEach(b=>b.classList.toggle('on',rec[b.dataset.k]===b.dataset.v));
  });
}
document.addEventListener('click',e=>{
  const b=e.target.closest('.vote button'); if(!b)return;
  const v=b.closest('.vote'), k=v.dataset.sid+'|'+v.dataset.arm;
  const rec=votes[k]||(votes[k]={});
  rec[b.dataset.k]=rec[b.dataset.k]===b.dataset.v?null:b.dataset.v;
  localStorage.setItem(KEY,JSON.stringify(votes)); paint();
});
paint();

document.querySelectorAll('#bar input[data-arm]').forEach(cb=>cb.onchange=()=>{
  document.querySelectorAll(`.arm[data-arm="${cb.dataset.arm}"]`)
    .forEach(a=>a.hidden=!cb.checked);
});

const fo=document.getElementById('fonly');
fo.onclick=()=>{
  fo.classList.toggle('on');
  const on=fo.classList.contains('on');
  document.querySelectorAll('.card').forEach(c=>{
    c.hidden = on && c.dataset.full!=='1';
  });
};

document.getElementById('exp').onclick=()=>{
  const rows=[['set_id','arm','pose','leak']];
  for(const k in votes){const [sid,arm]=k.split('|');
    rows.push([sid,arm,votes[k].pose||'',votes[k].leak||'']);}
  const csv=rows.map(r=>r.map(x=>`"${String(x).replace(/"/g,'""')}"`).join(',')).join('\\n');
  const a=document.createElement('a');
  a.href=URL.createObjectURL(new Blob([csv],{type:'text/csv'}));
  a.download='v37_votes.csv'; a.click();
};
</script>"""


if __name__ == "__main__":
    main()
