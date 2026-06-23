from datetime import datetime, timezone

BOTS = ("AutoModerator", "[deleted]")


def usable(c):
    b = (c.get("body") or "").strip()
    if not b or b in ("[removed]", "[deleted]"):
        return False
    if (c.get("author") or "") in BOTS:
        return False
    return True


def to_dt(utc):
    try:
        return datetime.fromtimestamp(int(utc), tz=timezone.utc).replace(tzinfo=None)
    except Exception:
        return datetime.now()
