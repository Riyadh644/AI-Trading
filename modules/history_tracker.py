import os
import json
from datetime import datetime, timedelta

HISTORY_FILE = "data/history_performance.json"

def load_history():
    if not os.path.exists(HISTORY_FILE):
        return {}
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_history(data):
    os.makedirs("data", exist_ok=True)
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def record_result(symbol, result):
    data = load_history()
    symbol = symbol.upper()
    today = datetime.now().strftime("%Y-%m-%d")
    if symbol not in data:
        data[symbol] = {"history": [], "last_seen": today}
    data[symbol]["history"].append({"date": today, "result": result})
    data[symbol]["last_seen"] = today
    save_history(data)

def get_success_rate(symbol):
    data = load_history()
    symbol = symbol.upper()
    if symbol not in data or not data[symbol]["history"]:
        return None
    records = data[symbol]["history"]
    wins = sum(1 for r in records if r["result"] == "win")
    return round((wins / len(records)) * 100, 2)

def was_seen_recently(symbol, days=5):
    data = load_history()
    symbol = symbol.upper()
    if symbol not in data:
        return False
    last_date = datetime.strptime(data[symbol]["last_seen"], "%Y-%m-%d")
    return datetime.now() - last_date < timedelta(days=days)

def had_recent_losses(symbol, max_losses=2, within_days=7):
    data = load_history()
    symbol = symbol.upper()
    if symbol not in data:
        return False
    limit_date = datetime.now() - timedelta(days=within_days)
    recent_losses = [
        r for r in data[symbol]["history"]
        if r["result"] == "loss" and datetime.strptime(r["date"], "%Y-%m-%d") >= limit_date
    ]
    return len(recent_losses) >= max_losses
