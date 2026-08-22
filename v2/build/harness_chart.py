# The v2.2.3 harness, drawn from the three-tier marks.
#
# Every panel is computed from v223_perfect_tier_picks.csv -- the absolute perfect/ok/
# fail pass -- not from the earlier AMT ranking, whose "perfect" meant tied-for-first
# among ten arms and so could not drive an absolute stop decision.
import csv, collections
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

REPO = "/Users/arviny/Downloads/Code/magichour_takehome"
GOOD, MIDC, BAD, ACC, DIM = "#3fb950", "#d29922", "#f85149", "#7c5cff", "#8a8a94"
GEN = {"PHEAD": 1, "BC_klein": 2, "QX_qwen_p1": 2}
RANK = {"perfect": 0, "ok": 1, "fail": 2}
T = 0.14

R = list(csv.DictReader(open(f"{REPO}/v223_perfect_tier_picks.csv")))
S, H = collections.OrderedDict(), {}
for r in R:
    S.setdefault(r["set_id"], {})[r["arm"]] = r["tier"]
    H[r["set_id"]] = float(r["hair_over_garment"])
n = len(S)
first = {k: ("BC_klein" if H[k] >= T else "PHEAD") for k in S}

plt.rcParams.update({"figure.facecolor": "white", "axes.facecolor": "white",
                     "font.size": 9, "axes.edgecolor": "#ccc", "text.color": "#222"})
fig, ax = plt.subplots(2, 3, figsize=(15.5, 8.2))
fig.suptitle("v2.2.3 harness  —  router → PHEAD|BC_klein → QX on failure  "
             "—  38 sets, absolute perfect/ok/fail marks",
             fontsize=13, fontweight="bold", y=0.985)

# 1 -- the arm profiles. QX's shape is the whole reason it is the last line.
a = ax[0][0]
arms = ["PHEAD", "BC_klein", "QX_qwen_p1"]
lab = ["PHEAD", "BC_klein", "QX"]
P = [sum(S[k][x] == "perfect" for k in S) for x in arms]
O = [sum(S[k][x] == "ok" for k in S) for x in arms]
F = [sum(S[k][x] == "fail" for k in S) for x in arms]
a.bar(lab, P, color=GOOD, label="perfect")
a.bar(lab, O, bottom=P, color=MIDC, label="ok")
a.bar(lab, F, bottom=np.add(P, O), color=BAD, label="fail")
for i, (p, o, f) in enumerate(zip(P, O, F)):
    a.text(i, p / 2, str(p), ha="center", va="center", fontsize=10, fontweight="bold",
           color="#08130a")
    if f:
        a.text(i, p + o + f / 2, str(f), ha="center", va="center", fontsize=10,
               fontweight="bold", color="#fff")
a.set_title("QX has the lowest ceiling and by far the lowest floor\n"
            "1 failure in 38 — a safety net, not a quality arm", fontsize=10)
a.set_ylabel("sets"); a.legend(fontsize=8, frameon=False, loc="lower right")

# 2 -- the cost/quality ladder. The point is the zero, not the perfect count.
a = ax[0][1]
def sim(trigger, fanout):
    tot, sh = 0, collections.Counter()
    for k in S:
        f = first[k]; tot += GEN[f]
        if S[k][f] not in trigger:
            sh[S[k][f]] += 1; continue
        cand = [f] + fanout(f)
        for x in fanout(f):
            tot += GEN[x]
        sh[S[k][min(cand, key=lambda z: RANK[S[k][z]])]] += 1
    return tot / n, sh
rows = [("first arm only", *sim(set(), lambda f: [])),
        ("+ fail→QX", *sim({"fail"}, lambda f: ["QX_qwen_p1"])),
        ("+ not-perfect→QX", *sim({"fail", "ok"}, lambda f: ["QX_qwen_p1"])),
        ("always escalate", *sim({"perfect", "fail", "ok"}, lambda f: ["QX_qwen_p1"]))]
y = np.arange(len(rows))
for i, (nm, g, sh) in enumerate(rows):
    left = 0
    for key, col in (("perfect", GOOD), ("ok", MIDC), ("fail", BAD)):
        a.barh(i, sh[key], left=left, color=col); left += sh[key]
    a.text(n + 0.6, i, f"{g:.2f} gen", va="center", fontsize=9, fontweight="bold",
           color=ACC)
a.set_yticks(y); a.set_yticklabels([r[0] for r in rows], fontsize=9)
a.invert_yaxis(); a.set_xlim(0, n + 7)
a.set_title("A failure-only detector already removes every failure\n"
            "the extra 2 perfects cost +0.26 generations", fontsize=10)
a.set_xlabel("sets shipped, by tier")

# 3 -- the hair router. AUC on the absolute marks.
a = ax[0][2]
pos = [H[k] for k in S if S[k]["PHEAD"] != "perfect"]
neg = [H[k] for k in S if S[k]["PHEAD"] == "perfect"]
auc = sum((p > q) + 0.5 * (p == q) for p in pos for q in neg) / (len(pos) * len(neg))
a.hist([neg, pos], bins=np.linspace(0, .22, 12), color=[GOOD, BAD],
       label=[f"PHEAD perfect (n={len(neg)})", f"PHEAD not perfect (n={len(pos)})"])
a.axvline(T, color=ACC, ls="--", lw=2)
a.text(T + .004, a.get_ylim()[1] * .88, f"route at {T:.0%}", color=ACC, fontsize=9,
       fontweight="bold")
a.set_title(f"Hair over garment predicts PHEAD failure\nAUC {auc:.3f} "
            f"— free, deterministic, already in the pipeline", fontsize=10)
a.set_xlabel("hair over garment (C3.2 − C3.1)"); a.set_ylabel("sets")
a.legend(fontsize=8, frameon=False)

# 4 -- what no deterministic check can see.
a = ax[1][0]
FC = [r for r in R if r["arm"] == first[r["set_id"]]]
checks = ["chk_degenerate", "chk_noop", "chk_people", "chk_identity",
          "chk_background", "gate_score"]
aucs = []
for c in checks:
    p = [float(r[c]) for r in FC if r["tier"] == "perfect"]
    q = [float(r[c]) for r in FC if r["tier"] != "perfect"]
    aucs.append(sum((x > y_) + 0.5 * (x == y_) for x in p for y_ in q) / (len(p) * len(q)))
cols = [ACC if v >= .5 else BAD for v in aucs]
a.barh(range(len(checks)), [v - .5 for v in aucs], left=.5, color=cols)
a.axvline(.5, color="#555", lw=1.2)
a.axvline(auc, color=GOOD, ls="--", lw=1.8)
a.text(auc - .01, len(checks) - .4, "hair (input feature)", color=GOOD, fontsize=8,
       ha="right", fontweight="bold")
a.set_yticks(range(len(checks)))
a.set_yticklabels([c.replace("chk_", "") for c in checks], fontsize=8.5)
a.invert_yaxis(); a.set_xlim(.3, .95)
a.set_title("No output check separates perfect from needs-escalation\n"
            "every one is noise; background is inverted", fontsize=10)
a.set_xlabel("AUC  (0.5 = coin flip)")

# 5 -- the third arm buys nothing, and why.
a = ax[1][1]
other = {"PHEAD": "BC_klein", "BC_klein": "PHEAD"}
esc = [k for k in S if S[k][first[k]] == "fail"]
oth = collections.Counter(S[k][other[first[k]]] for k in esc)
qx = collections.Counter(S[k]["QX_qwen_p1"] for k in esc)
x = np.arange(3); w = .38
a.bar(x - w/2, [oth[t] for t in ("perfect", "ok", "fail")], w, color="#c9c9d1",
      label="the other subtractive arm")
a.bar(x + w/2, [qx[t] for t in ("perfect", "ok", "fail")], w, color=ACC, label="QX")
a.set_xticks(x); a.set_xticklabels(["perfect", "ok", "fail"])
a.set_title(f"On the {len(esc)} escalated sets, QX matches or beats\n"
            "the third arm every time — it shares the failure mode", fontsize=10)
a.set_ylabel("sets"); a.legend(fontsize=8, frameon=False)

# 6 -- VLM economics. The error tolerance, not the accuracy, is the argument.
a = ax[1][2]
G = 0.015
names = ["one VLM\ncheck", "one wasted\nescalation", "one\ngeneration"]
vals = [0.0003, 2 * G, G]
a.bar(names, vals, color=[GOOD, BAD, DIM], width=.55)
a.set_yscale("log")
for i, v in enumerate(vals):
    a.text(i, v * 1.35, f"${v:.4f}", ha="center", fontsize=9.5, fontweight="bold")
a.set_title("The VLM can be wrong 100 times per save\nand still pay for itself",
            fontsize=10)
a.set_ylabel("USD (log scale)"); a.set_ylim(1e-4, .12)

for row in ax:
    for b in row:
        b.spines[["top", "right"]].set_visible(False)
        b.grid(axis="both", color="#eee", lw=.8); b.set_axisbelow(True)
fig.tight_layout(rect=[0, .008, 1, .963])
o = f"{REPO}/prd/v2/v2.2/images/harness_v223.png"
fig.savefig(o, dpi=150)
print(o, f"hair AUC {auc:.3f}")
