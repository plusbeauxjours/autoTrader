import os
import time
import requests
from datetime import datetime, timedelta

from data_fetcher import get_symbols, get_klines
from signal_generator import get_signal
from risk_manager import RiskManager
from trade_executor import TradeExecutor
from logger import log_trade, daily_report
from notifier import notify

# 환경변수 설정
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")
THRESHOLD = 3.0  # 가격 변동 감지 임계값 (%)
INTERVAL = 60    # 모니터링 간격 (초)

# 세션 재사용으로 성능 향상
session = requests.Session()
last_prices = {}

# 캐시 변수 추가
balance_cache = {'value': None, 'timestamp': None}
balance_cache_duration = 300  # 5분

def get_cached_balance(exec):
    """잔고 정보를 캐시하여 불필요한 API 호출 방지"""
    now = datetime.now()
    if (balance_cache['value'] is None or 
        balance_cache['timestamp'] is None or 
        (now - balance_cache['timestamp']).total_seconds() > balance_cache_duration):
        balance_cache['value'] = float(exec.cli.futures_account_balance()[6]['balance'])
        balance_cache['timestamp'] = now
    return balance_cache['value']

def notify_slack(message):
    """슬랙으로 메시지 전송"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log = f"[{timestamp}] {message}"
    print(log)
    if SLACK_WEBHOOK_URL:
        try:
            session.post(SLACK_WEBHOOK_URL, json={"text": log}, timeout=5)
        except Exception as e:
            print(f"[{timestamp}] Slack failed: {e}")

def fetch_all_prices():
    """모든 USDT 페어의 현재 가격 조회"""
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

def trade_logic(trigger_symbol):
    """트레이딩 로직 실행 - 특정 심볼에 대해서만 실행"""
    if not trigger_symbol:
        return
        
    notify_slack(f"\n🔄 Starting trade logic for {trigger_symbol}...")
    risk = RiskManager()
    
    # 거래 가능 여부 확인
    if not risk.can_trade(trigger_symbol):
        notify_slack(f"⏭️ Skipping {trigger_symbol} - trading not allowed")
        return
    
    # 시그널 확인
    notify_slack(f"📡 Analyzing {trigger_symbol}...")
    try:
        sig, reason = get_signal(trigger_symbol)
        notify_slack(f"📊 Signal for {trigger_symbol}: {sig}")
        notify_slack(f"📈 Reason: {reason}")
        
        # 매수/매도 신호가 없으면 종료
        if sig not in ('buy', 'sell'):
            return
            
        # 실행 단계
        notify_slack(f"🎯 Trade signal detected for {trigger_symbol}: {sig}")
        
        # 트레이드 실행기 초기화
        exec = TradeExecutor()
        balance = get_cached_balance(exec)
        notify_slack(f"💰 Current balance: {balance:.2f} USDT")
        
        # 가격 데이터 조회
        df = get_klines(trigger_symbol)
        entry = df['close'].iloc[-1]
        stop = df['close'][:-1].min() if sig == 'buy' else df['close'][:-1].max()
        notify_slack(f"📈 Entry price: {entry:.2f}, Stop price: {stop:.2f}")
        
        # 포지션 크기 및 레버리지 계산
        qty, lev = risk.size_leverage(balance, entry, stop)
        notify_slack(f"📊 Position size: {qty:.3f}, Leverage: {lev}x")
        
        # 레버리지 설정
        exec.set_leverage(trigger_symbol, lev)
        notify_slack(f"⚙️ Set leverage for {trigger_symbol} to {lev}x")
        
        # 주문 실행
        order_side = 'BUY' if sig == 'buy' else 'SELL'
        exec.enter_limit(trigger_symbol, order_side, qty, entry)
        notify_slack(f"✅ Entered {sig} order for {trigger_symbol} at {entry:.2f}")
        
        # TP/SL 설정
        tp = entry * 1.10 if sig == 'buy' else entry * 0.90
        exec.place_oco(trigger_symbol, 'SELL' if sig == 'buy' else 'BUY', qty, stop, tp)
        notify_slack(f"✅ Placed OCO order - TP: {tp:.2f}, SL: {stop:.2f}")
        
        # 예상 PnL 계산 및 등록
        pnl = (tp - entry) / entry * qty * lev
        risk.register(pnl, trigger_symbol)
        notify_slack(f"📊 Expected PnL: {pnl:.2f} USDT")
        
        # 로그 기록 및 알림
        log_trade({'symbol': trigger_symbol, 'side': sig, 'entry': entry, 'exit': tp, 'pnl': pnl})
        notify(f"{trigger_symbol} {sig}@{entry:.2f}, qty={qty:.3f}, lev={lev}x")
        notify_slack(f"📝 Trade logged and notification sent")
        
    except Exception as e:
        notify_slack(f"❌ Trading error for {trigger_symbol}: {e}")

def monitor():
    """가격 모니터링 및 이상 징후 감지"""
    global last_prices
    
    notify_slack("\n🚀 Starting Binance anomaly monitor + trader")
    
    # 초기 가격 데이터 로드
    last_prices = fetch_all_prices()
    if not last_prices:
        notify_slack("❌ Initial fetch failed. Exit.")
        return

    # 매일 보고서 날짜 추적
    last_report_day = datetime.now().day
    
    # 메인 모니터링 루프
    while True:
        # 주기적 데일리 리포트 생성
        current_day = datetime.now().day
        if current_day != last_report_day:
            daily_report()
            last_report_day = current_day
        
        print("\n🔁 Monitoring prices...")
        time.sleep(INTERVAL)
        
        # 최신 가격 조회
        current_prices = fetch_all_prices()
        if not current_prices:
            continue

        # 가격 변동 확인
        for symbol in current_prices:
            old = last_prices.get(symbol)
            if old is None:
                continue
                
            new = current_prices[symbol]
            change_pct = (new - old) / old * 100
            
            # 이상 징후 감지
            if abs(change_pct) >= THRESHOLD:
                notify_slack(f"🚨 Anomaly detected: {symbol} {change_pct:+.2f}%")
                
                # 해당 심볼에 대해 트레이딩 로직 실행
                trade_logic(symbol)

        # 가격 데이터 업데이트
        last_prices = current_prices

if __name__ == "__main__":
    try:
        monitor()
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped by user")
    except Exception as e:
        notify_slack(f"❌ Critical error: {e}")