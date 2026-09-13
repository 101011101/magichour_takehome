"""v3.15 - one row per case: what went in, the reference, the output, and PASS or FAIL.

Reads the run the smoke notebook zipped - records.json, meta.json, inputs/, refs/, gen/ -
and writes a page with failures first. Every row carries expected against actual for the
fields the test judges: the gate's verdict and head pixels, the route, whether the bald pass
ran, the requested and applied region, the fallback reason, and which call-2 sentence went.

  python3 v3/build/v315_page.py [RUN_DIR] [OUT_HTML]
      RUN_DIR   default v3/runs/v315/a100
      OUT_HTML  default v3/report/v315.html
"""
import html
import json
import os
import sys

from PIL import Image

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RUN = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.join(REPO, "v3", "runs", "v315", "a100")
OUT = os.path.abspath(sys.argv[2]) if len(sys.argv) > 2 else os.path.join(REPO, "v3", "report", "v315.html")
IMG = os.path.join(os.path.dirname(OUT), "img_v315")
THUMB = 220


def thumb(src, name):
    if not os.path.exists(src):
        return '<div class=miss>none</div>'
    dst = os.path.join(IMG, name)
    if not os.path.exists(dst):
        im = Image.open(src).convert("RGB")
        im.thumbnail((THUMB, THUMB * 2))
        im.save(dst, quality=85)
    w, h = Image.open(src).size
    rel = os.path.relpath(dst, os.path.dirname(OUT))
    return f'<figure><img src="{html.escape(rel)}" loading=lazy><figcaption>{w}x{h}</figcaption></figure>'


def field(label, expected, actual):
    ok = expected is None or str(actual).startswith(str(expected).split(" (")[0])
    return (f'<tr class="{"" if ok else "bad"}"><td>{label}</td><td>{html.escape(str(expected))}</td>'
            f'<td>{html.escape(str(actual))}</td></tr>')


def row(rec):
    c, a, e = rec["case"], rec.get("actual", {}), rec.get("expected", {})
    badge = '<span class="badge pass">PASS</span>' if rec["pass"] else '<span class="badge fail">FAIL</span>'
    table = "".join([
        field("gate says person", e.get("gate"), a.get("gate")),
        field("head pixels", None, a.get("head_px")),
        field("route", e.get("route"), a.get("route")),
        field("bald pass ran", e.get("bald_pass"), a.get("bald_pass")),
        field("requested region", None, c["region"]),
        field("applied region", e.get("applied"), a.get("applied")),
        field("fallback", None, a.get("fallback") or "-"),
        field("call 2 sentence", e.get("call2"), a.get("call2")),
        field("reference / output", None, f"{a.get('reference')} / {a.get('output')}"),
    ])
    times = " · ".join(f"{k} {v:.2f}s" for k, v in rec.get("times", {}).items())
    fails = "".join(f"<li>{html.escape(f)}</li>" for f in rec["fails"])
    notes = "".join(f"<li>{html.escape(n)}</li>" for n in rec.get("notes", []))
    tb = f'<pre>{html.escape(rec["traceback"])}</pre>' if rec.get("traceback") else ""
    return f"""<section class="{'ok' if rec['pass'] else 'ko'}">
  <h2>{badge} {html.escape(c['id'])} <span class=sub>{c['kind']} · {html.escape(c['why'])}</span></h2>
  <div class=imgs>
    <div><b>garment</b>{thumb(os.path.join(RUN, 'inputs', os.path.basename(c['garment_path'])), 'in_' + os.path.basename(c['garment_path']))}</div>
    <div><b>person</b>{thumb(os.path.join(RUN, 'inputs', os.path.basename(c['person_path'])), 'in_' + os.path.basename(c['person_path']))}</div>
    <div><b>reference</b>{thumb(os.path.join(RUN, 'refs', c['id'] + '.jpg'), 'ref_' + c['id'] + '.jpg')}</div>
    <div><b>output</b>{thumb(os.path.join(RUN, 'gen', c['id'] + '.jpg'), 'out_' + c['id'] + '.jpg')}</div>
    <table><tr><th></th><th>expected</th><th>actual</th></tr>{table}</table>
  </div>
  {f'<ul class=fails>{fails}</ul>' if fails else ''}{f'<ul class=notes>{notes}</ul>' if notes else ''}
  <div class=times>{html.escape(times)} · wall {rec.get('wall_seconds', 0):.2f}s</div>{tb}
</section>"""


def main():
    path = os.path.join(RUN, "records.json")
    if not os.path.exists(path):
        raise SystemExit(f"no run at {RUN} - unpack the notebook's zip there first")
    records = json.load(open(path))
    meta = json.load(open(os.path.join(RUN, "meta.json"))) if os.path.exists(os.path.join(RUN, "meta.json")) else {}
    os.makedirs(IMG, exist_ok=True)
    records.sort(key=lambda r: (r["pass"], r["case"]["kind"], r["case"]["id"]))
    groups = {k: [r for r in records if r["case"]["kind"] == k] for k in ("product", "worn")}
    summary = " · ".join(f"{k}: {sum(r['pass'] for r in v)}/{len(v)} pass" for k, v in groups.items())
    passed = sum(r["pass"] for r in records)
    doc = f"""<!doctype html><meta charset=utf-8><title>v3.15 — production smoke test</title>
<style>
body{{background:#0f1114;color:#e8eaed;font:14px/1.5 system-ui,sans-serif;margin:0;padding:0 18px 60px}}
h1{{font-size:20px;margin:20px 0 4px}} .lede{{color:#9aa4b2;max-width:70em}}
.total{{font-size:17px;font-weight:700;margin:10px 0 16px}}
section{{border-top:1px solid #262a30;padding:14px 0}} section.ko{{background:#1c1214}}
h2{{font-size:15px;margin:0 0 8px}} .sub{{color:#8a93a0;font-weight:400;font-size:12px}}
.badge{{font-size:12px;font-weight:800;padding:2px 8px;border-radius:4px;margin-right:6px}}
.badge.pass{{background:#2f9e5b;color:#fff}} .badge.fail{{background:#e5484d;color:#fff}}
.imgs{{display:flex;gap:12px;flex-wrap:wrap;align-items:flex-start}} .imgs b{{display:block;font-size:11px;color:#9aa4b2}}
figure{{margin:0}} img{{display:block;border-radius:3px;max-width:{THUMB}px}} figcaption{{font-size:11px;color:#6b7280}}
table{{border-collapse:collapse;font-size:12px}} td,th{{border:1px solid #2a2e35;padding:2px 8px;text-align:left}}
tr.bad td{{background:#4a1d20}} .fails{{color:#ff8a8f}} .notes{{color:#c9b36b}} .times{{color:#6b7280;font-size:11px}}
pre{{white-space:pre-wrap;font-size:11px;color:#ff8a8f}} .miss{{color:#6b7280;padding:30px 10px}}
</style>
<h1>v3.15 — the production notebook, run end to end with regions set</h1>
<p class=lede>Every case ran through <code>vp/tryon_er.ipynb</code>'s own cells at
{html.escape(str(meta.get('commit') or meta.get('branch', '?')))} (sha256 {html.escape(str(meta.get('shipped_sha256', '?'))[:16])})
on {html.escape(str(meta.get('gpu', '?')))}. Product shots must skip the bald pass and be forced to full; worn garments
must be cut at the hip or record why not, and call 2 must be sent the sentence for the region actually applied.
Failures first.</p>
<div class=total>{passed}/{len(records)} pass — {summary} · {meta.get('klein_calls', '?')} klein calls</div>
{''.join(row(r) for r in records)}
"""
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, "w").write(doc)
    print(f"{os.path.relpath(OUT, REPO)}  ({passed}/{len(records)} pass)")


if __name__ == "__main__":
    main()
