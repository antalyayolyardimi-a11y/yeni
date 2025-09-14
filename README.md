# KuCoin Trading Bot

Otomatik kripto para ticareti için modüler trading bot sistemi.

## Özellikleri

- Çoklu strateji sistemi (Trend/Range, SMC, Momentum)
- Telegram bildirim entegrasyonu
- KuCoin borsası desteği
- Adaptif öğrenme ve auto-tuning sistemi
- Mini-AI (online logistic regression) desteği

## Proje Yapısı

```
tradingbot/
│
├── config.py          # Konfigürasyon parametreleri
├── utils.py           # Yardımcı fonksiyonlar
├── indicators.py      # Teknik göstergeler
├── exchange.py        # Borsa işlemleri (KuCoin)
├── scoring.py         # Sinyal skorlama sistemi
├── ai.py              # AI ve adaptif öğrenme
├── alerts.py          # Telegram bildirimleri
├── scanner.py         # Ana tarama mantığı
├── main.py            # Ana giriş noktası
│
└── strategies/        # Strateji modülleri
    ├── __init__.py    # Paket tanımlaması
    ├── base.py        # Temel strateji sınıfı
    ├── trend_range.py # Trend/Range stratejisi
    ├── smc.py         # Smart Money Concept stratejisi
    └── momentum.py    # Momentum stratejisi
```

## Kurulum

1. Gerekli paketleri yükleyin:

```bash
pip install kucoin-python aiogram nest_asyncio pandas numpy
```

2. `config.py` içindeki Telegram token'ını ayarlayın:

```python
TELEGRAM_TOKEN = "YOUR_TELEGRAM_TOKEN"
```

## Kullanım

Bot'u başlatmak için:

```bash
python -m tradingbot.main
```

Farklı modlarda çalıştırmak için:

```bash
python -m tradingbot.main --mode aggressive
python -m tradingbot.main --mode balanced
python -m tradingbot.main --mode conservative
```

## Telegram Komutları

- `/start` - Bot'u başlat ve chat ID'yi kaydet
- `/mode <mod>` - Trading modunu değiştir (aggressive, balanced, conservative)
- `/analiz <sembol>` - Belirli bir sembol için teknik analiz yap
- `/aistats` - AI istatistiklerini görüntüle
- `/aireset` - AI modelini sıfırla

## Stratejiler

### Trend/Range Stratejisi
- Trend modu: Donchian kırılımı + retest/momentum
- Range modu: BB bantları içinde sıçrama/dönüş

### SMC Stratejisi
- Likidite süpürme → CHOCH (Change of Character)
- FVG (Fair Value Gap) ve OTE (Optimal Trade Entry) ile giriş

### Momentum Stratejisi
- DC/EMA kırılımları + momentum onayı
- Erken tetikleme (pre-break) ile kırılım öncesi fırsatları yakala

## Geliştirme

Yeni stratejiler eklemek için `strategies/` dizininde yeni bir dosya oluşturun ve `base.py` içindeki `BaseStrategy` sınıfını genişletin.