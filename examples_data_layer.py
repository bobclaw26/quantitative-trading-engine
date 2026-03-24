#!/usr/bin/env python3
"""
Data Layer Usage Examples

Demonstrates various ways to use the Twelve Data integration data layer:
1. Simple data fetching
2. Caching and statistics
3. Backfilling historical data
4. Real-time polling
5. Error handling
"""

import asyncio
import logging
import os
from datetime import datetime, timedelta
from src.data import (
    DataPipeline,
    TwelveDataClient,
    DataInterval,
    PipelineConfig,
    get_global_cache,
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# Example 1: Simple Data Fetching with Direct Client
# ============================================================================

async def example_1_simple_fetch():
    """Fetch daily AAPL data directly from API."""
    print("\n" + "="*70)
    print("Example 1: Simple Data Fetching")
    print("="*70)
    
    api_key = os.getenv('TWELVE_DATA_API_KEY')
    if not api_key:
        print("⚠️  TWELVE_DATA_API_KEY not set. Skipping example 1.")
        return
    
    client = TwelveDataClient(api_key=api_key)
    
    async with client:
        # Get last 20 daily candles for AAPL
        response = await client.get_timeseries(
            symbol='AAPL',
            interval=DataInterval.DAY_1,
            limit=20
        )
        
        if response.is_success():
            print(f"✅ Fetched {len(response.data)} candles\n")
            
            # Display last 5 candles
            for candle in response.data[-5:]:
                print(f"  {candle.timestamp.date()} | "
                      f"O:{candle.open:.2f} H:{candle.high:.2f} "
                      f"L:{candle.low:.2f} C:{candle.close:.2f} "
                      f"V:{candle.volume:,}")
        else:
            print(f"❌ Error: {response.error}")


# ============================================================================
# Example 2: Pipeline with Caching and Statistics
# ============================================================================

async def example_2_caching():
    """Demonstrate caching behavior and hit rate tracking."""
    print("\n" + "="*70)
    print("Example 2: Pipeline with Caching and Statistics")
    print("="*70)
    
    api_key = os.getenv('TWELVE_DATA_API_KEY')
    if not api_key:
        print("⚠️  TWELVE_DATA_API_KEY not set. Skipping example 2.")
        return
    
    pipeline = DataPipeline(api_key=api_key)
    await pipeline.initialize()
    
    try:
        # First fetch - cache miss
        print("\n1️⃣  First fetch (cache miss)...")
        start = datetime.utcnow()
        data1 = await pipeline.get_ohlcv('AAPL', DataInterval.DAY_1)
        elapsed1 = (datetime.utcnow() - start).total_seconds()
        print(f"   ✅ Got {len(data1)} candles in {elapsed1:.2f}s\n")
        
        # Second fetch - cache hit
        print("2️⃣  Second fetch (cache hit)...")
        start = datetime.utcnow()
        data2 = await pipeline.get_ohlcv('AAPL', DataInterval.DAY_1)
        elapsed2 = (datetime.utcnow() - start).total_seconds()
        print(f"   ✅ Got {len(data2)} candles in {elapsed2:.2f}s")
        print(f"   Speed improvement: {elapsed1/elapsed2:.1f}x faster 🚀\n")
        
        # Show cache statistics
        cache = await get_global_cache()
        stats = cache.stats()
        print("📊 Cache Statistics:")
        print(f"   Hits: {stats['hits']}")
        print(f"   Misses: {stats['misses']}")
        print(f"   Hit Rate: {stats['hit_rate_percent']:.1f}%")
        print(f"   Cache Size: {stats['size']} entries")
    
    finally:
        await pipeline.close()


# ============================================================================
# Example 3: Real-time Quote Fetching
# ============================================================================

async def example_3_quotes():
    """Fetch real-time quote data."""
    print("\n" + "="*70)
    print("Example 3: Real-time Quote Fetching")
    print("="*70)
    
    api_key = os.getenv('TWELVE_DATA_API_KEY')
    if not api_key:
        print("⚠️  TWELVE_DATA_API_KEY not set. Skipping example 3.")
        return
    
    client = TwelveDataClient(api_key=api_key)
    
    async with client:
        symbols = ['AAPL', 'GOOGL', 'MSFT']
        
        print(f"\nFetching quotes for: {', '.join(symbols)}\n")
        
        for symbol in symbols:
            quote = await client.get_quote(symbol)
            if quote:
                print(f"  {symbol}: ${quote.price:.2f}", end="")
                if quote.bid and quote.ask:
                    spread = quote.ask - quote.bid
                    print(f" (Bid: ${quote.bid:.2f}, Ask: ${quote.ask:.2f}, "
                          f"Spread: ${spread:.4f})")
                else:
                    print()
            else:
                print(f"  {symbol}: ❌ Failed to fetch")


# ============================================================================
# Example 4: Data Backfilling
# ============================================================================

async def example_4_backfill():
    """Backfill historical data for a symbol."""
    print("\n" + "="*70)
    print("Example 4: Historical Data Backfilling")
    print("="*70)
    
    api_key = os.getenv('TWELVE_DATA_API_KEY')
    if not api_key:
        print("⚠️  TWELVE_DATA_API_KEY not set. Skipping example 4.")
        return
    
    config = PipelineConfig(
        backfill_days=30,
        max_retries=3,
    )
    
    pipeline = DataPipeline(api_key=api_key, config=config)
    await pipeline.initialize()
    
    try:
        print("\n📥 Backfilling 30 days of daily data for AAPL...")
        
        start = datetime.utcnow()
        count = await pipeline.backfill_data(
            symbol='AAPL',
            interval=DataInterval.DAY_1,
            days=30
        )
        elapsed = (datetime.utcnow() - start).total_seconds()
        
        print(f"\n✅ Backfilled {count} candles in {elapsed:.2f}s")
        print(f"   Average: {count/elapsed:.1f} candles/second")
    
    finally:
        await pipeline.close()


# ============================================================================
# Example 5: Multiple Symbols with Different Intervals
# ============================================================================

async def example_5_multi_symbol():
    """Fetch multiple symbols with different time intervals."""
    print("\n" + "="*70)
    print("Example 5: Multiple Symbols with Different Intervals")
    print("="*70)
    
    api_key = os.getenv('TWELVE_DATA_API_KEY')
    if not api_key:
        print("⚠️  TWELVE_DATA_API_KEY not set. Skipping example 5.")
        return
    
    pipeline = DataPipeline(api_key=api_key)
    await pipeline.initialize()
    
    try:
        # Define queries
        queries = [
            ('AAPL', DataInterval.DAY_1),
            ('GOOGL', DataInterval.HOUR_1),
            ('MSFT', DataInterval.MINUTE_5),
        ]
        
        print("\nFetching multiple symbols:\n")
        
        for symbol, interval in queries:
            data = await pipeline.get_ohlcv(symbol, interval)
            if data:
                latest = data[-1]
                print(f"  {symbol:6} ({interval.value:6}) | "
                      f"Latest: {latest.timestamp} @ ${latest.close:.2f} "
                      f"| {len(data)} candles")
        
        # Show cache stats
        cache = await get_global_cache()
        stats = cache.stats()
        print(f"\nCache: {stats['hits']} hits, {stats['misses']} misses")
    
    finally:
        await pipeline.close()


# ============================================================================
# Example 6: Error Handling
# ============================================================================

async def example_6_error_handling():
    """Demonstrate error handling patterns."""
    print("\n" + "="*70)
    print("Example 6: Error Handling")
    print("="*70)
    
    api_key = os.getenv('TWELVE_DATA_API_KEY')
    if not api_key:
        print("⚠️  TWELVE_DATA_API_KEY not set. Skipping example 6.")
        return
    
    pipeline = DataPipeline(api_key=api_key)
    await pipeline.initialize()
    
    try:
        # Try with invalid symbol
        print("\nAttempting to fetch invalid symbol 'INVALIDTICKER'...")
        data = await pipeline.get_ohlcv('INVALIDTICKER', DataInterval.DAY_1)
        
        if not data:
            print("⚠️  No data returned (symbol may not exist)")
        else:
            print(f"✅ Got {len(data)} candles")
        
        # Try with very old date
        print("\nAttempting to fetch data from 1900...")
        old_date = datetime(1900, 1, 1)
        data = await pipeline.get_ohlcv(
            'AAPL',
            DataInterval.DAY_1,
            start_date=old_date
        )
        
        if not data:
            print("⚠️  No data available (date range may be invalid)")
        else:
            print(f"✅ Got {len(data)} candles")
    
    except Exception as e:
        print(f"❌ Error: {e}")
    
    finally:
        await pipeline.close()


# ============================================================================
# Example 7: All Supported Intervals
# ============================================================================

async def example_7_intervals():
    """Show all supported time intervals."""
    print("\n" + "="*70)
    print("Example 7: All Supported Intervals")
    print("="*70)
    
    intervals = [
        DataInterval.MINUTE_1,
        DataInterval.MINUTE_5,
        DataInterval.MINUTE_15,
        DataInterval.MINUTE_30,
        DataInterval.HOUR_1,
        DataInterval.HOUR_4,
        DataInterval.DAY_1,
        DataInterval.WEEK_1,
        DataInterval.MONTH_1,
    ]
    
    print("\nSupported time intervals:\n")
    for i, interval in enumerate(intervals, 1):
        print(f"  {i}. {interval.name:12} = {interval.value}")


# ============================================================================
# Main
# ============================================================================

async def main():
    """Run all examples."""
    print("\n")
    print("╔" + "="*68 + "╗")
    print("║" + " "*15 + "Data Layer Usage Examples" + " "*29 + "║")
    print("║" + " "*20 + "Twelve Data API Integration" + " "*21 + "║")
    print("╚" + "="*68 + "╝")
    
    try:
        # Run examples
        await example_1_simple_fetch()
        await example_2_caching()
        await example_3_quotes()
        await example_4_backfill()
        await example_5_multi_symbol()
        await example_6_error_handling()
        await example_7_intervals()
        
        print("\n" + "="*70)
        print("✅ All examples completed!")
        print("="*70 + "\n")
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        logger.exception("Unhandled exception")


if __name__ == '__main__':
    asyncio.run(main())
