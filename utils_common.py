import csv
import random
from datetime import datetime

def convert_str_to_datetime(str_datetime):
    format_str = "%Y-%m-%dT%H:%M:%SZ"
    return datetime.strptime(str_datetime, format_str)

def csv_to_dict_list(file_path):

    entries = []
    try:
        with open(file_path, mode='r', encoding='utf-8') as csv_file:
            reader = csv.DictReader(csv_file)
            for row in reader:
                entries.append(dict(row))
    except Exception as e:
        print(f"Error reading CSV file: {e}")
    return entries

def csv_to_dict_list_str(file_path):

    entries = []
    try:
        with open(file_path, mode='r', encoding='utf-8') as csv_file:
            reader = csv.DictReader(csv_file)
            for row in reader:
                entries.append(dict(row))
    except Exception as e:
        print(f"Error reading CSV file: {e}")
    return entries

def save_results_to_csv(results, filename='results.csv'):

    if not results:
        print("No results to save.")
        return

    fieldnames = list(results[0].keys())

    with open(filename, mode='w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for row in results:
            writer.writerow(row)

    print(f"Results saved to '{filename}'")

def profile_to_text(profile):

    return ", ".join([f"{key}: {value}" for key, value in profile.items()])

def check_random_threshold(threshold: float) -> bool:

    random_number = random.random()
    return random_number < threshold

def get_time_stamp():
    current_timestamp = datetime.now()
    return current_timestamp.strftime("%Y_%m_%d_%H_%M_%S")

if __name__ == "__main__":

    entries = csv_to_dict_list_str("./datasets/Profile_students.csv")
    print("Converted Entries:")
    for entry in entries:
        print(entry)

    for entry in entries:
        print(profile_to_text(entry))
