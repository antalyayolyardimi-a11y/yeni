# Trading Bot Modules Package
"""
Trading bot modules for signal generation, notifications, and commands.
"""

__version__ = "1.0.0"

# Make key classes available at package level
from .signal_generator import SignalGenerator, SignalType, SignalStrength, TradingSignal
from .telegram_notifier import NotificationManager
from .telegram_commands import TelegramCommandHandler

__all__ = [
    'SignalGenerator',
    'SignalType', 
    'SignalStrength',
    'TradingSignal',
    'NotificationManager',
    'TelegramCommandHandler'
]