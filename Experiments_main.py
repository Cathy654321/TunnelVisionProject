import os
import itertools
import pandas as pd

import utils_common
from SNTPlatform import SNTPlatform
from analysis_analyzer import Analyzer
from utils_consolidate_csvs import consolidate_csv_folder
from utils_consolidate_csvs import remove_files_in_folder

def iter_grid(grid: dict):
    keys = list(grid.keys())
    for values in itertools.product(*(grid[k] for k in keys)):
        yield dict(zip(keys, values))

def resolve_start_point(event_index: int, mapping: dict[int, int], default: int) -> int:

    return int(mapping.get(int(event_index), default))

def resolve_results_paths(dynamic: bool, static_folder: str, static_file: str):

    if not dynamic:
        os.makedirs(static_folder, exist_ok=True)
        return static_folder, static_file

    ts = utils_common.get_time_stamp()
    dynamic_folder = f"{static_folder}_{ts}"
    os.makedirs(dynamic_folder, exist_ok=True)
    dynamic_file = f"consolidated_results_case_{ts}.csv"
    return dynamic_folder, dynamic_file

def run_one_experiment(
        network,
        event_index: int,
        number_of_iteration: int,
        save_snapshot: bool,
        each_user_comment_aspect_count: int,
        user_vision_window_size: int,
        strategy: str,
        strategy_budget: int,
        mitigation_ratio: float,
        start_from_range: range,
        base_window: int = 300,
        results_dir: str = "./results_case",
):
    os.makedirs(results_dir, exist_ok=True)

    network.load_snapshot(network.SNAPSHOT_ALL)

    network.deploy_strategy({
        "strategy_mitigation": strategy,
        "strategy_budget": int(strategy_budget),
        "mitigation_ratio": float(mitigation_ratio),
    })

    network.simulate_comments(
        event_index=event_index,
        k=number_of_iteration,
        is_save=save_snapshot,
        max_aspects=each_user_comment_aspect_count,
        window_size=user_vision_window_size,
    )

    analyser = Analyzer(event=network.events[event_index])
    results = []

    start_step = getattr(start_from_range, "step", 100)
    window_length = base_window
    start_from_fixed = start_from_range.start

    for round_idx in range(1, len(start_from_range) + 1):
        end_at = start_from_fixed + window_length + start_step * (round_idx - 1)

        result = analyser.calculate_aspe_case(
            start_from=start_from_fixed,
            window_length=None,
            end_at=end_at
        )

        result.update({
            "round": round_idx,
            "dataset": event_index,
            "start_from": start_from_fixed,
            "window_length": window_length,
            "aspect_no": each_user_comment_aspect_count,
            "user_window_size": user_vision_window_size,
            "strategy": strategy,
            "strategy_budget": strategy_budget,
            "mitigation_ratio": mitigation_ratio,
        })
        results.append(result)

    out_name = (
        f"ds{event_index}_a{each_user_comment_aspect_count}_w{user_vision_window_size}_"
        f"s{strategy}_b{strategy_budget}_r{mitigation_ratio}_base{base_window}.csv"
    )
    out_path = os.path.join(results_dir, out_name)
    pd.DataFrame(results).to_csv(out_path, index=False)

    print(f"Saved: {out_path}")
    return out_path

def run_experiment_grid(network, grid: dict, common: dict, results_dir: str):
    outputs = []
    for cfg in iter_grid(grid):
        out_path = run_one_experiment(
            network=network,
            event_index=cfg["event_index"],
            number_of_iteration=common["number_of_iteration"],
            save_snapshot=common["save_snapshot"],
            each_user_comment_aspect_count=cfg["each_user_comment_aspect_count"],
            user_vision_window_size=common["user_vision_window_size"],
            strategy=cfg["strategy"],
            strategy_budget=cfg["strategy_budget"],
            mitigation_ratio=common["mitigation_ratio"],
            start_from_range=common["start_from_range_fn"](cfg["event_index"]),
            base_window=common["base_window"],
            results_dir=results_dir,
        )
        outputs.append(out_path)
    return outputs

def network_analysis(dynamic: bool = False):

    STATIC_RESULTS_DIR = "./results_case"
    STATIC_CONSOLIDATED = "consolidated_results_case.csv"

    results_dir, consolidated_file = resolve_results_paths(
        dynamic=dynamic,
        static_folder=STATIC_RESULTS_DIR,
        static_file=STATIC_CONSOLIDATED
    )

    network = SNTPlatform()
    network.load_events(event_data="./datasets/Event_standard.csv")
    network.load_users(profile_data="./datasets/Profile_students.csv")

    start_point_by_ds = {2: 900, 6: 900, 7: 800}
    default_start_point = 900

    def make_start_from_range(event_index: int) -> range:
        start_point = resolve_start_point(event_index, start_point_by_ds, default_start_point)
        end_point = start_point + 100 * 50
        return range(start_point, end_point, 50)

    common = {
        "number_of_iteration": 100,
        "save_snapshot": False,
        "user_vision_window_size": 30,
        "mitigation_ratio": 1.0,
        "base_window": 100,
        "start_from_range_fn": make_start_from_range,
    }

    grid = {
        "event_index": [2, 6, 7],
        "each_user_comment_aspect_count": [1],
        "strategy": ["remove", "summarize"],
        "strategy_budget": [1, 3, 5, 7, 9, 11, 13, 15],
    }

    run_experiment_grid(network, grid=grid, common=common, results_dir=results_dir)

    consolidate_csv_folder(
        results_folder=results_dir,
        output_file=consolidated_file,
        strict_columns=True
    )

    print(f"\n[Done]\nResults folder: {results_dir}\nConsolidated file: {consolidated_file}\n")
    return results_dir, consolidated_file

if __name__ == "__main__":

    network_analysis(dynamic=False)

