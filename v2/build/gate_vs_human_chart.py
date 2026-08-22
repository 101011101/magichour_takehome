# Why the deterministic gate is not usable as a control signal, drawn six ways.
#
# The comparison that matters is not gate-vs-truth in the abstract -- it is
# gate-vs-Ray against Ray-vs-Ray. The reviewer marked the same outputs twice, months
# apart, under two different questions (AMT tier, then binary usable). If the second
# panel row shows his two passes agreeing while the gate agrees with neither, the
# problem is the instrument, not the noise floor.
import csv, collections, statistics as st
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

REPO = "/Users/arviny/Downloads/Code/magichour_takehome"
ORDER = ["PHEAD", "BC_klein", "QX_qwen_p1"]
SHORT = {"PHEAD": "PHEAD", "BC_klein": "BC_klein", "QX_qwen_p1": "QX"}
CHECKS = ["degenerate", "noop", "people", "identity", "background"]
GOOD, BAD, ACC, DIM = "#3fb950", "#f85149", "#7c5cff", "#8a8a94"

R = list(csv.DictReader(open(f"{REPO}/v223_cheapest_usable_picks.csv")))
sets = collections.OrderedDict()
for r in R:
    sets.setdefault(r["set_id"], {})[r["arm"]] = r
POS = [float(r["gate_score"]) for r in R if r["my_verdict"] == "usable"]
NEG = [float(r["gate_score"]) for r in R if r["my_verdict"] != "usable"]
AUC = sum((p > n) + 0.5 * (p == n) for p in POS for n in NEG) / (len(POS) * len(NEG))

plt.rcParams.update({"figure.facecolor": "white", "axes.facecolor": "white",
                     "font.size": 9, "axes.edgecolor": "#cccccc",
                     "axes.labelcolor": "#333", "text.color": "#222"})
fig, ax = plt.subplots(2, 3, figsize=(15.5, 8.4))
fig.suptitle("The deterministic gate against the reviewer  —  114 cells, 38 sets, "
             "3 arms", fontsize=13, fontweight="bold", y=0.985)

# 1 -- score distributions. The whole argument in one panel: they sit on top of
# each other, so no threshold can separate them.
a = ax[0][0]
bins = np.linspace(0, 1, 13)
a.hist([POS, NEG], bins=bins, color=[GOOD, BAD], label=[f"Ray: usable (n={len(POS)})",
        f"Ray: unusable (n={len(NEG)})"], density=True)
a.axvline(st.mean(POS), color=GOOD, ls="--", lw=1.4)
a.axvline(st.mean(NEG), color=BAD, ls="--", lw=1.4)
a.set_title(f"Gate score distributions overlap almost exactly\n"
            f"means {st.mean(POS):.3f} vs {st.mean(NEG):.3f}  —  gap 0.010",
            fontsize=10)
a.set_xlabel("gate composite score"); a.set_ylabel("density")
a.legend(fontsize=8, frameon=False)

# 2 -- ROC. AUC 0.506 is the headline number.
a = ax[0][1]
ths = np.linspace(-0.01, 1.01, 300)
tpr = [sum(1 for p in POS if p >= t) / len(POS) for t in ths]
fpr = [sum(1 for n in NEG if n >= t) / len(NEG) for t in ths]
a.plot(fpr, tpr, color=ACC, lw=2.2, label=f"gate  (AUC {AUC:.3f})")
a.plot([0, 1], [0, 1], color=DIM, ls="--", lw=1.2, label="coin flip (AUC 0.500)")
a.set_title("The gate cannot rank a good frame above a bad one",
            fontsize=10)
a.set_xlabel("false positive rate"); a.set_ylabel("true positive rate")
a.legend(fontsize=8, frameon=False, loc="lower right")
a.set_xlim(0, 1); a.set_ylim(0, 1)

# 3 -- agreement vs threshold against the do-nothing baseline. There is no
# threshold at which the gate is worth consulting.
a = ax[0][2]
TH = np.arange(0.05, 0.96, 0.05)
agree = [100 * sum(1 for r in R if (float(r["gate_score"]) >= t)
                   == (r["my_verdict"] == "usable")) / len(R) for t in TH]
base = 100 * len(POS) / len(R)
a.plot(TH, agree, color=ACC, lw=2.2, marker="o", ms=3.5, label="gate agreement")
a.axhline(base, color=BAD, ls="--", lw=1.6,
          label=f'"accept everything"  {base:.1f}%')
a.fill_between(TH, agree, base, where=np.array(agree) < base, color=BAD, alpha=.10)
a.set_title("No threshold beats accepting every frame unchecked", fontsize=10)
a.set_xlabel("acceptance threshold"); a.set_ylabel("% cells agreeing with Ray")
a.set_ylim(40, 80); a.legend(fontsize=8, frameon=False, loc="lower left")

# 4 -- per-check separation, the diagnosis. Identity is the one check that works,
# and it is flat here because these three arms cannot fail that way.
a = ax[1][0]
sep_all, sep_cas = [], []
gateall = json_all = None
import json
G = json.load(open(f"{REPO}/v2/runs/amt/_gate.json"))
T = {"top": "perfect", "mid": "ok", "out": "fail"}
H = {}
for r in csv.DictReader(open(f"{REPO}/v221_attention_mod_rankings (1).csv")):
    if r.get("tier") in T:
        H[(r["set_id"], r["arm"])] = T[r["tier"]]
for r in csv.DictReader(open(f"{REPO}/v221_phead_verdicts.csv")):
    H[(r["set_id"], "PHEAD")] = r["verdict"]
P = [(v, H[tuple(k.split("|"))]) for k, v in G.items() if tuple(k.split("|")) in H]
for c in CHECKS:
    m = {l: st.mean([v["checks"][c] for v, h in P if h == l]) for l in ("perfect", "fail")}
    sep_all.append(m["perfect"] - m["fail"])
    k = {v: st.mean([float(r["chk_" + c]) for r in R if r["my_verdict"] == v])
         for v in ("usable", "unusable")}
    sep_cas.append(k["usable"] - k["unusable"])
x = np.arange(len(CHECKS)); w = 0.38
a.bar(x - w/2, sep_all, w, color=ACC, label="all 12 arms (456 outputs)")
a.bar(x + w/2, sep_cas, w, color="#c9c9d1", label="the 3 cascade arms only")
a.axhline(0, color="#555", lw=1)
a.annotate("identity works —\nbut only where a\nhead survives in\nthe reference",
           xy=(3 - w/2, sep_all[3]), xytext=(1.15, 0.175), fontsize=8, color="#444",
           arrowprops=dict(arrowstyle="->", color="#666", lw=1))
a.set_xticks(x); a.set_xticklabels(CHECKS, fontsize=8.5)
a.set_title("Every check flatlines on the arms we would actually ship", fontsize=10)
a.set_ylabel("separation  (good − bad)")
a.legend(fontsize=8, frameon=False)

# 5 -- the control. Ray's two independent passes against each other.
a = ax[1][1]
tiers = ["perfect", "ok", "fail"]
u = [sum(1 for r in R if r["amt_tier"] == t and r["my_verdict"] == "usable") for t in tiers]
n = [sum(1 for r in R if r["amt_tier"] == t and r["my_verdict"] != "usable") for t in tiers]
pct = [100 * uu / (uu + nn) if uu + nn else 0 for uu, nn in zip(u, n)]
a.bar(tiers, u, color=GOOD, label="later call: usable")
a.bar(tiers, n, bottom=u, color=BAD, label="later call: unusable")
for i, (p_, uu, nn) in enumerate(zip(pct, u, n)):
    a.text(i, uu + nn + 1.5, f"{p_:.0f}% usable", ha="center", fontsize=9,
           fontweight="bold", color="#222")
a.set_title("The control: Ray's earlier AMT tier predicts Ray\n"
            "95% → 44% → 0%, perfectly ordered", fontsize=10)
a.set_xlabel("earlier AMT tier"); a.set_ylabel("cells")
a.set_ylim(0, max(uu + nn for uu, nn in zip(u, n)) + 12)
a.legend(fontsize=8, frameon=False, loc="upper right")

# 6 -- who actually rescues PHEAD. This is the ordering decision.
a = ax[1][2]
ph = [sid for sid, s in sets.items() if s["PHEAD"]["my_verdict"] != "usable"]
res = {aa: sum(1 for sid in ph if sets[sid][aa]["my_verdict"] == "usable")
       for aa in ("BC_klein", "QX_qwen_p1")}
a.bar(["BC_klein", "QX"], [res["BC_klein"], res["QX_qwen_p1"]],
      color=["#c9c9d1", ACC], width=.55)
a.axhline(len(ph), color=DIM, ls="--", lw=1.3)
a.text(1.42, len(ph) + .18, f"{len(ph)} PHEAD failures", fontsize=8.5,
       color=DIM, ha="right")
for i, v in enumerate([res["BC_klein"], res["QX_qwen_p1"]]):
    a.text(i, v + .25, f"{v}/{len(ph)}", ha="center", fontsize=11, fontweight="bold")
a.set_title("QX rescues nearly twice what BC_klein does\n"
            "— so QX belongs in slot 2, not slot 3", fontsize=10)
a.set_ylabel("PHEAD failures rescued"); a.set_ylim(0, len(ph) + 2)

for row in ax:
    for a in row:
        a.spines[["top", "right"]].set_visible(False)
        a.grid(axis="y", color="#eeeeee", lw=.8)
        a.set_axisbelow(True)
fig.tight_layout(rect=[0, 0.008, 1, 0.965])
o = f"{REPO}/prd/v2/v2.2/images/gate_vs_human.png"
fig.savefig(o, dpi=150)
print(o, f"AUC {AUC:.3f}")
