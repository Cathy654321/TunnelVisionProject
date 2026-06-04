from datetime import datetime

class Event:
    def __init__(self, event_id):
        self.event_id = event_id
        self.topic = ""
        self.content = ""
        self.publishedAt = datetime.now()
        self.comments = []
        self.aspects = []

    def get_last_few_comments(self, k):
        if not self.comments:
            return []
        return self.comments[-k:] if k <= len(self.comments) else self.comments

    def get_last_few_comments_text(self, k):
        obtained_comments = self.get_last_few_comments(k)
        long_comment_text = ""
        for comment in obtained_comments:
            long_comment_text += str(comment).strip() + "\n"

        return long_comment_text
