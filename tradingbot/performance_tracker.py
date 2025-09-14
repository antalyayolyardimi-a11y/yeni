#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Performance Tracking & Auto-Optimization sistemi.
TP/SL takibi, analiz ve otomatik optimizasyon.
"""

import time
import json
import math
from dataclasses import dataclass, asdict, field
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone

from . import config
from .utils import log, now_utc

@dataclass
class SignalRecord:
    """Sinyal kaydı veri yapısı."""
    symbol: str
    side: str
    entry: float
    sl: float
    tp1: float
    tp2: float
    tp3: float
    score: float
    regime: str
    reason: str
    
    # Timing
    created_at: float
    closed_at: Optional[float] = None
    
    # Results
    status: str = "ACTIVE"  # ACTIVE, TP1, TP2, TP3, SL, CANCELLED
    pnl_pct: Optional[float] = None
    close_price: Optional[float] = None
    bars_held: int = 0
    
    # Analysis
    sl_reason: Optional[str] = None
    market_condition: Optional[str] = None
    volatility_at_entry: Optional[float] = None
    
    def to_dict(self) -> Dict:
        """Dict'e dönüştür."""
        return asdict(self)

@dataclass
class PerformanceStats:
    """Performance istatistikleri."""
    total_signals: int = 0
    active_signals: int = 0
    closed_signals: int = 0
    
    # Win/Loss
    tp1_count: int = 0
    tp2_count: int = 0
    tp3_count: int = 0
    sl_count: int = 0
    cancelled_count: int = 0
    
    # Performance Metrics
    win_rate: float = 0.0
    avg_pnl_pct: float = 0.0
    total_pnl_pct: float = 0.0
    avg_hold_time: float = 0.0
    
    # Strategy Performance
    regime_stats: Dict[str, Dict] = field(default_factory=dict)
    side_stats: Dict[str, Dict] = field(default_factory=dict)
    
    def __post_init__(self):
        if self.regime_stats is None:
            self.regime_stats = {}
        if self.side_stats is None:
            self.side_stats = {}

class PerformanceTracker:
    """
    Performance takip ve optimizasyon sistemi.
    """
    
    def __init__(self):
        """Performance tracker'ı başlat."""
        self.signals: Dict[str, SignalRecord] = {}
        self.stats = PerformanceStats()
        self.data_file = "/tmp/trading_performance.json"
        self.load_data()
        
        # Optimization settings
        self.last_optimization = time.time()
        self.optimization_interval = 3600  # 1 saat
        self.min_signals_for_optimization = 10
        
    def add_signal(self, signal_data: Dict[str, Any]) -> str:
        """
        Yeni sinyal ekle ve takibe başla.
        
        Args:
            signal_data: Sinyal verisi
            
        Returns:
            str: Signal ID
        """
        signal_id = f"{signal_data['symbol']}_{signal_data['side']}_{int(time.time())}"
        
        record = SignalRecord(
            symbol=signal_data['symbol'],
            side=signal_data['side'],
            entry=signal_data['entry'],
            sl=signal_data['sl'],
            tp1=signal_data['tps'][0],
            tp2=signal_data['tps'][1],
            tp3=signal_data['tps'][2],
            score=signal_data['score'],
            regime=signal_data.get('regime', 'UNKNOWN'),
            reason=signal_data.get('reason', ''),
            created_at=time.time(),
            volatility_at_entry=signal_data.get('_explain', {}).get('atr_pct', 0.0)
        )
        
        self.signals[signal_id] = record
        self.stats.total_signals += 1
        self.stats.active_signals += 1
        
        log(f"📊 Performance: Takibe eklendi {signal_id}")
        self.save_data()
        
        return signal_id
    
    def update_signal_status(self, exchange, symbol: str, side: str, entry: float) -> Optional[str]:
        """
        Sinyal durumunu güncelle.
        
        Args:
            exchange: Exchange nesnesi
            symbol: Sembol
            side: İşlem yönü
            entry: Giriş fiyatı
            
        Returns:
            str: Güncellenen durum
        """
        # İlgili sinyali bul
        signal_id = None
        for sid, record in self.signals.items():
            if (record.symbol == symbol and 
                record.side == side and 
                abs(record.entry - entry) < entry * 0.001 and  # %0.1 tolerans
                record.status == "ACTIVE"):
                signal_id = sid
                break
        
        if not signal_id:
            return None
            
        record = self.signals[signal_id]
        
        # Current price al
        df = exchange.get_ohlcv(symbol, "5min", 50)
        if df is None or len(df) == 0:
            return None
            
        current_price = float(df["c"].iloc[-1])
        bars_since_entry = min(len(df), 50)  # Max 50 bar takip
        
        # TP/SL kontrolü
        new_status = None
        close_price = current_price
        
        if side == "LONG":
            if current_price <= record.sl:
                new_status = "SL"
                close_price = record.sl
            elif current_price >= record.tp3:
                new_status = "TP3"
                close_price = record.tp3
            elif current_price >= record.tp2:
                new_status = "TP2"
                close_price = record.tp2
            elif current_price >= record.tp1:
                new_status = "TP1"
                close_price = record.tp1
        else:  # SHORT
            if current_price >= record.sl:
                new_status = "SL"
                close_price = record.sl
            elif current_price <= record.tp3:
                new_status = "TP3"
                close_price = record.tp3
            elif current_price <= record.tp2:
                new_status = "TP2"
                close_price = record.tp2
            elif current_price <= record.tp1:
                new_status = "TP1"
                close_price = record.tp1
        
        # Auto-cancel çok eski sinyaller (24 saat)
        if time.time() - record.created_at > 86400:
            new_status = "CANCELLED"
            close_price = current_price
        
        if new_status:
            # Sinyal kapat
            record.status = new_status
            record.closed_at = time.time()
            record.close_price = close_price
            record.bars_held = bars_since_entry
            
            # PnL hesapla
            if side == "LONG":
                record.pnl_pct = ((close_price - record.entry) / record.entry) * 100
            else:
                record.pnl_pct = ((record.entry - close_price) / record.entry) * 100
            
            # SL sebep analizi
            if new_status == "SL":
                record.sl_reason = self._analyze_sl_reason(exchange, symbol, record)
                record.market_condition = self._get_market_condition(exchange, symbol)
            
            # Stats güncelle
            self.stats.active_signals -= 1
            self.stats.closed_signals += 1
            
            if new_status == "TP1":
                self.stats.tp1_count += 1
            elif new_status == "TP2":
                self.stats.tp2_count += 1
            elif new_status == "TP3":
                self.stats.tp3_count += 1
            elif new_status == "SL":
                self.stats.sl_count += 1
            elif new_status == "CANCELLED":
                self.stats.cancelled_count += 1
            
            log(f"📊 {symbol} {side} → {new_status} | PnL: {record.pnl_pct:.2f}%")
            self.save_data()
            
            # Auto-optimization kontrolü
            if time.time() - self.last_optimization > self.optimization_interval:
                self._try_auto_optimization()
        
        return new_status
    
    def _analyze_sl_reason(self, exchange, symbol: str, record: SignalRecord) -> str:
        """
        SL sebebini analiz et.
        
        Args:
            exchange: Exchange nesnesi
            symbol: Sembol
            record: Sinyal kaydı
            
        Returns:
            str: SL sebebi
        """
        try:
            df = exchange.get_ohlcv(symbol, "15min", 20)
            if df is None or len(df) < 10:
                return "INSUFFICIENT_DATA"
            
            # Volatility analizi
            from .indicators import atr_wilder
            atr_now = float(atr_wilder(df["h"], df["l"], df["c"], 14).iloc[-1])
            atr_pct_now = atr_now / float(df["c"].iloc[-1])
            
            if record.volatility_at_entry and atr_pct_now > record.volatility_at_entry * 1.5:
                return "HIGH_VOLATILITY"
            
            # Trend değişimi
            current_trend = "UP" if df["c"].iloc[-1] > df["c"].iloc[-5] else "DOWN"
            expected_trend = "UP" if record.side == "LONG" else "DOWN"
            
            if current_trend != expected_trend:
                return "TREND_REVERSAL"
            
            # Gap/shock
            max_gap = 0
            for i in range(len(df) - 5, len(df)):
                if i > 0:
                    gap = abs(df["o"].iloc[i] - df["c"].iloc[i-1]) / df["c"].iloc[i-1]
                    max_gap = max(max_gap, gap)
            
            if max_gap > 0.02:  # %2+ gap
                return "MARKET_GAP"
            
            return "NORMAL_SL"
            
        except Exception as e:
            log(f"SL analiz hatası: {e}")
            return "ANALYSIS_ERROR"
    
    def _get_market_condition(self, exchange, symbol: str) -> str:
        """Market durumunu analiz et."""
        try:
            df = exchange.get_ohlcv(symbol, "1hour", 24)
            if df is None or len(df) < 20:
                return "UNKNOWN"
            
            # Volatility
            from .indicators import atr_wilder
            atr_val = float(atr_wilder(df["h"], df["l"], df["c"], 14).iloc[-1])
            atr_pct = atr_val / float(df["c"].iloc[-1])
            
            if atr_pct > 0.04:
                return "HIGH_VOLATILITY"
            elif atr_pct < 0.015:
                return "LOW_VOLATILITY"
            else:
                return "NORMAL_VOLATILITY"
                
        except:
            return "UNKNOWN"
    
    def _try_auto_optimization(self):
        """Otomatik optimizasyon dene."""
        if self.stats.closed_signals < self.min_signals_for_optimization:
            return
        
        log("🔧 Auto-optimization başlatılıyor...")
        
        # Win rate analizi
        win_signals = self.stats.tp1_count + self.stats.tp2_count + self.stats.tp3_count
        total_closed = self.stats.closed_signals
        current_wr = win_signals / max(1, total_closed)
        
        # Regime performance analizi
        regime_performance = self._analyze_regime_performance()
        
        # SL sebep analizi
        sl_reasons = self._analyze_sl_reasons()
        
        # Optimizasyon önerileri
        suggestions = []
        
        if current_wr < 0.4:  # %40'dan düşük WR
            suggestions.append("INCREASE_MIN_SCORE")
            
        if sl_reasons.get("HIGH_VOLATILITY", 0) > 3:
            suggestions.append("IMPROVE_VOLATILITY_FILTER")
            
        if sl_reasons.get("TREND_REVERSAL", 0) > 3:
            suggestions.append("STRENGTHEN_TREND_FILTER")
        
        # Auto-apply optimizations
        self._apply_optimizations(suggestions)
        
        self.last_optimization = time.time()
        log(f"🔧 Optimization tamamlandı. WR: {current_wr:.2f}, Suggestions: {len(suggestions)}")
    
    def _analyze_regime_performance(self) -> Dict[str, Dict]:
        """Strateji performance analizi."""
        regime_stats = {}
        
        for signal in self.signals.values():
            if signal.status == "ACTIVE":
                continue
                
            regime = signal.regime
            if regime not in regime_stats:
                regime_stats[regime] = {"total": 0, "wins": 0, "avg_pnl": 0.0}
            
            regime_stats[regime]["total"] += 1
            if signal.status in ["TP1", "TP2", "TP3"]:
                regime_stats[regime]["wins"] += 1
            
            if signal.pnl_pct:
                regime_stats[regime]["avg_pnl"] += signal.pnl_pct
        
        # Averageları hesapla
        for regime, stats in regime_stats.items():
            if stats["total"] > 0:
                stats["win_rate"] = stats["wins"] / stats["total"]
                stats["avg_pnl"] /= stats["total"]
        
        return regime_stats
    
    def _analyze_sl_reasons(self) -> Dict[str, int]:
        """SL sebeplerini analiz et."""
        sl_reasons = {}
        
        for signal in self.signals.values():
            if signal.status == "SL" and signal.sl_reason:
                reason = signal.sl_reason
                sl_reasons[reason] = sl_reasons.get(reason, 0) + 1
        
        return sl_reasons
    
    def _apply_optimizations(self, suggestions: List[str]):
        """Optimizasyon önerilerini uygula."""
        for suggestion in suggestions:
            if suggestion == "INCREASE_MIN_SCORE":
                config.BASE_MIN_SCORE = min(config.BASE_MIN_SCORE + 2, 75)
                log(f"🔧 MIN_SCORE artırıldı: {config.BASE_MIN_SCORE}")
                
            elif suggestion == "IMPROVE_VOLATILITY_FILTER":
                config.FBB_ATR_MAX = max(config.FBB_ATR_MAX * 0.9, 0.015)
                log(f"🔧 Volatility filtresi güçlendirildi: {config.FBB_ATR_MAX}")
                
            elif suggestion == "STRENGTHEN_TREND_FILTER":
                config.ADX_TREND_MIN = min(config.ADX_TREND_MIN + 2, 25)
                log(f"🔧 Trend filtresi güçlendirildi: {config.ADX_TREND_MIN}")
    
    def update_all_signals(self, exchange):
        """Tüm aktif sinyalleri güncelle."""
        active_signals = [s for s in self.signals.values() if s.status == "ACTIVE"]
        
        for signal in active_signals:
            self.update_signal_status(exchange, signal.symbol, signal.side, signal.entry)
    
    def get_status_report(self) -> str:
        """Detaylı durum raporu oluştur."""
        self._update_stats()
        
        # Ana istatistikler
        total = self.stats.total_signals
        active = self.stats.active_signals
        closed = self.stats.closed_signals
        
        # Eğer hiç sinyal yoksa başlangıç mesajı
        if total == 0:
            return """📊 **PERFORMANCE TRACKER**

🔄 **Durum**: Yeni başlatıldı
• Henüz hiç sinyal kaydedilmedi
• İlk sinyaller onaylandıktan sonra detaylı istatistikler görünecek

⏳ **Beklenen**: Sinyaller doğrulama havuzundan onaylandıktan sonra buraya eklenir"""
        
        tp_total = self.stats.tp1_count + self.stats.tp2_count + self.stats.tp3_count
        win_rate = (tp_total / max(1, closed)) * 100 if closed > 0 else 0
        
        # PnL hesaplama
        total_pnl = sum(s.pnl_pct for s in self.signals.values() if s.pnl_pct is not None)
        avg_pnl = total_pnl / max(1, closed) if closed > 0 else 0
        
        report = f"""📊 **TRADING BOT PERFORMANCE RAPORU**

📈 **Genel İstatistikler**
• Toplam Sinyal: `{total}`
• Aktif Sinyal: `{active}`
• Kapalı Sinyal: `{closed}`
• Win Rate: `{win_rate:.1f}%`
• Ortalama PnL: `{avg_pnl:.2f}%`
• Toplam PnL: `{total_pnl:.2f}%`

🎯 **Sonuç Dağılımı**
• TP1: `{self.stats.tp1_count}` ({(self.stats.tp1_count/max(1,closed)*100):.1f}%)
• TP2: `{self.stats.tp2_count}` ({(self.stats.tp2_count/max(1,closed)*100):.1f}%)
• TP3: `{self.stats.tp3_count}` ({(self.stats.tp3_count/max(1,closed)*100):.1f}%)
• SL: `{self.stats.sl_count}` ({(self.stats.sl_count/max(1,closed)*100):.1f}%)
• İptal: `{self.stats.cancelled_count}` ({(self.stats.cancelled_count/max(1,closed)*100):.1f}%)"""

        # Eğer hiç sinyal yoksa bilgilendirici mesaj
        if total == 0:
            report = f"""📊 **TRADING BOT PERFORMANCE RAPORU**

ℹ️ **Başlangıç Durumu**
• Henüz hiç sinyal gönderilmedi
• Bot şu anda sinyalleri tarayıp doğruluyor
• Signal validator havuzunda bekleyen sinyaller var
• İlk performans verileri yakında gelecek

📊 **Sistem Durumu**
• Bot Mode: `{config.MODE}`
• Min Score: `{config.BASE_MIN_SCORE}`
• Performance tracking: ✅ Aktif"""
            return report

        # Regime analizi
        regime_stats = self._analyze_regime_performance()
        if regime_stats:
            report += "\n\n🎪 **Strateji Performance**"
            for regime, stats in regime_stats.items():
                if stats["total"] >= 3:  # En az 3 sinyal olan stratejiler
                    report += f"\n• {regime}: {stats['win_rate']:.1f}% WR ({stats['wins']}/{stats['total']}) | Avg: {stats['avg_pnl']:.2f}%"
        
        # SL sebep analizi
        sl_reasons = self._analyze_sl_reasons()
        if sl_reasons:
            report += "\n\n❌ **SL Sebepleri**"
            total_sl = sum(sl_reasons.values())
            for reason, count in sorted(sl_reasons.items(), key=lambda x: x[1], reverse=True):
                pct = (count / total_sl * 100) if total_sl > 0 else 0
                reason_tr = {
                    "HIGH_VOLATILITY": "Yüksek Volatilite",
                    "TREND_REVERSAL": "Trend Dönüşü", 
                    "MARKET_GAP": "Market Gap",
                    "NORMAL_SL": "Normal SL",
                    "ANALYSIS_ERROR": "Analiz Hatası"
                }.get(reason, reason)
                report += f"\n• {reason_tr}: `{count}` ({pct:.1f}%)"
        
        # Aktif sinyaller
        active_list = [s for s in self.signals.values() if s.status == "ACTIVE"]
        if active_list:
            report += f"\n\n🔄 **Aktif Sinyaller ({len(active_list)})**"
            for signal in active_list[-5:]:  # Son 5 aktif sinyal
                age_hours = (time.time() - signal.created_at) / 3600
                report += f"\n• {signal.symbol} {signal.side} | Skor: {int(signal.score)} | Yaş: {age_hours:.1f}h"
        
        # Optimizasyon durumu
        next_opt_hours = (self.optimization_interval - (time.time() - self.last_optimization)) / 3600
        report += f"\n\n🔧 **Auto-Optimization**"
        report += f"\n• Son Opt: {((time.time() - self.last_optimization)/3600):.1f} saat önce"
        report += f"\n• Sonraki: {max(0, next_opt_hours):.1f} saat sonra"
        report += f"\n• Current Config: MinScore={config.BASE_MIN_SCORE}, ADX={config.ADX_TREND_MIN}"
        
        return report
    
    def save_data(self):
        """Verileri dosyaya kaydet."""
        try:
            data = {
                "signals": {k: v.to_dict() for k, v in self.signals.items()},
                "stats": asdict(self.stats),
                "last_save": time.time()
            }
            
            with open(self.data_file, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            log(f"Veri kaydetme hatası: {e}")
    
    def load_data(self):
        """Verileri dosyadan yükle."""
        try:
            with open(self.data_file, 'r') as f:
                data = json.load(f)
            
            # Signals yükle
            for sid, signal_data in data.get("signals", {}).items():
                self.signals[sid] = SignalRecord(**signal_data)
            
            # Stats yükle
            if "stats" in data:
                self.stats = PerformanceStats(**data["stats"])
            
            log(f"📊 Performance data yüklendi: {len(self.signals)} sinyal")
            
        except FileNotFoundError:
            log("📊 Yeni performance database oluşturuluyor")
        except Exception as e:
            log(f"Veri yükleme hatası: {e}")
    
    def update_signal_statuses(self):
        """Aktif sinyallerin durumlarını güncelle."""
        # Bu metod exchange'den fiyat bilgilerini alıp
        # sinyallerin TP/SL durumlarını kontrol edecek
        # Şimdilik basit implementasyon
        updated_count = 0
        for signal in self.signals.values():
            if signal.status == "ACTIVE":
                # Burada gerçek exchange kontrolü yapılacak
                updated_count += 1
        
        if updated_count > 0:
            self._update_stats()
            self.save_data()
    
    def _update_stats(self):
        """İstatistikleri güncelle."""
        # Temel sayılar güncelle
        active_count = sum(1 for s in self.signals.values() if s.status == "ACTIVE")
        closed_count = sum(1 for s in self.signals.values() if s.status != "ACTIVE")
        
        self.stats.active_signals = active_count
        self.stats.closed_signals = closed_count
        
        # Win rate hesapla
        if closed_count > 0:
            win_count = sum(1 for s in self.signals.values() if s.status in ["TP1", "TP2", "TP3"])
            self.stats.win_rate = win_count / closed_count
        
        # Ortalama PnL
        pnl_signals = [s for s in self.signals.values() if s.pnl_pct is not None]
        if pnl_signals:
            pnl_values = [s.pnl_pct for s in pnl_signals if s.pnl_pct is not None]
            if pnl_values:
                self.stats.avg_pnl_pct = sum(pnl_values) / len(pnl_values)
                self.stats.total_pnl_pct = sum(pnl_values)
    
    def check_auto_optimization(self):
        """Auto-optimization kontrolü yap."""
        # Win rate düşükse ATR multiplier artır
        # SL çok sık tetikleniyorsa ayarları değiştir
        
        if len(self.signals) < 10:  # Yeterli veri yok
            return None
            
        recent_signals = [s for s in self.signals.values() if s.status != "ACTIVE"]
        if len(recent_signals) < 5:
            return None
            
        win_count = sum(1 for s in recent_signals if s.status in ["TP1", "TP2", "TP3"])
        win_rate = win_count / len(recent_signals)
        
        if win_rate < 0.3:  # %30'dan düşük win rate
            # ATR multiplier'ı artır
            current_mult = getattr(self.stats, 'avg_atr_mult', 2.5)
            new_mult = min(3.5, current_mult * 1.2)
            return {"ATR_STOP_MULT": new_mult, "reason": f"Low win rate: {win_rate:.2%}"}
            
        return None