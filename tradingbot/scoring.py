#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Sinyal skorlama ve değerlendirme sistemi.
"""

import math
import pandas as pd
from typing import Dict, Any, Tuple, Optional, List

from . import config
from .utils import log, sigmoid
from .indicators import (
    atr_wilder, bollinger, adx, ema, body_strength, htf_gate_and_bias
)

# Geçmiş sembol penaltileri
_recent_penalty = {}

def mark_symbol_outcome(symbol: str, res: str):
    """
    Sembol sonucunu işaretle ve gerekirse penaltı uygula.
    
    Args:
        symbol: İşlem sembolü
        res: Sonuç ("TP" veya "SL")
    """
    if res == "SL":
        _recent_penalty[symbol] = config.PENALTY_DECAY

def use_recent_penalty(symbol: str) -> float:
    """
    Sembol için penaltı değerini döndür ve azalt.
    
    Args:
        symbol: İşlem sembolü
        
    Returns:
        float: Penaltı değeri (0-1 arası)
    """
    p = _recent_penalty.get(symbol, 0)
    if p > 0:
        _recent_penalty[symbol] = p - 1
        return 1.0
    return 0.0

def normalize_adx(adx_val: float) -> float:
    """
    ADX değerini normalize et.
    
    Args:
        adx_val: Ham ADX değeri
        
    Returns:
        float: Normalize edilmiş değer (0-1 arası)
    """
    return max(0.0, min(1.0, (adx_val - config.ADX_TREND_MIN) / 20.0))

def normalize_rr(rr1: float) -> float:
    """
    Risk-reward oranını normalize et.
    
    Args:
        rr1: Risk-reward oranı
        
    Returns:
        float: Normalize edilmiş değer (0-1 arası)
    """
    return max(0.0, min(1.0, (rr1 - 0.8) / 1.6))

def bw_advantage(bw: float) -> float:
    """
    Bollinger bant genişliğinden avantaj skoru hesapla.
    
    Args:
        bw: Bollinger bant genişliği
        
    Returns:
        float: Avantaj skoru (0-1 arası)
    """
    if math.isnan(bw):
        return 0.0
    return max(0.0, 1.0 - (bw / max(1e-6, config.BWIDTH_RANGE)))

def atr_in_sweet(atr_pct: float) -> float:
    """
    ATR yüzdesinin "tatlı bölge"de olup olmadığını kontrol et.
    
    Args:
        atr_pct: ATR yüzdesi
        
    Returns:
        float: 1.0 eğer tatlı bölgedeyse, aksi halde 0.0
    """
    return 1.0 if config.FBB_ATR_MIN <= atr_pct <= config.FBB_ATR_MAX else 0.0

def score_to_prob(score: float) -> float:
    """
    Skor değerini olasılığa dönüştür.
    
    Args:
        score: Ham skor değeri
        
    Returns:
        float: Olasılık değeri (0-1 arası)
    """
    return 1.0 / (1.0 + math.exp(-(config.PROB_CALIB_A * score + config.PROB_CALIB_B)))

def extract_features_for_scoring(symbol: str, df15: pd.DataFrame, df1h: pd.DataFrame, 
                                 candidate: Dict[str, Any], extra_ctx: Optional[Dict[str, Any]] = None) -> Tuple[Dict[str, float], Dict[str, Any]]:
    """
    Sinyal skorlaması için özellik çıkarımı.
    
    Args:
        symbol: İşlem sembolü
        df15: Düşük zaman dilimi DataFrame'i (15 dakika)
        df1h: Yüksek zaman dilimi DataFrame'i (1 saat)
        candidate: Aday sinyal
        extra_ctx: Ek bağlam bilgisi
        
    Returns:
        Tuple: (Özellikler sözlüğü, Açıklama sözlüğü)
    """
    c, h, l, o = df15["c"], df15["h"], df15["l"], df15["o"]
    close = float(c.iloc[-1])
    adxv = float(adx(h, l, c, 14).iloc[-1])
    
    entry = float(candidate["entry"])
    tp1 = float(candidate["tps"][0])
    sl = float(candidate["sl"])
    
    rr1 = (tp1 - entry) / max(1e-9, entry - sl) if candidate["side"] == "LONG" else (entry - tp1) / max(1e-9, sl - entry)
    
    _, _, _, bwidth, _ = bollinger(c, config.BB_PERIOD, config.BB_K)
    bw_last = float(bwidth.iloc[-1]) if pd.notna(bwidth.iloc[-1]) else float("nan")
    
    b1h, _, _, _ = htf_gate_and_bias(df1h)
    htf_align = (b1h == candidate["side"])
    
    # Momentum LTF doğrulaması
    from .strategies.trend_range import TrendRangeStrategy
    ltf_is_ok = TrendRangeStrategy(symbol).momentum_ok(df15, candidate["side"])
    
    has_retest_or_fvg = ("Retest" in candidate.get("reason", "")) or (candidate.get("regime") == "SMC")
    
    atrv = float(atr_wilder(h, l, c, config.ATR_PERIOD).iloc[-1])
    atr_pct = atrv / (close + 1e-12)
    
    vol_pct = (extra_ctx or {}).get("vol_pct", 0.5)
    
    feats = {
        "htf_align": 1.0 if htf_align else 0.0,
        "adx_norm": normalize_adx(adxv),
        "ltf_momo": 1.0 if ltf_is_ok else 0.0,
        "rr_norm": normalize_rr(rr1),      # ağırlığı 0 olduğundan puana etkisi yok
        "bw_adv": bw_advantage(bw_last),
        "retest_or_fvg": 1.0 if has_retest_or_fvg else 0.0,
        "atr_sweet": atr_in_sweet(atr_pct),
        "vol_pct": max(0.0, min(1.0, vol_pct)),
        "recent_penalty": use_recent_penalty(symbol),
    }
    
    explain = {
        "rr1": rr1, 
        "adx": adxv, 
        "bw": bw_last, 
        "atr_pct": atr_pct, 
        "b1h": b1h
    }
    
    return feats, explain

def composite_score_from_feats(feats: Dict[str, float]) -> float:
    """
    Özelliklerden bileşik skor hesapla.
    
    Args:
        feats: Özellikler sözlüğü
        
    Returns:
        float: Bileşik skor
    """
    s = config.SCORING_BASE
    for k, w in config.SCORING_WEIGHTS.items():
        s += w * float(feats.get(k, 0.0))
    return max(0.0, s)

def apply_scoring(symbol: str, df15: pd.DataFrame, df1h: pd.DataFrame, 
                 candidate: Optional[Dict[str, Any]], extra_ctx: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """
    Adaya skorlama uygula ve sonucu döndür.
    
    Args:
        symbol: İşlem sembolü
        df15: Düşük zaman dilimi DataFrame'i
        df1h: Yüksek zaman dilimi DataFrame'i
        candidate: Aday sinyal
        extra_ctx: Ek bağlam bilgisi
        
    Returns:
        Dict: Skorlanmış sinyal
    """
    if candidate is None:
        return None
        
    cand = candidate.copy()
    feats, explain = extract_features_for_scoring(symbol, df15, df1h, cand, extra_ctx or {})
    score = composite_score_from_feats(feats)
    
    # --- TA tabanlı sert kurallar ---
    htf_align = float(feats.get("htf_align", 0.0)) >= 1.0
    adx_norm = float(feats.get("adx_norm", 0.0))
    bw_adv = float(feats.get("bw_adv", 0.0))
    
    if not htf_align:
        score -= 10.0  # 1H bias ≠ sinyal yönü
    
    # Trend çok zayıfsa eleriz.
    if adx_norm < 0.10:
        score = 0.0
    
    if cand.get("regime") == "RANGE" and bw_adv < 0.20:
        score -= 6.0
    
    # erken tetikleyici geldiyse ufak bonus
    if cand.get("regime") == "PREMO":
        score += float(cand.get("_early_bonus", 0.0))
    
    score = max(0.0, score)
    
    prob = score_to_prob(score)
    cand["score"] = score
    cand["p"] = prob
    cand["_feats"] = feats
    cand["_explain"] = explain
    
    return cand

def pick_best_candidate(symbol: str, df15: pd.DataFrame, df1h: pd.DataFrame, 
                      vol_pct_cache: Optional[Dict[str, float]] = None) -> Optional[Dict[str, Any]]:
    """
    En iyi sinyali seç ve skorla.
    
    Args:
        symbol: İşlem sembolü
        df15: Düşük zaman dilimi DataFrame'i (15 dakika)
        df1h: Yüksek zaman dilimi DataFrame'i (1 saat)
        vol_pct_cache: Hacim yüzdelik önbelleği
        
    Returns:
        En iyi aday sinyal veya None
    """
    from .strategies.smc import SMCStrategy
    from .strategies.trend_range import TrendRangeStrategy
    from .strategies.momentum import MomentumStrategy
    
    best = None
    
    # legacy (SMC + TREND/RANGE)
    smc = tr = None
    
    try:
        smc = SMCStrategy(symbol).analyze(df15, df1h)
    except Exception as e:
        pass
        
    try:
        tr = TrendRangeStrategy(symbol).analyze(df15, df1h)
    except Exception as e:
        pass
        
    for c in [smc, tr]:
        if c:
            c = apply_scoring(symbol, df15, df1h, c, {"vol_pct": vol_pct_cache.get(symbol, 0.5) if vol_pct_cache else 0.5})
            if c and ((best is None) or (c["score"] > best["score"])):
                best = c
    
    # momentum-breakout (erken fırsat)
    mo = None
    try:
        mo = MomentumStrategy(symbol).analyze(df15, df1h)
    except Exception as e:
        pass
        
    if mo:
        mo = apply_scoring(symbol, df15, df1h, mo, {"vol_pct": vol_pct_cache.get(symbol, 0.5) if vol_pct_cache else 0.5})
        if mo:
            mo["score"] = max(mo["score"], config.BASE_MIN_SCORE - 4)
            if (best is None) or (mo["score"] > best["score"]):
                best = mo
            
    return best