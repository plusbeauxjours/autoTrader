# Binance Futures Auto-Trading Bot

📈 A fully automated Binance Futures trading bot powered by:

- **Volume spike anomaly detection**
- **Technical indicators**: RSI, MACD, Bollinger Bands
- **Twitter sentiment analysis** using VADER
- **Dynamic risk management** with trailing stop, isolated margin & leverage control
- **Slack alerts** for real-time updates
- **Daily performance reports** (PnL, win rate, trade count)

---

## 🔧 Features

### 📊 Market Signal Detection

- Monitors USDT futures pairs for sudden volume increases (3× 5min avg)
- Calculates technical signals (RSI, MACD crossover, Bollinger Band touches)
- Pulls latest tweets related to the coin and analyzes sentiment
- Combines signals into a composite score:
  - `score >= 0.5` → Buy
  - `score <= -0.5` → Sell
  - Confirmed over 3 consecutive minutes before executing

### 🛡 Risk Management

- Trades only **max 5 per day**
- Stops if **3 consecutive losses**
- Applies **cooldown of 30 mins** per symbol after trade
- Max **2% of balance** risked per trade
- Leverage adjusts based on stop-loss distance:
  - ≤1% → 10×
  - ≤2% → 5×
  - > 2% → 2×

### 💰 Trade Execution

- Uses **isolated margin mode**
- Enters with **limit orders**; cancels if slippage >1%
- Automatically sets **stop-loss (5%)** and **take-profit (10%)**
- Implements **trailing stop logic** (follows 50% of gain)

### 📢 Notifications

- Sends trade entries, exits, and daily reports to **Slack**

### 📄 Reporting

- Logs all trades to `trade_log.csv`
- Generates a summary every day with:
  - Total PnL
  - Win/Loss count
  - Win rate
  - Average PnL

---

## 🚀 Getting Started

### 1. Clone & Install

```bash
git clone https://github.com/yourusername/auto-bot.git
cd auto-bot
pip install -r requirements.txt
```

### 2. Setup `.env`

Rename `.env.example` → `.env` and fill in:

```env
BINANCE_API_KEY=your_key
BINANCE_API_SECRET=your_secret
TWITTER_BEARER_TOKEN=your_token
SLACK_WEBHOOK_URL=https://hooks.slack.com/...
```

### 3. Run

```bash
python main.py
```

### 4. Testing

The project includes comprehensive unit tests for all major components. To run the tests:

```bash
pytest tests/
```

Test coverage includes:

- Data fetching and processing
- Signal generation and analysis
- Risk management
- Trade execution
- Main monitoring logic

Each test file (`test_*.py`) corresponds to a module in the project and includes:

- Unit tests for individual functions
- Mock implementations for external APIs
- Error handling scenarios
- Edge cases

---

## 🧠 Architecture

```
main.py
├── data_fetcher.py           # Binance + Twitter data
├── technical_analysis.py     # RSI, MACD, BBANDS
├── sentiment_analysis.py     # VADER sentiment scoring
├── signal_generator.py       # Strategy logic
├── risk_manager.py           # Position sizing, limits
├── trade_executor.py         # Binance order functions
├── logger.py                 # Trade logs & daily report
└── notifier.py               # Slack alerts
```

---

## ⚠️ Disclaimer

> This is a research/educational project. Use at your own risk. Trading futures involves significant financial risk and can lead to substantial losses. Be sure to test thoroughly before live deployment.

---

## 📬 Contributions

Feel free to open issues, suggest improvements, or fork for your own strategies!
