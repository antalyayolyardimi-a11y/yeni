import asyncio
import logging
from telegram import Bot
from telegram.error import TelegramError
from typing import Optional

logger = logging.getLogger(__name__)

class NotificationManager:
    """Telegram notification manager"""
    
    def __init__(self, bot_token: Optional[str] = None, chat_id: Optional[str] = None):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.bot = None
        if bot_token:
            self.bot = Bot(token=bot_token)
    
    def initialize_telegram(self) -> bool:
        """Initialize Telegram bot"""
        if not self.bot_token or not self.chat_id:
            logger.error("Bot token or chat ID not provided")
            return False
        
        try:
            if not self.bot:
                self.bot = Bot(token=self.bot_token)
            return True
        except Exception as e:
            logger.error(f"Telegram initialization error: {e}")
            return False
    
    async def test_notifications(self) -> bool:
        """Test Telegram connection"""
        if not self.bot:
            return False
        
        try:
            bot_info = await self.bot.get_me()
            logger.info(f"Telegram bot connection successful: @{bot_info.username}")
            return True
        except Exception as e:
            logger.error(f"Telegram test error: {e}")
            return False
    
    async def send_message(self, message: str) -> bool:
        """Send message to Telegram"""
        if not self.bot or not self.chat_id:
            return False
        
        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode='Markdown'
            )
            return True
        except Exception as e:
            logger.error(f"Message send error: {e}")
            return False
    
    async def notify_signal(self, signal) -> bool:
        """Send trading signal notification"""
        if not signal:
            return False
        
        try:
            message = self._format_signal_message(signal)
            return await self.send_message(message)
        except Exception as e:
            logger.error(f"Signal notification error: {e}")
            return False
    
    async def notify_status(self, status: str) -> bool:
        """Send status notification"""
        try:
            message = f"🤖 **Bot Status**\n\n{status}"
            return await self.send_message(message)
        except Exception as e:
            logger.error(f"Status notification error: {e}")
            return False
    
    async def notify_error(self, error: str) -> bool:
        """Send error notification"""
        try:
            message = f"❌ **Error**\n\n{error}"
            return await self.send_message(message)
        except Exception as e:
            logger.error(f"Error notification error: {e}")
            return False
    
    def _format_signal_message(self, signal) -> str:
        """Format trading signal message"""
        try:
            direction_emoji = "🟢" if signal.signal_type.value == "LONG" else "🔴"
            strength_emoji = "🔥" if signal.strength.value == "GÜÇLÜ" else "⚡"
            
            message = f"""
{direction_emoji} **{signal.pair}** - {signal.signal_type.value}
{strength_emoji} Güç: {signal.strength.value}
💰 Fiyat: ${signal.price:.6f}
📊 Sebep: {signal.reason}
⏰ Zaman: {signal.timestamp.strftime("%H:%M:%S")}
"""
            return message.strip()
        except Exception as e:
            logger.error(f"Message formatting error: {e}")
            return f"Signal: {signal.pair} - {signal.signal_type.value}"