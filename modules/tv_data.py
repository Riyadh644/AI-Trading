import requests
import json
import os
import numpy as np
from datetime import datetime
from modules.ml_model import load_model, predict_buy_signal
from modules.history_tracker import was_seen_recently, had_recent_losses

TOP_STOCKS_FILE = "data/top_stocks.json"
WATCHLIST_FILE = "data/watchlist.json"
PUMP_FILE = "data/pump_stocks.json"

TRADINGVIEW_SESSION = "e383hxul1yky840oidvdojkelf5k5yfr"
TRADINGVIEW_HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Content-Type": "application/json",
    "Referer": "https://www.tradingview.com",
    "Cookie": f"sessionid={TRADINGVIEW_SESSION};"
}

def fetch_stocks_from_tradingview():
    url = "https://scanner.tradingview.com/america/scan"
    payload = {
        "filter": [
            {"left": "volume", "operation": "greater", "right": 2_000_000},
            {"left": "close", "operation": "greater", "right": 0},
            {"left": "close", "operation": "less", "right": 5},
            {"left": "exchange", "operation": "equal", "right": "NASDAQ"},
            {"left": "type", "operation": "equal", "right": "stock"},
            {"left": "change", "operation": "greater", "right": 0}
        ],
        "symbols": {"query": {"types": []}, "tickers": []},
        "columns": ["name", "close", "volume", "market_cap_basic", "change"],
        "sort": {"sortBy": "volume", "sortOrder": "desc"},
        "options": {"lang": "en"},
        "range": [0, 500]
    }

    try:
        response = requests.post(url, json=payload, headers=TRADINGVIEW_HEADERS, timeout=10)
        data = response.json()
        stocks = []
        for item in data.get("data", []):
            s = item["d"]
            stocks.append({
                "symbol": s[0],
                "close": s[1],
                "vol": s[2],
                "market_cap": s[3],
                "change": s[4]
            })
        return stocks
    except Exception as e:
        print(f"❌ فشل في جلب الأسهم من TradingView: {e}")
        return []

def analyze_market():
    print("📊 جاري تحليل السوق (مطابقة Webull)...")
    model = load_model()
    stocks = fetch_stocks_from_tradingview()

    top_stocks, watchlist, pump_stocks = [], [], []

    for stock in stocks:
        try:
            symbol = stock["symbol"].upper()
            if not isinstance(stock["market_cap"], (int, float)) or stock["market_cap"] > 3_200_000_000:
                continue

            # ✅ فحص الأداء السابق والتكرار
            if had_recent_losses(symbol): continue
            if was_seen_recently(symbol): continue

            # ✅ مؤشرات فنية من TradingView
            data = fetch_data_from_tradingview(symbol)
            if not data: continue

            is_green = data["close"] > data["open"]
            rsi_ok = data["RSI"] and data["RSI"] > 50
            macd_ok = data["MACD"] and data["MACD_signal"] and data["MACD"] > data["MACD_signal"]
            volume_ok = stock["vol"] > 1_000_000  # مؤقتًا

            if not (is_green and rsi_ok and macd_ok and volume_ok):
                continue

            features = {
                "ma10": stock["close"],
                "ma30": stock["close"],
                "vol": stock["vol"],
                "avg_vol": stock["vol"],
                "change": stock["change"],
                "close": stock["close"]
            }

            score = predict_buy_signal(model, features)
            stock["score"] = score
            print(f"🔍 {symbol} → Score: {score:.2f}%")

            if score >= 25:
                top_stocks.append(stock)
            elif 20 <= score < 25:
                watchlist.append(stock)

            if stock["change"] > 25 and stock["vol"] > stock["market_cap"]:
                pump_stocks.append(stock)

        except Exception as e:
            print(f"❌ تحليل {stock.get('symbol', 'UNKNOWN')} فشل: {e}")

    # ✅ فقط أفضل 3 لكل فئة
    top_stocks = sorted(top_stocks, key=lambda x: x["score"], reverse=True)[:3]
    watchlist = sorted(watchlist, key=lambda x: x["score"], reverse=True)[:3]
    pump_stocks = sorted(pump_stocks, key=lambda x: x["score"], reverse=True)[:3]

    save_json(TOP_STOCKS_FILE, top_stocks)
    save_json(WATCHLIST_FILE, watchlist)
    save_json(PUMP_FILE, pump_stocks)

    save_daily_history(top_stocks, "top_stocks")
    save_daily_history(watchlist, "watchlist")
    save_daily_history(pump_stocks, "pump_stocks")

    print(f"\n✅ تحليل مكتمل: {len(top_stocks)} أقوى، {len(watchlist)} مراقبة، {len(pump_stocks)} انفجار.")

def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=convert_np)

def convert_np(o):
    if isinstance(o, (np.integer, np.floating)):
        return o.item()
    raise TypeError

def save_daily_history(data, category):
    today = datetime.now().strftime("%Y-%m-%d")
    os.makedirs("history", exist_ok=True)
    filename = f"history/{category}_{today}.json"
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=convert_np)
        print(f"📁 تم حفظ {category} في {filename}")
    except Exception as e:
        print(f"❌ فشل حفظ {category}: {e}")

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

def analyze_single_stock(symbol):
    print(f"📊 تحليل سهم فردي: {symbol}")
    model = load_model()
    data = fetch_data_from_tradingview(symbol)

    if not data:
        print(f"❌ لا يمكن تحليل {symbol}: لا توجد بيانات من TradingView")
        return None

    features = {
        "ma10": data["close"],
        "ma30": data["close"],
        "vol": data["vol"],
        "avg_vol": data["vol"],
        "change": data["change"],
        "close": data["close"]
    }

    score = predict_buy_signal(model, features)
    result = {
        "symbol": symbol,
        "score": score,
        "signal": "buy" if score >= 25 else "watch" if score >= 20 else "reject"
    }

    print(f"✅ {symbol} → Score: {score:.2f}% → {result['signal']}")
    return result
