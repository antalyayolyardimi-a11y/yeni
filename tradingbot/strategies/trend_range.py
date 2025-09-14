#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Trend/Range stratejisi.
Trend modu: Donchian kırılımı + retest/momentum
Range modu: BB bantları içinde sıçrama/dönüş
"""

import pandas as pd
import math
from typing import Dict, Optional, Any, List

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from .. import config
from ..utils import sigmoid
from .base import BaseStrategy
from ..indicators import (
    atr_wilder, bollinger, donchian, adx, 
    body_strength, rsi, ema, htf_gate_and_bias
)

class TrendRangeStrategy(BaseStrategy):
    """
    Trend/Range stratejisi.
    Piyasa durumuna göre farklı davranış gösteren akıllı strateji.
    """
    
    def __init__(self, symbol: str):
        super().__init__(symbol)
        # Regime "TREND" veya "RANGE" olarak dinamik belirlenir
    
    def analyze(self, df15: pd.DataFrame, df1h: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """
        Trend/Range stratejisiyle verileri analiz et ve sinyal üret.

        Args:
            df15: Düşük zaman dilimi DataFrame'i (15 dakika)
            df1h: Yüksek zaman dilimi DataFrame'i (1 saat)
            
        Returns:
            Dict veya None: Sinyal veya sinyal yoksa None
        """
        o, c, h, l, v = df15["o"], df15["c"], df15["h"], df15["l"], df15["v"]
        atr_val = atr_wilder(h, l, c, config.ATR_PERIOD)
        ma, bb_u, bb_l, bwidth, _ = bollinger(c, config.BB_PERIOD, config.BB_K)
        dc_hi, dc_lo = donchian(h, l, config.DONCHIAN_WIN)
        bs = body_strength(o, c, h, l)
        
        close = float(c.iloc[-1])
        prev_close = float(c.iloc[-2])
        atrv = float(atr_val.iloc[-1])
        bw = float(bwidth.iloc[-1])
        dchi = float(dc_hi.shift(1).iloc[-1])
        dclo = float(dc_lo.shift(1).iloc[-1])
        
        bias, disp_ok, adx1h, trend_ok = htf_gate_and_bias(df1h)
        candidates = []
        
        # --- TREND BREAK + (RETEST or MOMENTUM) ---
        if trend_ok and disp_ok:
            if bias == "LONG":
                long_break = (prev_close > dchi * (1 + config.BREAK_BUFFER)) and (close >= prev_close)
                
                if long_break and (self.retest_ok_long(dchi, df15, atrv) or self.momentum_ok(df15, "LONG")):
                    sl, tps = self.compute_sl_tp("LONG", close, atrv)
                    rr1 = (tps[0] - close) / max(1e-9, close - sl)
                    
                    score = 40 + min(20, (adx1h - config.ADX_TREND_MIN) * 1.2) + (bs.iloc[-1] * 10)
                    if rr1 < 1.0:
                        score -= 4
                        
                    reason = f"Trend kırılımı + {'Retest' if self.retest_ok_long(dchi, df15, atrv) else 'Momentum'} | 1H ADX={adx1h:.1f}, BW={bw:.4f}"
                    
                    signal = self.create_signal_dict(
                        side="LONG",
                        entry=close,
                        sl=sl,
                        tps=tps,
                        score=score,
                        reason=reason
                    )
                    signal["regime"] = "TREND"
                    candidates.append(signal)
                    
            elif bias == "SHORT":
                short_break = (prev_close < dclo * (1 - config.BREAK_BUFFER)) and (close <= prev_close)
                
                if short_break and (self.retest_ok_short(dclo, df15, atrv) or self.momentum_ok(df15, "SHORT")):
                    sl, tps = self.compute_sl_tp("SHORT", close, atrv)
                    rr1 = (close - tps[0]) / max(1e-9, sl - close)
                    
                    score = 40 + min(20, (adx1h - config.ADX_TREND_MIN) * 1.2) + (bs.iloc[-1] * 10)
                    if rr1 < 1.0:
                        score -= 4
                        
                    reason = f"Trend kırılımı + {'Retest' if self.retest_ok_short(dclo, df15, atrv) else 'Momentum'} | 1H ADX={adx1h:.1f}, BW={bw:.4f}"
                    
                    signal = self.create_signal_dict(
                        side="SHORT",
                        entry=close,
                        sl=sl,
                        tps=tps,
                        score=score,
                        reason=reason
                    )
                    signal["regime"] = "TREND"
                    candidates.append(signal)
        
        # --- RANGE MEAN-REVERT (SMART BOUNCE) ---
        if (not trend_ok) and (not math.isnan(bw)) and bw <= config.BWIDTH_RANGE:
            rsi14 = float(rsi(c, 14).iloc[-1])
            ma_v, bbu_v, bbl_v = float(ma.iloc[-1]), float(bb_u.iloc[-1]), float(bb_l.iloc[-1])
            
            near_lower = close <= bbl_v * (1 + 0.0010)
            near_upper = close >= bbu_v * (1 - 0.0010)
            
            re_enter_long = (float(c.iloc[-2]) < bbl_v) and (float(c.iloc[-1]) > bbl_v)
            re_enter_short = (float(c.iloc[-2]) > bbu_v) and (float(c.iloc[-1]) < bbu_v)
            
            bs_last = float(body_strength(o, c, h, l).iloc[-1])
            
            VOL_MULT_REQ = config.VOL_MULT_REQ_GLOBAL
            vol_ok = float(v.iloc[-1]) > float(v.rolling(20).mean().iloc[-1]) * VOL_MULT_REQ
            RSI_LONG_TH = 36
            RSI_SHORT_TH = 64
            bs_last_req = 0.62
            
            if (near_lower and rsi14 < RSI_LONG_TH and re_enter_long and 
                bs_last >= bs_last_req and vol_ok and bias != "SHORT"):
                
                sl, tps = self.compute_sl_tp("LONG", close, atrv)
                score = 30 + (max(0, 38 - rsi14)) + (1 - bw / max(1e-12, config.BWIDTH_RANGE)) * 10
                
                reason = f"Bant içi bounce (false breakout→re-enter + güçlü mum + hacim) | RSI={rsi14:.1f}, BW={bw:.4f}"
                
                signal = self.create_signal_dict(
                    side="LONG",
                    entry=close,
                    sl=sl,
                    tps=tps,
                    score=score,
                    reason=reason
                )
                signal["regime"] = "RANGE"
                candidates.append(signal)
                
            if (near_upper and rsi14 > RSI_SHORT_TH and re_enter_short and 
                bs_last >= bs_last_req and vol_ok and bias != "LONG"):
                
                sl, tps = self.compute_sl_tp("SHORT", close, atrv)
                score = 30 + (max(0, rsi14 - 62)) + (1 - bw / max(1e-12, config.BWIDTH_RANGE)) * 10
                
                reason = f"Bant içi bounce (false breakout→re-enter + güçlü mum + hacim) | RSI={rsi14:.1f}, BW={bw:.4f}"
                
                signal = self.create_signal_dict(
                    side="SHORT",
                    entry=close,
                    sl=sl,
                    tps=tps,
                    score=score,
                    reason=reason
                )
                signal["regime"] = "RANGE"
                candidates.append(signal)
                
        if not candidates:
            return None
            
        # Ortak ATR% filtresi: aşırı oynak günleri ele
        atrv_last = float(atr_wilder(df15["h"], df15["l"], df15["c"], config.ATR_PERIOD).iloc[-1])
        close_last = float(df15["c"].iloc[-1])
        atr_pct = atrv_last / (close_last + 1e-12)
        
        if atr_pct > 0.035:
            return None
            
        return sorted(candidates, key=lambda x: x["score"], reverse=True)[0]
    
    def retest_ok_long(self, dc_break_level: float, df15: pd.DataFrame, atrv: float) -> bool:
        """
        Long için retest kontrolü.
        
        Args:
            dc_break_level: Donchian kırılım seviyesi
            df15: Düşük zaman dilimi DataFrame'i (15 dakika)
            atrv: ATR değeri
            
        Returns:
            bool: Retest onayı varsa True
        """
        low = float(df15["l"].iloc[-1])
        close = float(df15["c"].iloc[-1])
        open_ = float(df15["o"].iloc[-1])
        
        tol = config.RETEST_TOL_ATR * atrv
        touched = (low <= dc_break_level + tol)
        
        body_ratio = (close - open_) / max(1e-12, df15["h"].iloc[-1] - df15["l"].iloc[-1])
        strong = (close > open_) and (body_ratio > 0.55)
        
        return touched and strong
    
    def retest_ok_short(self, dc_break_level: float, df15: pd.DataFrame, atrv: float) -> bool:
        """
        Short için retest kontrolü.
        
        Args:
            dc_break_level: Donchian kırılım seviyesi
            df_ltf: Düşük zaman dilimi DataFrame'i (15 dakika)
            atrv: ATR değeri
            
        Returns:
            bool: Retest onayı varsa True
        """
        high = float(df15["h"].iloc[-1])
        close = float(df15["c"].iloc[-1])
        open_ = float(df15["o"].iloc[-1])
        
        tol = config.RETEST_TOL_ATR * atrv
        touched = (high >= dc_break_level - tol)
        
        body_ratio = (open_ - close) / max(1e-12, df15["h"].iloc[-1] - df15["l"].iloc[-1])
        strong = (close < open_) and (body_ratio > 0.55)
        
        return touched and strong
    
    def momentum_ok(self, df15: pd.DataFrame, side: str) -> bool:
        """
        Momentum onayı kontrolü.
        
        Args:
            df_ltf: Düşük zaman dilimi DataFrame'i (15 dakika)
            side: İşlem yönü ("LONG" veya "SHORT")
            
        Returns:
            bool: Momentum onayı varsa True
        """
        c, o = df15["c"], df15["o"]
        e9, e21 = ema(c, 9), ema(c, 21)
        bs = body_strength(o, c, df15["h"], df15["l"]).iloc[-1]
        
        if side == "LONG":
            return (e9.iloc[-1] > e21.iloc[-1]) and (float(c.iloc[-1]) >= float(c.iloc[-2])) and (bs >= 0.60)
        else:
            return (e9.iloc[-1] < e21.iloc[-1]) and (float(c.iloc[-1]) <= float(c.iloc[-2])) and (bs >= 0.60)