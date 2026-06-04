import os, re, json, subprocess, time, sys
from collections import defaultdict

from reddit_config import ID2LABEL as THREADS, RAW as OUT_DIR

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

DUMP_DIR = r"C:\Users\weli\Reddit_Dataset"
RS = os.path.join(DUMP_DIR, "RS_2019-04.zst")
RC = os.path.join(DUMP_DIR, "RC_2019-04.zst")
ZSTD = (r"C:\Users\weli\AppData\Local\Microsoft\WinGet\Packages"
        r"\Meta.Zstandard_Microsoft.Winget.Source_8wekyb3d8bbwe"
        r"\zstd-v1.5.7-win64\zstd.exe")
os.makedirs(OUT_DIR, exist_ok=True)

ID_NEEDLES = [(sid, ('"id":"' + sid + '"').encode()) for sid in THREADS]
LINKIDS = {("t3_" + sid).encode() for sid in THREADS}
LINKRX = re.compile(rb'"link_id":"(t3_[A-Za-z0-9]+)"')
SUB_KEEP = ("id", "title", "selftext", "author", "created_utc", "num_comments",
            "subreddit", "permalink", "score", "over_18")
COM_KEEP = ("id", "author", "body", "created_utc", "parent_id", "link_id", "score",
            "controversiality", "subreddit")

def stream(path):
    p = subprocess.Popen([ZSTD, "-dc", "--long=31", path], stdout=subprocess.PIPE, bufsize=1024 * 1024)
    for raw in p.stdout:
        yield raw
    p.stdout.close(); p.wait()

print(f"PASS 1/2  scanning RS for {len(THREADS)} submissions ...", flush=True)
subs = {}
t0 = time.time(); n = 0
for raw in stream(RS):
    n += 1
    if any(nd in raw for _, nd in ID_NEEDLES):
        try:
            o = json.loads(raw)
        except Exception:
            continue
        if o.get("id") in THREADS:
            subs[o["id"]] = {k: o.get(k) for k in SUB_KEEP}
            print(f"  found submission {o['id']} (r/{o.get('subreddit')}): {str(o.get('title'))[:60]}", flush=True)
            if len(subs) == len(THREADS):
                break
    if n % 4_000_000 == 0:
        print(f"  ...{n:,} submissions scanned, {time.time()-t0:.0f}s", flush=True)
print(f"  done pass 1: {len(subs)}/{len(THREADS)} submissions, {time.time()-t0:.0f}s\n", flush=True)

print("PASS 2/2  scanning RC for the threads' comments ...", flush=True)
comments = defaultdict(list)
t0 = time.time(); n = 0
for raw in stream(RC):
    n += 1
    m = LINKRX.search(raw)
    if m is not None and m.group(1) in LINKIDS:
        try:
            o = json.loads(raw)
        except Exception:
            continue
        comments[m.group(1).decode()].append({k: o.get(k) for k in COM_KEEP})
    if n % 20_000_000 == 0:
        tot = sum(len(v) for v in comments.values())
        print(f"  ...{n:,} comments scanned, {tot} collected, {time.time()-t0:.0f}s", flush=True)
print(f"  done pass 2: scanned {n:,} comments in {time.time()-t0:.0f}s\n", flush=True)

summary = []
for sid, label in THREADS.items():
    lid = "t3_" + sid
    cs = sorted(comments.get(lid, []), key=lambda c: c.get("created_utc") or 0)
    sub = subs.get(sid, {"id": sid})
    out = os.path.join(OUT_DIR, f"{sid}_{label}.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"submission": sub, "comments": cs}, f, ensure_ascii=False, indent=1)
    span_h = (max(c["created_utc"] for c in cs) - min(c["created_utc"] for c in cs)) / 3600.0 if cs else 0
    summary.append({"id": sid, "label": label, "subreddit": sub.get("subreddit"),
                    "title": sub.get("title"), "comments_in_dump": len(cs), "span_hours": round(span_h, 1)})
    print(f"  saved {os.path.basename(out)}  ({len(cs)} comments, span {span_h:.1f} h)", flush=True)

with open(os.path.join(OUT_DIR, "_summary.json"), "w", encoding="utf-8") as f:
    json.dump(summary, f, ensure_ascii=False, indent=2)
print("\nSUMMARY:")
for s in summary:
    print(f"  {s['id']} r/{s['subreddit']} {s['label']}: {s['comments_in_dump']} comments, {s['span_hours']}h")
print("\nDone -> datasets/reddit_raw/")
