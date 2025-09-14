import asyncio
import logging
import signal
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any

# Import modules - with proper error handling for missing modules
try:
    import config
except ImportError:
    # Create a basic config if missing
    class Config:
        TRADING_PAIRS = ["BTC/USDT", "ETH/USDT"]
        CHECK_INTERVAL = 300
        TIMEFRAME = "15m"
        TELEGRAM_BOT_TOKEN = ""
        TELEGRAM_CHAT_ID = ""
    config = Config()

try:
    from modules.signal_generator import SignalGenerator, SignalType
    from modules.telegram_notifier import NotificationManager
    from modules.telegram_commands import TelegramCommandHandler
except ImportError as e:
    logging.error(f"Module import error: {e}")

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading_bot.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

class MarketDataProvider:
    """Basic market data provider interface"""
    
    def __init__(self):
        self.cache = {}
    
    async def get_data(self, pair: str, timeframe: str, limit: int = 100) -> Optional[Any]:
        """Get market data"""
        # Placeholder implementation
        return None
    
    def clear_cache(self):
        """Clear data cache"""
        self.cache.clear()

class DataManager:
    """Data manager wrapper"""
    
    def __init__(self):
        self.provider = MarketDataProvider()
    
    async def get_data(self, pair: str, timeframe: str, limit: int = 100) -> Optional[Any]:
        """Get market data through provider"""
        return await self.provider.get_data(pair, timeframe, limit)
    
    def clear_cache(self):
        """Clear cache"""
        self.provider.clear_cache()

class TradingBot:
    """Main trading bot class"""
    
    def __init__(self):
        self.data_manager = DataManager()
        self.signal_generator = SignalGenerator()
        
        # Fix type issues by ensuring proper string types for Telegram
        bot_token = getattr(config, 'TELEGRAM_BOT_TOKEN', '') or ''
        chat_id = getattr(config, 'TELEGRAM_CHAT_ID', '') or ''
        
        self.notification_manager = NotificationManager(
            bot_token=bot_token,
            chat_id=chat_id
        )
        
        # Fix type mismatch by using DataManager instead of MarketDataProvider
        self.command_handler: Optional[TelegramCommandHandler] = None
        if bot_token:
            self.command_handler = TelegramCommandHandler(
                bot_token=bot_token,
                data_provider=self.data_manager,  # Use DataManager instead of MarketDataProvider
                notification_manager=self.notification_manager
            )
        
        self.is_running = False
        self.trading_pairs = getattr(config, 'TRADING_PAIRS', ["BTC/USDT", "ETH/USDT"])
        self.check_interval = getattr(config, 'CHECK_INTERVAL', 300)
        self.last_signals = {}
        
        # Graceful shutdown signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info("Shutdown signal received, stopping bot...")
        self.is_running = False
    
    async def initialize(self) -> bool:
        """Initialize bot components"""
        logger.info("Trading Bot initializing...")
        
        # Test Telegram connection
        if not self.notification_manager.initialize_telegram():
            logger.error("Telegram connection failed!")
            return False
        
        if not await self.notification_manager.test_notifications():
            logger.error("Telegram test message failed!")
            return False
        
        # Start command handler if available
        if self.command_handler:
            try:
                await self.command_handler.start_bot()
                logger.info("Telegram command handler started")
            except Exception as e:
                logger.error(f"Failed to start command handler: {e}")
        
        logger.info("Bot successfully initialized!")
        await self.notification_manager.notify_status("🚀 Trading Bot is now active!")
        
        return True
    
    async def analyze_pair(self, pair: str) -> Optional[Any]:
        """Analyze a trading pair"""
        try:
            # Get market data
            df = await self.data_manager.get_data(pair, getattr(config, 'TIMEFRAME', '15m'), 100)
            if df is None:
                logger.warning(f"No data for {pair}")
                return None
            
            # Generate signal
            signal = self.signal_generator.generate_signal(pair, df)
            
            if signal and signal.signal_type != SignalType.NEUTRAL:
                logger.info(f"Signal generated: {pair} - {signal.signal_type.value} - {signal.strength.value}")
                return signal
            
            return None
            
        except Exception as e:
            logger.error(f"Analysis error for {pair}: {e}")
            return None
    
    async def process_signals(self) -> List[Any]:
        """Process signals for all trading pairs"""
        signals = []
        
        logger.info(f"Processing {len(self.trading_pairs)} trading pairs...")
        
        # Analyze each pair
        for pair in self.trading_pairs:
            try:
                signal = await self.analyze_pair(pair)
                if signal:
                    signals.append(signal)
            except Exception as e:
                logger.error(f"Processing error for {pair}: {e}")
        
        logger.info(f"Generated {len(signals)} signals")
        return signals
    
    async def send_signals(self, signals: List[Any]) -> int:
        """Send trading signals"""
        sent_count = 0
        
        for signal in signals:
            try:
                # Check if we should send this signal (spam protection)
                if self.should_send_signal(signal):
                    success = await self.notification_manager.notify_signal(signal)
                    if success:
                        sent_count += 1
                        self.last_signals[signal.pair] = signal.timestamp
                        logger.info(f"Signal sent: {signal.pair}")
                    else:
                        logger.error(f"Failed to send signal: {signal.pair}")
                
            except Exception as e:
                logger.error(f"Signal sending error: {e}")
        
        return sent_count
    
    def should_send_signal(self, signal) -> bool:
        """Check if signal should be sent (spam protection)"""
        if signal.pair not in self.last_signals:
            return True
        
        # Check time difference since last signal
        time_diff = signal.timestamp - self.last_signals[signal.pair]
        
        # Send signal if enough time has passed (15 minutes)
        return time_diff > timedelta(minutes=15)
    
    async def run_cycle(self):
        """Run one bot cycle"""
        try:
            cycle_start = datetime.now()
            logger.info("Starting new cycle...")
            
            # Process signals
            signals = await self.process_signals()
            
            # Send signals
            sent_count = 0
            if signals:
                sent_count = await self.send_signals(signals)
            
            # Log cycle summary
            cycle_duration = datetime.now() - cycle_start
            logger.info(f"Cycle completed: {len(signals)} signals, {sent_count} sent, duration: {cycle_duration.total_seconds():.2f}s")
            
        except Exception as e:
            logger.error(f"Cycle error: {e}")
            await self.notification_manager.notify_error(f"Cycle error: {str(e)}")
    
    async def run(self):
        """Main bot loop"""
        if not await self.initialize():
            logger.error("Bot initialization failed!")
            return
        
        self.is_running = True
        error_count = 0
        max_errors = 5
        
        while self.is_running:
            try:
                await self.run_cycle()
                error_count = 0  # Reset error count on successful cycle
                
                # Wait for next cycle
                logger.info(f"Next cycle in {self.check_interval} seconds...")
                await asyncio.sleep(self.check_interval)
                
            except Exception as e:
                error_count += 1
                logger.error(f"Unexpected error (#{error_count}): {e}")
                
                await self.notification_manager.notify_error(
                    f"Bot error #{error_count}: {str(e)}"
                )
                
                if error_count >= max_errors:
                    logger.error(f"Too many errors ({max_errors}), stopping bot!")
                    await self.notification_manager.notify_error(
                        f"Bot stopped due to too many errors! ({max_errors} errors)"
                    )
                    break
                
                # Wait longer after error
                await asyncio.sleep(60)
        
        await self.cleanup()
    
    async def cleanup(self):
        """Cleanup resources"""
        logger.info("Bot shutting down...")
        
        # Stop command handler
        if self.command_handler:
            try:
                await self.command_handler.stop_bot()
            except Exception as e:
                logger.error(f"Error stopping command handler: {e}")
        
        await self.notification_manager.notify_status("Bot stopped 🛑")
        self.data_manager.clear_cache()
        logger.info("Bot successfully shut down")

async def main():
    """Main function"""
    bot = TradingBot()
    await bot.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot startup error: {e}")