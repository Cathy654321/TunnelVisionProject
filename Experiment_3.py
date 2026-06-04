import os
import pandas as pd
import matplotlib
import numpy as np
from scipy.interpolate import UnivariateSpline

matplotlib.use("TkAgg")
import matplotlib.pyplot as plt

def normalize_strategy(s: str) -> str:
    s = str(s).strip().lower()

    if s in {"no", "none"}:
        return "No"
    return s

def prepare_df(df: pd.DataFrame) -> pd.DataFrame:

    df = df.copy()

    if "strategy" not in df.columns:
        raise ValueError("Missing required column: 'strategy'")
    if "dataset" not in df.columns:
        raise ValueError("Missing required column: 'dataset'")
    if "aspect_no" not in df.columns:
        raise ValueError("Missing required column: 'aspect_no'")

    df["strategy"] = df["strategy"].astype(str).map(normalize_strategy)

    for col in ["dataset", "aspect_no", "strategy_budget"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    for col in ["ASPE", "CASE"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df

def average_metric_by_budget_simple(
        df: pd.DataFrame,
        dataset_id: int,
        aspect_no: int,
        metric: str,
        strategy: str,
        budgets: list[int],
) -> pd.DataFrame:

    if metric not in df.columns:
        raise ValueError(f"Metric '{metric}' not found. Available: {list(df.columns)}")

    strategy_norm = normalize_strategy(strategy)

    base_mask = (
            (df["dataset"] == dataset_id) &
            (df["aspect_no"] == aspect_no) &
            (df["strategy"] == strategy_norm)
    )

    out_rows = []

    if strategy_norm == "No":
        sub = df.loc[base_mask, metric]
        avg_val = sub.mean() if len(sub) else float("nan")
        for b in budgets:
            out_rows.append({"budget": b, "avg_metric": avg_val})
        return pd.DataFrame(out_rows)

    if "strategy_budget" not in df.columns:
        raise ValueError("Missing required column for mitigation strategies: 'strategy_budget'")

    for b in budgets:
        sub = df.loc[base_mask & (df["strategy_budget"] == b), metric]
        avg_val = sub.mean() if len(sub) else float("nan")
        out_rows.append({"budget": b, "avg_metric": avg_val})

    return pd.DataFrame(out_rows)

def plot_trend_with_band(
        x,
        y,
        color: str,
        label: str,
        linewidth: int = 3,
        smooth_factor: float = 0.3,
        band_alpha: float = 0.18,
):

    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)

    order = np.argsort(x)
    x = x[order]
    y = y[order]

    spline = UnivariateSpline(x, y, s=smooth_factor)
    x_smooth = np.linspace(x.min(), x.max(), 200)
    y_smooth = spline(x_smooth)

    residuals = y - spline(x)
    std = float(np.std(residuals)) if len(residuals) > 1 else 0.0

    plt.plot(x_smooth, y_smooth, color=color, linewidth=linewidth, label=label)
    plt.fill_between(
        x_smooth,
        y_smooth - std,
        y_smooth + std,
        color=color,
        alpha=band_alpha,
        linewidth=0,
    )

def plot_avg_metric_vs_budget_simple(
        df: pd.DataFrame,
        dataset_id: int,
        aspect_no: int,
        metric: str = "CASE",
        strategies=("No", "add", "remove", "update", "hybrid", "summarize"),
        budgets=(1, 3, 5, 7, 9, 11, 13, 15),
        output_dir: str = "Figures",
        save_pdf: bool = True,
        show: bool = True,
        mark_target: int = 11,
):
    budgets = list(budgets)

    styles = [

        {"marker": "s", "linestyle": "--", "color": "green"},
        {"marker": "^", "linestyle": "-.", "color": "red"},
        {"marker": "D", "linestyle": ":", "color": "purple"},
        {"marker": "P", "linestyle": "-", "color": "orange"},
        {"marker": "X", "linestyle": "--", "color": "black"},
    ]

    plt.figure(figsize=(10, 8))
    any_plotted = False

    for idx, strategy in enumerate(strategies):
        avg_df = average_metric_by_budget_simple(
            df=df,
            dataset_id=dataset_id,
            aspect_no=aspect_no,
            metric=metric,
            strategy=strategy,
            budgets=budgets,
        )

        if avg_df["avg_metric"].isna().all():
            print(f"[Skip] No matched data for strategy={strategy}")
            continue

        style = styles[idx % len(styles)]
        step = max(1, len(avg_df) // max(1, mark_target))

        plt.plot(
            avg_df["budget"],
            avg_df["avg_metric"],
            linestyle="None",
            marker=style["marker"],
            markersize=8,
            color=style["color"],
        )

        plot_trend_with_band(
            x=avg_df["budget"].values,
            y=avg_df["avg_metric"].values,
            color=style["color"],
            label=normalize_strategy(strategy),
            smooth_factor=0.3,
            band_alpha=0.18,
        )

        any_plotted = True

    if not any_plotted:
        print("No lines plotted. Check dataset/aspect_no/strategy names and budgets.")
        plt.close()
        return None

    plt.xlabel("Budget", fontsize=16)
    plt.ylabel(f"Average {metric}", fontsize=16)

    budgets = [b for b in budgets if b % 2 == 1 and b >= 1]
    plt.xticks(budgets, fontsize=14)
    plt.yticks(fontsize=14)
    plt.tick_params(axis="both", which="major", width=2, length=8)
    plt.grid(True)

    plt.legend(loc="best", fontsize=16, markerscale=1.8, borderpad=1.2, labelspacing=1.0, handlelength=3.0)
    plt.tight_layout()

    os.makedirs(output_dir, exist_ok=True)

    output_filename = None
    if save_pdf:
        output_filename = os.path.join(
            output_dir,
            f"AVG_{metric}_ds{dataset_id}_a{aspect_no}_budget.pdf"
        )
        plt.savefig(output_filename, format="pdf", bbox_inches="tight")
        print(f"Plot saved to {output_filename}")

    if show:
        plt.show()
    else:
        plt.close()

    return output_filename

if __name__ == "__main__":
    CSV_PATH = "consolidated_results_case.csv"
    DATASET_ID = 2
    ASPECT_NO = 1
    METRIC_NAME = "ASPE"

    df_raw = pd.read_csv(CSV_PATH)
    df = prepare_df(df_raw)

    plot_avg_metric_vs_budget_simple(
        df=df,
        dataset_id=DATASET_ID,
        aspect_no=ASPECT_NO,
        metric=METRIC_NAME,
        strategies=("add", "remove", "update", "hybrid", "summarize"),
        budgets=[1, 3, 5, 7, 9, 11, 13, 15],
        output_dir="Figures",
        save_pdf=True,
        show=True,
    )
