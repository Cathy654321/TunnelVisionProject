
import os, sys

THREADS = [
    ("bbf7wd", "nz_gun_debate"),
    ("bix6la", "ppd_80_20"),
    ("bgknkt", "bayarea_nimby"),
]

TITLES = {
    "nz_gun_debate": "NZ Gun Debate",
    "ppd_80_20":     "80-20 Rule",
    "bayarea_nimby": "NIMBYism",
}
SUBREDDITS = {
    "bbf7wd": "newzealand",
    "bix6la": "PurplePillDebate",
    "bgknkt": "bayarea",
}

DATASETS = [(sid, i) for i, (sid, _) in enumerate(THREADS)]
SID2IDX = {sid: i for i, (sid, _) in enumerate(THREADS)}
ID2LABEL = {sid: lab for sid, lab in THREADS}
DS_TITLES = {i: TITLES.get(lab, lab.replace("_", " ").title()) for i, (sid, lab) in enumerate(THREADS)}
PAPER_OFFSET = 4

os.environ.setdefault("OPENAI_API_KEY", "sk-reddit-exp5-offline-placeholder")

PKG = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(PKG)
if ROOT not in sys.path:
    sys.path.append(ROOT)

DATA = os.path.join(PKG, "data")
FIG = os.path.join(PKG, "figures")
RES = os.path.join(PKG, "results")
SNAP = os.path.join(DATA, "snapshots_absa_scan")
CUTS_JSON = os.path.join(DATA, "reddit_cut_points_scan.json")

for _d in (DATA, FIG, RES, SNAP):
    os.makedirs(_d, exist_ok=True)
