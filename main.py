import os
import yfinance as yf
import pandas as pd
from telegram.ext import ApplicationBuilder, CommandHandler

SYMBOL = "GC=F"

def get_data(interval, period="5d"):
    df = yf.download(SYMBOL, interval=interval, period=period, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

def calc_rsi(close, period=14):
    delta = close.diff()
    gain = delta.where(delta>0, 0).rolling(period).mean()
    loss = -delta.where(delta<0, 0).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calc_ema(close, period):
    return close.ewm(span=period).mean()

def calc_atr(df, period=14):
    hl = df['High'] - df['Low']
    hc = abs(df['High'] - df['Close'].shift())
    lc = abs(df['Low'] - df['Close'].shift())
    tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
    return tr.rolling(period).mean()

def agent_zone(df_h1):
    recent_high = df_h1['High'].tail(20).max()
    recent_low = df_h1['Low'].tail(20).min()
    price = df_h1['Close'].iloc[-1]
    if abs(price - recent_high) < abs(price - recent_low):
        return {"vote":"SELL", "zone":f"{recent_high-5:.1f}-{recent_high:.1f}", "type":"Supply H1"}
    else:
        return {"vote":"BUY", "zone":f"{recent_low:.1f}-{recent_low+5:.1f}", "type":"Demand H1"}

def agent_trend(df_h1):
    ema50 = calc_ema(df_h1['Close'], 50).iloc[-1]
    ema200 = calc_ema(df_h1['Close'], 200).iloc[-1]
    price = df_h1['Close'].iloc[-1]
    if price > ema50 > ema200:
        return {"vote":"BUY", "reason":f"Тренд UP (Price {price:.1f} > EMA50 {ema50:.1f})"}
    elif price < ema50 < ema200:
        return {"vote":"SELL", "reason":f"Тренд DOWN (Price {price:.1f} < EMA50 {ema50:.1f})"}
    else:
        return {"vote":"NEUTRAL", "reason":"Боковик"}

def agent_rsi(df_m15):
    rsi = calc_rsi(df_m15['Close']).iloc[-1]
    if rsi > 65:
        return {"vote":"SELL", "reason":f"RSI {rsi:.1f} перекуплен"}
    elif rsi < 35:
        return {"vote":"BUY", "reason":f"RSI {rsi:.1f} перепродан"}
    else:
        return {"vote":"NEUTRAL", "reason":f"RSI {rsi:.1f} нейтрально"}

def agent_pa(df_m15):
    last = df_m15.iloc[-1]
    prev = df_m15.iloc[-2]
    if prev['Close'] > prev['Open'] and last['Close'] < last['Open'] and last['Close'] < prev['Open']:
        return {"vote":"SELL", "reason":"Медвежье поглощение M15"}
    if prev['Close'] < prev['Open'] and last['Close'] > last['Open'] and last['Close'] > prev['Open']:
        return {"vote":"BUY", "reason":"Бычье поглощение M15"}
    return {"vote":"NEUTRAL", "reason":"Паттерна нет"}

def agent_atr(df_m15):
    atr = calc_atr(df_m15).iloc[-1]
    return {"atr": atr, "reason":f"ATR {atr:.2f} для SL/TP"}

def agent_boss(votes):
    buys = votes.count("BUY")
    sells = votes.count("SELL")
    if buys >= 3:
        return "BUY"
    if sells >= 3:
        return "SELL"
    return "WAIT"

async def start(update, context):
    await update.message.reply_text("🐻 Night Bear v2 с 6 агентами онлайн!\nЖми /signal для анализа")

async def signal(update, context):
    await update.message.reply_text("🐻 Анализирую... H1 + M15, 5 сек...")
    try:
        df_h1 = get_data("60m", "5d")
        df_m15 = get_data("15m", "5d")
        z = agent_zone(df_h1)
        t = agent_trend(df_h1)
        r = agent_rsi(df_m15)
        pa = agent_pa(df_m15)
        atr_data = agent_atr(df_m15)
        atr = atr_data['atr']
        price = df_m15['Close'].iloc[-1]
        votes = [z['vote'], t['vote'], r['vote'], pa['vote']]
        decision = agent_boss(votes)
        if decision == "WAIT":
            await update.message.reply_text(f"⏸️ Консенсуса нет\nЗона: {z['zone']}\nТренд: {t['reason']}\nRSI: {r['reason']}\nPA: {pa['reason']}\nЖди подтверждения M15")
            return
        if decision == "BUY":
            entry = price
            sl = entry - atr*1.5
            tp1 = entry + atr*1.5
            tp2 = entry + atr*3
            tp3 = entry + atr*4.5
        else:
            entry = price
            sl = entry + atr*1.5
            tp1 = entry - atr*1.5
            tp2 = entry - atr*3
            tp3 = entry - atr*4.5
        text = f"🐻 Night Bear - 6 Агентов Консенсус: {decision}\n\n📍 ЗОНА: {z['zone']} ({z['type']})\n📈 {t['reason']}\n⚡ {r['reason']}\n🕯️ {pa['reason']}\n🌪️ {atr_data['reason']}\n\nГолоса: {votes} -> {decision}\n\n💰 ТВХ: {entry:.2f}\n🛑 SL: {sl:.2f}\n🎯 TP1: {tp1:.2f}\n🎯 TP2: {tp2:.2f}\n🎯 TP3: {tp3:.2f}\n"
        await update.message.reply_text(text)
    except Exception as e:
        await update.message.reply_text(f"Ошибка: {e}")

app = ApplicationBuilder().token(os.environ["BOT_TOKEN"]).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("signal", signal))
print("Night Bear 6 Agents started")
app.run_polling()
