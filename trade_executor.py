import os
from binance.client import Client
from dotenv import load_dotenv

load_dotenv()
cli = Client(os.getenv('BINANCE_API_KEY'), os.getenv('BINANCE_API_SECRET'))

class TradeExecutor:
    def __init__(self): self.cli=cli

    def set_leverage(self, sym, lev):
        self.cli.futures_change_margin_type(symbol=sym, marginType='ISOLATED')
        self.cli.futures_change_leverage(symbol=sym, leverage=lev)

    def enter_limit(self, sym, side, qty, price):
        return self.cli.futures_create_order(
            symbol=sym, side=side.upper(), type='LIMIT', timeInForce='GTC',
            quantity=qty, price=price
        )

    def place_oco(self, sym, side, qty, stop, tp):
        return self.cli.futures_create_oco_order(
            symbol=sym, side=side.upper(), quantity=qty,
            stopPrice=stop, stopLimitPrice=round(stop*0.995,2),
            stopLimitTimeInForce='GTC', price=tp
        )
