"""Analysis for the iron man 2 VEi judge run vs the v3.3 baseline record.

  .venv/bin/python v3/runs/v34/judge_ironman2_vei/analyse.py

Reads meta/vlm_scores.csv (VEi, 600 cells expected) and the repo-root
v33_ironman_vlm_scores_bca4.csv (arm V = the v3.3 lock; also BC cells, ignored
except for the record). Prints everything the report needs; writes meta/per_pair.csv.
"""
import csv, json, os, statistics

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..", "..", "..", "..")
CRITERIA = ["garment", "identity", "scene", "clean", "hands", "realism"]
FID = ["garment", "identity", "scene"]

def fid(r): return sum(int(r[c]) for c in FID) / 3
def fails(r): return int(r["garment"]) <= 2 or int(r["clean"]) <= 2

vei = [r for r in csv.DictReader(open(os.path.join(HERE, "meta", "vlm_scores.csv"))) if r["arm"] == "VEi"]
base = list(csv.DictReader(open(os.path.join(ROOT, "v33_ironman_vlm_scores_bca4.csv"))))
v = [r for r in base if r["arm"] == "V"]

print(f"VEi cells: {len(vei)}  (pairs: {len(set(r['set_id'] for r in vei))}, seeds: {sorted(set(r['seed'] for r in vei))})")
print(f"baseline V cells: {len(v)}  (pairs: {len(set(r['set_id'] for r in v))}, "
      f"seed counts: {[(s, sum(1 for r in v if r['seed']==s)) for s in sorted(set(r['seed'] for r in v))]})")

print("\n== per-criterion means (VEi vs baseline V) ==")
for c in CRITERIA:
    mv = statistics.mean(int(r[c]) for r in vei)
    mb = statistics.mean(int(r[c]) for r in v)
    print(f"  {c:9s} VEi {mv:.3f}  V {mb:.3f}  delta {mv-mb:+.3f}")
fv = statistics.mean(fid(r) for r in vei); fb = statistics.mean(fid(r) for r in v)
print(f"  {'fidelity':9s} VEi {fv:.3f}  V {fb:.3f}  delta {fv-fb:+.3f}")
m6v = statistics.mean(sum(int(r[c]) for c in CRITERIA)/6 for r in vei)
m6b = statistics.mean(sum(int(r[c]) for c in CRITERIA)/6 for r in v)
print(f"  {'mean of 6':9s} VEi {m6v:.3f}  V {m6b:.3f}  delta {m6v-m6b:+.3f}")

def rates(rows, label, npairs=200):
    cf = sum(1 for r in rows if fails(r))
    bypair = {}
    for r in rows: bypair.setdefault(r["set_id"], []).append(r)
    all_pass = sum(1 for rs in bypair.values() if not any(fails(r) for r in rs))
    any_pass = sum(1 for rs in bypair.values() if not all(fails(r) for r in rs))
    all3 = sum(1 for rs in bypair.values() if len(rs) == 3 and not any(fails(r) for r in rs))
    print(f"\n== fail proxy (garment<=2 or clean<=2): {label} ==")
    print(f"  cell fails: {cf}/{len(rows)} ({cf/len(rows):.1%})  -> cell pass {len(rows)-cf}/{len(rows)} ({(len(rows)-cf)/len(rows):.1%})")
    print(f"  pairs passing at ALL scored seeds: {all_pass}/{len(bypair)} ({all_pass/len(bypair):.1%})"
          f"  [with exactly 3 seeds scored: {all3}]")
    print(f"  pairs passing at >=1 seed:        {any_pass}/{len(bypair)} ({any_pass/len(bypair):.1%})")
    seedn = {}
    for rs in bypair.values(): seedn[len(rs)] = seedn.get(len(rs), 0) + 1
    print(f"  seeds scored per pair: {sorted(seedn.items())}")
    return bypair

bp_vei = rates(vei, "VEi")
bp_v = rates(v, "baseline V")

print("\n== distribution sanity (VEi) ==")
n555 = sum(1 for r in vei if all(int(r[c]) == 5 for c in FID))
print(f"  cells 5/5/5 on garment/identity/scene: {n555}/{len(vei)} ({n555/len(vei):.1%})")
for c in CRITERIA:
    from collections import Counter
    d = Counter(int(r[c]) for r in vei)
    print(f"  {c:9s} " + "  ".join(f"{k}:{d.get(k,0)}" for k in range(1, 6)))
g1 = sum(1 for r in vei if int(r["garment"]) == 1)
print(f"  garment=1 cells: {g1}/{len(vei)}")
n555b = sum(1 for r in v if all(int(r[c]) == 5 for c in FID))
g1b = sum(1 for r in v if int(r['garment']) == 1)
print(f"  [baseline V: 5/5/5 {n555b}/{len(v)} ({n555b/len(v):.1%}); garment=1 {g1b}/{len(v)}]")

print("\n== 10 worst VEi pairs by 3-seed mean fidelity ==")
pair_fid = sorted(((statistics.mean(fid(r) for r in rs), sid, rs) for sid, rs in bp_vei.items()))
for f_, sid, rs in pair_fid[:10]:
    scores = " ".join(f"s{r['seed']}:g{r['garment']}/i{r['identity']}/s{r['scene']}" for r in sorted(rs, key=lambda r: r["seed"]))
    note = max(rs, key=lambda r: len(r["note"]))["note"].replace("\n", " ")
    print(f"  {f_:.2f}  {sid}  [{scores}]")
    print(f"        {note[:400]}")

with open(os.path.join(HERE, "meta", "per_pair.csv"), "w", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["set_id", "fid_vei", "fid_v", "cell_fails_vei", "cell_fails_v", "n_seeds_v"])
    for sid in sorted(bp_vei):
        rs = bp_vei[sid]; vs = bp_v.get(sid, [])
        w.writerow([sid, round(statistics.mean(fid(r) for r in rs), 3),
                    round(statistics.mean(fid(r) for r in vs), 3) if vs else "",
                    sum(1 for r in rs if fails(r)), sum(1 for r in vs if fails(r)) if vs else "", len(vs)])

# paired comparison on the shared pairs, pair-level means (unequal seed counts on V)
shared = [s for s in bp_vei if s in bp_v]
dv = [statistics.mean(fid(r) for r in bp_vei[s]) - statistics.mean(fid(r) for r in bp_v[s]) for s in shared]
print(f"\n== paired per-pair fidelity (n={len(shared)} shared pairs; V mean over its scored seeds) ==")
print(f"  mean diff VEi-V {statistics.mean(dv):+.3f}  (VEi better on {sum(1 for d in dv if d>0)}, "
      f"V better on {sum(1 for d in dv if d<0)}, tie {sum(1 for d in dv if d==0)})")

tin = sum(int(r["tokens_in"]) for r in vei); tout = sum(int(r["tokens_out"]) for r in vei)
print(f"\ntokens: {tin} in / {tout} out; ~${(tin*5+tout*15)/1e6:.2f} at gpt-5.5 PRICE")
