import os
import time
import json
import logging
import schedule
import asyncio
import nest_asyncio
import threading
import yfinance as yf
import requests
from datetime import datetime

from modules.analyze_performance import generate_report_summary
from modules.tv_data import analyze_market, analyze_single_stock, fetch_stocks_from_tradingview
from modules.ml_model import train_model_daily
from modules.symbols_updater import fetch_all_us_symbols, save_symbols_to_csv
from modules.telegram_bot import (
    start_telegram_bot,
    compare_stock_lists_and_alert,
    send_telegram_message
)
from modules.pump_detector import detect_pump_stocks
from modules.price_tracker import check_targets

nest_asyncio.apply()

NEWS_API_KEY = "BpXXFMPQ3JdCinpg81kfn4ohvmnhGZOwEmHjLIre"
POSITIVE_NEWS_FILE = "data/positive_watchlist.json"

if not os.path.exists("logs"):
    os.makedirs("logs")

logging.basicConfig(
    filename="logs/bot.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

def log(msg):
    print(msg)
    logging.info(msg)

def fetch_news_sentiment(symbol):
    try:
        url = f"https://api.marketaux.com/v1/news/all?symbols={symbol}&filter_entities=true&language=en&api_token={NEWS_API_KEY}"
        response = requests.get(url)
        if response.status_code == 200:
            articles = response.json().get("data", [])
            for article in articles:
                title = article.get("title", "").lower()
                if "bankruptcy" in title or "dilution" in title:
                    return "negative"
                if "record revenue" in title or "strong earnings" in title:
                    return "positive"
        return "neutral"
    except Exception as e:
        log(f"❌ خطأ في تحليل الأخبار لـ {symbol}: {e}")
        return "neutral"

def watch_positive_news_stocks():
    log("🟢 فحص الأسهم ذات الأخبار الإيجابية...")
    try:
        stocks = fetch_stocks_from_tradingview()
        positive_stocks = []

        old_list = []
        if os.path.exists(POSITIVE_NEWS_FILE):
            with open(POSITIVE_NEWS_FILE, "r", encoding="utf-8") as f:
                old_list = json.load(f)
            old_symbols = [s["symbol"] for s in old_list]
        else:
            old_symbols = []

        for stock in stocks:
            symbol = stock["symbol"]
            sentiment = fetch_news_sentiment(symbol)
            if sentiment == "positive":
                if symbol not in old_symbols:
                    msg = f"""📢 سهم جديد بأخبار إيجابية:
📈 {symbol}
✅ تم رصده في السوق"""
                    send_telegram_message(msg)
                log(f"✅ {symbol} لديه أخبار إيجابية.")
                positive_stocks.append(stock)

        if positive_stocks:
            os.makedirs(os.path.dirname(POSITIVE_NEWS_FILE), exist_ok=True)
            with open(POSITIVE_NEWS_FILE, "w", encoding="utf-8") as f:
                json.dump(positive_stocks, f, indent=2, ensure_ascii=False)
            log(f"✅ تم حفظ {len(positive_stocks)} سهم في قائمة الأخبار الإيجابية.")
        else:
            log("⚠️ لا توجد أسهم إيجابية حالياً.")
    except Exception as e:
        log(f"❌ فشل في مراقبة الأخبار الإيجابية: {e}")

def is_market_weak():
    try:
        spy = yf.Ticker("SPY")
        hist = spy.history(period="2d")
        if len(hist) >= 2:
            prev = hist["Close"].iloc[-2]
            today = hist["Close"].iloc[-1]
            change_pct = (today - prev) / prev * 100
            return change_pct < -1
    except Exception as e:
        log(f"❌ خطأ في تحليل SPY: {e}")
    return False

def daily_model_training():
    log("🔁 تدريب يومي للنموذج الذكي...")
    train_model_daily()

def update_market_data():
    log("📊 تحديث بيانات السوق...")
    try:
        if is_market_weak():
            log("⚠️ السوق ضعيف (SPY < -1%). تم إلغاء التوصيات.")
            return
        stocks = analyze_market()
        final_stocks = []
        for stock in stocks:
            sentiment = fetch_news_sentiment(stock["symbol"])
            if sentiment == "negative":
                log(f"⚠️ تم تجاهل {stock['symbol']} بسبب أخبار سلبية.")
                continue
            final_stocks.append(stock)
        log(f"✅ تحليل مكتمل: {len(final_stocks)} سهم بعد فلترة الأخبار.")
    except Exception as e:
        log(f"❌ فشل تحليل السوق: {e}")

def update_symbols():
    log("🔁 تحديث رموز السوق من NASDAQ الرسمي...")
    try:
        symbols = fetch_all_us_symbols()
        if symbols:
            save_symbols_to_csv(symbols)
            log(f"✅ تم تحديث {len(symbols)} رمز سوق.")
    except Exception as e:
        log(f"❌ فشل في تحديث الرموز: {e}")

def update_pump_stocks():
    log("💣 تحليل الانفجارات السعرية...")
    try:
        detect_pump_stocks()
        log("✅ تم تحديث أسهم الانفجار السعرية.")
    except Exception as e:
        log(f"❌ فشل تحليل الانفجارات: {e}")

def track_targets():
    log("🎯 متابعة لحظية للأسهم...")
    try:
        check_targets()
    except Exception as e:
        log(f"❌ خطأ في متابعة الأهداف: {e}")

def run_smart_alerts():
    log("🔔 فحص التغيرات في الأسهم...")
    try:
        from telegram import Bot
        bot = Bot(token="7740179871:AAFYnS_QS595Gw5uRTMuW8N9ajUB4pK4tJ0")
        asyncio.run(compare_stock_lists_and_alert(bot))
    except Exception as e:
        log(f"❌ فشل إرسال التنبيهات الذكية: {e}")

def run_bot():
    def bot_thread():
        log("🤖 بوت طويق شغال ...")
        start_telegram_bot()
    thread = threading.Thread(target=bot_thread, daemon=True)
    thread.start()

# 🧠 بدء العمليات
daily_model_training()
update_market_data()
update_pump_stocks()

# ⏱ جدولة كل المهام
schedule.every().day.at("00:00").do(daily_model_training)
schedule.every().day.at("03:00").do(update_symbols)
schedule.every(5).minutes.do(update_market_data)
schedule.every(5).minutes.do(update_pump_stocks)
schedule.every(5).minutes.do(track_targets)
schedule.every(5).minutes.do(run_smart_alerts)
schedule.every(10).minutes.do(watch_positive_news_stocks)

run_bot()

while True:
    schedule.run_pending()
    time.sleep(1)
