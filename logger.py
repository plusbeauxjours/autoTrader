import csv, os
from datetime import datetime
import pandas as pd

def log_trade(r):
    fn='trade_log.csv'
    new=not os.path.exists(fn)
    with open(fn,'a',newline='') as f:
        writer=csv.writer(f)
        if new: writer.writerow(['time','symbol','side','entry','exit','pnl'])
        writer.writerow([datetime.now(),r['symbol'],r['side'],r['entry'],r['exit'],r['pnl']])

def daily_report():
    df=pd.read_csv('trade_log.csv', parse_dates=['time'])
    today=df[df.time.dt.date==pd.Timestamp.now().date()]
    wins=len(today[today.pnl>0]); losses=len(today[today.pnl<=0])
    profit=today.pnl.sum(); total=len(today)
    return f"Trades:{total}, Wins:{wins}, Losses:{losses}, PNL:{profit:.2f}"
