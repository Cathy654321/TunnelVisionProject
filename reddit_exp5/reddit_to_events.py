import os, json, csv, pickle

from reddit_config import (THREADS, SUBREDDITS, PKG as HERE,
                           RAW as RAW_DIR, SNAP as SNAP_DIR, DATA as DS_DIR)
from Event import Event
from Comment import Comment
from SNTUser import SNTUser
import reddit_aspect_extract as rae

os.makedirs(SNAP_DIR, exist_ok=True)

N_ASPECTS = 12
MAX_ASPECTS_PER_COMMENT = 3
MAX_COMMENTS = 6000

def process_thread(sid, label):
    path = os.path.join(RAW_DIR, f"{sid}_{label}.json")
    with open(path, "r", encoding="utf-8") as f:
        rec = json.load(f)
    sub = rec["submission"]
    sr = SUBREDDITS.get(sid) or sub.get("subreddit") or "reddit"
    raw_comments = [c for c in rec["comments"] if rae.usable(c)][:MAX_COMMENTS]

    aspects, pairs_per_comment = rae.nmf_aspects(
        raw_comments, n_aspects=N_ASPECTS, max_per_comment=MAX_ASPECTS_PER_COMMENT)

    event = Event(event_id=sid)
    event.topic = sub.get("title") or sid
    event.content = (sub.get("selftext") or "").replace("\n", " ").strip()
    event.aspects = aspects
    event.publishedAt = rae.to_dt(sub.get("created_utc"))

    users = {}

    def get_user(author):
        if author not in users:
            u = SNTUser(user_id=author)
            u.profile = {"ID": author, "Source": f"reddit_{sr}", "Thread": sid}
            u.profile_text = f"Reddit user {author} in r/{sr} thread {sid}"
            users[author] = u
        return users[author]

    n_pairs = 0
    for c, pairs in zip(raw_comments, pairs_per_comment):
        u = get_user(c.get("author") or "unknown")
        com = Comment(from_user=u, to_event=event)
        com.text = c["body"][:500]
        com.aspect_opinion_pairs = pairs
        com.time_flag = rae.to_dt(c.get("created_utc"))
        u.posted.append(com)
        event.comments.append(com)
        n_pairs += len(pairs)

    snap = os.path.join(SNAP_DIR, f"snapshot_reddit_{sid}.pkl")
    with open(snap, "wb") as f:
        pickle.dump(list(users.values()), f)
        pickle.dump([event], f)

    span_h = 0.0
    if event.comments:
        ts = [c.time_flag for c in event.comments]
        span_h = (max(ts) - min(ts)).total_seconds() / 3600.0

    stats = {
        "id": sid, "label": label, "subreddit": sr, "topic": event.topic,
        "method": "nmf",
        "n_comments_total": len(rec["comments"]),
        "n_comments_used": len(event.comments),
        "n_authors": len(users), "n_aspects": len(aspects), "aspects": aspects,
        "avg_pairs_per_comment": round(n_pairs / max(1, len(event.comments)), 3),
        "comments_with_pairs": sum(1 for c in event.comments if c.aspect_opinion_pairs),
        "span_hours": round(span_h, 1), "snapshot": os.path.relpath(snap, HERE),
    }
    return event, stats

def main():
    all_stats, event_rows, profiles = [], [], {}
    for idx, (sid, label) in enumerate(THREADS):
        event, stats = process_thread(sid, label)
        all_stats.append(stats)
        event_rows.append({"ID": idx, "Topic": event.topic, "Content": event.content[:1500],
                           "Aspects": ",".join(event.aspects),
                           "Published Date Time Flag": event.publishedAt.strftime("%Y-%m-%dT%H:%M:%SZ")})
        print(f"[{sid}] {label} (r/{stats['subreddit']}): {stats['n_comments_used']} comments, "
              f"{stats['n_authors']} authors, {stats['n_aspects']} aspects, span {stats['span_hours']}h")
        print(f"   aspects: {', '.join(event.aspects)}")
        with open(os.path.join(SNAP_DIR, f"snapshot_reddit_{sid}.pkl"), "rb") as f:
            users = pickle.load(f)
        for u in users:
            profiles[f"{sid}:{u.id}"] = {"ID": f"{sid}:{u.id}", "Author": u.id, "Thread": sid,
                                         "Source": f"reddit_{stats['subreddit']}"}

    with open(os.path.join(DS_DIR, "Event_reddit.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["ID", "Topic", "Content", "Aspects", "Published Date Time Flag"])
        w.writeheader(); w.writerows(event_rows)
    with open(os.path.join(DS_DIR, "Profile_reddit.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["ID", "Author", "Thread", "Source"])
        w.writeheader(); w.writerows(profiles.values())
    with open(os.path.join(DS_DIR, "reddit_dataset_stats.json"), "w", encoding="utf-8") as f:
        json.dump(all_stats, f, ensure_ascii=False, indent=2)
    print(f"\nSaved Event_reddit.csv ({len(event_rows)}), Profile_reddit.csv ({len(profiles)}), reddit_dataset_stats.json")

if __name__ == "__main__":
    main()
