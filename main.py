import os
import time
import requests
from datetime import datetime

from data_fetcher import get_symbols, get_klines
from signal_generator import get_signal
from risk_manager import RiskManager
from trade_executor import TradeExecutor
from logger import log_trade, daily_report
from notifier import notify

SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")
THRESHOLD = 3.0  # % change to trigger
INTERVAL = 60    # check every 60 seconds

session = requests.Session()
last_prices = {}

def notify_slack(message):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log = f"[{timestamp}] {message}"
    print(log)
    if SLACK_WEBHOOK_URL:
        try:
            session.post(SLACK_WEBHOOK_URL, json={"text": log}, timeout=5)
        except Exception as e:
            print(f"[{timestamp}] Slack failed: {e}")

def fetch_all_prices():
    print("\n🔍 Fetching all prices...")
    url = 'https://fapi.binance.com/fapi/v1/ticker/price'
    try:
        res = session.get(url, timeout=5)
        res.raise_for_status()
        prices = {
            item['symbol']: float(item['price'])
            for item in res.json()
            if item['symbol'].endswith('USDT')
        }
        print(f"✅ Successfully fetched prices for {len(prices)} pairs")
        return prices
    except Exception as e:
        notify_slack(f"❌ Price fetch error: {e}")
        return {}

def trade_logic():
    print("\n🔄 Starting trade logic...")
    syms = get_symbols()
    risk = RiskManager()
    exec = TradeExecutor()
    balance = float(exec.cli.futures_account_balance()[6]['balance'])
    print(f"💰 Current balance: {balance:.2f} USDT")

    for sym in syms:
        if not risk.can_trade(sym):
            print(f"⏭️ Skipping {sym} - trading not allowed")
            continue
            
        print(f"\n📡 Checking signal for: {sym}")
        try:
            sig = get_signal(sym)
            print(f"📊 Signal for {sym}: {sig}")
        except Exception as e:
            print(f"❌ Signal error for {sym}: {e}")
            time.sleep(1)
            continue

        if sig in ('buy', 'sell'):
            notify_slack(f"🎯 Trade signal detected for {sym}: {sig}")
            df = get_klines(sym)
            entry = df['close'].iloc[-1]
            stop = df['close'][:-1].min() if sig == 'buy' else df['close'][:-1].max()
            notify_slack(f"📈 Entry price: {entry:.2f}, Stop price: {stop:.2f}")
            
            qty, lev = risk.size_leverage(balance, entry, stop)
            notify_slack(f"📊 Position size: {qty:.3f}, Leverage: {lev}x")
            
            exec.set_leverage(sym, lev)
            notify_slack(f"⚙️ Set leverage for {sym} to {lev}x")
            
            exec.enter_limit(sym, 'BUY' if sig == 'buy' else 'SELL', qty, entry)
            notify_slack(f"✅ Entered {sig} order for {sym} at {entry:.2f}")
            
            tp = entry * 1.10 if sig == 'buy' else entry * 0.90
            exec.place_oco(sym, 'SELL' if sig == 'buy' else 'BUY', qty, stop, tp)
            notify_slack(f"✅ Placed OCO order - TP: {tp:.2f}, SL: {stop:.2f}")
            
            pnl = (tp - entry) / entry * qty
            risk.register(pnl, sym)
            notify_slack(f"📊 Expected PnL: {pnl:.2f} USDT")
            
            log_trade({'symbol': sym, 'side': sig, 'entry': entry, 'exit': tp, 'pnl': pnl})
            notify(f"{sym} {sig}@{entry:.2f}, qty={qty:.3f}, lev={lev}x")
            notify_slack(f"📝 Trade logged and notification sent")

        time.sleep(1)

def monitor():
    global last_prices
    notify_slack("🚀 Binance anomaly monitor + trader started.")
    
    last_prices = fetch_all_prices()
    if not last_prices:
        notify_slack("❌ Initial fetch failed. Exit.")
        return

    while True:
        print("\n🔁 Monitoring prices...")
        time.sleep(INTERVAL)
        current_prices = fetch_all_prices()
        if not current_prices:
            continue

        for symbol in current_prices:
            old = last_prices.get(symbol)
            new = current_prices[symbol]
            if old is None:
                continue
            change_pct = (new - old) / old * 100
            if abs(change_pct) >= THRESHOLD:
                notify_slack(f"🚨 Detected anomaly: {symbol} {change_pct:+.2f}%")
                trade_logic()  # 📈 이상 징후 감지 시 트레이딩 진입

        last_prices = current_prices  # 재사용

if __name__ == "__main__":
    monitor()