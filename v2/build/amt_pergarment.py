# Per-set outcome: +1 perfect, 0 ok, -1 fail, three arms side by side.
#
# `ok` is drawn as a thin flat stub rather than nothing, because a zero-height bar is
# invisible and would read as missing data instead of as a middling result.
import csv, os
from collections import defaultdict
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(REPO, "prd", "v2", "v2.2", "images")
T = {"top": "perfect", "mid": "ok", "out": "fail"}
SCORE = {"perfect": 1, "ok": 0, "fail": -1}
ARMS = ["BC_klein", "PHEAD", "QX_qwen_p1"]
COL = {"BC_klein": "#7c5cff", "PHEAD": "#3fb950", "QX_qwen_p1": "#f0883e"}
NICE = {"BC_klein": "BC_klein  (bald → crop)", "PHEAD": "PHEAD  (free, deterministic)",
        "QX_qwen_p1": "QX  (Qwen extraction)"}


ABBR = {"dualuse_": "", "_nonceleb": "", "hugh_jackman_grey_suit_outdoor": "jackman",
        "man_black_suit_studio": "blk-suit", "zendaya_white_blazer_skirt": "zendaya",
        "scarlett_johansson_black_dress_backview_night": "scarlett",
        "queen_latifah_gown_stage": "latifah", "woman_top_denim_skirt": "denim-skirt",
        "lp_beige_long_coat_menswear": "beige-coat", "lp_floral_kimono_set": "kimono",
        "navy_peacoat_onmodel": "peacoat"}


def short(sid):
    s = sid
    for a, b in ABBR.items():
        s = s.replace(a, b)
    s = s.replace("HD_", "★")
    return s[:22] + "…" if len(s) > 23 else s


def main():
    V = defaultdict(dict)
    for r in csv.DictReader(open(os.path.join(REPO, "v221_attention_mod_rankings (1).csv"))):
        V[r["set_id"]][r["arm"]] = T[r["tier"]]
    p = os.path.join(REPO, "v221_phead_verdicts.csv")
    if os.path.exists(p):
        for r in csv.DictReader(open(p)):
            V[r["set_id"]]["PHEAD"] = r["verdict"]
    sets = sorted(V)
    lo = [s for s in sets if not s.startswith("HD_")]
    hi = [s for s in sets if s.startswith("HD_")]

    fig, axes = plt.subplots(2, 1, figsize=(17, 12.5), facecolor="#0d0d10",
                             gridspec_kw={"height_ratios": [len(lo), len(hi)],
                                          "hspace": .95})
    for ax, ss, title in ((axes[0], lo, f"LOW-damage references  (n={len(lo)})"),
                          (axes[1], hi, f"★ HIGH-damage references  (n={len(hi)})")):
        ax.set_facecolor("#0d0d10")
        x = np.arange(len(ss))
        w = .26
        for k, arm in enumerate(ARMS):
            off = (k - 1) * w
            for i, s in enumerate(ss):
                v = V[s].get(arm)
                if v is None:
                    continue
                y = SCORE[v]
                if y == 0:
                    # flat stub so `ok` is visible instead of reading as missing
                    # `ok` -- a visible flat stub, full colour, so it never reads
                    # as missing data
                    ax.bar(i + off, .115, bottom=-.057, width=w, color=COL[arm],
                           edgecolor="#0d0d10", linewidth=.6)
                else:
                    ax.bar(i + off, y, width=w, color=COL[arm], edgecolor="none")
        ax.axhline(0, color="#4a4a55", lw=1)
        ax.set_xticks(x)
        ax.set_xticklabels([short(s) for s in ss], rotation=50, ha="right",
                           fontsize=8.6, color="#e8e8ea")
        ax.set_yticks([-1, 0, 1])
        ax.set_yticklabels(["−1  fail", "0  ok", "+1  perfect"], fontsize=9.5,
                           color="#e8e8ea")
        ax.set_ylim(-1.35, 1.35)
        ax.set_xlim(-.7, len(ss) - .3)
        ax.set_title(title, color="#e8e8ea", fontsize=12, loc="left", pad=8)
        ax.tick_params(colors="#8a8a94")
        ax.grid(axis="y", color="#26262c", lw=.8)
        ax.set_axisbelow(True)
        for sp in ax.spines.values():
            sp.set_color("#26262c")
    handles = [plt.Rectangle((0, 0), 1, 1, color=COL[a]) for a in ARMS]
    axes[0].legend(handles, [NICE[a] for a in ARMS], frameon=False, fontsize=10,
                   labelcolor="#e8e8ea", ncol=3, loc="upper center",
                   bbox_to_anchor=(.5, 1.22))
    fig.suptitle("Per-reference outcome  —  the two mechanisms disagree, which is why "
                 "pairing them works",
                 color="#e8e8ea", fontsize=13.5, x=.5, y=1.0)
    os.makedirs(OUT, exist_ok=True)
    o = os.path.join(OUT, "amt_per_reference.png")
    fig.savefig(o, dpi=130, facecolor="#0d0d10", bbox_inches="tight")
    print(o)


if __name__ == "__main__":
    main()
