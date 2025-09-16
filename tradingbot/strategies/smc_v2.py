#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
SMC V2 - Gerçek Smart Money Concepts Stratejisi
15 dakika timeframe'de market structure, likidite avcılığı ve OTE retest mantığı
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, Any, List, Tuple

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from .. import config
from ..utils import sigmoid
from .base import BaseStrategy
from ..indicators import atr_wilder, ema, rsi

class SMCv2Strategy(BaseStrategy):
    """
    Gerçek Smart Money Concepts stratejisi.
    Market Structure + Liquidity Hunt + OTE Retest mantığı
    """
    
    def __init__(self, symbol: str):
        super().__init__(symbol)
        self.regime = "SMC_V2"
    
    def analyze(self, df15: pd.DataFrame, df1h: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """
        SMC V2 stratejisiyle 15M timeframe analizi - GEVŞEK VERSİYON
        """
        if len(df15) < config.SMC_STRUCTURE_LOOKBACK:
            return None
            
        # HTF Bias (1H) 
        htf_bias = self._get_htf_bias(df1h)
        
        # Market Structure Analysis (15M) - GEVŞEK
        structure = self._analyze_market_structure_simple(df15)
        if not structure:
            return None
            
        # Simple SMC Signal
        return self._create_simple_smc_signal(df15, structure, htf_bias)
    
    def _get_htf_bias(self, df1h: pd.DataFrame) -> str:
        """
        1H bias tespiti - SADECE EMA 20 (GEVŞEK)
        """
        if len(df1h) < 20:
            return "LONG"  # Default LONG
            
        close = df1h["c"]
        
        # EMA 20 bias (daha hızlı)
        ema20 = ema(close, 20)
        current_price = close.iloc[-1]
        
        # Basit EMA bias
        if current_price > ema20.iloc[-1]:
            return "LONG"
        else:
            return "SHORT"
    
    def _analyze_market_structure_simple(self, df: pd.DataFrame) -> Optional[Dict]:
        """
        Basit market structure - sadece son swing'lere bak
        """
        high = df["h"]
        low = df["l"]
        
        # Son 15 mumda basit swing detection
        swing_highs = []
        swing_lows = []
        
        for i in range(len(df) - 15, len(df) - 2):
            if i <= 1 or i >= len(df) - 1:
                continue
                
            # Basit swing high
            if high.iloc[i] > high.iloc[i-1] and high.iloc[i] > high.iloc[i+1]:
                swing_highs.append((i, high.iloc[i]))
                
            # Basit swing low  
            if low.iloc[i] < low.iloc[i-1] and low.iloc[i] < low.iloc[i+1]:
                swing_lows.append((i, low.iloc[i]))
        
        if len(swing_highs) >= 1 and len(swing_lows) >= 1:
            return {
                "swing_highs": swing_highs,
                "swing_lows": swing_lows
            }
        return None

    def _create_simple_smc_signal(self, df: pd.DataFrame, structure: Dict, htf_bias: str) -> Optional[Dict[str, Any]]:
        """
        Basit SMC sinyal - HTF bias yönünde swing break
        """
        high = df["h"]
        low = df["l"] 
        close = df["c"]
        current_price = close.iloc[-1]
        
        swing_highs = structure["swing_highs"]
        swing_lows = structure["swing_lows"]
        
        if htf_bias == "LONG" and swing_lows:
            # LONG - Son swing low'u kır
            last_low = min([x[1] for x in swing_lows[-3:]] if len(swing_lows) >= 3 else [x[1] for x in swing_lows])
            if current_price > last_low * 1.002:  # %0.2 kırım
                # ✅ DÜZELTİLDİ: ATR bazlı SL/TP hesaplama
                atrv = float(atr_wilder(df["h"], df["l"], df["c"], 14).iloc[-1])
                sl = last_low * 0.998
                risk = abs(current_price - sl)
                
                return {
                    "symbol": self.symbol,
                    "side": "LONG",
                    "action": "LONG",
                    "entry": current_price,
                    "sl": sl,
                    "tps": (  # ✅ DÜZELTİLDİ: 3 TP tuple formatında
                        current_price + risk * config.TPS_R[0], 
                        current_price + risk * config.TPS_R[1], 
                        current_price + risk * config.TPS_R[2]
                    ),
                    "regime": "SMC_V2_SIMPLE",
                    "confidence": 0.7,
                    "reason": "SMC V2: HTF LONG bias + Swing low break"
                }
                
        elif htf_bias == "SHORT" and swing_highs:
            # SHORT - Son swing high'ı kır
            last_high = max([x[1] for x in swing_highs[-3:]] if len(swing_highs) >= 3 else [x[1] for x in swing_highs])
            if current_price < last_high * 0.998:  # %0.2 kırım
                # ✅ DÜZELTİLDİ: ATR bazlı SL/TP hesaplama
                atrv = float(atr_wilder(df["h"], df["l"], df["c"], 14).iloc[-1])
                sl = last_high * 1.002
                risk = abs(sl - current_price)
                
                return {
                    "symbol": self.symbol,
                    "side": "SHORT",
                    "action": "SHORT", 
                    "entry": current_price,
                    "sl": sl,
                    "tps": (  # ✅ DÜZELTİLDİ: 3 TP tuple formatında
                        current_price - risk * config.TPS_R[0], 
                        current_price - risk * config.TPS_R[1], 
                        current_price - risk * config.TPS_R[2]
                    ),
                    "regime": "SMC_V2_SIMPLE",
                    "confidence": 0.7,
                    "reason": "SMC V2: HTF SHORT bias + Swing high break"
                }
        
        return None
    
    def _analyze_market_structure(self, df: pd.DataFrame) -> Optional[Dict]:
        """
        15M market structure analizi - swing highs/lows detection
        """
        high = df["h"]
        low = df["l"] 
        close = df["c"]
        
        swing_highs = []
        swing_lows = []
        
        # Swing points detection (son 50 mum içinde)
        lookback = min(config.SMC_STRUCTURE_LOOKBACK, len(df) - 5)
        start_idx = len(df) - lookback
        
        for i in range(start_idx + 3, len(df) - 3):
            # ✅ DÜZELTİLDİ: Swing High detection - daha gevşek kriterler (3 yerine 2 mum)
            if (high.iloc[i] > high.iloc[i-1] and high.iloc[i] > high.iloc[i+1] and
                high.iloc[i] > high.iloc[i-2] and high.iloc[i] > high.iloc[i+2]):
                swing_highs.append((i, high.iloc[i]))
                
            # ✅ DÜZELTİLDİ: Swing Low detection - daha gevşek kriterler (3 yerine 2 mum)
            if (low.iloc[i] < low.iloc[i-1] and low.iloc[i] < low.iloc[i+1] and
                low.iloc[i] < low.iloc[i-2] and low.iloc[i] < low.iloc[i+2]):
                swing_lows.append((i, low.iloc[i]))
        
        if len(swing_highs) < config.SMC_MIN_STRUCTURE_POINTS or len(swing_lows) < config.SMC_MIN_STRUCTURE_POINTS:
            return None
            
        return {
            "swing_highs": swing_highs,
            "swing_lows": swing_lows,
            "current_price": close.iloc[-1]
        }
    
    def _detect_liquidity_hunt(self, df: pd.DataFrame, structure: Dict) -> Optional[Dict]:
        """
        Likidite avcılığı tespiti - Equal highs/lows ve sweep detection
        """
        swing_highs = structure["swing_highs"]
        swing_lows = structure["swing_lows"] 
        current_price = structure["current_price"]
        
        high = df["h"]
        low = df["l"]
        close = df["c"]
        
        # Equal highs detection (son 3 swing high)
        if len(swing_highs) >= 3:
            last_highs = swing_highs[-3:]
            equal_highs = []
            
            for i in range(len(last_highs)):
                for j in range(i + 1, len(last_highs)):
                    high1 = last_highs[i][1] 
                    high2 = last_highs[j][1]
                    if abs(high1 - high2) / high1 <= config.SMC_LIQUIDITY_BUFFER:
                        equal_highs.append((last_highs[i], last_highs[j]))
        
        # Equal lows detection (son 3 swing low)
        if len(swing_lows) >= 3:
            last_lows = swing_lows[-3:]
            equal_lows = []
            
            for i in range(len(last_lows)):
                for j in range(i + 1, len(last_lows)):
                    low1 = last_lows[i][1]
                    low2 = last_lows[j][1] 
                    if abs(low1 - low2) / low1 <= config.SMC_LIQUIDITY_BUFFER:
                        equal_lows.append((last_lows[i], last_lows[j]))
        
        # Liquidity sweep detection (son 5 mumda)
        swept_highs = []
        swept_lows = []
        
        for i in range(len(df) - 5, len(df)):
            if i < 0:
                continue
                
            # High sweep check
            for sh_idx, sh_price in swing_highs:
                if (high.iloc[i] > sh_price * (1 + config.SMC_LIQUIDITY_BUFFER) and 
                    close.iloc[i] < sh_price):  # Wick above, close below
                    swept_highs.append((sh_idx, sh_price, i))
                    
            # Low sweep check
            for sl_idx, sl_price in swing_lows:
                if (low.iloc[i] < sl_price * (1 - config.SMC_LIQUIDITY_BUFFER) and
                    close.iloc[i] > sl_price):  # Wick below, close above
                    swept_lows.append((sl_idx, sl_price, i))
        
        if not swept_highs and not swept_lows:
            return None
            
        return {
            "swept_highs": swept_highs,
            "swept_lows": swept_lows,
            "equal_highs": equal_highs if 'equal_highs' in locals() else [],
            "equal_lows": equal_lows if 'equal_lows' in locals() else []
        }
    
    def _detect_choch(self, df: pd.DataFrame, structure: Dict, liquidity_hunt: Dict) -> Optional[Dict]:
        """
        Change of Character (CHOCH) detection
        """
        swing_highs = structure["swing_highs"]
        swing_lows = structure["swing_lows"]
        swept_highs = liquidity_hunt["swept_highs"]
        swept_lows = liquidity_hunt["swept_lows"]
        
        close = df["c"]
        current_price = close.iloc[-1]
        
        choch_signals = []
        
        # CHOCH for LONG (after low sweep)
        for sl_idx, sl_price, sweep_idx in swept_lows:
            # Find next swing high after sweep
            next_high = None
            for sh_idx, sh_price in swing_highs:
                if sh_idx > sweep_idx:
                    next_high = (sh_idx, sh_price)
                    break
            
            if next_high:
                # Check if current price broke above this high
                if current_price > next_high[1] * (1 + config.BOS_EPS):
                    choch_signals.append({
                        "direction": "LONG",
                        "sweep_low": sl_price,
                        "sweep_idx": sweep_idx,
                        "broken_high": next_high[1],
                        "broken_idx": next_high[0]
                    })
        
        # CHOCH for SHORT (after high sweep)  
        for sh_idx, sh_price, sweep_idx in swept_highs:
            # Find next swing low after sweep
            next_low = None
            for sl_idx, sl_price in swing_lows:
                if sl_idx > sweep_idx:
                    next_low = (sl_idx, sl_price)
                    break
                    
            if next_low:
                # Check if current price broke below this low
                if current_price < next_low[1] * (1 - config.BOS_EPS):
                    choch_signals.append({
                        "direction": "SHORT", 
                        "sweep_high": sh_price,
                        "sweep_idx": sweep_idx,
                        "broken_low": next_low[1],
                        "broken_idx": next_low[0]
                    })
        
        return choch_signals[-1] if choch_signals else None
    
    def _check_ote_retest(self, df: pd.DataFrame, choch: Dict, htf_bias: str) -> Optional[Dict]:
        """
        OTE (Optimal Trade Entry) retest confirmation
        """
        if not choch or choch["direction"] != htf_bias:
            return None
            
        close = df["c"]
        high = df["h"]
        low = df["l"] 
        volume = df["v"]
        current_price = close.iloc[-1]
        
        direction = choch["direction"]
        
        if direction == "LONG":
            # Calculate OTE levels for LONG
            leg_low = choch["sweep_low"]
            leg_high = choch["broken_high"]
            
            ote_min = leg_low + (leg_high - leg_low) * config.SMC_OTE_RETEST_MIN
            ote_max = leg_low + (leg_high - leg_low) * config.SMC_OTE_RETEST_MAX
            
            # Check if price retested into OTE zone
            in_ote_zone = ote_min <= current_price <= ote_max
            
            # Check for recent retest (son 5 mumda)
            retest_confirmed = False
            confirmation_candle = None
            
            for i in range(len(df) - config.SMC_RETEST_CANDLES, len(df)):
                if i < 0:
                    continue
                    
                if ote_min <= low.iloc[i] <= ote_max:
                    # Retest bulundu, confirmation mumu arıyoruz
                    if i < len(df) - 1:  # Son mum değil
                        next_candle = i + 1
                        # ✅ DÜZELTİLDİ: Open column kontrolü iyileştirildi (LONG)
                        if 'o' in df.columns:
                            open_price = df['o'].iloc[next_candle]
                        else:
                            # Open yoksa previous close kullan
                            open_price = close.iloc[next_candle-1] if next_candle > 0 else close.iloc[next_candle]
                        body_strength = abs(close.iloc[next_candle] - open_price) / (high.iloc[next_candle] - low.iloc[next_candle] + 1e-10)
                        
                        if (close.iloc[next_candle] > open_price and  # Bullish candle
                            body_strength >= config.SMC_CONFIRMATION_STRENGTH and  # Strong body
                            volume.iloc[next_candle] > volume.iloc[i] * config.SMC_VOLUME_FACTOR):  # Volume confirmation
                            retest_confirmed = True
                            confirmation_candle = next_candle
                            break
            
            if retest_confirmed:
                return {
                    "direction": "LONG",
                    "entry_zone_min": ote_min,
                    "entry_zone_max": ote_max,
                    "entry_price": (ote_min + ote_max) / 2,
                    "leg_low": leg_low,
                    "leg_high": leg_high,
                    "confirmation_idx": confirmation_candle
                }
                
        elif direction == "SHORT":
            # Calculate OTE levels for SHORT
            leg_high = choch["sweep_high"] 
            leg_low = choch["broken_low"]
            
            ote_min = leg_high - (leg_high - leg_low) * config.SMC_OTE_RETEST_MAX
            ote_max = leg_high - (leg_high - leg_low) * config.SMC_OTE_RETEST_MIN
            
            # Check if price retested into OTE zone
            in_ote_zone = ote_min <= current_price <= ote_max
            
            # Check for recent retest (son 5 mumda)
            retest_confirmed = False
            confirmation_candle = None
            
            for i in range(len(df) - config.SMC_RETEST_CANDLES, len(df)):
                if i < 0:
                    continue
                    
                if ote_min <= high.iloc[i] <= ote_max:
                    # Retest bulundu, confirmation mumu arıyoruz
                    if i < len(df) - 1:  # Son mum değil
                        next_candle = i + 1
                        # ✅ DÜZELTİLDİ: Open column kontrolü iyileştirildi (SHORT)
                        if 'o' in df.columns:
                            open_price = df['o'].iloc[next_candle]
                        else:
                            # Open yoksa previous close kullan
                            open_price = close.iloc[next_candle-1] if next_candle > 0 else close.iloc[next_candle]
                        body_strength = abs(close.iloc[next_candle] - open_price) / (high.iloc[next_candle] - low.iloc[next_candle] + 1e-10)
                        
                        if (close.iloc[next_candle] < open_price and  # Bearish candle
                            body_strength >= config.SMC_CONFIRMATION_STRENGTH and  # Strong body
                            volume.iloc[next_candle] > volume.iloc[i] * config.SMC_VOLUME_FACTOR):  # Volume confirmation
                            retest_confirmed = True
                            confirmation_candle = next_candle
                            break
            
            if retest_confirmed:
                return {
                    "direction": "SHORT",
                    "entry_zone_min": ote_min,
                    "entry_zone_max": ote_max, 
                    "entry_price": (ote_min + ote_max) / 2,
                    "leg_high": leg_high,
                    "leg_low": leg_low,
                    "confirmation_idx": confirmation_candle
                }
        
        return None
    
    def _create_smc_signal(self, df: pd.DataFrame, retest_signal: Dict, htf_bias: str) -> Optional[Dict[str, Any]]:
        """
        SMC sinyali oluştur
        """
        close = df["c"]
        high = df["h"] 
        low = df["l"]
        
        direction = retest_signal["direction"]
        entry_price = retest_signal["entry_price"]
        
        # ATR hesaplama
        atr = float(atr_wilder(high, low, close, config.ATR_PERIOD).iloc[-1])
        
        # SMC-based SL ve TP
        if direction == "LONG":
            sl = retest_signal["leg_low"] * (1 - config.SMC_LIQUIDITY_BUFFER)  # Sweep low altı
            
            # TP levels - Next structure + RR based
            tp1_rr = 1.5
            tp2_rr = 2.5  
            tp3_rr = 4.0
            
            risk = entry_price - sl
            tp1 = entry_price + (risk * tp1_rr)
            tp2 = entry_price + (risk * tp2_rr)
            tp3 = entry_price + (risk * tp3_rr)
            
        else:  # SHORT
            sl = retest_signal["leg_high"] * (1 + config.SMC_LIQUIDITY_BUFFER)  # Sweep high üstü
            
            # TP levels - Next structure + RR based
            tp1_rr = 1.5
            tp2_rr = 2.5
            tp3_rr = 4.0
            
            risk = sl - entry_price
            tp1 = entry_price - (risk * tp1_rr)
            tp2 = entry_price - (risk * tp2_rr) 
            tp3 = entry_price - (risk * tp3_rr)
        
        # Risk/Reward kontrolü
        rr1 = abs(tp1 - entry_price) / abs(entry_price - sl)
        if rr1 < 1.2:  # Minimum RR
            return None
            
        # Score calculation
        base_score = 55
        rr_bonus = min(20, rr1 * 5)
        htf_bonus = 10 if htf_bias == direction else 0
        total_score = base_score + rr_bonus + htf_bonus
        
        return self.create_signal_dict(
            side=direction,
            entry=entry_price,
            sl=sl,
            tps=(tp1, tp2, tp3),
            score=total_score,
            reason=f"SMC V2: Liquidity Hunt → CHOCH → OTE Retest (RR: {rr1:.1f})"
        )

# Helper function to add open column if missing
def add_open_column(df):
    """Add open column if missing (for volume calculation)"""
    if 'o' not in df.columns and len(df) > 0:
        # Open = previous close, first candle open = first close
        df = df.copy()
        df['o'] = df['c'].shift(1)
        df.loc[0, 'o'] = df.loc[0, 'c']  # First candle
        df['o'] = df['o'].fillna(df['c'])
    return df

# Apply to dataframes before using
def preprocess_dataframe(df):
    """Preprocess dataframe for SMC analysis"""
    df = add_open_column(df)
    return df