import re
from collections import Counter
from datetime import datetime, timezone
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

MIN_TERM_LEN = 3
_VADER = SentimentIntensityAnalyzer()

STOP = set("""
a about above after again against all am an and any are aren't as at be because been before being
below between both but by can can't cannot could couldn't did didn't do does doesn't doing don't down
during each few for from further had hadn't has hasn't have haven't having he he'd he'll he's her here
here's hers herself him himself his how how's i i'd i'll i'm i've if in into is isn't it it's its itself
let's me more most mustn't my myself no nor not of off on once only or other ought our ours ourselves out
over own same shan't she she'd she'll she's should shouldn't so some such than that that's the their theirs
them themselves then there there's these they they'd they'll they're they've this those through to too under
until up very was wasn't we we'd we'll we're we've were weren't what what's when when's where where's which
while who who's whom why why's with won't would wouldn't you you'd you'll you're you've your yours yourself
yourselves get got would also really like just dont im youre thats theyre would even much many one two
get really going make want know think people thing things said say says going lot way time even still
yta nta esh nah info aita reddit edit op also would could really like just dont cant im youre thats gonna
now will sounds sound see seen something someone anything anyone thing things way ways lot back next right
needs need said say says getting makes made goes went come came want wanted tell told give gave put takes
don doesnt didnt isnt wasnt werent arent wont wouldnt couldnt shouldnt havent hasnt ive id ill hes shes its
lets wanna kinda sorta yeah yep nope maybe probably actually pretty well good bad sure okay ok let made use
look looks looking feels felt seems seem thats theyve youve weve gotta na ta op's year day years days person
asshole ass shit shitty dick fuck fucking fucked bitch crap damn hell jerk piece stupid idiot dumb
situation deal big though else stuff kind sort bit point part case reason fact guy guys feel man
sounds anyway anymore whatever everybody nobody everyone somebody having little
never ever happen happens happening always saying every anyhow somehow honestly basically literally
serious seriously first second third already almost enough across along
lol lmao lmfao rofl roflmao omg omfg wtf wth lmaoo lmaooo haha hahaha hahah hah heh hehe hmm hmmm
yeah yep yup nope meh ugh oof uwu wee weee wow woah whoa god gods jesus christ holy please thanks
thank thx yikes bruh bro dude love hate great wonderful awesome terrible amazing cool fine boring
new take long last best mean different believe agree gonna wanna goes able
""".split())

def clean_tokens(text):
    text = text.lower()
    text = re.sub(r"http\S+|www\.\S+", " ", text)
    text = re.sub(r"[^a-z']+", " ", text)
    toks = [t.strip("'") for t in text.split()]
    return [t for t in toks if len(t) >= MIN_TERM_LEN and t not in STOP]

def sentences(text):
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", text) if s.strip()]

def vader(text):
    return _VADER.polarity_scores(text)["compound"]

def usable(c):
    b = (c.get("body") or "").strip()
    if not b or b in ("[removed]", "[deleted]"):
        return False
    if (c.get("author") or "") in ("AutoModerator", "[deleted]"):
        return False
    return True

def to_dt(utc):
    try:
        return datetime.fromtimestamp(int(utc), tz=timezone.utc).replace(tzinfo=None)
    except Exception:
        return datetime.now()

def _stem(w):
    for suf in ("ing", "ed", "es", "s"):
        if w.endswith(suf) and len(w) - len(suf) >= 3:
            return w[: -len(suf)]
    return w

def build_aspects(comments, n_aspects=14, name_cap_ratio=0.75, min_name_occ=5):

    df = Counter(); total = Counter(); capc = Counter()
    for c in comments:
        raw = c["body"]
        toks = clean_tokens(raw)
        uni = set(toks)
        bi = set(f"{toks[i]} {toks[i+1]}" for i in range(len(toks) - 1))
        for t in uni | bi:
            df[t] += 1
        for w in re.findall(r"[A-Za-z']+", raw):
            lw = w.lower().strip("'")
            if len(lw) >= MIN_TERM_LEN:
                total[lw] += 1
                if w[:1].isupper():
                    capc[lw] += 1

    def is_name(term):
        tot = total.get(term, 0)
        return tot >= min_name_occ and capc.get(term, 0) / tot >= name_cap_ratio

    ranked = sorted(df.items(), key=lambda kv: (kv[1], len(kv[0].split())), reverse=True)
    chosen, chosen_stems, chosen_pref, dropped = [], set(), set(), []
    for term, _ in ranked:
        parts = term.split()
        if len(parts) == 1:
            if is_name(term):
                if term not in dropped:
                    dropped.append(term)
                continue
            st = _stem(term)
            pref = term[:5] if len(term) >= 6 else None

            if st in chosen_stems or (pref is not None and pref in chosen_pref):
                continue
            chosen.append(term); chosen_stems.add(st)
            if pref is not None:
                chosen_pref.add(pref)
        else:
            if any(is_name(p) for p in parts):
                continue
            stems = [_stem(p) for p in parts]
            if all(s in chosen_stems for s in stems):
                continue
            chosen.append(term); chosen_stems.update(stems)
        if len(chosen) >= n_aspects:
            break
    disp = [" ".join(w.capitalize() for w in t.split()) for t in chosen]
    return disp, dropped

def comment_pairs(body, aspects_lc, max_aspects=3):

    toks = clean_tokens(body)
    tokset = set(toks)
    biset = set(f"{toks[i]} {toks[i+1]}" for i in range(len(toks) - 1))
    sents = sentences(body)
    pairs = []
    for disp, lc in aspects_lc:
        present = (lc in tokset) if " " not in lc else (lc in biset)
        if not present:
            continue
        host = next((s for s in sents if lc in s.lower()), None)
        score = vader(host) if host else vader(body)
        pairs.append({"aspect": disp, "opinion": (host or body)[:240], "score": round(score, 4)})
    pairs.sort(key=lambda p: abs(p["score"]), reverse=True)
    return pairs[:max_aspects]

def _nmf_unique_labels(top_terms_per_topic, max_terms=3):

    labels = []
    used = set()
    for tt in top_terms_per_topic:
        picked, seen = [], set()
        for t in tt:
            ws = t.split()
            if all(w in seen for w in ws):
                continue
            picked.append(t); seen.update(ws)
            if len(picked) >= max_terms:
                break
        lab = " / ".join(" ".join(w.capitalize() for w in p.split()) for p in picked) or "Topic"
        base, j = lab, 2
        while lab in used:
            extra = next((t for t in tt if t not in base.lower()), None)
            lab = f"{base} / {extra.title()}" if extra else f"{base} ({j})"; j += 1
        used.add(lab); labels.append(lab)
    return labels

def nmf_aspects(comments, n_aspects=12, max_per_comment=3, min_weight=0.15,
                min_df=4, max_df=0.5, max_features=2000, max_iter=400):

    import numpy as np
    from sklearn.feature_extraction.text import TfidfVectorizer, ENGLISH_STOP_WORDS
    from sklearn.decomposition import NMF

    def _clean(t):
        t = re.sub(r"http\S+|www\.\S+", " ", t)
        t = re.sub(r"&[a-z]+;", " ", t)
        t = re.sub(r"/?r/\w+|/?u/\w+", " ", t)
        return t

    texts = [_clean(c["body"]) for c in comments]
    web_stop = {"https", "http", "www", "com", "org", "net", "amp", "gt", "lt", "nbsp",
                "reddit", "edit", "deleted", "removed", "comment", "comments", "post",
                "posts", "title", "thread", "sub", "subreddit"}

    contr = {"didn", "doesn", "don", "wouldn", "couldn", "shouldn", "wasn", "weren", "isn",
             "aren", "hasn", "haven", "hadn", "won", "wont", "mustn", "shan", "ain", "ll",
             "ve", "re", "ya", "im", "id", "youre", "theyre", "thats", "gonna", "wanna"}
    stop = list(ENGLISH_STOP_WORDS | STOP | web_stop | contr)
    vec = TfidfVectorizer(stop_words=stop, ngram_range=(1, 2), min_df=min_df,
                          max_df=max_df, max_features=max_features)
    X = vec.fit_transform(texts)
    K = max(2, min(n_aspects, X.shape[1] - 1))
    model = NMF(n_components=K, init="nndsvda", max_iter=max_iter, random_state=0)
    Wd = model.fit_transform(X); H = model.components_
    terms = np.array(vec.get_feature_names_out())
    top_terms = [terms[H[k].argsort()[::-1][:8]].tolist() for k in range(K)]
    labels = _nmf_unique_labels(top_terms)
    pairs_per_comment = []
    for i, txt in enumerate(texts):
        w = Wd[i]
        if w.sum() <= 0:
            pairs_per_comment.append([]); continue
        wn = w / w.sum()
        order = list(wn.argsort()[::-1])
        chosen = [k for k in order if wn[k] >= min_weight][:max_per_comment] or [order[0]]
        sents = sentences(txt); low_sents = [s.lower() for s in sents]

        sc = round(vader(txt), 4)
        pl = []
        for k in chosen:
            host = None
            for term in top_terms[k]:
                hit = next((sents[j] for j, ls in enumerate(low_sents) if term in ls), None)
                if hit:
                    host = hit; break
            pl.append({"aspect": labels[k], "opinion": (host or txt)[:240], "score": sc})
        pairs_per_comment.append(pl)
    return labels, pairs_per_comment
