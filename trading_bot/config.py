import os
from typing import Dict, Any

class Config:
    """Trading bot configuration"""
    
    # API Configuration
    KUCOIN_API_KEY = os.getenv('KUCOIN_API_KEY', '')
    KUCOIN_API_SECRET = os.getenv('KUCOIN_API_SECRET', '')
    KUCOIN_API_PASSPHRASE = os.getenv('KUCOIN_API_PASSPHRASE', '')
    KUCOIN_SANDBOX = os.getenv('KUCOIN_SANDBOX', 'True').lower() == 'true'
    
    # Telegram Configuration
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
    TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '')
    
    # Trading Configuration
    TRADING_PAIRS = [
        'BTC/USDT', 'ETH/USDT', 'LTC/USDT', 'XRP/USDT', 'ADA/USDT',
        'DOT/USDT', 'LINK/USDT', 'AVAX/USDT', 'UNI/USDT', 'SHIB/USDT',
        'BCH/USDT', 'PEPE/USDT', 'DOGE/USDT', 'HYPE/USDT', 'MATIC/USDT',
        'SOL/USDT', 'BNB/USDT', 'TRX/USDT', 'ATOM/USDT', 'FTM/USDT'
    ]
    
    # Signal Configuration
    TIMEFRAME = '15m'
    SIGNAL_COOLDOWN = 300  # 5 minutes
    SIGNAL_POOL_SIZE = 3
    
    # Risk Management
    STOP_LOSS_PERCENT = 1.0
    TAKE_PROFIT_PERCENT = 2.0
    MAX_POSITION_SIZE = 100.0  # USDT
    
    # Technical Analysis
    RSI_PERIOD = 14
    RSI_OVERBOUGHT = 70
    RSI_OVERSOLD = 30
    
    EMA_FAST = 12
    EMA_SLOW = 26
    
    MACD_FAST = 12
    MACD_SLOW = 26
    MACD_SIGNAL = 9
    
    # Logging
    LOG_LEVEL = 'INFO'
    LOG_FILE = 'trading_bot.log'
    
    @classmethod
    def get_config(cls) -> Dict[str, Any]:
        """Get all configuration as dictionary"""
        return {
            'api': {
                'kucoin_key': cls.KUCOIN_API_KEY,
                'kucoin_secret': cls.KUCOIN_API_SECRET,
                'kucoin_passphrase': cls.KUCOIN_API_PASSPHRASE,
                'kucoin_sandbox': cls.KUCOIN_SANDBOX,
            },
            'telegram': {
                'bot_token': cls.TELEGRAM_BOT_TOKEN,
                'chat_id': cls.TELEGRAM_CHAT_ID,
            },
            'trading': {
                'pairs': cls.TRADING_PAIRS,
                'timeframe': cls.TIMEFRAME,
                'signal_cooldown': cls.SIGNAL_COOLDOWN,
                'stop_loss': cls.STOP_LOSS_PERCENT,
                'take_profit': cls.TAKE_PROFIT_PERCENT,
                'max_position': cls.MAX_POSITION_SIZE,
            }
        }