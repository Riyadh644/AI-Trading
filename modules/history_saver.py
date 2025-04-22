import json
import os
from datetime import datetime

def save_daily_history(data, category):
    """
    يحفظ ملف json باسم التاريخ والتصنيف مثل: top_stocks_2025-04-21.json
    """
    today = datetime.now().strftime("%Y-%m-%d")
    os.makedirs("history", exist_ok=True)
    filename = f"history/{category}_{today}.json"

    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"✅ تم حفظ نتائج {category} في {filename}")
    except Exception as e:
        print(f"❌ فشل حفظ {category}: {e}")
