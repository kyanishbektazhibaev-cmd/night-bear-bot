import os
from flask import Flask
from threading import Thread
import requests, telebot, time, random

TOKEN=os.environ.get("TELEGRAM_BOT_TOKEN")
bot=telebot.TeleBot(TOKEN)
app=Flask('')

@app.route('/')
def home(): return "Night Bear OK - Fixed"

def run(): app.run(host='0.0.0.0',port=8080)
Thread(target=run,daemon=True).start()

def get_klines():
    # 1. Пробуем Bybit - работает всегда
    try:
        u="https://api.bybit.com/v5/market/kline?category=spot&symbol=PAXGUSDT&interval=60&limit=100"
        r=requests.get(u,timeout=10).json()
        kl=r["result"]["list"][::-1]
        closes=[float(x[4]) for x in kl]
        if len(closes)>20:
            return closes
    except: pass
    # 2. Запасной Binance Vision
    try:
        u="https://data-api.binance.vision/api/v3/klines?symbol=PAXGUSDT&interval=1h&limit=100"
        r=requests.get(u,timeout=10).json()
        closes=[float(x[4]) for x in r]
        return closes
    except: return None

def get_price():
    closes=get_klines()
    if closes:
        return closes[-1], closes
    return None, None

def make_signal():
    price, closes = get_price()
    if not closes:
        return "⚠️ Биржа не отвечает, пробую еще раз...\nНапиши /signal через 30 сек"
    ma20=sum(closes[-20:])/20
    side="BUY 🟢 ЛОНГ" if price > ma20 else "SELL 🔴 ШОРТ"
    sl = price*0.995 if "BUY" in side else price*1.005
    tp1 = price*1.005 if "BUY" in side else price*0.995
    tp2 = price*1.01 if "BUY" in side else price*0.99
    tp3 = price*1.015 if "BUY" in side else price*0.985
    return f"🐻 Night Bear - XAUUSD {side}\n\n💰 Цена: {price:.2f}\n📍 Entry: {price:.2f}\n\n🛑 SL: {sl:.2f} (-0.5%)\n🎯 TP1: {tp1:.2f}\n🎯 TP2: {tp2:.2f}\n🎯 TP3: {tp3:.2f}\n\n⚡️ Риск 1-2% | Исправлено ✅"

@bot.message_handler(commands=['start'])
def start(m):
    bot.send_message(m.chat.id, "🐻 Night Bear Исправлен!\n\n/signal - сигнал по золоту")

@bot.message_handler(commands=['signal'])
def signal(m):
    bot.send_message(m.chat.id, make_signal())

print("Night Bear FIXED started")
bot.infinity_polling()
