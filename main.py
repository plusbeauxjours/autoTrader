import time
from data_fetcher import get_symbols, get_klines
from signal_generator import get_signal
from risk_manager import RiskManager
from trade_executor import TradeExecutor
from logger import log_trade, daily_report
from notifier import notify

def main():
    syms=get_symbols(); risk=RiskManager(); exec=TradeExecutor()
    balance=float(exec.cli.futures_account_balance()[6]['balance'])
    while True:
        for sym in syms:
            if not risk.can_trade(sym): continue
            sig=get_signal(sym)
            if sig in ('buy','sell'):
                df=get_klines(sym)
                entry=df['close'].iloc[-1]
                stop= df['close'][:-1].min() if sig=='buy' else df['close'][:-1].max()
                qty,lev=risk.size_leverage(balance,entry,stop)
                exec.set_leverage(sym,lev)
                exec.enter_limit(sym, 'BUY' if sig=='buy' else 'SELL', qty, entry)
                tp=entry*1.10 if sig=='buy' else entry*0.90
                exec.place_oco(sym, 'SELL' if sig=='buy' else 'BUY', qty, stop, tp)
                pnl= (tp-entry)/entry*qty # rough
                risk.register(pnl,sym)
                log_trade({'symbol':sym,'side':sig,'entry':entry,'exit':tp,'pnl':pnl})
                notify(f"{sym} {sig}@{entry:.2f}, qty={qty:.3f}, lev={lev}x")
                time.sleep(1)
        report=daily_report(); notify("Daily report: "+report)
        time.sleep(3600)

if __name__=='__main__':
    main()
