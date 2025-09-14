#!/usr/bin/env python3
"""
Trading Bot Main Module
Automated cryptocurrency trading bot with technical analysis
"""

import asyncio
import logging
import signal
import sys
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import threading
import os

# Import bot modules
from trading_bot.config import Config
from trading_bot.modules.signal_generator import SignalGenerator, SignalType, SignalStrength
from trading_bot.modules.telegram_notifier import TelegramNotifier
from trading_bot.modules.telegram_commands import TelegramCommandHandler
from trading_bot.modules.data_manager import DataManager

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading_bot.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

class TradingBot:
    """Main trading bot class"""
    
    def __init__(self):
        self.config = Config()
        self.running = False
        self.signal_generator = SignalGenerator()
        self.data_manager = DataManager()
        
        # Initialize telegram components
        self.telegram_notifier = None
        self.command_handler = None
        
        # Bot state
        self.signal_pool = []
        self.trade_history = []
        self.bot_start_time = datetime.now()
        self.last_scan_time = None
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
    def initialize(self) -> bool:
        """Initialize bot components"""
        try:
            logger.info("Initializing Trading Bot...")
            
            # Initialize Telegram notifier
            telegram_token = self.config.TELEGRAM_BOT_TOKEN
            telegram_chat_id = self.config.TELEGRAM_CHAT_ID
            
            if telegram_token and telegram_chat_id:
                self.telegram_notifier = TelegramNotifier(telegram_token, telegram_chat_id)
                
                # Test Telegram connection
                if self.telegram_notifier.test_connection():
                    logger.info("✅ Telegram connection successful")
                    
                    # Initialize command handler
                    self.command_handler = TelegramCommandHandler(
                        telegram_token, telegram_chat_id, self
                    )
                    self.command_handler.start_command_listener()
                    logger.info("✅ Telegram command handler started")
                else:
                    logger.warning("⚠️ Telegram connection failed, continuing without notifications")
            else:
                logger.warning("⚠️ Telegram credentials not configured")
            
            # Send startup notification
            if self.telegram_notifier:
                startup_message = """
🚀 *Trading Bot Started*

*Status:* Initializing
*Pairs:* 20 symbols
*Timeframe:* 15m
*Start Time:* {}

Bot is scanning markets for trading opportunities...
                """.format(datetime.now().strftime('%H:%M:%S')).strip()
                
                self.telegram_notifier.send_message(startup_message)
            
            logger.info("✅ Trading Bot initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Trading Bot: {str(e)}")
            return False
    
    def start(self):
        """Start the trading bot"""
        if not self.initialize():
            logger.error("Failed to initialize bot, exiting...")
            return
        
        logger.info("🤖 Starting Trading Bot main loop...")
        self.running = True
        
        try:
            while self.running:
                self._main_loop_iteration()
                time.sleep(self.config.SIGNAL_COOLDOWN)  # Wait before next scan
                
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt, shutting down...")
        except Exception as e:
            logger.error(f"Error in main loop: {str(e)}")
        finally:
            self.shutdown()
    
    def _main_loop_iteration(self):
        """Execute one iteration of the main loop"""
        try:
            logger.info("🔄 Starting market scan cycle...")
            
            # Scan markets for signals
            new_signals = self._scan_markets()
            
            # Update signal pool
            self._update_signal_pool(new_signals)
            
            # Process signals and execute trades
            self._process_signals()
            
            # Update scan time
            self.last_scan_time = datetime.now()
            
            # Send status update every 10 cycles
            cycle_count = len(self.trade_history) + len(self.signal_pool)
            if cycle_count % 10 == 0 and self.telegram_notifier:
                self._send_status_update()
            
            logger.info(f"✅ Scan cycle completed. Next scan in {self.config.SIGNAL_COOLDOWN} seconds")
            
        except Exception as e:
            logger.error(f"Error in main loop iteration: {str(e)}")
            if self.telegram_notifier:
                self.telegram_notifier.send_error_notification(f"Main loop error: {str(e)}")
    
    def _scan_markets(self) -> List[Dict[str, Any]]:
        """Scan markets for trading signals"""
        signals = []
        
        try:
            logger.info(f"📊 Scanning {len(self.config.TRADING_PAIRS)} trading pairs...")
            
            for symbol in self.config.TRADING_PAIRS:
                try:
                    # Get market data
                    df = self.data_manager.get_market_data(symbol, self.config.TIMEFRAME)
                    
                    if df is not None and len(df) > 0:
                        # Generate signal
                        signal = self.signal_generator.analyze_market_data(df, symbol)
                        
                        # Only add significant signals
                        if signal['signal'] != 'NEUTRAL' and signal['confidence'] > 50:
                            signals.append(signal)
                            logger.info(f"📈 Signal: {symbol} - {signal['signal']} ({signal['confidence']:.1f}%)")
                    
                except Exception as e:
                    logger.warning(f"Error scanning {symbol}: {str(e)}")
                    continue
            
            logger.info(f"🎯 Found {len(signals)} valid signals")
            
            # Send signal notifications
            for signal in signals:
                if self.telegram_notifier:
                    self.telegram_notifier.send_signal_notification(signal)
            
            return signals
            
        except Exception as e:
            logger.error(f"Error scanning markets: {str(e)}")
            return []
    
    def _update_signal_pool(self, new_signals: List[Dict[str, Any]]):
        """Update the signal pool with new signals"""
        try:
            # Add new signals to pool
            for signal in new_signals:
                signal['added_time'] = datetime.now()
                self.signal_pool.append(signal)
            
            # Remove old signals (older than 1 hour)
            current_time = datetime.now()
            self.signal_pool = [
                signal for signal in self.signal_pool
                if current_time - signal['added_time'] < timedelta(hours=1)
            ]
            
            logger.info(f"📊 Signal pool updated: {len(self.signal_pool)} active signals")
            
        except Exception as e:
            logger.error(f"Error updating signal pool: {str(e)}")
    
    def _process_signals(self):
        """Process signals and simulate trades"""
        try:
            if not self.signal_pool:
                logger.debug("No signals to process")
                return
            
            # For demo purposes, simulate trade execution
            for signal in self.signal_pool[:3]:  # Process up to 3 signals
                trade_result = self._simulate_trade(signal)
                if trade_result:
                    self.trade_history.append(trade_result)
                    
                    # Send trade notification
                    if self.telegram_notifier:
                        self.telegram_notifier.send_trade_update(trade_result)
            
            # Clear processed signals
            self.signal_pool = self.signal_pool[3:]
            
        except Exception as e:
            logger.error(f"Error processing signals: {str(e)}")
    
    def _simulate_trade(self, signal: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Simulate trade execution"""
        try:
            import random
            
            # Simulate trade outcome based on signal confidence
            confidence = signal['confidence']
            success_probability = confidence / 100.0
            
            # Random outcome based on confidence
            is_successful = random.random() < success_probability
            
            # Simulate P&L
            if is_successful:
                pnl = random.uniform(0.5, 3.0)  # Profit between 0.5% and 3%
                status = 'TAKE_PROFIT'
            else:
                pnl = -random.uniform(0.5, 2.0)  # Loss between 0.5% and 2%
                status = 'STOP_LOSS'
            
            trade_result = {
                'symbol': signal['symbol'],
                'signal_type': signal['signal'],
                'entry_price': 100.0,  # Simulated price
                'exit_price': 100.0 * (1 + pnl/100),
                'pnl': pnl,
                'status': status,
                'timestamp': datetime.now().isoformat(),
                'confidence': confidence
            }
            
            logger.info(f"💰 Trade executed: {signal['symbol']} - {status} ({pnl:+.2f}%)")
            return trade_result
            
        except Exception as e:
            logger.error(f"Error simulating trade: {str(e)}")
            return None
    
    def _send_status_update(self):
        """Send bot status update"""
        try:
            # Calculate statistics
            total_trades = len(self.trade_history)
            successful_trades = sum(1 for trade in self.trade_history if trade['pnl'] > 0)
            success_rate = (successful_trades / total_trades * 100) if total_trades > 0 else 0
            
            uptime = datetime.now() - self.bot_start_time
            uptime_str = str(uptime).split('.')[0]  # Remove microseconds
            
            status_data = {
                'active_signals': len(self.signal_pool),
                'total_trades': total_trades,
                'success_rate': success_rate,
                'uptime': uptime_str
            }
            
            self.telegram_notifier.send_bot_status(status_data)
            
        except Exception as e:
            logger.error(f"Error sending status update: {str(e)}")
    
    def _signal_handler(self, signum, frame):
        """Handle system signals"""
        logger.info(f"Received signal {signum}, shutting down...")
        self.shutdown()
    
    def shutdown(self):
        """Shutdown the trading bot"""
        logger.info("🛑 Shutting down Trading Bot...")
        self.running = False
        
        # Stop command handler
        if self.command_handler:
            self.command_handler.stop_command_listener()
        
        # Send shutdown notification
        if self.telegram_notifier:
            shutdown_message = """
🛑 *Trading Bot Stopped*

*Status:* Shutdown
*Total Trades:* {}
*Uptime:* {}

Bot has been safely stopped.
            """.format(
                len(self.trade_history),
                str(datetime.now() - self.bot_start_time).split('.')[0]
            ).strip()
            
            self.telegram_notifier.send_message(shutdown_message)
        
        logger.info("✅ Trading Bot shutdown complete")

def main():
    """Main entry point"""
    logger.info("🚀 Starting Trading Bot Application...")
    
    # Create and start bot
    bot = TradingBot()
    bot.start()

if __name__ == "__main__":
    main()