import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class SignalType(Enum):
    """Signal types for trading"""
    LONG = "LONG"
    SHORT = "SHORT"
    NEUTRAL = "NEUTRAL"

class SignalStrength(Enum):
    """Signal strength levels"""
    WEAK = "WEAK"
    MODERATE = "MODERATE"
    STRONG = "STRONG"

class TechnicalIndicators:
    """Technical analysis indicators for signal generation"""
    
    @staticmethod
    def rsi(data: pd.Series, period: int = 14) -> pd.Series:
        """Calculate RSI (Relative Strength Index)"""
        delta = data.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    @staticmethod
    def ema(data: pd.Series, period: int) -> pd.Series:
        """Calculate EMA (Exponential Moving Average)"""
        return data.ewm(span=period, adjust=False).mean()
    
    @staticmethod
    def macd(data: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Calculate MACD (Moving Average Convergence Divergence)"""
        ema_fast = TechnicalIndicators.ema(data, fast)
        ema_slow = TechnicalIndicators.ema(data, slow)
        macd_line = ema_fast - ema_slow
        signal_line = TechnicalIndicators.ema(macd_line, signal)
        histogram = macd_line - signal_line
        return macd_line, signal_line, histogram
    
    @staticmethod
    def stochastic(high: pd.Series, low: pd.Series, close: pd.Series, k_period: int = 14, d_period: int = 3) -> Tuple[pd.Series, pd.Series]:
        """Calculate Stochastic Oscillator"""
        lowest_low = low.rolling(window=k_period).min()
        highest_high = high.rolling(window=k_period).max()
        k_percent = 100 * ((close - lowest_low) / (highest_high - lowest_low))
        d_percent = k_percent.rolling(window=d_period).mean()
        return k_percent, d_percent
    
    @staticmethod
    def bollinger_bands(data: pd.Series, period: int = 20, std_dev: float = 2) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Calculate Bollinger Bands"""
        sma = data.rolling(window=period).mean()
        std = data.rolling(window=period).std()
        upper_band = sma + (std * std_dev)
        lower_band = sma - (std * std_dev)
        return upper_band, sma, lower_band

class SignalGenerator:
    """Generate trading signals based on technical analysis"""
    
    def __init__(self):
        self.rsi_period = 14
        self.rsi_overbought = 70
        self.rsi_oversold = 30
        self.ema_fast = 12
        self.ema_slow = 26
        self.macd_fast = 12
        self.macd_slow = 26
        self.macd_signal = 9
        
    def analyze_market_data(self, df: pd.DataFrame, symbol: str) -> Dict:
        """Analyze market data and generate signals"""
        try:
            if len(df) < 50:
                logger.warning(f"Insufficient data for {symbol}: {len(df)} candles")
                return self._create_signal_result(symbol, SignalType.NEUTRAL, SignalStrength.WEAK, 0.0, "Insufficient data")
            
            # Calculate technical indicators
            close_prices = df['close']
            high_prices = df['high']
            low_prices = df['low']
            volume = df['volume']
            
            # RSI
            rsi = TechnicalIndicators.rsi(close_prices, self.rsi_period)
            current_rsi = rsi.iloc[-1]
            
            # EMA
            ema_fast = TechnicalIndicators.ema(close_prices, self.ema_fast)
            ema_slow = TechnicalIndicators.ema(close_prices, self.ema_slow)
            
            # MACD
            macd_line, signal_line, histogram = TechnicalIndicators.macd(
                close_prices, self.macd_fast, self.macd_slow, self.macd_signal
            )
            
            # Stochastic
            stoch_k, stoch_d = TechnicalIndicators.stochastic(high_prices, low_prices, close_prices)
            
            # Volume analysis
            volume_sma = volume.rolling(window=20).mean()
            volume_ratio = volume.iloc[-1] / volume_sma.iloc[-1] if volume_sma.iloc[-1] > 0 else 1.0
            
            # Generate signal
            signal_type, strength, confidence = self._generate_signal(
                current_rsi, ema_fast.iloc[-1], ema_slow.iloc[-1],
                macd_line.iloc[-1], signal_line.iloc[-1], histogram.iloc[-1],
                stoch_k.iloc[-1], stoch_d.iloc[-1], volume_ratio
            )
            
            return self._create_signal_result(symbol, signal_type, strength, confidence, "Technical analysis")
            
        except Exception as e:
            logger.error(f"Error analyzing {symbol}: {str(e)}")
            return self._create_signal_result(symbol, SignalType.NEUTRAL, SignalStrength.WEAK, 0.0, f"Error: {str(e)}")
    
    def _generate_signal(self, rsi: float, ema_fast: float, ema_slow: float,
                        macd: float, signal: float, histogram: float,
                        stoch_k: float, stoch_d: float, volume_ratio: float) -> Tuple[SignalType, SignalStrength, float]:
        """Generate trading signal based on technical indicators"""
        
        bullish_signals = 0
        bearish_signals = 0
        signal_strength_scores = []
        
        # RSI Analysis - More sensitive thresholds
        if rsi < self.rsi_oversold:
            bullish_signals += 2  # Strong signal
            signal_strength_scores.append(0.9)
        elif rsi > self.rsi_overbought:
            bearish_signals += 2  # Strong signal
            signal_strength_scores.append(0.9)
        elif 30 < rsi < 45:
            bullish_signals += 1
            signal_strength_scores.append(0.6)
        elif 55 < rsi < 70:
            bearish_signals += 1
            signal_strength_scores.append(0.6)
        
        # EMA Analysis - Enhanced weight
        ema_diff_percent = ((ema_fast - ema_slow) / ema_slow) * 100
        if ema_diff_percent > 0.5:  # Strong bullish trend
            bullish_signals += 1.5
            signal_strength_scores.append(0.8)
        elif ema_diff_percent > 0:  # Weak bullish trend
            bullish_signals += 0.8
            signal_strength_scores.append(0.5)
        elif ema_diff_percent < -0.5:  # Strong bearish trend
            bearish_signals += 1.5
            signal_strength_scores.append(0.8)
        elif ema_diff_percent < 0:  # Weak bearish trend
            bearish_signals += 0.8
            signal_strength_scores.append(0.5)
        
        # MACD Analysis - Enhanced sensitivity
        if macd > signal and histogram > 0:
            bullish_signals += 1.2
            signal_strength_scores.append(0.8)
        elif macd < signal and histogram < 0:
            bearish_signals += 1.2
            signal_strength_scores.append(0.8)
        elif macd > signal:  # MACD bullish but weakening
            bullish_signals += 0.6
            signal_strength_scores.append(0.4)
        elif macd < signal:  # MACD bearish but weakening
            bearish_signals += 0.6
            signal_strength_scores.append(0.4)
        
        # Stochastic Analysis - More sensitive
        if stoch_k < 20 and stoch_d < 20 and stoch_k > stoch_d:  # Oversold with bullish divergence
            bullish_signals += 1.5
            signal_strength_scores.append(0.7)
        elif stoch_k > 80 and stoch_d > 80 and stoch_k < stoch_d:  # Overbought with bearish divergence
            bearish_signals += 1.5
            signal_strength_scores.append(0.7)
        elif stoch_k < 30:  # General oversold
            bullish_signals += 0.8
            signal_strength_scores.append(0.4)
        elif stoch_k > 70:  # General overbought
            bearish_signals += 0.8
            signal_strength_scores.append(0.4)
        
        # Volume Analysis - Enhanced
        if volume_ratio > 2.0:  # Very high volume
            signal_strength_scores.append(0.6)
        elif volume_ratio > 1.5:  # High volume
            signal_strength_scores.append(0.4)
        elif volume_ratio > 1.2:  # Above average volume
            signal_strength_scores.append(0.2)
        
        # Determine signal type
        signal_diff = bullish_signals - bearish_signals
        if signal_diff > 0.5:
            signal_type = SignalType.LONG
            signal_count = bullish_signals
        elif signal_diff < -0.5:
            signal_type = SignalType.SHORT
            signal_count = bearish_signals
        else:
            signal_type = SignalType.NEUTRAL
            signal_count = 0
        
        # Calculate confidence with enhanced scoring
        max_possible_signals = 6.0  # Increased max possible
        confidence = min(100.0, (signal_count / max_possible_signals) * 100)
        
        # Boost confidence if multiple indicators align
        if len(signal_strength_scores) >= 3:
            confidence *= 1.2  # 20% boost for multiple confirmations
        
        confidence = min(100.0, confidence)  # Cap at 100%
        
        # Determine strength with adjusted thresholds
        if confidence >= 70:
            strength = SignalStrength.STRONG
        elif confidence >= 50:
            strength = SignalStrength.MODERATE
        else:
            strength = SignalStrength.WEAK
        
        return signal_type, strength, confidence
    
    def _create_signal_result(self, symbol: str, signal_type: SignalType, 
                            strength: SignalStrength, confidence: float, reason: str) -> Dict:
        """Create a standardized signal result"""
        return {
            'symbol': symbol,
            'signal': signal_type.value,
            'strength': strength.value,
            'confidence': round(confidence, 2),
            'reason': reason,
            'timestamp': pd.Timestamp.now().isoformat()
        }
    
    def get_signal_summary(self, signals: List[Dict]) -> Dict:
        """Get summary of all signals"""
        if not signals:
            return {'total': 0, 'long': 0, 'short': 0, 'neutral': 0, 'avg_confidence': 0.0}
        
        signal_counts = {}
        total_confidence = 0
        
        for signal in signals:
            signal_type = signal['signal']
            signal_counts[signal_type] = signal_counts.get(signal_type, 0) + 1
            total_confidence += signal['confidence']
        
        return {
            'total': len(signals),
            'long': signal_counts.get('LONG', 0),
            'short': signal_counts.get('SHORT', 0),  
            'neutral': signal_counts.get('NEUTRAL', 0),
            'avg_confidence': round(total_confidence / len(signals), 2)
        }