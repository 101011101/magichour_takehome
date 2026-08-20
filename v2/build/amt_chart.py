# Ternary-state chart for the attention modulation test, plus the failure-correlation
# matrix that explains WHY unions help.
#
# Three states only: perfect (tied-first), ok (ranked middle), fail (cut). Mean rank
# is not plotted anywhere -- the top band is a TIE, so averaging rank would treat
# ties as an ordering. That error was made once and withdrawn.
import csv, math, os
from collections import defaultdict
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(REPO, "prd", "v2", "v2.2", "images")
T = {"top": "perfect", "mid": "ok", "out": "fail"}
C = {"perfect": "#3fb950", "ok": "#d29922", "fail": "#f85149"}


def load():
    V = defaultdict(dict)
    for r in csv.DictReader(open(os.path.join(REPO, "v221_attention_mod_rankings (1).csv"))):
        V[r["set_id"]][r["arm"]] = T[r["tier"]]
    p = os.path.join(REPO, "v221_phead_verdicts.csv")
    if os.path.exists(p):
        for r in csv.DictReader(open(p)):
            V[r["set_id"]]["PHEAD"] = r["verdict"]
    return V


def main():
    V = load()
    sets = sorted(V)
    hi = [s for s in sets if s.startswith("HD_")]
    lo = [s for s in sets if not s.startswith("HD_")]
    ARMS = ["BC_klein", "D3B", "QX_qwen_p1", "PHEAD", "D1hB", "D2B",
            "control", "D3O", "D1hO", "D2O", "BALD_raw"]
    NICE = {"QX_qwen_p1": "QX (Qwen extract)", "BC_klein": "BC_klein (bald→crop)",
            "D3B": "D3B (pixelate/bald)", "PHEAD": "PHEAD (free)",
            "control": "control (C3.1)", "BALD_raw": "BALD (no crop)"}

    def share(arm, ss):
        d = {k: 0 for k in C}
        for s in ss:
            v = V[s].get(arm)
            if v:
                d[v] += 1
        n = sum(d.values()) or 1
        return {k: d[k] / n * 100 for k in C}, n

    fig = plt.figure(figsize=(15, 9), facecolor="#0d0d10")
    gs = fig.add_gridspec(2, 2, height_ratios=[1.35, 1], hspace=0.42, wspace=0.24)

    # ---- stacked ternary bars, low vs high
    for col, (ss, title) in enumerate(((lo, f"LOW-damage  (n={len(lo)})"),
                                       (hi, f"HIGH-damage  (n={len(hi)})"))):
        ax = fig.add_subplot(gs[0, col], facecolor="#0d0d10")
        order = sorted(ARMS, key=lambda a: -(share(a, ss)[0]["perfect"] - share(a, ss)[0]["fail"]))
        y = np.arange(len(order))
        left = np.zeros(len(order))
        for k in ("perfect", "ok", "fail"):
            w = np.array([share(a, ss)[0][k] for a in order])
            ax.barh(y, w, left=left, color=C[k], height=.72,
                    label=k if col == 0 else None, edgecolor="#0d0d10", linewidth=1.2)
            for i, (l, ww) in enumerate(zip(left, w)):
                if ww >= 9:
                    ax.text(l + ww / 2, i, f"{ww:.0f}", ha="center", va="center",
                            fontsize=9, color="#0d0d10", fontweight="bold")
            left += w
        ax.set_yticks(y)
        ax.set_yticklabels([NICE.get(a, a) for a in order], fontsize=9.5, color="#e8e8ea")
        ax.invert_yaxis()
        ax.set_xlim(0, 100)
        ax.set_xlabel("% of sets", color="#8a8a94", fontsize=9)
        ax.set_title(title, color="#e8e8ea", fontsize=12, pad=10, loc="left")
        ax.tick_params(colors="#8a8a94", labelsize=8.5)
        for sp in ax.spines.values():
            sp.set_color("#26262c")
        if col == 0:
            ax.legend(loc="upper center", bbox_to_anchor=(.5, -.14), frameon=False,
                      fontsize=9.5, labelcolor="#e8e8ea", ncol=3)

    # ---- failure correlation: which arms fail TOGETHER
    key = ["BC_klein", "D3B", "PHEAD", "control", "QX_qwen_p1"]
    N = len(sets)

    def phi(a, b):
        n11 = sum(1 for s in sets if V[s].get(a) == "fail" and V[s].get(b) == "fail")
        n10 = sum(1 for s in sets if V[s].get(a) == "fail" and V[s].get(b) != "fail")
        n01 = sum(1 for s in sets if V[s].get(a) != "fail" and V[s].get(b) == "fail")
        n00 = N - n11 - n10 - n01
        d = math.sqrt((n11 + n10) * (n01 + n00) * (n11 + n01) * (n10 + n00))
        return (n11 * n00 - n10 * n01) / d if d else 0.0

    ax = fig.add_subplot(gs[1, 0], facecolor="#0d0d10")
    M = np.array([[phi(a, b) for b in key] for a in key])
    im = ax.imshow(M, cmap="coolwarm", vmin=-.6, vmax=.6)
    ax.set_xticks(range(len(key)))
    ax.set_xticklabels([NICE.get(k, k).split(" ")[0] for k in key], rotation=30,
                       ha="right", fontsize=9, color="#e8e8ea")
    ax.set_yticks(range(len(key)))
    ax.set_yticklabels([NICE.get(k, k).split(" ")[0] for k in key], fontsize=9,
                       color="#e8e8ea")
    for i in range(len(key)):
        for j in range(len(key)):
            ax.text(j, i, f"{M[i, j]:.2f}", ha="center", va="center", fontsize=9,
                    color="#111" if abs(M[i, j]) > .3 else "#e8e8ea", fontweight="bold")
    ax.set_title("Do these two arms fail on the SAME sets?\n"
                 "red = fail together (redundant) · blue = fail apart (complementary)",
                 color="#e8e8ea", fontsize=10.5, pad=10, loc="left")
    for sp in ax.spines.values():
        sp.set_color("#26262c")

    # ---- union coverage: observed vs an independence model
    ax = fig.add_subplot(gs[1, 1], facecolor="#0d0d10")
    p = {a: sum(1 for s in sets if V[s].get(a) == "perfect") / N for a in ARMS}
    combos = [("D3B", "QX_qwen_p1"), ("BC_klein", "QX_qwen_p1"),
              ("PHEAD", "QX_qwen_p1"), ("BC_klein", "QX_qwen_p1", "D3B"),
              ("BC_klein", "D3B"), ("PHEAD", "BC_klein")]
    lab, obs, ind = [], [], []
    for c in combos:
        o = sum(1 for s in sets if any(V[s].get(a) == "perfect" for a in c)) / N * 100
        q = 1.0
        for a in c:
            q *= (1 - p[a])
        lab.append(" + ".join(NICE.get(x, x).split(" ")[0] for x in c))
        obs.append(o)
        ind.append((1 - q) * 100)
    y = np.arange(len(lab))
    ax.barh(y - .19, ind, height=.36, color="#3a3a44", label="if they failed independently")
    ax.barh(y + .19, obs, height=.36, color="#7c5cff", label="observed")
    for i, (o, n) in enumerate(zip(obs, ind)):
        ax.text(max(o, n) + 1.5, i + .19, f"{o - n:+.0f}", va="center", fontsize=9,
                color="#3fb950" if o > n else "#f85149", fontweight="bold")
    ax.set_yticks(y)
    ax.set_yticklabels(lab, fontsize=9, color="#e8e8ea")
    ax.invert_yaxis()
    ax.set_xlim(0, 108)
    ax.set_xlabel("% of sets with at least one 'perfect'", color="#8a8a94", fontsize=9)
    ax.set_title("Union coverage — does pairing arms beat chance?",
                 color="#e8e8ea", fontsize=10.5, pad=10, loc="left")
    ax.tick_params(colors="#8a8a94", labelsize=8.5)
    ax.legend(frameon=False, fontsize=8.5, labelcolor="#e8e8ea",
              loc="upper center", bbox_to_anchor=(.5, -.16), ncol=2)
    for sp in ax.spines.values():
        sp.set_color("#26262c")

    fig.suptitle("Attention Modulation Test — 38 sets, ternary outcome",
                 color="#e8e8ea", fontsize=14, x=.055, ha="left", y=.975)
    os.makedirs(OUT, exist_ok=True)
    p_out = os.path.join(OUT, "amt_outcomes.png")
    fig.savefig(p_out, dpi=135, facecolor="#0d0d10", bbox_inches="tight")
    print(p_out)


if __name__ == "__main__":
    main()
