# Trading Bot Configuration

# Trading pairs to monitor
TRADING_PAIRS = [
    "BTC/USDT",
    "ETH/USDT", 
    "BNB/USDT",
    "ADA/USDT",
    "XRP/USDT",
    "SOL/USDT",
    "DOGE/USDT",
    "DOT/USDT",
    "AVAX/USDT",
    "MATIC/USDT"
]

# Time frame for analysis
TIMEFRAME = "15m"

# Check interval in seconds (5 minutes)
CHECK_INTERVAL = 300

# Telegram configuration
TELEGRAM_BOT_TOKEN = ""
TELEGRAM_CHAT_ID = ""

# Risk management
RISK_PER_TRADE = 0.02  # 2% risk per trade
MAX_DAILY_TRADES = 10
STOP_LOSS_PERCENTAGE = 0.03  # 3% stop loss

# Technical analysis parameters
RSI_PERIOD = 14
RSI_OVERSOLD = 30
RSI_OVERBOUGHT = 70

EMA_FAST = 12
EMA_SLOW = 26

MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9