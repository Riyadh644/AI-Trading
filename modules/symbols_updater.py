import pandas as pd
import requests
import os

def fetch_all_us_symbols():
    # روابط NASDAQ الرسمية
    nasdaq_url = "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"
    other_url = "https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"

    try:
        print("🔁 جاري تحميل رموز NASDAQ...")
        nasdaq_txt = requests.get(nasdaq_url).text
        print("🔁 جاري تحميل رموز NYSE/AMEX...")
        other_txt = requests.get(other_url).text

        nasdaq_lines = nasdaq_txt.strip().split("\n")[1:-1]
        other_lines = other_txt.strip().split("\n")[1:-1]

        nasdaq_symbols = [line.split("|")[0] for line in nasdaq_lines]
        other_symbols = [line.split("|")[0] for line in other_lines]

        all_symbols = sorted(list(set(nasdaq_symbols + other_symbols)))

        return all_symbols

    except Exception as e:
        print(f"❌ خطأ أثناء تحميل الرموز: {e}")
        return []

def save_symbols_to_csv(symbols, file_path="modules/all_symbols.csv"):
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        df = pd.DataFrame(symbols, columns=["symbol"])
        df.to_csv(file_path, index=False)
        print(f"✅ تم حفظ {len(symbols)} رمز في: {file_path}")
    except Exception as e:
        print(f"❌ فشل حفظ الملف: {e}")

if __name__ == "__main__":
    symbols = fetch_all_us_symbols()
    if symbols:
        save_symbols_to_csv(symbols)
