
from collections import Counter


def _norm_sent(score):
    if isinstance(score, str):
        return score
    if score > 0.1:
        return "positive"
    if score < -0.1:
        return "negative"
    return "neutral"


def window_concentration(comments, topk=5):
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
