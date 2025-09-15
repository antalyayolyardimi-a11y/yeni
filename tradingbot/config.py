#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Konfigürasyon ayarları ve sabitler.
"""

# Trading parametreleri
TF_LTF = "15min"
TF_HTF = "1hour"
LOOKBACK_LTF = 320
LOOKBACK_HTF = 180

# Bot ayarları
SLEEP_SECONDS = 300
SYMBOL_CONCURRENCY = 8
SCAN_LIMIT = 1000  # Yüksek limit, pratikte tüm sembolleri tarar

# Çalışma modu ve ayarlar
MODE = "aggressive"
MIN_VOLVALUE_USDT = 2_000_000
BASE_MIN_SCORE = 42  # SMC V2 için çok daha makul
FALLBACK_MIN_SCORE = 45  # Daha düşük fallback
TOP_N_PER_SCAN = 3  # Artırıldı (2'den 3'e)
COOLDOWN_SEC = 1800
OPPOSITE_MIN_BARS = 2

# Telegram ayarları
TELEGRAM_BOT_TOKEN = "8484153893:AAEybdOXrMvpDEjAg-o2KiCFYWtDSL1PxH4"
TELEGRAM_CHAT_ID = None  # Bot otomatik tespit edecek

# Teknik analiz parametreleri
ADX_TREND_MIN = 18
ONEH_DISP_BODY_MIN = 0.55
ONEH_DISP_LOOKBACK = 2

BB_PERIOD = 20
BB_K = 2.0
BWIDTH_RANGE = 0.055
DONCHIAN_WIN = 20
BREAK_BUFFER = 0.0008
RETEST_TOL_ATR = 0.25

SWING_LEFT = 2
SWING_RIGHT = 2
SWEEP_EPS = 0.0005
BOS_EPS = 0.0005
FVG_LOOKBACK = 20
OTE_LOW, OTE_HIGH = 0.62, 0.79
SMC_REQUIRE_FVG = True

# SMC V2 (Smart Money Concepts) - 15M İçin GEVŞEK ama KALİTELİ
SMC_STRUCTURE_LOOKBACK = 30  # Daha kısa lookback (7.5 saat)
SMC_MIN_STRUCTURE_POINTS = 2  # Sadece 2 swing point yeterli
SMC_LIQUIDITY_BUFFER = 0.003  # %0.3 gevşek buffer 
SMC_RETEST_CANDLES = 5  # Daha uzun retest süresi (1.25 saat)
SMC_CONFIRMATION_STRENGTH = 0.45  # Daha gevşek onay mumu
SMC_OTE_RETEST_MIN = 0.3  # 30% minimum retest (gevşek)
SMC_OTE_RETEST_MAX = 0.85  # 85% maximum retest (çok gevşek)
SMC_VOLUME_FACTOR = 1.05  # Minimal volume gerekli

ATR_PERIOD = 14
SWING_WIN = 10
MAX_SL_ATRx = 2.0
MIN_SL_ATRx = 0.30
TPS_R = (1.0, 1.6, 2.2)

# ATR+R risk ayarları
USE_ATR_R_RISK = True
ATR_STOP_MULT = 1.2

# Momentum onay ayarları
MOMO_CONFIRM_MODE = "2of3"
MOMO_BODY_MIN = 0.50
MOMO_REL_VOL = 1.35
MOMO_NET_BODY_TH = 0.80

# Erken tetikleyici ayarları
EARLY_TRIGGERS_ON = True
PREBREAK_ATR_X = 0.40
EARLY_MOMO_BODY_MIN = 0.45
EARLY_REL_VOL = 1.20
EARLY_ADX_BONUS = 2.0

FALLBACK_ENABLE = False
FBB_EPS = 0.0003
FBB_ATR_MIN = 0.0010
FBB_ATR_MAX = 0.028

EVAL_BARS_AHEAD = 12
ADAPT_MIN_SAMPLES = 20
ADAPT_WINDOW = 60
ADAPT_UP_THRESH = 0.55
ADAPT_DN_THRESH = 0.35
ADAPT_STEP = 2
MIN_SCORE_FLOOR = 58
MIN_SCORE_CEIL = 78

PRINT_PREFIX = "📟"

# Log ayarları
VERBOSE_SCAN = True
SHOW_SYMBOL_LIST_AT_START = True
SHOW_SKIP_REASONS = True
CHUNK_PRINT = 20

# Scoring ayarları
SCORING_WEIGHTS = {
    "htf_align": 18.0,
    "adx_norm": 14.0,
    "ltf_momo": 10.0,
    "rr_norm": 0.0,  # RR puanı devre dışı
    "bw_adv": 5.0,
    "retest_or_fvg": 8.0,
    "atr_sweet": 3.0,
    "vol_pct": 8.0,
    "recent_penalty": -3.0,
}
SCORING_BASE = 20.0
PROB_CALIB_A = 0.10
PROB_CALIB_B = -7.0

# Auto-tuner ayarları
AUTO_TUNER_ON = True
WR_TARGET = 0.52
WIN_MIN_SAMPLES = 20
TUNE_WINDOW = 80
TUNE_COOLDOWN_SEC = 900

# Sınır korumaları
BOUNDS = {
    "BASE_MIN_SCORE": (56, 80),
    "ADX_TREND_MIN": (12, 26),
    "BWIDTH_RANGE": (0.045, 0.090),
    "VOL_MULT_REQ": (1.10, 1.80),
}

# Range hacim eşiği
VOL_MULT_REQ_GLOBAL = 1.40

# Adaptif gevşetme
EMPTY_LIMIT = 3
RELAX_STEP = 2
RELAX_MAX = 6
PENALTY_DECAY = 2

# Sinyal doğrulama sistemi
SIGNAL_VALIDATION_ENABLED = True
VALIDATION_TIMEOUT_SEC = 720   # 12 dakika (2 mum x 5dk + buffer)
VALIDATION_MIN_BARS = 2        # Minimum 2 mum analizi
VALIDATION_BODY_STRENGTH_MIN = 0.60  # Güçlü mum kriteri
VALIDATION_VOLUME_MULTIPLIER = 1.1   # Hacim çarpanı
VALIDATION_RSI_OVERBOUGHT = 75       # RSI aşırı alım
VALIDATION_RSI_OVERSOLD = 25         # RSI aşırı satım
# Ek filtre: 2 mum için ATR-normalize momentum eşiği (|Δclose|/ATR5 ≥ eşik)
VALIDATION_ATR_MOVE_MIN = 0.25  # aggressive: 0.20, balanced: 0.25, conservative: 0.30 öneri

# AI ayarları
AI_ENABLED = True
AI_LR = 0.02
AI_L2 = 1e-4
AI_INIT_BIAS = -2.0

# Telegram
TELEGRAM_TOKEN = "8484153893:AAEybdOXrMvpDEjAg-o2KiCFYWtDSL1PxH4"

# Mod konfigürasyonları
MODE_CONFIGS = {
    "aggressive": {
        "MIN_VOLVALUE_USDT": 700_000,
        "BASE_MIN_SCORE": 52,
        "FALLBACK_MIN_SCORE": 55,
        "TOP_N_PER_SCAN": 5,
        "COOLDOWN_SEC": 900,
        "ADX_TREND_MIN": 14,
        "ONEH_DISP_BODY_MIN": 0.45,
        "BWIDTH_RANGE": 0.080,
        "BREAK_BUFFER": 0.0006,
        "RETEST_TOL_ATR": 0.50,
        "SMC_REQUIRE_FVG": False,
        "FBB_ATR_MIN": 0.0007,
        "FBB_ATR_MAX": 0.030,
        "FALLBACK_ENABLE": False,
        "ATR_STOP_MULT": 1.0
    },
    "balanced": {
        "MIN_VOLVALUE_USDT": 2_000_000,
        "BASE_MIN_SCORE": 68,
        "FALLBACK_MIN_SCORE": 62,
        "TOP_N_PER_SCAN": 2,
        "COOLDOWN_SEC": 1800,
        "ADX_TREND_MIN": 18,
        "ONEH_DISP_BODY_MIN": 0.55,
        "BWIDTH_RANGE": 0.055,
        "BREAK_BUFFER": 0.0008,
        "RETEST_TOL_ATR": 0.25,
        "SMC_REQUIRE_FVG": True,
        "FBB_ATR_MIN": 0.0010,
        "FBB_ATR_MAX": 0.028,
        "FALLBACK_ENABLE": False,
        "ATR_STOP_MULT": 1.2
    },
    "conservative": {
        "MIN_VOLVALUE_USDT": 3_000_000,
        "BASE_MIN_SCORE": 72,
        "FALLBACK_MIN_SCORE": 65,
        "TOP_N_PER_SCAN": 2,
        "COOLDOWN_SEC": 2400,
        "ADX_TREND_MIN": 20,
        "ONEH_DISP_BODY_MIN": 0.60,
        "BWIDTH_RANGE": 0.045,
        "BREAK_BUFFER": 0.0012,
        "RETEST_TOL_ATR": 0.20,
        "SMC_REQUIRE_FVG": True,
        "FBB_ATR_MIN": 0.0012,
        "FBB_ATR_MAX": 0.020,
        "FALLBACK_ENABLE": False,
        "ATR_STOP_MULT": 1.5
    }
}

# ================== GLOBAL PARAMS (balanced+ varsayılan) ==================
TF_LTF              = "15min"
TF_HTF              = "1hour"
LOOKBACK_LTF        = 320
LOOKBACK_HTF        = 180

SLEEP_SECONDS       = 300       # 5 dk tarama
SYMBOL_CONCURRENCY  = 8
SCAN_LIMIT          = 260

# Orta-sıkı preset (balanced+)
MIN_VOLVALUE_USDT   = 2_000_000
BASE_MIN_SCORE      = 68
FALLBACK_MIN_SCORE  = 62
TOP_N_PER_SCAN      = 2
COOLDOWN_SEC        = 1800
OPPOSITE_MIN_BARS   = 2

ADX_TREND_MIN       = 18
ONEH_DISP_BODY_MIN  = 0.55
ONEH_DISP_LOOKBACK  = 2

BB_PERIOD           = 20
BB_K                = 2.0
BWIDTH_RANGE        = 0.055
DONCHIAN_WIN        = 20
BREAK_BUFFER        = 0.0008
RETEST_TOL_ATR      = 0.25

SWING_LEFT          = 2
SWING_RIGHT         = 2
SWEEP_EPS           = 0.0005
BOS_EPS             = 0.0005
FVG_LOOKBACK        = 20
OTE_LOW, OTE_HIGH   = 0.62, 0.79
SMC_REQUIRE_FVG     = True

ATR_PERIOD          = 14
SWING_WIN           = 10
MAX_SL_ATRx         = 2.0
MIN_SL_ATRx         = 0.30
TPS_R               = (1.0, 1.6, 2.2)

# ===== ATR+R risk ayarları =====
USE_ATR_R_RISK      = True      # SL/TP swing yerine ATR+R kullan
ATR_STOP_MULT       = 1.2       # balanced için varsayılan; mode'a göre değişecek

# ===== Momentum onay ayarları =====
# Seçenekler: "off", "strict3", "2of3", "net_body", "ema_rv", "hybrid"
MOMO_CONFIRM_MODE   = "2of3"
MOMO_BODY_MIN       = 0.50     # gövde/oran tabanı
MOMO_REL_VOL        = 1.35     # relatif hacim eşiği (v[-1] > 20MA * MOMO_REL_VOL)
MOMO_NET_BODY_TH    = 0.80     # net gövde eşiği (3 mumun işaretli gövde toplamı)

# ===== Erken tetikleyici (pre-break) =====
EARLY_TRIGGERS_ON   = True     # erken sinyal aç/kapat
PREBREAK_ATR_X      = 0.40     # Donchian kırılımına ATR*0.35 kadar yaklaşınca tetikle
EARLY_MOMO_BODY_MIN = 0.45     # erken modda gövde/menzil eşiği
EARLY_REL_VOL       = 1.20     # erken modda relatif hacim eşiği (20MA ×1.20)
EARLY_ADX_BONUS     = 2.0      # 1H ADX trend bölgesindeyse küçük skor bonusu

FALLBACK_ENABLE     = False
FBB_EPS             = 0.0003
FBB_ATR_MIN         = 0.0010
FBB_ATR_MAX         = 0.028

EVAL_BARS_AHEAD     = 12
ADAPT_MIN_SAMPLES   = 20
ADAPT_WINDOW        = 60
ADAPT_UP_THRESH     = 0.55
ADAPT_DN_THRESH     = 0.35
ADAPT_STEP          = 2
MIN_SCORE_FLOOR     = 58
MIN_SCORE_CEIL      = 78

PRINT_PREFIX        = "📟"

# ---- LOG AYARLARI ----
VERBOSE_SCAN = True
SHOW_SYMBOL_LIST_AT_START = True
SHOW_SKIP_REASONS = True
CHUNK_PRINT = 20

# ================== SCORING CONFIG ==================
SCORING_WEIGHTS = {
    "htf_align": 18.0,
    "adx_norm": 14.0,
    "ltf_momo": 10.0,
    "rr_norm": 16.0,      # RR puanı devre dışı (aşağıda 0'a çekildi)
    "bw_adv": 5.0,
    "retest_or_fvg": 8.0,
    "atr_sweet": 3.0,
    "vol_pct": 8.0,
    "recent_penalty": -3.0,
}
SCORING_BASE   = 20.0
PROB_CALIB_A   = 0.10
PROB_CALIB_B   = -7.0

# ===== SELF-LEARN / AUTO-TUNER =====
AUTO_TUNER_ON     = True
WR_TARGET         = 0.52     # hedef başarı oranı
WIN_MIN_SAMPLES   = 20
TUNE_WINDOW       = 80
TUNE_COOLDOWN_SEC = 900

# Boş tarama ve rahatlama ayarları
EMPTY_LIMIT       = 10       # Bu kadar boş tarama sonrasında skor düşürmeye başla
RELAX_MAX         = 20       # Maksimum rahatlama miktarı (skor puanı)
RELAX_STEP        = 2        # Her boş taramada düşürülecek skor
PENALTY_DECAY     = 0.85     # Ceza azalma katsayısı

# Sınır korumaları
BOUNDS = {
    "BASE_MIN_SCORE": (56, 80),
    "ADX_TREND_MIN":  (12, 26),
    "BWIDTH_RANGE":   (0.045, 0.090),
    "VOL_MULT_REQ":   (1.10, 1.80),
}

# RANGE hacim eşiği (tuner bunu oynatacak)
VOL_MULT_REQ_GLOBAL = 1.40

# RR puanlamasını kapat (SL'i manuel yöneteceksin)
SCORING_WEIGHTS["rr_norm"] = 0.0

# ===== TELEGRAM AYARLARI =====
TELEGRAM_TOKEN = "8484153893:AAEybdOXrMvpDEjAg-o2KiCFYWtDSL1PxH4"

# ===== MOD AYARLARI =====
MODE = "aggressive"

# ===== MINI AI (ONLINE LOGIT) =====
AI_ENABLED   = True
AI_LR        = 0.02
AI_L2        = 1e-4
AI_INIT_BIAS = -2.0

# KuCoin sembol normalizasyonu için tanınan quote'lar
KNOWN_QUOTES = ["USDT", "USDC", "BTC", "ETH", "TUSD", "EUR", "KCS"]

# ===== MOD KONFIGÜRASYONLARI =====
MODE_CONFIGS = {
    "aggressive": {
        "MIN_VOLVALUE_USDT": 700_000,
        "BASE_MIN_SCORE": 52,
        "FALLBACK_MIN_SCORE": 55,
        "TOP_N_PER_SCAN": 5,
        "COOLDOWN_SEC": 900,
        "ADX_TREND_MIN": 14,
        "ONEH_DISP_BODY_MIN": 0.45,
        "BWIDTH_RANGE": 0.080,
        "BREAK_BUFFER": 0.0006,
        "RETEST_TOL_ATR": 0.50,
        "SMC_REQUIRE_FVG": False,
        "FBB_ATR_MIN": 0.0007,
        "FBB_ATR_MAX": 0.030,
        "FALLBACK_ENABLE": False,
        "ATR_STOP_MULT": 1.0
    },
    "conservative": {
        "MIN_VOLVALUE_USDT": 3_000_000,
        "BASE_MIN_SCORE": 72,
        "FALLBACK_MIN_SCORE": 65,
        "TOP_N_PER_SCAN": 2,
        "COOLDOWN_SEC": 2400,
        "ADX_TREND_MIN": 20,
        "ONEH_DISP_BODY_MIN": 0.60,
        "BWIDTH_RANGE": 0.045,
        "BREAK_BUFFER": 0.0012,
        "RETEST_TOL_ATR": 0.20,
        "SMC_REQUIRE_FVG": True,
        "FBB_ATR_MIN": 0.0012,
        "FBB_ATR_MAX": 0.020,
        "FALLBACK_ENABLE": False,
        "ATR_STOP_MULT": 1.5
    },
    "balanced": {
        "MIN_VOLVALUE_USDT": 2_000_000,
        "BASE_MIN_SCORE": 52,  # Colab ile aynı
        "FALLBACK_MIN_SCORE": 50,
        "TOP_N_PER_SCAN": 3,
        "COOLDOWN_SEC": 1800,
        "ADX_TREND_MIN": 18,
        "ONEH_DISP_BODY_MIN": 0.55,
        "BWIDTH_RANGE": 0.055,
        "BREAK_BUFFER": 0.0008,
        "RETEST_TOL_ATR": 0.25,
        "SMC_REQUIRE_FVG": True,
        "FBB_ATR_MIN": 0.0010,
        "FBB_ATR_MAX": 0.028,
        "FALLBACK_ENABLE": False,
        "ATR_STOP_MULT": 1.2
    }
}

# Global state başlangıç değerleri
INITIAL_STATE = {
    "cached_chat_id": None,
    "last_signal_ts": {},
    "position_state": {},
    "signals_store": {},
    "sid_counter": 0,
    "dyn_MIN_SCORE": BASE_MIN_SCORE,
    "signals_history": [],
    "vol_pct_cache": {},
    "empty_scans": 0,
    "relax_acc": 0,
    "last_tune_ts": 0,
    "recent_signals": []
}