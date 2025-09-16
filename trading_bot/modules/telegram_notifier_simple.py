import asyncio
import logging
from telegram import Bot
from telegram.error import TelegramError
from typing import Optional

logger = logging.getLogger(__name__)

class NotificationManager:
    """Basit Telegram bildirim yöneticisi"""
    
    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.bot = Bot(token=bot_token)
    
    async def test_connection(self):
        """Telegram bağlantısını test et"""
        try:
            bot_info = await self.bot.get_me()
            logger.info(f"Telegram bot bağlantısı başarılı: @{bot_info.username}")
            return True
        except Exception as e:
            logger.error(f"Telegram bağlantı hatası: {e}")
            return False
    
    async def send_message(self, message: str):
        """Basit mesaj gönder"""
        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode='Markdown'
            )
            return True
        except Exception as e:
            logger.error(f"Mesaj gönderim hatası: {e}")
            return False