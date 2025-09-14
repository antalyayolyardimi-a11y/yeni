import logging
from typing import Optional
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, ContextTypes

logger = logging.getLogger(__name__)

class TelegramCommandHandler:
    """Telegram command handler for trading bot"""
    
    def __init__(self, bot_token: str, data_provider, notification_manager):
        self.bot_token = bot_token
        self.data_provider = data_provider
        self.notification_manager = notification_manager
        self.application = None
    
    def setup_commands(self):
        """Setup command handlers"""
        if not self.application:
            self.application = Application.builder().token(self.bot_token).build()
        
        # Add command handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("status", self.status_command))
        self.application.add_handler(CommandHandler("tp", self.tp_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command"""
        if update.message:
            await update.message.reply_text(
                "🤖 Trading Bot Started!\n\n"
                "Available commands:\n"
                "/status - Bot status\n"
                "/tp - Take profit info\n"
                "/help - Show help"
            )
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /status command"""
        try:
            status_message = "🤖 **Bot Status**\n\n"
            status_message += "✅ Bot is running\n"
            status_message += "📊 Monitoring markets\n"
            status_message += "🔔 Notifications active"
            
            if update.message:
                await update.message.reply_text(status_message)
        except Exception as e:
            logger.error(f"Status command error: {e}")
            if update.message:
                await update.message.reply_text("❌ Error getting status")
    
    async def tp_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /tp command"""
        try:
            tp_message = "🎯 **Take Profit Info**\n\n"
            tp_message += "Currently no active positions\n"
            tp_message += "Use this command to check TP levels"
            
            if update.message:
                await update.message.reply_text(tp_message)
        except Exception as e:
            logger.error(f"TP command error: {e}")
            if update.message:
                await update.message.reply_text("❌ Error getting TP info")
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /help command"""
        help_text = """
🤖 **Trading Bot Commands**

/start - Start the bot
/status - Check bot status  
/tp - Take profit information
/help - Show this help message

📊 The bot monitors markets and sends trading signals automatically.
        """
        
        if update.message:
            await update.message.reply_text(help_text.strip())
    
    async def start_bot(self):
        """Start the Telegram bot"""
        try:
            if not self.application:
                self.setup_commands()
            
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling()
            
            logger.info("Telegram command bot started")
        except Exception as e:
            logger.error(f"Failed to start Telegram bot: {e}")
    
    async def stop_bot(self):
        """Stop the Telegram bot"""
        try:
            if self.application:
                await self.application.updater.stop()
                await self.application.stop()
                await self.application.shutdown()
            
            logger.info("Telegram command bot stopped")
        except Exception as e:
            logger.error(f"Failed to stop Telegram bot: {e}")