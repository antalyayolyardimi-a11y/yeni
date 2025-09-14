#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
AI ve adaptif öğrenme sistemi.
Mini-AI (online logistic regression) ve auto-tuner içerir.
"""

import time
import math
from typing import Dict, List, Any, Optional, Union, Tuple

from . import config
from .utils import log, clip_value

# ================== MINI AI (ONLINE LOGIT) ==================
# AI ağırlıkları ve state
_ai_w = {k: 0.0 for k in config.SCORING_WEIGHTS.keys()}
_ai_b = config.AI_INIT_BIAS
_ai_seen = 0

def sigm(x: float) -> float:
    """
    Sigmoid fonksiyonu.
    
    Args:
        x: Giriş değeri
        
    Returns:
        float: Sigmoid çıktısı (0-1 arası)
    """
    return 1.0 / (1.0 + math.exp(-x))

def ai_predict_proba(feats: Dict[str, float]) -> float:
    """
    AI modeli ile olasılık tahmini yap.
    
    Args:
        feats: Özellik vektörü
        
    Returns:
        float: Olasılık tahmini (0-1 arası)
    """
    z = _ai_b
    for k, v in feats.items():
        z += _ai_w.get(k, 0.0) * float(v)
    return sigm(z)

def ai_update_online(feats: Dict[str, float], y: int):
    """
    AI modelini çevrimiçi olarak güncelle.
    
    Args:
        feats: Özellik vektörü
        y: Gerçek sonuç (1=kazanç, 0=kayıp)
    """
    global _ai_b, _ai_w, _ai_seen
    
    p = ai_predict_proba(feats)
    err = (p - y)
    
    _ai_b -= config.AI_LR * (err + config.AI_L2 * _ai_b)
    
    for k, v in feats.items():
        g = err * float(v) + config.AI_L2 * _ai_w.get(k, 0.0)
        _ai_w[k] = _ai_w.get(k, 0.0) - config.AI_LR * g
        
    _ai_seen += 1

def enrich_with_ai(cand: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sinyal adayını AI tahminiyle zenginleştir.
    
    Args:
        cand: Sinyal adayı
        
    Returns:
        Dict: Zenginleştirilmiş sinyal
    """
    if not config.AI_ENABLED:
        cand["p_final"] = cand.get("p", 0.5)
        return cand
        
    feats = cand.get("_feats", {})
    ai_p = ai_predict_proba(feats)
    
    cand["ai_p"] = ai_p
    cand["p_final"] = (cand.get("p", 0.5) + ai_p) / 2.0
    
    return cand

def get_ai_stats() -> Dict[str, Any]:
    """
    AI durumu hakkında bilgi ver.
    
    Returns:
        Dict: AI istatistikleri
    """
    return {
        "seen": _ai_seen,
        "bias": _ai_b,
        "weights": dict(_ai_w)
    }

def reset_ai():
    """
    AI modelini sıfırla.
    """
    global _ai_w, _ai_b, _ai_seen
    _ai_w = {k: 0.0 for k in config.SCORING_WEIGHTS.keys()}
    _ai_b = config.AI_INIT_BIAS
    _ai_seen = 0

# ================== AUTO-TUNER ==================
def _recent_wr(history: List[Dict[str, Any]], n: int) -> Optional[float]:
    """
    Son n sinyalin başarı oranını hesapla.
    
    Args:
        history: Sinyal geçmişi
        n: Bakılacak sinyal sayısı
        
    Returns:
        float veya None: Başarı oranı veya yetersiz veri varsa None
    """
    arr = [1 if s.get("resolved") and s.get("result") == "TP" else 
           (0 if s.get("resolved") else None) for s in history[-n:]]
           
    arr = [x for x in arr if x is not None]
    
    if not arr:
        return None
        
    return sum(arr) / len(arr)

def _streak(history: List[Dict[str, Any]], what: str = "SL") -> int:
    """
    Belirli bir sonucun ard arda tekrar sayısını hesapla.
    
    Args:
        history: Sinyal geçmişi
        what: Aranacak sonuç ("SL" veya "TP")
        
    Returns:
        int: Ard arda tekrar sayısı
    """
    k = 0
    for s in reversed(history):
        if not s.get("resolved"):
            break
        if s.get("result") == what:
            k += 1
        else:
            break
    return k

def auto_tune_now(state: Dict[str, Any], signals_history: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Auto-tuner çalıştır ve parametreleri güncelle.
    
    Args:
        state: Durum değişkenleri
        signals_history: Sinyal geçmişi
        
    Returns:
        Dict: Güncellenmiş durum
    """
    if not config.AUTO_TUNER_ON or len(signals_history) < config.WIN_MIN_SAMPLES:
        return state
        
    now = time.time()
    if now - state.get("last_tune_ts", 0) < config.TUNE_COOLDOWN_SEC:
        return state
    
    wr = _recent_wr(signals_history, config.TUNE_WINDOW)
    if wr is None:
        return state
        
    sl_streak = _streak(signals_history, "SL")
    changed = False
    
    # Durum değişkenlerini yerel kopyala
    base_min_score = state.get("BASE_MIN_SCORE", config.BASE_MIN_SCORE)
    adx_trend_min = state.get("ADX_TREND_MIN", config.ADX_TREND_MIN)
    bwidth_range = state.get("BWIDTH_RANGE", config.BWIDTH_RANGE)
    vol_mult_req_global = state.get("VOL_MULT_REQ_GLOBAL", config.VOL_MULT_REQ_GLOBAL)
    
    if sl_streak >= 3:
        base_min_score = clip_value(base_min_score + 2, *config.BOUNDS["BASE_MIN_SCORE"])
        adx_trend_min = clip_value(adx_trend_min + 1, *config.BOUNDS["ADX_TREND_MIN"])
        vol_mult_req_global = clip_value(vol_mult_req_global + 0.05, *config.BOUNDS["VOL_MULT_REQ"])
        changed = True
    else:
        delta = wr - config.WR_TARGET
        step = 2 if abs(delta) > 0.06 else 1
        
        if delta < -0.01:
            base_min_score = clip_value(base_min_score - step, *config.BOUNDS["BASE_MIN_SCORE"])
            adx_trend_min = clip_value(adx_trend_min - 1, *config.BOUNDS["ADX_TREND_MIN"])
            bwidth_range = clip_value(bwidth_range + 0.003, *config.BOUNDS["BWIDTH_RANGE"])
            vol_mult_req_global = clip_value(vol_mult_req_global - 0.05, *config.BOUNDS["VOL_MULT_REQ"])
            changed = True
        elif delta > 0.04:
            base_min_score = clip_value(base_min_score + 1, *config.BOUNDS["BASE_MIN_SCORE"])
            vol_mult_req_global = clip_value(vol_mult_req_global + 0.03, *config.BOUNDS["VOL_MULT_REQ"])
            changed = True
    
    if changed:
        state["BASE_MIN_SCORE"] = base_min_score
        state["ADX_TREND_MIN"] = adx_trend_min
        state["BWIDTH_RANGE"] = bwidth_range
        state["VOL_MULT_REQ_GLOBAL"] = vol_mult_req_global
        state["dyn_MIN_SCORE"] = base_min_score
        state["last_tune_ts"] = now
        
        log(f"🛠️ AutoTune | WR={wr:.2f} | BASE_MIN_SCORE={base_min_score} ADX_MIN={adx_trend_min} BW={bwidth_range:.3f} VOLx={vol_mult_req_global:.2f}")
    
    return state