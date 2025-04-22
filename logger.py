import csv
import os
from datetime import datetime
from notifier import notify_slack

def ensure_log_file():
    """trade_log.csv 파일이 존재하는지 확인하고 없으면 생성"""
    if not os.path.exists('trade_log.csv'):
        try:
            with open('trade_log.csv', 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['timestamp', 'symbol', 'side', 'entry', 'exit', 'pnl'])
            notify_slack("📝 Created new trade_log.csv file")
        except Exception as e:
            notify_slack(f"❌ Failed to create trade_log.csv: {str(e)}")
            raise

def log_trade(trade):
    """거래 기록을 CSV 파일에 저장"""
    try:
        ensure_log_file()
        
        with open('trade_log.csv', 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                trade['symbol'],
                trade['side'],
                trade['entry'],
                trade['exit'],
                trade['pnl']
            ])
    except Exception as e:
        notify_slack(f"❌ Failed to log trade: {str(e)}")

def daily_report():
    """일일 거래 보고서 생성"""
    try:
        ensure_log_file()
        
        today = datetime.now().strftime('%Y-%m-%d')
        trades = []
        total_pnl = 0
        
        with open('trade_log.csv', 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['timestamp'].startswith(today):
                    trades.append(row)
                    total_pnl += float(row['pnl'])
        
        if trades:
            report = f"📊 *Daily Trading Report ({today})*\n"
            report += f"• Total Trades: {len(trades)}\n"
            report += f"• Total PnL: {total_pnl:.2f} USDT\n"
            report += "\nRecent Trades:\n"
            
            for trade in trades[-5:]:  # 최근 5개 거래만 표시
                report += f"• {trade['symbol']} {trade['side']} @{trade['entry']} -> {trade['exit']} ({trade['pnl']} USDT)\n"
            
            notify_slack(report)
        else:
            notify_slack(f"📊 *Daily Trading Report ({today})*\n• No trades today")
    except Exception as e:
        notify_slack(f"❌ Failed to generate daily report: {str(e)}")
