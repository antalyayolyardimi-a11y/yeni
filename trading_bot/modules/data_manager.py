import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
import logging
import requests
import time
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class DataManager:
    """Manage market data fetching and caching"""
    
    def __init__(self):
        self.cache = {}
        self.cache_expiry = {}
        self.cache_duration = 60  # Cache for 1 minute
        
    def get_market_data(self, symbol: str, timeframe: str = '15m', limit: int = 100) -> Optional[pd.DataFrame]:
        """Get market data for a symbol"""
        try:
            # Check cache first
            cache_key = f"{symbol}_{timeframe}_{limit}"
            if self._is_cache_valid(cache_key):
                logger.debug(f"Returning cached data for {symbol}")
                return self.cache[cache_key]
            
            # Fetch new data
            data = self._fetch_market_data(symbol, timeframe, limit)
            if data is not None:
                self._cache_data(cache_key, data)
            
            return data
            
        except Exception as e:
            logger.error(f"Error getting market data for {symbol}: {str(e)}")
            return None
    
    def _fetch_market_data(self, symbol: str, timeframe: str, limit: int) -> Optional[pd.DataFrame]:
        """Fetch market data from exchange API"""
        try:
            # Simulate market data for demo purposes
            # In real implementation, this would connect to KuCoin API
            logger.info(f"Fetching market data for {symbol}")
            
            # Generate sample OHLCV data
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=limit)
            
            # Create time series
            time_range = pd.date_range(start=start_time, end=end_time, freq='15min')[:limit]
            
            # Generate realistic price data with some randomness
            base_price = 100.0
            if 'BTC' in symbol:
                base_price = 45000.0
            elif 'ETH' in symbol:
                base_price = 3000.0
            elif 'USDT' in symbol:
                base_price = 1.0
            
            # Generate OHLCV data with random walk
            np.random.seed(hash(symbol) % 2**32)  # Consistent random data per symbol
            
            price_changes = np.random.normal(0, 0.01, len(time_range))  # 1% volatility
            prices = [base_price]
            
            for change in price_changes[1:]:
                new_price = prices[-1] * (1 + change)
                prices.append(max(new_price, base_price * 0.5))  # Prevent negative prices
            
            # Create OHLCV data
            data = []
            for i, timestamp in enumerate(time_range):
                price = prices[i]
                volatility = abs(price_changes[i]) * 2
                
                high = price * (1 + volatility * 0.5)
                low = price * (1 - volatility * 0.5)
                open_price = prices[i-1] if i > 0 else price
                close_price = price
                volume = np.random.uniform(1000, 10000)
                
                data.append({
                    'timestamp': timestamp,
                    'open': open_price,
                    'high': high,
                    'low': low,
                    'close': close_price,
                    'volume': volume
                })
            
            df = pd.DataFrame(data)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.set_index('timestamp')
            
            logger.debug(f"Generated {len(df)} candles for {symbol}")
            return df
            
        except Exception as e:
            logger.error(f"Error fetching data for {symbol}: {str(e)}")
            return None
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached data is still valid"""
        if cache_key not in self.cache:
            return False
        
        if cache_key not in self.cache_expiry:
            return False
        
        return datetime.now() < self.cache_expiry[cache_key]
    
    def _cache_data(self, cache_key: str, data: pd.DataFrame):
        """Cache market data"""
        self.cache[cache_key] = data.copy()
        self.cache_expiry[cache_key] = datetime.now() + timedelta(seconds=self.cache_duration)
    
    def clear_cache(self):
        """Clear all cached data"""
        self.cache.clear()
        self.cache_expiry.clear()
        logger.info("Market data cache cleared")
    
    def get_cache_info(self) -> Dict[str, Any]:
        """Get cache information"""
        valid_entries = sum(1 for key in self.cache.keys() if self._is_cache_valid(key))
        
        return {
            'total_entries': len(self.cache),
            'valid_entries': valid_entries,
            'expired_entries': len(self.cache) - valid_entries,
            'cache_duration': self.cache_duration
        }
    
    def get_symbol_list(self) -> List[str]:
        """Get list of available trading symbols"""
        # This would normally come from exchange API
        return [
            'BTC/USDT', 'ETH/USDT', 'LTC/USDT', 'XRP/USDT', 'ADA/USDT',
            'DOT/USDT', 'LINK/USDT', 'AVAX/USDT', 'UNI/USDT', 'SHIB/USDT',
            'BCH/USDT', 'PEPE/USDT', 'DOGE/USDT', 'HYPE/USDT', 'MATIC/USDT',
            'SOL/USDT', 'BNB/USDT', 'TRX/USDT', 'ATOM/USDT', 'FTM/USDT'
        ]