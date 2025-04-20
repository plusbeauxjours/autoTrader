# AutoBot - Automated Cryptocurrency Trading Bot

An automated trading bot that combines technical analysis and sentiment analysis to identify and execute trading opportunities in cryptocurrency futures markets.

## Features

- **Real-time Market Monitoring**: Continuously monitors price movements and volume spikes
- **Technical Analysis**: Uses RSI, Bollinger Bands, and MACD indicators
- **Sentiment Analysis**: Analyzes Twitter sentiment for additional trading signals
- **Risk Management**: Implements position sizing and leverage management
- **Automated Trading**: Executes trades with take-profit and stop-loss orders
- **Notifications**: Sends alerts via Slack for trades and anomalies

## Components

### Data Fetcher (`data_fetcher.py`)

- Fetches historical price data from Binance
- Retrieves recent tweets for sentiment analysis
- Handles API rate limiting and error handling

### Signal Generator (`signal_generator.py`)

- Combines technical and sentiment analysis
- Detects volume spikes
- Generates trading signals based on multiple indicators

### Risk Manager (`risk_manager.py`)

- Manages position sizing based on account balance
- Adjusts leverage based on volatility
- Tracks trade history and performance

### Trade Executor (`trade_executor.py`)

- Executes trades on Binance Futures
- Places OCO (One-Cancels-Other) orders for take-profit and stop-loss
- Manages leverage settings

### Logger (`logger.py`)

- Logs trade entries and exits
- Generates daily performance reports
- Tracks trading metrics

### Notifier (`notifier.py`)

- Sends notifications via Slack
- Alerts on trades and anomalies
- Provides real-time updates

## Setup

1. Clone the repository:

```bash
git clone https://github.com/plusbeauxjours/autoTrader.git
cd autobot
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Set up environment variables:

Edit `.env` with your credentials:

```
BINANCE_API_KEY=
BINANCE_API_SECRET=
TWITTER_BEARER_TOKEN
SLACK_WEBHOOK_URL=
```

4. Run the bot:

```bash
python main.py
```

## Trading Strategy

The bot uses a combination of technical and sentiment analysis to identify trading opportunities:

1. **Volume Spike Detection**: Identifies unusual trading activity
2. **Technical Indicators**:
   - RSI (Relative Strength Index)
   - Bollinger Bands
   - MACD (Moving Average Convergence Divergence)
3. **Sentiment Analysis**: Analyzes Twitter sentiment for additional confirmation
4. **Signal Generation**: Combines indicators into a single score
5. **Trade Execution**: Enters positions with OCO orders for risk management

## Risk Management

- Position sizing based on account balance
- Dynamic leverage adjustment
- Stop-loss and take-profit orders
- Trade history tracking
- Daily performance monitoring

## Requirements

- Python 3.8+
- Binance API credentials
- Slack webhook URL (optional)
- Twitter API credentials (optional)

## Dependencies

- python-binance
- pandas
- numpy
- scikit-learn
- requests
- python-dotenv

## License

MIT License

## Disclaimer

This bot is for educational purposes only. Use at your own risk. Cryptocurrency trading involves significant risk of loss.
