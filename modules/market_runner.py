import os
import json
import time
from datetime import datetime
from modules.ml_model import load_model, predict_buy_signal
from modules.tv_data import get_all_symbols, get_stock_data

TOP_FILE = "data/top_stocks.json"
WATCHLIST_FILE = "data/watchlist.json"
PUMP_FILE = "data/pump_stocks.json"
HISTORY_PATH = "history"

def analyze_market():
    model = load_model()
    symbols = get_all_symbols()

    top = []
    watchlist = []
    pump = []

    for i, symbol in enumerate(symbols):
        try:
            data = get_stock_data(symbol)
            if not data:
                continue

            score = predict_buy_signal(model, data)
            data["score"] = score

            entry = round(data["close"], 2)
            data["entry"] = entry
            data["target1"] = round(entry * 1.1, 2)
            data["target2"] = round(entry * 1.25, 2)
            data["stop_loss"] = round(entry * 0.85, 2)

            if score >= 90:
                top.append(data)
            elif 80 <= score < 90:
                watchlist.append(data)

            if data["change"] > 25 and data["vol"] > data["avg_vol"] * 2:
                pump.append(data)

        except Exception as e:
            print(f"❌ {symbol}: {e}")

        if (i + 1) % 50 == 0:
            print(f"✅ تم تحليل {i+1} من {len(symbols)}")
            time.sleep(3)

    save_json(TOP_FILE, top)
    save_json(WATCHLIST_FILE, watchlist)
    save_json(PUMP_FILE, pump)
    save_daily_history("top_stocks", top)
    save_daily_history("watchlist", watchlist)
    save_daily_history("pump_stocks", pump)

    print(f"📊 النتائج: {len(top)} أقوى، {len(watchlist)} مراقبة، {len(pump)} انفجار")

def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def save_daily_history(name, data):
    today = datetime.now().strftime("%Y-%m-%d")
    os.makedirs(HISTORY_PATH, exist_ok=True)
    path = f"{HISTORY_PATH}/{name}_{today}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    print("🔁 تحليل السوق الجاري...", datetime.now())
    analyze_market()
