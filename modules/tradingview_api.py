import requests

def get_filtered_symbols():
    print("🔍 استخراج الأسهم من TradingView حسب السعر فقط (0 - 5 دولار)...")

    url = "https://scanner.tradingview.com/america/scan"
    headers = {
        "Content-Type": "application/json"
    }

    payload = {
        "filter": [
            {"left": "close", "operation": "greater", "right": 0},
            {"left": "close", "operation": "less", "right": 5}
        ],
        "symbols": {"query": {"types": []}},
        "columns": ["name", "exchange", "close", "volume", "market_cap_basic"],
        "sort": {"sortBy": "volume", "sortOrder": "desc"},
        "range": [0, 150],
        "options": {"lang": "en"}
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code != 200:
            print(f"❌ خطأ في الاتصال: {response.status_code} - {response.text}")
            return []

        data = response.json()
        if not data or "data" not in data:
            print("❌ لا توجد بيانات صالحة في الرد من TradingView.")
            return []

        symbols = []
        for item in data["data"]:
            try:
                name = item["d"][0]  # أول عمود: name
                exchange = item["d"][1]  # ثاني عمود: exchange
                if exchange == "NASDAQ":
                    symbols.append(name)
            except Exception:
                continue

        print(f"✅ تم جلب {len(symbols)} رمز من TradingView (فلتر السعر فقط + NASDAQ)")
        return symbols

    except Exception as e:
        print(f"❌ خطأ أثناء جلب البيانات: {e}")
        return []
