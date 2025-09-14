#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Borsa iletişimi ve işlemleri.
"""

import time
from typing import Dict, List, Optional, Set, Tuple, Union, Any
from kucoin.client import Market

from . import config
from .utils import log, to_df_klines

class Exchange:
    def __init__(self):
        """KuCoin API client'ını başlat"""
        self.market_client = Market(url="https://api.kucoin.com")
        self.client = self.market_client  # Geriye uyumluluk için alias
        self._symbols_set = None
    
    def _load_symbols_set(self):
        """Desteklenen sembollerin setini yükle."""
        if self._symbols_set is not None:
            return
        try:
            symbols = self._api_call_with_retry(self.client.get_symbol_list)
            self._symbols_set = {sym.get("symbol", "") for sym in symbols or []}
        except Exception as e:
            log(f"Sembol listesi yüklenirken hata: {e}")
            self._symbols_set = set()
    
    def _api_call_with_retry(self, func, *args, **kwargs):
        """API çağrısını retry logic ile gerçekleştir"""
        return self._retry_request(func, *args, **kwargs)
    
    def _retry_request(self, func, *args, **kwargs):
        """API isteğini retry logic ile gerçekleştir"""
        max_retries = 3
        retry_delays = [5, 15, 30]  # Her denemede daha uzun bekle
        
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
            raw = self._api_call_with_retry(self.client.get_kline, symbol, interval, limit=limit)
            return to_df_klines(raw)
        except Exception as e:
            msg = str(e)
            if "Unsupported trading pair" in msg or '"code":"400100"' in msg:
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
            syms = self._api_call_with_retry(self.client.get_symbol_list)
        except Exception as e:
            log(f"Sembol listesi alınamadı: {e}")
            return []
            
        if syms is None:
            return []
        pairs = [s["symbol"] for s in syms if s.get("quoteCurrency") == "USDT"]
        
        try:
            tickers_response = self._api_call_with_retry(self.client.get_all_tickers)
        except Exception as e:
            log(f"Ticker verileri alınamadı: {e}")
            return pairs[:50]  # Default fallback
            
        if tickers_response is None:
            return pairs[:50]  # Default fallback
        tickers = tickers_response.get("ticker", [])
        volmap = {t.get("symbol"): float(t.get("volValue", 0.0)) for t in tickers}
        
        filt = [s for s in pairs if volmap.get(s, 0.0) >= config.MIN_VOLVALUE_USDT]
        if not filt:
            filt = pairs
            
        return filt
    
    def build_vol_pct_cache(self, symbols: List[str]) -> Dict[str, float]:
        """
        Semboller için hacim yüzdelik oranlarını hesapla.
        
        Args:
            symbols: Semboller listesi
            
        Returns:
            Dict: {sembol: hacim_yüzdelik} eşleşmesi
        """
        try:
            tickers_response = self._api_call_with_retry(self.client.get_all_tickers)
        except Exception as e:
            log(f"Ticker verileri alınamadı: {e}")
            return {sym: 0.0 for sym in symbols}
            
        if tickers_response is None:
            return {s: 0.0 for s in symbols}
        tickers = tickers_response.get("ticker", [])
        volmap = {t.get("symbol"): float(t.get("volValue", 0.0)) for t in tickers}
        
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