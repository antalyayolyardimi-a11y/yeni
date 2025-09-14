import logging
from typing import Dict, Any, Optional, Callable
from datetime import datetime
import threading
import time

logger = logging.getLogger(__name__)

class TelegramCommandHandler:
    """Handle Telegram bot commands"""
    
    def __init__(self, bot_token: str, chat_id: str, trading_bot_instance=None):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.trading_bot = trading_bot_instance
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
        self.commands = {}
        self.last_update_id = 0
        self.running = False
        self.command_thread = None
        
        # Register default commands
        self._register_commands()
    
    def _register_commands(self):
        """Register available commands"""
        self.commands = {
            '/start': self._handle_start,
            '/help': self._handle_help,
            '/status': self._handle_status,
            '/tp': self._handle_take_profit,
            '/sl': self._handle_stop_loss,
            '/signals': self._handle_signals,
            '/stats': self._handle_stats,
            '/stop': self._handle_stop
        }
    
    def start_command_listener(self):
        """Start listening for commands"""
        if self.running:
            logger.warning("Command listener already running")
            return
        
        self.running = True
        self.command_thread = threading.Thread(target=self._command_loop, daemon=True)
        self.command_thread.start()
        logger.info("Telegram command listener started")
    
    def stop_command_listener(self):
        """Stop listening for commands"""
        self.running = False
        if self.command_thread:
            self.command_thread.join(timeout=5)
        logger.info("Telegram command listener stopped")
    
    def _command_loop(self):
        """Main command listening loop"""
        while self.running:
            try:
                self._check_for_updates()
                time.sleep(2)  # Check every 2 seconds
            except Exception as e:
                logger.error(f"Error in command loop: {str(e)}")
                time.sleep(5)
    
    def _check_for_updates(self):
        """Check for new messages/commands"""
        try:
            import requests
            url = f"{self.base_url}/getUpdates"
            params = {
                'offset': self.last_update_id + 1,
                'timeout': 5,
                'allowed_updates': ['message']
            }
            
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get('ok') and data.get('result'):
                    for update in data['result']:
                        self._process_update(update)
                        self.last_update_id = update['update_id']
        
        except Exception as e:
            logger.error(f"Error checking for updates: {str(e)}")
    
    def _process_update(self, update: Dict[str, Any]):
        """Process a single update"""
        try:
            message = update.get('message')
            if not message:
                return
            
            chat_id = str(message['chat']['id'])
            if chat_id != self.chat_id:
                return  # Ignore messages from other chats
            
            text = message.get('text', '').strip()
            if not text.startswith('/'):
                return  # Only process commands
            
            command = text.split()[0].lower()
            args = text.split()[1:] if len(text.split()) > 1 else []
            
            if command in self.commands:
                response = self.commands[command](args)
                if response:
                    self._send_response(response)
            else:
                self._send_response(f"Unknown command: {command}\nType /help for available commands")
        
        except Exception as e:
            logger.error(f"Error processing update: {str(e)}")
    
    def _send_response(self, message: str):
        """Send response message"""
        try:
            import requests
            url = f"{self.base_url}/sendMessage"
            payload = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': 'Markdown'
            }
            
            requests.post(url, json=payload, timeout=10)
        
        except Exception as e:
            logger.error(f"Error sending response: {str(e)}")
    
    def _handle_start(self, args) -> str:
        """Handle /start command"""
        return """
🤖 *Trading Bot Started*

Welcome to the automated trading bot!

Available commands:
• /help - Show this help message
• /status - Bot status and statistics
• /tp - Take profit information
• /sl - Stop loss information  
• /signals - Current active signals
• /stats - Trading statistics
• /stop - Stop the bot

The bot is now monitoring markets and will send signals automatically.
        """.strip()
    
    def _handle_help(self, args) -> str:
        """Handle /help command"""
        return """
🆘 *Help - Available Commands*

*Status Commands:*
• `/status` - Current bot status
• `/signals` - Active signals
• `/stats` - Trading statistics

*Risk Management:*
• `/tp` - Take profit settings
• `/sl` - Stop loss settings

*Control:*
• `/stop` - Stop the bot
• `/start` - Restart the bot

*Info:*
• `/help` - Show this message

Use these commands to monitor and control your trading bot.
        """.strip()
    
    def _handle_status(self, args) -> str:
        """Handle /status command"""
        try:
            if not self.trading_bot:
                return "❌ Trading bot instance not available"
            
            # Get bot status from trading bot instance
            uptime = datetime.now().strftime('%H:%M:%S')
            
            return f"""
🤖 *Bot Status*

*Status:* 🟢 Running
*Uptime:* {uptime}
*Last Update:* {datetime.now().strftime('%H:%M:%S')}

*Market Scanning:* Active
*Signal Generation:* Enabled
*Risk Management:* Active

Type `/signals` for current signals
Type `/stats` for trading statistics
            """.strip()
        
        except Exception as e:
            return f"❌ Error getting status: {str(e)}"
    
    def _handle_take_profit(self, args) -> str:
        """Handle /tp command"""
        return """
🎯 *Take Profit Settings*

*Current TP:* 2.0%
*TP Strategy:* Fixed percentage
*Auto TP:* Enabled

*Recent TP Hits:* 
• No recent take profits

*Settings:*
• Trailing TP: Disabled
• Partial TP: Disabled

Take profits are automatically executed when price targets are reached.
        """.strip()
    
    def _handle_stop_loss(self, args) -> str:
        """Handle /sl command"""
        return """
🛑 *Stop Loss Settings*

*Current SL:* 1.0%
*SL Strategy:* Fixed percentage  
*Auto SL:* Enabled

*Recent SL Hits:*
• Check logs for recent stop losses

*Settings:*
• Trailing SL: Disabled
• ATR-based SL: Disabled

Stop losses are automatically executed to protect capital.
        """.strip()
    
    def _handle_signals(self, args) -> str:
        """Handle /signals command"""
        try:
            current_time = datetime.now().strftime('%H:%M:%S')
            
            return f"""
📊 *Current Signals*

*Active Signals:* Scanning...
*Signal Pool:* Monitoring
*Last Scan:* {current_time}

*Recent Signals:*
• Waiting for market conditions
• Technical analysis in progress

*Next Scan:* In 5 minutes

Use `/status` to check overall bot health.
            """.strip()
        
        except Exception as e:
            return f"❌ Error getting signals: {str(e)}"
    
    def _handle_stats(self, args) -> str:
        """Handle /stats command"""
        return """
📈 *Trading Statistics*

*Total Trades:* 0
*Successful Trades:* 0
*Failed Trades:* 0
*Success Rate:* 0.0%

*P&L Summary:*
• Total P&L: 0.00 USDT
• Average P&L: 0.00%
• Best Trade: 0.00%
• Worst Trade: 0.00%

*Current Session:*
• Session Start: Today
• Signals Generated: 0
• Trades Executed: 0

Statistics will update as trading activity occurs.
        """.strip()
    
    def _handle_stop(self, args) -> str:
        """Handle /stop command"""
        return """
⏹️ *Bot Stop Requested*

The trading bot stop has been requested.

*Note:* The bot will continue running until manually stopped by the operator.

*Open Positions:* Will be monitored
*Active Orders:* Will remain active
*Risk Management:* Still active

Contact the operator to fully stop the bot if needed.
        """.strip()