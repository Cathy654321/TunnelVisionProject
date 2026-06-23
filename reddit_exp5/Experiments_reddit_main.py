
import os, pickle
from collections import Counter
from reddit_config import SNAP as SNAP_DIR
from SNTUser import SNTUser
from analysis_analyzer import Analyzer

WINDOW_SIZE = 30
MITIGATION_RATIO = 0.5
BASE_WINDOW = 60
ROUND_STEP = 30
MAX_ROUNDS = 18
MAX_USERS = 200


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


def seed_to_cut(users, events, cut, max_users=MAX_USERS):
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
