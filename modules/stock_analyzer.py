import requests
import json
import time
import os
import random
import pandas as pd
from modules.ml_model import load_model, predict_buy_signal

ALL_SYMBOLS_CSV = "modules/all_symbols.csv"
TOP_STOCKS_FILE = "data/top_stocks.json"
WATCHLIST_FILE = "data/watchlist.json"
PUMP_FILE = "data/pump_stocks.json"

TRADINGVIEW_SESSION = "e383hxul1yky840oidvdojkelf5k5yfr"
TRADINGVIEW_HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Content-Type": "application/x-www-form-urlencoded",
    "Referer": "https://www.tradingview.com",
    "Cookie": f"sessionid={TRADINGVIEW_SESSION};"
}

def get_symbols():
    df = pd.read_csv(ALL_SYMBOLS_CSV)
    df = df[df["symbol"].apply(lambda x: isinstance(x, str))]
    df = df[~df["symbol"].str.contains(r'[\.\$\-]', regex=True)]
    return df["symbol"].tolist()

def fetch_data_from_tradingview(symbol):
    try:
        payload = {
            "symbols": {"tickers": [f"NASDAQ:{symbol}"], "query": {"types": []}},
            "columns": [
                "close", "open", "volume", "change", "Recommend.All",
                "RSI", "MACD.macd", "MACD.signal", "Stoch.K", "Stoch.D"
            ]
        }
        response = requests.post(
            "https://scanner.tradingview.com/america/scan",
            headers=TRADINGVIEW_HEADERS,
            data=json.dumps(payload),
            timeout=10
        )
        result = response.json()
        if "data" not in result or not result["data"]:
            return None

        row = result["data"][0]["d"]
        return {
            "symbol": symbol,
            "close": row[0],
            "open": row[1],
            "vol": row[2],
            "change": row[3],
            "recommend": row[4],
            "RSI": row[5],
            "MACD": row[6],
            "MACD_signal": row[7],
            "Stoch_K": row[8],
            "Stoch_D": row[9],
        }
    except Exception as e:
        print(f"❌ TradingView Error {symbol}: {e}")
        return None

def analyze_symbol(symbol, model):
    data = fetch_data_from_tradingview(symbol)
    if not data:
        return None

    try:
        avg_vol = float(data["vol"]) / 2  # تقدير مبدئي لعدم توفر avg_vol من TradingView
        features = {
            "ma10": float(data["close"]),
            "ma30": float(data["close"]),
            "vol": float(data["vol"]),
            "avg_vol": avg_vol,
            "change": float(data["change"]),
            "close": float(data["close"]),
        }
        score = predict_buy_signal(model, features)
        data["score"] = score
        return data
    except Exception as e:
        print(f"❌ تحليل السهم {symbol} فشل: {e}")
        return None

def analyze_market(batch_size=30, sleep_between_batches=2):
    print("📊 جاري تحليل السوق عبر TradingView...")
    model = load_model()
    symbols = get_symbols()

    top_stocks, watchlist, pump_stocks = [], [], []

    for i in range(0, len(symbols), batch_size):
        batch = symbols[i:i+batch_size]
        print(f"\n⏳ تحليل دفعة {i//batch_size + 1} من {len(symbols)//batch_size}...")

        for symbol in batch:
            data = analyze_symbol(symbol, model)
            if not data:
                continue
            score = data["score"]
            if score >= 90:
                top_stocks.append(data)
            elif 80 <= score < 90:
                watchlist.append(data)

            avg_vol = float(data["vol"]) / 2  # نفس التقدير داخل الشرط
            if (
                isinstance(data["change"], (int, float)) and
                isinstance(data["vol"], (int, float)) and
                data["change"] > 25 and data["vol"] > avg_vol * 2
            ):
                pump_stocks.append(data)

            time.sleep(random.uniform(1.2, 2.0))  # تقليل احتمال الحظر

        print(f"✅ تم تحليل {len(batch)} رمز")
        time.sleep(sleep_between_batches)

    save_json(TOP_STOCKS_FILE, top_stocks)
    save_json(WATCHLIST_FILE, watchlist)
    save_json(PUMP_FILE, pump_stocks)

    print(f"\n✅ تحليل مكتمل: {len(top_stocks)} أقوى، {len(watchlist)} مراقبة، {len(pump_stocks)} انفجار.")

def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
