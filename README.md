# Trading Bot

Automated cryptocurrency trading bot with technical analysis and Telegram integration.

## Features

- 📊 Technical analysis with multiple indicators (RSI, EMA, MACD, Stochastic)
- 🤖 Automated signal generation and trading
- 📱 Telegram notifications and command interface
- 🛡️ Risk management with stop loss and take profit
- 📈 Real-time market scanning
- 🔄 Signal pool management
- 📋 Trading statistics and performance tracking

## Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd yeni
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and settings
   ```

4. **Run the bot**
   ```bash
   python trading_bot/main.py
   ```

## Configuration

Edit the `.env` file with your settings:

- **KuCoin API**: Get your API credentials from KuCoin
- **Telegram Bot**: Create a bot with @BotFather and get chat ID
- **Trading Settings**: Adjust risk parameters as needed

## Telegram Commands

- `/start` - Start the bot and show welcome message
- `/status` - Show current bot status
- `/signals` - Display active trading signals
- `/tp` - Take profit information
- `/sl` - Stop loss information  
- `/stats` - Trading statistics
- `/help` - Show available commands

## Trading Pairs

The bot monitors 20 major cryptocurrency pairs:
- BTC/USDT, ETH/USDT, LTC/USDT, XRP/USDT, ADA/USDT
- DOT/USDT, LINK/USDT, AVAX/USDT, UNI/USDT, SHIB/USDT
- BCH/USDT, PEPE/USDT, DOGE/USDT, HYPE/USDT, MATIC/USDT
- SOL/USDT, BNB/USDT, TRX/USDT, ATOM/USDT, FTM/USDT

## Risk Management

- **Stop Loss**: 1.0% (configurable)
- **Take Profit**: 2.0% (configurable)
- **Position Size**: 100 USDT max (configurable)
- **Signal Cooldown**: 5 minutes between scans

## Technical Indicators

- **RSI**: Relative Strength Index for momentum
- **EMA**: Exponential Moving Averages for trend
- **MACD**: Moving Average Convergence Divergence
- **Stochastic**: Oscillator for overbought/oversold conditions
- **Volume**: Volume analysis for confirmation

## Logging

All trading activity is logged to `trading_bot.log` with timestamps and detailed information.

## Support

For issues or questions, please check the logs and ensure your API credentials are correctly configured.