#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Sinyal doğrulama sistemi.
5 dakikalık grafikte 3 mum analizi yaparak sinyal doğrulaması.
"""

import time
import pandas as pd
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timezone

from . import config
from .utils import log
from .exchange import Exchange
from .indicators import ema, rsi, body_strength

@dataclass
class PendingSignal:
    """Bekleyen sinyal verisi."""
    symbol: str
    side: str
    entry: float
    sl: float
    tps: tuple
    score: float
    reason: str
    regime: str
    created_at: float
    bar_count: int = 0
    confirmed: bool = False
    cancelled: bool = False
    validation_data: Optional[Dict] = None

class SignalValidator:
    """
    Sinyal doğrulama sistemi.
    5 dakikalık grafikte 3 mum analizi yaparak sinyal onaylar veya iptal eder.
    """
    
    def __init__(self, exchange: Exchange):
        self.exchange = exchange
        self.pending_signals: Dict[str, PendingSignal] = {}  # symbol -> PendingSignal
        self.confirmed_signals: List[Dict] = []
        
    def add_signal_to_pool(self, signal: Dict[str, Any]) -> str:
        """
        Sinyali doğrulama havuzuna ekle.
        
        Args:
            signal: Sinyal verisi
            
        Returns:
            str: Sinyal ID'si
        """
        symbol = signal["symbol"]
        
        # Eğer bu sembol için zaten bekleyen sinyal varsa, eskisini iptal et
        if symbol in self.pending_signals:
            self.pending_signals[symbol].cancelled = True
            log(f"⚠️ {symbol} için eski bekleyen sinyal iptal edildi")
        
        # Yeni bekleyen sinyal oluştur
        pending = PendingSignal(
            symbol=symbol,
            side=signal["side"],
            entry=signal["entry"],
            sl=signal["sl"],
            tps=signal["tps"],
            score=signal["score"],
            reason=signal["reason"],
            regime=signal["regime"],
            created_at=time.time(),
            validation_data={}
        )
        
        self.pending_signals[symbol] = pending
        
        log(f"🔄 {symbol} {signal['side']} sinyali doğrulama havuzuna eklendi (15 dakika bekleyecek)")
        
        return f"{symbol}_{int(pending.created_at)}"
    
    def validate_pending_signals(self) -> List[Dict]:
        """
        Bekleyen sinyalleri doğrula ve onaylanmış olanları döndür.
        
        Returns:
            List[Dict]: Onaylanmış sinyaller
        """
        confirmed_this_round = []
        symbols_to_remove = []
        
        for symbol, pending in self.pending_signals.items():
            if pending.cancelled or pending.confirmed:
                symbols_to_remove.append(symbol)
                continue
                
            # Timeout kontrolü (20 dakika)
            if time.time() - pending.created_at > 1200:  # 20 dakika
                pending.cancelled = True
                symbols_to_remove.append(symbol)
                log(f"⏰ {symbol} sinyali zaman aşımı nedeniyle iptal edildi")
                continue
            
            # 5 dakikalık veri al ve analiz et
            validation_result = self._analyze_5min_confirmation(pending)
            
            if validation_result["action"] == "confirm":
                pending.confirmed = True
                
                # Onaylanmış sinyal oluştur
                confirmed_signal = {
                    "symbol": pending.symbol,
                    "side": pending.side,
                    "entry": pending.entry,
                    "sl": pending.sl,
                    "tps": pending.tps,
                    "score": pending.score + validation_result.get("bonus_score", 0),
                    "reason": f"{pending.reason} + 5m doğrulama",
                    "regime": pending.regime,
                    "validation": validation_result["details"]
                }
                
                confirmed_this_round.append(confirmed_signal)
                symbols_to_remove.append(symbol)
                
                log(f"✅ {symbol} {pending.side} sinyali 5m analizle ONAYLANDI!")
                
            elif validation_result["action"] == "cancel":
                pending.cancelled = True
                symbols_to_remove.append(symbol)
                log(f"❌ {symbol} sinyali 5m analizde başarısız - İPTAL EDİLDİ")
                
            # Devam eden analiz için log
            elif validation_result["action"] == "continue":
                log(f"🔍 {symbol} 5m analiz devam ediyor ({pending.bar_count}/3 mum)")
        
        # Tamamlanmış sinyalleri temizle
        for symbol in symbols_to_remove:
            if symbol in self.pending_signals:
                del self.pending_signals[symbol]
        
        return confirmed_this_round
    
    def _analyze_5min_confirmation(self, pending: PendingSignal) -> Dict[str, Any]:
        """
        5 dakikalık grafikte 3 mum analizi yaparak doğrulama.
        
        Args:
            pending: Bekleyen sinyal
            
        Returns:
            Dict: Analiz sonucu {"action": "confirm"/"cancel"/"continue", "details": {}, "bonus_score": 0}
        """
        symbol = pending.symbol
        
        # 5 dakikalık veriyi al
        df5m = self.exchange.get_ohlcv(symbol, "5min", 100)
        
        if df5m is None or len(df5m) < 10:
            return {"action": "continue", "details": {"error": "Veri alınamadı"}}
        
        # Sinyal oluşturulduğu zamandaki bar'ı bul
        signal_time = pd.to_datetime(pending.created_at, unit="s", utc=True)
        
        # Sinyal zamanından sonraki barları al
        future_bars = df5m[df5m["time"] > signal_time].copy()
        
        if len(future_bars) < 3:
            return {"action": "continue", "details": {"bars_available": len(future_bars)}}
        
        # Son 3 mumu analiz et
        analysis_bars = future_bars.tail(3)
        
        return self._perform_3bar_analysis(pending, analysis_bars)
    
    def _perform_3bar_analysis(self, pending: PendingSignal, bars: pd.DataFrame) -> Dict[str, Any]:
        """
        3 mum analizi gerçekleştir.
        
        Args:
            pending: Bekleyen sinyal
            bars: Analiz edilecek 3 mum
            
        Returns:
            Dict: Analiz sonucu
        """
        o, c, h, l, v = bars["o"], bars["c"], bars["h"], bars["l"], bars["v"]
        
        # Temel veriler
        closes = c.values
        opens = o.values
        highs = h.values
        lows = l.values
        volumes = v.values
        
        # Body strength hesapla
        body_strengths = []
        for i in range(len(bars)):
            body = abs(closes[i] - opens[i])
            total_range = highs[i] - lows[i]
            if total_range > 0:
                body_strengths.append(body / total_range)
            else:
                body_strengths.append(0)
        
        # Momentum analizi
        price_momentum = closes[-1] - closes[0]  # 3 mumun net fiyat değişimi
        avg_body_strength = sum(body_strengths) / len(body_strengths)
        avg_volume = sum(volumes) / len(volumes)
        
        # RSI ve EMA (daha geniş veri için)
        full_closes = pd.concat([bars["c"].iloc[:-3], bars["c"]] if len(bars) > 3 else [bars["c"]])
        rsi_val = float(rsi(full_closes, 14).iloc[-1]) if len(full_closes) >= 14 else 50
        
        # LONG sinyali doğrulaması
        if pending.side == "LONG":
            # Olumlu kriterler
            bullish_momentum = price_momentum > 0
            strong_bodies = avg_body_strength >= 0.60
            volume_support = avg_volume > bars["v"].rolling(10).mean().iloc[-1] * 1.1
            rsi_not_overbought = rsi_val < 75
            
            # Olumsuz kriterler (iptal nedenleri)
            bearish_momentum = price_momentum < -0.002 * closes[0]  # %0.2 düşüş
            weak_bodies = avg_body_strength < 0.30
            volume_weak = avg_volume < bars["v"].rolling(10).mean().iloc[-1] * 0.7
            
            positive_signals = sum([bullish_momentum, strong_bodies, volume_support, rsi_not_overbought])
            negative_signals = sum([bearish_momentum, weak_bodies, volume_weak])
            
            details = {
                "price_momentum": price_momentum,
                "avg_body_strength": avg_body_strength,
                "avg_volume": avg_volume,
                "rsi": rsi_val,
                "positive_count": positive_signals,
                "negative_count": negative_signals,
                "criteria": {
                    "bullish_momentum": bullish_momentum,
                    "strong_bodies": strong_bodies,
                    "volume_support": volume_support,
                    "rsi_not_overbought": rsi_not_overbought
                }
            }
            
            # Karar verme
            if negative_signals >= 2:
                return {"action": "cancel", "details": details}
            elif positive_signals >= 3:
                bonus = min(5, positive_signals)
                return {"action": "confirm", "details": details, "bonus_score": bonus}
            else:
                return {"action": "continue", "details": details}
        
        # SHORT sinyali doğrulaması
        else:  # pending.side == "SHORT"
            # Olumlu kriterler
            bearish_momentum = price_momentum < 0
            strong_bodies = avg_body_strength >= 0.60
            volume_support = avg_volume > bars["v"].rolling(10).mean().iloc[-1] * 1.1
            rsi_not_oversold = rsi_val > 25
            
            # Olumsuz kriterler (iptal nedenleri)
            bullish_momentum = price_momentum > 0.002 * closes[0]  # %0.2 yükseliş
            weak_bodies = avg_body_strength < 0.30
            volume_weak = avg_volume < bars["v"].rolling(10).mean().iloc[-1] * 0.7
            
            positive_signals = sum([bearish_momentum, strong_bodies, volume_support, rsi_not_oversold])
            negative_signals = sum([bullish_momentum, weak_bodies, volume_weak])
            
            details = {
                "price_momentum": price_momentum,
                "avg_body_strength": avg_body_strength,
                "avg_volume": avg_volume,
                "rsi": rsi_val,
                "positive_count": positive_signals,
                "negative_count": negative_signals,
                "criteria": {
                    "bearish_momentum": bearish_momentum,
                    "strong_bodies": strong_bodies,
                    "volume_support": volume_support,
                    "rsi_not_oversold": rsi_not_oversold
                }
            }
            
            # Karar verme
            if negative_signals >= 2:
                return {"action": "cancel", "details": details}
            elif positive_signals >= 3:
                bonus = min(5, positive_signals)
                return {"action": "confirm", "details": details, "bonus_score": bonus}
            else:
                return {"action": "continue", "details": details}
    
    def get_pending_count(self) -> int:
        """Bekleyen sinyal sayısını döndür."""
        return len([p for p in self.pending_signals.values() if not p.cancelled and not p.confirmed])
    
    def get_status_summary(self) -> Dict[str, Any]:
        """Doğrulama sistemi durumu özeti."""
        total_pending = len(self.pending_signals)
        active_pending = self.get_pending_count()
        
        symbols = list(self.pending_signals.keys())
        
        return {
            "total_pending": total_pending,
            "active_pending": active_pending,
            "pending_symbols": symbols,
            "oldest_signal_age": min([time.time() - p.created_at for p in self.pending_signals.values()]) if self.pending_signals else 0
        }