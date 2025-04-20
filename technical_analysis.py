import talib

def apply_indicators(df):
    price = df['close'].values
    df['rsi'] = talib.RSI(price, timeperiod=14)
    macd, macd_sig, _ = talib.MACD(price, fastperiod=12, slowperiod=26, signalperiod=9)
    df['macd'], df['macd_sig'] = macd, macd_sig
    upper, mid, lower = talib.BBANDS(price, timeperiod=20)
    df['bb_upper'], df['bb_mid'], df['bb_lower'] = upper, mid, lower
    return df
