import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from unittest.mock import patch, MagicMock
import pandas as pd
from datetime import datetime

from data_fetcher import get_symbols, get_klines, get_tweets

@pytest.fixture
def mock_binance_client():
    with patch('data_fetcher.client') as mock_client:
        yield mock_client

@pytest.fixture
def mock_twitter_client():
    with patch('data_fetcher.twitter_client') as mock_client:
        yield mock_client

def test_get_symbols(mock_binance_client):
    # Mock the futures_exchange_info response
    mock_binance_client.futures_exchange_info.return_value = {
        'symbols': [
            {'symbol': 'BTCUSDT', 'status': 'TRADING'},
            {'symbol': 'ETHUSDT', 'status': 'TRADING'},
            {'symbol': 'XRPUSDT', 'status': 'HALT'},
        ]
    }
    
    symbols = get_symbols()
    assert len(symbols) == 2
    assert 'BTCUSDT' in symbols
    assert 'ETHUSDT' in symbols
    assert 'XRPUSDT' not in symbols

def test_get_klines(mock_binance_client):
    # Mock the futures_klines response
    mock_data = [
        [1610000000000, '50000', '51000', '49000', '50500', '1000', 1610000599999,
         '50000000', 1000, '500', '25000000', '0'],
        [1610000600000, '50500', '51500', '49500', '51000', '1200', 1610001199999,
         '60000000', 1200, '600', '30000000', '0']
    ]
    mock_binance_client.futures_klines.return_value = mock_data
    
    df = get_klines('BTCUSDT')
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 2
    assert 'open_time' in df.columns
    assert 'close' in df.columns
    assert 'volume' in df.columns
    assert df['close'].dtype == float
    assert df['volume'].dtype == float

def test_get_tweets(mock_twitter_client):
    # Mock the search_recent_tweets response
    mock_tweets = MagicMock()
    mock_tweets.data = [
        MagicMock(text='Tweet 1'),
        MagicMock(text='Tweet 2')
    ]
    mock_twitter_client.search_recent_tweets.return_value = mock_tweets
    
    tweets = get_tweets('BTC')
    assert len(tweets) == 2
    assert 'Tweet 1' in tweets
    assert 'Tweet 2' in tweets

def test_get_tweets_empty(mock_twitter_client):
    # Mock empty response
    mock_tweets = MagicMock()
    mock_tweets.data = None
    mock_twitter_client.search_recent_tweets.return_value = mock_tweets
    
    tweets = get_tweets('BTC')
    assert len(tweets) == 0 