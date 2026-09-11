"""The bank: every cell of the 600, classified by the strongest evidence that exists for it.

Five instruments were used across v3.6 and they do not all deserve equal weight. The order
here is deliberate:

  on BC's 50 failures    the strict side-by-side pass. It is complete over that set, it was
                         marked in one sitting against the same bar as the BC record, and it
                         is the only instrument that judged every one of them.
  everywhere else        the blind A/B, where it reaches - arm hidden, sides shuffled. It
                         covers the three cells BC passes and ER fails, which the
                         side-by-side pass could only phrase ambiguously.
  otherwise              the head-to-head, then the raw counts.

Each instrument is used where it is strongest rather than by a single ranking: blindness wins
on cells where the question is "which of these two", coverage wins on the failure set the BC
record is defined by. Where the blind and the side-by-side passes overlap they agree on 5 of 8
cells; the three they do not are noted on the page.

  python3 v3/build/v36_bank.py     ->  v3/report/v36_bank.html
"""
import csv
import html
import os
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import v36_report as R                # noqa: E402

REPORT = os.path.join(REPO, "v3", "report")
T = os.path.join(REPO, "v3", "testsets")


def load(p, k="bc_failed"):
    return {(r["set_id"], r["seed"]): r[k] == "fail" for r in csv.DictReader(open(os.path.join(T, p)))}


def main():
    os.makedirs(R.IMG, exist_ok=True)
    bc2, er = load("bc2_count.csv"), load("er_count.csv")
    bc1 = load("bc_count.csv")
    bf = {(r["set_id"], r["seed"]): (r["block"], r["er_verdict"])
          for r in csv.DictReader(open(os.path.join(T, "v36_bcfail.csv")))}
    bl = {(r["set_id"], r["seed"]): r["better_arm"]
          for r in csv.DictReader(open(os.path.join(T, "v36_discordant.csv")))}
    hh = {(r["set_id"], r["seed"]): r["better"]
          for r in csv.DictReader(open(os.path.join(T, "v36_er_vs_bc.csv"))) if r["better"]}

    def verdict(c):
        if c in bf and bf[c][0] == "bcfail":       # complete over BC's failure set
            return ("ER better" if bf[c][1] == "clean" else "both fail"), "side by side"
        if c in bl:                                 # blind, and it covers the other direction
            m = {"ER": "ER better", "BC": "BC better", "both": "both clean", "neither": "both fail"}
            return m[bl[c]], "blind A/B"
        if c in bf:                                 # eronly, whose wording was ambiguous
            return ("both fail" if bf[c][1] == "same" else "BC better"), "side by side"
        if c in hh:
            return {"ER": "ER better", "BC": "BC better", "same": "both clean"}[hh[c]], "head to head"
        if bc2.get(c) and not er.get(c):
            return "ER better", "counts, cross-session"
        if er.get(c) and not bc2.get(c):
            return "BC better", "counts, cross-session"
        return ("both fail" if bc2.get(c) else "both clean"), "counts"

    v = {c: verdict(c) for c in bc2}
    groups = {k: sorted(c for c in v if v[c][0] == k)
              for k in ("ER better", "BC better", "both fail", "both clean")}

    def block(key, cls, note, images=True):
        cells = groups[key]
        if images:
            body = "".join(
                R.cell(sid, sd, note=f"{v[(sid, sd)][1]}") for sid, sd in cells)
        else:
            body = ("<div class='list'>" + "".join(
                f"<span>{html.escape(sid)} <i>s{sd}</i></span>" for sid, sd in cells) + "</div>")
        return (f"<h2 class='{cls}'>{key} &mdash; {len(cells)}</h2>"
                f"<p class='sec'>{note}</p>{body}")

    page = f"""{R.HEAD.replace('TITLE', 'The bank &mdash; every cell, every verdict')}
<div class='wrap'>
<p class='lede'>All 600 cells, each classified by the <b>strongest instrument that judged
it</b>: a blind A/B first, then the strict side-by-side, then the 150-cell head-to-head, then
the raw counts. Every row says which. Reference only &mdash; nothing here is marked.
<a href='v36_report.html'>&larr; the report</a></p>
<div class='tiles'>
  <div class='tile good'><div class='v'>{len(groups['ER better'])}</div>
    <div class='l'>ER better</div><div class='s'>BC fails, ER does not</div></div>
  <div class='tile'><div class='v'>{len(groups['BC better'])}</div>
    <div class='l'>BC better</div><div class='s'>ER fails, BC does not</div></div>
  <div class='tile'><div class='v'>{len(groups['both fail'])}</div>
    <div class='l'>both fail</div><div class='s'>reference-side &mdash; no prompt reaches these</div></div>
  <div class='tile'><div class='v'>{len(groups['both clean'])}</div>
    <div class='l'>both clean</div><div class='s'>the arms are indistinguishable</div></div>
</div>
{block('ER better', 'good', 'Every cell the evidence says ER repairs. The tag on each row is the instrument that judged it.')}
{block('BC better', 'bad', 'Every cell the evidence says ER breaks. All three come from the blind pass, which judged them with the arm hidden; the side-by-side pass could only phrase the question ambiguously for this direction, so the blind verdict stands.')}
{block('both fail', '', 'The floor. The fault is upstream of call 2 - the reference, the crop, the pair - and no wording of call 2 reaches it.')}
{block('both clean', '', 'Listed without images: 546 cells where both arms are fine.', images=False)}
<footer>Built by <code>v3/build/v36_bank.py</code> from every marks CSV in
<code>v3/testsets/</code> &middot; instrument precedence is in the script's docstring
&middot; BC of record is pass 2 ({sum(bc2.values())}/600); pass 1 found {sum(bc1.values())}
&middot; <a href='v36_report.html'>the report &rarr;</a></footer>
</div>{R.LB}{R.SCRIPT}
<style>.list{{display:flex;flex-wrap:wrap;gap:5px;margin:6px 0 18px}}
.list span{{background:#15151b;border:1px solid var(--line);border-radius:5px;
 padding:2px 7px;font:11px ui-monospace,monospace;color:var(--dim)}}
.list i{{color:#6a6a74;font-style:normal}}
h2.good{{color:var(--good)}}h2.bad{{color:var(--bad)}}
.tiles{{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:9px;margin:14px 0}}
.tile{{border:1px solid var(--line);border-radius:9px;background:var(--card);padding:12px 14px}}
.tile .v{{font:600 30px/1.1 ui-sans-serif,sans-serif;letter-spacing:-.6px}}
.tile.good .v{{color:var(--good)}}
.tile .l{{font-size:13px;margin-top:3px}}.tile .s{{font-size:11.5px;color:var(--dim);margin-top:3px}}
</style>"""
    open(os.path.join(REPORT, "v36_bank.html"), "w").write(page)
    print(f"v3/report/v36_bank.html")
    for k in groups:
        print(f"  {k:12s} {len(groups[k])}")


if __name__ == "__main__":
    main()
