from data_fetcher import get_klines, get_tweets
from technical_analysis import apply_indicators
from sentiment_analysis import sentiment_score

SPIKE_FACTOR = 3.0
CONFIRM_PERIOD = 3
BUY_THRESHOLD = 0.5
SELL_THRESHOLD = -0.5

_history = {}

def detect_spike(df):
    return df['volume'].iloc[-1] > SPIKE_FACTOR * df['volume'][:-1].mean()

def compute_score(symbol):
    df = apply_indicators(get_klines(symbol))
    if not detect_spike(df): return 0.0
    latest = df.iloc[-1]
    # simple TA score
    ta_score = 0
    if latest['rsi'] < 30 and latest['close'] < latest['bb_lower']: ta_score+=1
    if latest['rsi'] > 70 and latest['close'] > latest['bb_upper']: ta_score-=1
    ta_score += 1 if latest['macd'] > latest['macd_sig'] else -1
    ta_score /= 3
    # sentiment
    text_list = get_tweets(symbol[:-4])
    sent = sentiment_score(text_list)
    sent_sig = 1 if sent>0.2 else (-1 if sent<-0.2 else 0)
    return 0.5*ta_score + 0.5*sent_sig

def get_signal(symbol):
    s = compute_score(symbol)
    hist = _history.setdefault(symbol, [])
    hist.append(s)
    if len(hist) < CONFIRM_PERIOD: return 'hold'
    window = hist[-CONFIRM_PERIOD:]
    if all(v>=BUY_THRESHOLD for v in window): return 'buy'
    if all(v<=SELL_THRESHOLD for v in window): return 'sell'
    return 'hold'
