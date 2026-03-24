# Data Architecture - Phase 1: Twelve Data Integration

## Overview

The data layer provides a robust, high-performance pipeline for ingesting real-time and historical market data from the Twelve Data API. It implements intelligent caching, rate-limiting, and async I/O to maximize throughput while respecting API constraints.

**Key Features:**
- ✅ Real-time and historical OHLCV data
- ✅ Multiple time intervals (1min to 1month)
- ✅ Smart in-memory caching with TTL
- ✅ Rate limiting (800 req/min free tier)
- ✅ Async/await for high concurrency
- ✅ Automatic retry with backoff
- ✅ Historical data backfilling
- ✅ Comprehensive error handling

## Architecture

### Component Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Data Pipeline                             │
│  (manages overall data flow, polling, backfilling)          │
└────────────────────────┬────────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┐
         │               │               │
    ┌────▼───┐    ┌─────▼──────┐  ┌────▼──────┐
    │  Cache │    │   Client   │  │  Models   │
    │ (TTL)  │    │ (Rate Lim) │  │ (OHLCV)   │
    └─────────┘    └──────┬─────┘  └───────────┘
                          │
                   ┌──────▼──────┐
                   │ Twelve Data │
                   │     API     │
                   └─────────────┘
```

### Component Descriptions

#### 1. **Data Models** (`src/data/models.py`)
Type-safe data structures for market data:

- **OHLCV**: Candlestick data (Open, High, Low, Close, Volume)
  - Includes validation (high ≥ open/close, low ≤ open/close)
  - Timezone-aware timestamps
  - Optional turnover tracking
  
- **Tick**: Individual trade/quote data
  - Bid/ask prices
  - Volume information
  - Trade metadata
  
- **Quote**: Real-time price updates
  - Current price and spread
  - Volume and change metrics
  - Minimal overhead for speed
  
- **DataInterval**: Enum for supported intervals
  - 1min, 5min, 15min, 30min, 1h, 4h, 1d, 1w, 1mo
  
- **DataRequest/DataResponse**: Standardized API contracts
  - Request validation
  - Consistent response format

#### 2. **Twelve Data Client** (`src/data/twelve_data_client.py`)
HTTP client with built-in rate limiting and error handling:

**Rate Limiting:**
- Token bucket algorithm
- 800 requests/minute (free tier limit)
- Automatic backoff when limit reached
- Per-request tracking

**API Integration:**
- `get_timeseries()`: Historical OHLCV data (1min to 1month)
- `get_quote()`: Real-time quote data
- `get_intraday()`: Minute-level data
- Automatic retry with exponential backoff
- JSON parsing and validation
- Error recovery

**Configuration:**
```python
client = TwelveDataClient(api_key="your_key")
async with client:
    response = await client.get_timeseries(
        symbol="AAPL",
        interval=DataInterval.DAY_1,
        start_date=datetime(2024, 1, 1),
        limit=5000
    )
```

#### 3. **Caching Layer** (`src/data/cache.py`)
In-memory cache with TTL and concurrent access support:

**Features:**
- Thread-safe async operations
- TTL-based expiration
- Key generation from symbol + interval
- Automatic cleanup on size limits
- Hit/miss statistics

**Cache Strategies by Data Type:**

| Data Type | Default TTL | Use Case |
|-----------|------------|----------|
| Daily OHLCV | 1 hour | Stable, updated daily |
| Intraday (1min-30min) | 15 minutes | Fast-changing data |
| Quotes | 1 minute | Real-time updates |
| Ticks | 5 minutes | High-frequency data |

**API:**
```python
cache = DataCache(max_entries=10000)

# Store and retrieve OHLCV
await cache.set_ohlcv('AAPL', DataInterval.DAY_1, candles, ttl_seconds=3600)
data = await cache.get_ohlcv('AAPL', DataInterval.DAY_1)

# Quote caching
await cache.set_quote(quote)
quote = await cache.get_quote('AAPL')

# Cache stats
stats = cache.stats()  # {hits, misses, hit_rate_percent, ...}
```

#### 4. **Data Pipeline** (`src/data/pipeline.py`)
Orchestrates client, cache, and polling:

**Features:**
- Transparent caching with optional refresh
- Historical data backfilling
- Real-time polling
- Concurrency control via semaphores
- Automatic retry logic
- Configuration management

**Configuration:**
```python
config = PipelineConfig(
    max_concurrent_requests=5,
    ohlcv_cache_ttl=3600,
    intraday_cache_ttl=900,
    backfill_days=30,
    poll_interval_seconds=60,
    max_retries=3,
)
pipeline = DataPipeline(config=config)
await pipeline.initialize()
```

**Usage Patterns:**

1. **Fetch with caching:**
   ```python
   data = await pipeline.get_ohlcv('AAPL', DataInterval.DAY_1)
   # Checks cache first, fetches from API if needed
   ```

2. **Force fresh data:**
   ```python
   data = await pipeline.get_ohlcv('AAPL', DataInterval.DAY_1, force_refresh=True)
   ```

3. **Backfill historical data:**
   ```python
   await pipeline.backfill_data('AAPL', DataInterval.DAY_1, days=90)
   ```

4. **Polling for real-time updates:**
   ```python
   task = await pipeline.start_polling(['AAPL', 'GOOGL'], DataInterval.MINUTE_1)
   # ... do work ...
   await pipeline.stop_polling()
   ```

## Data Flow Diagrams

### Read Operation Flow

```
Request for AAPL/1d
    │
    ├─► Check Cache
    │   │
    │   ├─ Hit → Return cached data
    │   │
    │   └─ Miss ↓
    │
    ├─► Apply Rate Limit
    │
    ├─► Call Twelve Data API
    │   │
    │   ├─ Success ↓
    │   │
    │   └─ Failure → Retry (exponential backoff)
    │
    ├─► Parse Response → OHLCV objects
    │
    ├─► Store in Cache (with TTL)
    │
    └─► Return Data to Caller
```

### Backfill Operation Flow

```
Backfill 30 days of AAPL/1d
    │
    ├─► Calculate date range (today - 30 days)
    │
    ├─► For daily: Single request (max 5000 candles)
    │   or
    │   For intraday: Batch requests (24h at a time)
    │
    ├─► Respect rate limits (wait between batches)
    │
    ├─► Parse all responses
    │
    ├─► Store in cache (long TTL for backfilled data)
    │
    └─► Return total candles ingested
```

## API Rate Limits

### Free Tier (Twelve Data)
- **Request Limit:** 800 requests/minute
- **Historical Data:** Up to 5,000 candles per request
- **Real-time Updates:** Delayed by 5-15 minutes
- **Supported Intervals:** All (1min to 1month)

### Rate Limit Handling

The client implements a **token bucket algorithm**:

```
┌─────────────────────────────────────────┐
│ Token Bucket (800 tokens/60 seconds)    │
│                                          │
│ Request 1 ─┐  (consume 1 token)        │
│ Request 2 ─┤  (consume 1 token)        │
│ Request 3 ─┤  (consume 1 token)        │
│ ...        │                            │
│ Request 800 ┘  (consume 1 token)       │
│                                          │
│ Request 801 ──► WAIT (refill in 60s)    │
└─────────────────────────────────────────┘
```

**Configuration:**
```python
# Adjust for your tier
limiter = RateLimiter(max_requests=800, window_seconds=60)
await limiter.wait_if_needed()  # Blocks if limit reached
```

## Cost Considerations

### API Costs
- **Free Tier:** $0 (800 req/min limit)
- **Pro Tier:** $25/month (2000 req/min)
- **Enterprise:** Custom pricing

### Optimization Strategies

1. **Caching reduces requests**
   - Daily data cached for 1 hour → ~40x fewer requests
   - Intraday cached for 15 min → ~4x fewer requests

2. **Backfilling in batches**
   - Fetch 5000 candles per request
   - 30 days of daily data = 1 request
   - 30 days of minute data = ~240 requests

3. **Smart polling intervals**
   - Daily data: Poll once per day
   - Hourly data: Poll every hour
   - Minute data: Poll every 1-5 minutes

**Cost Estimate (1000 requests/day):**
- Requests per year: ~365,000
- At free tier limit: Sustainable year-round
- Cost: $0

## Database Design (Phase 2)

### PostgreSQL Schema
```sql
-- OHLCV candles
CREATE TABLE ohlcv_candles (
    id BIGSERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    interval VARCHAR(10) NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    open DECIMAL(20,8) NOT NULL,
    high DECIMAL(20,8) NOT NULL,
    low DECIMAL(20,8) NOT NULL,
    close DECIMAL(20,8) NOT NULL,
    volume BIGINT NOT NULL,
    turnover DECIMAL(20,8),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(symbol, interval, timestamp),
    INDEX idx_symbol_interval_timestamp (symbol, interval, timestamp)
);

-- Real-time quotes
CREATE TABLE quotes (
    id BIGSERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    price DECIMAL(20,8) NOT NULL,
    bid DECIMAL(20,8),
    ask DECIMAL(20,8),
    timestamp TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_symbol_timestamp (symbol, timestamp)
);

-- Tick data
CREATE TABLE ticks (
    id BIGSERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    price DECIMAL(20,8) NOT NULL,
    bid DECIMAL(20,8),
    ask DECIMAL(20,8),
    volume BIGINT,
    timestamp TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_symbol_timestamp (symbol, timestamp)
);
```

## Error Handling Strategy

### Retryable Errors
- Network timeouts → exponential backoff
- Rate limit exceeded → wait and retry
- Temporary API downtime → retry with backoff

### Non-retryable Errors
- Invalid API key → fail immediately
- Symbol not found → fail immediately
- Invalid parameters → fail immediately

### Error Recovery
```python
# Automatic retry with exponential backoff
for attempt in range(max_retries):
    try:
        data = await client.get_timeseries(...)
        if data.is_success():
            return data
    except Exception as e:
        if attempt < max_retries - 1:
            wait_time = retry_backoff * (attempt + 1)
            await asyncio.sleep(wait_time)
        else:
            raise
```

## Testing Strategy

### Unit Tests
- **models.py**: Validation logic, serialization
- **cache.py**: TTL expiration, hit rates, thread safety
- **twelve_data_client.py**: Rate limiting, error handling
- **pipeline.py**: Integration, backfilling logic

### Integration Tests
- End-to-end data flows
- Cache coherency
- Rate limit enforcement
- Error recovery

### Load Tests
- Concurrent request handling
- Cache performance under load
- Memory usage with large datasets

## Migration from Alpha Vantage

### Differences
| Feature | Alpha Vantage | Twelve Data |
|---------|--------------|------------|
| Rate Limit | 5 req/min | 800 req/min |
| Coverage | US equities only | Global coverage |
| Delay | Real-time | 5-15 min delayed |
| Intervals | Limited | All supported |
| Cost | Free (limited) | Free (800 req/min) |

### Migration Steps
1. Keep both clients temporarily
2. Dual-write to both APIs
3. Validate data consistency
4. Cutover to Twelve Data
5. Archive old Alpha Vantage data

## Future Enhancements (Phase 2+)

1. **Database Storage**
   - PostgreSQL persistence
   - Historical data archival
   - Query optimization

2. **Advanced Caching**
   - Redis integration for distributed cache
   - Cache warming strategies
   - Compression for large datasets

3. **Real-time Streaming**
   - WebSocket support
   - Event-driven updates
   - Sub-minute latency

4. **Data Quality**
   - Outlier detection
   - Gap filling
   - Volume profile analysis

5. **Analytics**
   - Data freshness metrics
   - API usage dashboard
   - Cost tracking

## References

- **Twelve Data API:** https://twelvedata.com/docs
- **Rate Limiting:** https://en.wikipedia.org/wiki/Token_bucket
- **Async Python:** https://docs.python.org/3/library/asyncio.html
- **PostgreSQL JSON:** https://www.postgresql.org/docs/current/datatype-json.html
