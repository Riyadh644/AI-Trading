import os
import pandas as pd
import yfinance as yf
from tqdm import tqdm
from modules.tradingview_api import get_filtered_symbols

# إنشاء مجلد البيانات إن لم يكن موجود
os.makedirs("datasets", exist_ok=True)

# فلترة محلية حسب الشروط الذكية
def filter_locally(symbols):
    filtered = []
    for symbol in tqdm(symbols, desc="🔎 تطبيق الفلاتر الذكية داخل Python"):
        try:
            stock = yf.Ticker(symbol)
            df = stock.history(period="6mo", interval="1d")
            if df.empty or len(df) < 30:
                continue

            current = df.iloc[-1]
            avg_volume = df["Volume"].tail(60).mean()

            if (
                current["Volume"] > 2_000_000 and
                avg_volume > 0 and
                "Close" in current and
                0 < current["Close"] < 5
            ):
                info = stock.info
                market_cap = info.get("marketCap", 0)
                if market_cap and market_cap < 500_000_000:
                    filtered.append(symbol)
        except Exception:
            continue
    return filtered

# حساب المؤشرات الفنية
def extract_features(df):
    df["MA10"] = df["Close"].rolling(window=10).mean()
    df["MA30"] = df["Close"].rolling(window=30).mean()
    df["Avg_Volume"] = df["Volume"].rolling(window=10).mean()
    df["Change"] = df["Close"].pct_change() * 100
    return df

# إنشاء الإشارة (Signal)
def generate_signals(df, threshold=3):  # خفضناها إلى 3%
    future = df["Close"].shift(-3)
    current = df["Close"]
    df["Signal"] = ((future - current) / current * 100) >= threshold
    df["Signal"] = df["Signal"].astype(int)
    return df

# تجميع البيانات
def generate_training_data(symbols):
    rows = []
    for symbol in tqdm(symbols, desc="📥 تحميل وتحليل الأسهم"):
        try:
            df = yf.download(symbol, period="6mo", interval="1d", progress=False, auto_adjust=True)
            if df.empty or "Close" not in df.columns or df["Close"].dropna().empty:
                print(f"❌ {symbol}: بيانات غير صالحة أو العمود Close فارغ")
                continue

            df = extract_features(df)
            df = generate_signals(df, threshold=3)

            # تحقق من وجود إشارات متنوعة قبل التخزين
            valid_signals = df["Signal"].value_counts()
            if valid_signals.get(1, 0) == 0 or valid_signals.get(0, 0) == 0:
                print(f"⚠️ {symbol}: بيانات غير متوازنة (Signal=0 أو Signal=1 مفقود)")
                continue

            for i in range(len(df)):
                if pd.notnull(df.at[i, "MA10"]) and pd.notnull(df.at[i, "MA30"]) and pd.notnull(df.at[i, "Volume"]) \
                    and pd.notnull(df.at[i, "Avg_Volume"]) and pd.notnull(df.at[i, "Change"]) and pd.notnull(df.at[i, "Signal"]):
                    
                    rows.append({
                        "Symbol": symbol,
                        "MA10": df.at[i, "MA10"],
                        "MA30": df.at[i, "MA30"],
                        "Volume": df.at[i, "Volume"],
                        "Avg_Volume": df.at[i, "Avg_Volume"],
                        "Change": df.at[i, "Change"],
                        "Signal": df.at[i, "Signal"],
                    })

        except Exception as e:
            print(f"❌ {symbol}: خطأ أثناء التحميل - {e}")
            continue

    df_final = pd.DataFrame(rows)
    df_final.to_csv("datasets/training_data.csv", index=False)
    print(f"\n✅ تم حفظ {len(df_final)} صف في datasets/training_data.csv")

# بدء التنفيذ
if __name__ == "__main__":
    print("🔍 استخراج الأسهم من TradingView حسب السعر فقط (0 - 5 دولار)...")
    initial_symbols = get_filtered_symbols()
    print(f"✅ تم جلب {len(initial_symbols)} رمز من TradingView (فلتر السعر فقط + NASDAQ)")
    smart_filtered = filter_locally(initial_symbols)
    print(f"✅ تم ترشيح {len(smart_filtered)} سهم بعد الفلاتر الذكية")
    generate_training_data(smart_filtered)
