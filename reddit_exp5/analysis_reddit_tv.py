import os, json, pickle
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from reddit_config import (THREADS, SUBREDDITS, TITLES,
                           SNAP as SNAP_DIR, FIG as FIG_DIR, RES as RES_DIR, DATA as DS_DIR)
from Event import Event
from Comment import Comment
from SNTUser import SNTUser
from analysis_analyzer import Analyzer

os.makedirs(FIG_DIR, exist_ok=True)
os.makedirs(RES_DIR, exist_ok=True)

def load_event(sid):
    with open(os.path.join(SNAP_DIR, f"snapshot_reddit_{sid}.pkl"), "rb") as f:
        users = pickle.load(f)
        events = pickle.load(f)
    return events[0]

def _norm_sent(score):
    if isinstance(score, str):
        return score
    if score > 0.1:
        return "positive"
    if score < -0.1:
        return "negative"
    return "neutral"

def window_concentration(comments, topk=5):

    from collections import Counter
    freq = Counter()
    for c in comments:
        for p in c.aspect_opinion_pairs:
            a = p.get("aspect"); s = _norm_sent(p.get("score"))
            if a:
                freq[(a, s)] += 1
    total = sum(freq.values())
    if total == 0:
        return 0.0, 0
    top = sum(c for _, c in freq.most_common(topk))
    return round(top / total, 4), len(freq)

def sliding(analyzer, comments, n, W, step):
    rows = []
    for i, start in enumerate(range(0, max(1, n - W + 1), step), 1):
        r = analyzer.calculate_aspe_case(start_from=start, window_length=W)
        share, distinct = window_concentration(comments[start:start + W])
        rows.append({"timestep": i, "start": start, "ASPE": r["ASPE"], "CASE": r["CASE"],
                     "C": r["AspectCoverage (C)"], "Cs": r["SentimentCoverage (Cs)"],
                     "top5_share": share, "distinct_pairs": distinct})
    return rows

def cumulative(analyzer, n, step):
    rows = []
    for i, end in enumerate(range(step, n + 1, step), 1):
        r = analyzer.calculate_aspe_case(start_from=0, end_at=end)
        rows.append({"step": i, "end": end, "ASPE": r["ASPE"], "CASE": r["CASE"],
                     "C": r["AspectCoverage (C)"], "Cs": r["SentimentCoverage (Cs)"]})
    return rows

def pick_cut(cum, n):

    half = [r for r in cum if r["end"] <= max(1, int(0.6 * n))]
    if not half:
        half = cum
    peak = max(half, key=lambda r: r["ASPE"])
    cut = peak["end"]
    cut = max(40, min(cut, int(0.6 * n)))
    cut = min(cut, n)
    return cut, round(peak["ASPE"], 4)

def _smooth(y, k=5):
    if len(y) < k:
        return y
    out = []
    for i in range(len(y)):
        lo = max(0, i - k // 2); hi = min(len(y), i + k // 2 + 1)
        out.append(sum(y[lo:hi]) / (hi - lo))
    return out

def plot_two(rows, xkey, title, fname):
    xs = [r[xkey] for r in rows]
    plt.figure(figsize=(8, 6))
    plt.plot(xs, [r["ASPE"] for r in rows], marker="o", linewidth=2.5, markersize=5, label="ASPE", color="blue")
    plt.plot(xs, [r["CASE"] for r in rows], marker="s", linewidth=2.5, markersize=5, label="CASE", color="red")
    plt.xlabel("Timestep" if xkey == "timestep" else "Comments seen", fontsize=15)
    plt.ylabel("Metric value", fontsize=15)
    plt.title(title, fontsize=13)
    plt.grid(True); plt.legend(fontsize=14)
    plt.tight_layout()
    plt.savefig(fname, format="pdf"); plt.close()

def plot_narrowing(rows, title, fname):

    xs = [r["timestep"] for r in rows]
    aspe = _smooth([r["ASPE"] for r in rows])
    conc = _smooth([r["top5_share"] for r in rows])
    fig, ax1 = plt.subplots(figsize=(8, 6))
    ax1.plot(xs, aspe, color="blue", linewidth=2.8, marker="o", markersize=4, label="ASPE (smoothed)")
    ax1.set_xlabel("Timestep (sliding window over real comments)", fontsize=14)
    ax1.set_ylabel("ASPE", color="blue", fontsize=14)
    ax1.tick_params(axis="y", labelcolor="blue")
    ax2 = ax1.twinx()
    ax2.plot(xs, conc, color="red", linewidth=2.8, marker="s", markersize=4, label="Top-5 pair share (smoothed)")
    ax2.set_ylabel("Top-5 (aspect,sentiment) share", color="red", fontsize=14)
    ax2.tick_params(axis="y", labelcolor="red")
    plt.title(title, fontsize=13)
    ax1.grid(True, alpha=0.3)
    fig.tight_layout()
    plt.savefig(fname, format="pdf"); plt.close()

def main():
    curve_rows = []
    cut_info = {}
    for sid, label in THREADS:
        event = load_event(sid)
        n = len(event.comments)
        analyzer = Analyzer(event=event)
        W = 30
        step = max(3, W // 6)

        sl = sliding(analyzer, event.comments, n, W, step)
        cum = cumulative(analyzer, n, max(5, n // 30))
        cut, peak = pick_cut(cum, n)

        sr = SUBREDDITS.get(sid, "reddit"); ttl = TITLES.get(label, label)
        tag = f"r/{sr} ({ttl})"
        plot_two(sl, "timestep", f"{tag}: sliding-window (W={W})", os.path.join(FIG_DIR, f"ASPE_CASE_{sid}.pdf"))
        plot_two(cum, "end", f"{tag}: cumulative", os.path.join(FIG_DIR, f"cumulative_{sid}.pdf"))
        plot_narrowing(sl, f"{tag}: ASPE vs concentration (W={W})", os.path.join(FIG_DIR, f"narrowing_{sid}.pdf"))

        full = analyzer.calculate_aspe_case()
        cut_metrics = analyzer.calculate_aspe_case(start_from=0, end_at=cut)
        cut_info[sid] = {
            "label": label, "n_comments": n, "window_W": W, "step": step,
            "cut_index": cut, "cut_fraction": round(cut / n, 3),
            "ASPE_full": full["ASPE"], "CASE_full": full["CASE"],
            "ASPE_at_cut": cut_metrics["ASPE"], "CASE_at_cut": cut_metrics["CASE"],
            "ASPE_early_peak": peak,
            "ASPE_first_window": sl[0]["ASPE"] if sl else None,
            "ASPE_last_window": sl[-1]["ASPE"] if sl else None,
        }
        for r in sl:
            curve_rows.append({"id": sid, "label": label, "kind": "sliding", **r})
        for r in cum:
            curve_rows.append({"id": sid, "label": label, "kind": "cumulative",
                               "timestep": r["step"], "start": 0, **{k: r[k] for k in ("ASPE", "CASE", "C", "Cs")},
                               "end": r["end"]})

        print(f"[{sid}] {label}: n={n}, W={W} | full ASPE={full['ASPE']} CASE={full['CASE']} "
              f"| sliding ASPE {sl[0]['ASPE']:.3f} -> {sl[-1]['ASPE']:.3f} "
              f"| cut={cut} ({cut/n:.0%}), ASPE@cut={cut_metrics['ASPE']}")

    import csv
    keys = ["id", "label", "kind", "timestep", "start", "end", "ASPE", "CASE", "C", "Cs",
            "top5_share", "distinct_pairs"]
    with open(os.path.join(RES_DIR, "reddit_tv_curves.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore")
        w.writeheader(); w.writerows(curve_rows)
    with open(os.path.join(DS_DIR, "reddit_cut_points.json"), "w", encoding="utf-8") as f:
        json.dump(cut_info, f, indent=2)
    print("\nSaved figures -> reddit_exp5/figures/, curves -> reddit_exp5/results/, cut points -> reddit_exp5/data/")

if __name__ == "__main__":
    main()
