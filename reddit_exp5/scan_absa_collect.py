
import os, re, json, subprocess, time, random

DUMP = r"C:\Users\weli\Reddit_Dataset"
RS = os.path.join(DUMP, "RS_2019-04.zst")
RC = os.path.join(DUMP, "RC_2019-04.zst")
ZSTD = (r"C:\Users\weli\AppData\Local\Microsoft\WinGet\Packages"
        r"\Meta.Zstandard_Microsoft.Winget.Source_8wekyb3d8bbwe\zstd-v1.5.7-win64\zstd.exe")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "scan_absa")
THREADS_DIR = os.path.join(OUT, "threads")
os.makedirs(THREADS_DIR, exist_ok=True)

SIZE_LO, SIZE_HI = 150, 700
SPAN_MAX_H = 48.0
MIN_USABLE = 120
POOL_RS = 2200
TARGET = 300
SEED = 7

BLOCK = {
    "me_irl", "meirl", "2meirl4meirl", "memes", "dankmemes", "funny", "adviceanimals",
    "wholesomememes", "prequelmemes", "historymemes", "comedyheaven", "okbuddyretard",
    "terriblefacebookmemes", "memeeconomy", "dank_meme", "edgymemes", "trippinthroughtime",
    "pics", "aww", "gifs", "mildlyinteresting", "interestingasfuck", "damnthatsinteresting",
    "oddlysatisfying", "nextfuckinglevel", "beamazed", "whatcouldgowrong", "instant_regret",
    "tihi", "gaming", "blackpeopletwitter", "whitepeopletwitter", "insanepeoplefacebook",
    "facepalm", "cringetopia", "trashy", "publicfreakout", "holup", "unexpected",
    "contagiouslaughter", "mademesmile", "aboringdystopia", "reactiongifs", "hmmm",
    "cursedcomments", "murderedbywords", "clevercomebacks", "rareinsults", "woooosh",
    "therewasanattempt", "nonononoyes", "wellthatsucks", "crappydesign", "assholedesign",
    "mildlyinfuriating", "softwaregore", "gatekeeping", "im14andthisisdeep", "iamatotalpieceofshit",
    "gifsthatkeepongiving", "perfecttiming", "outoftheloop", "tumblr", "4chan", "greentext",
    "starterpacks", "raimimemes", "surrealmemes", "deepfriedmemes", "bonehurtingjuice",
}
SPAM_RX = re.compile(rb"(livestream|streams?$|\bstream\b|hq$|tv$|porn|gonewild|nsfw|nude|onlyfans)", re.I)
NCRX = re.compile(rb'"num_comments":(\d+)')
LINKRX = re.compile(rb'"link_id":"(t3_[A-Za-z0-9]+)"')

BOTS = {"AutoModerator", "[deleted]", "B0tRank", "RemindMeBot", "sneakpeekbot",
        "WikiTextBot", "thesav_bot", "totesmessenger"}


def stream(path):
    p = subprocess.Popen([ZSTD, "-dc", "--long=31", path], stdout=subprocess.PIPE, bufsize=1 << 20)
    for raw in p.stdout:
        yield raw
    p.stdout.close(); p.wait()


def usable(c):
    b = (c.get("body") or "").strip()
    if not b or b in ("[removed]", "[deleted]"):
        return False
    if (c.get("author") or "") in BOTS:
        return False
    return True


def rs_pass():
    random.seed(SEED)
    print(f"RS pass: reservoir-sampling {POOL_RS} threads, {SIZE_LO}-{SIZE_HI} cmts, topic subs only ...", flush=True)
    res, qual, n, t0 = [], 0, 0, time.time()
    for raw in stream(RS):
        n += 1
        m = NCRX.search(raw)
        if not m:
            continue
        nc = int(m.group(1))
        if not (SIZE_LO <= nc <= SIZE_HI):
            continue
        try:
            o = json.loads(raw)
        except Exception:
            continue
        sub = (o.get("subreddit") or "")
        if o.get("over_18") or sub.lower() in BLOCK or SPAM_RX.search(sub.encode()):
            continue
        if (o.get("subreddit_type") or "public") not in ("public", "restricted"):
            continue
        qual += 1
        item = {"id": o.get("id"), "subreddit": sub, "num_comments": nc,
                "title": o.get("title"), "selftext": (o.get("selftext") or "")[:600],
                "created_utc": o.get("created_utc"), "domain": o.get("domain")}
        if len(res) < POOL_RS:
            res.append(item)
        else:
            j = random.randint(0, qual - 1)
            if j < POOL_RS:
                res[j] = item
        if n % 1_000_000 == 0:
            print(f"  ...{n:,} submissions scanned, {qual} qualifying, {time.time()-t0:.0f}s", flush=True)
    print(f"  RS done: pool={len(res)} (from {qual} qualifying), {time.time()-t0:.0f}s", flush=True)
    return {it["id"]: it for it in res if it["id"]}


def rc_pass(pool):
    linkset = {("t3_" + i).encode() for i in pool}
    print(f"RC pass: collecting comments for {len(pool)} threads (streaming 152GB) ...", flush=True)
    buf, n, t0 = {}, 0, time.time()
    for raw in stream(RC):
        n += 1
        m = LINKRX.search(raw)
        if m is not None and m.group(1) in linkset:
            try:
                o = json.loads(raw)
            except Exception:
                continue
            buf.setdefault(m.group(1).decode(), []).append(
                {"body": o.get("body"), "author": o.get("author"),
                 "created_utc": o.get("created_utc"), "id": o.get("id")})
        if n % 20_000_000 == 0:
            print(f"  ...{n:,} comments scanned, {time.time()-t0:.0f}s", flush=True)
    print(f"  RC done: {time.time()-t0:.0f}s", flush=True)
    return buf


def main():
    pool = rs_pass()
    json.dump(list(pool.values()), open(os.path.join(OUT, "pool_rs.json"), "w", encoding="utf-8"), indent=1)

    buf = rc_pass(pool)

    print("Filtering by span + min-usable, down-selecting ...", flush=True)
    selected, rejected = [], []
    cand = list(pool.items())
    random.seed(SEED + 1); random.shuffle(cand)
    for sid, meta in cand:
        raw_cs = buf.get("t3_" + sid, [])
        cs = sorted([c for c in raw_cs if usable(c) and c.get("created_utc")],
                    key=lambda c: c["created_utc"])
        if len(cs) < MIN_USABLE:
            rejected.append({**meta, "n_usable": len(cs), "reason": "min_usable"})
            continue
        span_h = (cs[-1]["created_utc"] - cs[0]["created_utc"]) / 3600.0
        if span_h > SPAN_MAX_H:
            rejected.append({**meta, "n_usable": len(cs), "span_h": round(span_h, 1), "reason": "span"})
            continue
        rec = {**meta, "n_usable": len(cs), "span_h": round(span_h, 1)}
        if len(selected) < TARGET:
            json.dump(cs, open(os.path.join(THREADS_DIR, f"{sid}.json"), "w", encoding="utf-8"))
            selected.append(rec)
        else:
            rejected.append({**rec, "reason": "over_target"})
    json.dump(selected, open(os.path.join(OUT, "selected.json"), "w", encoding="utf-8"), indent=1)
    json.dump(rejected, open(os.path.join(OUT, "rejected.json"), "w", encoding="utf-8"), indent=1)
    print(f"\nSELECTED {len(selected)} threads (target {TARGET}); comments -> scan_absa/threads/")
    from collections import Counter
    subc = Counter(r["subreddit"] for r in selected)
    print("top subreddits in pool:", dict(subc.most_common(12)))


if __name__ == "__main__":
    main()
