#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Sinyal doğrulama sistemi test scripti.
"""

import asyncio
import time
from tradingbot.exchange import Exchange
from tradingbot.signal_validator import SignalValidator
from tradingbot.utils import log

async def test_signal_validation():
    """
    Sinyal doğrulama sistemini test et.
    """
    exchange = Exchange()
    validator = SignalValidator(exchange)
    
    # Test sinyali oluştur
    test_signal = {
        "symbol": "BTC-USDT",
        "side": "LONG", 
        "entry": 50000.0,
        "sl": 49000.0,
        "tps": (51000.0, 52000.0, 53000.0),
        "score": 72.5,
        "reason": "Test sinyali - Trend kırılımı",
        "regime": "TREND"
    }
    
    log("🧪 Test sinyali oluşturuluyor...")
    
    # Sinyali havuza ekle
    signal_id = validator.add_signal_to_pool(test_signal)
    log(f"✅ Sinyal havuza eklendi: {signal_id}")
    
    # 30 saniye boyunca doğrulama sürecini takip et
    for i in range(6):
        log(f"\n--- Test döngüsü {i+1}/6 ---")
        
        # Doğrulama yap
        confirmed = validator.validate_pending_signals()
        
        if confirmed:
            log(f"🎯 Sinyal ONAYLANDI! {len(confirmed)} adet")
            for signal in confirmed:
                log(f"   {signal['symbol']} {signal['side']} - Skor: {signal['score']}")
            break
        
        # Durum özeti
        status = validator.get_status_summary()
        log(f"📊 Bekleyen: {status['active_pending']}, Toplam: {status['total_pending']}")
        
        if status['active_pending'] == 0:
            log("❌ Tüm sinyaller iptal edildi veya tamamlandı")
            break
            
        # 5 saniye bekle
        await asyncio.sleep(5)
    
    log("🏁 Test tamamlandı!")

if __name__ == "__main__":
    asyncio.run(test_signal_validation())