
import os, sys, json, hashlib, time
from concurrent.futures import ThreadPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from scipy.stats import spearmanr
from reddit_absa_extract import MODEL, _CREATE_KW, _client
from analysis_analyzer import Analyzer
from analysis_reddit_tv import sliding
from Event import Event
from Comment import Comment

OUT = os.path.join(HERE, "scan_absa")
THREADS_DIR = os.path.join(OUT, "threads")
EXTRACT_DIR = os.path.join(OUT, "cache_extract")
CANON_DIR = os.path.join(OUT, "cache_canon")
PRE_DIR = os.path.join(OUT, "prescreen")
for d in (EXTRACT_DIR, CANON_DIR, PRE_DIR):
    os.makedirs(d, exist_ok=True)

SENT2SCORE = {"positive": 1.0, "neutral": 0.0, "negative": -1.0}
SENTSET = set(SENT2SCORE)
PROMPT_V = "openabsa-1"
W, STEP = 30, 5

_EXTRACT_SYS = (
    "You extract aspect-based sentiment from ONE comment in a focused online discussion. "
    "An ASPECT is an evaluable facet/attribute of the discussion's subject toward which the "
    "commenter takes a stance. Give each a SHORT lowercase noun-phrase name (2-4 words). Bind "
    "sentiment to EACH aspect independently (a comment may be positive on one facet, negative on "
    "another). Rules: include a facet ONLY if the comment takes a stance on it; 'positive'=favorable/"
    "supportive, 'negative'=critical/opposed, 'neutral'=addressed without clear valence; empty list "
    "for jokes/off-topic/pure factual asides. Return STRICT JSON "
    '{"pairs":[{"aspect":"<short noun phrase>","sentiment":"positive|neutral|negative"}]}'
)
_CANON_SYS = (
    "You merge near-duplicate aspect phrases extracted from ONE discussion thread into a small "
    "canonical set of evaluable facets. Group synonyms/paraphrases; assign EVERY input phrase to "
    "exactly one canonical aspect (a short lowercase noun phrase). Aim for 6-15 canonical aspects. "
    'Return STRICT JSON {"map":{"<raw phrase>":"<canonical aspect>", ...}} covering every input phrase.'
)


def _h(*parts):
    h = hashlib.sha256()
    h.update(("||".join(parts)).encode("utf-8"))
    return h.hexdigest()


def _load(path):
    return json.load(open(path, encoding="utf-8")) if os.path.exists(path) else {}


def _extract_one(client, title, body):
    user = f"Discussion: {title}\n\nComment:\n\"\"\"\n{body[:3500]}\n\"\"\"\nReturn the JSON."
    for attempt in range(4):
        try:
            r = client.chat.completions.create(
                model=MODEL, response_format={"type": "json_object"},
                messages=[{"role": "system", "content": _EXTRACT_SYS},
                          {"role": "user", "content": user}], **_CREATE_KW)
            raw = json.loads(r.choices[0].message.content)
            out, seen = [], set()
            for p in raw.get("pairs", []):
                a = (p.get("aspect") or "").strip().lower()
                s = (p.get("sentiment") or "").strip().lower()
                if a and s in SENTSET and a not in seen:
                    seen.add(a); out.append({"aspect": a, "sentiment": s})
            return out
        except Exception as e:
            if attempt == 3:
                raise RuntimeError(str(e)[:160])
            time.sleep(1.5 * (attempt + 1))


def _canon_call(client, title, phrases):
    user = (f"Discussion: {title}\n\nRaw aspect phrases ({len(phrases)}):\n"
            + json.dumps(sorted(phrases), ensure_ascii=False) + "\nReturn the JSON map.")
    r = client.chat.completions.create(
        model=MODEL, response_format={"type": "json_object"},
        messages=[{"role": "system", "content": _CANON_SYS},
                  {"role": "user", "content": user}], **_CREATE_KW)
    m = json.loads(r.choices[0].message.content).get("map", {})
    return {str(k).strip().lower(): str(v).strip().lower() for k, v in m.items()}


def extract_all(selected, client, workers=16, checkpoint_every=3000):
    """Open-extract every comment of every selected thread, caching per sid to cache_extract/
    incrementally so the run is durable and resumable cache-first."""
    todo = []
    caches = {}
    for sid, title, comments in selected:
        cache = _load(os.path.join(EXTRACT_DIR, f"{sid}.json")); caches[sid] = cache
        for c in comments:
            k = _h(c["body"], MODEL, PROMPT_V)
            if k not in cache:
                todo.append((sid, k, title, c["body"]))
    print(f"  open-extraction: {len(todo)} comment calls to make "
          f"({sum(len(v) for v in caches.values())} cached)", flush=True)
    if not todo:
        return caches

    def flush(sids):
        for sid in sids:
            json.dump(caches[sid], open(os.path.join(EXTRACT_DIR, f"{sid}.json"), "w",
                      encoding="utf-8"), ensure_ascii=False)

    done = failed = 0
    dirty = set()
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(_extract_one, client, t, b): (sid, k) for sid, k, t, b in todo}
        for fut in as_completed(futs):
            sid, k = futs[fut]
            try:
                caches[sid][k] = fut.result(); dirty.add(sid)
            except Exception:
                failed += 1
            done += 1
            if done % 500 == 0:
                print(f"    extracted {done}/{len(todo)} ({failed} failed)", flush=True)
            if done % checkpoint_every == 0:
                flush(dirty); dirty = set()
                print(f"    [checkpoint] saved {done} extractions to cache_extract/", flush=True)
    flush(dirty)
    print(f"  extraction done ({failed} failed)", flush=True)
    return caches


def score_thread(sid, title, comments, ecache, client):
    raw_pairs = [ecache.get(_h(c["body"], MODEL, PROMPT_V), []) for c in comments]
    uniq = sorted({p["aspect"] for pl in raw_pairs for p in pl})
    if len(uniq) < 3:
        return None
    cpath = os.path.join(CANON_DIR, f"{sid}.json")
    canon = _load(cpath)
    ckey = _h(json.dumps(uniq), MODEL, PROMPT_V)
    cmap = canon.get(ckey)
    if cmap is None:
        try:
            cmap = _canon_call(client, title, uniq)
        except Exception:
            cmap = {a: a for a in uniq}
        canon[ckey] = cmap
        json.dump(canon, open(cpath, "w", encoding="utf-8"), ensure_ascii=False)
    def cn(a):
        return cmap.get(a, a)
    canon_aspects = sorted({cn(a) for a in uniq})
    ev = Event(event_id=sid); ev.aspects = canon_aspects
    canon_labels = []
    for c, pl in zip(comments, raw_pairs):
        seen, pairs = set(), []
        for p in pl:
            a = cn(p["aspect"])
            if a not in seen:
                seen.add(a); pairs.append({"aspect": a, "score": SENT2SCORE[p["sentiment"]]})
        cm = Comment(from_user=None, to_event=ev); cm.aspect_opinion_pairs = pairs
        ev.comments.append(cm)
        canon_labels.append([{"aspect": x["aspect"], "score": x["score"]} for x in pairs])
    n = len(ev.comments)
    if n < W + STEP:
        return None
    an = Analyzer(event=ev)
    sl = sliding(an, ev.comments, n, W, STEP)
    if len(sl) < 8:
        return None
    ts = [r["timestep"] for r in sl]
    rA, pA = spearmanr(ts, [r["ASPE"] for r in sl])
    rC, pC = spearmanr(ts, [r["top5_share"] for r in sl])
    th = max(1, len(sl) // 3)
    early = sum(r["ASPE"] for r in sl[:th]) / th
    late = sum(r["ASPE"] for r in sl[-th:]) / th
    n_pairs = sum(len(pl) for pl in canon_labels)
    n_mixed = sum(1 for pl in canon_labels if len({x["score"] for x in pl}) > 1)
    summary = {"sid": sid, "n_comments": n, "n_aspects": len(canon_aspects),
               "n_pairs": n_pairs, "n_with_aspect": sum(1 for pl in canon_labels if pl),
               "n_mixed": n_mixed, "rho_aspe": round(float(rA), 4), "p_aspe": float(pA),
               "rho_conc": round(float(rC), 4), "p_conc": float(pC),
               "aspe_early": round(early, 3), "aspe_late": round(late, 3),
               "narrow_score": round(-float(rA) + float(rC) + max(0.0, early - late), 4),
               "aspects": canon_aspects}
    json.dump({"summary": summary, "curve": sl, "labels": canon_labels},
              open(os.path.join(PRE_DIR, f"{sid}.json"), "w", encoding="utf-8"), ensure_ascii=False)
    return summary, sl


def canon_all(selected, ecaches, client, workers=16):
    """Parallelize the per-thread canonicalization calls (cache-first); each thread writes its
    own cache_canon/<sid>.json so this is safe to parallelize and fully resumable."""
    todo = []
    for sid, title, comments in selected:
        ec = ecaches[sid]
        uniq = sorted({p["aspect"] for c in comments
                       for p in ec.get(_h(c["body"], MODEL, PROMPT_V), [])})
        if len(uniq) < 3:
            continue
        ckey = _h(json.dumps(uniq), MODEL, PROMPT_V)
        if ckey not in _load(os.path.join(CANON_DIR, f"{sid}.json")):
            todo.append((sid, title, uniq, ckey))
    print(f"  canonicalization: {len(todo)} thread calls ({len(selected)-len(todo)} cached)", flush=True)
    if not todo:
        return

    def do(sid, title, uniq, ckey):
        try:
            m = _canon_call(client, title, uniq)
        except Exception:
            m = {a: a for a in uniq}
        return sid, ckey, m

    done = 0
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = [ex.submit(do, *t) for t in todo]
        for fut in as_completed(futs):
            sid, ckey, m = fut.result()
            cpath = os.path.join(CANON_DIR, f"{sid}.json")
            canon = _load(cpath); canon[ckey] = m
            json.dump(canon, open(cpath, "w", encoding="utf-8"), ensure_ascii=False)
            done += 1
            if done % 25 == 0:
                print(f"    canonicalized {done}/{len(todo)}", flush=True)


def main():
    sel = json.load(open(os.path.join(OUT, "selected.json"), encoding="utf-8"))
    selected = []
    for rec in sel:
        sid = rec["id"]
        cpath = os.path.join(THREADS_DIR, f"{sid}.json")
        if not os.path.exists(cpath):
            continue
        comments = [c for c in json.load(open(cpath, encoding="utf-8")) if (c.get("body") or "").strip()]
        selected.append((sid, rec.get("title") or sid, comments))
    print(f"pre-screening {len(selected)} threads with {MODEL} ...", flush=True)
    client = _client()
    ecaches = extract_all(selected, client)

    print("canonicalizing (parallel) ...", flush=True)
    canon_all(selected, ecaches, client)

    print("scoring ...", flush=True)
    rows, curve_rows = [], []
    meta = {r["id"]: r for r in sel}
    for i, (sid, title, comments) in enumerate(selected, 1):
        res = score_thread(sid, title, comments, ecaches[sid], client)
        if res is None:
            continue
        summ, sl = res
        m = meta.get(sid, {})
        summ2 = {**summ, "subreddit": m.get("subreddit"), "span_h": m.get("span_h"), "title": title}
        rows.append(summ2)
        for r in sl:
            curve_rows.append({"sid": sid, **r})
        if i % 25 == 0:
            print(f"  scored {i}/{len(selected)}", flush=True)

    rows.sort(key=lambda r: r["narrow_score"], reverse=True)
    import csv
    rk = ["sid", "subreddit", "n_comments", "n_aspects", "n_pairs", "n_with_aspect", "n_mixed",
          "rho_aspe", "p_aspe", "rho_conc", "p_conc", "aspe_early", "aspe_late", "narrow_score",
          "span_h", "title"]
    with open(os.path.join(OUT, "ranking.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=rk, extrasaction="ignore"); w.writeheader(); w.writerows(rows)
    ck = ["sid", "timestep", "start", "ASPE", "CASE", "C", "Cs", "top5_share", "distinct_pairs"]
    with open(os.path.join(OUT, "curves.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=ck, extrasaction="ignore"); w.writeheader(); w.writerows(curve_rows)

    narrowers = [r for r in rows if r["rho_aspe"] <= -0.25 and r["rho_conc"] >= 0.15]
    sig_narrow = [r for r in rows if r["rho_aspe"] < 0 and r["p_aspe"] < 0.05]
    print(f"\n=== {len(rows)} threads scored ===")
    print(f"clear narrowers (rho_ASPE<=-0.25 & rho_conc>=0.15): {len(narrowers)}")
    print(f"any significant narrowing (rho_ASPE<0, p<0.05):     {len(sig_narrow)}")
    print(f"{'sid':<9}{'rhoA':>7}{'rhoC':>7}{'early':>7}{'late':>7}{'n':>5}  subreddit  title")
    for r in rows[:15]:
        print(f"{r['sid']:<9}{r['rho_aspe']:>7.2f}{r['rho_conc']:>7.2f}{r['aspe_early']:>7.2f}"
              f"{r['aspe_late']:>7.2f}{r['n_comments']:>5}  r/{r['subreddit']}  {(r['title'] or '')[:48]}")
    print("\nSaved -> scan_absa/ranking.csv, scan_absa/curves.csv, scan_absa/prescreen/<sid>.json")


if __name__ == "__main__":
    main()
