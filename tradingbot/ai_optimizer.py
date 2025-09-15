#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
AI Super Optimizer - Otomatik Parametre Optimizasyonu
Tüm bot parametrelerini AI ile dinamik olarak optimize eder.
"""

import time
import json
import math
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone
from pathlib import Path

from . import config
from .utils import log, clip_value


class AIOptimizer:
    """
    AI Super Optimizer - Bot parametrelerini otomatik optimize eder.
    """
    
    def __init__(self):
        self.optimization_history = []
        self.performance_window = 20  # Son 20 sinyali analiz et
        self.learning_rate = 0.1
        self.optimization_cooldown = 300  # 5 dakika cooldown
        self.last_optimization = 0
        
        # Optimizable parameters with their safe ranges
        self.optimizable_params = {
            'ATR_STOP_MULT': (1.0, 3.0, 'float'),
            'BASE_MIN_SCORE': (30, 60, 'int'),
            'TOP_N_PER_SCAN': (1, 5, 'int'),
            'VALIDATION_TIMEOUT_SEC': (300, 1800, 'int'),
            'MIN_VOLVALUE_USDT': (1000000, 5000000, 'int'),
            'ADX_TREND_MIN': (15, 30, 'int'),
            'BB_K': (1.5, 2.5, 'float'),
            'VALIDATION_MIN_BARS': (2, 4, 'int'),
            'VALIDATION_BODY_STRENGTH_MIN': (0.4, 0.8, 'float'),
            'VALIDATION_VOLUME_MULTIPLIER': (1.0, 2.0, 'float'),
            'VALIDATION_ATR_MOVE_MIN': (0.15, 0.5, 'float')
        }
        
        # Performance metrics tracking
        self.metrics = {
            'win_rate': 0.0,
            'avg_profit': 0.0,
            'avg_loss': 0.0,
            'sl_hit_rate': 0.0,
            'tp1_hit_rate': 0.0,
            'avg_bars_held': 0.0,
            'sharpe_ratio': 0.0
        }
        
        log("🧠 AI Super Optimizer başlatıldı!")
    
    def analyze_performance(self, signal_records: List[Dict]) -> Dict[str, float]:
        """
        Son performansı analiz et ve metrikleri hesapla.
        
        Args:
            signal_records: Sinyal kayıtları listesi
            
        Returns:
            Dict: Performance metrikleri
        """
        if len(signal_records) < 5:
            return self.metrics
            
        # Son N sinyali al
        recent_signals = signal_records[-self.performance_window:]
        
        wins = 0
        losses = 0
        profits = []
        losses_list = []
        sl_hits = 0
        tp1_hits = 0
        bars_held = []
        
        for signal in recent_signals:
            if signal.get('status') in ['TP1', 'TP2', 'TP3']:
                wins += 1
                if signal.get('pnl_pct'):
                    profits.append(signal['pnl_pct'])
                if signal.get('status') == 'TP1':
                    tp1_hits += 1
            elif signal.get('status') == 'SL':
                losses += 1
                sl_hits += 1
                if signal.get('pnl_pct'):
                    losses_list.append(abs(signal['pnl_pct']))
                    
            if signal.get('bars_held'):
                bars_held.append(signal['bars_held'])
        
        total_trades = wins + losses
        if total_trades == 0:
            return self.metrics
            
        # Metrikleri hesapla
        self.metrics = {
            'win_rate': wins / total_trades,
            'avg_profit': sum(profits) / len(profits) if profits else 0.0,
            'avg_loss': sum(losses_list) / len(losses_list) if losses_list else 0.0,
            'sl_hit_rate': sl_hits / total_trades,
            'tp1_hit_rate': tp1_hits / total_trades,
            'avg_bars_held': sum(bars_held) / len(bars_held) if bars_held else 0.0,
            'sharpe_ratio': self._calculate_sharpe(recent_signals)
        }
        
        return self.metrics
    
    def _calculate_sharpe(self, signals: List[Dict]) -> float:
        """Sharpe ratio hesapla."""
        returns = []
        for signal in signals:
            if signal.get('pnl_pct') is not None:
                returns.append(signal['pnl_pct'])
        
        if len(returns) < 3:
            return 0.0
            
        avg_return = sum(returns) / len(returns)
        std_return = math.sqrt(sum((r - avg_return) ** 2 for r in returns) / len(returns))
        
        return avg_return / std_return if std_return > 0 else 0.0
    
    def identify_failure_reasons(self, failed_signals: List[Dict]) -> Dict[str, int]:
        """
        Başarısız sinyallerin sebeplerini analiz et.
        
        Args:
            failed_signals: Başarısız sinyaller
            
        Returns:
            Dict: Başarısızlık sebepleri ve sayıları
        """
        reasons = {}
        
        for signal in failed_signals:
            if signal.get('status') != 'SL':
                continue
                
            # Root cause analysis
            if signal.get('sl_reason'):
                reason = signal['sl_reason']
            else:
                # Heuristic analysis based on signal data
                reason = self._analyze_failure_heuristic(signal)
            
            reasons[reason] = reasons.get(reason, 0) + 1
        
        return reasons
    
    def _analyze_failure_heuristic(self, signal: Dict) -> str:
        """
        Heuristic failure analysis.
        """
        # Bu basit bir heuristic, gerçekte daha sofistike olabilir
        bars_held = signal.get('bars_held', 0)
        
        if bars_held < 3:
            return "immediate_reversal"
        elif bars_held < 10:
            return "weak_momentum"
        elif signal.get('volatility_at_entry', 0) > 0.05:
            return "high_volatility"
        else:
            return "trend_change"
    
    def suggest_optimizations(self, performance_metrics: Dict, failure_reasons: Dict) -> Dict[str, float]:
        """
        Performance ve failure analysis'e göre optimizasyon önerileri.
        
        Args:
            performance_metrics: Performance metrikleri
            failure_reasons: Başarısızlık sebepleri
            
        Returns:
            Dict: Önerilen parametre değişiklikleri
        """
        suggestions = {}
        log(f"🧠 AI ANALYSIS BAŞLADI:")
        log(f"   📊 Win Rate: {performance_metrics['win_rate']:.1%}")
        log(f"   📊 SL Hit Rate: {performance_metrics['sl_hit_rate']:.1%}")
        log(f"   📊 TP1 Hit Rate: {performance_metrics['tp1_hit_rate']:.1%}")
        log(f"   📊 Avg Profit: {performance_metrics['avg_profit']:.2f}%")
        log(f"   📊 Avg Loss: {performance_metrics['avg_loss']:.2f}%")
        log(f"   📊 Sharpe Ratio: {performance_metrics['sharpe_ratio']:.2f}")
        
        if failure_reasons:
            log(f"   🔍 SL Sebepleri: {failure_reasons}")
        
        # Win rate düşükse
        if performance_metrics['win_rate'] < 0.4:
            old_score = config.BASE_MIN_SCORE
            new_score = min(config.BASE_MIN_SCORE + 5, 60)
            suggestions['BASE_MIN_SCORE'] = new_score
            log(f"   🎯 Win rate düşük (%{performance_metrics['win_rate']*100:.1f}) → BASE_MIN_SCORE {old_score} → {new_score}")
            
            old_bars = config.VALIDATION_MIN_BARS
            new_bars = min(config.VALIDATION_MIN_BARS + 1, 4)
            suggestions['VALIDATION_MIN_BARS'] = new_bars
            log(f"   🎯 Daha fazla doğrulama → VALIDATION_MIN_BARS {old_bars} → {new_bars}")
        
        # SL çok sık çarpıyorsa
        if performance_metrics['sl_hit_rate'] > 0.6:
            old_atr = config.ATR_STOP_MULT
            new_atr = min(config.ATR_STOP_MULT + 0.2, 3.0)
            suggestions['ATR_STOP_MULT'] = new_atr
            log(f"   🛑 SL çok sık çarpıyor (%{performance_metrics['sl_hit_rate']*100:.1f}) → ATR_STOP_MULT {old_atr} → {new_atr}")
            
        # Immediate reversal çoksa
        if failure_reasons.get('immediate_reversal', 0) > 3:
            old_body = config.VALIDATION_BODY_STRENGTH_MIN
            new_body = min(config.VALIDATION_BODY_STRENGTH_MIN + 0.1, 0.8)
            suggestions['VALIDATION_BODY_STRENGTH_MIN'] = new_body
            log(f"   ⚡ Immediate reversal çok ({failure_reasons.get('immediate_reversal')}) → BODY_STRENGTH {old_body:.2f} → {new_body:.2f}")
            
            old_vol = config.VALIDATION_VOLUME_MULTIPLIER
            new_vol = min(config.VALIDATION_VOLUME_MULTIPLIER + 0.1, 2.0)
            suggestions['VALIDATION_VOLUME_MULTIPLIER'] = new_vol
            log(f"   ⚡ Volume filtreleme güçlendirildi → VOLUME_MULTIPLIER {old_vol:.1f} → {new_vol:.1f}")
        
        # High volatility failures
        if failure_reasons.get('high_volatility', 0) > 2:
            old_vol = config.MIN_VOLVALUE_USDT
            new_vol = max(config.MIN_VOLVALUE_USDT - 500000, 1000000)
            suggestions['MIN_VOLVALUE_USDT'] = new_vol
            log(f"   🌪️ High volatility failures ({failure_reasons.get('high_volatility')}) → MIN_VOLVALUE {old_vol/1000000:.1f}M → {new_vol/1000000:.1f}M")
            
            old_adx = config.ADX_TREND_MIN
            new_adx = min(config.ADX_TREND_MIN + 2, 30)
            suggestions['ADX_TREND_MIN'] = new_adx
            log(f"   🌪️ Trend filtreleme güçlendirildi → ADX_TREND_MIN {old_adx} → {new_adx}")
        
        # Trend reversal çoksa
        if failure_reasons.get('trend_reversal', 0) > 3:
            old_adx = config.ADX_TREND_MIN
            new_adx = min(config.ADX_TREND_MIN + 3, 30)
            suggestions['ADX_TREND_MIN'] = new_adx
            log(f"   🔄 Trend reversal çok ({failure_reasons.get('trend_reversal')}) → ADX_TREND_MIN {old_adx} → {new_adx}")
            
            old_atr = config.ATR_STOP_MULT
            new_atr = min(config.ATR_STOP_MULT + 0.3, 3.0)
            suggestions['ATR_STOP_MULT'] = new_atr
            log(f"   🔄 SL genişletiliyor → ATR_STOP_MULT {old_atr:.1f} → {new_atr:.1f}")
        
        # TP1 hit rate düşükse
        if performance_metrics['tp1_hit_rate'] < 0.3:
            old_atr_move = config.VALIDATION_ATR_MOVE_MIN
            new_atr_move = max(config.VALIDATION_ATR_MOVE_MIN - 0.05, 0.15)
            suggestions['VALIDATION_ATR_MOVE_MIN'] = new_atr_move
            log(f"   🎯 TP1 hit rate düşük (%{performance_metrics['tp1_hit_rate']*100:.1f}) → ATR_MOVE_MIN {old_atr_move:.2f} → {new_atr_move:.2f}")
        
        # Weak momentum çoksa
        if failure_reasons.get('weak_momentum', 0) > 2:
            old_score = config.BASE_MIN_SCORE
            new_score = min(config.BASE_MIN_SCORE + 3, 60)
            suggestions['BASE_MIN_SCORE'] = new_score
            log(f"   💪 Weak momentum çok ({failure_reasons.get('weak_momentum')}) → BASE_MIN_SCORE {old_score} → {new_score}")
        
        if not suggestions:
            log(f"   ✅ AI: Mevcut parametreler optimal görünüyor, değişiklik önerilmiyor")
        else:
            log(f"   🔧 AI: {len(suggestions)} parametre için değişiklik öneriliyor")
        
        return suggestions
    
    def apply_optimizations(self, suggestions: Dict[str, float]) -> None:
        """
        Önerilen optimizasyonları config'e uygula.
        
        Args:
            suggestions: Önerilen değişiklikler
        """
        if not suggestions:
            return
            
        applied = []
        log(f"🧠 AI OPTIMIZER: {len(suggestions)} parametre değiştiriliyor...")
        
        for param, new_value in suggestions.items():
            if hasattr(config, param):
                old_value = getattr(config, param)
                
                # Safe range kontrolü
                if param in self.optimizable_params:
                    min_val, max_val, param_type = self.optimizable_params[param]
                    new_value = clip_value(new_value, min_val, max_val)
                    
                    if param_type == 'int':
                        new_value = int(new_value)
                
                # Değişiklik kayda değerse uygula
                if abs(new_value - old_value) > 0.01:
                    setattr(config, param, new_value)
                    change_desc = f"{param}: {old_value} → {new_value}"
                    applied.append(change_desc)
                    log(f"   ✅ {change_desc}")
                    
                    # Reasoning ekle
                    if param == 'ATRSTOPMULT':
                        log(f"      💭 Sebep: SL mesafesi genişletildi, trend reversal'a karşı koruma")
                    elif param == 'BASE_MIN_SCORE':
                        log(f"      💭 Sebep: Daha kaliteli sinyaller için minimum skor artırıldı")
                    elif param == 'ADX_TREND_MIN':
                        log(f"      💭 Sebep: Güçlü trend koşulu, zayıf trendlerde trading azaltıldı")
                    elif param == 'VALIDATION_BODY_STRENGTH_MIN':
                        log(f"      💭 Sebep: Güçlü mum kriteri, zayıf momentum filtrelendi")
                    elif param == 'VALIDATION_MIN_BARS':
                        log(f"      💭 Sebep: Daha fazla confirmation bar, erken giriş azaltıldı")
                else:
                    log(f"   ⏸️ {param}: Değişim çok küçük ({old_value} ≈ {new_value:.3f}), atlandı")
        
        if applied:
            log(f"🧠 ✅ AI OPTIMIZASYON TAMAMLANDI: {len(applied)} parametre güncellendi")
            self.optimization_history.append({
                'timestamp': time.time(),
                'changes': dict(suggestions),
                'metrics': dict(self.metrics),
                'reasoning': applied
            })
        else:
            log(f"🧠 ⚠️ AI: Önerilen değişiklikler çok küçük, hiçbiri uygulanmadı")
    
    def should_optimize(self) -> bool:
        """
        Optimizasyon yapılmalı mı kontrol et.
        
        Returns:
            bool: Optimizasyon yapılmalıysa True
        """
        now = time.time()
        if now - self.last_optimization < self.optimization_cooldown:
            return False
            
        return True
    
    def optimize(self, signal_records: List[Dict]) -> None:
        """
        Ana optimizasyon fonksiyonu.
        
        Args:
            signal_records: Tüm sinyal kayıtları
        """
        if not self.should_optimize():
            return
            
        if len(signal_records) < 10:
            log(f"🧠 AI: Yeterli veri yok ({len(signal_records)}/10), optimizasyon bekliyor...")
            return
            
        log(f"🧠 🔍 AI OPTIMIZER ÇALIŞIYOR...")
        log(f"   📊 Analiz edilen sinyal sayısı: {len(signal_records)}")
        log(f"   📊 Analysis window: Son {self.performance_window} sinyal")
        
        # Performance analizi
        performance = self.analyze_performance(signal_records)
        
        # Başarısız sinyalleri analiz et
        failed_signals = [s for s in signal_records[-self.performance_window:] 
                         if s.get('status') == 'SL']
        log(f"   📊 Başarısız sinyal sayısı: {len(failed_signals)}")
        
        failure_reasons = self.identify_failure_reasons(failed_signals)
        
        # Optimizasyon önerilerini al
        suggestions = self.suggest_optimizations(performance, failure_reasons)
        
        if suggestions:
            # Optimizasyonları uygula
            self.apply_optimizations(suggestions)
            self.last_optimization = time.time()
        
        log(f"🧠 ✅ AI OPTIMIZER TMAMLANDİ (Cooldown: {self.optimization_cooldown//60} dakika)")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        AI Optimizer istatistiklerini getir.
        
        Returns:
            Dict: İstatistikler
        """
        return {
            'optimization_count': len(self.optimization_history),
            'last_optimization': self.last_optimization,
            'current_metrics': self.metrics,
            'recent_changes': self.optimization_history[-3:] if len(self.optimization_history) >= 3 else self.optimization_history
        }


# Global AI Optimizer instance
_ai_optimizer = None

def get_ai_optimizer() -> AIOptimizer:
    """AI Optimizer singleton instance'ı getir."""
    global _ai_optimizer
    if _ai_optimizer is None:
        _ai_optimizer = AIOptimizer()
    return _ai_optimizer

def optimize_parameters(signal_records: List[Dict]) -> None:
    """
    Parametreleri optimize et.
    
    Args:
        signal_records: Sinyal kayıtları
    """
    optimizer = get_ai_optimizer()
    optimizer.optimize(signal_records)

def get_optimizer_stats() -> Dict[str, Any]:
    """AI Optimizer istatistiklerini getir."""
    optimizer = get_ai_optimizer()
    return optimizer.get_stats()