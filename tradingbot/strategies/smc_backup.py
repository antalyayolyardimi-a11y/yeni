#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
SMC (Smart Money Concept) stratejisi.
Likidite süpürme -> CHOCH (Change of Character) + FVG/OTE tabanlı strateji.
"""

import pandas as pd
from typing import Dict, Optional, Any

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from .. import config
from ..utils import sigmoid
from .base import BaseStrategy
from ..indicators import atr_wilder, find_swings, find_fvgs, ema

class SMCStrategy(BaseStrategy):
    """
    Smart Money Concept stratejisi.
    Likidite süpürme, CHOCH (Change of Character) ve FVG/OTE bölgelerini kullanır.
    """
    
    def __init__(self, symbol: str):
        super().__init__(symbol)
        self.regime = "SMC"
    
    def analyze(self, df15: pd.DataFrame, df1h: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """
        SMC stratejisiyle verileri analiz et ve sinyal üret.

        Args:
            df15: Düşük zaman dilimi DataFrame'i
            df1h: Yüksek zaman dilimi DataFrame'i
            
        Returns:
            Dict veya None: Sinyal veya sinyal yoksa None
        """
        bias = htf_bias_only(df1h)

        o, c, h, l, v = df15["o"], df15["c"], df15["h"], df15["l"], df15["v"]
        atrv = float(atr_wilder(h, l, c, config.ATR_PERIOD).iloc[-1])
        
        sh_idx, sl_idx = find_swings(h, l, config.SWING_LEFT, config.SWING_RIGHT)
        
        if len(sh_idx) < 2 and len(sl_idx) < 2:
            return None
            
        last_close = c.iloc[-1]
        
        # ==== LONG ====
        if len(sl_idx) >= 2 and bias == "LONG":
            ref_low = l.iloc[sl_idx[-2]]
            swept_low = (l.iloc[sl_idx[-1]] < ref_low * (1 - config.SWEEP_EPS)) and (c.iloc[sl_idx[-1]] > ref_low * (1 - config.SWEEP_EPS))
            
            minor_sh = next((idx for idx in reversed(sh_idx) if idx >= sl_idx[-1]), sh_idx[-1] if sh_idx else None)
            choch_up = (minor_sh is not None) and (last_close > h.iloc[minor_sh] * (1 + config.BOS_EPS))
            
            if swept_low and choch_up:
                bull_fvg, _ = find_fvgs(h, l, config.FVG_LOOKBACK)
                
                if config.SMC_REQUIRE_FVG and not bull_fvg:
                    return None
                    
                leg_low = l.iloc[sl_idx[-1]]
                leg_high = max(last_close, h.iloc[minor_sh]) if minor_sh is not None else last_close
                leg = abs(leg_high - leg_low)
                
                if leg / (last_close + 1e-12) < 0.004:
                    return None
                    
                ote_a = leg_low + (leg_high - leg_low) * config.OTE_LOW
                ote_b = leg_low + (leg_high - leg_low) * config.OTE_HIGH
                
                entry_a, entry_b = (bull_fvg[0], bull_fvg[1]) if bull_fvg else (ote_a, ote_b)
                entry_mid = (entry_a + entry_b) / 2
                
                sl, tps = self.compute_sl_tp("LONG", entry_mid, atrv)
                
                rr1 = (tps[0] - entry_mid) / max(1e-9, entry_mid - sl)
                score = 45 + min(15, rr1 * 10)
                
                return self.create_signal_dict(
                    side="LONG",
                    entry=entry_mid,
                    sl=sl,
                    tps=tps,
                    score=score,
                    reason="SMC: likidite süpürme → CHOCH (+FVG/OTE)"
                )
        
        # ==== SHORT ====
        if len(sh_idx) >= 2 and bias == "SHORT":
            ref_high = h.iloc[sh_idx[-2]]
            swept_high = (h.iloc[sh_idx[-1]] > ref_high * (1 + config.SWEEP_EPS)) and (c.iloc[sh_idx[-1]] < ref_high * (1 + config.SWEEP_EPS))
            
            minor_sl = next((idx for idx in reversed(sl_idx) if idx >= sh_idx[-1]), sl_idx[-1] if sl_idx else None)
            choch_dn = (minor_sl is not None) and (last_close < l.iloc[minor_sl] * (1 - config.BOS_EPS))
            
            if swept_high and choch_dn:
                _, bear_fvg = find_fvgs(h, l, config.FVG_LOOKBACK)
                
                if config.SMC_REQUIRE_FVG and not bear_fvg:
                    return None
                    
                leg_high = h.iloc[sh_idx[-1]]
                leg_low = min(last_close, l.iloc[minor_sl]) if minor_sl is not None else last_close
                leg = abs(leg_high - leg_low)
                
                if leg / (last_close + 1e-12) < 0.004:
                    return None
                    
                ote_a = leg_high - (leg_high - leg_low) * config.OTE_LOW
                ote_b = leg_high - (leg_high - leg_low) * config.OTE_HIGH
                
                entry_a, entry_b = (bear_fvg[0], bear_fvg[1]) if bear_fvg else (ote_a, ote_b)
                entry_mid = (entry_a + entry_b) / 2
                
                sl, tps = self.compute_sl_tp("SHORT", entry_mid, atrv)
                
                rr1 = (entry_mid - tps[0]) / max(1e-9, sl - entry_mid)
                score = 45 + min(15, rr1 * 10)
                
                return self.create_signal_dict(
                    side="SHORT",
                    entry=entry_mid,
                    sl=sl,
                    tps=tps,
                    score=score,
                    reason="SMC: likidite süpürme → CHOCH (+FVG/OTE)"
                )
        
        return None

def htf_bias_only(df1h: pd.DataFrame) -> str:
    """
    1 saatlik bias tespiti.
    
    Args:
        df1h: Yüksek zaman dilimi DataFrame'i (1 saat)
        
    Returns:
        str: LONG, SHORT veya NEUTRAL
    """
    c = df1h["c"]
    
    # Simple bias based on last few candles
    if len(c) < 5:
        return "NEUTRAL"
        
    # Check if price is trending up or down over last 5 candles
    recent_trend = (c.iloc[-1] - c.iloc[-5]) / c.iloc[-5]
    
    if recent_trend > 0.01:  # 1% up trend
        return "LONG"
    elif recent_trend < -0.01:  # 1% down trend
        return "SHORT"
    else:
        return "NEUTRAL"