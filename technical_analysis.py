import ta
import pandas as pd

def apply_indicators(df):
    # 인덱스가 필요한 경우 설정
    if 'open_time' in df.columns:
        df = df.set_index('open_time', drop=False)
    
    # pandas 데이터프레임과 호환되도록 close 컬럼 확인
    price_col = 'close'
    if price_col not in df.columns:
        raise ValueError(f"DataFrame must have a '{price_col}' column")
    
    # RSI 계산 (ta 라이브러리 사용)
    df['rsi'] = ta.momentum.RSIIndicator(df[price_col], window=14).rsi()
    
    # MACD 계산
    macd_indicator = ta.trend.MACD(
        df[price_col], 
        window_slow=26, 
        window_fast=12, 
        window_sign=9
    )
    df['macd'] = macd_indicator.macd()
    df['macd_sig'] = macd_indicator.macd_signal()
    
    # 볼린저 밴드 계산
    bollinger = ta.volatility.BollingerBands(
        df[price_col], 
        window=20, 
        window_dev=2
    )
    df['bb_upper'] = bollinger.bollinger_hband()
    df['bb_mid'] = bollinger.bollinger_mavg()
    df['bb_lower'] = bollinger.bollinger_lband()
    
    # 인덱스가 설정되었으면 다시 복원
    if 'open_time' in df.columns and df.index.name == 'open_time':
        df = df.reset_index(drop=True)
        
    return df
