import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from unittest.mock import patch, MagicMock

from trade_executor import TradeExecutor

@pytest.fixture
def trade_executor():
    return TradeExecutor()

def test_set_leverage(trade_executor):
    with patch.object(trade_executor.cli, 'futures_change_margin_type') as mock_margin, \
         patch.object(trade_executor.cli, 'futures_change_leverage') as mock_leverage:
        
        trade_executor.set_leverage('BTCUSDT', 10)
        
        mock_margin.assert_called_once_with(symbol='BTCUSDT', marginType='ISOLATED')
        mock_leverage.assert_called_once_with(symbol='BTCUSDT', leverage=10)

def test_enter_limit(trade_executor):
    with patch.object(trade_executor.cli, 'futures_create_order') as mock_order:
        mock_order.return_value = {'orderId': 12345}
        
        result = trade_executor.enter_limit('BTCUSDT', 'BUY', 1.0, 50000.0)
        
        mock_order.assert_called_once_with(
            symbol='BTCUSDT',
            side='BUY',
            type='LIMIT',
            timeInForce='GTC',
            quantity=1.0,
            price=50000.0
        )
        assert result == {'orderId': 12345}

def test_place_oco(trade_executor):
    with patch.object(trade_executor.cli, 'futures_place_batch_orders') as mock_oco:
        trade_executor.place_oco('BTCUSDT', 'SELL', 0.1, 50000, 55000)
        mock_oco.assert_called_once_with(
            batchOrders=[
                {
                    'symbol': 'BTCUSDT',
                    'side': 'SELL',
                    'type': 'LIMIT',
                    'timeInForce': 'GTC',
                    'quantity': 0.1,
                    'price': 55000
                },
                {
                    'symbol': 'BTCUSDT',
                    'side': 'SELL',
                    'type': 'STOP_MARKET',
                    'timeInForce': 'GTC',
                    'quantity': 0.1,
                    'stopPrice': 50000
                }
            ]
        )

def test_place_oco_error_handling(trade_executor):
    with patch.object(trade_executor.cli, 'futures_place_batch_orders') as mock_oco:
        mock_oco.side_effect = Exception("API Error")
        with pytest.raises(Exception) as exc_info:
            trade_executor.place_oco('BTCUSDT', 'SELL', 0.1, 50000, 55000)
        assert str(exc_info.value) == "API Error" 