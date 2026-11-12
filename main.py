import os
from flask import Flask
from threading import Thread
import requests, telebot, time

TOKEN=os.environ.get("TELEGRAM_BOT_TOKEN")
bot=telebot.TeleBot(TOKEN)
app=Flask('')

@app.route('/')
def home(): return "Night Bear OK"

def run(): app.run(host='0.0.0.0',port=8080)
Thread(target=run,daemon=True).start()

def get_klines():
 try:
  u="https://api.binance.com/api/v3/klines?symbol=PAXGUSDT&interval=15m&limit=250"
  r=requests.get(u,timeout=10).json()
  return [float(x[4]) for x in r]
 except: return None

def ema(d,p):
 k=2/(p+1); v=[sum(d[:p])/p]
 for x in d[p:]: v.append(x*k+v[-1]*(1-k))
 return v[-1]

def rsi(d,per=14):
 dl=[d[i+1]-d[i] for i in range(len(d)-1)]
 g=[max(x,0) for x in dl[-per:]]; l=[abs(min(x,0)) for x in dl[-per:]]
 ag=sum(g)/per; al=sum(l)/per
 return 70 if al==0 else 100-(100/(1+ag/al))

@bot.message_handler(commands=['start'])
def s(m): bot.reply_to(m,"🐻 Night Bear!\nКоманды:\n/signal - сигнал сейчас (на русском, стиль Exness)")

@bot.message_handler(commands=['signal'])
def sig(m):
 c=get_klines()
 if not c:
  bot.reply_to(m,"⚠️ Биржа не отвечает");return
 price=c[-1]; e50=ema(c,50); e200=ema(c,200); r=rsi(c,14)
 if price>e50>e200 and r>50:
  bot.reply_to(m,f"🐻 BUY 🟢\nЦена ${price:.2f}\nВход ${price:.2f}\nСтоп ${price-12:.2f}\nTP1 ${price+8:.2f} TP2 ${price+18:.2f} TP3 ${price+32:.2f}\nТренд: выше EMA50 {e50:.2f} EMA200 {e200:.2f} RSI {r:.1f}")
 elif price<e50<e200 and r<50:
  bot.reply_to(m,f"🐻 SELL 🔴\nЦена ${price:.2f}\nВход ${price:.2f}\nСтоп ${price+12:.2f}\nTP1 ${price-8:.2f} TP2 ${price-18:.2f} TP3 ${price-32:.2f}\nТренд: ниже EMA50/200 как в Exness RSI {r:.1f}")
 else:
  bot.reply_to(m,f"🐻 ОЖИДАНИЕ ⚪\nЦена ${price:.2f}\nEMA50 {e50:.2f} EMA200 {e200:.2f} RSI {r:.1f}\nНет четкого тренда")

bot.infinity_polling()
