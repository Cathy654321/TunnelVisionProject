
import os, sys, json, pickle, csv
HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from scipy.stats import spearmanr
from reddit_config import DATA, RES
from Event import Event
from Comment import Comment
from SNTUser import SNTUser
from analysis_analyzer import Analyzer
from analysis_reddit_tv import sliding, cumulative, pick_cut
import reddit_utils as rae
import reddit_absa_extract as absa

SIDS = ["bgknkt", "bfvqy1", "bbf7wd", "bct7zc", "bip3hg", "bgv8rd", "bix6la"]
SUBS = {"bgknkt": "bayarea", "bfvqy1": "unpopularopinion", "bbf7wd": "newzealand",
        "bct7zc": "teslamotors", "bip3hg": "vegetarian", "bgv8rd": "Vechain", "bix6la": "PurplePillDebate"}
PRESCREEN = {"bgknkt": -0.82, "bfvqy1": -0.62, "bbf7wd": -0.52, "bct7zc": -0.55,
             "bip3hg": -0.39, "bgv8rd": -0.43, "bix6la": -0.46}

THREADS_DIR = os.path.join(HERE, "scan_absa", "threads")
SNAP_SCAN = os.path.join(DATA, "snapshots_absa_scan")
EXPORT_DIR = os.path.join(DATA, "scan_verify_exports")
os.makedirs(SNAP_SCAN, exist_ok=True); os.makedirs(EXPORT_DIR, exist_ok=True)
SCORE2LAB = {1.0: "positive", 0.0: "neutral", -1.0: "negative"}


def build(sid):
    comments = json.load(open(os.path.join(THREADS_DIR, f"{sid}.json"), encoding="utf-8"))
    comments = [c for c in comments if (c.get("body") or "").strip()]
    labels, pairs_per_comment = absa.absa_aspects(comments, sid, max_per_comment=3, verbose=False)

    sr = SUBS[sid]
    event = Event(event_id=sid); event.aspects = labels
    users = {}
    def get_user(a):
        if a not in users:
            u = SNTUser(user_id=a); u.profile = {"ID": a, "Source": f"reddit_{sr}", "Thread": sid}
            u.profile_text = f"Reddit user {a} in r/{sr} thread {sid}"; users[a] = u
        return users[a]
    export_rows = []
    for idx, (c, pairs) in enumerate(zip(comments, pairs_per_comment)):
        u = get_user(c.get("author") or "unknown")
        com = Comment(from_user=u, to_event=event)
        com.text = (c["body"] or "")[:500]; com.aspect_opinion_pairs = pairs
        com.time_flag = rae.to_dt(c.get("created_utc"))
        u.posted.append(com); event.comments.append(com)
        export_rows.append({
            "idx": idx, "comment_id": c.get("id"), "author": c.get("author"),
            "created_utc": c.get("created_utc"),
            "aspects": " | ".join(p["aspect"] for p in pairs),
            "sentiments": " | ".join(SCORE2LAB[p["score"]] for p in pairs),
            "scores": " | ".join(str(p["score"]) for p in pairs),
            "body": (c["body"] or "").replace("\r", " ")})
    with open(os.path.join(SNAP_SCAN, f"snapshot_reddit_{sid}.pkl"), "wb") as f:
        pickle.dump(list(users.values()), f); pickle.dump([event], f)
    with open(os.path.join(EXPORT_DIR, f"{sid}_aspect_sentiment.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(export_rows[0].keys()), quoting=csv.QUOTE_ALL)
        w.writeheader(); w.writerows(export_rows)
    return event


def main():
    gate_rows, cut_info = [], {}
    print(f"{'sid':9}{'n':>5}{'asp':>5}{'mixed':>6}  {'rhoASPE_full(p)':>18}{'pre':>7}{'rhoConc(p)':>16}  verdict")
    for sid in SIDS:
        ev = build(sid)
        n = len(ev.comments)
        an = Analyzer(event=ev)
        sl = sliding(an, ev.comments, n, 30, 5)
        cum = cumulative(an, n, max(5, n // 30)); cut, peak = pick_cut(cum, n)
        ts = [r["timestep"] for r in sl]
        rA, pA = spearmanr(ts, [r["ASPE"] for r in sl])
        rC, pC = spearmanr(ts, [r["top5_share"] for r in sl])
        mixed = sum(1 for c in ev.comments if len({p["score"] for p in c.aspect_opinion_pairs}) > 1)
        nasp = len(ev.aspects)
        full_narrows = (rA <= -0.25 and rC >= 0.15 and pA < 0.05)
        verdict = "NARROWS" if full_narrows else ("weak" if rA < 0 else "broadens")
        print(f"{sid:9}{n:>5}{nasp:>5}{mixed:>6}  {rA:>+8.3f}({pA:.1e}){PRESCREEN[sid]:>7}{rC:>+8.3f}({pC:.1e})  {verdict}")
        gate_rows.append({"sid": sid, "subreddit": SUBS[sid], "n": n, "n_aspects": nasp,
                          "n_mixed": mixed, "rho_aspe_full": round(float(rA), 4), "p_aspe": float(pA),
                          "rho_conc_full": round(float(rC), 4), "p_conc": float(pC),
                          "rho_aspe_prescreen": PRESCREEN[sid],
                          "aspe_first": round(sl[0]["ASPE"], 3), "aspe_last": round(sl[-1]["ASPE"], 3),
                          "cut_index": cut, "verdict": verdict})
        cut_info[sid] = {"subreddit": SUBS[sid], "n_comments": n, "cut_index": cut,
                         "cut_fraction": round(cut / n, 3), "rho_aspe_full": round(float(rA), 4)}
    with open(os.path.join(RES, "scan_verify_gate.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(gate_rows[0].keys())); w.writeheader(); w.writerows(gate_rows)
    json.dump(cut_info, open(os.path.join(DATA, "reddit_cut_points_scan.json"), "w", encoding="utf-8"), indent=2)
    nnar = sum(1 for r in gate_rows if r["verdict"] == "NARROWS")
    print(f"\nFull-method confirmed narrowers: {nnar}/{len(SIDS)}")
    print("Saved -> snapshots_absa_scan/, reddit_cut_points_scan.json, scan_verify_exports/, results/scan_verify_gate.csv")


if __name__ == "__main__":
    main()
