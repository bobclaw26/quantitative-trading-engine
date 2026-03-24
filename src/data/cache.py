"""
Caching layer for market data using in-memory storage with TTL support.
Designed for high-speed access with configurable expiration.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

from models import OHLCV, DataInterval, Tick, Quote

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Single cache entry with TTL support."""
    data: Any
    timestamp: datetime = field(default_factory=datetime.utcnow)
    ttl_seconds: int = 3600  # Default 1 hour
    
    def is_expired(self) -> bool:
        """Check if cache entry has expired."""
        age = (datetime.utcnow() - self.timestamp).total_seconds()
        return age > self.ttl_seconds
    
    def age_seconds(self) -> float:
        """Get age of cache entry in seconds."""
        return (datetime.utcnow() - self.timestamp).total_seconds()


class DataCache:
    """
    In-memory cache for OHLCV and tick data with TTL support.
    Thread-safe with async/await support.
    """
    
    # Default TTLs (seconds)
    DEFAULT_OHLCV_TTL = 3600  # 1 hour for 1-day candles
    DEFAULT_TICK_TTL = 300     # 5 minutes for tick data
    DEFAULT_QUOTE_TTL = 60     # 1 minute for quotes
    INTRADAY_TTL = 900         # 15 minutes for intraday candles
    
    def __init__(self, max_entries: int = 10000):
        """
        Initialize cache.
        
        Args:
            max_entries: Maximum number of entries before cleanup
        """
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = asyncio.Lock()
        self._max_entries = max_entries
        self._hits = 0
        self._misses = 0
    
    def _make_key(self, symbol: str, interval: DataInterval, 
                  start_date: Optional[datetime] = None) -> str:
        """Generate cache key from parameters."""
        if start_date:
            return f"{symbol}:{interval.value}:{start_date.isoformat()}"
        return f"{symbol}:{interval.value}"
    
    async def get_ohlcv(self, symbol: str, interval: DataInterval,
                       start_date: Optional[datetime] = None) -> Optional[List[OHLCV]]:
        """
        Retrieve OHLCV data from cache.
        
        Args:
            symbol: Trading symbol
            interval: Data interval
            start_date: Optional start date for range queries
            
        Returns:
            List of OHLCV data or None if not found/expired
        """
        key = self._make_key(symbol, interval, start_date)
        
        async with self._lock:
            if key not in self._cache:
                self._misses += 1
                return None
            
            entry = self._cache[key]
            if entry.is_expired():
                del self._cache[key]
                self._misses += 1
                return None
            
            self._hits += 1
            logger.debug(f"Cache hit for {key} (age: {entry.age_seconds():.1f}s)")
            return entry.data
    
    async def set_ohlcv(self, symbol: str, interval: DataInterval,
                       data: List[OHLCV], ttl_seconds: Optional[int] = None,
                       start_date: Optional[datetime] = None) -> None:
        """
        Store OHLCV data in cache.
        
        Args:
            symbol: Trading symbol
            interval: Data interval
            data: List of OHLCV candles
            ttl_seconds: Time-to-live in seconds (None for default)
            start_date: Optional start date for range queries
        """
        key = self._make_key(symbol, interval, start_date)
        
        # Determine TTL based on interval
        if ttl_seconds is None:
            if interval in (DataInterval.MINUTE_1, DataInterval.MINUTE_5, 
                          DataInterval.MINUTE_15, DataInterval.MINUTE_30):
                ttl_seconds = self.INTRADAY_TTL
            else:
                ttl_seconds = self.DEFAULT_OHLCV_TTL
        
        async with self._lock:
            # Check cache size and cleanup if needed
            if len(self._cache) >= self._max_entries:
                await self._cleanup_expired()
            
            entry = CacheEntry(data=data, ttl_seconds=ttl_seconds)
            self._cache[key] = entry
            logger.debug(f"Cached {len(data)} candles for {key} (TTL: {ttl_seconds}s)")
    
    async def get_quote(self, symbol: str) -> Optional[Quote]:
        """
        Retrieve quote from cache.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Quote object or None if not found/expired
        """
        key = f"quote:{symbol}"
        
        async with self._lock:
            if key not in self._cache:
                self._misses += 1
                return None
            
            entry = self._cache[key]
            if entry.is_expired():
                del self._cache[key]
                self._misses += 1
                return None
            
            self._hits += 1
            return entry.data
    
    async def set_quote(self, quote: Quote, ttl_seconds: int = DEFAULT_QUOTE_TTL) -> None:
        """
        Store quote in cache.
        
        Args:
            quote: Quote object
            ttl_seconds: Time-to-live in seconds
        """
        key = f"quote:{quote.symbol}"
        
        async with self._lock:
            if len(self._cache) >= self._max_entries:
                await self._cleanup_expired()
            
            entry = CacheEntry(data=quote, ttl_seconds=ttl_seconds)
            self._cache[key] = entry
            logger.debug(f"Cached quote for {quote.symbol} (TTL: {ttl_seconds}s)")
    
    async def get_tick(self, symbol: str, limit: int = 100) -> Optional[List[Tick]]:
        """
        Retrieve tick data from cache.
        
        Args:
            symbol: Trading symbol
            limit: Maximum number of ticks to return
            
        Returns:
            List of Tick objects or None if not found/expired
        """
        key = f"ticks:{symbol}"
        
        async with self._lock:
            if key not in self._cache:
                self._misses += 1
                return None
            
            entry = self._cache[key]
            if entry.is_expired():
                del self._cache[key]
                self._misses += 1
                return None
            
            self._hits += 1
            data = entry.data
            return data[-limit:] if len(data) > limit else data
    
    async def set_tick(self, symbol: str, ticks: List[Tick], 
                      ttl_seconds: int = DEFAULT_TICK_TTL) -> None:
        """
        Store tick data in cache.
        
        Args:
            symbol: Trading symbol
            ticks: List of Tick objects
            ttl_seconds: Time-to-live in seconds
        """
        key = f"ticks:{symbol}"
        
        async with self._lock:
            if len(self._cache) >= self._max_entries:
                await self._cleanup_expired()
            
            entry = CacheEntry(data=ticks, ttl_seconds=ttl_seconds)
            self._cache[key] = entry
            logger.debug(f"Cached {len(ticks)} ticks for {symbol}")
    
    async def clear(self, symbol: Optional[str] = None) -> int:
        """
        Clear cache entries.
        
        Args:
            symbol: If provided, clear only entries for this symbol.
                   If None, clear entire cache.
                   
        Returns:
            Number of entries cleared
        """
        async with self._lock:
            if symbol is None:
                count = len(self._cache)
                self._cache.clear()
                return count
            
            # Clear entries for specific symbol
            keys_to_delete = [k for k in self._cache.keys() 
                            if symbol in k]
            count = len(keys_to_delete)
            for key in keys_to_delete:
                del self._cache[key]
            
            logger.info(f"Cleared {count} cache entries for {symbol}")
            return count
    
    async def _cleanup_expired(self) -> int:
        """
        Remove expired entries from cache.
        
        Returns:
            Number of entries removed
        """
        expired_keys = [k for k, v in self._cache.items() 
                       if v.is_expired()]
        
        for key in expired_keys:
            del self._cache[key]
        
        if expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
        
        return len(expired_keys)
    
    def stats(self) -> dict:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache stats
        """
        total_requests = self._hits + self._misses
        hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0
        
        return {
            'size': len(self._cache),
            'max_entries': self._max_entries,
            'hits': self._hits,
            'misses': self._misses,
            'total_requests': total_requests,
            'hit_rate_percent': hit_rate,
        }
    
    async def reset_stats(self) -> None:
        """Reset cache statistics."""
        self._hits = 0
        self._misses = 0


# Global cache instance
_cache = DataCache()


async def get_global_cache() -> DataCache:
    """Get the global cache instance."""
    return _cache
