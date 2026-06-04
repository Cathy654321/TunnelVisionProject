import os
import pandas as pd
import matplotlib

matplotlib.use("TkAgg")
import matplotlib.pyplot as plt

def normalize_strategy_name(s: str) -> str:

    s = str(s).strip().lower()
    if s in {"none", "no"}:
        return "No"
    return s

def load_results(csv_path: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path)

    if "strategy" not in df.columns:
        raise ValueError("Missing required column: 'strategy'")
    df["strategy"] = df["strategy"].astype(str).str.strip()

    for col in ["dataset", "aspect_no", "round", "strategy_budget"]:
        if col not in df.columns:
            raise ValueError(f"Missing required column: '{col}'")
        df[col] = pd.to_numeric(df[col], errors="coerce")

    for col in ["ASPE", "CASE"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df["strategy"] = df["strategy"].map(normalize_strategy_name)

    return df

def filter_series_simple(
    df: pd.DataFrame,
    dataset: int,
    aspect_no: int,
    strategy: str,
    metric: str,
    budget: int | None = None,
) -> pd.DataFrame:

    if metric not in df.columns:
        raise ValueError(f"Metric '{metric}' not found. Available: {list(df.columns)}")

    strategy_norm = normalize_strategy_name(strategy)

    mask = (
            (df["dataset"] == dataset)
            & (df["aspect_no"] == aspect_no)
            & (df["strategy"] == strategy_norm)
    )

    if strategy_norm != "No" and budget is not None:
        mask &= (df["strategy_budget"] == budget)

    sub = df.loc[mask, ["round", metric]].dropna().sort_values("round")
    return sub

def plot_compare_budget_special_vs_main(
    df: pd.DataFrame,
    dataset: int,
    aspect_no: int = 1,
    metric: str = "ASPE",
    budget_main: int = 5,
    budget_special: int = 999,
    output_dir: str = "Figures",
    save_pdf: bool = True,
    show: bool = True,
    mark_target: int = 12,
    include_main_remove_summarize: bool = True,
):

    lines = [
        ("No", "No", None),
        (f"add (b={budget_main})", "add", budget_main),
        (f"update (b={budget_main})", "update", budget_main),
        (f"hybrid (b={budget_main})", "hybrid", budget_main),

        (f"remove (b={budget_special})", "remove", budget_special),
        (f"summarize (b={budget_special})", "summarize", budget_special),
    ]

    if include_main_remove_summarize:
        lines += [
            (f"remove (b={budget_main})", "remove", budget_main),
            (f"summarize (b={budget_main})", "summarize", budget_main),
        ]

    styles = [
        {"marker": "o", "linestyle": "-",  "color": "blue"},
        {"marker": "s", "linestyle": "--", "color": "green"},
        {"marker": "D", "linestyle": ":",  "color": "purple"},
        {"marker": "P", "linestyle": "-",  "color": "orange"},
        {"marker": "^", "linestyle": "-.", "color": "red"},
        {"marker": "X", "linestyle": "--", "color": "black"},
        {"marker": "v", "linestyle": "-.", "color": "brown"},
        {"marker": "*", "linestyle": ":",  "color": "teal"},
    ]

    plt.figure(figsize=(10, 8))
    any_plotted = False

    for i, (label, strategy, b) in enumerate(lines):
        style = styles[i % len(styles)]

        sub = filter_series_simple(
            df=df,
            dataset=dataset,
            aspect_no=aspect_no,
            strategy=strategy,
            metric=metric,
            budget=b,
        )

        if sub.empty:
            print(f"[Skip] No data for: dataset={dataset}, aspect_no={aspect_no}, strategy={strategy}, budget={b}")
            continue

        step = max(1, len(sub) // max(1, mark_target))

        plt.plot(
            sub["round"],
            sub[metric],
            label=label,
            linewidth=3,
            markersize=8,
            marker=style["marker"],
            linestyle=style["linestyle"],
            color=style["color"],
            markevery=step,
        )

        any_plotted = True

    if not any_plotted:
        print("No lines plotted. Check dataset/aspect_no/strategy/budget values in the CSV.")
        plt.close()
        return None

    plt.xlabel("Round", fontsize=16)
    plt.ylabel(f"Average {metric}", fontsize=16)
    plt.xticks(fontsize=14)
    plt.yticks(fontsize=14)
    plt.tick_params(axis="both", which="major", width=2, length=8)
    plt.grid(True)

    plt.legend(
        loc="best",
        fontsize=14,
        markerscale=1.5,
        borderpad=1.0,
        labelspacing=0.8,
        handlelength=3.0,
    )
    plt.tight_layout()

    os.makedirs(output_dir, exist_ok=True)
    out_path = None

    if save_pdf:
        out_path = os.path.join(
            output_dir,
            f"{metric}_ds{dataset}_compare_b{budget_special}_vs_b{budget_main}.pdf"
        )
        plt.savefig(out_path, format="pdf", bbox_inches="tight")
        print(f"Plot saved to {out_path}")

    if show:
        plt.show()
    else:
        plt.close()

    return out_path

if __name__ == "__main__":
    CSV_PATH = "consolidated_results_case.csv"

    DATASET_ID = 2
    ASPECT_NO = 1
    METRIC = "ASPE"

    BUDGET_MAIN = 5
    BUDGET_SPECIAL = 999

    OUTPUT_DIR = "Figures"
    SAVE_PDF = True
    SHOW = True

    df = load_results(CSV_PATH)

    plot_compare_budget_special_vs_main(
        df=df,
        dataset=DATASET_ID,
        metric=METRIC,
        budget_main=BUDGET_MAIN,
        budget_special=BUDGET_SPECIAL,
        output_dir=OUTPUT_DIR,
        save_pdf=SAVE_PDF,
        show=SHOW,
        include_main_remove_summarize=True,
    )
