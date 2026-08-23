"""The numbers quoted in prd/v2/, recomputed from the review CSV.

Every arm tally, the router's behaviour and the escalation economics are quoted in
four documents and a report. This file is the single place they are checked against
the data, so a claim cannot drift from its evidence silently.

Skips if the CSV is absent -- it lives at the repo root, not in the package.
"""
import collections
import csv
import os

import pytest

CSV = os.path.join(os.path.dirname(__file__), "..", "..", "..",
                   "v223_perfect_tier_picks.csv")
TIER = {"perfect": 0, "ok": 1, "fail": 2}


@pytest.fixture(scope="module")
def sets():
    if not os.path.exists(CSV):
        pytest.skip("v223_perfect_tier_picks.csv not present")
    by = collections.defaultdict(dict)
    for r in csv.DictReader(open(CSV)):
        by[r["set_id"]][r["arm"]] = r
    return by


def tally(sets, pick):
    c = collections.Counter()
    for d in sets.values():
        c[d[pick(d)]["tier"]] += 1
    return c["perfect"], c["ok"], c["fail"]


def test_sample_size(sets):
    """n = 38, one reviewer, one seed, unblinded. Quoted everywhere."""
    assert len(sets) == 38


def test_arm_tallies(sets):
    assert tally(sets, lambda d: "PHEAD") == (23, 5, 10)
    assert tally(sets, lambda d: "BC_klein") == (28, 6, 4)


def test_bc_is_the_strongest_single_arm(sets):
    """The comparison the whole harness is measured against."""
    p_phead, _, f_phead = tally(sets, lambda d: "PHEAD")
    p_bc, _, f_bc = tally(sets, lambda d: "BC_klein")
    assert p_bc > p_phead and f_bc < f_phead


def _router(t):
    return lambda d: ("BC_klein"
                      if float(d["PHEAD"]["hair_over_garment"]) >= t else "PHEAD")


def test_shipped_threshold_routes_ten_of_thirtyeight(sets):
    n = sum(1 for d in sets.values()
            if float(d["PHEAD"]["hair_over_garment"]) >= 0.14)
    assert n == 10


def test_shipped_threshold_tally(sets):
    assert tally(sets, _router(0.14)) == (28, 5, 5)


def test_the_low_threshold_plateau_is_flat(sets):
    """0.05 through 0.09 all give 29/6/3 -- a plateau, not a spike. This is the
    evidence that 0.14 is past the useful point, and the reason the cut-point is
    called out as retunable rather than settled. Recorded, NOT shipped: picking it
    off this scoreboard is fitting on the same 38 sets."""
    for t in (0.05, 0.06, 0.07, 0.08, 0.09):
        assert tally(sets, _router(t)) == (29, 6, 3), t


def test_the_low_threshold_beats_always_bc(sets):
    """Strictly better AND cheaper -- one more perfect, one fewer fail, 1.55
    generations against 2.00."""
    assert tally(sets, _router(0.08)) == (29, 6, 3)
    assert tally(sets, lambda d: "BC_klein") == (28, 6, 4)
    calls = sum(2 if float(d["PHEAD"]["hair_over_garment"]) >= 0.08 else 1
                for d in sets.values())
    assert calls == 59 and round(calls / len(sets), 2) == 1.55


def test_the_router_cannot_beat_the_oracle(sets):
    """Ceiling over PHEAD+BC is 29/6/3, which the 0.08 plateau already reaches. A
    better router is worth nothing; a different ARM is where the remaining 3 live."""
    oracle = tally(sets, lambda d: min(("PHEAD", "BC_klein"),
                                       key=lambda a: TIER[d[a]["tier"]]))
    assert oracle == (29, 6, 3)
    assert tally(sets, _router(0.08)) == oracle


def test_the_cheap_arm_wins_exactly_once(sets):
    """p015+p007: PHEAD perfect, BC fail. The bald pass damages it. This one set is
    the entire reason a router can beat always-BC."""
    wins = [s for s, d in sets.items()
            if TIER[d["PHEAD"]["tier"]] < TIER[d["BC_klein"]["tier"]]]
    assert wins == ["p015+p007"]
