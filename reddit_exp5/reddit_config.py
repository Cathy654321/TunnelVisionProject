THREADS = [
    ("bf35w1", "fortnite_fov"),
    ("bi9svs", "climate_top100"),
    ("behozy", "healthcare_debate"),
]

TITLES = {
    "fortnite_fov":      "Fortnite FOV",
    "climate_top100":    "Climate Top-100",
    "healthcare_debate": "Healthcare Debate",
}
SUBREDDITS = {
    "bf35w1": "FortniteCompetitive",
    "bi9svs": "environment",
    "behozy": "me_irl",
}

DATASETS = [(sid, i) for i, (sid, _) in enumerate(THREADS)]
SID2IDX = {sid: i for i, (sid, _) in enumerate(THREADS)}
ID2LABEL = {sid: lab for sid, lab in THREADS}
DS_TITLES = {i: TITLES.get(lab, lab.replace("_", " ").title()) for i, (sid, lab) in enumerate(THREADS)}

PAPER_OFFSET = 4

import os, sys

os.environ.setdefault("OPENAI_API_KEY", "sk-reddit-exp5-offline-placeholder")

PKG = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(PKG)
if ROOT not in sys.path:
    sys.path.append(ROOT)

DATA = os.path.join(PKG, "data")
RAW = os.path.join(DATA, "reddit_raw")
SNAP = os.path.join(DATA, "snapshots")
FIG = os.path.join(PKG, "figures")
RES = os.path.join(PKG, "results")
RES_CASE = os.path.join(RES, "case")
RES_LATE = os.path.join(RES, "late")
CONSOLIDATED = os.path.join(RES, "consolidated_results_case_reddit.csv")
EVENT_CSV = os.path.join(DATA, "Event_reddit.csv")
PROFILE_CSV = os.path.join(DATA, "Profile_reddit.csv")
STATS_JSON = os.path.join(DATA, "reddit_dataset_stats.json")
CUTS_JSON = os.path.join(DATA, "reddit_cut_points.json")
CURVES_CSV = os.path.join(RES, "reddit_tv_curves.csv")
AVG_CSV = os.path.join(RES, "reddit_avg_aspe_case_by_strategy_budget.csv")
TABLE_TEX = os.path.join(PKG, "reddit_results_table.tex")

for _d in (DATA, RAW, SNAP, FIG, RES, RES_CASE, RES_LATE):
    os.makedirs(_d, exist_ok=True)
