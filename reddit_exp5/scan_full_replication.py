
import os, sys, json, glob
import numpy as np
import pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from reddit_config import DATA, RES
import Experiments_reddit_main as M
import Experiments_reddit_seeds as S

M.SNAP_DIR = os.path.join(DATA, "snapshots_absa_scan")
CUTS = {k: int(v["cut_index"]) for k, v in
        json.load(open(os.path.join(DATA, "reddit_cut_points_scan.json"))).items()}
DATASETS = [("bbf7wd", 0, "newzealand"), ("bix6la", 1, "PurplePillDebate"), ("bgknkt", 2, "bayarea")]
NUM_SEEDS = 10
RES_SCAN = os.path.join(RES, "seeds_scan")
os.makedirs(RES_SCAN, exist_ok=True)


def out_path(ds, sid, strat, b, w, a, k):
    return os.path.join(RES_SCAN, f"ds{ds}_{sid}_a{a}_s{strat}_b{b}_w{w}_seed{k}.csv")


def run():
    cfgs = S.build_scenarios()
    for sid, ds, lab in DATASETS:
        cut = CUTS[sid]
        todo = [(c, k) for c in cfgs for k in range(NUM_SEEDS)
                if not os.path.exists(out_path(ds, sid, c[0], c[1], c[2], c[3], k))]
        print(f"[{sid}/DS{ds+4} {lab}] cut={cut}: {len(todo)}/{len(cfgs)*NUM_SEEDS} runs", flush=True)
        for i, ((strat, b, w, a), k) in enumerate(todo, 1):
            rows = S.run_one(sid, ds, cut, strat, b, w, a, k)
            pd.DataFrame(rows).to_csv(out_path(ds, sid, strat, b, w, a, k), index=False)
            if i % 25 == 0:
                print(f"   {i}/{len(todo)}", flush=True)
    print("[runs done]", flush=True)


def aggregate():
    from scipy.stats import wilcoxon
    df = pd.concat([pd.read_csv(f) for f in glob.glob(os.path.join(RES_SCAN, "*.csv"))], ignore_index=True)
    early = df[df.warmup == 0]
    g = (early[early.aspect_no == 1].groupby(["dataset", "strategy", "strategy_budget", "seed"])["ASPE"]
         .mean().reset_index(name="run_mean"))
    t4 = g.groupby(["dataset", "strategy", "strategy_budget"])["run_mean"].agg(["mean", "std", "count"]).reset_index()
    t4.to_csv(os.path.join(RES, "scan_table4.csv"), index=False)
    rows = []
    for ds in sorted(g.dataset.unique()):
        base = g[(g.dataset == ds) & (g.strategy == "No")].set_index("seed")["run_mean"]
        for (st, b), sub in g[(g.dataset == ds) & (g.strategy != "No")].groupby(["strategy", "strategy_budget"]):
            s = sub.set_index("seed")["run_mean"].reindex(base.index).dropna()
            common = base.reindex(s.index)
            if len(s) >= 6:
                try:
                    _, p = wilcoxon(s, common, alternative="greater")
                except ValueError:
                    p = float("nan")
                rows.append({"dataset": ds, "strategy": st, "budget": b, "mean_diff": (s - common).mean(), "p": p})
    pd.DataFrame(rows).to_csv(os.path.join(RES, "scan_seeds_stats.csv"), index=False)

    def finals(sub):
        return sub.loc[sub.groupby("seed")["round"].idxmax()]["ASPE"]
    t5 = []
    for ds in sorted(df.dataset.unique()):
        arms = {"No": df[(df.dataset == ds) & (df.strategy == "No") & (df.aspect_no == 1) & (df.warmup == 0)],
                "early_b11": df[(df.dataset == ds) & (df.strategy == "update") & (df.strategy_budget == 11) & (df.warmup == 0)],
                "late_b11": df[(df.dataset == ds) & (df.strategy == "update") & (df.strategy_budget == 11) & (df.warmup > 0)],
                "late_b3": df[(df.dataset == ds) & (df.strategy == "update") & (df.strategy_budget == 3) & (df.warmup > 0)]}
        for arm, sub in arms.items():
            if len(sub):
                fr = finals(sub); t5.append({"dataset": ds, "arm": arm, "mean": fr.mean(), "std": fr.std(), "n": len(fr)})
    pd.DataFrame(t5).to_csv(os.path.join(RES, "scan_table5.csv"), index=False)
    fm = []
    for ds in sorted(df.dataset.unique()):
        for a in (1, 2, 3):
            sub = df[(df.dataset == ds) & (df.strategy == "No") & (df.aspect_no == a)]
            if len(sub):
                fr = finals(sub); fm.append({"dataset": ds, "aspect_no": a, "final_mean": fr.mean(), "final_std": fr.std()})
    pd.DataFrame(fm).to_csv(os.path.join(RES, "scan_formation.csv"), index=False)
    print("[aggregated] -> scan_table4.csv, scan_table5.csv, scan_formation.csv, scan_seeds_stats.csv", flush=True)


if __name__ == "__main__":
    run()
    aggregate()
