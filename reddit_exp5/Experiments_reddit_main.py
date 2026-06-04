import os, sys, json, pickle, argparse, itertools
import pandas as pd

from reddit_config import (DATASETS, SID2IDX,
                           SNAP as SNAP_DIR, RES_CASE as RES_DIR,
                           CONSOLIDATED, CUTS_JSON as CUTS)
from SNTPlatform import SNTPlatform
from SNTUser import SNTUser
from analysis_analyzer import Analyzer
from utils_consolidate_csvs import consolidate_csv_folder

WINDOW_SIZE = 30
MITIGATION_RATIO = 0.5
BUDGETS = [1, 3, 5, 9, 11, 15]
GREEDY = ["add", "remove", "update", "hybrid", "summarize"]
SWEEP = ["add", "remove", "update", "summarize"]
BASE_WINDOW = 60
ROUND_STEP = 30
MAX_ROUNDS = 18

def load_fresh(sid):
    with open(os.path.join(SNAP_DIR, f"snapshot_reddit_{sid}.pkl"), "rb") as f:
        users = pickle.load(f)
        events = pickle.load(f)

    by_id = {u.id: u for u in users}
    ev = events[0]
    for c in ev.comments:
        fu = getattr(c, "from_user", None)
        uid = getattr(fu, "id", None)
        if uid is None:
            continue
        u = by_id.get(uid)
        if u is None:
            u = SNTUser(user_id=uid); by_id[uid] = u; users.append(u)
        c.from_user = u
    for u in users:
        u.posted = []
    for c in ev.comments:
        if getattr(c, "from_user", None) is not None:
            c.from_user.posted.append(c)
    return users, events

MAX_USERS = 200

def seed_to_cut(users, events, cut, max_users=MAX_USERS):

    from collections import Counter
    seed_full = events[0].comments[:cut]
    cnt = Counter(id(c.from_user) for c in seed_full if c.from_user is not None)
    cand = [u for u in users if cnt.get(id(u), 0) > 0]
    cand.sort(key=lambda u: cnt.get(id(u), 0), reverse=True)
    active = cand[:max_users] if (max_users and len(cand) > max_users) else cand
    keep = {id(u) for u in active}
    seed = [c for c in seed_full if c.from_user is not None and id(c.from_user) in keep]
    seed_ids = {id(c) for c in seed}
    for u in active:
        u.posted = [c for c in u.posted if id(c) in seed_ids]
    events[0].comments = list(seed)
    return active

def analyse(event, start):
    analyzer = Analyzer(event=event)
    n = len(event.comments)
    rows = []
    for r in range(1, MAX_ROUNDS + 1):
        end_at = start + BASE_WINDOW + ROUND_STEP * (r - 1)
        if end_at > n:
            break
        res = analyzer.calculate_aspe_case(start_from=start, window_length=None, end_at=end_at)
        res["round"] = r
        rows.append(res)
    return rows

def run_config(sid, ds_idx, cut, strategy, budget, aspect, iters):
    users, events = load_fresh(sid)
    active = seed_to_cut(users, events, cut)
    seed_len = len(events[0].comments)
    net = SNTPlatform()
    net.users = active
    net.events = events
    net.deploy_strategy({"strategy_mitigation": strategy,
                         "strategy_budget": int(budget),
                         "mitigation_ratio": float(MITIGATION_RATIO)})
    net.simulate_comments(event_index=0, k=iters, window_size=WINDOW_SIZE, max_aspects=aspect)
    rows = analyse(events[0], seed_len)
    for res in rows:
        res.update({"dataset": ds_idx, "reddit_id": sid, "start_from": seed_len, "n_users": len(active),
                    "window_length": BASE_WINDOW, "aspect_no": aspect,
                    "user_window_size": WINDOW_SIZE, "windows_size": WINDOW_SIZE,
                    "strategy": strategy, "strategy_budget": budget,
                    "mitigation_ratio": MITIGATION_RATIO})
    out = os.path.join(RES_DIR, f"ds{ds_idx}_{sid}_a{aspect}_s{strategy}_b{budget}.csv")
    pd.DataFrame(rows).to_csv(out, index=False)
    return out, len(rows)

def build_grid():

    cfgs = []
    cfgs.append(("No", 0, 1))
    cfgs.append(("No", 0, 2))
    cfgs.append(("No", 0, 3))
    for strat in SWEEP:
        for b in BUDGETS:
            cfgs.append((strat, b, 1))
    cfgs.append(("hybrid", 3, 1))
    cfgs.append(("hybrid", 11, 1))
    cfgs.append(("remove", 999, 1))
    cfgs.append(("summarize", 999, 1))

    seen, out = set(), []
    for c in cfgs:
        if c not in seen:
            seen.add(c); out.append(c)
    return out

def run_dataset(sid, iters, pilot=False):
    os.makedirs(RES_DIR, exist_ok=True)
    with open(CUTS) as f:
        cut = int(json.load(f)[sid]["cut_index"])
    ds_idx = SID2IDX[sid]
    grid = build_grid()
    if pilot:
        grid = [("No", 0, 1), ("update", 5, 1), ("summarize", 999, 1)]
    print(f"[{sid}] dataset {ds_idx}: cut={cut}, iters={iters}, {len(grid)} configs", flush=True)
    import time
    for i, (strat, b, asp) in enumerate(grid, 1):
        t0 = time.time()
        out, nrows = run_config(sid, ds_idx, cut, strat, b, asp, iters)
        print(f"  [{i}/{len(grid)}] {strat} b={b} a={asp}: {nrows} rounds, "
              f"{time.time()-t0:.1f}s -> {os.path.basename(out)}", flush=True)
    print(f"[{sid}] done.", flush=True)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sid", choices=[s for s, _ in DATASETS])
    ap.add_argument("--iters", type=int, default=12)
    ap.add_argument("--pilot", action="store_true")
    ap.add_argument("--consolidate", action="store_true")
    args = ap.parse_args()

    if args.consolidate:
        consolidate_csv_folder(results_folder=RES_DIR, output_file=CONSOLIDATED, strict_columns=False)
        print(f"Consolidated -> {CONSOLIDATED}")
        return
    if not args.sid:
        ap.error("provide --sid <id> or --consolidate")
    run_dataset(args.sid, args.iters, pilot=args.pilot)

if __name__ == "__main__":
    main()
