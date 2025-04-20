import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from unittest.mock import patch
import time

from risk_manager import RiskManager

@pytest.fixture
def risk_manager():
    return RiskManager(max_daily=5, max_streak=3, cooldown_m=30, risk=0.02)

def test_can_trade(risk_manager):
    # Test initial state
    assert risk_manager.can_trade('BTCUSDT') == True
    
    # Test max daily trades
    risk_manager.trades = 5
    assert risk_manager.can_trade('BTCUSDT') == False
    
    # Test max streak
    risk_manager.trades = 0
    risk_manager.streak = 3
    assert risk_manager.can_trade('BTCUSDT') == False
    
    # Test cooldown
    risk_manager.streak = 0
    risk_manager.last['BTCUSDT'] = time.time()
    assert risk_manager.can_trade('BTCUSDT') == False

def test_register(risk_manager):
    # Test positive PnL
    risk_manager.register(100, 'BTCUSDT')
    assert risk_manager.streak == 0
    assert risk_manager.trades == 1
    assert 'BTCUSDT' in risk_manager.last
    
    # Test negative PnL
    risk_manager.register(-100, 'ETHUSDT')
    assert risk_manager.streak == 1
    assert risk_manager.trades == 2
    assert 'ETHUSDT' in risk_manager.last

def test_size_leverage(risk_manager):
    # Test with small price difference (<=1%)
    qty, lev = risk_manager.size_leverage(10000, 100, 99)
    assert lev == 10
    assert qty == 200  # (10000 * 0.02) / (100 - 99)
    
    # Test with medium price difference (<=2%)
    qty, lev = risk_manager.size_leverage(10000, 100, 98)
    assert lev == 5
    assert qty == 100  # (10000 * 0.02) / (100 - 98)
    
    # Test with large price difference (>2%)
    qty, lev = risk_manager.size_leverage(10000, 100, 95)
    assert lev == 2
    assert qty == 40  # (10000 * 0.02) / (100 - 95)

@patch('time.time')
def test_daily_reset(mock_time, risk_manager):
    # Set initial time
    mock_time.return_value = 0
    risk_manager.start = 0
    
    # Simulate trades
    risk_manager.trades = 4
    risk_manager.streak = 2
    
    # Advance time by 24 hours + 1 second
    mock_time.return_value = 86401
    
    # Should reset counters
    assert risk_manager.can_trade('BTCUSDT') == True
    assert risk_manager.trades == 0
    assert risk_manager.streak == 0 