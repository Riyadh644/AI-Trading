import os
import json
from datetime import datetime, timedelta
import yfinance as yf
import pytz  # 👈 ضروري لإدارة المناطق الزمنية

def generate_report_summary():
    path = "data/trade_history.json"
    if not os.path.exists(path):
        return "❌ لا يوجد سجل توصيات."

    with open(path, "r", encoding="utf-8") as f:
        history = json.load(f)

    # ✅ نستخدم توقيت السعودية
    tz = pytz.timezone("Asia/Riyadh")
    now_sa = datetime.now(tz)
    target_date = now_sa.strftime("%Y-%m-%d")
    next_date = (now_sa + timedelta(days=1)).strftime("%Y-%m-%d")

    # فلترة التوصيات لهذا التاريخ
    trades = [x for x in history if x["timestamp"].startswith(target_date)]

    if not trades:
        return "❌ لا يوجد تقرير يومي لإرسالة."


    summary = {
        "top": {"✅": [], "❌": []},
        "watchlist": {"✅": [], "❌": []},
        "pump": {"✅": [], "❌": []}
    }

    for trade in trades:
        symbol = trade["symbol"]
        category = trade.get("category", "unknown")
        entry = float(trade["entry_price"])

        try:
            data = yf.Ticker(symbol).history(start=target_date, end=next_date)
            if data.empty:
                continue
            high = round(data["High"].max(), 2)
        except:
            continue

        status = "✅" if high >= round(entry * 1.1, 2) else "❌"
        summary[category][status].append(symbol)

    def format_block(label, cat):
        success = len(summary[cat]["✅"])
        fail = len(summary[cat]["❌"])
        return f"{label}\n✅ ناجحة: {success}\n❌ خاسرة: {fail}\n"

    report = f"📊 تقرير أداء يوم {target_date}\n\n"
    report += format_block("📈 أقوى الأسهم", "top")
    report += format_block("🕵️‍♂️ تحت المراقبة", "watchlist")
    report += format_block("💣 أسهم قابلة للانفجار", "pump")

    total_success = sum(len(summary[cat]["✅"]) for cat in summary)
    total_fail = sum(len(summary[cat]["❌"]) for cat in summary)

    report += f"\n📈 إجمالي الصفقات الناجحة: {total_success}"
    report += f"\n📉 إجمالي الصفقات الخاسرة: {total_fail}"

    return report.strip()
