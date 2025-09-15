#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Trading Bot Ana Giriş Noktası
"""

import asyncio
import argparse
import sys
import os

# Python path'i düzenle
sys.path.insert(0, os.path.dirname(__file__))

from . import config
from .scanner import Scanner
from .utils import log, now_utc
from .exchange import Exchange


def parse_args():
    """
    Komut satırı argümanlarını ayrıştır.
    
    Returns:
        Namespace: Ayrıştırılan argümanlar
    """
    parser = argparse.ArgumentParser(description='KuCoin Trading Bot')
    
    parser.add_argument('--mode', '-m', 
                        choices=['aggressive', 'balanced', 'conservative'],
                        default=config.MODE,
                        help='Trading modu (default: %(default)s)')
    
    parser.add_argument('--scan-limit', '-l',
                        type=int, 
                        default=config.SCAN_LIMIT,
                        help='Taranacak maksimum sembol sayısı (default: %(default)s)')
    
    parser.add_argument('--reset-ai', '-r',
                        action='store_true',
                        help='AI modeli sıfırla')
    
    parser.add_argument('--test-telegram', '-t',
                        action='store_true',
                        help='Telegram entegrasyonunu test et ve çık')
                        
    parser.add_argument('--verbose', '-v',
                        action='store_true',
                        help='Detaylı günlük kaydı')
    
    args = parser.parse_args()
    return args


def configure_from_args(args):
    """
    Komut satırı argümanlarına göre konfigürasyonu ayarla.
    
    Args:
        args: Ayrıştırılmış argümanlar
    """
    if args.mode:
        config.MODE = args.mode
        
    if args.scan_limit:
        config.SCAN_LIMIT = args.scan_limit
        
    if args.verbose:
        config.VERBOSE_SCAN = True
        config.SHOW_SKIP_REASONS = True


async def test_telegram():
    """
    Telegram entegrasyonunu test et.
    """
    from .alerts import AlertManager
    
    log("Telegram bağlantısı test ediliyor...")
    exchange = Exchange()
    alert_mgr = AlertManager()
    alert_mgr.set_exchange(exchange)  # Exchange'i AlertManager'a bağla
    
    try:
        await alert_mgr.send_message("🔌 Bot bağlantı testi başarılı!")
        log("✅ Telegram testi başarılı!")
        return True
    except Exception as e:
        log(f"❌ Telegram testi başarısız: {e}")
        return False


async def main():
    """
    Ana program akışı.
    """
    args = parse_args()
    configure_from_args(args)
    
    log(f"Bot başlatılıyor | Mode: {config.MODE}")
    log(f"Bot zamanı: {now_utc()}")
    
    # AI sıfırlama
    if args.reset_ai:
        from .ai import reset_ai
        reset_ai()
        log("⚠️ AI modeli sıfırlandı.")
    
    # Telegram testi
    if args.test_telegram:
        success = await test_telegram()
        return
    
    # Exchange bağlantısını test et
    exchange = Exchange()
    syms = exchange.get_filtered_symbols()
    log(f"Exchange bağlantısı kuruldu. {len(syms)} adet sembol alındı.")
    
    # Ana tarama işlemini başlat
    scanner = Scanner()
    await scanner.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log("Bot durduruldu (CTRL+C)")
        sys.exit(0)
    except Exception as e:
        log(f"Kritik hata: {e}")
        sys.exit(1)