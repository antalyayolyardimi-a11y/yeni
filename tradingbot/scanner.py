#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Ana tarama ve işlem mantığı.
"""

import asyncio
import time
import random
import pandas as pd
from typing import Dict, List, Tuple, Any, Optional, Set

from . import config
from .utils import log, now_utc
from .exchange import Exchange
from .alerts import AlertManager
from .scoring import pick_best_candidate
from .ai import auto_tune_now, enrich_with_ai, reset_ai
from .signal_validator import SignalValidator

class Scanner:
    """
    Ana tarama mantığı ve yönetici sınıf.
    """
    
    def __init__(self):
        """
        Tarama ve sinyal yönetimi için gerekli değişkenleri başlat.
        """
        self.exchange = Exchange()
        self.alert_manager = AlertManager()
        self.signal_validator = SignalValidator(self.exchange)  # Yeni doğrulama sistemi
        
        # Durum değişkenleri
        self.state = {
            "last_signal_ts": {},
            "position_state": {},
            "signals_history": [],
            "vol_pct_cache": {},
            "dyn_MIN_SCORE": config.BASE_MIN_SCORE,
            "empty_scans": 0,
            "relax_acc": 0,
            "last_tune_ts": 0,
            "MODE": config.MODE,
            "BASE_MIN_SCORE": config.BASE_MIN_SCORE,
            "ADX_TREND_MIN": config.ADX_TREND_MIN,
            "BWIDTH_RANGE": config.BWIDTH_RANGE,
            "VOL_MULT_REQ_GLOBAL": config.VOL_MULT_REQ_GLOBAL
        }
    
    async def run(self):
        """
        Ana tarama döngüsünü başlat.
        """
        # Telegram ve tarama işlemlerini paralel çalıştır
        await asyncio.gather(
            self.alert_manager.dp.start_polling(self.alert_manager.bot),
            self.run_scanner()
        )
    
    async def run_scanner(self):
        """
        Ana tarama döngüsü.
        """
        # Başlangıç sembol listesini ve hacim bilgilerini al
        syms = self.exchange.get_filtered_symbols()
        random.shuffle(syms)
        # Tüm sembolleri kullan (limit yok)
        
        # Hacim persentil cache'ini oluştur
        self.state["vol_pct_cache"] = self.exchange.build_vol_pct_cache(syms)
        
        log(f"Toplam {len(syms)} USDT çifti | Mode: {self.state['MODE']}")
        
        if config.SHOW_SYMBOL_LIST_AT_START:
            for chunk in self._chunked(syms, config.CHUNK_PRINT):
                log("Taranacak: " + "  ".join(chunk))
        
        # Tarama semaforunu oluştur (eş zamanlı istek sayısını sınırla)
        sem = asyncio.Semaphore(config.SYMBOL_CONCURRENCY)
        
        while True:
            # Açık sinyalleri çözümle ve auto-tuner çalıştır
            self.resolve_open_signals()
            self.state = auto_tune_now(self.state, self.state["signals_history"])
            
            # Bekleyen sinyalleri doğrula (5 dakikalık analiz)
            confirmed_signals = self.signal_validator.validate_pending_signals()
            
            # Doğrulanmış sinyalleri gönder
            for confirmed in confirmed_signals:
                log(
                    f"🎯 ONAYLANDI: {confirmed['symbol']} {confirmed['side']} | "
                    f"Entry={confirmed['entry']:.6f} "
                    f"TP1={confirmed['tps'][0]:.6f} "
                    f"SL={confirmed['sl']:.6f} | "
                    f"Skor={int(confirmed['score'])} | "
                    f"{confirmed['reason']}"
                )
                await self.alert_manager.send_signal(confirmed)
                
                # Durum bilgilerini güncelle
                self.state["last_signal_ts"][confirmed["symbol"]] = time.time()
                
                # Performans değerlendirmesi için sinyali kaydet
                self.schedule_signal_for_eval(
                    confirmed["symbol"], 
                    confirmed["side"], 
                    confirmed["entry"], 
                    confirmed["sl"], 
                    confirmed["tps"][0], 
                    int(time.time()), 
                    feats=confirmed.get("_feats", {})
                )
            
            # Tarama başla
            t0 = time.time()
            tasks = [self.scan_one_symbol(sym, sem) for sym in syms]
            results = await asyncio.gather(*tasks)
            candidates = [r for r in results if r]
            candidates.sort(key=lambda x: x["score"], reverse=True)
            
            # İstatistikleri hazırla
            strong_count = sum(1 for c in candidates if c["score"] >= self.state["dyn_MIN_SCORE"])
            sent = 0
            
            # Sinyal havuza ekle (direkt gönderme yerine)
            for cand in candidates:
                if sent >= config.TOP_N_PER_SCAN:
                    break
                    
                # Standart sinyal gönderme koşulu veya fallback koşulu
                if (cand["score"] >= self.state["dyn_MIN_SCORE"] or 
                    (strong_count == 0 and cand["score"] >= config.FALLBACK_MIN_SCORE)):
                    
                    # Sinyali doğrulama havuzuna ekle
                    signal_id = self.signal_validator.add_signal_to_pool(cand)
                    
                    # Durum bilgilerini güncelle
                    self.state["position_state"][cand["symbol"]] = {
                        'side': cand["side"],
                        'bar_idx': cand["_bar_idx"],
                        'last_bar_ts': cand["_last_bar_ts"]
                    }
                    
                    sent += 1
            
            # Tarama süresini hesapla ve logla
            dt_scan = time.time() - t0
            pending_count = self.signal_validator.get_pending_count()
            log(f"♻️ Tarama tamam ({dt_scan:.1f}s). Havuza eklenen: {sent}. Bekleyen doğrulama: {pending_count}. DynMinScore={self.state['dyn_MIN_SCORE']} | Mode={self.state['MODE']}")
            
            # Adaptif gevşetme (sinyal yoksa geçici yumuşatma)
            if strong_count == 0:
                self.state["empty_scans"] += 1
                if (self.state["empty_scans"] >= config.EMPTY_LIMIT and 
                    self.state["relax_acc"] < config.RELAX_MAX):
                    self.state["dyn_MIN_SCORE"] = max(58, self.state["dyn_MIN_SCORE"] - config.RELAX_STEP)
                    self.state["relax_acc"] += config.RELAX_STEP
                    self.state["empty_scans"] = 0
            else:
                self.state["empty_scans"] = 0
                self.state["dyn_MIN_SCORE"] = max(self.state["dyn_MIN_SCORE"], self.state["BASE_MIN_SCORE"])  # normale dön
            
            # Tekrar açık sinyalleri çözümle
            self.resolve_open_signals()
            
            # Bekleme süresi
            await asyncio.sleep(config.SLEEP_SECONDS)
    
    async def scan_one_symbol(self, sym: str, sem) -> Optional[Dict[str, Any]]:
        """
        Bir sembolü tara ve sinyal varsa döndür.
        
        Args:
            sym: Taranacak sembol
            sem: Senkronizasyon semaforü
            
        Returns:
            Dict veya None: Sinyal adayı veya None
        """
        async with sem:
            if config.VERBOSE_SCAN:
                log(f"🔎 Taranıyor: {sym}")
                
            now = time.time()
            
            # Cooldown kontrolü
            if sym in self.state["last_signal_ts"] and now - self.state["last_signal_ts"][sym] < config.COOLDOWN_SEC:
                if config.SHOW_SKIP_REASONS:
                    log(f"⏳ (cooldown) atlanıyor: {sym}")
                return None
            
            # Verileri al
            df_ltf = self.exchange.get_ohlcv(sym, config.TF_LTF, config.LOOKBACK_LTF)
            df_htf = self.exchange.get_ohlcv(sym, config.TF_HTF, config.LOOKBACK_HTF)
            
            if df_ltf is None or len(df_ltf) < 80 or df_htf is None or len(df_htf) < 60:
                if config.SHOW_SKIP_REASONS:
                    log(f"— Veri yok/az: {sym}")
                return None
            
            # Son bar kontrolü
            last_bar_ts = int(df_ltf["time"].iloc[-1].timestamp())
            if sym in self.state["position_state"] and self.state["position_state"][sym].get("last_bar_ts") == last_bar_ts:
                if config.SHOW_SKIP_REASONS:
                    log(f"— Aynı bar, atlanıyor: {sym}")
                return None
            
            # Aday sinyali bul
            best = None
            try:
                best = pick_best_candidate(sym, df_ltf, df_htf, self.state["vol_pct_cache"])
            except Exception as e:
                log(f"candidate hata ({sym}): {e}")
            
            if not best:
                if config.SHOW_SKIP_REASONS:
                    log(f"— Aday yok: {sym}")
                return None
            
            # Flip kontrolü
            if not self.can_emit(sym, best["side"], df_ltf):
                if config.SHOW_SKIP_REASONS:
                    log(f"— Aday blok (flip): {sym}")
                return None
            
            # AI ile zenginleştir
            best = enrich_with_ai(best)
            
            if config.VERBOSE_SCAN:
                log(f"✓ Aday: {sym} {best['side']} | Skor={int(best['score'])}")
                
            # Bar bilgisini ekle
            best["_bar_idx"] = len(df_ltf) - 1
            best["_last_bar_ts"] = last_bar_ts
            
            return best
    
    def can_emit(self, symbol: str, side: str, df_ltf: pd.DataFrame) -> bool:
        """
        Sembol için sinyal gönderilebilir mi kontrol et.
        
        Args:
            symbol: Sembol
            side: İşlem yönü
            df_ltf: Düşük zaman dilimi DataFrame'i (15 dakika)
            
        Returns:
            bool: Sinyal gönderilebilirse True
        """
        st = self.state["position_state"].get(symbol)
        
        if st is None:
            return True
            
        if side == st['side']:
            return False
            
        bars_since = (len(df_ltf) - 1) - st['bar_idx']
        
        return bars_since >= config.OPPOSITE_MIN_BARS
    
    def schedule_signal_for_eval(self, sym: str, side: str, entry: float, sl: float, tp1: float, 
                              bar_ts: int, feats: Optional[Dict[str, float]] = None):
        """
        Sinyali değerlendirme için planla.
        
        Args:
            sym: Sembol
            side: İşlem yönü
            entry: Giriş fiyatı
            sl: Stop loss
            tp1: İlk take profit
            bar_ts: Bar timestamp
            feats: Özellik vektörü
        """
        self.state["signals_history"].append({
            "symbol": sym,
            "side": side,
            "entry": float(entry),
            "sl": float(sl),
            "tp1": float(tp1),
            "ts_close": int(bar_ts),
            "resolved": False,
            "result": None,
            "_feats": feats or {}
        })
    
    def evaluate_signal_outcome(self, sym: str, side: str, entry: float, sl: float, tp1: float, 
                             since_ts: int) -> Optional[str]:
        """
        Geçmiş sinyali değerlendir ve sonucunu döndür.
        
        Args:
            sym: Sembol
            side: İşlem yönü
            entry: Giriş fiyatı
            sl: Stop loss
            tp1: İlk take profit
            since_ts: Sinyal timestamp
            
        Returns:
            str veya None: "TP", "SL" veya None (henüz sonuç yok)
        """
        df = self.exchange.get_ohlcv(sym, config.TF_LTF, config.LOOKBACK_LTF)
        
        if df is None:
            return None
            
        ts = pd.to_datetime(since_ts, unit="s", utc=True)
        idx = df.index[df["time"] == ts]
        
        if len(idx) == 0:
            idx = df.index[df["time"] > ts]
            if len(idx) == 0:
                return None
            start_pos = idx.tolist()[0]
        else:
            start_pos = idx.tolist()[0] + 1
            
        end_pos = min(len(df) - 1, start_pos + config.EVAL_BARS_AHEAD)
        
        for i in range(start_pos, end_pos + 1):
            hi = float(df["h"].iloc[i])
            lo = float(df["l"].iloc[i])
            
            if side == "LONG":
                if lo <= sl and hi >= tp1:
                    return "SL"
                if lo <= sl:
                    return "SL"
                if hi >= tp1:
                    return "TP"
            else:
                if hi >= sl and lo <= tp1:
                    return "SL"
                if hi >= sl:
                    return "SL"
                if lo <= tp1:
                    return "TP"
                    
        return None
    
    def resolve_open_signals(self):
        """
        Açık sinyalleri çözümle ve güncelle.
        """
        updated = 0
        for s in self.state["signals_history"]:
            if s["resolved"]:
                continue
                
            res = self.evaluate_signal_outcome(
                s["symbol"], s["side"], s["entry"], s["sl"], s["tp1"], s["ts_close"]
            )
            
            if res in ("TP", "SL"):
                s["resolved"] = True
                s["result"] = res
                updated += 1
                
                from .scoring import mark_symbol_outcome
                mark_symbol_outcome(s["symbol"], res)
                
                # AI güncellemesi
                if config.AI_ENABLED and "_feats" in s:
                    from .ai import ai_update_online
                    ai_update_online(s["_feats"], 1 if res == "TP" else 0)
        
        if updated:
            self.adapt_thresholds()
    
    def adapt_thresholds(self):
        """
        Skorlama eşiklerini performansa göre ayarla.
        """
        recent = [s for s in self.state["signals_history"] if s.get("resolved")]
        recent = recent[-config.ADAPT_WINDOW:]
        
        if len(recent) < config.ADAPT_MIN_SAMPLES:
            return
            
        wins = sum(1 for s in recent if s.get("result") == "TP")
        wr = wins / len(recent)
        
        if wr > config.ADAPT_UP_THRESH:
            self.state["dyn_MIN_SCORE"] = max(config.MIN_SCORE_FLOOR, self.state["dyn_MIN_SCORE"] - config.ADAPT_STEP)
        elif wr < config.ADAPT_DN_THRESH:
            self.state["dyn_MIN_SCORE"] = min(config.MIN_SCORE_CEIL, self.state["dyn_MIN_SCORE"] + config.ADAPT_STEP)
    
    def _chunked(self, seq, n):
        """
        Listeyi n boyutunda parçalara böl.
        
        Args:
            seq: Bölünecek liste
            n: Parça boyutu
            
        Returns:
            Generator: Parçalanmış liste
        """
        for i in range(0, len(seq), n):
            yield seq[i:i+n]
            
    def apply_mode_change(self, mode):
        """
        Modu değiştir ve ilgili ayarları uygula.
        
        Args:
            mode: Uygulanacak mod ("aggressive", "balanced", "conservative")
        """
        # Global config değişkenini güncelle
        config.MODE = mode
        
        # Config yükle
        mode_config = config.MODE_CONFIGS[mode]
        
        # State değişkenlerini güncelle
        self.state["MODE"] = mode
        self.state["BASE_MIN_SCORE"] = mode_config["BASE_MIN_SCORE"]
        self.state["dyn_MIN_SCORE"] = mode_config["BASE_MIN_SCORE"]
        
        # Diğer parametre değerlerini güncelle
        self.state["ADX_TREND_MIN"] = mode_config["ADX_TREND_MIN"]
        self.state["BWIDTH_RANGE"] = mode_config["BWIDTH_RANGE"]
        
        # Global değişkenleri de güncelle (Geçici çözüm, daha iyi bir yaklaşım gerekiyor)
        config.BASE_MIN_SCORE = mode_config["BASE_MIN_SCORE"]
        config.FALLBACK_MIN_SCORE = mode_config["FALLBACK_MIN_SCORE"]
        config.TOP_N_PER_SCAN = mode_config["TOP_N_PER_SCAN"]
        config.COOLDOWN_SEC = mode_config["COOLDOWN_SEC"]
        config.ADX_TREND_MIN = mode_config["ADX_TREND_MIN"]
        config.ONEH_DISP_BODY_MIN = mode_config["ONEH_DISP_BODY_MIN"]
        config.BWIDTH_RANGE = mode_config["BWIDTH_RANGE"]
        config.BREAK_BUFFER = mode_config["BREAK_BUFFER"]
        config.RETEST_TOL_ATR = mode_config["RETEST_TOL_ATR"]
        config.SMC_REQUIRE_FVG = mode_config["SMC_REQUIRE_FVG"]
        config.FBB_ATR_MIN = mode_config["FBB_ATR_MIN"]
        config.FBB_ATR_MAX = mode_config["FBB_ATR_MAX"]
        config.FALLBACK_ENABLE = mode_config["FALLBACK_ENABLE"]
        config.ATR_STOP_MULT = mode_config["ATR_STOP_MULT"]