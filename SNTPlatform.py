import os

from Event import Event
import utils_common
import pickle
from SNTUser import SNTUser

class SNTPlatform:

    SNAPSHOT_PATH = "./snapshots/"

    SIMULATION_PATH = "./simulations/"

    SNAPSHOT_ALL = "snapshot_all_2025_april_llm.pkl"

    def __init__(self):
        self.users = []
        self.events = []
        self.current_snapshot = ""
        self.mitigation_strategy = {}

    def load_users(self, profile_data):
        entries = utils_common.csv_to_dict_list_str(profile_data)
        for entry in entries:
            user = SNTUser(user_id=entry['ID'])
            user.profile = entry
            user.profile_text = utils_common.profile_to_text(entry)
            self.users.append(user)

    def deploy_strategy(self, mitigation_strategy):
        self.mitigation_strategy = mitigation_strategy
        for user in self.users:
            user.strategy_mitigation = mitigation_strategy['strategy_mitigation']
            user.strategy_budget = mitigation_strategy['strategy_budget']
            user.mitigation_ratio = mitigation_strategy['mitigation_ratio']

    def load_events(self, event_data):
        entries = utils_common.csv_to_dict_list_str(event_data)
        for entry in entries:
            event = Event(event_id=entry["ID"])
            event.topic = entry["Topic"]
            event.content = entry["Content"]
            event.aspects = entry["Aspects"].split(',')
            event.publishedAt = utils_common.convert_str_to_datetime(entry["Published Date Time Flag"])
            self.events.append(event)

    def save_snapshot(self, suffix="", is_simulation=False):
        filename = "snapshot_" + utils_common.get_time_stamp() + suffix + ".pkl"
        if is_simulation:
            full_path = self.SIMULATION_PATH + filename
        else:
            full_path = self.SNAPSHOT_PATH + filename

        try:
            with open(full_path, 'wb') as file:
                pickle.dump(self.users, file)
                pickle.dump(self.events, file)
            print(filename + " has been saved")
            self.current_snapshot = filename
        except Exception as e:
            print(f"Error saving data: {e}")

    def load_snapshot(self, filename):

        try:
            with open(SNTPlatform.SNAPSHOT_PATH + filename, 'rb') as file:
                self.users = pickle.load(file)
                self.events = pickle.load(file)
                self.current_snapshot = filename
            print("Snapshots loaded successfully.")
        except Exception as e:
            print(f"Error loading data: {e}")

    def load_snapshot_simulation(self, filename):

        try:
            with open(SNTPlatform.SIMULATION_PATH + filename, 'rb') as file:
                self.users = pickle.load(file)
                self.events = pickle.load(file)
                self.current_snapshot = filename
            print("Simulation Snapshots loaded successfully.")
        except Exception as e:
            print(f"Error loading data: {e}")

    def clear_network(self):
        self.users = []
        self.events = []
        self.current_snapshot = ""

    def start_discussion(self, event_index=2):
        selected_event = self.events[event_index]
        for user in self.users:
            user.post_comment(event=selected_event, window_size=6)

    def generate_comments(self, event_index, k=10, is_save=False):

        for i in range(k):
            self.start_discussion(event_index=event_index)
            print(f"******** Event {event_index} Discussions: Iteration {i + 1} out of {k} is completed! *********")
        if is_save:
            self.save_snapshot(suffix=f"event{event_index}_LLM_total_iter_{k}")

    def simulate_comments(self, event_index, k=500, window_size=10, max_aspects=2, is_save=False):

        for i in range(k):
            for j in range(len(self.users)):
                self.users[j].post_comment_bayesian(event=self.events[event_index], window_size=window_size,
                                                    max_aspects=max_aspects)
            print('Progress ===== ', i, ' of ', k, ' is completed!!')
        if is_save:
            self.save_snapshot(suffix=f"event{event_index}_Bayes_W{window_size}_Aspects{max_aspects}",
                               is_simulation=True)
