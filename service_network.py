from SNTPlatform import SNTPlatform
from utils_data_manager import DataManager
import analysis_vis_results
from analysis_analyzer import Analyzer
import matplotlib

matplotlib.use('TkAgg')
import matplotlib.pyplot as plt

def build_network(event_data='./datasets/Event_standard.csv',
                  profile_data='./datasets/Profile_students.csv'):

    network = SNTPlatform()
    network.load_events(event_data=event_data)
    network.load_users(profile_data=profile_data)
    return network

def network_simulations(network, number_of_interation=10, save_the_simulation_snapshot=False,
                        each_user_comment_aspect_count=1, user_vision_window_size=30):

    network.load_snapshot(network.SNAPSHOT_ALL)

    for event_index in range(0, len(network.events)):

        network.simulate_comments(event_index=event_index,
                                  k=number_of_interation,
                                  is_save=save_the_simulation_snapshot,
                                  max_aspects=each_user_comment_aspect_count,
                                  window_size=user_vision_window_size)

        analyser = Analyzer(event=network.events[event_index])

        comments_length = len(network.events[event_index].comments)
        index = 0
        results = []

        for i in range(100, comments_length, 100):
            result = analyser.calculate_aspe_case(start_from=i, window_length=100 + (index * 100))
            index += 1
            print(f"round:{index} -  {result}")
            results.append(result)

        analysis_vis_results.plot_case_results(results)

def network_generations(network, event_id):
    if event_id == 'all':
        for event_index in range(0, len(network.events)):
            print(f"======= Event {event_index} starts =========")
            network.generate_comments(event_index=event_index, is_save=True, k=20)
    else:
        network.generate_comments(event_index=event_id, is_save=True, k=20)

def read_network(network, network_file_pkl, event_id=0, snapshot_or_simulation='simulation'):

    if snapshot_or_simulation == 'simulation':
        network.load_snapshot_simulation(network_file_pkl)
    else:
        network.load_snapshot(network_file_pkl)
    index = 0
    results = []
    analyser = Analyzer(event=network.events[event_id])

    for i in range(1, 1000, 5):
        result = analyser.calculate_aspe_case(start_from=i, window_length=None)
        index += 1
        result["round"] = index
        print(result)
        results.append(result)

    analysis_vis_results.plot_case_results(results)

if __name__ == '__main__':
    network = build_network()
    print(network.SNAPSHOT_ALL)

