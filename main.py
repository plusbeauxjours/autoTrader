import os
import time
import logging
import requests
import atexit
from datetime import datetime, timedelta
from dotenv import load_dotenv

from data_fetcher import get_symbols, get_klines
from signal_generator import get_signal, cleanup_history
from risk_manager import RiskManager
from trade_executor import TradeExecutor
from logger import log_trade, daily_report
from notifier import notify

# 환경 변수 설정
def setup_environment():
    """환경 변수 설정 및 로깅 초기화"""
    # Azure VM에서 실행 중인지 확인
    azure_env_path = "/home/azureuser/AutoBot/.env"
    local_env_path = ".env"
    
    # 먼저 로컬 환경 변수 시도
    load_dotenv(local_env_path)
    
    # Azure VM 환경 확인 및 설정
    is_azure_vm = os.path.exists("/home/azureuser/AutoBot")
    if is_azure_vm and os.path.exists(azure_env_path):
        load_dotenv(azure_env_path, override=True)
        
    # 로깅 설정
    log_handlers = []
    log_format = "%(asctime)s %(levelname)s %(message)s"
    
    # 콘솔 핸들러 추가
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(log_format))
    log_handlers.append(console_handler)
    
    # Azure VM에서는 파일 로깅 추가
    if is_azure_vm:
        log_path = "/home/azureuser/AutoBot/bot.log"
        file_handler = logging.FileHandler(log_path)
        file_handler.setFormatter(logging.Formatter(log_format))
        log_handlers.append(file_handler)
    
    # 루트 로거 설정
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # 기존 핸들러 제거 및 새 핸들러 추가
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    for handler in log_handlers:
        root_logger.addHandler(handler)
    
    # 환경 정보 로깅
    webhook_url = os.getenv("SLACK_WEBHOOK_URL")
    if webhook_url:
        masked_url = webhook_url[:15] + "..." + webhook_url[-10:] if len(webhook_url) > 30 else webhook_url
        logging.info(f"SLACK_WEBHOOK_URL 설정됨: {masked_url}")
    else:
        logging.warning("SLACK_WEBHOOK_URL이 설정되지 않았습니다!")
    
    return {
        "SLACK_WEBHOOK_URL": webhook_url,
        "IS_AZURE_VM": is_azure_vm
    }

# 환경 설정 및 변수 초기화
env_config = setup_environment()
SLACK_WEBHOOK_URL = env_config["SLACK_WEBHOOK_URL"]
IS_AZURE_VM = env_config["IS_AZURE_VM"]
THRESHOLD = 3.0  # 가격 변동 감지 임계값 (%)
INTERVAL = 60    # 모니터링 간격 (초)
MAX_SYMBOLS = 500  # 최대 모니터링 심볼 수

# 글로벌 변수
session = requests.Session()
last_prices = {}
balance_cache = {'value': None, 'timestamp': None}
balance_cache_duration = 300  # 5분
last_cleanup_time = datetime.now()
cleanup_interval = 3600  # 1시간마다 메모리 정리

# 슬랙 연결 테스트
def test_slack_connection():
    """슬랙 연결 테스트"""
    if not SLACK_WEBHOOK_URL:
        logging.error("Slack 연결 테스트 실패: Webhook URL이 설정되지 않았습니다.")
        return False
        
    try:
        r = requests.post(SLACK_WEBHOOK_URL, json={"text": "🚀 AutoBot 시작 테스트 메시지"}, timeout=10)
        status = r.status_code
        logging.info(f"Slack 테스트 요청 응답: {status} {r.text}")
        if status != 200:
            logging.error(f"Slack 연결 테스트 실패: HTTP 상태 코드 {status}")
            return False
        return True
    except Exception as e:
        logging.exception(f"Slack 연결 테스트 중 오류 발생: {e}")
        return False

def cleanup_resources():
    """프로그램 종료 시 리소스 정리"""
    if session:
        session.close()
    try:
        notify_slack("🛑 Bot shutting down, cleaning up resources")
    except Exception as e:
        logging.error(f"종료 알림 전송 중 오류: {e}")

# 종료 시 리소스 정리 등록
atexit.register(cleanup_resources)

def get_cached_balance(exec):
    """잔고 정보를 캐시하여 불필요한 API 호출 방지"""
    now = datetime.now()
    if (balance_cache['value'] is None or 
        balance_cache['timestamp'] is None or 
        (now - balance_cache['timestamp']).total_seconds() > balance_cache_duration):
        try:
            balance_cache['value'] = float(exec.cli.futures_account_balance()[6]['balance'])
            balance_cache['timestamp'] = now
        except Exception as e:
            logging.error(f"잔고 정보 조회 중 오류: {e}")
            if balance_cache['value'] is None:
                balance_cache['value'] = 0.0
    return balance_cache['value']

def perform_periodic_cleanup():
    """주기적인 메모리 정리 수행"""
    now = datetime.now()
    
    # balance_cache가 없거나 timestamp가 None인 경우 초기화
    if 'balance_cache' not in globals() or balance_cache['timestamp'] is None:
        balance_cache['timestamp'] = now
        balance_cache['balance'] = None
        return
        
    # 24시간 이상 지난 경우 캐시 초기화
    if (now - balance_cache['timestamp']).total_seconds() > 86400:
        balance_cache['timestamp'] = now
        balance_cache['balance'] = None
        notify_slack("🧹 Balance cache cleared after 24 hours")

def notify_slack(message):
    """슬랙으로 메시지 전송"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log = f"[{timestamp}] {message}"
    print(log)
    
    if not SLACK_WEBHOOK_URL:
        logging.warning("Slack 메시지 전송 실패: Webhook URL이 설정되지 않았습니다.")
        return
        
    try:
        response = session.post(SLACK_WEBHOOK_URL, json={"text": log}, timeout=10)
        if response.status_code != 200:
            logging.error(f"Slack 전송 실패: 상태 코드 {response.status_code}, 응답: {response.text}")
    except Exception as e:
        logging.error(f"Slack 알림 전송 중 오류: {e}")

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
        logging.error(f"가격 조회 오류: {e}")
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
    except Exception as e:
        notify_slack(f"❌ Signal generation error for {trigger_symbol}: {str(e)}")
        return
        
    # 매수/매도 신호가 없으면 종료
    if sig not in ('buy', 'sell'):
        return
            
    # 실행 단계
    notify_slack(f"🎯 Trade signal detected for {trigger_symbol}: {sig}")
    
    # 트레이드 실행기 초기화 및 재시도 로직
    max_retries = 3
    retry_delay = 5  # seconds
    
    for attempt in range(max_retries):
        try:
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
            
            # 성공적으로 완료되면 루프 종료
            break
            
        except (requests.exceptions.RequestException, ConnectionError) as e:
            if attempt < max_retries - 1:
                notify_slack(f"⚠️ Connection error (attempt {attempt + 1}/{max_retries}): {str(e)}")
                time.sleep(retry_delay)
                continue
            else:
                notify_slack(f"❌ Trading error for {trigger_symbol}: Max retries exceeded. Last error: {str(e)}")
                return
        except Exception as e:
            notify_slack(f"❌ Trading error for {trigger_symbol}: {str(e)}")
            return

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
        
        # 주기적 메모리 정리
        perform_periodic_cleanup()
        
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
    notify_slack("🤖 AutoBot이 시작되었습니다!")
    
    # 슬랙 연결 테스트
    slack_working = test_slack_connection()
    if not slack_working:
        logging.warning("⚠️ Slack 연결 테스트 실패, 로컬 로깅만 사용합니다.")
    
    try:
        monitor()
    except KeyboardInterrupt:
        notify_slack("\n🛑 Bot stopped by user")
        cleanup_resources()
    except Exception as e:
        error_msg = f"❌ Critical error: {e}"
        notify_slack(error_msg)
        logging.exception(error_msg)
        cleanup_resources()