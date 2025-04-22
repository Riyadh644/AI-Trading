# modules/stock_utils.py
import yfinance as yf
import pandas as pd

def get_stock_history(symbol, period="60d", interval="1d"):
    try:
        df = yf.download(symbol, period=period, interval=interval, progress=False)
        if df is None or df.empty:
            return None
        df.reset_index(inplace=True)
        return df
    except Exception as e:
        print(f"❌ خطأ في تحميل {symbol}: {e}")
        return None
