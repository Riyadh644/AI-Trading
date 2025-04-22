import yfinance as yf
import json
import os
from modules.telegram_bot import broadcast_message

TRACKED_FILE = "data/tracked_stocks.json"

def load_tracked():
    if os.path.exists(TRACKED_FILE):
        with open(TRACKED_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_tracked(data):
    with open(TRACKED_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def check_targets():
    tracked = load_tracked()
    updated = []

    for stock in tracked:
        symbol = stock.get("symbol")
        target1 = stock.get("target1")
        target2 = stock.get("target2")
        stop_loss = stock.get("stop_loss")
        last_alert = stock.get("last_alert", "")

        try:
            ticker = yf.Ticker(symbol)
            price = ticker.history(period="1d", interval="1m")
            if price.empty:
                continue
            current = price["Close"].iloc[-1]

            if target2 and current >= target2 and last_alert != "target2":
                msg = f"🏁 تم الوصول للهدف 2 لسهم {symbol}"
                broadcast_message.sync(msg)
                stock["last_alert"] = "target2"

            elif target1 and current >= target1 and last_alert != "target1":
                msg = f"🎯 تم تحقيق الهدف الأول لسهم {symbol}"
                broadcast_message.sync(msg)
                stock["last_alert"] = "target1"

            elif stop_loss and current <= stop_loss and last_alert != "stop":
                msg = f"⛔ سهم {symbol} كسر وقف الخسارة، يُفضل الخروج من الصفقة"
                broadcast_message.sync(msg)
                stock["last_alert"] = "stop"

        except Exception as e:
            print(f"⚠️ خطأ أثناء متابعة {symbol}: {e}")
            continue

        updated.append(stock)

    save_tracked(updated)

def add_trade(symbol, entry, target1, target2, stop_loss):
    tracked = load_tracked()
    exists = any(s["symbol"] == symbol for s in tracked)
    if not exists:
        tracked.append({
            "symbol": symbol,
            "entry": entry,
            "target1": target1,
            "target2": target2,
            "stop_loss": stop_loss,
            "last_alert": ""
        })
        save_tracked(tracked)
