import pandas as pd

def load_results(csv_path: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path)

    required = {"dataset", "aspect_no", "strategy", "strategy_budget", "ASPE", "CASE"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    df["strategy"] = df["strategy"].astype(str).str.strip()

    for col in ["dataset", "aspect_no", "strategy_budget", "ASPE", "CASE"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df["ASPE"] = df["ASPE"].round(4)
    df["CASE"] = df["CASE"].round(4)

    return df

def compute_avg_aspe_case_table(
        df: pd.DataFrame,
        datasets: list[int],
        strategies: tuple[str, ...] = ("No", "add", "remove", "update", "hybrid", "summarize"),
        budgets: list[int] | None = None,
        aspect_no: int = 1,
        special_strategies: tuple[str, ...] = ("remove", "summarize"),
        budget_main: int | None = None,
        budget_special: int | None = None,
) -> pd.DataFrame:

    if budgets is None:
        budgets = list(range(0, 11))
    budgets = list(budgets)

    compute_all_budgets = (budget_main is None and budget_special is None)

    base_df = df[df["dataset"].isin(datasets) & (df["aspect_no"] == aspect_no)].copy()

    base_df = base_df.dropna(subset=["dataset", "aspect_no", "strategy", "ASPE", "CASE"])

    def is_no_label(x: str) -> bool:
        return str(x).strip().lower() in {"no", "none"}

    base_df["_strategy_cmp"] = base_df["strategy"].astype(str).str.strip()
    base_df["_strategy_cmp_lower"] = base_df["_strategy_cmp"].str.lower()

    rows = []

    for ds in datasets:
        ds_df = base_df[base_df["dataset"] == ds]

        for strategy in strategies:
            strategy_str = str(strategy).strip()
            strategy_lower = strategy_str.lower()

            if is_no_label(strategy_str):
                sub = ds_df[ds_df["_strategy_cmp_lower"].isin({"no", "none"})]
                avg_aspe = sub["ASPE"].mean()
                avg_case = sub["CASE"].mean()

                for b in budgets:
                    rows.append(
                        {
                            "dataset": ds,
                            "strategy": "No",
                            "budget": b,
                            "avg_ASPE": round(avg_aspe, 4) if pd.notna(avg_aspe) else float("nan"),
                            "avg_CASE": round(avg_case, 4) if pd.notna(avg_case) else float("nan"),
                        }
                    )
                continue

            if compute_all_budgets:

                for b in budgets:
                    sub = ds_df[
                        (ds_df["_strategy_cmp"] == strategy_str)
                        & (ds_df["strategy_budget"] == b)
                        ]
                    avg_aspe = sub["ASPE"].mean()
                    avg_case = sub["CASE"].mean()

                    rows.append(
                        {
                            "dataset": ds,
                            "strategy": strategy_str,
                            "budget": b,
                            "avg_ASPE": round(avg_aspe, 4) if pd.notna(avg_aspe) else float("nan"),
                            "avg_CASE": round(avg_case, 4) if pd.notna(avg_case) else float("nan"),
                        }
                    )
            else:

                chosen_budget = budget_special if strategy_lower in {s.lower() for s in
                                                                     special_strategies} else budget_main

                sub = ds_df[
                    (ds_df["_strategy_cmp"] == strategy_str)
                    & (ds_df["strategy_budget"] == chosen_budget)
                    ]
                avg_aspe = sub["ASPE"].mean()
                avg_case = sub["CASE"].mean()

                for b in budgets:
                    rows.append(
                        {
                            "dataset": ds,
                            "strategy": strategy_str,
                            "budget": b,
                            "avg_ASPE": round(avg_aspe, 4) if pd.notna(avg_aspe) else float("nan"),
                            "avg_CASE": round(avg_case, 4) if pd.notna(avg_case) else float("nan"),
                        }
                    )

    out = pd.DataFrame(rows)

    if "_strategy_cmp" in out.columns:
        out = out.drop(columns=["_strategy_cmp"], errors="ignore")
    if "_strategy_cmp_lower" in out.columns:
        out = out.drop(columns=["_strategy_cmp_lower"], errors="ignore")

    return out

if __name__ == "__main__":
    INPUT_CSV = "consolidated_results_case.csv"
    OUTPUT_CSV = "avg_aspe_case_by_dataset_strategy_budget.csv"

    DATASETS = [2, 6, 7]
    STRATEGIES = ("No", "add", "remove", "update", "hybrid", "summarize")
    BUDGETS = [1, 3, 5, 7, 9, 11, 13, 15]
    ASPECT_NO = 1

    df = load_results(INPUT_CSV)

    table_df = compute_avg_aspe_case_table(
        df=df,
        datasets=DATASETS,
        strategies=STRATEGIES,
        budgets=BUDGETS,
        aspect_no=ASPECT_NO,
        budget_main=None,
        budget_special=None,
    )

    table_df.to_csv(OUTPUT_CSV, index=False)
    print(f"Saved table to: {OUTPUT_CSV}")
