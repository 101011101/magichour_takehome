"""Every cell the blind sweep says `ER` breaks and `BC` does not.

The other direction is on `v36_report.html`; this page exists so the regressions can be
looked at as a set rather than sampled. Derived from the join of the two blind counts, so
the page cannot show a cell whose verdict does not say what the page says it does.

  python3 v3/build/v36_regressions_page.py    ->  v3/report/v36_regressions.html
"""
import csv
import os
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import v36_report as R                # noqa: E402  the strip builder and the page styles

REPORT = os.path.join(REPO, "v3", "report")


def main():
    os.makedirs(R.IMG, exist_ok=True)
    er = {(r["set_id"], r["seed"]): r["bc_failed"] == "fail"
          for r in csv.DictReader(open(R.ERCOUNT))}
    bc = {(r["set_id"], r["seed"]): r["bc_failed"] == "fail"
          for r in csv.DictReader(open(R.COUNT))}
    worse = sorted(c for c in er if er[c] and not bc.get(c))
    other = sorted(c for c in er if bc.get(c) and not er[c])

    strips = "".join(R.cell(sid, sd) for sid, sd in worse)
    page = f"""{R.HEAD.replace('TITLE', 'Every cell ER breaks')}
<div class='wrap'>
<p class='lede'>The {len(worse)} cells the blind sweep marks clean under <code>BC</code> and
failed under <code>ER</code> &mdash; against {len(other)} the other way.
<a href='v36_report.html'>&larr; the result</a></p>
{strips}
<footer>From the join of <code>v3/testsets/bc_count.csv</code> and
<code>er_count.csv</code> &middot; rebuild:
<code>python3 v3/build/v36_regressions_page.py</code></footer>
</div>{R.LB}{R.SCRIPT}"""
    open(os.path.join(REPORT, "v36_regressions.html"), "w").write(page)
    print(f"v3/report/v36_regressions.html  ({len(worse)} cells)")
    for c in worse:
        print("  ", c[0], "s" + c[1])


if __name__ == "__main__":
    main()
