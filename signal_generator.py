from data_fetcher import get_klines, get_tweets
from technical_analysis import apply_indicators
from sentiment_analysis import sentiment_score
from notifier import notify_slack
import requests
import time
import os
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

SPIKE_FACTOR = 3.0
CONFIRM_PERIOD = 3
BUY_THRESHOLD = 0.5
SELL_THRESHOLD = -0.5
MAX_HISTORY_LENGTH = 50  # 각 심볼당 최대 기록 개수

_history = {}

def detect_spike(df):
    return df['volume'].iloc[-1] > SPIKE_FACTOR * df['volume'][:-1].mean()

def compute_score(symbol):
    try:
        df = apply_indicators(get_klines(symbol))
        if not detect_spike(df): return 0.0
        latest = df.iloc[-1]
        # simple TA score
        ta_score = 0
        if latest['rsi'] < 30 and latest['close'] < latest['bb_lower']: ta_score += 1
        if latest['rsi'] > 70 and latest['close'] > latest['bb_upper']: ta_score -= 1
        ta_score += 1 if latest['macd'] > latest['macd_sig'] else -1
        ta_score = (ta_score + 1) / 3  # Normalize to [0,1] range
        
        # sentiment
        text_list = get_tweets(symbol[:-4])
        sent = sentiment_score(text_list)
        sent_sig = 1 if sent>0.2 else (-1 if sent<-0.2 else 0)
        
        # 트윗 감성 분석 결과를 Slack으로 전송
        if text_list:
            tweet_links = [f"https://twitter.com/user/status/{tweet['id']}" for tweet in text_list]
            sentiment_message = (
                f"📊 *{symbol} Sentiment Analysis*\n"
                f"• Score: {sent:.2f}\n"
                f"• Signal: {sent_sig}\n"
                f"• Analyzed Tweets: {len(text_list)}\n"
                f"• Sample Tweet Links:\n"
            )
            # 최대 5개의 트윗 링크만 표시
            for link in tweet_links[:5]:
                sentiment_message += f"  - {link}\n"
            notify_slack(sentiment_message)
        
        final_score = 0.5*ta_score + 0.5*sent_sig
        return final_score
    except Exception as e:
        notify_slack(f"❌ Error in compute_score for {symbol}: {str(e)}")
        return 0.0

def get_signal(symbol):
    s = compute_score(symbol)
    hist = _history.setdefault(symbol, [])
    hist.append(s)
    
    # 히스토리 크기 제한
    if len(hist) > MAX_HISTORY_LENGTH:
        hist = hist[-MAX_HISTORY_LENGTH:]
        _history[symbol] = hist
    
    if len(hist) < CONFIRM_PERIOD: return 'hold', 'Not enough data'
    window = hist[-CONFIRM_PERIOD:]
    if all(v>=BUY_THRESHOLD for v in window): 
        return 'buy', f'Score above buy threshold for {CONFIRM_PERIOD} periods'
    if all(v<=SELL_THRESHOLD for v in window):
        return 'sell', f'Score below sell threshold for {CONFIRM_PERIOD} periods'
    return 'hold', f'Score between thresholds for {CONFIRM_PERIOD} periods'

def cleanup_history():
    """사용되지 않는 심볼의 기록 정리"""
    global _history
    # 가장 오래된 사용 기록이 있는 심볼부터 제거 (간단한 메모리 관리)
    if len(_history) > 100:  # 100개 이상 심볼이 기록되면
        # 심볼 목록 중 절반만 유지
        symbols = list(_history.keys())
        to_remove = symbols[:len(symbols)//2]
        for sym in to_remove:
            del _history[sym]

def get_tweets(symbol):
    """트위터에서 관련 트윗 가져오기"""
    try:
        # Get Twitter API token from environment variables
        twitter_token = os.getenv("TWITTER_BEARER_TOKEN")
        if not twitter_token:
            notify_slack("❌ Twitter API token not found in environment variables")
            return []
            
        # Twitter API 호출 전 상태 확인
        response = requests.get(
            "https://api.twitter.com/2/tweets/search/recent",
            headers={"Authorization": f"Bearer {twitter_token}"},
            params={"query": f"#{symbol} lang:en", "max_results": 50}  # 최대 결과 수를 50으로 제한
        )
        
        # Rate limit 정보 확인
        if 'x-rate-limit-remaining' in response.headers:
            remaining = int(response.headers['x-rate-limit-remaining'])
            reset_time = int(response.headers['x-rate-limit-reset'])
            
            # Rate limit이 임계값 이하일 때 경고
            if remaining < 5:  # 임계값을 5로 낮춤
                notify_slack(f"⚠️ Twitter API rate limit warning: {remaining} calls remaining")
                return []  # Rate limit이 낮으면 빈 결과 반환
            
            # Rate limit 초과 시
            if response.status_code == 429:
                reset_time = int(response.headers['x-rate-limit-reset'])
                wait_time = reset_time - int(time.time())
                notify_slack(f"❌ Twitter API rate limit exceeded. Skipping tweets for {symbol}")
                return []  # Rate limit 초과 시 빈 결과 반환
            
        response.raise_for_status()
        return response.json().get('data', [])
    except Exception as e:
        notify_slack(f"❌ Twitter API error for {symbol}: {str(e)}")
        return []
