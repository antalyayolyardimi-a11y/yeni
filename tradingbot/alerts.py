#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Telegram bildirimleri ve mesajlaşma sistemi.
"""

import time
import math
import pandas as pd
from typing import Dict, Any, Optional, List, Union

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

from . import config
from .utils import log, fmt
from .indicators import (
    atr_wilder, bollinger, adx, rsi, ema, body_strength, 
    donchian, swing_high, swing_low, htf_gate_and_bias
)

class AlertManager:
    def __init__(self):
        """Telegram bot ve ilgili değişkenleri başlat."""
        self.bot = Bot(token=config.TELEGRAM_TOKEN)
        self.dp = Dispatcher()
        self.cached_chat_id = None
        self.signals_store = {}
        self.sid_counter = 0
        
        # Komutları kaydet
        self._register_commands()
    
    def _register_commands(self):
        """Telegram komutlarını kaydet."""
        self.dp.message(Command("start"))(self.start_handler)
        self.dp.message(Command("mode"))(self.mode_handler)
        self.dp.message(Command("aistats"))(self.ai_stats_cmd)
        self.dp.message(Command("aireset"))(self.ai_reset_cmd)
        self.dp.message(Command("analiz"))(self.analiz_cmd)
    
    async def start_handler(self, m: Message):
        """
        /start komutuna yanıt ver.
        
        Args:
            m: Telegram mesajı
        """
        self.cached_chat_id = m.chat.id
        
        await m.answer(
            "✅ Bot hazır.\n"
            f"Mode: *{config.MODE}* (ATR_STOP_MULT={config.ATR_STOP_MULT})\n"
            "• 5 dakikada bir tarar, sinyaller 15m grafiğe göre üretilir.\n"
            "• Komutlar: /mode | /analiz <Sembol> | /aistats | /aireset",
            parse_mode="Markdown"
        )
        
        return {"cached_chat_id": self.cached_chat_id}
    
    async def mode_handler(self, m: Message):
        """
        /mode komutuna yanıt ver ve modu değiştir.
        
        Args:
            m: Telegram mesajı
        """
        if m.text is None:
            await m.answer("Geçersiz komut.")
            return None
            
        parts = m.text.strip().split()
        if len(parts) < 2:
            await m.answer("Kullanım: /mode aggressive | balanced | conservative")
            return None
            
        target = parts[1].lower()
        if target not in ("aggressive", "balanced", "conservative"):
            await m.answer("Geçersiz mod. Seçenekler: aggressive | balanced | conservative")
            return None
        
        # Mode değişimini arayüze bildir
        await m.answer(
            f"⚙️ Mode: *{target}*\n"
            f"MinScore={config.MODE_CONFIGS[target]['BASE_MIN_SCORE']}, "
            f"ADXmin={config.MODE_CONFIGS[target]['ADX_TREND_MIN']}, "
            f"BWmax={config.MODE_CONFIGS[target]['BWIDTH_RANGE']}, "
            f"VolMin≈{config.MODE_CONFIGS[target]['MIN_VOLVALUE_USDT']}, "
            f"ATR_STOP_MULT={config.MODE_CONFIGS[target]['ATR_STOP_MULT']}",
            parse_mode="Markdown"
        )
        
        # Yeni modu döndür (ana uygulama tarafından işlenecek)
        return {"new_mode": target}
    
    async def ai_stats_cmd(self, m: Message):
        """
        /aistats komutuna yanıt ver.
        
        Args:
            m: Telegram mesajı
        """
        # AI istatistiklerini almak için callback kullanılacak
        # (get_ai_stats fonksiyonu scanner.py'da bu amaçla çağrılacak)
        from .ai import get_ai_stats
        
        if not config.AI_ENABLED:
            await m.answer("AI kapalı.")
            return None
        
        stats = get_ai_stats()
        lines = [f"AI seen: #{stats['seen']} | bias={stats['bias']:.3f}"]
        
        for k in sorted(stats['weights'].keys()):
            lines.append(f"{k:14s}: {stats['weights'][k]: .3f}")
        
        await m.answer("```\n" + "\n".join(lines) + "\n```", parse_mode="Markdown")
        return None
    
    async def ai_reset_cmd(self, m: Message):
        """
        /aireset komutuna yanıt ver.
        
        Args:
            m: Telegram mesajı
        """
        # AI resetleme isteğini ana uygulamaya ilet
        await m.answer("AI ağırlıkları sıfırlandı.")
        return {"reset_ai": True}
    
    async def analiz_cmd(self, m: Message, exchange):
        """
        /analiz komutuna yanıt ver.
        
        Args:
            m: Telegram mesajı
            exchange: Exchange nesnesi
        """
        if m.text is None:
            await m.answer("Geçersiz komut.")
            return None
            
        parts = m.text.strip().split()
        if len(parts) < 2:
            await m.answer("Kullanım: /analiz WIFUSDT veya /analiz WIF-USDT")
            return None
            
        raw = parts[1].upper()
        norm = exchange.normalize_symbol_to_kucoin(raw)
        
        if not norm:
            await m.answer(f"❗ '{raw}' KuCoin'de bulunamadı. Örn: WIFUSDT → WIF-USDT")
            return None
            
        await m.answer(f"⏳ Analiz ediliyor: {norm}")
        
        try:
            text = self._analyze_symbol_text(norm, exchange)
            await m.answer(text, parse_mode="Markdown")
        except Exception as e:
            await m.answer(f"Analiz hatası ({norm}): {e}")
            
        return None
    
    def human_reason_text(self, sig: Dict[str, Any]) -> str:
        """
        Sinyal için insan tarafından okunabilir bir neden metni oluştur.
        
        Args:
            sig: Sinyal verisi
            
        Returns:
            str: İnsan tarafından okunabilir neden metni
        """
        r = sig.get("reason", "")
        regime = sig.get("regime", "-")
        
        if regime == "TREND":
            return "1H trend yönünde kırılım; retest veya güçlü momentum teyidi"
        if regime == "RANGE":
            return "Dar bantta false-break sonrası içeri dönüş + güçlü mum + hacim"
        if regime == "SMC":
            return "Likidite süpürme → CHOCH; FVG/OTE bölgesinden dönüş"
        if regime == "MO":
            return "Momentum + DC/EMA kırılımı"
        if regime == "PREMO":
            return "Erken tetik: DC kırılımına çok yakın + momentum onayı"
        if regime == "FALLBACK":
            return "BB dışı taşma sonrası dönüş (FBB)"
            
        return r or "-"
    
    async def send_signal(self, sig: Dict[str, Any]) -> bool:
        """
        Telegram üzerinden sinyal mesajı gönder.
        
        Args:
            sig: Gönderilecek sinyal verisi
            
        Returns:
            bool: Başarılıysa True, değilse False
        """
        if self.cached_chat_id is None:
            log("Chat yok → /start bekleniyor.")
            return False
            
        # Sinyali depola
        sid = str(self.sid_counter)
        self.sid_counter += 1
        self.signals_store[sid] = {"sig": sig, "ts": time.time()}
        
        t1, t2, t3 = sig["tps"]
        
        # Ek bilgileri hesapla
        rr1 = ((t1 - sig["entry"]) / max(1e-9, sig["entry"] - sig["sl"])) if sig["side"] == "LONG" else ((sig["entry"] - t1) / max(1e-9, sig["sl"] - sig["entry"]))
        ex = sig.get("_explain", {})
        reason_text = self.human_reason_text(sig)
        htf = ex.get("b1h", "-")
        
        # Mesaj başlığı
        title = f"🔔 {sig['symbol']} • {sig['side']} • {sig.get('regime','-')} • Mode: {config.MODE}"
        
        # Seviyeler bölümü
        levels = (
            f"• Entry : `{fmt(sig['entry'])}`\n"
            f"• SL    : `{fmt(sig['sl'])}`\n"
            f"• TP1   : `{fmt(t1)}`\n"
            f"• TP2   : `{fmt(t2)}`\n"
            f"• TP3   : `{fmt(t3)}`"
        )
        
        # Kısa özet
        quick = f"• 1H Bias: *{htf}*\n• Neden: {reason_text}\n• R (TP1'e): *{rr1:.2f}*"
        
        # Notlar
        notes = (
            "- *SL (Stop Loss)*: Zarar durdur.\n"
            "- *TP (Take Profit)*: Kar al seviyeleri.\n"
            "- *R*: ATR_STOP_MULT × ATR; *1.0R* = SL mesafesi."
        )
        
        # Tam mesaj
        text = (
            f"*{title}*\n\n"
            f"*Özet*\n{quick}\n\n"
            f"*Seviyeler*\n{levels}\n\n"
            f"*Notlar*\n{notes}"
        )
        
        try:
            await self.bot.send_message(chat_id=self.cached_chat_id, text=text, parse_mode="Markdown")
            return True
        except (TelegramBadRequest, TelegramForbiddenError) as e:
            log("Telegram:", e)
            return False
    
    async def send_message(self, text: str, parse_mode: Optional[str] = None) -> bool:
        """
        Telegram üzerinden genel bir mesaj gönder.
        
        Args:
            text: Gönderilecek mesaj metni
            parse_mode: Mesajın format tipi (Markdown, HTML, vb.)
            
        Returns:
            bool: Başarılıysa True, değilse False
        """
        if self.cached_chat_id is None:
            log("Chat yok → /start bekleniyor.")
            return False
            
        try:
            await self.bot.send_message(chat_id=self.cached_chat_id, text=text, parse_mode=parse_mode)
            return True
        except (TelegramBadRequest, TelegramForbiddenError) as e:
            log("Telegram:", e)
            return False
    
    def _analyze_symbol_text(self, symbol: str, exchange) -> str:
        """
        Sembol için analiz metni oluştur.
        
        Args:
            symbol: Analiz edilecek sembol
            exchange: Exchange nesnesi
            
        Returns:
            str: Analiz metni
        """
        df15 = exchange.get_ohlcv(symbol, config.TF_LTF, config.LOOKBACK_LTF)
        df1h = exchange.get_ohlcv(symbol, config.TF_HTF, config.LOOKBACK_HTF)
        
        if df15 is None or len(df15) < 80 or df1h is None or len(df1h) < 60:
            return "Veri alınamadı ya da yetersiz."
        
        o, c, h, l, v = df15["o"], df15["c"], df15["h"], df15["l"], df15["v"]
        close = float(c.iloc[-1])
        
        rsi14 = float(rsi(c, 14).iloc[-1])
        adx15 = float(adx(h, l, c, 14).iloc[-1])
        atrv = float(atr_wilder(h, l, c, config.ATR_PERIOD).iloc[-1])
        atr_pct = atrv / (close + 1e-12)
        
        ma, bb_u, bb_l, bwidth, _ = bollinger(c, config.BB_PERIOD, config.BB_K)
        bw = float(bwidth.iloc[-1]) if pd.notna(bwidth.iloc[-1]) else float("nan")
        bbu = float(bb_u.iloc[-1])
        bbl = float(bb_l.iloc[-1])
        
        dc_hi, dc_lo = donchian(h, l, config.DONCHIAN_WIN)
        dchi = float(dc_hi.iloc[-1])
        dclo = float(dc_lo.iloc[-1])
        
        bias, disp_ok, adx1h, trend_ok = htf_gate_and_bias(df1h)
        
        sw_hi = float(swing_high(h, config.SWING_WIN))
        sw_lo = float(swing_low(l, config.SWING_WIN))
        
        regime = "TREND" if (trend_ok and disp_ok) else ("RANGE" if (not math.isnan(bw) and bw <= config.BWIDTH_RANGE) else "NEUTRAL")
        
        pos_bb = "Alt banda yakın" if close <= bbl * (1 + 0.001) else ("Üst banda yakın" if close >= bbu * (1 - 0.001) else "Band içi")
        pos_dc = "Üst kırılım yakın" if close >= dchi * (1 - 0.001) else ("Alt kırılım yakın" if close <= dclo * (1 + 0.001) else "Orta")
        
        # ATR+R örnek SL
        risk = config.ATR_STOP_MULT * atrv
        sl_long = close - risk
        sl_short = close + risk
        rr_hint = "ATR+R standardı: TP'ler (1.0R, 1.6R, 2.2R). R = ATR_STOP_MULT × ATR."
        
        txt = (
            f"📊 *{symbol}* — Teknik Analiz (15m + 1H)\n"
            f"• Fiyat: `{fmt(close)}` | ATR%≈`{atr_pct:.4f}` | BW≈`{bw:.4f}`\n"
            f"• RSI14(15m): `{rsi14:.1f}` | ADX(15m): `{adx15:.1f}`\n"
            f"• 1H Bias: *{bias}* | ADX(1H): `{adx1h:.1f}` | Trend_OK: *{str(trend_ok)}*\n"
            f"• BB Pozisyon: {pos_bb} | Donchian: {pos_dc}\n"
            f"• Donchian Üst/Alt: `{fmt(dchi)}` / `{fmt(dclo)}` | Swing H/L({config.SWING_WIN}): `{fmt(sw_hi)}` / `{fmt(sw_lo)}`\n"
            f"• Rejim Tahmini: *{regime}*\n\n"
            f"🎯 *Plan İpuçları*\n"
            f"- TREND gününde (ADX1H yüksek): kırılım + retest/momentum kovala.\n"
            f"- RANGE gününde: alt/üst banda sarkıp *içeri dönüş + güçlü mum + hacim* varsa bounce denenir.\n"
            f"- ATR+R Stop/TP: LONG SL `{fmt(sl_long)}` | SHORT SL `{fmt(sl_short)}`. {rr_hint}\n"
        )
        
        return txt