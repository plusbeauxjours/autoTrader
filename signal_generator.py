from data_fetcher import get_klines, get_tweets
from technical_analysis import apply_indicators
from sentiment_analysis import sentiment_score

SPIKE_FACTOR = 3.0
CONFIRM_PERIOD = 3
BUY_THRESHOLD = 0.5
SELL_THRESHOLD = -0.5
MAX_HISTORY_LENGTH = 50  # 각 심볼당 최대 기록 개수

_history = {}

def detect_spike(df):
    return df['volume'].iloc[-1] > SPIKE_FACTOR * df['volume'][:-1].mean()

def compute_score(symbol):
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
    final_score = 0.5*ta_score + 0.5*sent_sig
    return final_score

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
