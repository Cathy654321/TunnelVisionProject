import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from reddit_config import DS_TITLES, PKG as HERE, CONSOLIDATED as CSV, FIG, RES
os.makedirs(FIG, exist_ok=True); os.makedirs(RES, exist_ok=True)
STRATS = ["No", "add", "remove", "update", "hybrid", "summarize"]
STYLES = [{"m": "o", "ls": "-", "c": "blue"}, {"m": "s", "ls": "--", "c": "green"},
          {"m": "^", "ls": "-.", "c": "red"}, {"m": "D", "ls": ":", "c": "purple"},
          {"m": "P", "ls": "-", "c": "orange"}, {"m": "X", "ls": "--", "c": "black"}]

def load():
    df = pd.read_csv(CSV)
    for col in ["dataset", "aspect_no", "round", "strategy_budget", "ASPE", "CASE"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df["strategy"] = df["strategy"].astype(str).str.strip()
    return df

def exp1(df):
    for ds in sorted(df["dataset"].dropna().unique()):
        for metric in ["ASPE", "CASE"]:
            sub = df[(df.dataset == ds) & (df.strategy == "No")]
            if sub.empty:
                continue
            plt.figure(figsize=(8, 6))
            for i, a in enumerate([1, 2, 3]):
                g = sub[sub.aspect_no == a].sort_values("round")
                if g.empty:
                    continue
                s = STYLES[i]
                plt.plot(g["round"], g[metric], label=f"{a} aspect(s)", linewidth=3, markersize=7,
                         marker=s["m"], linestyle=s["ls"], color=s["c"], markevery=5)
            plt.xlabel("Round", fontsize=15); plt.ylabel(metric, fontsize=15)
            plt.title(f"Exp1 TV formation - {DS_TITLES.get(int(ds), ds)}", fontsize=13)
            plt.grid(True); plt.legend(fontsize=13); plt.tight_layout()
            plt.savefig(os.path.join(FIG, f"Exp1_{metric}_ds{int(ds)}.pdf")); plt.close()

def exp2(df):
    for ds in sorted(df["dataset"].dropna().unique()):
        for budget in [3, 11]:
            plt.figure(figsize=(8, 6))
            any_p = False
            for i, strat in enumerate(STRATS):
                if strat == "No":
                    g = df[(df.dataset == ds) & (df.strategy == "No") & (df.aspect_no == 1)]
                else:
                    g = df[(df.dataset == ds) & (df.strategy == strat) & (df.aspect_no == 1) &
                           (df.strategy_budget == budget)]
                g = g.sort_values("round")
                if g.empty:
                    continue
                s = STYLES[i]
                plt.plot(g["round"], g["ASPE"], label=strat, linewidth=3, markersize=7,
                         marker=s["m"], linestyle=s["ls"], color=s["c"], markevery=5)
                any_p = True
            if not any_p:
                plt.close(); continue
            plt.xlabel("Round", fontsize=15); plt.ylabel("ASPE", fontsize=15)
            plt.title(f"Exp2 strategies (b={budget}) - {DS_TITLES.get(int(ds), ds)}", fontsize=13)
            plt.grid(True); plt.legend(fontsize=12); plt.tight_layout()
            plt.savefig(os.path.join(FIG, f"Exp2_ASPE_ds{int(ds)}_b{budget}.pdf")); plt.close()

def exp3(df):
    budgets = [1, 3, 5, 7, 9, 11, 13, 15]
    for ds in sorted(df["dataset"].dropna().unique()):
        for metric in ["ASPE", "CASE"]:
            plt.figure(figsize=(8, 6))

            no = df[(df.dataset == ds) & (df.strategy == "No") & (df.aspect_no == 1)][metric].mean()
            plt.axhline(no, color="blue", linestyle="-", linewidth=2.5, label="No")
            for i, strat in enumerate(STRATS[1:], 1):
                ys = []
                for b in budgets:
                    g = df[(df.dataset == ds) & (df.strategy == strat) & (df.aspect_no == 1) &
                           (df.strategy_budget == b)][metric]
                    ys.append(g.mean() if len(g) else float("nan"))
                s = STYLES[i]
                plt.plot(budgets, ys, label=strat, linewidth=3, markersize=8,
                         marker=s["m"], linestyle=s["ls"], color=s["c"])
            plt.xlabel("Budget", fontsize=15); plt.ylabel(f"Average {metric}", fontsize=15)
            plt.title(f"Exp3 budget sensitivity - {DS_TITLES.get(int(ds), ds)}", fontsize=13)
            plt.grid(True); plt.legend(fontsize=12); plt.tight_layout()
            plt.savefig(os.path.join(FIG, f"Exp3_AVG_{metric}_ds{int(ds)}.pdf")); plt.close()

def exp4(df):
    lines = [("No", "No", None), ("remove b=5", "remove", 5), ("summarize b=5", "summarize", 5),
             ("remove b=999 (isolation)", "remove", 999), ("summarize b=999 (max)", "summarize", 999)]
    for ds in sorted(df["dataset"].dropna().unique()):
        plt.figure(figsize=(8, 6))
        any_p = False
        for i, (label, strat, b) in enumerate(lines):
            if strat == "No":
                g = df[(df.dataset == ds) & (df.strategy == "No") & (df.aspect_no == 1)]
            else:
                g = df[(df.dataset == ds) & (df.strategy == strat) & (df.aspect_no == 1) &
                       (df.strategy_budget == b)]
            g = g.sort_values("round")
            if g.empty:
                continue
            s = STYLES[i % len(STYLES)]
            plt.plot(g["round"], g["ASPE"], label=label, linewidth=3, markersize=7,
                     marker=s["m"], linestyle=s["ls"], color=s["c"], markevery=5)
            any_p = True
        if not any_p:
            plt.close(); continue
        plt.xlabel("Round", fontsize=15); plt.ylabel("ASPE", fontsize=15)
        plt.title(f"Exp4 isolation / max summary - {DS_TITLES.get(int(ds), ds)}", fontsize=13)
        plt.grid(True); plt.legend(fontsize=11); plt.tight_layout()
        plt.savefig(os.path.join(FIG, f"Exp4_ASPE_ds{int(ds)}_b999_vs_b5.pdf")); plt.close()

def summary_table(df):
    rows = []
    budgets = [0, 1, 3, 5, 7, 9, 11, 13, 15]
    for ds in sorted(df["dataset"].dropna().unique()):
        for strat in STRATS:
            for b in ([0] if strat == "No" else budgets[1:]):
                g = df[(df.dataset == ds) & (df.strategy == strat) & (df.aspect_no == 1) &
                       (df.strategy_budget == b)]
                if g.empty:
                    continue
                rows.append({"dataset": int(ds), "strategy": strat, "budget": b,
                             "avg_ASPE": round(g["ASPE"].mean(), 4), "avg_CASE": round(g["CASE"].mean(), 4)})
    out = pd.DataFrame(rows)
    out.to_csv(os.path.join(RES, "reddit_avg_aspe_case_by_strategy_budget.csv"), index=False)
    print(f"Summary table -> reddit_exp5/results/reddit_avg_aspe_case_by_strategy_budget.csv ({len(out)} rows)")
    return out

def write_latex_table(summ):

    budgets = [1, 3, 5, 9, 11, 15]
    dss = [int(d) for d in sorted(summ["dataset"].dropna().unique())]
    PAPER_OFFSET = 4
    colspec = "l c | " + " | ".join(["c c"] * len(dss))
    head_ds = " & ".join(
        (r"\multicolumn{2}{c|}{\textbf{DS%d}}" % (d + PAPER_OFFSET)) if i < len(dss) - 1
        else (r"\multicolumn{2}{c}{\textbf{DS%d}}" % (d + PAPER_OFFSET))
        for i, d in enumerate(dss))
    head_metric = " & ".join(["ASPE & CASE"] * len(dss))
    lines = [
        r"\begin{table}[ht]", r"\centering",
        r"\caption{Average ASPE and CASE by mitigation strategy and budget for the real "
        r"datasets (Bayesian continuation seeded at the cut point). `--' = not run for that "
        r"(strategy, budget).}",
        r"\label{tab:exp3}", r"\resizebox{\textwidth}{!}{%",
        r"\begin{tabular}{%s}" % colspec, r"\toprule",
        r"\textbf{Strategy} & \textbf{b} & " + head_ds + r" \\",
        r" & & " + head_metric + r" \\", r"\midrule",
    ]
    def cell(ds, strat, b):
        r = summ[(summ.dataset == ds) & (summ.strategy == strat) & (summ.budget == b)]
        if r.empty:
            return "--", "--"
        return f"{r['avg_ASPE'].iloc[0]:.3f}", f"{r['avg_CASE'].iloc[0]:.3f}"
    order = [("No", [0])] + [(s, budgets) for s in ["add", "remove", "update", "summarize"]]
    for strat, bs in order:
        for b in bs:
            cells = []
            for ds in dss:
                a, c = cell(ds, strat, b)
                cells += [a, c]
            if all(x == "--" for x in cells):
                continue
            lines.append(f"{strat} & {b} & " + " & ".join(cells) + r" \\")
        lines.append(r"\midrule")
    lines += [r"\bottomrule", r"\end{tabular}}", r"\end{table}"]
    with open(os.path.join(HERE, "reddit_results_table.tex"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("LaTeX table -> reddit_results_table.tex")

def main():
    df = load()
    print(f"Loaded {len(df)} rows, datasets={sorted(df['dataset'].dropna().unique())}")
    exp1(df); exp2(df); exp3(df); exp4(df)
    summ = summary_table(df)
    write_latex_table(summ)
    print("All Exp1-4 figures saved to reddit_exp5/figures/")

if __name__ == "__main__":
    main()
