"""VEi vs VE and VEi vs VS on the v3.4 failure set, all A100, seeds 49/50/51, judged blind
by ironman_vlm.score(). Pairs are the unit; seeds are draws. Same statistics as
judge_fal_vs_a100/analyse.py + null.py, with the same-seed pairing (all arms share seeds
49/50/51, so position-paired = same-seed). Writes meta/per_pair.csv, meta/analysis.json."""
import csv, itertools, json, os
import numpy as np
from scipy import stats

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
CRIT = ["garment", "identity", "scene", "clean", "hands", "realism"]
FID, REAL = ["garment", "identity", "scene"], ["clean", "hands", "realism"]
PRICE = {"gpt-5.5": (5.0, 15.0)}
ARMS, SEEDS = ["VEi", "VE", "VS"], ["49", "50", "51"]
COMPS = [("VEi", "VE"), ("VEi", "VS"), ("VE", "VS")]
rng = np.random.default_rng(0)

rows = list(csv.DictReader(open(os.path.join(HERE, "meta", "vlm_scores.csv"))))
cls = {r["set_id"]: r for r in csv.DictReader(open(os.path.join(ROOT, "v3", "testsets", "v34_failures.csv")))}
cell = {}
for r in rows:
    v = {c: int(r[c]) for c in CRIT}
    v["fid"] = np.mean([v[c] for c in FID]); v["real"] = np.mean([v[c] for c in REAL]); v["mean6"] = np.mean([v[c] for c in CRIT])
    v["note"] = r["note"]; v["tin"] = int(r["tokens_in"]); v["tout"] = int(r["tokens_out"])
    cell[(r["set_id"], r["arm"], r["seed"])] = v
tin = sum(v["tin"] for v in cell.values()); tout = sum(v["tout"] for v in cell.values())
usd = (tin * PRICE["gpt-5.5"][0] + tout * PRICE["gpt-5.5"][1]) / 1e6
print(f"scored cells: {len(cell)} / 279   tokens in {tin:,} out {tout:,}   ~${usd:.2f} at $5/$15 per M (PRICE table in ironman_vlm.py)")

pairs = sorted(cls)
complete = [p for p in pairs if all((p, a, s) in cell for a in ARMS for s in SEEDS)]
partial = [p for p in pairs if p not in complete and any((p, a, s) in cell for a in ARMS for s in SEEDS)]
print(f"pairs with all 9 cells: {len(complete)} / {len(pairs)}; partial: {partial}")
METRICS = ["fid", "real", "mean6"] + CRIT

def pairmean(p, arm, m):
    return float(np.mean([cell[(p, arm, s)][m] for s in SEEDS]))

def boot_ci(d, B=20000):
    d = np.asarray(d, float); idx = rng.integers(0, len(d), (B, len(d)))
    m = d[idx].mean(1); return float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))

def tests(d):
    d = np.asarray(d, float); nz = d[d != 0]
    pos, neg = int((nz > 0).sum()), int((nz < 0).sum())
    sign_p = float(stats.binomtest(pos, pos + neg, 0.5).pvalue) if len(nz) else 1.0
    try: wil_p = float(stats.wilcoxon(d, zero_method="wilcox").pvalue) if len(nz) else 1.0
    except ValueError: wil_p = 1.0
    lo, hi = boot_ci(d)
    return {"n": int(len(d)), "mean_diff": float(d.mean()), "ci95": [lo, hi], "sd": float(d.std(ddof=1)) if len(d) > 1 else 0.0,
            "pos": pos, "neg": neg, "zero": int((d == 0).sum()), "sign_p": sign_p, "wilcoxon_p": wil_p}

def winner(f1, r1, f2, r2, eps=1e-9):
    # SCORING_CRITERIA §4: fidelity first, realism breaks a fidelity tie
    if f1 > f2 + eps: return 1
    if f2 > f1 + eps: return -1
    if r1 > r2 + eps: return 1
    if r2 > r1 + eps: return -1
    return 0

out = {"scored_cells": len(cell), "tokens_in": tin, "tokens_out": tout, "usd_est": usd,
       "pairs_complete": len(complete), "pairs_partial": partial}
per_pair = []
for p in complete:
    d = {"set_id": p, "class": cls[p]["class"], "seed_stable": cls[p]["seed_stable"]}
    for a in ARMS:
        for m in METRICS: d[f"{a}_{m}"] = pairmean(p, a, m)
    for a, b in COMPS:
        for m in METRICS: d[f"diff_{m}_{a}v{b}"] = d[f"{a}_{m}"] - d[f"{b}_{m}"]
        w = winner(d[f"{a}_fid"], d[f"{a}_real"], d[f"{b}_fid"], d[f"{b}_real"])
        d[f"winner_{a}v{b}"] = a if w == 1 else b if w == -1 else "tie"
        cross = [winner(cell[(p, a, s)]["fid"], cell[(p, a, s)]["real"], cell[(p, b, t)]["fid"], cell[(p, b, t)]["real"])
                 for s in SEEDS for t in SEEDS]
        d[f"cross_{a}_{a}v{b}"] = cross.count(1); d[f"cross_{b}_{a}v{b}"] = cross.count(-1); d[f"cross_tie_{a}v{b}"] = cross.count(0)
        same = [winner(cell[(p, a, s)]["fid"], cell[(p, a, s)]["real"], cell[(p, b, s)]["fid"], cell[(p, b, s)]["real"]) for s in SEEDS]
        d[f"same_{a}_{a}v{b}"] = same.count(1); d[f"same_{b}_{a}v{b}"] = same.count(-1); d[f"same_tie_{a}v{b}"] = same.count(0)
    per_pair.append(d)
with open(os.path.join(HERE, "meta", "per_pair.csv"), "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(per_pair[0].keys())); w.writeheader()
    for d in per_pair: w.writerow({k: (round(v, 3) if isinstance(v, float) else v) for k, v in d.items()})

for a, b in COMPS:
    key = f"{a}v{b}"
    print(f"\n== paired difference {a} - {b}, per pair (mean over 3 seeds each) ==")
    out.setdefault("paired", {})[key] = {}
    for m in METRICS:
        t = tests([d[f"diff_{m}_{key}"] for d in per_pair])
        t[f"{a}_mean"] = float(np.mean([d[f"{a}_{m}"] for d in per_pair])); t[f"{b}_mean"] = float(np.mean([d[f"{b}_{m}"] for d in per_pair]))
        out["paired"][key][m] = t
        print(f"{m:9s} {a} {t[f'{a}_mean']:.3f}  {b} {t[f'{b}_mean']:.3f}  diff {t['mean_diff']:+.3f}  CI95 [{t['ci95'][0]:+.3f}, {t['ci95'][1]:+.3f}]  "
              f"+{t['pos']}/-{t['neg']}/={t['zero']}  sign p={t['sign_p']:.3f}  wilcoxon p={t['wilcoxon_p']:.3f}")
    wins = {a: sum(1 for d in per_pair if d[f"winner_{key}"] == a), b: sum(1 for d in per_pair if d[f"winner_{key}"] == b),
            "tie": sum(1 for d in per_pair if d[f"winner_{key}"] == "tie")}
    cross = {k: sum(d[f"cross_{k}_{key}"] for d in per_pair) for k in (a, b)}; cross["tie"] = sum(d[f"cross_tie_{key}"] for d in per_pair)
    same = {k: sum(d[f"same_{k}_{key}"] for d in per_pair) for k in (a, b)}; same["tie"] = sum(d[f"same_tie_{key}"] for d in per_pair)
    out["paired"][key]["wins_pair"] = wins; out["paired"][key]["wins_cross_cells"] = cross; out["paired"][key]["wins_same_seed_cells"] = same
    print(f"pair winners (fidelity first, realism breaks ties): {a} {wins[a]} · {b} {wins[b]} · tie {wins['tie']}")
    print(f"   all 3x3 cross-seed cells ({sum(cross.values())}): {a} {cross[a]} · {b} {cross[b]} · tie {cross['tie']}")
    print(f"   same-seed cells ({sum(same.values())}): {a} {same[a]} · {b} {same[b]} · tie {same['tie']}")
    all_a = [d["set_id"] for d in per_pair if d[f"cross_{a}_{key}"] == 9]; all_b = [d["set_id"] for d in per_pair if d[f"cross_{b}_{key}"] == 9]
    s3a = [d["set_id"] for d in per_pair if d[f"same_{a}_{key}"] == 3]; s3b = [d["set_id"] for d in per_pair if d[f"same_{b}_{key}"] == 3]
    out["paired"][key]["all9"] = {a: all_a, b: all_b}; out["paired"][key]["same3"] = {a: s3a, b: s3b}
    print(f"   {a} wins all 9 cross: {all_a}\n   {b} wins all 9 cross: {all_b}")
    print(f"   {a} wins all 3 same-seed: {s3a}\n   {b} wins all 3 same-seed: {s3b}")

    # within-pair label permutation: shuffle which 3 of the pair's 6 cells are labelled `a` (the "arm is just another seed" null)
    X = np.array([[[cell[(p, x, s)][m] for m in ("fid", "real", "mean6")] for s in SEEDS] for p in complete for x in (a, b)])
    X = X.reshape(len(complete), 2, 3, 3)  # pair, arm(a,b), seed, metric
    obs = (X[:, 0].mean(1) - X[:, 1].mean(1))                       # pairs x 3
    obs_w = sum(winner(*X[i, 0].mean(0)[:2], *X[i, 1].mean(0)[:2]) for i in range(len(complete)))
    B = 20000; combos = list(itertools.combinations(range(6), 3))
    six = X.reshape(len(complete), 6, 3)
    null = np.zeros((B, 3)); null_w = np.zeros(B)
    for bi in range(B):
        dd = np.zeros(3); ww = 0
        for i in range(len(complete)):
            c = combos[rng.integers(len(combos))]; o = [j for j in range(6) if j not in c]
            va, vb = six[i, list(c)].mean(0), six[i, o].mean(0); dd += va - vb; ww += winner(va[0], va[1], vb[0], vb[1])
        null[bi] = dd / len(complete); null_w[bi] = ww
    out["paired"][key]["perm"] = {}
    for j, m in enumerate(["fid", "real", "mean6"]):
        p2 = float((np.abs(null[:, j]) >= abs(obs[:, j].mean()) - 1e-12).mean()); p1 = float((null[:, j] >= obs[:, j].mean() - 1e-12).mean())
        out["paired"][key]["perm"][m] = {"obs": float(obs[:, j].mean()), "p_two_sided": p2, "p_one_sided": p1,
                                         "null_sd": float(null[:, j].std()), "null_q95_abs": float(np.percentile(np.abs(null[:, j]), 95))}
        print(f"   perm {m:6s}: obs {obs[:, j].mean():+.3f}  p2 {p2:.3f}  p1({a}>{b}) {p1:.3f}  null SD {null[:, j].std():.3f}  95% |null| < {np.percentile(np.abs(null[:, j]), 95):.3f}")
    pw2 = float((np.abs(null_w) >= abs(obs_w)).mean())
    out["paired"][key]["perm"]["wins"] = {"obs": int(obs_w), "p_two_sided": pw2, "null_sd": float(null_w.std())}
    print(f"   perm pair-win margin {obs_w:+d}: p two-sided {pw2:.3f}; null SD {null_w.std():.2f}")

print("\n== cell-level means (93 cells per arm) and fail proxy (garment<=2 or clean<=2) ==")
out["cells"] = {}
for a in ARMS:
    cs = [cell[(p, a, s)] for p in complete for s in SEEDS]
    fails = sum(1 for c in cs if c["garment"] <= 2 or c["clean"] <= 2)
    out["cells"][a] = {m: float(np.mean([c[m] for c in cs])) for m in METRICS}; out["cells"][a]["fail_proxy"] = fails; out["cells"][a]["n"] = len(cs)
    print(f"{a:4s} n={len(cs)} " + "  ".join(f"{m} {out['cells'][a][m]:.2f}" for m in METRICS) + f"  fail-proxy {fails}/{len(cs)}")
for a in ARMS:
    sds = [np.std([cell[(p, a, s)]["fid"] for s in SEEDS], ddof=1) for p in complete]
    out["cells"][a]["within_pair_seed_sd_fid"] = float(np.mean(sds))
    print(f"{a:4s} mean within-pair across-seed SD of fidelity: {np.mean(sds):.3f}")

print("\n== same-arm seed-vs-seed splits (fresh-draw baseline; first / second / tie; mean fid diff) ==")
out["seed_splits"] = {}
for a in ARMS:
    for s, t in itertools.combinations(SEEDS, 2):
        ws = [winner(cell[(p, a, s)]["fid"], cell[(p, a, s)]["real"], cell[(p, a, t)]["fid"], cell[(p, a, t)]["real"]) for p in complete]
        dd = np.mean([cell[(p, a, s)]["fid"] - cell[(p, a, t)]["fid"] for p in complete])
        out["seed_splits"][f"{a} s{s} vs s{t}"] = {"first": ws.count(1), "second": ws.count(-1), "tie": ws.count(0), "fid_diff": float(dd)}
        print(f"  {a:4s} s{s} vs s{t}: {ws.count(1):2d} / {ws.count(-1):2d} / {ws.count(0):2d}   fid diff {dd:+.3f}")

print("\n== per-class (VEi - VE and VEi - VS on fidelity) ==")
out["per_class"] = {}
for k in ("F1", "F2", "F3", "F4"):
    ds = [d for d in per_pair if d["class"] == k]
    if not ds: continue
    out["per_class"][k] = {"n": len(ds)}
    line = f"{k} n={len(ds):2d} fid " + " ".join(f"{a} {np.mean([d[f'{a}_fid'] for d in ds]):.2f}" for a in ARMS)
    for a, b in COMPS[:2]:
        t = tests([d[f"diff_fid_{a}v{b}"] for d in ds])
        w = {x: sum(1 for d in ds if d[f"winner_{a}v{b}"] == x) for x in (a, b, "tie")}
        out["per_class"][k][f"{a}v{b}"] = {"fid": t, "wins": w}
        line += f" | {a}-{b} {t['mean_diff']:+.2f} CI[{t['ci95'][0]:+.2f},{t['ci95'][1]:+.2f}] wins {w[a]}/{w[b]}/{w['tie']}"
    print(line)

print("\n== seed-stable pairs, garment mean per arm ==")
for d in per_pair:
    if d["seed_stable"] == "yes":
        print(f"  {d['set_id'][:60]:60s} garment " + " ".join(f"{a} {d[f'{a}_garment']:.2f}" for a in ARMS))

print("\n== notable pairs (all cells) ==")
NOTABLE = ["g027+p003", "g029+p004", "p019+dualuse_gal_gadot_blue_dress_redcarpet", "p015+p016"]
out["notable"] = {}
for p in NOTABLE:
    print(f"-- {p}")
    out["notable"][p] = {}
    for a in ARMS:
        for s in SEEDS:
            c = cell.get((p, a, s))
            if c:
                out["notable"][p][f"{a}_s{s}"] = {k: c[k] for k in CRIT + ["note"]}
                print(f"  {a:4s} s{s}: " + " ".join(f"{k}={c[k]}" for k in CRIT) + f"  fid={c['fid']:.2f} real={c['real']:.2f}\n     {c['note']}")

def clean(o):
    if isinstance(o, dict): return {k: clean(v) for k, v in o.items()}
    if isinstance(o, list): return [clean(v) for v in o]
    if isinstance(o, (np.floating, float)): return round(float(o), 4)
    if isinstance(o, np.integer): return int(o)
    return o
json.dump(clean(out), open(os.path.join(HERE, "meta", "analysis.json"), "w"), indent=1)

print("\n== per-pair table (sorted by diff fid VEi-VE) ==")
print("set_id | class | VEi fid/real | VE fid/real | VS fid/real | dVE | dVS | winner VEivVE | VEivVS")
for d in sorted(per_pair, key=lambda d: -d["diff_fid_VEivVE"]):
    print(f"{d['set_id'][:70]:70s} {d['class']} {d['VEi_fid']:.2f}/{d['VEi_real']:.2f} {d['VE_fid']:.2f}/{d['VE_real']:.2f} "
          f"{d['VS_fid']:.2f}/{d['VS_real']:.2f} {d['diff_fid_VEivVE']:+.2f} {d['diff_fid_VEivVS']:+.2f} "
          f"{d['winner_VEivVE']:4s} {d['winner_VEivVS']:4s}")
