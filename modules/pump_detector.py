import yfinance as yf
import pandas as pd
import json
from datetime import datetime, timedelta
from modules.tradingview_api import get_filtered_symbols

def detect_pump_stocks():
    pump_candidates = []
    symbols = get_filtered_symbols()

    for symbol in symbols:
        try:
            stock = yf.Ticker(symbol)
            hist = stock.history(period="3mo", interval="1d")

            if hist.empty or len(hist) < 20:
                continue

            # شروط الانفجار
            current = hist.iloc[-1]
            prev = hist.iloc[-2]
            avg_vol = hist['Volume'].tail(60).mean()

            price_change = ((current["Close"] - prev["Close"]) / prev["Close"]) * 100
            volume_spike = current["Volume"] > avg_vol * 2

            if price_change > 15 and volume_spike and current["Close"] < 5:
                pump_candidates.append({
                    "symbol": symbol,
                    "price": round(current["Close"], 2),
                    "change%": round(price_change, 2),
                    "volume": int(current["Volume"]),
                })
        except:
            continue

    # حفظ النتائج
    with open("pump_stocks.json", "w") as f:
        json.dump(pump_candidates, f, indent=2)

    return pump_candidates
