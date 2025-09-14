import asyncio
import logging
from typing import Optional, Dict, Any
import requests
from datetime import datetime

logger = logging.getLogger(__name__)

class TelegramNotifier:
    """Handle Telegram notifications for trading bot"""
    
    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
        self.session = requests.Session()
        
    def send_message(self, message: str, parse_mode: str = "Markdown") -> bool:
        """Send a message to Telegram"""
        try:
            url = f"{self.base_url}/sendMessage"
            payload = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': parse_mode
            }
            
            response = self.session.post(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                logger.debug("Telegram message sent successfully")
                return True
            else:
                logger.error(f"Failed to send Telegram message: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending Telegram message: {str(e)}")
            return False
    
    def send_signal_notification(self, signal_data: Dict[str, Any]) -> bool:
        """Send signal notification to Telegram"""
        try:
            symbol = signal_data.get('symbol', 'UNKNOWN')
            signal_type = signal_data.get('signal', 'NEUTRAL')
            strength = signal_data.get('strength', 'WEAK')
            confidence = signal_data.get('confidence', 0.0)
            
            # Create signal emoji
            signal_emoji = "🟢" if signal_type == "LONG" else "🔴" if signal_type == "SHORT" else "⚪"
            strength_emoji = "🔥" if strength == "STRONG" else "⚡" if strength == "MODERATE" else "💫"
            
            message = f"""
{signal_emoji} *SIGNAL DETECTED* {strength_emoji}

*Symbol:* `{symbol}`
*Direction:* {signal_type}
*Strength:* {strength}
*Confidence:* {confidence}%

*Time:* {datetime.now().strftime('%H:%M:%S')}
            """.strip()
            
            return self.send_message(message)
            
        except Exception as e:
            logger.error(f"Error sending signal notification: {str(e)}")
            return False
    
    def send_trade_update(self, trade_data: Dict[str, Any]) -> bool:
        """Send trade update notification"""
        try:
            symbol = trade_data.get('symbol', 'UNKNOWN')
            status = trade_data.get('status', 'UNKNOWN')
            pnl = trade_data.get('pnl', 0.0)
            entry_price = trade_data.get('entry_price', 0.0)
            exit_price = trade_data.get('exit_price', 0.0)
            
            # Create status emoji
            if status == 'PROFIT':
                status_emoji = "✅"
            elif status == 'LOSS':
                status_emoji = "❌"
            elif status == 'STOP_LOSS':
                status_emoji = "🛑"
            elif status == 'TAKE_PROFIT':
                status_emoji = "🎯"
            else:
                status_emoji = "ℹ️"
            
            pnl_emoji = "💚" if pnl > 0 else "❤️" if pnl < 0 else "💛"
            
            message = f"""
{status_emoji} *TRADE CLOSED* {pnl_emoji}

*Symbol:* `{symbol}`
*Status:* {status}
*Entry:* {entry_price}
*Exit:* {exit_price}
*PnL:* {pnl:.2f}%

*Time:* {datetime.now().strftime('%H:%M:%S')}
            """.strip()
            
            return self.send_message(message)
            
        except Exception as e:
            logger.error(f"Error sending trade update: {str(e)}")
            return False
    
    def send_bot_status(self, status_data: Dict[str, Any]) -> bool:
        """Send bot status notification"""
        try:
            active_signals = status_data.get('active_signals', 0)
            total_trades = status_data.get('total_trades', 0)
            success_rate = status_data.get('success_rate', 0.0)
            uptime = status_data.get('uptime', 'Unknown')
            
            message = f"""
🤖 *BOT STATUS*

*Active Signals:* {active_signals}
*Total Trades:* {total_trades}
*Success Rate:* {success_rate:.1f}%
*Uptime:* {uptime}

*Time:* {datetime.now().strftime('%H:%M:%S')}
            """.strip()
            
            return self.send_message(message)
            
        except Exception as e:
            logger.error(f"Error sending bot status: {str(e)}")
            return False
    
    def send_error_notification(self, error_message: str) -> bool:
        """Send error notification"""
        try:
            message = f"""
⚠️ *ERROR ALERT*

{error_message}

*Time:* {datetime.now().strftime('%H:%M:%S')}
            """.strip()
            
            return self.send_message(message)
            
        except Exception as e:
            logger.error(f"Error sending error notification: {str(e)}")
            return False
    
    def test_connection(self) -> bool:
        """Test Telegram bot connection"""
        try:
            url = f"{self.base_url}/getMe"
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 200:
                bot_info = response.json()
                if bot_info.get('ok'):
                    logger.info(f"Telegram bot connected: {bot_info['result']['username']}")
                    return True
            
            logger.error(f"Telegram connection failed: {response.text}")
            return False
            
        except Exception as e:
            logger.error(f"Error testing Telegram connection: {str(e)}")
            return False