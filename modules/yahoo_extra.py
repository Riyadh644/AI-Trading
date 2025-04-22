import requests

def fetch_bulk_yahoo_data(symbols):
    symbol_str = ",".join(symbols)
    url = f"https://query1.finance.yahoo.com/v7/finance/quote?symbols={symbol_str}"
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        response = requests.get(url, headers=headers, timeout=10)
        data = response.json().get("quoteResponse", {}).get("result", [])

        result = {}
        for item in data:
            symbol = item.get("symbol")
            market_cap = item.get("marketCap")
            avg_vol = item.get("averageDailyVolume3Month")
            price = item.get("regularMarketPrice")

            result[symbol] = {
                "market_cap": market_cap,
                "avg_vol": avg_vol,
                "price": price
            }

        # ✅ طباعة أول 5 أمثلة من البيانات
        count = 0
        print("\n🔍 أمثلة من البيانات المحملة من Yahoo:")
        for sym, val in result.items():
            print(f"  🔹 {sym} | السعر: {val['price']} | Market Cap: {val['market_cap']} | Avg Vol: {val['avg_vol']}")
            count += 1
            if count >= 5:
                break

        return result

    except Exception as e:
        print(f"❌ Bulk Yahoo Fetch Error: {e}")
        return {}


