#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Momentum stratejisi.
DC/EMA kırılımları + momentum onayı ile erken tetikleme sistemi.
"""

import pandas as pd
import math
from typing import Dict, Optional, Any

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from .. import config
from ..utils import sigmoid
from .base import BaseStrategy
from ..indicators import (
    atr_wilder, donchian, ema, body_strength, htf_gate_and_bias
)

class MomentumStrategy(BaseStrategy):
    """
    Momentum kırılım stratejisi.
    Donchian ve EMA kırılımlarını erken yakalar.
    """
    
    def __init__(self, symbol: str):
        super().__init__(symbol)
        self.regime = "MO"
    
    def analyze(self, df15: pd.DataFrame, df1h: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """
        Momentum stratejisiyle verileri analiz et ve sinyal üret.

        Args:
            df15: Düşük zaman dilimi DataFrame'i (15 dakika)
            df1h: Yüksek zaman dilimi DataFrame'i (1 saat)
            
        Returns:
            Dict veya None: Sinyal veya sinyal yoksa None
        """
        if not config.EARLY_TRIGGERS_ON:
            return None
            
        o, c, h, l, v = df15["o"], df15["c"], df15["h"], df15["l"], df15["v"]
        atrv = float(atr_wilder(h, l, c, config.ATR_PERIOD).iloc[-1])
        close = float(c.iloc[-1])
        
        bias, _, adx1h, _ = htf_gate_and_bias(df1h)
        
        # EMA'lar
        e9 = ema(c, 9)
        e21 = ema(c, 21)
        
        # Donchian kanalları
        dc_hi, dc_lo = donchian(h, l, config.DONCHIAN_WIN)
        dchi = float(dc_hi.shift(1).iloc[-1])
        dclo = float(dc_lo.shift(1).iloc[-1])
        
        prebreak_dist = config.PREBREAK_ATR_X * atrv
        
        candidates = []
        
        # === LONG MOMENTUM ===
        if bias == "LONG":
            # Donchian kırılımına yakın mı?
            near_dc_break = close >= (dchi - prebreak_dist)
            
            # EMA momentum onayı
            ema_momentum = (e9.iloc[-1] > e21.iloc[-1]) and (c.iloc[-1] > e9.iloc[-1])
            
            if near_dc_break and ema_momentum and self._momentum_confirm_long(df15):
                regime_type = "PREMO" if close < dchi else "MO"
                
                sl, tps = self.compute_sl_tp("LONG", close, atrv)
                
                # Skor hesaplama
                score = 55
                if adx1h >= config.ADX_TREND_MIN:
                    score += config.EARLY_ADX_BONUS
                    
                # Erken tetikleme bonusu
                early_bonus = max(0, (dchi - close) / (prebreak_dist + 1e-9)) * 3
                
                reason = f"Momentum kırılım {'(erken)' if regime_type == 'PREMO' else ''} | ADX1H={adx1h:.1f}"
                
                signal = self.create_signal_dict(
                    side="LONG",
                    entry=close,
                    sl=sl,
                    tps=tps,
                    score=score,
                    reason=reason
                )
                signal["regime"] = regime_type
                signal["_early_bonus"] = early_bonus
                candidates.append(signal)
        
        # === SHORT MOMENTUM ===
        elif bias == "SHORT":
            # Donchian kırılımına yakın mı?
            near_dc_break = close <= (dclo + prebreak_dist)
            
            # EMA momentum onayı
            ema_momentum = (e9.iloc[-1] < e21.iloc[-1]) and (c.iloc[-1] < e9.iloc[-1])
            
            if near_dc_break and ema_momentum and self._momentum_confirm_short(df15):
                regime_type = "PREMO" if close > dclo else "MO"
                
                sl, tps = self.compute_sl_tp("SHORT", close, atrv)
                
                # Skor hesaplama
                score = 55
                if adx1h >= config.ADX_TREND_MIN:
                    score += config.EARLY_ADX_BONUS
                    
                # Erken tetikleme bonusu
                early_bonus = max(0, (close - dclo) / (prebreak_dist + 1e-9)) * 3
                
                reason = f"Momentum kırılım {'(erken)' if regime_type == 'PREMO' else ''} | ADX1H={adx1h:.1f}"
                
                signal = self.create_signal_dict(
                    side="SHORT",
                    entry=close,
                    sl=sl,
                    tps=tps,
                    score=score,
                    reason=reason
                )
                signal["regime"] = regime_type
                signal["_early_bonus"] = early_bonus
                candidates.append(signal)
        
        return candidates[0] if candidates else None
    
    def _momentum_confirm_long(self, df15: pd.DataFrame) -> bool:
        """
        Long yönünde momentum onayı.
        
        Args:
            df15: Düşük zaman dilimi DataFrame'i (15 dakika)
            
        Returns:
            bool: Momentum onayı varsa True
        """
        return self._momentum_check(df15, "LONG")
    
    def _momentum_confirm_short(self, df15: pd.DataFrame) -> bool:
        """
        Short yönünde momentum onayı.
        
        Args:
            df15: Düşük zaman dilimi DataFrame'i (15 dakika)
            
        Returns:
            bool: Momentum onayı varsa True
        """
        return self._momentum_check(df15, "SHORT")
    
    def _momentum_check(self, df15: pd.DataFrame, side: str) -> bool:
        """
        Momentum onay kontrolü.
        
        Args:
            df15: Düşük zaman dilimi DataFrame'i (15 dakika)
            side: İşlem yönü ("LONG" veya "SHORT")
            
        Returns:
            bool: Momentum onayı varsa True
        """
        if config.MOMO_CONFIRM_MODE == "off":
            return True
            
        o, c, h, l, v = df15["o"], df15["c"], df15["h"], df15["l"], df15["v"]
        
        # Body strength kontrolü
        bs = body_strength(o, c, h, l)
        body_ok = bs.iloc[-1] >= config.EARLY_MOMO_BODY_MIN
        
        # Hacim kontrolü
        vol_ma = v.rolling(20).mean()
        vol_ok = v.iloc[-1] > vol_ma.iloc[-1] * config.EARLY_REL_VOL
        
        # Net gövde kontrolü (son 3 mumun net gövdesi)
        net_body = 0.0
        for i in range(-3, 0):
            if side == "LONG":
                net_body += max(0, c.iloc[i] - o.iloc[i])
            else:
                net_body += max(0, o.iloc[i] - c.iloc[i])
        
        total_range = sum(h.iloc[i] - l.iloc[i] for i in range(-3, 0))
        net_ok = (net_body / max(1e-9, total_range)) >= config.MOMO_NET_BODY_TH
        
        if config.MOMO_CONFIRM_MODE == "strict3":
            return body_ok and vol_ok and net_ok
        elif config.MOMO_CONFIRM_MODE == "2of3":
            return sum([body_ok, vol_ok, net_ok]) >= 2
        elif config.MOMO_CONFIRM_MODE == "net_body":
            return net_ok
        else:
            return body_ok or vol_ok