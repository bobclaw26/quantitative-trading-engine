# Data Layer - Twelve Data Integration

Real-time and historical market data pipeline with intelligent caching and rate limiting.

## Quick Start

### Installation

```bash
pip install -r requirements-data.txt
```

### Set API Key

```bash
export TWELVE_DATA_API_KEY="your_api_key_here"
```

Get a free key from: https://twelvedata.com

## Usage Examples

### Example 1: Simple Data Fetch

```python
import asyncio
from src.data import TwelveDataClient, DataInterval

async def fetch_data():
    client = TwelveDataClient()
    
    async with client:
        # Get last 100 daily candles for AAPL
        response = await client.get_timeseries(
            symbol='AAPL',
            interval=DataInterval.DAY_1,
            limit=100
        )
        
        for candle in response.data:
            print(f"{candle.timestamp}: O={candle.open} C={candle.close}")

asyncio.run(fetch_data())
```

### Example 2: Data Pipeline with Caching

```python
import asyncio
from src.data import DataPipeline, DataInterval

async def with_pipeline():
    pipeline = DataPipeline()
    await pipeline.initialize()
    
    # Fetches from API and caches result
    data = await pipeline.get_ohlcv('AAPL', DataInterval.DAY_1)
    print(f"Got {len(data)} candles")
    
    # Next call uses cache (within TTL)
    data = await pipeline.get_ohlcv('AAPL', DataInterval.DAY_1)
    print("From cache!")
    
    # Force fresh data
    data = await pipeline.get_ohlcv('AAPL', DataInterval.DAY_1, force_refresh=True)
    print("Fresh data from API")

asyncio.run(with_pipeline())
```

### Example 3: Backfilling Historical Data

```python
import asyncio
from src.data import DataPipeline, DataInterval

async def backfill():
    pipeline = DataPipeline()
    await pipeline.initialize()
    
    # Fetch 3 months of daily data
    count = await pipeline.backfill_data(
        symbol='AAPL',
        interval=DataInterval.DAY_1,
        days=90
    )
    
    print(f"Backfilled {count} candles")
    
    await pipeline.close()

asyncio.run(backfill())
```

### Example 4: Real-time Polling

```python
import asyncio
from src.data import DataPipeline, DataInterval

async def polling():
    pipeline = DataPipeline()
    await pipeline.initialize()
    
    # Start polling for minute-level data
    symbols = ['AAPL', 'GOOGL', 'MSFT']
    task = await pipeline.start_polling(symbols, DataInterval.MINUTE_1)
    
    # Let it run for 5 minutes
    try:
        await asyncio.sleep(300)
    finally:
        await pipeline.stop_polling()
        await task

asyncio.run(polling())
```

### Example 5: Quote Data

```python
import asyncio
from src.data import TwelveDataClient

async def get_quotes():
    client = TwelveDataClient()
    
    async with client:
        quote = await client.get_quote('AAPL')
        if quote:
            print(f"AAPL: ${quote.price}")
            print(f"  Bid: ${quote.bid} | Ask: ${quote.ask}")
            print(f"  Change: {quote.change_percent}%")

asyncio.run(get_quotes())
```

### Example 6: Cache Statistics

```python
import asyncio
from src.data import DataPipeline, DataInterval, get_global_cache

async def cache_stats():
    pipeline = DataPipeline()
    await pipeline.initialize()
    
    # Do some operations
    await pipeline.get_ohlcv('AAPL', DataInterval.DAY_1)
    await pipeline.get_ohlcv('AAPL', DataInterval.DAY_1)  # Cache hit
    await pipeline.get_ohlcv('GOOGL', DataInterval.DAY_1)
    
    # Check stats
    cache = await get_global_cache()
    stats = cache.stats()
    
    print(f"Cache hits: {stats['hits']}")
    print(f"Cache misses: {stats['misses']}")
    print(f"Hit rate: {stats['hit_rate_percent']:.1f}%")

asyncio.run(cache_stats())
```

## Data Models

### OHLCV (Candlestick Data)

```python
from src.data import OHLCV, DataInterval
from datetime import datetime

candle = OHLCV(
    timestamp=datetime.utcnow(),
    symbol='AAPL',
    interval=DataInterval.DAY_1,
    open=150.0,
    high=155.0,
    low=149.0,
    close=152.0,
    volume=1000000,
    turnover=1520000000.0  # Optional
)

# Convert to dict
data = candle.to_dict()
```

### Quote (Real-time Price)

```python
from src.data import Quote

quote = Quote(
    symbol='AAPL',
    price=150.5,
    bid=150.4,
    ask=150.6,
    change=2.5,
    change_percent=1.69
)
```

### Tick (Trade Data)

```python
from src.data import Tick
from datetime import datetime

tick = Tick(
    timestamp=datetime.utcnow(),
    symbol='AAPL',
    price=150.5,
    bid=150.4,
    ask=150.6,
    bid_volume=1000,
    ask_volume=1500,
    volume=1000
)
```

## Configuration

### Pipeline Configuration

```python
from src.data import DataPipeline, PipelineConfig

config = PipelineConfig(
    # Concurrency
    max_concurrent_requests=5,
    request_timeout_seconds=30,
    
    # Caching
    use_cache=True,
    ohlcv_cache_ttl=3600,         # 1 hour
    intraday_cache_ttl=900,        # 15 minutes
    
    # Backfilling
    backfill_days=30,
    backfill_batch_size=100,
    
    # Polling
    poll_interval_seconds=60,
    
    # Retry logic
    max_retries=3,
    retry_backoff_seconds=5,
)

pipeline = DataPipeline(config=config)
```

### Rate Limiter Configuration

```python
from src.data.twelve_data_client import RateLimiter

# Twelve Data free tier: 800 requests/minute
limiter = RateLimiter(max_requests=800, window_seconds=60)

# Wait if needed
await limiter.wait_if_needed()
```

## Supported Data Intervals

```python
from src.data import DataInterval

DataInterval.MINUTE_1    # 1 minute
DataInterval.MINUTE_5    # 5 minutes
DataInterval.MINUTE_15   # 15 minutes
DataInterval.MINUTE_30   # 30 minutes
DataInterval.HOUR_1      # 1 hour
DataInterval.HOUR_4      # 4 hours
DataInterval.DAY_1       # 1 day
DataInterval.WEEK_1      # 1 week
DataInterval.MONTH_1     # 1 month
```

## Error Handling

```python
import asyncio
from src.data import DataPipeline, DataInterval

async def safe_fetch():
    pipeline = DataPipeline()
    await pipeline.initialize()
    
    try:
        data = await pipeline.get_ohlcv('AAPL', DataInterval.DAY_1)
        if not data:
            print("No data returned")
        else:
            print(f"Got {len(data)} candles")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await pipeline.close()

asyncio.run(safe_fetch())
```

## Testing

Run unit tests:

```bash
# All tests
pytest tests/ -v

# Specific test file
pytest tests/test_data_models.py -v

# With coverage
pytest tests/ --cov=src/data --cov-report=html
```

Test files:
- `tests/test_data_models.py` - Model validation
- `tests/test_data_cache.py` - Cache functionality
- `tests/test_twelve_data_client.py` - API integration (mock)

## Performance Tips

1. **Cache Effectively**
   - Set appropriate TTLs for your use case
   - Monitor hit rate with `cache.stats()`

2. **Batch Requests**
   - Fetch multiple days in one request when possible
   - Use backfilling for historical data

3. **Concurrent Access**
   - Use semaphores for rate-limited concurrency
   - Monitor request rates

4. **Smart Polling**
   - Poll less frequently for stable data (daily)
   - Poll more frequently for volatile data (minute)

## API Documentation

See full documentation in `docs/DATA_ARCHITECTURE.md`:
- Architecture overview
- Database schema (Phase 2)
- Rate limit details
- Cost considerations
- Migration guide

## Environment Variables

```bash
# Required
export TWELVE_DATA_API_KEY="your_key"

# Optional
export DATA_CACHE_SIZE=10000              # Max cache entries
export DATA_CACHE_CLEANUP_INTERVAL=300    # Cleanup interval in seconds
export DATA_REQUEST_TIMEOUT=30            # Request timeout in seconds
export DATA_MAX_RETRIES=3                 # Max retries on failure
```

## Troubleshooting

### Rate Limit Errors
- Reduce `max_concurrent_requests` in PipelineConfig
- Increase `poll_interval_seconds`
- Check your API tier limit

### Missing Data
- Check symbol exists on Twelve Data
- Verify date range is available
- Check API key has access

### Cache Not Working
- Verify `use_cache=True` in PipelineConfig
- Check cache TTL settings
- Monitor with `cache.stats()`

### High Memory Usage
- Reduce `max_entries` in DataCache
- Decrease cache TTL values
- Enable aggressive cleanup

## Contributing

1. Write tests for new features
2. Follow async patterns with `async/await`
3. Document public APIs
4. Update ARCHITECTURE.md for major changes

## References

- **Twelve Data Docs:** https://twelvedata.com/docs
- **Async Python:** https://docs.python.org/3/library/asyncio.html
- **API Specification:** See `docs/DATA_ARCHITECTURE.md`
