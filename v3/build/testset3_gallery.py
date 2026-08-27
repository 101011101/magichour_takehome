"""Build the test_set3 gallery page.

One pool. Every image is an on-model photograph, so every image can take either side
of a pairing. Metadata carried over from test-set-1's manifest is shown where it
exists and marked absent where it does not.
"""
import csv
import html
import os
from collections import Counter

from PIL import Image

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SET = os.path.join(REPO, "test_set3")
REPORT = os.path.join(REPO, "v3", "report")
IMG = os.path.join(REPORT, "img_ts3")
THUMB, FULL = 340, 900


def web(src, stem, width, suffix=""):
    dst = os.path.join(IMG, f"{stem}{suffix}.jpg")
    if not os.path.exists(dst):
        im = Image.open(src).convert("RGB")
        if im.width > width:
            im = im.resize((width, int(im.height * width / im.width)), Image.LANCZOS)
        im.save(dst, quality=84, optimize=True)
    return f"img_ts3/{stem}{suffix}.jpg"


def card(r):
    src = os.path.join(REPO, r["path"])
    im = Image.open(src)
    t = web(src, r["id"], THUMB)
    f = web(src, r["id"], FULL, "@f")
    tags = [v for k, v in (("pose", r["pose"]), ("body_size", r["body_size"]),
                           ("skin_tone", r["skin_tone"]), ("gender", r["gender"]),
                           ("framing", r["framing"]), ("category", r["category"]),
                           ("photo_style", r["photo_style"])) if v]
    hard = f"<span class='hard'>{html.escape(r['hard_case'])}</span>" if r["hard_case"] else ""
    hf = float(r["hair_frac"]) if r.get("hair_frac") else None
    nohair = "<span class='nh'>no hair in frame</span>" if hf is not None and hf < 0.0005 else ""
    return (f"<figure class='c' data-src='{r['source_set']}' data-hard='{r['hard_case']}' "
            f"data-nohair='{1 if (hf is not None and hf < 0.0005) else 0}'>"
            f"<img src='{t}' data-full='{f}' alt='{html.escape(r['id'])}' loading='lazy'>"
            f"<figcaption><b>{html.escape(r['id'])}</b>"
            f"<span class='dim'>{im.width}&times;{im.height} · {r['source_set']}</span>"
            f"{hard}{nohair}"
            + ("".join(f"<span class='t'>{html.escape(x)}</span>" for x in tags)
               or "<span class='t none'>no metadata</span>")
            + "</figcaption></figure>")


def main():
    os.makedirs(IMG, exist_ok=True)
    rows = list(csv.DictReader(open(os.path.join(SET, "manifest.csv"))))
    srcs = Counter(r["source_set"] for r in rows)
    hard = Counter(r["hard_case"] for r in rows if r["hard_case"])
    nometa = [r for r in rows if not r["pose"] and not r["category"]]
    nohair = [r for r in rows if r.get("hair_frac") and float(r["hair_frac"]) < 0.0005]

    o = [HEAD]
    o.append("<div class='wrap'>")
    o.append("<div class='q'><b>One pool: every image contains a person wearing an "
             "outfit, so every image can take either side of a pairing.</b> "
             "Product-only shots &mdash; flat-lay and ghost mannequin &mdash; are "
             "excluded, because they can only ever be the garment, which makes the pool "
             "asymmetric and a fold impossible to state cleanly. The 13 test-set-1 "
             "garments tagged <code>on_model</code> are in; the 17 tagged "
             "<code>flat_lay</code> or <code>ghost_mannequin</code> are out. Both tags "
             "were checked against the images before being trusted.</div>")
    o.append("<div class='meta'>Provenance: "
             + " &middot; ".join(f"<b>{v}</b> from <code>{html.escape(k)}</code>"
                                 for k, v in srcs.most_common())
             + f". <b>{len(rows)}</b> images total.</div>")
    if hard:
        o.append("<div class='meta'>Hard cases tagged in test-set-1: "
                 + " &middot; ".join(f"<b>{v}</b> {html.escape(k)}"
                                      for k, v in hard.most_common())
                 + f". <b>{len(nometa)}</b> images carry no metadata at all &mdash; "
                 "test_set2 was never tagged.</div>")
    o.append(f"<div class='meta'><b>{len(nohair)}</b> images show no hair in frame "
             "(cropped at the neck, or a covered head). Recorded because it is the "
             "variable that decides whether BC_klein's bald pass has anything to do: "
             "a reference with no hair cannot have hair removed from it. The number "
             "behind it is a coarse 256&times;256 area fraction &mdash; it ranks "
             "references, it does not classify them.</div>")
    o.append(FILTERS)
    o.append("<div class='grid'>" + "".join(card(r) for r in rows) + "</div>")
    o.append("<footer>Of record: <code>test_set3/manifest.csv</code>, built by "
             "<code>v3/build/make_testset3.py</code> from <code>test_set1/</code> and "
             "<code>test_set2/</code>. Copies, not moves &mdash; the earlier sets are "
             "still cited by runs already on disk.</footer></div>")
    o.append(LB + SCRIPT)
    open(os.path.join(REPORT, "testset3.html"), "w").write("\n".join(o))
    print(f"v3/report/testset3.html  ({len(rows)} on-model images, "
          f"{len(nohair)} with no hair in frame)")


HEAD = """<title>test_set3</title>
<meta name='viewport' content='width=device-width,initial-scale=1'>
<style>
:root{--bg:#0d0d10;--fg:#e8e8ea;--dim:#8a8a94;--line:#26262c;--acc:#7c5cff;
 --good:#3fb950;--bad:#f85149;--mid:#d29922}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
 font:15px/1.6 ui-sans-serif,-apple-system,"Segoe UI",Roboto,sans-serif}
.wrap{max-width:1400px;margin:0 auto;padding:30px 26px 0}
h1{margin:0 0 6px;font-size:25px}
h2{font-size:19px;margin:40px 0 12px;padding-top:14px;border-top:1px solid var(--line)}
h2 .sub{font-size:13px;color:var(--dim);font-weight:400}
.lede{color:var(--dim);max-width:84ch;font-size:14px;margin:0 0 18px}
table{border-collapse:collapse;font-size:13px;margin:14px 0}
th,td{padding:5px 14px;border-bottom:1px solid #1d1d23;text-align:right}
th:first-child,td:first-child{text-align:left}
th{color:var(--dim);font-weight:600}
td.y{color:var(--good)}td.n{color:var(--bad)}
.q{border-left:3px solid var(--acc);padding:2px 0 2px 14px;margin:16px 0;max-width:86ch;
 font-size:14px;color:#c8c8d0}
.q b{color:var(--fg)}
.meta{font-size:12.5px;color:var(--dim);margin:8px 0;max-width:100ch}
.meta b{color:var(--fg)}
#f{display:flex;gap:7px;flex-wrap:wrap;margin:18px 0 4px;align-items:center}
#f button{font:inherit;font-size:12px;padding:4px 11px;border-radius:20px;cursor:pointer;
 background:#16161c;color:var(--dim);border:1px solid var(--line)}
#f button.on{background:var(--acc);border-color:var(--acc);color:#fff}
#f span{font-size:11.5px;color:var(--dim);margin-right:4px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(178px,1fr));gap:10px}
figure.c{margin:0;background:#101014;border:1px solid var(--line);border-radius:8px;
 overflow:hidden;display:flex;flex-direction:column}
figure.c.hide{display:none}
figure.c img{width:100%;aspect-ratio:3/4;object-fit:cover;object-position:top center;
 display:block;background:#fff;cursor:zoom-in}
figcaption{padding:7px 8px 9px;display:flex;flex-wrap:wrap;gap:3px;align-items:center}
figcaption b{font-size:11.5px;width:100%;word-break:break-all;line-height:1.3}
.dim{font-size:10px;color:var(--dim);width:100%;margin-bottom:2px}
.t{font-size:9.5px;padding:1px 6px;border-radius:20px;border:1px solid var(--line);
 color:var(--dim)}
.t.none{border-style:dashed}
.nh{font-size:9.5px;padding:1px 6px;border-radius:20px;background:#1a1226;
 border:1px solid #4b3a78;color:#b9a7ec}
.hard{font-size:9.5px;padding:1px 6px;border-radius:20px;background:#2a1a12;
 border:1px solid #6b4423;color:var(--mid)}
#lb{display:none;position:fixed;inset:0;background:rgba(0,0,0,.95);z-index:99;
 align-items:center;justify-content:center;flex-direction:column;gap:10px;padding:20px}
#lb.on{display:flex}#lb img{max-width:95vw;max-height:88vh;object-fit:contain;background:#fff}
#lbc{color:var(--dim);font-size:13px}
footer{border-top:1px solid var(--line);margin-top:44px;padding:22px 0 30px;
 color:var(--dim);font-size:12.5px}
code{background:#1b1b22;padding:1px 5px;border-radius:4px;font-size:12px}
</style>
<div class='wrap'><h1>test_set3</h1>
<p class='lede'>Every image in the set. One pool of on-model photographs, any of which
can be the person input or the garment source. Assembled from <code>test_set1/</code>
and <code>test_set2/</code>; click any image for full size.</p></div>
"""

FILTERS = """<div id='f'><span>source</span>
<button class='on' data-k='src' data-v=''>all</button>
<button data-k='src' data-v='test_set1'>test_set1</button>
<button data-k='src' data-v='test_set2/people'>test_set2 people</button>
<button data-k='src' data-v='test_set2/clothes (on-model)'>test_set2 on-model</button>
<button data-k='src' data-v='test_set1/garments (on-model)'>test_set1 on-model garments</button>
<span style='margin-left:14px'>filter</span>
<button data-k='hard' data-v='__any'>hard case</button>
<button data-k='nohair' data-v='1'>no hair in frame</button></div>"""

LB = "<div id='lb'><img id='lbi' alt=''><div id='lbc'></div></div>"

SCRIPT = """<script>
let F={src:'',hard:'',nohair:''};
function apply(){
  document.querySelectorAll('figure.c').forEach(c=>{
    let ok=true;
    if(F.src && c.dataset.src!==F.src) ok=false;
    if(F.hard==='__any' && !c.dataset.hard) ok=false;
    if(F.nohair==='1' && c.dataset.nohair!=='1') ok=false;
    c.classList.toggle('hide',!ok);
  });
}
document.getElementById('f').addEventListener('click',e=>{
  const b=e.target.closest('button'); if(!b) return;
  const k=b.dataset.k, v=b.dataset.v;
  F[k] = (F[k]===v) ? '' : v;
  document.querySelectorAll(`#f button[data-k="${k}"]`).forEach(x=>
    x.classList.toggle('on',x.dataset.v===F[k]));
  if(k==='src' && !F.src) document.querySelector('#f button[data-v=""]').classList.add('on');
  apply();
});
document.addEventListener('click',e=>{
  const im=e.target.closest('figure.c img'); if(!im) return;
  document.getElementById('lbi').src=im.dataset.full;
  document.getElementById('lbc').textContent=im.getAttribute('alt');
  document.getElementById('lb').classList.add('on');
});
document.getElementById('lb').addEventListener('click',()=>
  document.getElementById('lb').classList.remove('on'));
document.addEventListener('keydown',e=>{if(e.key==='Escape')
  document.getElementById('lb').classList.remove('on')});
</script>"""

if __name__ == "__main__":
    main()
