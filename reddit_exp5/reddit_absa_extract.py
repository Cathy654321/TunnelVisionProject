
import os, json, time, hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed

from reddit_config import PKG, DATA
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(PKG), ".env"), override=True)
except Exception:
    pass

SCHEMA_DIR = os.path.join(PKG, "aspect_schemas")
CACHE_DIR = os.path.join(DATA, "absa_cache")
os.makedirs(CACHE_DIR, exist_ok=True)

MODEL = "gpt-5-mini"
PROMPT_VERSION = "absa-acsa-1"
SENT2SCORE = {"positive": 1.0, "neutral": 0.0, "negative": -1.0}


def _create_kwargs(model):
    if model.startswith(("gpt-5", "o1", "o3", "o4")):
        return {"reasoning_effort": "minimal", "max_completion_tokens": 2000}
    return {"temperature": 0, "max_tokens": 600}


_CREATE_KW = _create_kwargs(MODEL)

_SYSTEM = (
    "You are a careful aspect-based sentiment annotator. You are given a FIXED list of "
    "ASPECTS (each an evaluable attribute of one event) and a single Reddit comment. "
    "Identify which of the listed aspects the comment expresses an opinion or stance toward, "
    "and the sentiment toward EACH such aspect INDEPENDENTLY -- a comment can be positive "
    "about one aspect and negative about another in the same breath. "
    "Rules: (1) use ONLY aspect names from the provided list, copied verbatim; never invent "
    "aspects. (2) sentiment is the commenter's stance toward that aspect: 'positive' = "
    "favorable/supportive/satisfied/in-favor; 'negative' = unfavorable/critical/dissatisfied/"
    "opposed; 'neutral' = addressed with no clear valence or a balanced view. (3) include an "
    "aspect ONLY if the comment genuinely takes a stance on it (explicit or clearly implicit); "
    "do not pad. (4) if the comment is a joke, off-topic, a pure factual aside, or addresses "
    "no listed aspect, return an empty list. "
    "Return STRICT JSON: {\"pairs\": [{\"aspect\": \"<exact name>\", "
    "\"sentiment\": \"positive|neutral|negative\", \"evidence\": \"<short verbatim span>\"}]}"
)


def load_schema(sid):
    with open(os.path.join(SCHEMA_DIR, f"{sid}.json"), encoding="utf-8") as f:
        s = json.load(f)
    s["_names"] = [a["name"] for a in s["aspects"]]
    s["_nameset"] = set(s["_names"])
    return s


def _schema_block(schema):
    lines = [f"Event: {schema['event_title']}", "Aspects (name: definition):"]
    for a in schema["aspects"]:
        lines.append(f"- {a['name']}: {a['definition']}")
    return "\n".join(lines)


def _cache_path(sid):
    return os.path.join(CACHE_DIR, f"{sid}__{MODEL}.json")


def _load_cache(sid):
    p = _cache_path(sid)
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    return {}


def _key(body, schema):
    h = hashlib.sha256()
    h.update((body + "||" + schema["schema_version"] + "||" + MODEL + "||" + PROMPT_VERSION).encode("utf-8"))
    return h.hexdigest()


def _client():
    from openai import OpenAI
    return OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))


def _label_one(client, body, schema):
    user = _schema_block(schema) + "\n\nComment:\n\"\"\"\n" + body[:4000] + "\n\"\"\"\n\nReturn the JSON."
    for attempt in range(4):
        try:
            r = client.chat.completions.create(
                model=MODEL, response_format={"type": "json_object"},
                messages=[{"role": "system", "content": _SYSTEM},
                          {"role": "user", "content": user}],
                **_CREATE_KW,
            )
            raw = json.loads(r.choices[0].message.content)
            out, seen = [], set()
            for p in raw.get("pairs", []):
                a = (p.get("aspect") or "").strip()
                s = (p.get("sentiment") or "").strip().lower()
                if a in schema["_nameset"] and s in SENT2SCORE and a not in seen:
                    seen.add(a)
                    out.append({"aspect": a, "sentiment": s, "evidence": (p.get("evidence") or "")[:240]})
            return out
        except Exception as e:
            if attempt == 3:
                raise RuntimeError(f"label failed after retries: {e}")
            time.sleep(1.5 * (attempt + 1))


def label_comments(bodies, sid, workers=8, verbose=True):
    schema = load_schema(sid)
    cache = _load_cache(sid)
    keys = [_key(b, schema) for b in bodies]
    todo = [(i, b, k) for i, (b, k) in enumerate(zip(bodies, keys)) if k not in cache]
    if verbose:
        print(f"[{sid}] {len(bodies)} comments, {len(todo)} to label ({len(bodies)-len(todo)} cached)", flush=True)
    if todo:
        client = _client()
        done, failed = 0, 0
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futs = {ex.submit(_label_one, client, b, schema): (i, k) for i, b, k in todo}
            for fut in as_completed(futs):
                i, k = futs[fut]
                try:
                    cache[k] = fut.result()
                except Exception as e:
                    failed += 1
                    if failed <= 3:
                        print(f"   [warn] {e}", flush=True)
                done += 1
                if verbose and done % 25 == 0:
                    print(f"   labeled {done}/{len(todo)} ({failed} failed)", flush=True)
        with open(_cache_path(sid), "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False)
        if verbose:
            print(f"   saved cache -> {os.path.basename(_cache_path(sid))} ({failed} failed)", flush=True)
    return [cache.get(k, []) for k in keys]


def absa_aspects(comments, sid, max_per_comment=3, workers=8, verbose=True):
    schema = load_schema(sid)
    bodies = [c["body"] for c in comments]
    labeled = label_comments(bodies, sid, workers=workers, verbose=verbose)
    pairs_per_comment = []
    for body, recs in zip(bodies, labeled):
        pl = []
        for r in recs[:max_per_comment] if max_per_comment else recs:
            pl.append({"aspect": r["aspect"],
                       "opinion": (r.get("evidence") or body)[:240],
                       "score": SENT2SCORE[r["sentiment"]]})
        pairs_per_comment.append(pl)
    return schema["_names"], pairs_per_comment
