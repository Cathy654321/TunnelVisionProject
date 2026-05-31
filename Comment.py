from datetime import datetime

class Comment:
    def __init__(self, from_user, to_event):
        self.from_user = from_user
        self.to_event = to_event
        self.text = ""
        self.aspect_opinion_pairs = []
        self.time_flag = datetime.now()

    def __str__(self):

        return "; ".join(

            [f"I talk about {pair['aspect']} with an sentiment score of {pair['score']}" for pair in
             self.aspect_opinion_pairs])
