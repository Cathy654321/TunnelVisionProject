import os
import pandas as pd
import matplotlib

matplotlib.use("TkAgg")
import matplotlib.pyplot as plt

def load_results(csv_path: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path)

    if "strategy" in df.columns:
        df["strategy"] = df["strategy"].astype(str).str.strip()
        df["strategy"] = df["strategy"].replace({"none": "None", "NONE": "None"})

    for col in ["dataset", "aspect_no", "round", "windows_size", "strategy_budget"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    for col in ["mitigation_ratio", "ASPE", "CASE"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df

def filter_data(
        df: pd.DataFrame,
        dataset: int,
        strategy: str,
        aspect_nos=(1, 2, 3),
        windows_size: int | None = None,
        strategy_budget: int | None = None,
        mitigation_ratio: float | None = None,
) -> pd.DataFrame:

    strategy = str(strategy).strip()
    if strategy.lower() == "no":
        strategy = "No"

    mask = (df["dataset"] == dataset) & (df["strategy"] == strategy) & (df["aspect_no"].isin(aspect_nos))

    if windows_size is not None:
        mask &= (df["windows_size"] == windows_size)
    if strategy_budget is not None:
        mask &= (df["strategy_budget"] == strategy_budget)
    if mitigation_ratio is not None:
        mask &= (df["mitigation_ratio"] == mitigation_ratio)

    out = df.loc[mask].copy()
    return out

def plot_metric_by_aspect(
        df: pd.DataFrame,
        dataset: int,
        strategy: str,
        metric: str = "ASPE",
        aspect_nos=(1, 2, 3),
        windows_size: int | None = None,
        strategy_budget: int | None = None,
        mitigation_ratio: float | None = None,
        output_dir: str = ".",
        save_pdf: bool = True,
        show: bool = False,
):

    if metric not in df.columns:
        raise ValueError(f"Metric '{metric}' not found. Available: {list(df.columns)}")

    sub = filter_data(
        df=df,
        dataset=dataset,
        strategy=strategy,
        aspect_nos=aspect_nos,
        windows_size=windows_size,
        strategy_budget=strategy_budget,
        mitigation_ratio=mitigation_ratio,
    )

    if sub.empty:
        print("No rows matched the filter. Try loosening filters or check dataset/strategy.")
        return None

    sub = sub.sort_values(["aspect_no", "round"])

    styles = [
        {'marker': 'o', 'linestyle': '-', 'color': 'blue'},
        {'marker': 's', 'linestyle': '--', 'color': 'green'},
        {'marker': '^', 'linestyle': '-.', 'color': 'red'},
        {'marker': 'D', 'linestyle': ':', 'color': 'purple'},
        {'marker': 'P', 'linestyle': '-', 'color': 'orange'},
    ]

    plt.figure(figsize=(10, 8))

    unique_aspects = [a for a in aspect_nos if a in set(sub["aspect_no"].dropna().unique())]
    for idx, a in enumerate(unique_aspects):
        group = sub[sub["aspect_no"] == a]
        style = styles[idx % len(styles)]

        plt.plot(
            group["round"],
            group[metric],
            label=f"{int(a)} aspect(s)",
            linewidth=3,
            markersize=8,
            marker=style["marker"],
            linestyle=style["linestyle"],
            color=style["color"],
            markevery=5
        )

    plt.xlabel("Round",fontsize=16)
    plt.ylabel(metric,fontsize=16)
    plt.xticks(fontsize=14)
    plt.yticks(fontsize=14)
    plt.tick_params(axis='both', which='major', width=2, length=8)
    plt.tick_params(axis='both', which='minor', width=1, length=4)

    plt.legend(

        loc="best",
        fontsize=16,
        title_fontsize=18,
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

        strategy_clean = str(strategy).replace(" ", "")
        extra = []
        if windows_size is not None:
            extra.append(f"w{windows_size}")
        if strategy_budget is not None:
            extra.append(f"b{strategy_budget}")
        if mitigation_ratio is not None:
            extra.append(f"r{mitigation_ratio}")
        extra_txt = "_" + "_".join(extra) if extra else ""

        output_filename = os.path.join(
            output_dir,
            f"{metric}_ds{dataset}_strategy{strategy_clean}{extra_txt}.pdf"
        )
        plt.savefig(output_filename, format="pdf")
        print(f"Plot saved to {output_filename}")

    if show:
        plt.show()
    else:
        plt.close()

    return output_filename

if __name__ == "__main__":

    CSV_PATH = "consolidated_results_case.csv"
    DATASET = 2
    METRIC = "ASPE"
    STRATEGY = "No"
    STRATEGY_BUDGET = 0
    MITIGATION_RATIO = None

    WINDOWS_SIZE = None

    OUTPUT_DIRECTORY = "Figures"
    SAVE_PDF = True
    SHOW = True

    df = load_results(CSV_PATH)

    plot_metric_by_aspect(
        df=df,
        dataset=DATASET,
        strategy=STRATEGY,
        metric=METRIC,
        aspect_nos=(1, 2, 3),
        windows_size=WINDOWS_SIZE,
        strategy_budget=STRATEGY_BUDGET,
        mitigation_ratio=MITIGATION_RATIO,
        output_dir=OUTPUT_DIRECTORY,
        save_pdf=SAVE_PDF,
        show=SHOW
    )
