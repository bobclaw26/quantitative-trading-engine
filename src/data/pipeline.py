"""
Data ingestion pipeline combining Twelve Data API and caching.

Implements polling strategy with smart caching to minimize API calls
while maintaining data freshness. Supports backfilling historical data.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Optional
from dataclasses import dataclass

from models import OHLCV, DataInterval, DataResponse, DataRequest
from twelve_data_client import TwelveDataClient
from cache import DataCache, get_global_cache

logger = logging.getLogger(__name__)


@dataclass
class PipelineConfig:
    """Configuration for data pipeline."""
    # Rate limiting
    max_concurrent_requests: int = 5
    request_timeout_seconds: int = 30
    
    # Caching
    use_cache: bool = True
    ohlcv_cache_ttl: int = 3600  # 1 hour for daily candles
    intraday_cache_ttl: int = 900  # 15 minutes for intraday
    
    # Backfilling
    backfill_days: int = 30  # How many days of history to fetch
    backfill_batch_size: int = 100  # Candles per request
    
    # Polling
    poll_interval_seconds: int = 60  # How often to poll for new data
    
    # Retry logic
    max_retries: int = 3
    retry_backoff_seconds: int = 5


class DataPipeline:
    """
    Data ingestion pipeline with caching and rate limiting.
    
    Features:
    - Automatic caching with TTL
    - Historical data backfilling
    - Polling for real-time updates
    - Concurrent request handling
    - Error recovery and retries
    """
    
    def __init__(self, api_key: Optional[str] = None, 
                 config: Optional[PipelineConfig] = None):
        """
        Initialize pipeline.
        
        Args:
            api_key: Twelve Data API key
            config: Pipeline configuration
        """
        self.client = TwelveDataClient(api_key=api_key)
        self.config = config or PipelineConfig()
        self.cache: Optional[DataCache] = None
        self._running = False
        self._semaphore = asyncio.Semaphore(self.config.max_concurrent_requests)
    
    async def initialize(self) -> None:
        """Initialize pipeline (get cache instance)."""
        self.cache = await get_global_cache()
        logger.info("Pipeline initialized")
    
    async def _execute_with_semaphore(self, coro):
        """Execute coroutine with concurrency limiting."""
        async with self._semaphore:
            return await coro
    
    async def _fetch_with_retry(self, symbol: str, interval: DataInterval,
                               start_date: Optional[datetime] = None,
                               end_date: Optional[datetime] = None,
                               limit: int = 5000) -> DataResponse:
        """
        Fetch data with automatic retry logic.
        
        Args:
            symbol: Trading symbol
            interval: Data interval
            start_date: Optional start date
            end_date: Optional end date
            limit: Maximum candles
            
        Returns:
            DataResponse (may have error)
        """
        for attempt in range(self.config.max_retries):
            try:
                response = await self.client.get_timeseries(
                    symbol=symbol,
                    interval=interval,
                    start_date=start_date,
                    end_date=end_date,
                    limit=limit
                )
                
                if response.is_success():
                    return response
                
                if attempt < self.config.max_retries - 1:
                    wait_time = self.config.retry_backoff_seconds * (attempt + 1)
                    logger.warning(
                        f"Retry {attempt + 1}/{self.config.max_retries} "
                        f"for {symbol}, waiting {wait_time}s"
                    )
                    await asyncio.sleep(wait_time)
            
            except Exception as e:
                logger.error(f"Error fetching {symbol}: {e}")
                if attempt < self.config.max_retries - 1:
                    wait_time = self.config.retry_backoff_seconds * (attempt + 1)
                    await asyncio.sleep(wait_time)
        
        return DataResponse(
            request=DataRequest(symbol=symbol, interval=interval),
            error="Max retries exceeded"
        )
    
    async def get_ohlcv(self, symbol: str, interval: DataInterval,
                       start_date: Optional[datetime] = None,
                       end_date: Optional[datetime] = None,
                       force_refresh: bool = False) -> List[OHLCV]:
        """
        Get OHLCV data with caching.
        
        Args:
            symbol: Trading symbol
            interval: Data interval
            start_date: Optional start date
            end_date: Optional end date
            force_refresh: Skip cache and fetch fresh data
            
        Returns:
            List of OHLCV data
        """
        # Check cache first (unless force_refresh)
        if self.config.use_cache and not force_refresh and self.cache:
            cached = await self.cache.get_ohlcv(symbol, interval, start_date)
            if cached:
                logger.info(f"Cache hit: {symbol} {interval.value}")
                return cached
        
        # Fetch from API
        response = await self._execute_with_semaphore(
            self._fetch_with_retry(symbol, interval, start_date, end_date)
        )
        
        if response.is_success():
            # Cache the result
            if self.config.use_cache and self.cache:
                ttl = (self.config.intraday_cache_ttl 
                      if interval in (DataInterval.MINUTE_1, DataInterval.MINUTE_5,
                                     DataInterval.MINUTE_15, DataInterval.MINUTE_30)
                      else self.config.ohlcv_cache_ttl)
                
                await self.cache.set_ohlcv(
                    symbol, interval, response.data,
                    ttl_seconds=ttl,
                    start_date=start_date
                )
            
            logger.info(f"Fetched {len(response.data)} candles: {symbol} {interval.value}")
            return response.data
        else:
            logger.error(f"Failed to fetch {symbol}: {response.error}")
            return []
    
    async def backfill_data(self, symbol: str, interval: DataInterval,
                           days: Optional[int] = None) -> int:
        """
        Backfill historical data for a symbol.
        
        Args:
            symbol: Trading symbol
            interval: Data interval
            days: Number of days to backfill (uses config default if None)
            
        Returns:
            Total number of candles backfilled
        """
        if days is None:
            days = self.config.backfill_days
        
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        logger.info(f"Starting backfill for {symbol}: {days} days")
        
        # For daily data, we can fetch in one go (max 5000 candles)
        if interval == DataInterval.DAY_1:
            response = await self._execute_with_semaphore(
                self._fetch_with_retry(
                    symbol, interval,
                    start_date=start_date,
                    end_date=end_date,
                    limit=5000
                )
            )
            
            if response.is_success() and self.cache:
                await self.cache.set_ohlcv(
                    symbol, interval, response.data,
                    ttl_seconds=86400,  # 24 hours for backfilled data
                    start_date=start_date
                )
                logger.info(f"Backfilled {len(response.data)} daily candles")
                return len(response.data)
        
        else:
            # For intraday data, fetch in batches
            total_candles = 0
            current_end = end_date
            
            while current_end > start_date:
                batch_start = max(
                    start_date,
                    current_end - timedelta(hours=24)  # Fetch 24h at a time
                )
                
                response = await self._execute_with_semaphore(
                    self._fetch_with_retry(
                        symbol, interval,
                        start_date=batch_start,
                        end_date=current_end,
                        limit=5000
                    )
                )
                
                if response.is_success():
                    total_candles += len(response.data)
                    
                    if self.cache:
                        await self.cache.set_ohlcv(
                            symbol, interval, response.data,
                            ttl_seconds=self.config.intraday_cache_ttl
                        )
                
                current_end = batch_start
                await asyncio.sleep(0.1)  # Small delay between batches
            
            logger.info(f"Backfilled {total_candles} intraday candles")
            return total_candles
    
    async def poll_symbol(self, symbol: str, interval: DataInterval) -> None:
        """
        Poll for new data periodically (for real-time updates).
        
        Args:
            symbol: Trading symbol
            interval: Data interval to poll
        """
        logger.info(f"Starting poll for {symbol} ({interval.value})")
        
        while self._running:
            try:
                # Fetch latest data without caching requirement
                data = await self.get_ohlcv(symbol, interval, force_refresh=True)
                
                if data:
                    latest = data[-1]
                    logger.debug(
                        f"Polled {symbol}: {latest.timestamp} "
                        f"O:{latest.open} C:{latest.close}"
                    )
                
                await asyncio.sleep(self.config.poll_interval_seconds)
            
            except Exception as e:
                logger.error(f"Polling error for {symbol}: {e}")
                await asyncio.sleep(self.config.poll_interval_seconds)
    
    async def start_polling(self, symbols: List[str], 
                           interval: DataInterval) -> asyncio.Task:
        """
        Start polling multiple symbols.
        
        Args:
            symbols: List of symbols to poll
            interval: Data interval
            
        Returns:
            Asyncio Task that can be cancelled
        """
        self._running = True
        
        async def poll_all():
            tasks = [
                asyncio.create_task(self.poll_symbol(symbol, interval))
                for symbol in symbols
            ]
            await asyncio.gather(*tasks)
        
        return asyncio.create_task(poll_all())
    
    async def stop_polling(self) -> None:
        """Stop polling tasks."""
        self._running = False
        logger.info("Polling stopped")
    
    async def close(self) -> None:
        """Close pipeline and cleanup resources."""
        await self.stop_polling()
        logger.info("Pipeline closed")


# Global pipeline instance
_pipeline: Optional[DataPipeline] = None


async def get_pipeline(api_key: Optional[str] = None) -> DataPipeline:
    """Get or create the global pipeline instance."""
    global _pipeline
    
    if _pipeline is None:
        _pipeline = DataPipeline(api_key=api_key)
        await _pipeline.initialize()
    
    return _pipeline
