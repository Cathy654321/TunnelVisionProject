# Tunnel Vision in Online Social Networks

Reference implementation of the paper *Tunnel Vision in Online Social Networks: Entropy Metrics and Exposure Interventions at the Aspect-Sentiment Level*.

## Overview

Online social networks often exhibit a progressive narrowing of collective attention, where discussion concentrates on a small subset of an event's aspects (and a single sentiment per aspect) while alternative perspectives are increasingly overlooked. We refer to this phenomenon as **tunnel vision**. Unlike echo chambers, filter bubbles, or system-level polarization, tunnel vision is event-centred and manifests at the **aspect-sentiment level**, reflecting a loss of topical and evaluative diversity within a single discussion rather than a clustering of opinions.

This project provides a computational framework that:

1. Formally characterizes tunnel vision as a distribution-concentration problem over aspect-sentiment pairs.
2. Quantifies it using two coverage-aware entropy metrics:
   - **ASPE**: Aspect-Sentiment Pairwise Entropy (within-support balance).
   - **CASE**: Coverage-Adjusted Aspect-Sentiment Entropy (balance plus aspect and sentiment coverage).
3. Implements an Agent-based Multifaceted Engagement Model (MEM) in which LLM-generated discussion traces seed a Bayesian behavior model, and budget-constrained interventions reshape each user's reading window.
4. Evaluates **five budget-constrained mitigation strategies** (`add`, `remove`, `update`, `hybrid`, `summarize`) against a `No`-intervention baseline.

The repository releases all source code, the LLM-generated snapshot used in the paper, profile/event configurations, the consolidated results CSV, and the scripts that produce every reported figure and table. This is intended to support **reproducibility** and to let other researchers **learn from, extend, and reuse** the framework. It also includes a real-data validation module, `reddit_exp5/`, which reproduces the framework's findings on real Reddit discussions (**Experiment 5**; see the dedicated section below).

## Project Pipeline

### 1. Snapshots (LLM-Driven Discussion Generation)

Initial discussion traces are produced via **LLM-driven simulation** over a fixed set of events.

- An OpenAI API key is required only for this step.
- Rename `MY.env` to `.env` and set your OpenAI (ChatGPT) API key inside it.
- Generated snapshots are written to `snapshots/`.
- `datasets/Event_standard.csv` contains **9 event topics**. Following the paper, the three datasets used in the reported experiments correspond to event IDs **2, 6, and 7** (Healthcare Reform, Volcanic Eruption, and Social Media / Adolescent Mental Health).
- A bundled snapshot, `snapshots/snapshot_all_2025_april_llm.pkl`, is provided so that the LLM stage can be skipped when reproducing the paper figures.

The high-level entry point for snapshot generation is `service_network.network_generations(...)`, which internally calls `SNTPlatform.generate_comments(event_index=..., is_save=True, k=20)`.

### 2. Simulations (User Behaviour Modelling)

Behavioural simulation runs on top of a loaded snapshot.

- The simulation is governed by **Bayesian updating** over aspect-sentiment choices for each of the **100 simulated users**, with a fixed perceptual **window of the most recent 30 comments**.
- The simulation is computationally efficient and does not call any LLM API.
- Saving simulation outputs is optional; when enabled they are written to `simulations/`.

### 3. Algorithms (Tunnel Vision Mitigation)

The mitigation algorithms are implemented in `algorithm_collections.py`. Each strategy operates as a post-processing transformation on the user's reading window without modifying user history:

- `add`: append synthetic hints that introduce previously unused aspect-sentiment pairs.
- `remove`: hide existing comments that reinforce dominant pairs.
- `update`: replace existing comments with synthetic hints carrying unused pairs.
- `hybrid`: at each step pick the single best operation over the pooled `add`/`remove`/`update` candidate set.
- `summarize`: append one synthetic summary comment that aggregates aspect-sentiment pairs not yet exposed in the current window.

`add`, `remove`, `update`, and `hybrid` share a unified **greedy** template that picks the one-step modification with the largest positive CASE gain at each step until the budget is exhausted; `summarize` is deterministic and does not rely on marginal-gain evaluation. Strategies are selected per-user by setting the corresponding **algorithm flag** via `SNTPlatform.deploy_strategy({...})`.

### 4. Experiments

The core experimental driver is `Experiments_main.py`.

- Per-run results are written to `./results_case/` as one CSV per `(dataset, aspect_count, strategy, budget, ...)` configuration.
- After all runs finish, `utils_consolidate_csvs.consolidate_csv_folder(...)` (invoked at the end of `Experiments_main.py`) merges the per-run CSVs into `consolidated_results_case.csv`, which is what the figure and table scripts read.
- The `grid` dict near the bottom of `Experiments_main.py` controls which `(strategy, strategy_budget)` combinations are run. The default grid covers `remove` and `summarize` over budgets `{1,3,5,7,9,11,13,15}`; edit the grid to include `add`, `update`, `hybrid` (and additional budgets) to regenerate every cell in Table 2 of the paper.

### 5. Visualisations and Tables

All figures and tables in the paper are produced from `consolidated_results_case.csv`:

- `Experiment_1.py`: tunnel vision formation under no intervention (varying aspects per comment).
- `Experiment_2.py`: per-round ASPE under different mitigation strategies at fixed budgets.
- `Experiment_3.py`: average ASPE/CASE vs. budget across strategies.
- `Experiment_3_table.py`: produces the strategy/budget/dataset table (`avg_aspe_case_by_dataset_strategy_budget.csv`) underlying Table 2.
- `Experiment_4.py`: limiting behaviour under user isolation (`remove`, `b=999`) and maximum summarization (`summarize`, `b=999`).

Each script writes its PDFs to `Figures/` by default; the dataset, strategy, and budget selected for each figure are configured in the `if __name__ == "__main__":` block at the bottom of the file.

## Code Structure

### Core Entities / Models

- `Event.py`
- `SNTUser.py`
- `Comment.py`
- `SNTPlatform.py`

**Important:** Do not rename or merge these files. The bundled `.pkl` snapshots are pickled with these exact module/class names and will fail to load if they are renamed.

### Network Service

- `service_network.py`: build, load, simulate, and inspect snapshots and simulations.

### Analysis

- `analysis_analyzer.py`: computes ASPE and CASE from a (sub-)window of comments.
- `analysis_vis_results.py`: shared plotting helpers used during exploration.

### Utility Modules

- `utils_common.py`: CSV I/O, profile-to-text conversion, timestamps, randomness helpers.
- `utils_consolidate_csvs.py`: per-run CSV consolidation and (optional) line-wise averaging.
- `utils_data_manager.py`: dataset helpers.
- `utils_llm_manager.py`: OpenAI API wrapper used during snapshot generation.
- `utils_sentiment_analysis.py`: VADER-based sentiment scoring.

## Environment and Setup

- **Python:** 3.13
- **Dependencies:** `requirements.txt` (contractions, matplotlib, numpy, openai, pandas, pydantic, python-dotenv, requests, scikit-learn, scipy, tqdm, vaderSentiment). The last three (`scikit-learn`, `scipy`, `contractions`) are used by the Experiment 5 module.

## Installation

Linux / macOS:

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Windows (PowerShell):

```powershell
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Windows (cmd):

```cmd
python -m venv venv
venv\Scripts\activate.bat
pip install -r requirements.txt
```

## Reproducing the Paper Figures

The bundled snapshot and `consolidated_results_case.csv` are sufficient to regenerate all reported figures and tables without an API key:

```bash
# 1. Run all experiments (uses the bundled snapshot; no API call).
#    Edit the `grid` dict in Experiments_main.py to cover every
#    strategy/budget combination you want to reproduce.
python Experiments_main.py

# 2. Consolidate per-run CSVs into a single results file.
#    (Step 2 is invoked automatically at the end of step 1; run it
#    explicitly only if you regenerate the per-run CSVs manually.)
python utils_consolidate_csvs.py

# 3. Render each figure and the strategy/budget table.
python Experiment_1.py
python Experiment_2.py
python Experiment_3.py
python Experiment_3_table.py
python Experiment_4.py
```

Snapshot regeneration (step 1 of the project pipeline above) is only required if you want to re-run the LLM-based discussion generation from scratch, and does need an OpenAI API key configured in `.env`.

## Reproducibility

- The bundled snapshot, event/profile datasets, source code, and `consolidated_results_case.csv` are all included in this repository.
- Every figure and table in the paper can be reproduced directly from the bundled artifacts without invoking the OpenAI API.
- Snapshot regeneration (LLM-driven discussion generation) is the only stage that requires an OpenAI API key.

## Experiment 5: Real-World Validation on Reddit (`reddit_exp5/`)

`reddit_exp5/` is a self-contained, decoupled module that validates the framework on three real, medium-sized Reddit discussion threads (Pushshift, April 2019). It corresponds to *Experiment 5: Validation on Real-World Reddit Discussions* in the paper. Its Python sources are kept **comment-free** (release build).

The module is decoupled from the rest of the project: it keeps its own `data/`, `figures/`, and `results/`, and reuses the core framework classes (`Event`, `Comment`, `SNTUser`, `SNTPlatform`, `analysis_analyzer.Analyzer`, `utils_consolidate_csvs`) by adding the project root to `sys.path` at import time. The dependency is one-way: the rest of the project imports nothing from it, so it does not affect Experiments 1 to 4.

### Datasets

These threads were selected from a reservoir-sampled scan of the dump (medium, focused threads of roughly 150 to 700 comments) and then validated for robustness: each shows clean aspect-level tunnel vision under NMF-topic aspects with comment-level VADER for every tested topic count K in {10, 12, 14} (sliding window W = 30).

| Paper DS | id | Subreddit | Topic | rho_ASPE | rho_conc | Cmts |
|---|---|---|---|---|---|---|
| 4 | `bf35w1` | r/FortniteCompetitive | FOV-slider feature debate | -0.66 | +0.68 | 180 |
| 5 | `bi9svs` | r/environment | "Top 100 companies killing the planet" (climate) | -0.64 | +0.63 | 366 |
| 6 | `behozy` | r/me_irl | US vs. other countries healthcare debate | -0.66 | +0.51 | 217 |

The dataset set lives in `reddit_exp5/reddit_config.py` (`THREADS`, `TITLES`, `SUBREDDITS`); every script reads from there. The datasets are independent: each has its own raw JSON, snapshot, cut point, and per-dataset results.

### Running Experiment 5

From the project root:

```bash
# 1. build Event/Comment/SNTUser snapshots with NMF-topic aspects   (deterministic)
python reddit_exp5/reddit_to_events.py

# 2. ASPE/CASE narrowing figures + cut points                        (deterministic)
python reddit_exp5/analysis_reddit_tv.py

# 3. seeded Bayesian experiments (one process per dataset, parallelisable)
python reddit_exp5/Experiments_reddit_main.py --sid bf35w1
python reddit_exp5/Experiments_reddit_main.py --sid bi9svs
python reddit_exp5/Experiments_reddit_main.py --sid behozy
python reddit_exp5/Experiments_reddit_main.py --consolidate

# 4. early-vs-late intervention (per dataset)
python reddit_exp5/Experiments_reddit_late.py --sid bf35w1   # plus bi9svs, behozy

# 5. figures + tables
python reddit_exp5/reddit_make_figures.py

# 0. (optional, needs the dumps + zstd) re-extract the raw threads
python reddit_exp5/extract_reddit_datasets.py
```

Steps 3 and 4 use stochastic Bayesian simulation; the shipped `reddit_exp5/results/` reproduce the exact numbers reported in the paper. Steps 1, 2, and 5 are deterministic (NMF `random_state=0`, VADER, fixed cut logic) and regenerate identical artifacts. Aspects are NMF latent topics labelled by their top terms; sentiment is comment-level VADER. `extract_reddit_datasets.py` reads absolute dump and `zstd.exe` paths at its top; adjust those if the dumps move. Everything else is module-relative.

## Citation

If you use this code or data, please cite the accompanying paper:

> Wang, X., Liu, Y., Wu, S., Xia, J., Li, W., & Bai, Q. *Tunnel Vision in Online Social Networks: Entropy Metrics and Exposure Interventions at the Aspect-Sentiment Level.* (to appear).
