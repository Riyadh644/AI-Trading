# modules/indicators.py
def calculate_indicators(df):
    df["ma10"] = df["Close"].rolling(window=10).mean()
    df["ma30"] = df["Close"].rolling(window=30).mean()
    df["avg_vol"] = df["Volume"].rolling(window=30).mean()
    df["change"] = df["Close"].pct_change() * 100
    df.dropna(inplace=True)
    return df
