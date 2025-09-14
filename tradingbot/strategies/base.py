#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Temel strateji sınıfı. Tüm stratejiler bundan türer.
"""

import pandas as pd
from abc import ABC, abstractmethod
from typing import Dict, Optional, Any, Union, List, Tuple

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from .. import config
from ..indicators import atr_wilder

class BaseStrategy(ABC):
    """
    Strateji sınıflarının temel sınıfı.
    """
    
    def __init__(self, symbol: str):
        """
        Strateji için gereken temel değişkenleri başlat.
        
        Args:
            symbol: İşlem yapılacak sembol
        """
        self.symbol = symbol
        self.regime = "BASE"  # Alt sınıflar override edecek
    
    @abstractmethod
    def analyze(self, df15: pd.DataFrame, df1h: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """
        Strateji ile veriyi analiz et ve sinyal üret.
        
        Args:
            df15: Düşük zaman dilimi DataFrame'i
            df1h: Yüksek zaman dilimi DataFrame'i
            
        Returns:
            Sinyal dict'i veya None
        """
    
    def compute_sl_tp(self, side: str, entry: float, atrv: float) -> Tuple[float, Tuple[float, float, float]]:
        """
        ATR tabanlı SL ve TP seviyelerini hesapla.
        
        Args:
            side: İşlem yönü ("LONG" veya "SHORT")
            entry: Giriş fiyatı
            atrv: ATR değeri
            
        Returns:
            Tuple: (SL seviyesi, (TP1, TP2, TP3) seviyeleri)
        """
        risk = config.ATR_STOP_MULT * atrv
        
        if side == "LONG":
            sl  = entry - risk
            tps = (
                entry + config.TPS_R[0] * risk, 
                entry + config.TPS_R[1] * risk, 
                entry + config.TPS_R[2] * risk
            )
        else:
            sl  = entry + risk
            tps = (
                entry - config.TPS_R[0] * risk, 
                entry - config.TPS_R[1] * risk, 
                entry - config.TPS_R[2] * risk
            )
            
        return sl, tps
    
    def create_signal_dict(self, side: str, entry: float, sl: float, tps: Tuple[float, float, float], 
                          score: float, reason: str) -> Dict[str, Any]:
        """
        Sinyal sözlüğü oluştur.
        
        Args:
            side: İşlem yönü ("LONG" veya "SHORT")
            entry: Giriş fiyatı
            sl: Stop Loss fiyatı
            tps: (TP1, TP2, TP3) değerlerini içeren tuple
            score: Sinyal skoru
            reason: Sinyalin açıklaması
            
        Returns:
            Dict: Tam sinyal bilgisini içeren sözlük
        """
        from ..utils import sigmoid
        
        return {
            "symbol": self.symbol,
            "side": side,
            "entry": entry,
            "sl": sl,
            "tps": tps,
            "score": score,
            "p": sigmoid((score - 65) / 7),
            "regime": self.regime,
            "reason": reason
        }