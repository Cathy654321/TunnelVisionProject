
import os, sys, pickle
HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
from scipy.stats import spearmanr
from reddit_config import DATA, FIG
from analysis_analyzer import Analyzer
from analysis_reddit_tv import sliding, _smooth

SNAP = os.path.join(DATA, "snapshots_absa_scan")
OUTDIRS = [FIG]
_pf = os.path.join(os.path.dirname(HERE), "paper", "figures")
if os.path.isdir(_pf):
    OUTDIRS.append(_pf)
DATASETS = [("bbf7wd", "DS4 NZ gun debate"), ("bix6la", "DS5 80-20 rule"), ("bgknkt", "DS6 NIMBYism")]
plt.rcParams.update({"axes.labelsize": 16, "xtick.labelsize": 13, "ytick.labelsize": 13,
                     "legend.fontsize": 12, "pdf.fonttype": 42})


def load_event(sid):
    with open(os.path.join(SNAP, f"snapshot_reddit_{sid}.pkl"), "rb") as f:
        pickle.load(f); return pickle.load(f)[0]


def main():
    for sid, _ in DATASETS:
        ev = load_event(sid); n = len(ev.comments)
        sl = sliding(Analyzer(event=ev), ev.comments, n, 30, 5)
        xs = [r["timestep"] for r in sl]
        rA, _ = spearmanr(xs, [r["ASPE"] for r in sl])
        rC, _ = spearmanr(xs, [r["top5_share"] for r in sl])
        aspe = _smooth([r["ASPE"] for r in sl]); conc = _smooth([r["top5_share"] for r in sl])
        me = max(1, len(xs) // 9)
        fig, ax1 = plt.subplots(figsize=(3.7, 3.0))
        ax1.plot(xs, aspe, color="tab:blue", lw=2.2, marker="o", ms=4, markevery=me, label="ASPE")
        ax1.set_xlabel("Timestep (sliding window)"); ax1.set_ylabel("ASPE", color="tab:blue")
        ax1.tick_params(axis="y", labelcolor="tab:blue")
        ax1.xaxis.set_major_locator(MaxNLocator(5, integer=True)); ax1.yaxis.set_major_locator(MaxNLocator(5))
        ax1.grid(True, alpha=0.3)
        ax2 = ax1.twinx()
        ax2.plot(xs, conc, color="tab:red", lw=2.2, marker="s", ms=4, markevery=me, label="Top-5 share")
        ax2.set_ylabel("Top-5 pair share", color="tab:red"); ax2.tick_params(axis="y", labelcolor="tab:red")
        ax2.yaxis.set_major_locator(MaxNLocator(5))
        h1, l1 = ax1.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
        ax1.legend(h1 + h2, l1 + l2, loc="lower center", bbox_to_anchor=(0.5, 1.01), ncol=2,
                   fontsize=11.5, frameon=False, handlelength=1.6, columnspacing=1.0)
        fig.tight_layout(pad=0.3)
        for _d in OUTDIRS:
            fig.savefig(os.path.join(_d, f"reddit_narrowing_{sid}.pdf"), bbox_inches="tight", pad_inches=0.02)
        plt.close(fig)
        print(f"  {sid}: rho_ASPE={rA:+.2f} rho_conc={rC:+.2f} -> reddit_narrowing_{sid}.pdf")


if __name__ == "__main__":
    main()
