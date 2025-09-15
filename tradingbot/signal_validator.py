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
import os
import json
from pathlib import Path
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
        # Persist storage
        data_dir = Path(os.environ.get("TRADING_DATA_DIR", Path(__file__).resolve().parent.parent / "data"))
        try:
            data_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        self.pool_file = str(data_dir / "pending_signals.json")
        self._load_pool()
        
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
        
        wait_min = int(max(1, getattr(config, 'VALIDATION_TIMEOUT_SEC', 600)) // 60)
        log(f"🔄 {symbol} {signal['side']} sinyali doğrulama havuzuna eklendi ({wait_min} dakika bekleyecek)")
        
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
                
            # Timeout kontrolü (config)
            if time.time() - pending.created_at > max(300, getattr(config, 'VALIDATION_TIMEOUT_SEC', 1200)):
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
                need_bars = getattr(config, 'VALIDATION_MIN_BARS', 3)
                log(f"🔍 {symbol} 5m analiz devam ediyor ({pending.bar_count}/{need_bars} mum)")
        
        # Tamamlanmış sinyalleri temizle
        for symbol in symbols_to_remove:
            if symbol in self.pending_signals:
                del self.pending_signals[symbol]
        # Persist et
        self._save_pool()
        
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
        
        # 5 dakikalık veriyi al (retry logic ile)
        df5m = None
        for attempt in range(3):
            try:
                df5m = self.exchange.get_ohlcv(symbol, "5min", 100)
                if df5m is not None and len(df5m) >= 10:
                    break
            except Exception as e:
                log(f"{symbol} 5min veri hatası (deneme {attempt+1}/3): {e}")
                if attempt < 2:
                    import time
                    time.sleep(3)  # 3 saniye bekle

        if df5m is None or len(df5m) < 10:
            # Veri yoksa iptal etme, devam et
            log(f"⚠️ {symbol} 5min veri alınamadı, tekrar denenecek")
            return {"action": "continue", "details": {"error": "Veri alınamadı, retry"}}
        
        
        # Sinyal oluşturulduğu zamandaki bar'ı bul
        signal_time = pd.to_datetime(pending.created_at, unit="s", utc=True)
        
        # Sinyal zamanından sonraki barları al
        future_bars = df5m[df5m["time"] > signal_time].copy()
        # İlerlemeyi güncelle (kaç bar oluştu)
        try:
            pending.bar_count = int(len(future_bars))
        except Exception:
            pass
        
        if len(future_bars) < getattr(config, 'VALIDATION_MIN_BARS', 3):
            return {"action": "continue", "details": {"bars_available": len(future_bars)}}
        
        # Son N mumu analiz et
        analysis_bars = future_bars.tail(getattr(config, 'VALIDATION_MIN_BARS', 3))
        
        # Geniş 5m seriden hacim MA10 ve RSI(14) hesapla
        try:
            vol_ma10 = float(df5m["v"].rolling(10).mean().iloc[-1]) if len(df5m) >= 10 else float(df5m["v"].mean())
        except Exception:
            vol_ma10 = float(analysis_bars["v"].mean())
        try:
            rsi_val_full = float(rsi(df5m["c"], 14).iloc[-1]) if len(df5m) >= 14 else 50.0
        except Exception:
            rsi_val_full = 50.0
        # 5m ATR (14) ile 2-mum ATR-normalize momentum için referans
        try:
            from .indicators import atr_wilder
            atr5 = float(atr_wilder(df5m["h"], df5m["l"], df5m["c"], 14).iloc[-1])
        except Exception:
            atr5 = None
        
        return self._perform_3bar_analysis(pending, analysis_bars, vol_ma10, rsi_val_full, atr5)
    
    def _perform_3bar_analysis(self, pending: PendingSignal, bars: pd.DataFrame, vol_ma10: float, rsi_val_ext: float, atr5: Optional[float]) -> Dict[str, Any]:
        """
        3 mum analizi gerçekleştir.
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
            total_range = max(1e-9, highs[i] - lows[i])
            body_strengths.append(body / total_range)
        
        # Momentum analizi (ham) ve ATR-normalize büyüklük
        price_momentum = closes[-1] - closes[0]
        atr_move = abs(price_momentum) / max(1e-12, atr5) if (atr5 and atr5 > 0) else 0.0
        atr_move_ok = atr_move >= float(getattr(config, 'VALIDATION_ATR_MOVE_MIN', 0.25))
        avg_body_strength = sum(body_strengths) / max(1, len(body_strengths))
        avg_volume = sum(volumes) / max(1, len(volumes))
        
        # RSI (geniş 5m seriden gelen değer)
        rsi_val = float(rsi_val_ext)
        
        if pending.side == "LONG":
            bullish_momentum = price_momentum > 0
            strong_bodies = avg_body_strength >= float(getattr(config, 'VALIDATION_BODY_STRENGTH_MIN', 0.60))
            volume_support = avg_volume > float(vol_ma10) * float(getattr(config, 'VALIDATION_VOLUME_MULTIPLIER', 1.1))
            rsi_not_overbought = rsi_val < getattr(config, 'VALIDATION_RSI_OVERBOUGHT', 75)
            
            bearish_momentum = price_momentum < -0.002 * closes[0]
            weak_bodies = avg_body_strength < 0.30
            volume_weak = avg_volume < float(vol_ma10) * 0.7
            
            positive_signals = sum([bullish_momentum, atr_move_ok, strong_bodies, volume_support, rsi_not_overbought])
            negative_signals = sum([bearish_momentum, weak_bodies, volume_weak])
            
            details = {
                "price_momentum": float(price_momentum),
                "avg_body_strength": float(avg_body_strength),
                "avg_volume": float(avg_volume),
                "rsi": float(rsi_val),
                "positive_count": int(positive_signals),
                "negative_count": int(negative_signals),
                "atr_move": float(atr_move),
                "atr_move_ok": bool(atr_move_ok),
            }
            
            if negative_signals >= 2:
                return {"action": "cancel", "details": details}
            elif positive_signals >= 3:
                bonus = min(5, int(positive_signals))
                return {"action": "confirm", "details": details, "bonus_score": bonus}
            else:
                return {"action": "continue", "details": details}
        else:
            bearish_momentum = price_momentum < 0
            strong_bodies = avg_body_strength >= float(getattr(config, 'VALIDATION_BODY_STRENGTH_MIN', 0.60))
            volume_support = avg_volume > float(vol_ma10) * float(getattr(config, 'VALIDATION_VOLUME_MULTIPLIER', 1.1))
            rsi_not_oversold = rsi_val > getattr(config, 'VALIDATION_RSI_OVERSOLD', 25)
            
            bullish_momentum = price_momentum > 0.002 * closes[0]
            weak_bodies = avg_body_strength < 0.30
            volume_weak = avg_volume < float(vol_ma10) * 0.7
            
            positive_signals = sum([bearish_momentum, atr_move_ok, strong_bodies, volume_support, rsi_not_oversold])
            negative_signals = sum([bullish_momentum, weak_bodies, volume_weak])
            
            details = {
                "price_momentum": float(price_momentum),
                "avg_body_strength": float(avg_body_strength),
                "avg_volume": float(avg_volume),
                "rsi": float(rsi_val),
                "positive_count": int(positive_signals),
                "negative_count": int(negative_signals),
                "atr_move": float(atr_move),
                "atr_move_ok": bool(atr_move_ok),
            }
            
            if negative_signals >= 2:
                return {"action": "cancel", "details": details}
            elif positive_signals >= 3:
                bonus = min(5, int(positive_signals))
                return {"action": "confirm", "details": details, "bonus_score": bonus}
            else:
                return {"action": "continue", "details": details}

    def _save_pool(self):
        """Bekleyen havuzu diske kaydet."""
        try:
            data = {}
            for sym, p in self.pending_signals.items():
                data[sym] = {
                    "symbol": p.symbol,
                    "side": p.side,
                    "entry": p.entry,
                    "sl": p.sl,
                    "tps": list(p.tps) if isinstance(p.tps, (list, tuple)) else [],
                    "score": p.score,
                    "reason": p.reason,
                    "regime": p.regime,
                    "created_at": p.created_at,
                    "bar_count": p.bar_count,
                    "confirmed": p.confirmed,
                    "cancelled": p.cancelled,
                }
            with open(self.pool_file, 'w') as f:
                json.dump(data, f)
        except Exception as e:
            log(f"Pending pool kaydetme hatası: {e}")

    def _load_pool(self):
        """Bekleyen havuzu diskten yükle."""
        try:
            with open(self.pool_file, 'r') as f:
                data = json.load(f)
            for sym, d in data.items():
                self.pending_signals[sym] = PendingSignal(
                    symbol=d.get('symbol', sym),
                    side=d.get('side', 'LONG'),
                    entry=float(d.get('entry', 0.0)),
                    sl=float(d.get('sl', 0.0)),
                    tps=tuple(d.get('tps', [])) if d.get('tps') else (0.0, 0.0, 0.0),
                    score=float(d.get('score', 0.0)),
                    reason=d.get('reason', ''),
                    regime=d.get('regime', 'UNKNOWN'),
                    created_at=float(d.get('created_at', time.time() - 60)),
                    bar_count=int(d.get('bar_count', 0)),
                    confirmed=bool(d.get('confirmed', False)),
                    cancelled=bool(d.get('cancelled', False)),
                    validation_data={}
                )
            if data:
                log(f"🔁 Pending pool yüklendi: {len(self.pending_signals)} sembol")
        except FileNotFoundError:
            pass
        except Exception as e:
            log(f"Pending pool yükleme hatası: {e}")
    
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