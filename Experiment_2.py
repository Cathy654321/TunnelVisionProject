import os
import pandas as pd
import matplotlib

matplotlib.use("TkAgg")
import matplotlib.pyplot as plt

def load_results(csv_path: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path)

    if "strategy" in df.columns:
        df["strategy"] = df["strategy"].astype(str).str.strip()
        df["strategy"] = df["strategy"].replace({"no": "No", "NO": "No"})

    for col in ["dataset", "aspect_no", "round", "windows_size", "strategy_budget"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    for col in ["mitigation_ratio", "ASPE", "CASE"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df

def filter_for_strategy_compare(
        df: pd.DataFrame,
        dataset: int,
        strategy: str,
        budget: int | None,
        aspect_no: int | None = None,
        windows_size: int | None = None,
        mitigation_ratio: float | None = None,
) -> pd.DataFrame:

    strategy = str(strategy).strip()
    if strategy.lower() == "no":
        strategy = "No"

    mask = (df["dataset"] == dataset) & (df["strategy"].astype(str).str.strip() == strategy)

    if aspect_no is not None:
        mask &= (df["aspect_no"] == aspect_no)

    if windows_size is not None:
        mask &= (df["windows_size"] == windows_size)

    if mitigation_ratio is not None:
        mask &= (df["mitigation_ratio"] == mitigation_ratio)

    if budget is not None:
        mask &= (df["strategy_budget"] == budget)

    out = df.loc[mask].copy()
    return out

def plot_metric_by_strategy(
        df: pd.DataFrame,
        dataset: int,
        budget: int,
        metric: str = "ASPE",
        strategies=("No", "add", "remove", "update", "hybrid", "summarize"),
        aspect_no: int | None = 1,
        windows_size: int | None = None,
        mitigation_ratio: float | None = None,
        output_dir: str = ".",
        save_pdf: bool = True,
        show: bool = False,
        mark_target: int = 12,
):

    if metric not in df.columns:
        raise ValueError(f"Metric '{metric}' not found. Available: {list(df.columns)}")

    styles = [
        {'marker': 'o', 'linestyle': '-', 'color': 'blue'},
        {'marker': 's', 'linestyle': '--', 'color': 'green'},
        {'marker': '^', 'linestyle': '-.', 'color': 'red'},
        {'marker': 'D', 'linestyle': ':', 'color': 'purple'},
        {'marker': 'P', 'linestyle': '-', 'color': 'orange'},
        {'marker': 'X', 'linestyle': '--', 'color': 'black'},
    ]

    plt.figure(figsize=(10, 8))

    any_plotted = False

    for idx, strategy in enumerate(strategies):
        sub = filter_for_strategy_compare(
            df=df,
            dataset=dataset,
            strategy=strategy,
            budget=budget,
            aspect_no=aspect_no,
            windows_size=windows_size,
            mitigation_ratio=mitigation_ratio,
        )

        if sub.empty:
            print(f"[Skip] No data for dataset={dataset}, strategy={strategy}, budget={budget}, aspect_no={aspect_no}")
            continue

        sub = sub.sort_values(["round"])

        if aspect_no is None:
            sub = (
                sub.groupby("round", as_index=False)[metric]
                .mean()
                .sort_values("round")
            )

        style = styles[idx % len(styles)]
        step = max(1, len(sub) // mark_target)

        plt.plot(
            sub["round"],
            sub[metric],
            label=strategy,
            linewidth=3,
            markersize=8,
            marker=style["marker"],
            linestyle=style["linestyle"],
            color=style["color"],
            markevery=step,
        )

        any_plotted = True

    if not any_plotted:
        print("No lines plotted. Check filters (dataset/window/aspect/budget/ratio).")
        plt.close()
        return None

    plt.xlabel("Round", fontsize=16)
    plt.ylabel(metric, fontsize=16)
    plt.xticks(fontsize=14)
    plt.yticks(fontsize=14)
    plt.tick_params(axis='both', which='major', width=2, length=8)
    plt.tick_params(axis='both', which='minor', width=1, length=4)

    plt.legend(
        loc="best",
        fontsize=16,
        markerscale=1.8,
        borderpad=1.2,
        labelspacing=1.0,
        handlelength=3.0
    )

    plt.grid(True)
    plt.tight_layout()

    os.makedirs(output_dir, exist_ok=True)
    output_filename = None
    if save_pdf:
        extra = []
        if windows_size is not None:
            extra.append(f"w{windows_size}")
        if mitigation_ratio is not None:
            extra.append(f"r{mitigation_ratio}")
        extra.append(f"b{budget}")
        if aspect_no is None:
            extra.append("aspectMean")
        else:
            extra.append(f"a{aspect_no}")

        extra_txt = "_".join(extra)

        output_filename = os.path.join(
            output_dir,
            f"{metric}_ds{dataset}_strategyCompare_{extra_txt}.pdf"
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

    DATASET_ID = 7
    STRATEGY_BUDGET = 11
    METRIC_NAME = "ASPE"

    ASPECT_NO = 1
    WINDOW_SIZE = None
    MITIGATION_RATIO = None

    OUTPUT_DIR = "Figures"
    SAVE_PDF = True
    SHOW_PLOT = True

    df = load_results(CSV_PATH)

    plot_metric_by_strategy(
        df=df,
        dataset=DATASET_ID,
        budget=STRATEGY_BUDGET,
        metric=METRIC_NAME,
        aspect_no=ASPECT_NO,
        windows_size=WINDOW_SIZE,
        mitigation_ratio=MITIGATION_RATIO,
        output_dir=OUTPUT_DIR,
        save_pdf=SAVE_PDF,
        show=SHOW_PLOT
    )
