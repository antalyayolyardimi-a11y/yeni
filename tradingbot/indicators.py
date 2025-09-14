#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Teknik gösterge fonksiyonları modülü.
"""

import pandas as pd
import numpy as np
from typing import Tuple

from .utils import series_like

def ema(series, n: int):
    """
    Exponential Moving Average hesapla.
    
    Args:
        series: Hesaplama yapılacak seri
        n: EMA periyodu
        
    Returns:
        pd.Series: EMA değerlerini içeren seri
    """
    return pd.Series(series).ewm(span=n, adjust=False).mean()

def rsi(series, period: int = 14):
    """
    Relative Strength Index hesapla.
    
    Args:
        series: Kapanış fiyatları
        period: RSI periyodu
        
    Returns:
        pd.Series: RSI değerlerini içeren seri
    """
    d = series.diff()
    up = d.clip(lower=0.0)
    dn = (-d).clip(lower=0.0)
    ru = up.rolling(period).mean()
    rd = dn.rolling(period).mean()
    rs = ru/(rd+1e-12)
    return 100 - (100/(1+rs))

def body_strength(o, c, h, l):
    """
    Mum gövdesi/menzil oranını hesapla.
    
    Args:
        o: Açılış serisi
        c: Kapanış serisi
        h: Yüksek serisi
        l: Düşük serisi
        
    Returns:
        pd.Series: Body strength değerleri (0-1 arası)
    """
    o = series_like(o, c.index)
    h = series_like(h, c.index)
    l = series_like(l, c.index)
    
    body = np.abs(c.to_numpy() - o.to_numpy())
    rng  = np.abs(h.to_numpy() - l.to_numpy())
    rng[rng == 0] = np.nan
    val = body / rng
    
    return pd.Series(np.nan_to_num(val, nan=0.0), index=c.index)

def atr_wilder(h, l, c, n: int = 14):
    """
    Wilder's Average True Range hesapla.
    
    Args:
        h: Yüksek serisi
        l: Düşük serisi
        c: Kapanış serisi
        n: ATR periyodu
        
    Returns:
        pd.Series: ATR değerlerini içeren seri
    """
    pc = c.shift(1)
    tr1 = np.abs((h - l).to_numpy())
    tr2 = np.abs((h - pc).to_numpy())
    tr3 = np.abs((l - pc).to_numpy())
    tr  = pd.Series(np.maximum.reduce([tr1, tr2, tr3]), index=c.index)
    
    return tr.ewm(alpha=1/n, adjust=False).mean()

def adx(h, l, c, n: int = 14):
    """
    Average Directional Index (ADX) hesapla.
    
    Args:
        h: Yüksek serisi
        l: Düşük serisi
        c: Kapanış serisi
        n: ADX periyodu
        
    Returns:
        pd.Series: ADX değerlerini içeren seri
    """
    up = h.diff()
    dn = -l.diff()
    
    plus_dm  = np.where((up > dn) & (up > 0), up, 0.0)
    minus_dm = np.where((dn > up) & (dn > 0), dn, 0.0)
    
    atr_val = atr_wilder(h, l, c, n)
    
    pdi = 100 * pd.Series(plus_dm,  index=c.index).ewm(alpha=1/n, adjust=False).mean()/(atr_val+1e-12)
    ndi = 100 * pd.Series(minus_dm, index=c.index).ewm(alpha=1/n, adjust=False).mean()/(atr_val+1e-12)
    
    dx  = (np.abs(pdi - ndi) / ((pdi + ndi) + 1e-12)) * 100
    
    return pd.Series(dx, index=c.index).ewm(alpha=1/n, adjust=False).mean()

def bollinger(close, n: int = 20, k: float = 2.0) -> Tuple[pd.Series, pd.Series, pd.Series, pd.Series, pd.Series]:
    """
    Bollinger Bantları hesapla.
    
    Args:
        close: Kapanış fiyatları serisi
        n: Periyot
        k: Standart sapma çarpanı
        
    Returns:
        Tuple: (MA, Upper Band, Lower Band, Bandwidth, StdDev)
    """
    ma = close.rolling(n).mean()
    std = close.rolling(n).std(ddof=0)
    upper = ma + k*std
    lower = ma - k*std
    bwidth = (upper - lower) / (ma + 1e-12)
    
    return ma, upper, lower, bwidth, std

def donchian(h, l, win: int = 20) -> Tuple[pd.Series, pd.Series]:
    """
    Donchian kanalları hesapla.
    
    Args:
        h: Yüksek serisi
        l: Düşük serisi
        win: Pencere boyutu
        
    Returns:
        Tuple: (Üst bant, Alt bant)
    """
    return h.rolling(win).max(), l.rolling(win).min()

def swing_high(highs, win: int = 10) -> float:
    """Son win kadar çubuktaki en yüksek değeri döndür."""
    return highs.iloc[-win:].max()

def swing_low(lows, win: int = 10) -> float:
    """Son win kadar çubuktaki en düşük değeri döndür."""
    return lows.iloc[-win:].min()

def find_swings(h, l, left: int = 2, right: int = 2):
    """
    Zaman serisinde swing high ve swing low noktalarını bul.
    
    Args:
        h: Yüksek fiyat serisi
        l: Düşük fiyat serisi
        left: Sol tarafta bakılacak çubuk sayısı
        right: Sağ tarafta bakılacak çubuk sayısı
        
    Returns:
        Tuple: (swing high indeksleri, swing low indeksleri)
    """
    sh_idx, sl_idx = [], []
    
    for i in range(left, len(h)-right):
        wh = h.iloc[i-left:i+right+1]
        wl = l.iloc[i-left:i+right+1]
        
        if h.iloc[i] == wh.max() and (wh.idxmax()==h.index[i]):
            sh_idx.append(i)
        if l.iloc[i] == wl.min() and (wl.idxmin()==l.index[i]):
            sl_idx.append(i)
    
    return sh_idx, sl_idx

def find_fvgs(h, l, lookback: int = 20):
    """
    Fair Value Gap (FVG) bölgelerini bul.
    
    Args:
        h: Yüksek fiyat serisi
        l: Düşük fiyat serisi
        lookback: Geriye dönük bakılacak çubuk sayısı
        
    Returns:
        Tuple: (son boğa FVG'si, son ayı FVG'si) - Tuple veya None olarak
    """
    bulls, bears = [], []
    start = max(2, len(h)-lookback)
    
    for i in range(start, len(h)):
        try:
            if l.iloc[i] > h.iloc[i-2]:
                bulls.append((h.iloc[i-2], l.iloc[i]))
            if h.iloc[i] < l.iloc[i-2]:
                bears.append((h.iloc[i], l.iloc[i-2]))
        except:
            pass
    
    return bulls[-1] if bulls else None, bears[-1] if bears else None

def htf_gate_and_bias(df1h):
    """
    1 saatlik verilerden trend yönü ve durumunu analiz et.
    
    Args:
        df1h: 1 saatlik OHLC DataFrame'i
        
    Returns:
        Tuple: (bias, disp_ok, adx1h, trend_ok)
            - bias: "LONG", "SHORT" veya "NEUTRAL" olarak trend yönü
            - disp_ok: Displacement onayı varsa True
            - adx1h: ADX değeri
            - trend_ok: Trend durumu yeterliyse True
    """
    from . import config
    
    c, h, l, o = df1h["c"], df1h["h"], df1h["l"], df1h["o"]
    e50 = ema(c, 50)
    
    bias = "NEUTRAL"
    if pd.notna(e50.iloc[-1]) and pd.notna(e50.iloc[-2]):
        if e50.iloc[-1] > e50.iloc[-2]:
            bias = "LONG"
        elif e50.iloc[-1] < e50.iloc[-2]:
            bias = "SHORT"
    
    disp_ok = False
    for i in range(1, config.ONEH_DISP_LOOKBACK+1):
        rng = float(h.iloc[-i] - l.iloc[-i])
        body = abs(float(c.iloc[-i] - o.iloc[-i]))
        if rng > 0 and (body/rng) >= config.ONEH_DISP_BODY_MIN:
            disp_ok = True
            break
    
    adx1h = float(adx(h, l, c, 14).iloc[-1])
    trend_ok = adx1h >= config.ADX_TREND_MIN
    
    return bias, disp_ok, adx1h, trend_ok

def htf_bias_only(df1h):
    """
    Sadece 1 saatlik verilerden trend yönünü belirle.
    
    Args:
        df1h: 1 saatlik OHLC DataFrame'i
        
    Returns:
        str: "LONG", "SHORT" veya "NEUTRAL" olarak trend yönü
    """
    c = df1h["c"]
    e50 = ema(c, 50)
    
    if pd.isna(e50.iloc[-1]) or pd.isna(e50.iloc[-2]):
        return "NEUTRAL"
        
    return "LONG" if e50.iloc[-1] > e50.iloc[-2] else ("SHORT" if e50.iloc[-1] < e50.iloc[-2] else "NEUTRAL")