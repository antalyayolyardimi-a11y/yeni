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

class FastSignalGenerator:
    """Kısa vadeli trading için hızlı sinyal üretimi"""
    
    def __init__(self, rsi_oversold=25, rsi_overbought=75, min_volume_ratio=1.3):
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought
        self.min_volume_ratio = min_volume_ratio
    
    def analyze_fast_rsi_signals(self, df: pd.DataFrame) -> Tuple[SignalType, str, SignalStrength]:
        """Hızlı RSI tabanlı sinyal analizi"""
        current_rsi = df['rsi'].iloc[-1]
        prev_rsi = df['rsi'].iloc[-2]
        
        if pd.isna(current_rsi) or pd.isna(prev_rsi):
            return SignalType.NEUTRAL, "", SignalStrength.WEAK
        
        # RSI momentum kontrolü (daha hızlı sinyaller)
        rsi_momentum = current_rsi - prev_rsi
        
        if current_rsi < self.rsi_oversold:
            if rsi_momentum > 0:  # RSI yükselmeye başladı
                strength = SignalStrength.STRONG if current_rsi < 20 else SignalStrength.MODERATE
                return SignalType.LONG, f"RSI aşırı satım bölgesinde yükseliş ({current_rsi:.1f})", strength
        
        elif current_rsi > self.rsi_overbought:
            if rsi_momentum < 0:  # RSI düşmeye başladı
                strength = SignalStrength.STRONG if current_rsi > 80 else SignalStrength.MODERATE
                return SignalType.SHORT, f"RSI aşırı alım bölgesinde düşüş ({current_rsi:.1f})", strength
        
        # RSI orta seviye momentum
        elif 40 < current_rsi < 60:
            if rsi_momentum > 3:
                return SignalType.LONG, f"RSI momentum artışı ({current_rsi:.1f})", SignalStrength.WEAK
            elif rsi_momentum < -3:
                return SignalType.SHORT, f"RSI momentum azalışı ({current_rsi:.1f})", SignalStrength.WEAK
        
        return SignalType.NEUTRAL, "", SignalStrength.WEAK
    
    def analyze_ema_signals(self, df: pd.DataFrame) -> Tuple[SignalType, str, SignalStrength]:
        """EMA crossover tabanlı sinyal analizi"""
        current_price = df['close'].iloc[-1]
        current_ema_fast = df['ema_fast'].iloc[-1]
        current_ema_slow = df['ema_slow'].iloc[-1]
        prev_ema_fast = df['ema_fast'].iloc[-2]
        prev_ema_slow = df['ema_slow'].iloc[-2]
        
        if pd.isna(current_ema_fast) or pd.isna(current_ema_slow):
            return SignalType.NEUTRAL, "", SignalStrength.WEAK
        
        # EMA Golden Cross: Fast EMA crosses above Slow EMA
        if prev_ema_fast <= prev_ema_slow and current_ema_fast > current_ema_slow:
            return SignalType.LONG, f"EMA Golden Cross", SignalStrength.STRONG
        
        # EMA Death Cross: Fast EMA crosses below Slow EMA
        elif prev_ema_fast >= prev_ema_slow and current_ema_fast < current_ema_slow:
            return SignalType.SHORT, f"EMA Death Cross", SignalStrength.STRONG
        
        # Fiyat EMA'ların üzerinde/altında
        elif current_price > current_ema_fast > current_ema_slow:
            ema_distance = ((current_price - current_ema_fast) / current_ema_fast) * 100
            if ema_distance < 2:  # Fiyat EMA'ya yakın
                return SignalType.LONG, f"Fiyat EMA üzerinde trend yukarı", SignalStrength.MODERATE
        
        elif current_price < current_ema_fast < current_ema_slow:
            ema_distance = ((current_ema_fast - current_price) / current_ema_fast) * 100
            if ema_distance < 2:  # Fiyat EMA'ya yakın
                return SignalType.SHORT, f"Fiyat EMA altında trend aşağı", SignalStrength.MODERATE
        
        return SignalType.NEUTRAL, "", SignalStrength.WEAK
    
    def analyze_fast_macd_signals(self, df: pd.DataFrame) -> Tuple[SignalType, str, SignalStrength]:
        """Hızlı MACD tabanlı sinyal analizi"""
        current_macd = df['macd'].iloc[-1]
        current_signal = df['macd_signal'].iloc[-1]
        prev_macd = df['macd'].iloc[-2]
        prev_signal = df['macd_signal'].iloc[-2]
        current_histogram = df['macd_histogram'].iloc[-1]
        prev_histogram = df['macd_histogram'].iloc[-2]
        
        if pd.isna(current_macd) or pd.isna(current_signal):
            return SignalType.NEUTRAL, "", SignalStrength.WEAK
        
        # MACD line crosses signal line
        if prev_macd <= prev_signal and current_macd > current_signal:
            strength = SignalStrength.STRONG if current_histogram > 0 else SignalStrength.MODERATE
            return SignalType.LONG, f"MACD golden cross", strength
        
        elif prev_macd >= prev_signal and current_macd < current_signal:
            strength = SignalStrength.STRONG if current_histogram < 0 else SignalStrength.MODERATE
            return SignalType.SHORT, f"MACD death cross", strength
        
        # Histogram momentum (daha hızlı sinyal)
        histogram_change = current_histogram - prev_histogram
        if abs(histogram_change) > 0.0001:  # Histogram değişimi
            if current_histogram > 0 and histogram_change > 0:
                return SignalType.LONG, f"MACD histogram momentum artışı", SignalStrength.WEAK
            elif current_histogram < 0 and histogram_change < 0:
                return SignalType.SHORT, f"MACD histogram momentum azalışı", SignalStrength.WEAK
        
        return SignalType.NEUTRAL, "", SignalStrength.WEAK
    
    def analyze_stochastic_signals(self, df: pd.DataFrame) -> Tuple[SignalType, str, SignalStrength]:
        """Hızlı Stochastic sinyal analizi"""
        current_k = df['stoch_k'].iloc[-1]
        current_d = df['stoch_d'].iloc[-1]
        prev_k = df['stoch_k'].iloc[-2]
        prev_d = df['stoch_d'].iloc[-2]
        
        if pd.isna(current_k) or pd.isna(current_d):
            return SignalType.NEUTRAL, "", SignalStrength.WEAK
        
        # Stochastic crossover
        if prev_k <= prev_d and current_k > current_d:
            if current_k < 30:  # Aşırı satım bölgesinde
                return SignalType.LONG, f"Stochastic golden cross (aşırı satım)", SignalStrength.MODERATE
            else:
                return SignalType.LONG, f"Stochastic golden cross", SignalStrength.WEAK
        
        elif prev_k >= prev_d and current_k < current_d:
            if current_k > 70:  # Aşırı alım bölgesinde
                return SignalType.SHORT, f"Stochastic death cross (aşırı alım)", SignalStrength.MODERATE
            else:
                return SignalType.SHORT, f"Stochastic death cross", SignalStrength.WEAK
        
        return SignalType.NEUTRAL, "", SignalStrength.WEAK
    
    def analyze_momentum_signals(self, df: pd.DataFrame) -> Tuple[SignalType, str, SignalStrength]:
        """Momentum ve ROC tabanlı sinyal analizi"""
        current_momentum = df['momentum'].iloc[-1]
        current_roc = df['roc'].iloc[-1]
        williams_r = df['williams_r'].iloc[-1]
        
        if pd.isna(current_momentum) or pd.isna(current_roc):
            return SignalType.NEUTRAL, "", SignalStrength.WEAK
        
        # Güçlü momentum sinyalleri
        if current_momentum > 2 and current_roc > 1:
            if williams_r < -80:  # Aşırı satım + momentum
                return SignalType.LONG, f"Güçlü yukarı momentum ({current_momentum:.1f}%)", SignalStrength.STRONG
            else:
                return SignalType.LONG, f"Yukarı momentum ({current_momentum:.1f}%)", SignalStrength.MODERATE
        
        elif current_momentum < -2 and current_roc < -1:
            if williams_r > -20:  # Aşırı alım + negatif momentum
                return SignalType.SHORT, f"Güçlü aşağı momentum ({current_momentum:.1f}%)", SignalStrength.STRONG
            else:
                return SignalType.SHORT, f"Aşağı momentum ({current_momentum:.1f}%)", SignalStrength.MODERATE
        
        return SignalType.NEUTRAL, "", SignalStrength.WEAK
    
    def analyze_volume_confirmation(self, df: pd.DataFrame) -> Tuple[bool, str]:
        """Volume confirmation kontrolü"""
        current_volume_ratio = df['volume_ratio'].iloc[-1]
        volume_roc = df['volume_roc'].iloc[-1]
        
        if pd.isna(current_volume_ratio):
            return False, ""
        
        if current_volume_ratio >= self.min_volume_ratio:
            if volume_roc > 20:  # Volume hızla artıyor
                return True, "Yüksek volume konfirmasyonu"
            else:
                return True, "Volume konfirmasyonu"
        
        return False, ""
    
    def generate_signal(self, pair: str, df: pd.DataFrame) -> Optional[TradingSignal]:
        """Ana hızlı sinyal üretme fonksiyonu"""
        if len(df) < 30:  # Daha az veri yeterli
            return None
        
        # Tüm sinyalleri analiz et
        rsi_signal, rsi_reason, rsi_strength = self.analyze_fast_rsi_signals(df)
        ema_signal, ema_reason, ema_strength = self.analyze_ema_signals(df)
        macd_signal, macd_reason, macd_strength = self.analyze_fast_macd_signals(df)
        stoch_signal, stoch_reason, stoch_strength = self.analyze_stochastic_signals(df)
        momentum_signal, momentum_reason, momentum_strength = self.analyze_momentum_signals(df)
        
        # Volume confirmation
        volume_confirmed, volume_reason = self.analyze_volume_confirmation(df)
        
        # Sinyal skorlaması
        signal_scores = {SignalType.LONG: 0, SignalType.SHORT: 0, SignalType.NEUTRAL: 0}
        reasons = []
        
        # Her gösterge için skor hesapla
        for signal, reason, strength in [
            (rsi_signal, rsi_reason, rsi_strength),
            (ema_signal, ema_reason, ema_strength),
            (macd_signal, macd_reason, macd_strength),
            (stoch_signal, stoch_reason, stoch_strength),
            (momentum_signal, momentum_reason, momentum_strength)
        ]:
            if signal != SignalType.NEUTRAL:
                score = 1
                if strength == SignalStrength.MODERATE:
                    score = 2
                elif strength == SignalStrength.STRONG:
                    score = 3
                
                signal_scores[signal] += score
                if reason:
                    reasons.append(reason)
        
        # En yüksek skora sahip sinyali seç
        final_signal = max(signal_scores, key=signal_scores.get)
        max_score = signal_scores[final_signal]
        
        # Daha düşük eşik (hızlı sinyaller için)
        if max_score < 2:
            return None
        
        # Final sinyal gücünü hesapla
        if max_score >= 5:
            final_strength = SignalStrength.STRONG
        elif max_score >= 3:
            final_strength = SignalStrength.MODERATE
        else:
            final_strength = SignalStrength.WEAK
        
        # Volume confirmation bonus
        if volume_confirmed and final_signal != SignalType.NEUTRAL:
            reasons.append(volume_reason)
            if final_strength == SignalStrength.WEAK:
                final_strength = SignalStrength.MODERATE
        
        current_price = df['close'].iloc[-1]
        current_indicators = {
            'rsi': df['rsi'].iloc[-1],
            'macd': df['macd'].iloc[-1],
            'ema_fast': df['ema_fast'].iloc[-1],
            'ema_slow': df['ema_slow'].iloc[-1],
            'stoch_k': df['stoch_k'].iloc[-1],
            'momentum': df['momentum'].iloc[-1],
            'volume_ratio': df['volume_ratio'].iloc[-1],
            'price_change': df['price_change'].iloc[-1]
        }
        
        return TradingSignal(
            pair=pair,
            signal_type=final_signal,
            strength=final_strength,
            price=current_price,
            indicators=current_indicators,
            timestamp=datetime.now(),
            reason=" | ".join(reasons[:3])  # En fazla 3 sebep
        )

# Geriye uyumluluk
SignalGenerator = FastSignalGenerator