import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from unittest.mock import patch, MagicMock
import os
import time
from datetime import datetime

from main import notify_slack, fetch_all_prices, trade_logic, monitor

@pytest.fixture
def mock_env():
    with patch.dict('os.environ', {
        'SLACK_WEBHOOK_URL': 'https://hooks.slack.com/test',
        'BINANCE_API_KEY': 'test_key',
        'BINANCE_API_SECRET': 'test_secret'
    }):
        yield

@pytest.fixture
def mock_session():
    with patch('main.session') as mock:
        yield mock

def test_notify_slack(mock_env, mock_session):
    mock_session.post.return_value = MagicMock(status_code=200)
    
    notify_slack("Test message")
    
    mock_session.post.assert_called_once()
    assert "Test message" in mock_session.post.call_args[1]['json']['text']

def test_notify_slack_error(mock_env, mock_session):
    mock_session.post.side_effect = Exception("Connection error")
    
    # Should not raise exception
    notify_slack("Test message")

def test_fetch_all_prices(mock_session):
    mock_response = MagicMock()
    mock_response.json.return_value = [
        {'symbol': 'BTCUSDT', 'price': '50000.0'},
        {'symbol': 'ETHUSDT', 'price': '3000.0'},
        {'symbol': 'XRPBTC', 'price': '0.0001'}  # Should be filtered out
    ]
    mock_session.get.return_value = mock_response
    
    prices = fetch_all_prices()
    
    assert len(prices) == 2
    assert prices['BTCUSDT'] == 50000.0
    assert prices['ETHUSDT'] == 3000.0
    assert 'XRPBTC' not in prices

def test_fetch_all_prices_error(mock_session):
    mock_session.get.side_effect = Exception("API Error")
    
    prices = fetch_all_prices()
    assert prices == {}

@patch('main.get_symbols')
@patch('main.get_signal')
@patch('main.get_klines')
@patch('main.RiskManager')
@patch('main.TradeExecutor')
@patch('main.log_trade')
@patch('main.notify')
def test_trade_logic(mock_notify, mock_log_trade, mock_trade_executor, mock_risk_manager,
                    mock_get_klines, mock_get_signal, mock_get_symbols):
    # Setup mocks
    mock_get_symbols.return_value = ['BTCUSDT']
    mock_get_signal.return_value = 'buy'
    mock_get_klines.return_value = MagicMock(
        __getitem__=lambda self, key: MagicMock(
            iloc=MagicMock(
                __getitem__=lambda self, idx: 50000.0
            ),
            min=lambda: 49000.0,
            max=lambda: 51000.0
        )
    )
    mock_risk_manager.return_value.can_trade.return_value = True
    mock_risk_manager.return_value.size_leverage.return_value = (1.0, 10)
    mock_trade_executor.return_value.cli.futures_account_balance.return_value = [
        {}, {}, {}, {}, {}, {}, {'balance': '10000.0'}
    ]
    
    trade_logic()
    
    # Verify trade execution
    mock_trade_executor.return_value.set_leverage.assert_called_once()
    mock_trade_executor.return_value.enter_limit.assert_called_once()
    mock_trade_executor.return_value.place_oco.assert_called_once()
    mock_log_trade.assert_called_once()
    mock_notify.assert_called_once()

@patch('main.fetch_all_prices')
@patch('main.trade_logic')
@patch('main.notify_slack')
@patch('time.sleep')
def test_monitor(mock_sleep, mock_notify_slack, mock_trade_logic, mock_fetch_prices):
    # Setup mock prices
    initial_prices = {'BTCUSDT': 50000.0, 'ETHUSDT': 3000.0}
    current_prices = {'BTCUSDT': 51500.0, 'ETHUSDT': 3000.0}  # 3% increase in BTC
    
    mock_fetch_prices.side_effect = [initial_prices, current_prices]
    mock_sleep.side_effect = KeyboardInterrupt()  # To break the infinite loop
    
    monitor()
    
    # Verify monitoring behavior
    mock_notify_slack.assert_called()
    mock_trade_logic.assert_called_once()  # Should be called for BTC price change
    assert mock_sleep.call_count >= 1 