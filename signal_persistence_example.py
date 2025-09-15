#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Signal persistence örneği - bekleyen sinyalleri kalıcı hale getirmek için.
"""

import json
import time
from typing import Dict, Any
from pathlib import Path

class PersistentSignalStore:
    """Bekleyen sinyalleri dosyaya kaydeden ve yükleyen sınıf."""
    
    def __init__(self, storage_file: str = "pending_signals.json"):
        self.storage_file = Path(storage_file)
        self.pending_signals = {}
        self.load_signals()
    
    def load_signals(self):
        """Kaydedilmiş sinyalleri yükle."""
        if self.storage_file.exists():
            try:
                with open(self.storage_file, 'r') as f:
                    data = json.load(f)
                    self.pending_signals = data
                    print(f"📁 {len(self.pending_signals)} bekleyen sinyal yüklendi")
            except Exception as e:
                print(f"⚠️ Sinyal yükleme hatası: {e}")
                self.pending_signals = {}
    
    def save_signals(self):
        """Mevcut sinyalleri kaydet."""
        try:
            with open(self.storage_file, 'w') as f:
                json.dump(self.pending_signals, f, indent=2)
        except Exception as e:
            print(f"⚠️ Sinyal kaydetme hatası: {e}")
    
    def add_signal(self, symbol: str, signal_data: Dict[str, Any]):
        """Sinyal ekle ve kaydet."""
        self.pending_signals[symbol] = {
            **signal_data,
            'added_at': time.time()
        }
        self.save_signals()
        print(f"💾 {symbol} sinyali kaydedildi")
    
    def remove_signal(self, symbol: str):
        """Sinyali kaldır ve kaydet."""
        if symbol in self.pending_signals:
            del self.pending_signals[symbol]
            self.save_signals()
            print(f"🗑️ {symbol} sinyali kaldırıldı")
    
    def get_pending_signals(self) -> Dict[str, Any]:
        """Bekleyen sinyalleri getir."""
        return self.pending_signals.copy()
    
    def cleanup_old_signals(self, max_age_hours: float = 24):
        """Eski sinyalleri temizle."""
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600
        
        old_signals = []
        for symbol, data in self.pending_signals.items():
            if current_time - data.get('added_at', 0) > max_age_seconds:
                old_signals.append(symbol)
        
        for symbol in old_signals:
            self.remove_signal(symbol)
            
        if old_signals:
            print(f"🧹 {len(old_signals)} eski sinyal temizlendi")

# Kullanım örneği:
if __name__ == "__main__":
    store = PersistentSignalStore()
    
    # Sinyal ekle
    store.add_signal("BTC-USDT", {
        "side": "LONG",
        "entry": 45000,
        "sl": 44000,
        "score": 65
    })
    
    # Bekleyen sinyalleri göster
    pending = store.get_pending_signals()
    print("Bekleyen sinyaller:", pending)
    
    # Eski sinyalleri temizle
    store.cleanup_old_signals(max_age_hours=1)