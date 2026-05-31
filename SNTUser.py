import utils_common
import utils_llm_manager
import json
import contractions
import utils_sentiment_analysis
import algorithm_collections
from Comment import Comment
import random
from collections import Counter

class SNTUser:
    all_sentiments = ["positive", "neutral", "negative"]

    def __init__(self, user_id, active_rate=0.5, stubbornness=0.5):
        self.id = user_id
        self.profile_text = ""
        self.profile = {}
        self.active_rate = active_rate
        self.stubbornness = stubbornness
        self.received = []
        self.posted = []
        self.strategy_mitigation = 'No'
        self.strategy_budget = 0
        self.mitigation_ratio = 1.0

    def __setstate__(self, state):
        self.__dict__.update(state)

        if 'strategy_mitigation' not in self.__dict__:
            self.strategy_mitigation = 'No'
        if 'strategy_budget' not in self.__dict__:
            self.strategy_budget = 0
        if 'mitigation_ratio' not in self.__dict__:
            self.mitigation_ratio = 1.0

    def post_comment(self, event, window_size=5):

        if not utils_common.check_random_threshold(self.active_rate):

            return

        aspect_count = random.randint(1, 3)

        prompt = (f"Act as the person with the profile: {self.profile_text}. \n"
                  f"Join the discussion on the topic: {event.topic}. \n"
                  f"You can see the recent discussions: \n {event.get_last_few_comments_text(window_size)}. \n"
                  f"Please choose {aspect_count} aspects from: {event.aspects} and provide your personal opinion towards each of your chosen aspects. \n "
                  f"No neutral opinions. \n"
                  f"Only return the aspect-opinion pairs in the following format: \n"
                  f"An array of dictionaries, where each dictionary contains a single 'aspect' key (the chosen aspect) and its corresponding 'opinion' value. \n"
                  f"Example of the required output format: [{{aspect': 'aspect1', 'opinion': 'opinion1'}}, {{'aspect': 'aspect2', 'opinion': 'opinion2'}}]. \n"
                  f"Return the array of dictionaries only, no other text or explanation.")
        print(prompt)
        print("============================")
        answer = ""
        try:
            answer = utils_llm_manager.GPT_Response(prompt=prompt, model="gpt-4o", max_tokens=500, temperature=0.2)

            answer = contractions.fix(answer).strip()
            answer = answer.replace("'", '"')
            answer = answer.replace("json", '')
            answer = answer.replace("```", '')
            answer = answer.replace("\n", '')

            aspect_opinion_pairs = json.loads(answer)

            for entry in aspect_opinion_pairs:
                entry['score'] = utils_sentiment_analysis.get_vader_sentiment_score(entry['opinion'])

            comment = Comment(from_user=self, to_event=event)

            comment.text = answer
            comment.aspect_opinion_pairs = aspect_opinion_pairs

            self.posted.append(comment)
            event.comments.append(comment)

        except Exception as e:
            print(f"Exception occured: {e}")
            print(f"Answer from GPT: {answer}")

    def post_comment_bayesian(self, event, window_size=20, max_aspects=3):
        if not utils_common.check_random_threshold(self.active_rate):
            return

        user_view = event.get_last_few_comments(window_size)

        if self.strategy_mitigation != 'No' and random.random() < self.mitigation_ratio:
            if self.strategy_mitigation == 'add':
                user_view = algorithm_collections.tv_mitigation_add(
                    user=self, event=event, user_view=user_view, budget=self.strategy_budget
                )
            elif self.strategy_mitigation == 'remove':
                user_view = algorithm_collections.tv_mitigation_remove(
                    user=self, event=event, user_view=user_view, budget=self.strategy_budget
                )
            elif self.strategy_mitigation == 'update':
                user_view = algorithm_collections.tv_mitigation_update(
                    user=self, event=event, user_view=user_view, budget=self.strategy_budget
                )
            elif self.strategy_mitigation == 'hybrid':
                user_view = algorithm_collections.tv_mitigation_hybrid(
                    user=self, event=event, user_view=user_view, budget=self.strategy_budget
                )
            elif self.strategy_mitigation == 'summarize':
                user_view = algorithm_collections.tv_mitigation_summarize(
                    user=self, event=event, user_view=user_view, budget=self.strategy_budget
                )

        aspect_opinion_pairs = self.post_and_feedback_bayesian(
            event_aspects=event.aspects, user_view=user_view, max_aspects=max_aspects)

        comment = Comment(from_user=self, to_event=event)
        comment.text = "\n".join([pair['opinion'] for pair in aspect_opinion_pairs])
        comment.aspect_opinion_pairs = aspect_opinion_pairs
        self.posted.append(comment)
        event.comments.append(comment)

    def post_and_feedback_bayesian(self, event_aspects, user_view, max_aspects=3):

        aspect_counter = Counter()

        for c in getattr(self, "posted", []):
            pairs = getattr(c, "aspect_opinion_pairs", []) or []
            for p in pairs:
                a = p.get("aspect")
                if a in event_aspects:
                    aspect_counter[a] += 1

        alpha = 0.5

        total_aspect_mentions = sum(aspect_counter.values())
        K_alpa = len(event_aspects)

        P_a = {
            a: (aspect_counter[a] + alpha) / (total_aspect_mentions + alpha * K_alpa)
            for a in event_aspects
        }

        external_evidence_count = {a: 0 for a in event_aspects}
        for c in user_view:
            for pair in getattr(c, 'aspect_opinion_pairs', []):
                if pair.get('aspect') in event_aspects:
                    external_evidence_count[pair['aspect']] += 1

        total_external_evidence = sum(external_evidence_count.values())

        beta = 0.5
        K_beta = len(event_aspects)
        P_e_given_a = {
            a: (external_evidence_count[a] + beta) / (total_external_evidence + beta * K_beta)
            for a in event_aspects
        }

        balance_weight = 1.5
        norm_const = sum((P_e_given_a[a] ** balance_weight) * P_a[a] for a in event_aspects)
        P_a_given_e = {
            a: (P_e_given_a[a] ** balance_weight) * P_a[a] / norm_const
            for a in event_aspects
        }

        num_aspects_to_choose = min(max_aspects, len(event_aspects))
        chosen_aspects = self._weighted_sample_multiple(P_a_given_e, num_aspects_to_choose)

        aspect_opinion_pairs = []

        for chosen_aspect in chosen_aspects:

            sent_counter = Counter()

            for c in getattr(self, "posted", []):
                pairs = getattr(c, "aspect_opinion_pairs", []) or []
                for p in pairs:
                    if p.get("aspect") != chosen_aspect:
                        continue

                    score = p.get("score", None)
                    if score is None:
                        continue

                    s = SNTUser._map_score_to_sentiment(float(score))
                    if s in SNTUser.all_sentiments:
                        sent_counter[s] += 1

            total_sent = sum(sent_counter.values())

            if total_sent > 0:
                P_s_given_a = {s: sent_counter[s] / total_sent for s in SNTUser.all_sentiments}
            else:
                P_s_given_a = {s: 1 / len(SNTUser.all_sentiments) for s in SNTUser.all_sentiments}

            external_evidence_sentiment_count = {s: 0 for s in SNTUser.all_sentiments}
            for c in user_view:
                for pair in getattr(c, 'aspect_opinion_pairs', []):
                    if pair.get('aspect') == chosen_aspect:
                        score = pair.get('score', 0.0)
                        s = self._map_score_to_sentiment(score)
                        external_evidence_sentiment_count[s] += 1

            total_s_external_evidence = sum(external_evidence_sentiment_count.values())
            P_e_given_s_a = {
                s: (external_evidence_sentiment_count[s] / total_s_external_evidence) if total_s_external_evidence > 0 else 1 / len(
                    SNTUser.all_sentiments)
                for s in SNTUser.all_sentiments}

            norm_const_s = sum(P_e_given_s_a[s] * P_s_given_a[s] for s in SNTUser.all_sentiments)

            if norm_const_s <= 0:

                P_s_given_a_e = dict(P_s_given_a)
            else:
                P_s_given_a_e = {s: P_e_given_s_a[s] * P_s_given_a[s] / norm_const_s for s in SNTUser.all_sentiments}

            chosen_sentiment = self._weighted_sample(P_s_given_a_e)
            opinion_text = f"I think the aspect '{chosen_aspect}' is {chosen_sentiment}."
            score = self._map_sentiment_to_score(chosen_sentiment)

            aspect_opinion_pairs.append({
                'aspect': chosen_aspect,
                'opinion': opinion_text,
                'score': score
            })

        return aspect_opinion_pairs

    @staticmethod
    def _weighted_sample(prob_dict):
        items = list(prob_dict.items())
        keys = [k for k, _ in items]
        weights = [v for _, v in items]
        total = sum(weights)
        normalized_weights = [w / total for w in weights]
        return random.choices(keys, weights=normalized_weights, k=1)[0]

    @staticmethod
    def _weighted_sample_multiple(prob_dict, k):

        items = list(prob_dict.items())
        keys = [k for k, _ in items]
        weights = [v for _, v in items]
        total = sum(weights)
        normalized_weights = [w / total for w in weights]

        selected = []
        while len(selected) < k and keys:
            choice = random.choices(keys, weights=normalized_weights, k=1)[0]
            selected.append(choice)
            index = keys.index(choice)
            del keys[index]
            del normalized_weights[index]
            if sum(normalized_weights) > 0:
                normalized_weights = [w / sum(normalized_weights) for w in normalized_weights]
        return selected

    @staticmethod
    def _map_score_to_sentiment(score):
        if score > 0.1:
            return "positive"
        elif score < -0.1:
            return "negative"
        else:
            return "neutral"

    @staticmethod
    def _map_sentiment_to_score(sentiment):
        return {"positive": 0.8, "negative": -0.8, "neutral": 0.0}[sentiment]
