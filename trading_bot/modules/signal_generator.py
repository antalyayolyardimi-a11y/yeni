import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from enum import Enum
from datetime import datetime

class SignalType(Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    NEUTRAL = "NEUTRAL"

class SignalStrength(Enum):
    WEAK = "ZAYIF"
    MODERATE = "ORTA"
    STRONG = "GÜÇLÜ"

class TradingSignal:
    def __init__(self, pair: str, signal_type: SignalType, strength: SignalStrength, 
                 price: float, indicators: Dict, timestamp: datetime, reason: str):
        self.pair = pair
        self.signal_type = signal_type
        self.strength = strength
        self.price = price
        self.indicators = indicators
        self.timestamp = timestamp
        self.reason = reason

class SignalGenerator:
    """Trading signal generator"""
    
    def __init__(self):
        self.signal_counts = {
            SignalType.LONG: 0,
            SignalType.SHORT: 0,
            SignalType.NEUTRAL: 0
        }
    
    def analyze_rsi_signals(self, df: pd.DataFrame) -> Tuple[SignalType, str, SignalStrength]:
        """RSI based signal analysis"""
        current_rsi = df['rsi'].iloc[-1]
        if pd.isna(current_rsi):
            return SignalType.NEUTRAL, "", SignalStrength.WEAK
        
        if current_rsi < 30:
            return SignalType.LONG, f"RSI oversold ({current_rsi:.1f})", SignalStrength.MODERATE
        elif current_rsi > 70:
            return SignalType.SHORT, f"RSI overbought ({current_rsi:.1f})", SignalStrength.MODERATE
        
        return SignalType.NEUTRAL, "", SignalStrength.WEAK
    
    def analyze_ema_signals(self, df: pd.DataFrame) -> Tuple[SignalType, str, SignalStrength]:
        """EMA crossover signal analysis"""
        if len(df) < 2:
            return SignalType.NEUTRAL, "", SignalStrength.WEAK
            
        current_ema_fast = df['ema_fast'].iloc[-1]
        current_ema_slow = df['ema_slow'].iloc[-1]
        prev_ema_fast = df['ema_fast'].iloc[-2]
        prev_ema_slow = df['ema_slow'].iloc[-2]
        
        if pd.isna(current_ema_fast) or pd.isna(current_ema_slow):
            return SignalType.NEUTRAL, "", SignalStrength.WEAK
        
        # Golden Cross
        if prev_ema_fast <= prev_ema_slow and current_ema_fast > current_ema_slow:
            return SignalType.LONG, "EMA Golden Cross", SignalStrength.STRONG
        
        # Death Cross
        elif prev_ema_fast >= prev_ema_slow and current_ema_fast < current_ema_slow:
            return SignalType.SHORT, "EMA Death Cross", SignalStrength.STRONG
        
        return SignalType.NEUTRAL, "", SignalStrength.WEAK
    
    def analyze_macd_signals(self, df: pd.DataFrame) -> Tuple[SignalType, str, SignalStrength]:
        """MACD signal analysis"""
        if len(df) < 2:
            return SignalType.NEUTRAL, "", SignalStrength.WEAK
            
        current_macd = df['macd'].iloc[-1]
        current_signal = df['macd_signal'].iloc[-1]
        prev_macd = df['macd'].iloc[-2]
        prev_signal = df['macd_signal'].iloc[-2]
        
        if pd.isna(current_macd) or pd.isna(current_signal):
            return SignalType.NEUTRAL, "", SignalStrength.WEAK
        
        # MACD crosses above signal line
        if prev_macd <= prev_signal and current_macd > current_signal:
            return SignalType.LONG, "MACD golden cross", SignalStrength.MODERATE
        
        # MACD crosses below signal line
        elif prev_macd >= prev_signal and current_macd < current_signal:
            return SignalType.SHORT, "MACD death cross", SignalStrength.MODERATE
        
        return SignalType.NEUTRAL, "", SignalStrength.WEAK
    
    def generate_signal(self, pair: str, df: pd.DataFrame) -> Optional[TradingSignal]:
        """Generate trading signal"""
        if len(df) < 30:
            return None
        
        # Analyze different indicators
        rsi_signal, rsi_reason, rsi_strength = self.analyze_rsi_signals(df)
        ema_signal, ema_reason, ema_strength = self.analyze_ema_signals(df)
        macd_signal, macd_reason, macd_strength = self.analyze_macd_signals(df)
        
        # Collect signals and their strengths
        signals_data = [
            (rsi_signal, rsi_reason, rsi_strength),
            (ema_signal, ema_reason, ema_strength),
            (macd_signal, macd_reason, macd_strength)
        ]
        
        # Count signals by type
        signal_counts = {SignalType.LONG: 0, SignalType.SHORT: 0, SignalType.NEUTRAL: 0}
        reasons = []
        
        for signal, reason, strength in signals_data:
            signal_counts[signal] += 1
            if reason:
                reasons.append(reason)
        
        # Find dominant signal - Fix for Pylance error: use lambda instead of signal_counts.get
        final_signal = max(signal_counts, key=lambda signal_type: signal_counts[signal_type])
        
        # Only generate signal if we have consensus
        if signal_counts[final_signal] <= 1 or final_signal == SignalType.NEUTRAL:
            return None
        
        # Determine final strength
        final_strength = SignalStrength.MODERATE
        
        current_price = df['close'].iloc[-1]
        current_indicators = {
            'rsi': df['rsi'].iloc[-1] if 'rsi' in df.columns else None,
            'macd': df['macd'].iloc[-1] if 'macd' in df.columns else None,
            'ema_fast': df['ema_fast'].iloc[-1] if 'ema_fast' in df.columns else None,
            'ema_slow': df['ema_slow'].iloc[-1] if 'ema_slow' in df.columns else None
        }
        
        return TradingSignal(
            pair=pair,
            signal_type=final_signal,
            strength=final_strength,
            price=current_price,
            indicators=current_indicators,
            timestamp=datetime.now(),
            reason=" | ".join(reasons[:2])
        )