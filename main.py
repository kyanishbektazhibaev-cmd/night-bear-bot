import os, requests, pandas as pd, time
from datetime import datetime

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

def get_klines(symbol="PAXGUSDT", interval="60", limit=100):
    try:
        url = f"https://api.bybit.com/v5/market/kline?category=spot&symbol={symbol}&interval={interval}&limit={limit}"
        r = requests.get(url, timeout=10).json()
        klines = r['result']['list'][::-1]
        df = pd.DataFrame(klines, columns=['time','open','high','low','close','vol','turn'])
        for c in ['open','high','low','close']: df[c]=df[c].astype(float)
        return df
    except:
        b_interval = {"1":"1m","5":"5m","15":"15m","60":"1h","240":"4h"}[interval]
        url = f"https://data-api.binance.vision/api/v3/klines?symbol={symbol}&interval={b_interval}&limit={limit}"
        data = requests.get(url, timeout=10).json()
        df = pd.DataFrame(data, columns=['time','open','high','low','close','vol','a','b','c','d','e','f'])
        for c in ['open','high','low','close']: df[c]=df[c].astype(float)
        return df

def rsi(series, p=14):
    delta = series.diff()
    gain = delta.where(delta > 0, 0).rolling(p).mean()
    loss = -delta.where(delta < 0, 0).rolling(p).mean()
    rs = gain/loss
    return 100 - (100/(1+rs))

def find_snr(df, lookback=50):
    highs = df['high'].tail(lookback)
    lows = df['low'].tail(lookback)
    res = highs[highs==highs.rolling(5,center=True).max()].nlargest(3).mean()
    sup = lows[lows==lows.rolling(5,center=True).min()].nsmallest(3).mean()
    return round(res,2), round(sup,2)

def pattern(df):
    last = df.iloc[-1]
    prev = df.iloc[-2]
    body = abs(last['close']-last['open'])
    rng = last['high']-last['low']
    if rng==0: return "Нет"
    low_wick = min(last['open'],last['close']) - last['low']
    up_wick = last['high'] - max(last['open'],last['close'])
    if low_wick > body*2: return "📌 Бычий Пин-бар"
    if up_wick > body*2: return "📌 Медвежий Пин-бар"
    if last['close']>last['open'] and prev['close']<prev['open'] and last['close']>prev['open']: return "🔥 Бычье Поглощение"
    if last['close']<last['open'] and prev['close']>prev['open'] and last['close']<prev['open']: return "🔥 Медвежье Поглощение"
    if body < rng*0.2: return "⭐ Доджи"
    return "Нет"

def build_signal():
    df_h4 = get_klines(interval="240")
    df_h1 = get_klines(interval="60")
    df_m15 = get_klines(interval="15")
    df_m5 = get_klines(interval="5")
    for df in [df_h4, df_h1, df_m15, df_m5]:
        df['ma20']=df['close'].rolling(20).mean()
        df['ma50']=df['close'].rolling(50).mean()
        df['rsi']=rsi(df['close'])
    price = df_h1.iloc[-1]['close']
    res, sup = find_snr(df_h1)
    pat_h1 = pattern(df_h1)
    pat_m5 = pattern(df_m5)
    trend_h4 = "ВВЕРХ 🟢" if df_h4.iloc[-1]['close'] > df_h4.iloc[-1]['ma50'] else "ВНИЗ 🔴"
    trend_h1 = "BUY 🟢" if price > df_h1.iloc[-1]['ma20'] else "SELL 🔴"
    if "SELL" in trend_h1:
        tvh = f"{res-3:.1f} - {res:.1f}"
        sl = res+9
        tp1, tp2, tp3 = price-15, sup, sup-15
    else:
        tvh = f"{sup:.1f} - {sup+3:.1f}"
        sl = sup-9
        tp1, tp2, tp3 = price+15, res, res+15
    txt = f"🐻 NIGHT BEAR V3.1 (H4/H1/M15/M5)\n\n"
    txt += f"XAUUSD {trend_h1} - СИГНАЛ\nЦена: {price:.2f}\n\n"
    txt += f"📊 МУЛЬТИ-ТФ:\nH4: {trend_h4} RSI {df_h4.iloc[-1]['rsi']:.0f}\n"
    txt += f"H1: {pat_h1} RSI {df_h1.iloc[-1]['rsi']:.0f}\n"
    txt += f"M5: {pat_m5} (снайпер)\n\n"
    txt += f"📍 СНР:\nСопротивление: {res}\nПоддержка: {sup}\n\n"
    txt += f"🎯 ПЛАН ДЛЯ РАЗГОНА:\nТВХ ЗОНА: {tvh} (жди!)\n"
    txt += f"SL: {sl:.2f}\nTP1: {tp1:.2f} | TP2: {tp2:.2f} | TP3: {tp3:.2f}\nRR: 1 к 3+"
    return txt

def send(msg):
    if not BOT_TOKEN or not CHAT_ID: 
        print(msg)
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": msg})

if __name__ == "__main__":
    while True:
        try:
            sig = build_signal()
            send(sig)
            print(sig)
        except Exception as e:
            print(f"Error: {e}")
        time.sleep(3600)
