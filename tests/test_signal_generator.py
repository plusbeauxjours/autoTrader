import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from unittest.mock import patch, MagicMock
import pandas as pd
import numpy as np

from signal_generator import detect_spike, compute_score, get_signal

@pytest.fixture
def sample_dataframe():
    return pd.DataFrame({
        'volume': [100, 200, 300, 400, 500, 2000],  # Last value is a spike
        'close': [100, 101, 102, 103, 104, 105],
        'rsi': [25, 26, 27, 28, 29, 30],
        'bb_lower': [95, 96, 97, 98, 99, 100],
        'bb_upper': [105, 106, 107, 108, 109, 110],
        'macd': [1, 2, 3, 4, 5, 6],
        'macd_sig': [0.5, 1.5, 2.5, 3.5, 4.5, 5.5]
    })

def test_detect_spike(sample_dataframe):
    # Test with spike
    assert detect_spike(sample_dataframe) == True
    
    # Test without spike
    no_spike_df = sample_dataframe.copy()
    no_spike_df['volume'] = [100, 200, 300, 400, 500, 600]
    assert detect_spike(no_spike_df) == False

@patch('signal_generator.get_klines')
@patch('signal_generator.get_tweets')
@patch('signal_generator.sentiment_score')
@patch('signal_generator.apply_indicators')
def test_compute_score(mock_apply_indicators, mock_sentiment_score, mock_get_tweets, mock_get_klines, sample_dataframe):
    # Setup mocks
    mock_apply_indicators.return_value = sample_dataframe
    mock_sentiment_score.return_value = 0.3  # Positive sentiment
    mock_get_tweets.return_value = ['positive tweet']
    
    # Verify mock setup
    mock_get_tweets.assert_not_called()
    mock_sentiment_score.assert_not_called()
    
    score = compute_score('BTCUSDT')
    
    # Verify mock calls
    mock_get_tweets.assert_called_once_with('BTC')  # symbol[:-4]
    mock_sentiment_score.assert_called_once_with(['positive tweet'])
    
    # Calculate expected score
    # ta_score = (1 + 1) / 3 = 0.666... (1 for RSI < 30 and close < bb_lower, 1 for MACD > MACD_sig)
    # sent_sig = 1 (because 0.3 > 0.2)
    # final_score = 0.5 * 0.666... + 0.5 * 1 = 0.833...
    expected_score = 0.5 * (2/3) + 0.5 * 1  # 0.833...
    
    # Verify the score calculation with a small tolerance for floating point imprecision
    assert abs(score - expected_score) < 0.0001, f"Expected score {expected_score}, got {score}"

def test_get_signal():
    # Test buy signal
    symbol = 'BTCUSDT'
    for _ in range(3):  # CONFIRM_PERIOD
        signal = get_signal(symbol)
    assert signal == 'hold'  # Initial state
    
    # Mock compute_score to return values above BUY_THRESHOLD
    with patch('signal_generator.compute_score', return_value=0.6):
        for _ in range(3):
            signal = get_signal(symbol)
        assert signal == 'buy'
    
    # Mock compute_score to return values below SELL_THRESHOLD
    with patch('signal_generator.compute_score', return_value=-0.6):
        for _ in range(3):
            signal = get_signal(symbol)
        assert signal == 'sell'
    
    # Mock compute_score to return values between thresholds
    with patch('signal_generator.compute_score', return_value=0.0):
        for _ in range(3):
            signal = get_signal(symbol)
        assert signal == 'hold' 