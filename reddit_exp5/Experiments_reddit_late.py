import os, sys, json, argparse
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from reddit_config import DS_TITLES, RES_LATE as RES, FIG, CUTS_JSON as CUTS
from SNTPlatform import SNTPlatform
from Experiments_reddit_main import (load_fresh, seed_to_cut, analyse, WINDOW_SIZE,
                                     MITIGATION_RATIO, SID2IDX)

os.makedirs(RES, exist_ok=True); os.makedirs(FIG, exist_ok=True)

WARMUP = 6
POST = 8
TOTAL = WARMUP + POST

SCENARIOS = [
    ("No",              "No",     0,  0),
    ("early update b11", "update", 11, 0),
    ("late update b11",  "update", 11, WARMUP),
    ("late update b3",   "update", 3,  WARMUP),
]
STYLES = [{"c": "black", "ls": "-", "m": "o"}, {"c": "blue", "ls": "-", "m": "s"},
          {"c": "red", "ls": "--", "m": "^"}, {"c": "orange", "ls": ":", "m": "D"}]

def run_scenario(sid, strategy, budget, warmup):
    users, events = load_fresh(sid)
    with open(CUTS) as f:
        cut = int(json.load(f)[sid]["cut_index"])
    active = seed_to_cut(users, events, cut)
    seed_len = len(events[0].comments)
    net = SNTPlatform(); net.users = active; net.events = events
    if warmup > 0:
        net.deploy_strategy({"strategy_mitigation": "No", "strategy_budget": 0, "mitigation_ratio": MITIGATION_RATIO})
        net.simulate_comments(event_index=0, k=warmup, window_size=WINDOW_SIZE, max_aspects=1)
        net.deploy_strategy({"strategy_mitigation": strategy, "strategy_budget": int(budget), "mitigation_ratio": MITIGATION_RATIO})
        net.simulate_comments(event_index=0, k=POST, window_size=WINDOW_SIZE, max_aspects=1)
    else:
        net.deploy_strategy({"strategy_mitigation": strategy, "strategy_budget": int(budget), "mitigation_ratio": MITIGATION_RATIO})
        net.simulate_comments(event_index=0, k=TOTAL, window_size=WINDOW_SIZE, max_aspects=1)
    return analyse(events[0], seed_len)

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--sid", required=True); args = ap.parse_args()
    sid = args.sid; ds = SID2IDX[sid]
    series = {}
    for label, strat, b, warm in SCENARIOS:
        rows = run_scenario(sid, strat, b, warm)
        series[label] = [(r["round"], r["ASPE"]) for r in rows]
        print(f"[{sid}] {label}: {len(rows)} rounds, ASPE {rows[0]['ASPE']:.2f}->{rows[-1]['ASPE']:.2f}", flush=True)

    plt.figure(figsize=(8, 6))
    for i, (label, *_ ) in enumerate(SCENARIOS):
        xs = [x for x, _ in series[label]]; ys = [y for _, y in series[label]]
        s = STYLES[i]
        plt.plot(xs, ys, label=label, color=s["c"], linestyle=s["ls"], marker=s["m"],
                 linewidth=2.8, markersize=6, markevery=3)
    plt.xlabel("Round", fontsize=15); plt.ylabel("ASPE", fontsize=15)
    plt.title(f"Exp5 early vs late intervention - {DS_TITLES.get(ds, sid)}", fontsize=13)
    plt.grid(True); plt.legend(fontsize=12); plt.tight_layout()
    out = os.path.join(FIG, f"Exp5_early_vs_late_ds{ds}.pdf")
    plt.savefig(out); plt.close()

    import csv
    with open(os.path.join(RES, f"ds{ds}_{sid}_late.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["scenario", "round", "ASPE"])
        for label, *_ in SCENARIOS:
            for rnd, a in series[label]:
                w.writerow([label, rnd, a])
    print(f"[{sid}] saved {out}")

if __name__ == "__main__":
    main()
