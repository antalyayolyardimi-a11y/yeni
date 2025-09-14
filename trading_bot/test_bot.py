#!/usr/bin/env python3
"""
Test script to demonstrate trading bot functionality
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modules.signal_generator import SignalGenerator  
from modules.data_manager import DataManager
from modules.telegram_notifier import TelegramNotifier
from config import Config

def test_signal_generation():
    """Test signal generation"""
    print("🔍 Testing Signal Generation...")
    
    sg = SignalGenerator()
    dm = DataManager()
    
    symbols = ['BTC/USDT', 'ETH/USDT', 'LTC/USDT']
    
    for symbol in symbols:
        data = dm.get_market_data(symbol, '15m', 100)
        signal = sg.analyze_market_data(data, symbol)
        
        print(f"  {symbol}: {signal['signal']} ({signal['strength']}) - {signal['confidence']:.1f}%")
    
    print("✅ Signal generation working\n")

def test_data_manager():
    """Test data manager"""
    print("📊 Testing Data Manager...")
    
    dm = DataManager()
    data = dm.get_market_data('BTC/USDT', '15m', 50)
    
    print(f"  Fetched {len(data)} candles for BTC/USDT")
    print(f"  Columns: {list(data.columns)}")
    print(f"  Price range: {data['close'].min():.2f} - {data['close'].max():.2f}")
    
    # Test cache
    cache_info = dm.get_cache_info()
    print(f"  Cache: {cache_info['valid_entries']} valid entries")
    
    print("✅ Data manager working\n")

def test_config():
    """Test configuration"""
    print("⚙️ Testing Configuration...")
    
    config = Config()
    print(f"  Trading pairs: {len(config.TRADING_PAIRS)}")
    print(f"  Timeframe: {config.TIMEFRAME}")
    print(f"  Signal cooldown: {config.SIGNAL_COOLDOWN}s")
    print(f"  Stop loss: {config.STOP_LOSS_PERCENT}%")
    print(f"  Take profit: {config.TAKE_PROFIT_PERCENT}%")
    
    print("✅ Configuration working\n")

def main():
    """Main test function"""
    print("🤖 Trading Bot Test Suite")
    print("=" * 40)
    
    test_config()
    test_data_manager()
    test_signal_generation()
    
    print("🎉 All tests completed successfully!")
    print("\nTo start the bot:")
    print("  python main.py")
    print("\nTo configure Telegram:")
    print("  1. Copy .env.example to .env")
    print("  2. Add your Telegram bot token and chat ID")
    print("  3. Add your KuCoin API credentials (optional for demo)")

if __name__ == "__main__":
    main()