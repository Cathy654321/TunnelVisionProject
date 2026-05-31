import os
import glob
import pandas as pd

def remove_files_in_folder(folder: str, pattern: str = "*.csv") -> int:

    file_paths = glob.glob(os.path.join(folder, pattern))
    deleted = 0

    for path in file_paths:
        try:
            os.remove(path)
            deleted += 1
        except FileNotFoundError:
            pass
        except PermissionError as e:
            print(f"[Skip] Permission denied: {path} ({e})")
        except OSError as e:
            print(f"[Skip] Failed to delete: {path} ({e})")

    print(f"Deleted {deleted} file(s) from '{folder}' matching '{pattern}'.")
    return deleted

def consolidate_csv_folder(
        results_folder: str,
        output_file: str,
        pattern: str = "*.csv",
        add_source_file_col: bool = True,
        strict_columns: bool = True,
) -> str | None:

    csv_files = sorted(glob.glob(os.path.join(results_folder, pattern)))
    if not csv_files:
        print(f"No CSV files found in folder: {results_folder}")
        return None

    consolidated = []
    expected_cols = None

    for file_path in csv_files:
        df = pd.read_csv(file_path)

        if strict_columns:
            if expected_cols is None:
                expected_cols = list(df.columns)
            elif list(df.columns) != expected_cols:
                raise ValueError(
                    f"Column mismatch in {os.path.basename(file_path)}.\n"
                    f"Expected: {expected_cols}\n"
                    f"Found:    {list(df.columns)}"
                )

        if add_source_file_col:
            df.insert(0, "source_file", os.path.basename(file_path))

        consolidated.append(df)

    final_df = pd.concat(consolidated, ignore_index=True)
    final_df.to_csv(output_file, index=False)
    print(f"Consolidated file saved as: {output_file}")

    return output_file

def average_csv_folder_linewise(
        folder: str,
        output_file: str,
        pattern: str = "*.csv",
        avg_columns: list[str] | None = None,
        strict_columns: bool = True,
        strict_rows: bool = True,
        strict_non_avg_values: bool = False,
) -> str | None:

    if avg_columns is None:
        avg_columns = ["ASPE", "AspectCoverage (C)", "SentimentCoverage (Cs)", "CASE"]

    csv_files = sorted(glob.glob(os.path.join(folder, pattern)))
    csv_files = [f for f in csv_files if os.path.isfile(f)]

    if not csv_files:
        print(f"No CSV files found in folder: {folder}")
        return None

    dfs: list[pd.DataFrame] = []
    expected_cols: list[str] | None = None
    expected_len: int | None = None

    for file_path in csv_files:
        df = pd.read_csv(file_path)

        if strict_columns:
            if expected_cols is None:
                expected_cols = list(df.columns)
            elif list(df.columns) != expected_cols:
                raise ValueError(
                    f"Column mismatch in {os.path.basename(file_path)}.\n"
                    f"Expected: {expected_cols}\n"
                    f"Found:    {list(df.columns)}"
                )

        if strict_rows:
            if expected_len is None:
                expected_len = len(df)
            elif len(df) != expected_len:
                raise ValueError(
                    f"Row count mismatch in {os.path.basename(file_path)}.\n"
                    f"Expected rows: {expected_len}\n"
                    f"Found rows:    {len(df)}"
                )

        dfs.append(df)

    template = dfs[0].copy()
    for col in avg_columns:
        if col not in template.columns:
            raise KeyError(
                f"Required column '{col}' not found. Available columns: {list(template.columns)}"
            )

    if strict_non_avg_values:
        non_avg_cols = [c for c in template.columns if c not in avg_columns]
        for i, df in enumerate(dfs[1:], start=2):
            for c in non_avg_cols:
                if not template[c].equals(df[c]):
                    raise ValueError(
                        f"Non-averaged column '{c}' differs between file 1 and file {i} "
                        f"({os.path.basename(csv_files[i - 1])})."
                    )

    for col in avg_columns:
        stacked = pd.concat([df[col] for df in dfs], axis=1)

        stacked = stacked.apply(pd.to_numeric, errors="coerce")

        if stacked.isna().any().any():
            bad_rows = stacked.isna().any(axis=1).sum()
            raise ValueError(
                f"Column '{col}' has non-numeric or missing values in at least {bad_rows} row(s) "
                f"across the input files. Please clean data or adjust parsing."
            )

        template[col] = stacked.mean(axis=1).round(4)

    template.to_csv(output_file, index=False)
    print(f"Averaged file saved as: {output_file}")
    return output_file

def consolidate_each_subfolder_to_temp(
    temp_folder: str = "./temp",
    pattern: str = "*.csv",
    add_source_file_col: bool = True,
    strict_columns: bool = True,
    overwrite: bool = True,
) -> list[str]:

    if not os.path.isdir(temp_folder):
        raise ValueError(f"temp_folder does not exist or is not a directory: {temp_folder}")

    outputs: list[str] = []

    subfolders = sorted(
        [
            os.path.join(temp_folder, name)
            for name in os.listdir(temp_folder)
            if os.path.isdir(os.path.join(temp_folder, name))
        ]
    )

    if not subfolders:
        print(f"No subfolders found under: {temp_folder}")
        return outputs

    for sub in subfolders:
        sub_name = os.path.basename(sub.rstrip("/\\"))
        out_path = os.path.join(temp_folder, f"{sub_name}_consolidated.csv")

        if (not overwrite) and os.path.exists(out_path):
            print(f"[Skip] Exists (overwrite=False): {out_path}")
            outputs.append(out_path)
            continue

        saved = consolidate_csv_folder(
            results_folder=sub,
            output_file=out_path,
            pattern=pattern,
            add_source_file_col=add_source_file_col,
            strict_columns=strict_columns,
        )

        if saved is None:
            print(f"[Skip] No CSVs in subfolder: {sub}")
            continue

        outputs.append(saved)

    print(f"Created {len(outputs)} consolidated file(s) under '{temp_folder}'.")
    return outputs

