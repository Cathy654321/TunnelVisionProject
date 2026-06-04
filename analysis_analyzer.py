import math
from collections import defaultdict

class Analyzer:

    def __init__(self, event):
        self.all_sentiments = {"positive", "neutral", "negative"}
        self.delta = 0.1
        self.event = event

    def calculate_aspe_case(self, start_from=0, window_length=None, end_at=None):

        def normalize_sentiment(score):
            if isinstance(score, str):
                return score
            elif score > 0.1:
                return "positive"
            elif score < -0.1:
                return "negative"
            else:
                return "neutral"

        all_comments = self.event.comments
        start_from = max(0, int(start_from))

        if end_at is not None:
            end_at = min(len(all_comments), int(end_at))
            end_at = max(start_from, end_at)
            comments = all_comments[start_from:end_at]
        else:
            comments = all_comments[start_from:]

        if window_length is not None:
            window_length = max(0, int(window_length))
            comments = comments[:window_length]

        pair_freq = defaultdict(int)
        sentiment_freq = defaultdict(int)
        discussed_aspects = set()
        total_mentions = 0
        total_comments = len(comments)

        for comment in comments:
            for pair in comment.aspect_opinion_pairs:
                aspect = pair.get("aspect")
                sentiment = normalize_sentiment(pair.get("score"))
                if not aspect or not sentiment:
                    continue
                pair_freq[(aspect, sentiment)] += 1
                sentiment_freq[sentiment] += 1
                discussed_aspects.add(aspect)
                total_mentions += 1

        aspe = 0.0
        for freq in pair_freq.values():
            p = freq / total_mentions
            aspe -= p * math.log2(p)

        total_possible_aspects = len(self.event.aspects)
        covered_aspects = len(discussed_aspects)
        C = covered_aspects / total_possible_aspects if total_possible_aspects > 0 else 0

        k_total = len(self.all_sentiments)
        Cs_numerator = 0.0

        for sentiment in self.all_sentiments:
            freq = sentiment_freq.get(sentiment, 0)
            w_j = freq / (
                    self.delta * total_comments) if total_comments > 0 and freq >= self.delta * total_comments else 0
            Cs_numerator += min(w_j, 1)

        Cs = Cs_numerator / k_total if k_total > 0 else 0

        case = aspe * (0.3 + 0.7 * math.sqrt(C * Cs))

        return {
            "ASPE": round(aspe, 4),
            "AspectCoverage (C)": round(C, 4),
            "SentimentCoverage (Cs)": round(Cs, 4),
            "CASE": round(case, 4),
            "CommentsUsed": total_comments,
            "StartFrom": start_from,
            "EndAt": start_from + total_comments - 1
        }

