import json
import os
from datetime import datetime

def get_today_filename(name):
    today = datetime.now().strftime("%Y-%m-%d")
    return f"data/{name}_{today}.json"

def save_json_data(name, data):
    filename = get_today_filename(name)
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_json_data(name):
    filename = get_today_filename(name)
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    return []
