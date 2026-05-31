from analysis_analyzer import Analyzer
from Event import Event
from Comment import Comment

budget_applied_rate = 1.0

key_metrics = "CASE"

def tv_mitigation_add(user, event, user_view, budget):

    user.strategy_budget = budget
    if budget <= 0:
        return user_view

    base_view = user_view

    sentiment_scores = [0.6, -0.6]
    candidates = [{"aspect": a, "score": s} for a in event.aspects for s in sentiment_scores]

    injected_comments = []
    selected = set()

    def make_delta_comment(pairs):
        c = Comment(from_user=None, to_event=None)
        if getattr(c, "aspect_opinion_pairs", None) is None:
            c.aspect_opinion_pairs = []

        if isinstance(pairs, dict):
            c.aspect_opinion_pairs.append(pairs)
        else:
            c.aspect_opinion_pairs.extend(pairs)

        return c

    for step in range(budget):
        best_gain = float("-inf")
        best_candidate = None

        for cand in candidates:
            key = (cand["aspect"], cand["score"])
            if key in selected:
                continue

            temp_view = base_view + injected_comments + [make_delta_comment(cand)]

            delta_gain_obj = feedback_function_aspe_delta(
                base_view,
                temp_view,
                event.aspects
            )

            gain = delta_gain_obj.get(key_metrics, float("-inf"))
            if gain > best_gain:
                best_gain = gain
                best_candidate = cand

        if best_candidate is None or best_gain <= 0:
            break

        injected_comments.append(make_delta_comment(best_candidate))
        selected.add((best_candidate["aspect"], best_candidate["score"]))

    return base_view + injected_comments

def tv_mitigation_remove(user, event, user_view, budget):

    user.strategy_budget = budget
    if budget <= 0:
        return user_view

    base_view = user_view
    n = len(base_view)
    if n == 0:
        return user_view

    removed_idx = set()

    for step in range(min(budget, n)):
        best_gain = float("-inf")
        best_remove = None

        current_view = [c for i, c in enumerate(base_view) if i not in removed_idx]

        for i in range(n):
            if i in removed_idx:
                continue

            temp_view = [c for j, c in enumerate(base_view) if j not in removed_idx and j != i]

            delta_gain_obj = feedback_function_aspe_delta(
                base_view,
                temp_view,
                event.aspects
            )

            gain = delta_gain_obj.get(key_metrics, float("-inf"))
            if gain > best_gain:
                best_gain = gain
                best_remove = i

        if best_remove is None or best_gain <= 0:
            break

        removed_idx.add(best_remove)

    return [c for i, c in enumerate(base_view) if i not in removed_idx]

def tv_mitigation_update(user, event, user_view, budget):

    user.strategy_budget = budget
    if budget <= 0 or not user_view:
        return user_view

    base_view = user_view
    n = len(base_view)

    sentiment_scores = [0.6, -0.6]
    candidates = [{"aspect": a, "score": s} for a in event.aspects for s in sentiment_scores]

    def make_delta_comment(pair):
        c = Comment(from_user=None, to_event=None)
        if getattr(c, "aspect_opinion_pairs", None) is None:
            c.aspect_opinion_pairs = []
        c.aspect_opinion_pairs.append(pair)
        return c

    working = list(base_view)
    used_candidates = set()
    replaced_idx = set()

    for step in range(min(budget, n)):
        best_gain = float("-inf")
        best_idx = None
        best_cand = None

        for idx in range(n):
            if idx in replaced_idx:
                continue

            old_item = working[idx]

            for cand in candidates:
                key = (cand["aspect"], cand["score"])
                if key in used_candidates:
                    continue

                cand_comment = make_delta_comment(cand)

                working[idx] = cand_comment
                delta_gain_obj = feedback_function_aspe_delta(base_view, working, event.aspects)
                gain = delta_gain_obj.get(key_metrics, float("-inf"))

                working[idx] = old_item

                if gain > best_gain:
                    best_gain = gain
                    best_idx = idx
                    best_cand = cand

        if best_idx is None or best_gain <= 0:
            break

        working[best_idx] = make_delta_comment(best_cand)
        replaced_idx.add(best_idx)
        used_candidates.add((best_cand["aspect"], best_cand["score"]))

    return working

def tv_mitigation_hybrid(user, event, user_view, budget):

    user.strategy_budget = budget
    if budget <= 0:
        return user_view

    current_view = user_view
    aspects = event.aspects

    for step in range(budget):

        add_view = tv_mitigation_add(user, event, current_view, budget=1)
        remove_view = tv_mitigation_remove(user, event, current_view, budget=1)
        update_view = tv_mitigation_update(user, event, current_view, budget=1)

        gain_add = feedback_function_aspe_delta(current_view, add_view, aspects).get(key_metrics, float("-inf"))
        gain_remove = feedback_function_aspe_delta(current_view, remove_view, aspects).get(key_metrics, float("-inf"))
        gain_update = feedback_function_aspe_delta(current_view, update_view, aspects).get(key_metrics, float("-inf"))

        best_gain = max(gain_add, gain_remove, gain_update)

        if best_gain <= 0 or best_gain == float("-inf"):
            break

        if best_gain == gain_add:
            current_view = add_view
        elif best_gain == gain_remove:
            current_view = remove_view
        else:
            current_view = update_view

    return current_view

def tv_mitigation_summarize(user, event, user_view, budget):

    user.strategy_budget = budget

    base_view = user_view
    if not getattr(event, "comments", None):
        return base_view

    seen_comment_ids = {id(c) for c in base_view}

    unique_pairs = []
    seen_pair_keys = set()

    for c in event.comments:
        if id(c) in seen_comment_ids:
            continue

        for pair in getattr(c, "aspect_opinion_pairs", []) or []:
            aspect = pair.get("aspect")
            score = pair.get("score")
            if aspect is None or score is None:
                continue

            if score >= 0.1:
                score = 0.8
            elif score <= -0.1:
                score = -0.8
            else:
                score = 0.0

            key = (aspect, score)
            if key in seen_pair_keys:
                continue

            seen_pair_keys.add(key)
            unique_pairs.append({"aspect": aspect, "score": score})

    if not unique_pairs:
        return base_view

    unique_pairs.sort(key=lambda x: (str(x["aspect"]), float(x["score"])))

    if budget and budget > 0:
        unique_pairs = unique_pairs[:budget]

    summary_comment = Comment(from_user=None, to_event=None)
    if getattr(summary_comment, "aspect_opinion_pairs", None) is None:
        summary_comment.aspect_opinion_pairs = []
    summary_comment.aspect_opinion_pairs.extend(unique_pairs)

    return list(base_view) + [summary_comment]

def feedback_function_aspe_case(updated_user_view, event_aspects):
    event_hypothesis = Event(event_id=999)
    event_hypothesis.aspects = event_aspects
    event_hypothesis.comments = updated_user_view
    analyzer = Analyzer(event=event_hypothesis)
    return analyzer.calculate_aspe_case()

def feedback_function_aspe_delta(original_user_view, updated_user_view, event_aspects):
    event_hypothesis_original = Event(event_id=999)
    event_hypothesis_original.aspects = event_aspects
    event_hypothesis_original.comments = original_user_view
    analyzer_original = Analyzer(event=event_hypothesis_original)
    result_original = analyzer_original.calculate_aspe_case()

    event_hypothesis_updated = Event(event_id=1000)
    event_hypothesis_updated.aspects = event_aspects
    event_hypothesis_updated.comments = updated_user_view
    analyzer_updated = Analyzer(event=event_hypothesis_updated)
    result_updated = analyzer_updated.calculate_aspe_case()

    return {
        "ASPE": round(result_updated["ASPE"] - result_original["ASPE"], 4),
        "CASE": round(result_updated["CASE"] - result_original["CASE"], 4)
    }
