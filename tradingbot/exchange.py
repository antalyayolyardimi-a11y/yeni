#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Borsa iletişimi ve işlemleri.
"""

import time
import ccxt
from typing import Dict, List, Optional, Set, Tuple, Union, Any

from . import config
from .utils import log, to_df_klines

class Exchange:
    def __init__(self):
        """CCXT KuCoin client'ını başlat"""
        self.client = ccxt.kucoin({
            'enableRateLimit': True,
        })
        self._symbols_set = None
    
    def _load_symbols_set(self):
        """Desteklenen sembollerin setini yükle."""
        if self._symbols_set is not None:
            return
        try:
            markets = self._api_call_with_retry(self.client.load_markets)
            self._symbols_set = set(self.client.symbols) if self.client.symbols else set()
        except Exception as e:
            log(f"Sembol listesi yüklenirken hata: {e}")
            self._symbols_set = set()
    
    def _api_call_with_retry(self, func, *args, **kwargs):
        """API çağrısını retry logic ile gerçekleştir"""
        return self._retry_request(func, *args, **kwargs)
    
    def _retry_request(self, func, *args, **kwargs):
        """API isteğini retry logic ile gerçekleştir"""
        max_retries = 3
        retry_delays = getattr(config, 'DEFAULT_RETRY_DELAYS', [5, 15, 30])  # ✅ DÜZELTİLDİ: Magic number config'den
        
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                print(f"📟 API hatası (deneme {attempt + 1}/{max_retries}): {e}")
                
                if attempt < max_retries - 1:
                    delay = retry_delays[attempt]
                    print(f"📟 {delay} saniye bekleyip tekrar deneniyor...")
                    time.sleep(delay)
                else:
                    print(f"📟 Tüm denemeler başarısız oldu: {e}")
                    return None
    
    def normalize_symbol_to_kucoin(self, user_sym: str) -> Optional[str]:
        """
        Kullanıcı girişini KuCoin sembol formatına normalize eder.
        
        Args:
            user_sym: WIFUSDT, wif-usdt, WIF/USDT gibi kullanıcı girişi
            
        Returns:
            str: WIF-USDT gibi normalize edilmiş sembol veya None
        """
        if not user_sym:
            return None
            
        s = user_sym.strip().upper().replace(" ", "").replace("_", "-").replace("/", "-")
        
        if "-" in s:
            cand = s
        else:
            cand = None
            for q in config.KNOWN_QUOTES:
                if s.endswith(q):
                    base = s[: -len(q)]
                    if base:
                        cand = f"{base}-{q}"
                        break
            if cand is None:
                cand = s
                
        if self._symbols_set is None:
            self._load_symbols_set()
            
        if self._symbols_set and cand in self._symbols_set:
            return cand
            
        alts = [cand.replace("--", "-")]
        
        if "-" not in s:
            for q in config.KNOWN_QUOTES:
                if s.endswith(q):
                    base = s[: -len(q)]
                    if base:
                        alts.append(f"{base}-{q}")
                        
        if "-" not in cand and all(not cand.endswith(q) for q in config.KNOWN_QUOTES):
            alts.append(f"{cand}-USDT")
            
        for a in alts:
            if self._symbols_set and a in self._symbols_set:
                return a
                
        return None
    
    def _convert_interval_to_ccxt(self, interval: str) -> str:
        """KuCoin interval formatını CCXT formatına dönüştür"""
        mapping = {
            "1min": "1m",
            "5min": "5m", 
            "15min": "15m",
            "30min": "30m",
            "1hour": "1h",
            "4hour": "4h",
            "1day": "1d",
            "1week": "1w"
        }
        return mapping.get(interval, interval)
        
    def get_ohlcv(self, symbol: str, interval: str, limit: int):
        """
        Belirtilen sembolün mum verilerini al.
        
        Args:
            symbol: Sembol (örn: "BTC-USDT")
            interval: Zaman aralığı (örn: "15min", "1hour")
            limit: Alınacak mum sayısı
            
        Returns:
            pd.DataFrame veya None: OHLCV verileri içeren DataFrame veya hata durumunda None
        """
        try:
            ccxt_interval = self._convert_interval_to_ccxt(interval)
            raw = self._api_call_with_retry(self.client.fetch_ohlcv, symbol, ccxt_interval, limit=limit)
            return to_df_klines(raw)
        except Exception as e:
            msg = str(e)
            if "does not exist" in msg or "not found" in msg:
                log(f"❗ Desteklenmeyen parite: {symbol} (KuCoin formatı 'BASE-QUOTE' olmalı, örn. WIF-USDT)")
            else:
                log(f"{symbol} {interval} veri hatası:", e)
            return None
    
    def get_filtered_symbols(self) -> List[str]:
        """
        Hacim filtreli USDT sembolleri listesi.
        
        Returns:
            List[str]: Hacim koşulunu sağlayan semboller listesi
        """
        try:
            # Markets'ı yükle
            markets = self._api_call_with_retry(self.client.load_markets)
            
            # USDT çiftlerini filtrele
            symbols = self.client.symbols or []
            usdt_pairs = [symbol for symbol in symbols 
                         if symbol.endswith('/USDT')]
            
            # 24h ticker verilerini al
            tickers = self._api_call_with_retry(self.client.fetch_tickers) or {}
            
            # Hacim filtrelemesi (USDT cinsinden)
            filtered = []
            for symbol in usdt_pairs:
                ticker = tickers.get(symbol, {})
                quote_volume = ticker.get('quoteVolume', 0.0) or 0.0
                if quote_volume >= config.MIN_VOLVALUE_USDT:
                    # CCXT formatından KuCoin formatına dönüştür (BTC/USDT -> BTC-USDT)
                    kucoin_symbol = symbol.replace('/', '-')
                    filtered.append(kucoin_symbol)
            
            if not filtered:
                # Fallback - tüm USDT çiftleri
                filtered = [symbol.replace('/', '-') for symbol in usdt_pairs[:50]]
            
            return filtered
            
        except Exception as e:
            log(f"Filtered symbols hatası: {e}")
            return ["BTC-USDT", "ETH-USDT", "SOL-USDT"]  # Safe fallback
    
    def get_volume_percentiles(self, symbols: List[str]) -> Dict[str, float]:
        """
        Sembollerin hacim yüzdeliklerini hesapla.
        
        Args:
            symbols: Semboller listesi
            
        Returns:
            Dict: {sembol: hacim_yüzdelik} eşleşmesi
        """
        try:
            # 24h ticker verilerini al
            tickers = self._api_call_with_retry(self.client.fetch_tickers) or {}
        except Exception as e:
            log(f"Ticker verileri alınamadı: {e}")
            return {sym: 0.0 for sym in symbols}
        
        # KuCoin formatından CCXT formatına dönüştür ve hacim map'i oluştur
        volmap = {}
        for symbol in symbols:
            ccxt_symbol = symbol.replace('-', '/')  # BTC-USDT -> BTC/USDT
            ticker = tickers.get(ccxt_symbol, {})
            volmap[symbol] = ticker.get('quoteVolume', 0.0) or 0.0
        
        vals = [volmap.get(s, 0.0) for s in symbols]
        if not vals:
            return {}
            
        sorted_vals = sorted(vals)
        n = len(sorted_vals)
        
        cache = {}
        for s in symbols:
            v = volmap.get(s, 0.0)
            rank = sum(1 for x in sorted_vals if x <= v)
            cache[s] = rank / n
            
        return cache
    
    def build_vol_pct_cache(self, symbols: List[str]) -> Dict[str, float]:
        """
        Sembol listesi için hacim percentile cache'i oluştur.
        Geriye uyumluluk için get_volume_percentiles'a yönlendir.
        
        Args:
            symbols: Semboller listesi
            
        Returns:
            Dict: {sembol: hacim_yüzdelik} eşleşmesi
        """
        return self.get_volume_percentiles(symbols)