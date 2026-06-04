import pickle

class DataManager:
    EVENT_COMMENTS_FILE = "event_comments.txt"

    def __init__(self):
        self.users = []
        self.events = []

    def save_to_file(self, filename):

        try:
            with open(filename, 'wb') as file:
                pickle.dump(self.users, file)
                pickle.dump(self.events, file)
            print("Data saved successfully.")
        except Exception as e:
            print(f"Error saving data: {e}")

    def load_from_file(self, filename):

        try:
            with open(filename, 'rb') as file:
                self.users = pickle.load(file)
                self.events = pickle.load(file)
            print("Data loaded successfully.")
        except Exception as e:
            print(f"Error loading data: {e}")

    def save_event_comments_to_file(events, filename=EVENT_COMMENTS_FILE):
        with open(filename, "w", encoding="utf-8") as f:
            for event in events:
                f.write(f"Event ID: {event.event_id}\n")
                f.write(f"Topic: {event.topic}\n")
                f.write(f"Content: {event.content}\n")
                f.write(f"Published At: {event.publishedAt.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Aspects Mentioned: {', '.join(event.aspects)}\n")
                f.write("Comments:\n")

                if not event.comments:
                    f.write("  No comments yet.\n")
                else:
                    for comment in event.comments:
                        f.write(f"  From: {comment.from_user.id}, Profile: {comment.from_user.profile_text} \n")
                        if comment.text:
                            f.write(f"    Text: {comment.text}\n")
                        for pair in comment.aspect_opinion_pairs:
                            aspect = pair.get("aspect", "N/A")
                            opinion = pair.get("opinion", "N/A")
                            score = pair.get("score", "N/A")
                            f.write(f"    - Aspect: {aspect}, Opinion: {opinion}, Sentiment Score: {score}\n")
                        f.write(f"    Commented At: {comment.time_flag.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("\n" + "-" * 50 + "\n\n")

        print(f"Comments have been saved to {filename}")
