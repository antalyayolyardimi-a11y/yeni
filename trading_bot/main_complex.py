import asyncio
import logging
import signal
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

# Local imports
import config
from modules.market_data import DataManager
from modules.technical_analysis import TechnicalAnalysis
from modules.signal_generator import SignalGenerator
from modules.telegram_notifier import NotificationManager
from modules.signal_pool import SignalPool
from modules.trade_memory import TradeMemory
from modules.trade_tracker import TradeTracker

# Logging konfigürasyonu
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading_bot.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

class TradingBot:
    """Ana trading bot sınıfı"""
    
    def __init__(self):
        self.data_manager = DataManager()
        self.trade_memory = TradeMemory("trade_memory.json")
        self.technical_analysis = TechnicalAnalysis()
        self.signal_generator = SignalGenerator()
        )
        
        self.notification_manager = NotificationManager()
        
        # 🔥 Havuz Doğrulama Sistemi
        self.signal_pool = SignalPool(
            data_manager=self.data_manager,
            validation_candles=3,  # 3 mum kontrolü
            validation_interval=5  # 5dk aralık
        )
        
        # 🎯 İşlem Takip Sistemi
        self.trade_tracker = TradeTracker(self.data_manager, self.trade_memory, self.notification_manager)
        
        self.is_running = False
        self.trading_pairs = config.TRADING_PAIRS
        self.check_interval = config.CHECK_INTERVAL
        self.last_signals = {}  # Son sinyal zamanlarını takip et
        
        # Graceful shutdown için signal handler
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def signal_handler(self, signum, frame):
        """Güvenli kapatma için signal handler"""
        logger.info("Kapatma sinyali alındı, bot durduruluyor...")
        self.is_running = False
    
    async def initialize(self) -> bool:
        """Bot'u başlat ve gerekli kontrolleri yap"""
        logger.info("KuCoin Hızlı Trading Bot başlatılıyor...")
        
        # Telegram bağlantısını test et
        if not self.notification_manager.initialize_telegram():
            logger.error("Telegram bağlantısı başarısız!")
            return False
        
        if not await self.notification_manager.test_notifications():
            logger.error("Telegram test mesajı gönderilemedi!")
            return False
        
        # Market data bağlantısını test et
        test_data = await self.data_manager.get_data("BTC/USDT", "15m", 10)
        if test_data is None or test_data.empty:
            logger.error("Market data bağlantısı başarısız!")
            await self.notification_manager.notify_error("Market data bağlantısı kurulamadı!")
            return False
        
        # KuCoin'den top volume pairs al
        try:
            top_pairs = await self.data_manager.alternative_provider.get_top_volume_pairs(15)
            if top_pairs:
                # Config pairs ile birleştir
                all_pairs = list(set(config.TRADING_PAIRS + top_pairs))
                self.trading_pairs = all_pairs[:20]  # Max 20 coin
                logger.info(f"KuCoin top volume pairs eklendi: {len(self.trading_pairs)} coin")
            else:
                logger.warning("KuCoin top pairs alınamadı, config pairs kullanılıyor")
        except Exception as e:
            logger.error(f"Top pairs alma hatası: {e}")
        
        logger.info("Bot başarıyla başlatıldı!")
        await self.notification_manager.notify_status(
            f"🚀 KuCoin Hızlı Bot + Havuz Doğrulama aktif!\n"
            f"📊 15dk tarama → 5dk doğrulama sistemi\n"
            f"🎯 3 mum doğrulaması (%66 onay gerekli)\n"
            f"💰 İzlenen coinler: {len(self.trading_pairs)}\n"
            f"⏰ Kontrol: 5 dakikada bir\n\n"
            f"Coinler: {', '.join(self.trading_pairs[:10])}..."
        )
        return True
    
    async def analyze_pair(self, pair: str) -> Optional:
        """Bir coin çiftini hızlı analiz et"""
        try:
            # Market verilerini çek (15m)
            df = await self.data_manager.get_data(pair, config.TIMEFRAME, 100)
            if df is None or len(df) < 30:
                logger.warning(f"Yetersiz veri: {pair}")
                return None
            
            # Hızlı teknik analiz göstergelerini hesapla
            df_with_indicators = self.technical_analysis.get_all_fast_indicators(df)
            
            # Hızlı sinyal üret
            signal = self.signal_generator.generate_signal(pair, df_with_indicators)
            
            if signal and signal.signal_type != SignalType.NEUTRAL:
                smc_info = ""
                if hasattr(signal, 'indicators') and 'smc_score' in signal.indicators:
                    smc_info = f" [SMC: {signal.indicators['smc_score']}, Güven: {signal.indicators['smc_confidence']:.1f}%]"
                logger.info(f"⚡ Hızlı sinyal: {pair} - {signal.signal_type.value} - {signal.strength.value}{smc_info}")
                return signal
            
            return None
            
        except Exception as e:
            logger.error(f"Analiz hatası {pair}: {e}")
            logger.error(traceback.format_exc())
            return None
    
    async def process_signals(self) -> Tuple[List, List]:
        """15dk tarama sinyalleri ve havuz doğrulama sinyalleri"""
        scanning_signals = []
        confirmed_signals = []
        
        # 1. 15dk tarama sinyalleri (havuza eklenmek üzere)
        logger.info(f"📊 15dk tarama başlatılıyor: {len(self.trading_pairs)} coin...")
        
        # Paralel analiz için task'lar oluştur
        tasks = []
        for pair in self.trading_pairs:
            task = asyncio.create_task(self.analyze_pair(pair))
            tasks.append((pair, task))
        
        # Sonuçları bekle
        for pair, task in tasks:
            try:
                signal = await task
                if signal:
                    scanning_signals.append(signal)
            except Exception as e:
                logger.error(f"Task hatası {pair}: {e}")
        
        # 2. Havuz doğrulama döngüsü
        logger.info(f"🎯 Havuz doğrulama döngüsü başlatılıyor...")
        confirmed_signals = await self.signal_pool.process_validation_cycle()
        
        logger.info(f"📊 Tarama tamamlandı: {len(scanning_signals)} yeni sinyal")
        logger.info(f"🎯 Havuz doğrulama: {len(confirmed_signals)} onaylı sinyal")
        
        return scanning_signals, confirmed_signals
    
    async def send_signals(self, signals: List) -> int:
        """Havuz onaylı sinyalleri Telegram'a gönder ve AI sistemine ekle"""
        sent_count = 0
        
        for signal in signals:
            try:
                # Havuz onaylı sinyalleri spam koruması olmadan gönder
                success = await self.notification_manager.notify_signal(signal)
                if success:
                    sent_count += 1
                    self.last_signals[signal.pair] = signal.timestamp
                    
                    # 🧠 AI SİSTEMİNE EKLE: İşlem kaydı oluştur ve takibe başla
                    try:
                        # Güncel data al
                        df = await self.data_manager.get_data(signal.pair, "15m", 100)
                        
                        if df is not None and len(df) >= 50:
                            # Trade record oluştur (ATR seviyeli)
                            trade_record = self.trade_memory.create_trade_record(signal, df)
                            
                            if trade_record:
                                # Hafızaya ekle
                                self.trade_memory.add_trade(trade_record)
                                
                                # Takip sistemine ekle
                                self.trade_tracker.add_trade_to_track(trade_record)
                                
                                logger.info(f"🤖 AI sistemi: {signal.pair} işlemi takibe alındı!")
                                
                                # Seviye bilgilerini Telegram'a gönder
                                levels_message = f"""
🎯 **{signal.pair} SEVİYELERİ**

💰 **Entry:** ${trade_record.entry_price:.6f}
🛑 **Stop Loss:** ${trade_record.levels.stop_loss:.6f}
🎯 **TP1:** ${trade_record.levels.tp1:.6f}
🎯 **TP2:** ${trade_record.levels.tp2:.6f}  
🎯 **TP3:** ${trade_record.levels.tp3:.6f}

📊 **ATR:** {trade_record.levels.atr_value:.6f}
📈 **R/R Ratio:** {trade_record.levels.risk_reward_ratio:.2f}

🤖 **AI takibi başladı!** Sonuç otomatik bildirilecek.
"""
                                await self.notification_manager.send_message(levels_message)
                                
                    except Exception as ai_error:
                        logger.error(f"AI sistem hatası: {ai_error}")
                    
                else:
                    logger.error(f"Sinyal gönderilemedi: {signal.pair}")
                    
            except Exception as e:
                logger.error(f"Sinyal gönderim hatası: {e}")
        
        return sent_count
    
    def should_send_signal(self, signal) -> bool:
        """Sinyal gönderilmeli mi kontrol et (hızlı trading için spam koruması)"""
        if signal.pair not in self.last_signals:
            return True
        
        # Son sinyal zamanından bu yana geçen süre
        time_diff = signal.timestamp - self.last_signals[signal.pair]
        
        # 15 dakikada bir aynı coin için sinyal gönder (daha hızlı)
        return time_diff > timedelta(minutes=15)
    
    async def run_cycle(self):
        """Bir havuz doğrulama döngüsü çalıştır"""
        try:
            cycle_start = datetime.now()
            logger.info("🔄 Yeni havuz döngüsü başlıyor...")
            
            # 1. Sinyalleri analiz et (15dk + 5dk doğrulama)
            scanning_signals, confirmed_signals = await self.process_signals()
            
            # 2. Yeni tarama sinyallerini havuza ekle
            added_to_pool = 0
            for signal in scanning_signals:
                if self.signal_pool.add_signal_to_pool(signal):
                    added_to_pool += 1
            
            # 3. Havuz onaylı sinyalleri gönder
            sent_count = 0
            if confirmed_signals:
                sent_count = await self.send_signals(confirmed_signals)
                
                # Özet mesajı
                if sent_count > 0:
                    summary = f"✅ {sent_count} HAVUZ ONAYILI sinyal gönderildi!\n"
                    for signal in confirmed_signals[:sent_count]:
                        summary += f"• {signal.pair}: {signal.signal_type.value}\n"
                    await self.notification_manager.notify_status(summary)
            
            # 4. Havuz durumu
            pool_status = self.signal_pool.get_pool_status()
            
            # 5. Süresi geçen sinyalleri temizle
            self.signal_pool.clear_expired_signals()
            
            # Döngü özeti
            logger.info(f"📊 Yeni tarama: {len(scanning_signals)} sinyal")
            logger.info(f"🎯 Havuza eklenen: {added_to_pool}")
            logger.info(f"✅ Onaylı gönderilen: {sent_count}")
            logger.info(f"🔄 Havuzda bekleyen: {pool_status['total_signals']}")
            
            # Havuz durumu loglama
            if pool_status['total_signals'] > 0:
                status_summary = ", ".join([f"{status}: {count}" for status, count in pool_status['by_status'].items()])
                logger.info(f"📊 Havuz durumu: {status_summary}")
            
            # Döngü süresi
            cycle_duration = datetime.now() - cycle_start
            logger.info(f"🕐 Döngü tamamlandı: {cycle_duration.total_seconds():.2f}s")
            
        except Exception as e:
            logger.error(f"Döngü hatası: {e}")
            logger.error(traceback.format_exc())
            await self.notification_manager.notify_error(f"Havuz döngü hatası: {str(e)}")
    
    async def run(self):
        """Ana bot döngüsünü çalıştır"""
        if not await self.initialize():
            logger.error("Bot başlatılamadı!")
            return
        
        self.is_running = True
        error_count = 0
        max_errors = 5
        
        # 🎯 AI İşlem Takip Sistemini arka planda başlat
        tracking_task = asyncio.create_task(self.trade_tracker.start_tracking())
        logger.info("🤖 AI İşlem Takip Sistemi başlatıldı!")
        
        # AI performans özetini gönder
        performance_summary = self.trade_memory.get_performance_summary()
        await self.notification_manager.send_message(performance_summary)
        
        while self.is_running:
            try:
                await self.run_cycle()
                error_count = 0  # Başarılı döngü, hata sayacını sıfırla
                
                # Sonraki döngüye kadar bekle
                logger.info(f"Sonraki kontrol: {config.CHECK_INTERVAL} saniye...")
                await asyncio.sleep(config.CHECK_INTERVAL)
                
            except Exception as e:
                error_count += 1
                logger.error(f"Beklenmeyen hata (#{error_count}): {e}")
                logger.error(traceback.format_exc())
                
                await self.notification_manager.notify_error(
                    f"Bot hatası #{error_count}: {str(e)}"
                )
                
                if error_count >= max_errors:
                    logger.error(f"Çok fazla hata ({max_errors}), bot durduruluyor!")
                    await self.notification_manager.notify_error(
                        f"Bot çok fazla hata aldığı için durduruluyor! ({max_errors} hata)"
                    )
                    break
                
                # Hata sonrası daha uzun bekle
                await asyncio.sleep(60)
        
        await self.cleanup()
    
    async def cleanup(self):
        """Temizlik işlemleri"""
        logger.info("Bot kapatılıyor...")
        await self.notification_manager.notify_status("Bot durduruldu 🛑")
        self.data_manager.clear_cache()
        logger.info("Bot başarıyla kapatıldı")

async def main():
    """Ana fonksiyon"""
    bot = TradingBot()
    await bot.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot kullanıcı tarafından durduruldu")
    except Exception as e:
        logger.error(f"Bot başlatma hatası: {e}")
        logger.error(traceback.format_exc())