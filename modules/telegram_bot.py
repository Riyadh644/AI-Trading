from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.error import NetworkError
import asyncio
import json
import os
import yfinance as yf
import time
import numpy as np
from datetime import datetime
import requests


from modules.tv_data import analyze_market, fetch_data_from_tradingview
from modules.ml_model import load_model, predict_buy_signal
from modules.user_manager import save_user, get_all_users
from modules.analyze_performance import generate_report_summary

BOT_TOKEN = "7740179871:AAFYnS_QS595Gw5uRTMuW8N9ajUB4pK4tJ0"
USERS_FILE = "data/users.json"

keyboard = [
    ["📈 عرض أقوى الأسهم"],
    ["🕵️‍♂️ الأسهم تحت المراقبة"],
    ["💣 أسهم قابلة للانفجار"],
    ["📊 اختبار سهم معين"],
    ["📥 تحديث الأسهم الآن"],
    ["📊 عرض تقرير الأداء اليومي"]
]
markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_all_user_ids():
    if os.path.exists(USERS_FILE):
        import json
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            users = json.load(f)
        return list(users.keys())
    return []

def send_telegram_message(message):
    chat_ids = get_all_user_ids()
    for chat_id in chat_ids:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML"
        }
        try:
            requests.post(url, json=payload, timeout=10)
        except Exception as e:
            print(f"❌ فشل إرسال الرسالة إلى {chat_id}: {e}")

def load_json(path):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


async def safe_send_message(bot, chat_id, text, retries=3, delay=5):
    # تقسيم الرسالة الطويلة إلى أجزاء صغيرة
    max_len = 4000
    parts = [text[i:i + max_len] for i in range(0, len(text), max_len)]

    for part in parts:
        for attempt in range(retries):
            try:
                await bot.send_message(chat_id=chat_id, text=part, reply_markup=markup)
                break  # تم الإرسال بنجاح، نخرج من حلقة المحاولة
            except NetworkError as e:
                print(f"⚠️ فشل الإرسال (محاولة {attempt+1}/{retries}): {e}")
                await asyncio.sleep(delay)
        else:
            print("❌ فشل نهائي في إرسال الرسالة.")



async def broadcast_message(bot, text):
    users = get_all_users()
    for chat_id in users:
        await safe_send_message(bot, chat_id, text)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    save_user(chat_id)
    await update.get_bot().send_message(
        chat_id=chat_id,
        text=(
            "🤖 أهلاً بك في بوت توصيات الأسهم الذكية!\n\n"
            "📊 تحليلات لحظية بناء على الذكاء الصناعي\n"
            "اختر من القائمة للبدء:"
        ),
        reply_markup=markup
    )


def save_trade_history(stock, category):
    path = "data/trade_history.json"
    os.makedirs("data", exist_ok=True)
    history = load_json(path)

    symbol = stock["symbol"]
    if any(x["symbol"] == symbol for x in history):
        return

    record = {
        "symbol": symbol,
        "entry_price": round(stock.get("entry", stock.get("close", 0)), 2),
        "score": round(stock.get("score", 0), 2),
        "category": category,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    history.append(record)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)


async def show_daily_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    summary = generate_report_summary()
    if summary:
        await safe_send_message(update.get_bot(), update.effective_chat.id, summary)
    else:
        await safe_send_message(update.get_bot(), update.effective_chat.id, "❌ لا يوجد تقرير أداء لهذا اليوم.")


async def top_stocks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_json("data/top_stocks.json")
    if not data:
        return await safe_send_message(update.get_bot(), update.effective_chat.id, "❌ لا توجد أسهم قوية حالياً.")

    # ✅ أخذ أعلى 3 أسهم فقط
    data = sorted(data, key=lambda x: x.get("score", 0), reverse=True)[:3]

    msg = ""
    for stock in data:
        entry = round(stock.get("entry", stock.get("close", 0)), 2)
        target1 = round(entry * 1.1, 2)
        target2 = round(entry * 1.25, 2)
        stop_loss = round(entry * 0.85, 2)
        score = stock.get("score", 0)

        msg += f"""
📈 {stock['symbol']}
✅ إشارة: شراء قوي
💰 سعر الدخول: {entry}
🎯 الهدف 1: {target1}
🏁 الهدف 2: {target2}
🛑 وقف الخسارة: {stop_loss}
📊 نسبة النجاح: {score:.2f}%
""".strip() + "\n\n"

        save_trade_history(stock, category="top")

    await safe_send_message(update.get_bot(), update.effective_chat.id, msg.strip())



async def watchlist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_json("data/watchlist.json")
    if not data:
        return await safe_send_message(update.get_bot(), update.effective_chat.id, "❌ لا توجد أسهم تحت المراقبة حالياً.")

    # ✅ أقوى 3 أسهم فقط
    data = sorted(data, key=lambda x: x.get("score", 0), reverse=True)[:3]

    msg = ""
    for stock in data:
        entry = round(stock.get("entry", stock.get("close", 0)), 2)
        target1 = round(entry * 1.1, 2)
        target2 = round(entry * 1.25, 2)
        stop_loss = round(entry * 0.85, 2)
        score = stock.get("score", 0)

        msg += f"""
🕵️‍♂️ {stock['symbol']}
✅ إشارة: تحت المراقبة
💰 سعر الدخول: {entry}
🎯 الهدف 1: {target1}
🏁 الهدف 2: {target2}
🛑 وقف الخسارة: {stop_loss}
📊 نسبة النجاح: {score:.2f}%
""".strip() + "\n\n"

        save_trade_history(stock, category="watchlist")

    await safe_send_message(update.get_bot(), update.effective_chat.id, msg.strip())



async def pump_stocks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_json("data/pump_stocks.json")
    if not data:
        return await safe_send_message(update.get_bot(), update.effective_chat.id, "❌ لا توجد أسهم مرشحة للانفجار حالياً.")

    # ✅ أخذ فقط أقوى 3 أسهم حسب score
    data = sorted(data, key=lambda x: x.get("score", 0), reverse=True)[:3]

    msg = ""
    for stock in data:
        symbol = stock.get("symbol", "رمز غير معروف")
        price = round(stock.get("price", stock.get("close", 0)), 2)
        score = stock.get("score", 0)

        entry = price
        target1 = round(entry * 1.1, 2)
        target2 = round(entry * 1.25, 2)
        stop_loss = round(entry * 0.85, 2)

        msg += f"""
💣 {symbol}
✅ إشارة: قابلة للانفجار
💰 سعر الدخول: {entry}
🎯 الهدف 1: {target1}
🏁 الهدف 2: {target2}
🛑 وقف الخسارة: {stop_loss}
📊 نسبة النجاح: {score:.2f}%
""".strip() + "\n\n"

        save_trade_history(stock, category="pump")

    await safe_send_message(update.get_bot(), update.effective_chat.id, msg.strip())



async def analyze_stock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    symbol = update.message.text.strip().upper()
    if not symbol.isalpha() or len(symbol) > 5:
        return await safe_send_message(update.get_bot(), update.effective_chat.id, "❌ أرسل رمز سهم صحيح مثل: TSLA أو PLUG")

    model = load_model()
    data = fetch_data_from_tradingview(symbol)
    if not data:
        return await safe_send_message(update.get_bot(), update.effective_chat.id, f"❌ لا يمكن تحليل السهم: {symbol}")

    features = {
        "ma10": data["close"],   # استبدل بقيمة فعلية لو توفر تاريخ
        "ma30": data["close"],
        "vol": data["vol"],
        "avg_vol": data["vol"],
        "change": data["change"],
        "close": data["close"]
    }

    score = predict_buy_signal(model, features)
    close = round(float(data["close"]), 2)

    if score >= 90:
        entry = close
        target1 = round(entry * 1.1, 2)
        target2 = round(entry * 1.25, 2)
        stop_loss = round(entry * 0.85, 2)
        msg = f"""
📈 {symbol}
✅ إشارة: شراء قوي
💰 سعر الدخول: {entry}
🎯 الهدف 1: {target1}
🏁 الهدف 2: {target2}
🛑 وقف الخسارة: {stop_loss}
📊 نسبة النجاح: {score:.2f}%
"""
    elif score >= 80:
        msg = f"🕵️‍♂️ {symbol} تحت المراقبة\n📊 نسبة النجاح: {score:.2f}%"
    else:
        msg = f"❌ لا توجد إشارة شراء قوية على {symbol} (نسبة النجاح: {score:.2f}%)"

    await safe_send_message(update.get_bot(), update.effective_chat.id, msg.strip())


async def update_symbols_now(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await safe_send_message(update.get_bot(), update.effective_chat.id, "🔄 جاري تحديث وتحليل السوق...")
    try:
        await compare_stock_lists_and_alert(update.get_bot())
        await safe_send_message(update.get_bot(), update.effective_chat.id, "✅ تم التحديث وإرسال التنبيهات الذكية.")
    except Exception as e:
        await safe_send_message(update.get_bot(), update.effective_chat.id, f"❌ فشل التحديث: {e}")


async def compare_stock_lists_and_alert(bot):
    print("🔄 تحديث وتحليل السوق للمقارنة...")

    # 1. حفظ النسخة القديمة
    old_top = load_json("data/top_stocks.json")
    old_watch = load_json("data/watchlist.json")
    old_pump = load_json("data/pump_stocks.json")

    # 2. تحديث السوق
    analyze_market()

    # 3. تحميل النسخة الجديدة
    new_top = load_json("data/top_stocks.json")
    new_watch = load_json("data/watchlist.json")
    new_pump = load_json("data/pump_stocks.json")

    sections = [
        ("📈", "أقوى الأسهم", old_top, new_top),
        ("🕵️‍♂️", "الأسهم تحت المراقبة", old_watch, new_watch),
        ("💣", "الأسهم القابلة للانفجار", old_pump, new_pump)
    ]

    users = get_all_users()

    for emoji, name, old, new in sections:
        added, removed, changed = compare_lists(old, new)

        for stock in added:
            msg = f"{emoji} سهم جديد في {name}:\n📌 {stock['symbol']}\n📊 Score: {stock.get('score', 0):.2f}%"
            for chat_id in users:
                await safe_send_message(bot, chat_id, msg)

        for ch in changed:
            msg = f"""📌 <b>{ch['symbol']}</b>
💵 السعر: {ch['new']['close']:.2f}
📊 نسبة النجاح: {ch['new']['score']:.2f}%"""

            for chat_id in users:
                await safe_send_message(bot, chat_id, msg)

        for stock in removed:
            msg = f"{emoji} سهم خرج من {name}:\n📌 {stock['symbol']}"
            for chat_id in users:
                await safe_send_message(bot, chat_id, msg)

    transitioned = {s["symbol"] for s in new_top} & {s["symbol"] for s in old_watch}
    for symbol in transitioned:
        msg = f"🔁 السهم {symbol} انتقل من 🕵️‍♂️ تحت المراقبة إلى 📈 أقوى الأسهم ✅"
        for chat_id in users:
            await safe_send_message(bot, chat_id, msg)


def compare_lists(old, new):
    old_symbols = {s["symbol"]: s for s in old}
    new_symbols = {s["symbol"]: s for s in new}

    added = [new_symbols[s] for s in new_symbols if s not in old_symbols]
    removed = [old_symbols[s] for s in old_symbols if s not in new_symbols]
    changed = [
        {"symbol": s, "old": old_symbols[s], "new": new_symbols[s]}
        for s in new_symbols if s in old_symbols and (
            old_symbols[s].get("score", 0) != new_symbols[s].get("score", 0)
            or round(old_symbols[s].get("close", 0), 2) != round(new_symbols[s].get("close", 0), 2)
        )
    ]
    return added, removed, changed


def start_telegram_bot():
    while True:
        try:
            app = ApplicationBuilder().token(BOT_TOKEN).build()
            app.add_handler(CommandHandler("start", start))
            app.add_handler(MessageHandler(filters.Regex("(?i)^📈"), top_stocks))
            app.add_handler(MessageHandler(filters.Regex("(?i)^🕵️‍♂️"), watchlist))
            app.add_handler(MessageHandler(filters.Regex("(?i)^💣"), pump_stocks))
            app.add_handler(MessageHandler(filters.Regex("(?i)^📥"), update_symbols_now))
            app.add_handler(MessageHandler(filters.Regex("(?i)^📊 عرض تقرير الأداء اليومي"), show_daily_report))
            app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, analyze_stock))

            print("✅ بوت التليجرام جاهز لاستقبال الأوامر")
            app.run_polling()
        except Exception as e:
            print(f"❌ فشل الاتصال بـ Telegram: {e}")
            print("🔁 إعادة المحاولة بعد 10 ثواني...")
            time.sleep(10)
# ✅ إرسال تقرير الأداء اليومي تلقائيًا لجميع المستخدمين
# ✅ إرسال تقرير الأداء اليومي تلقائيًا لجميع المستخدمين (بحد أقصى 4096 حرف للرسالة)
async def send_performance_report():
    from telegram import Bot
    bot = Bot(BOT_TOKEN)
    users = get_all_users()
    
    summary = generate_report_summary()
    if not summary:
        print("❌ لا يوجد تقرير يومي لإرساله.")
        return

    # تقسيم التقرير إلى أجزاء لا تتجاوز 4000 حرف
    max_len = 4000
    parts = [summary[i:i + max_len] for i in range(0, len(summary), max_len)]

    for user_id in users:
        for part in parts:
            try:
                await bot.send_message(chat_id=user_id, text=part, reply_markup=markup)
            except Exception as e:
                print(f"❌ فشل في إرسال التقرير لـ {user_id}: {e}")
