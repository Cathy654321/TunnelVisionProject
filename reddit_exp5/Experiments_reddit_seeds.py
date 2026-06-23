
import random
from Experiments_reddit_main import (load_fresh, seed_to_cut, analyse,
                                     WINDOW_SIZE, MITIGATION_RATIO)
from Comment import Comment
from SNTPlatform import SNTPlatform
import algorithm_collections

NUM_SEEDS = 10
WARMUP, POST = 6, 8
TOTAL_ITERS = WARMUP + POST
SENTIMENT_SCORES = [0.6, -0.6]


def _make_hint(pair):
    c = Comment(from_user=None, to_event=None)
    if getattr(c, "aspect_opinion_pairs", None) is None:
        c.aspect_opinion_pairs = []
    c.aspect_opinion_pairs.append(pair)
    return c


def _random_add(user, event, user_view, budget):
    user.strategy_budget = budget
    if budget <= 0:
        return user_view
    candidates = [{"aspect": a, "score": s} for a in event.aspects for s in SENTIMENT_SCORES]
    random.shuffle(candidates)
    return user_view + [_make_hint(c) for c in candidates[:budget]]


def _random_update(user, event, user_view, budget):
    user.strategy_budget = budget
    if budget <= 0 or len(user_view) == 0:
        return user_view
    candidates = [{"aspect": a, "score": s} for a in event.aspects for s in SENTIMENT_SCORES]
    random.shuffle(candidates)
    k = min(budget, len(user_view), len(candidates))
    idx = random.sample(range(len(user_view)), k)
    new_view = list(user_view)
    for j, i in enumerate(idx):
        new_view[i] = _make_hint(candidates[j])
    return new_view


RANDOM_VARIANTS = {
    "random_add":    ("add",    "tv_mitigation_add",    _random_add),
    "random_update": ("update", "tv_mitigation_update", _random_update),
}


def build_scenarios():
    cfgs = [("No", 0, 0, 1), ("No", 0, 0, 2), ("No", 0, 0, 3)]
    for strat in ["add", "remove", "update", "summarize", "hybrid",
                  "random_add", "random_update"]:
        for b in (3, 11):
            cfgs.append((strat, b, 0, 1))
    cfgs.append(("update", 11, WARMUP, 1))
    cfgs.append(("update", 3,  WARMUP, 1))
    return cfgs


def run_one(sid, ds, cut, strategy, budget, warmup, aspect, seed_k):
    random.seed(f"{sid}|{strategy}|{budget}|{warmup}|{aspect}|{seed_k}")
    users, events = load_fresh(sid)
    active = seed_to_cut(users, events, cut)
    seed_len = len(events[0].comments)
    net = SNTPlatform(); net.users = active; net.events = events

    fw_strategy, patch = strategy, None
    if strategy in RANDOM_VARIANTS:
        fw_strategy, attr, fn = RANDOM_VARIANTS[strategy]
        patch = (attr, getattr(algorithm_collections, attr))
        setattr(algorithm_collections, attr, fn)
    try:
        if warmup > 0:
            net.deploy_strategy({"strategy_mitigation": "No", "strategy_budget": 0,
                                 "mitigation_ratio": MITIGATION_RATIO})
            net.simulate_comments(event_index=0, k=warmup,
                                  window_size=WINDOW_SIZE, max_aspects=aspect)
            net.deploy_strategy({"strategy_mitigation": fw_strategy,
                                 "strategy_budget": int(budget),
                                 "mitigation_ratio": MITIGATION_RATIO})
            net.simulate_comments(event_index=0, k=POST,
                                  window_size=WINDOW_SIZE, max_aspects=aspect)
        else:
            net.deploy_strategy({"strategy_mitigation": fw_strategy,
                                 "strategy_budget": int(budget),
                                 "mitigation_ratio": MITIGATION_RATIO})
            net.simulate_comments(event_index=0, k=TOTAL_ITERS,
                                  window_size=WINDOW_SIZE, max_aspects=aspect)
    finally:
        if patch is not None:
            setattr(algorithm_collections, patch[0], patch[1])

    rows = analyse(events[0], seed_len)
    for r in rows:
        r.update({"dataset": ds, "reddit_id": sid, "strategy": strategy,
                  "strategy_budget": budget, "warmup": warmup, "aspect_no": aspect,
                  "seed": seed_k, "iters": TOTAL_ITERS,
                  "mitigation_ratio": MITIGATION_RATIO})
    return rows
