"""
Unit tests for data caching layer.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from src.data.models import OHLCV, DataInterval, Tick, Quote
from src.data.cache import DataCache, CacheEntry


class TestCacheEntry:
    """Test CacheEntry with TTL."""
    
    def test_cache_entry_not_expired(self):
        """Test that fresh entry is not expired."""
        entry = CacheEntry(data={'test': 'data'}, ttl_seconds=3600)
        assert not entry.is_expired()
    
    def test_cache_entry_expired(self):
        """Test that old entry is expired."""
        old_time = datetime.utcnow() - timedelta(hours=2)
        entry = CacheEntry(
            data={'test': 'data'},
            timestamp=old_time,
            ttl_seconds=3600
        )
        assert entry.is_expired()
    
    def test_cache_entry_age(self):
        """Test age calculation."""
        entry = CacheEntry(data={'test': 'data'}, ttl_seconds=3600)
        age = entry.age_seconds()
        assert 0 <= age < 1


class TestDataCache:
    """Test DataCache async operations."""
    
    @pytest.fixture
    async def cache(self):
        """Create cache instance for testing."""
        return DataCache(max_entries=100)
    
    @pytest.mark.asyncio
    async def test_cache_initialization(self):
        """Test cache initialization."""
        cache = DataCache(max_entries=1000)
        assert cache._max_entries == 1000
        assert len(cache._cache) == 0
    
    @pytest.mark.asyncio
    async def test_set_and_get_ohlcv(self):
        """Test setting and getting OHLCV data."""
        cache = DataCache()
        now = datetime.utcnow()
        
        candles = [
            OHLCV(
                timestamp=now,
                symbol='AAPL',
                interval=DataInterval.DAY_1,
                open=150.0,
                high=155.0,
                low=149.0,
                close=152.0,
                volume=1000000
            )
        ]
        
        # Set data
        await cache.set_ohlcv('AAPL', DataInterval.DAY_1, candles)
        
        # Get data
        result = await cache.get_ohlcv('AAPL', DataInterval.DAY_1)
        assert result is not None
        assert len(result) == 1
        assert result[0].symbol == 'AAPL'
    
    @pytest.mark.asyncio
    async def test_cache_miss(self):
        """Test cache miss for non-existent key."""
        cache = DataCache()
        result = await cache.get_ohlcv('NONEXISTENT', DataInterval.DAY_1)
        assert result is None
    
    @pytest.mark.asyncio
    async def test_cache_expiration(self):
        """Test that expired cache entries are not returned."""
        cache = DataCache()
        now = datetime.utcnow()
        
        candles = [
            OHLCV(
                timestamp=now,
                symbol='AAPL',
                interval=DataInterval.DAY_1,
                open=150.0,
                high=155.0,
                low=149.0,
                close=152.0,
                volume=1000000
            )
        ]
        
        # Set with very short TTL
        await cache.set_ohlcv('AAPL', DataInterval.DAY_1, candles, ttl_seconds=1)
        
        # Should be cached
        result = await cache.get_ohlcv('AAPL', DataInterval.DAY_1)
        assert result is not None
        
        # Wait for expiration
        await asyncio.sleep(1.1)
        
        # Should not be cached anymore
        result = await cache.get_ohlcv('AAPL', DataInterval.DAY_1)
        assert result is None
    
    @pytest.mark.asyncio
    async def test_set_and_get_quote(self):
        """Test quote caching."""
        cache = DataCache()
        
        quote = Quote(symbol='AAPL', price=150.5, bid=150.4, ask=150.6)
        
        await cache.set_quote(quote)
        result = await cache.get_quote('AAPL')
        
        assert result is not None
        assert result.symbol == 'AAPL'
        assert result.price == 150.5
    
    @pytest.mark.asyncio
    async def test_set_and_get_ticks(self):
        """Test tick data caching."""
        cache = DataCache()
        now = datetime.utcnow()
        
        ticks = [
            Tick(timestamp=now, symbol='AAPL', price=150.5),
            Tick(timestamp=now + timedelta(seconds=1), symbol='AAPL', price=150.6),
        ]
        
        await cache.set_tick('AAPL', ticks)
        result = await cache.get_tick('AAPL')
        
        assert result is not None
        assert len(result) == 2
    
    @pytest.mark.asyncio
    async def test_tick_limit(self):
        """Test tick limit parameter."""
        cache = DataCache()
        now = datetime.utcnow()
        
        ticks = [
            Tick(timestamp=now + timedelta(seconds=i), symbol='AAPL', price=150.0 + i*0.1)
            for i in range(100)
        ]
        
        await cache.set_tick('AAPL', ticks)
        result = await cache.get_tick('AAPL', limit=10)
        
        assert result is not None
        assert len(result) == 10
    
    @pytest.mark.asyncio
    async def test_clear_all(self):
        """Test clearing entire cache."""
        cache = DataCache()
        now = datetime.utcnow()
        
        candles = [
            OHLCV(
                timestamp=now,
                symbol='AAPL',
                interval=DataInterval.DAY_1,
                open=150.0,
                high=155.0,
                low=149.0,
                close=152.0,
                volume=1000000
            )
        ]
        
        await cache.set_ohlcv('AAPL', DataInterval.DAY_1, candles)
        await cache.set_ohlcv('GOOGL', DataInterval.DAY_1, candles)
        
        assert len(cache._cache) > 0
        cleared = await cache.clear()
        
        assert cleared > 0
        assert len(cache._cache) == 0
    
    @pytest.mark.asyncio
    async def test_clear_by_symbol(self):
        """Test clearing cache for specific symbol."""
        cache = DataCache()
        now = datetime.utcnow()
        
        candles = [
            OHLCV(
                timestamp=now,
                symbol='AAPL',
                interval=DataInterval.DAY_1,
                open=150.0,
                high=155.0,
                low=149.0,
                close=152.0,
                volume=1000000
            )
        ]
        
        await cache.set_ohlcv('AAPL', DataInterval.DAY_1, candles)
        await cache.set_ohlcv('GOOGL', DataInterval.DAY_1, candles)
        
        initial_size = len(cache._cache)
        cleared = await cache.clear('AAPL')
        
        assert cleared > 0
        assert len(cache._cache) < initial_size
        
        # AAPL should be gone
        result = await cache.get_ohlcv('AAPL', DataInterval.DAY_1)
        assert result is None
        
        # GOOGL should still be there
        result = await cache.get_ohlcv('GOOGL', DataInterval.DAY_1)
        assert result is not None
    
    @pytest.mark.asyncio
    async def test_cache_stats(self):
        """Test cache statistics."""
        cache = DataCache()
        now = datetime.utcnow()
        
        candles = [
            OHLCV(
                timestamp=now,
                symbol='AAPL',
                interval=DataInterval.DAY_1,
                open=150.0,
                high=155.0,
                low=149.0,
                close=152.0,
                volume=1000000
            )
        ]
        
        await cache.set_ohlcv('AAPL', DataInterval.DAY_1, candles)
        
        # One hit
        await cache.get_ohlcv('AAPL', DataInterval.DAY_1)
        
        # One miss
        await cache.get_ohlcv('NONEXISTENT', DataInterval.DAY_1)
        
        stats = cache.stats()
        
        assert stats['hits'] == 1
        assert stats['misses'] == 1
        assert stats['total_requests'] == 2
        assert stats['hit_rate_percent'] == 50.0
    
    @pytest.mark.asyncio
    async def test_cache_reset_stats(self):
        """Test resetting cache statistics."""
        cache = DataCache()
        
        # Create some activity
        await cache.get_ohlcv('AAPL', DataInterval.DAY_1)
        await cache.get_ohlcv('GOOGL', DataInterval.DAY_1)
        
        # Reset
        await cache.reset_stats()
        
        stats = cache.stats()
        assert stats['hits'] == 0
        assert stats['misses'] == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
