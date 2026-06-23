
import os, sys, glob
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
from reddit_config import RES, FIG

OUTDIRS = [FIG]
_pf = os.path.join(os.path.dirname(HERE), "paper", "figures")
if os.path.isdir(_pf):
    OUTDIRS.append(_pf)
plt.rcParams.update({"axes.labelsize": 17, "xtick.labelsize": 14, "ytick.labelsize": 14,
                     "legend.fontsize": 12, "pdf.fonttype": 42})
STRAT = {"No": ("black", "-"), "add": ("tab:green", "--"), "remove": ("tab:red", "-."),
         "update": ("tab:blue", "-"), "summarize": ("tab:orange", ":"), "hybrid": ("tab:purple", "--")}
ASP = {1: ("tab:blue", "-"), 2: ("tab:green", "--"), 3: ("tab:red", ":")}
LW = 2.2


def band(ax, sub, label, color, ls):
    piv = sub.pivot_table(index="round", columns="seed", values="ASPE").dropna()
    if piv.empty:
        return
    m, s = piv.mean(axis=1), piv.std(axis=1)
    ax.plot(m.index, m.values, label=label, color=color, linestyle=ls, linewidth=LW)
    ax.fill_between(m.index, (m - s).values, (m + s).values, color=color, alpha=0.15, linewidth=0)


def finish(fig, ax, fname, ncol, fs=11):
    ax.set_xlabel("Round"); ax.set_ylabel("ASPE"); ax.grid(True, alpha=0.35)
    ax.xaxis.set_major_locator(MaxNLocator(5, integer=True)); ax.yaxis.set_major_locator(MaxNLocator(5))
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.01), ncol=ncol, fontsize=fs,
              frameon=False, handlelength=1.6, columnspacing=0.9, handletextpad=0.4)
    fig.tight_layout(pad=0.3)
    for _d in OUTDIRS:
        fig.savefig(os.path.join(_d, fname), bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)


def main():
    df = pd.concat([pd.read_csv(f) for f in glob.glob(os.path.join(RES, "seeds_scan", "*.csv"))], ignore_index=True)
    for ds in (0, 1, 2):
        no = df[(df.dataset == ds) & (df.strategy == "No") & (df.aspect_no == 1) & (df.warmup == 0)]
        fig, ax = plt.subplots(figsize=(3.6, 2.95))
        for a in (1, 2, 3):
            band(ax, df[(df.dataset == ds) & (df.strategy == "No") & (df.aspect_no == a) & (df.warmup == 0)],
                 f"{a} aspect(s)", *ASP[a])
        finish(fig, ax, f"reddit_scan_Exp1_ds{ds}.pdf", 3, 11.5)
        fig, ax = plt.subplots(figsize=(3.6, 2.95))
        for s in ["No", "add", "remove", "update", "summarize", "hybrid"]:
            sub = no if s == "No" else df[(df.dataset == ds) & (df.strategy == s) & (df.strategy_budget == 11) & (df.warmup == 0)]
            band(ax, sub, s, *STRAT[s])
        finish(fig, ax, f"reddit_scan_Exp2_ds{ds}_b11.pdf", 3, 11)
        fig, ax = plt.subplots(figsize=(3.6, 2.95))
        arms = [("No", no, "black", "-"),
                ("early update b11", df[(df.dataset == ds) & (df.strategy == "update") & (df.strategy_budget == 11) & (df.warmup == 0)], "tab:blue", "-"),
                ("late update b11", df[(df.dataset == ds) & (df.strategy == "update") & (df.strategy_budget == 11) & (df.warmup > 0)], "tab:red", "--"),
                ("late update b3", df[(df.dataset == ds) & (df.strategy == "update") & (df.strategy_budget == 3) & (df.warmup > 0)], "tab:orange", ":")]
        for lab, sub, c, ls in arms:
            band(ax, sub, lab, c, ls)
        finish(fig, ax, f"reddit_scan_Exp5_ds{ds}.pdf", 2, 10.5)
        print(f"ds{ds}: wrote reddit_scan_Exp1/Exp2/Exp5_ds{ds}.pdf")


if __name__ == "__main__":
    main()
