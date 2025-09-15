#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Yardımcı fonksiyonlar ve utility modülü.
"""

import sys
import math
import datetime as dt
import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Optional, Set, Union, Any

from . import config

def log(*args):
    """Log mesajı yazdır ve hemen flush yap."""
    print(config.PRINT_PREFIX, *args)
    sys.stdout.flush()

def now_utc():
    """Şu anki UTC zamanını döndür."""
    return dt.datetime.now(dt.timezone.utc)

def fmt(x: float) -> str:
    """Float değerini 6 ondalık basamaklı formatlı string olarak döndür."""
    return f"{x:.6f}"

def sigmoid(x: float) -> float:
    """Sigmoid fonksiyonu (0-1 arası normalize edilmiş değer döndürür)."""
    return 1/(1+math.exp(-x))

def clip_value(value: float, lower: float, upper: float) -> float:
    """Değeri belirli bir aralıkta kırp (clip)."""
    return max(lower, min(upper, value))

def to_df_klines(raw):
    """
    CCXT OHLCV verilerini pandas DataFrame'e dönüştür.
    
    Args:
        raw: CCXT API'sinden dönen OHLCV verileri (timestamp, open, high, low, close, volume formatında)
        
    Returns:
        pd.DataFrame veya None: Dönüştürülmüş DataFrame veya veri yoksa None
    """
    # CCXT: [timestamp, open, high, low, close, volume]
    if not raw: 
        return None
    
    df = pd.DataFrame(raw, columns=["time", "o", "h", "l", "c", "v"])
    for col in ["time", "o", "h", "l", "c", "v"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    
    df.dropna(inplace=True)
    df["time"] = pd.to_datetime(df["time"].astype(np.int64), unit="ms", utc=True)
    df.sort_values("time", inplace=True)
    df.reset_index(drop=True, inplace=True)
    
    return df

def chunked(seq, n):
    """Diziyi n boyutlu parçalara böl."""
    for i in range(0, len(seq), n):
        yield seq[i:i+n]

def series_like(x, idx):
    """Eğer x bir Series değilse, verilen index ile Series'e dönüştür."""
    return x if isinstance(x, pd.Series) else pd.Series(x, index=idx)