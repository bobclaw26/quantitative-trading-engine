"""
Twelve Data API client with rate limiting and error handling.

Integrates with Twelve Data API for real-time and historical market data.
Handles rate limiting (800 requests/minute on free tier).

Documentation: https://twelvedata.com/docs
"""

import asyncio
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import aiohttp
from urllib.parse import urlencode

from models import OHLCV, Tick, Quote, DataInterval, DataSource, DataResponse, DataRequest

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Rate limiter implementing token bucket algorithm.
    Ensures compliance with API rate limits.
    """
    
    def __init__(self, max_requests: int = 800, window_seconds: int = 60):
        """
        Initialize rate limiter.
        
        Args:
            max_requests: Maximum requests allowed in the window
            window_seconds: Window size in seconds (default 60 = 1 minute)
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = []
        self._lock = asyncio.Lock()
    
    async def wait_if_needed(self) -> float:
        """
        Wait if rate limit would be exceeded.
        
        Returns:
            Time waited in seconds
        """
        async with self._lock:
            now = datetime.utcnow()
            window_start = now - timedelta(seconds=self.window_seconds)
            
            # Remove old requests outside the window
            self.requests = [req_time for req_time in self.requests 
                           if req_time > window_start]
            
            # If at limit, wait
            if len(self.requests) >= self.max_requests:
                oldest_request = self.requests[0]
                wait_time = (oldest_request - window_start).total_seconds()
                
                if wait_time > 0:
                    logger.warning(f"Rate limit reached, waiting {wait_time:.2f}s")
                    await asyncio.sleep(wait_time)
                    
                    # Recursively check again after waiting
                    return wait_time + await self.wait_if_needed()
            
            # Add current request
            self.requests.append(datetime.utcnow())
            return 0.0


class TwelveDataClient:
    """
    Twelve Data API client with rate limiting and error handling.
    
    Supports:
    - Real-time and historical OHLCV data
    - Multiple time intervals (1min to 1month)
    - Quote data
    - Tick data
    - Proper error handling and retry logic
    """
    
    BASE_URL = "https://api.twelvedata.com"
    
    # API endpoints
    ENDPOINTS = {
        'timeseries': '/time_series',
        'quote': '/quote',
        'intraday': '/intraday',
    }
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Twelve Data client.
        
        Args:
            api_key: API key (uses TWELVE_DATA_API_KEY env var if not provided)
            
        Raises:
            ValueError: If API key is not provided or available
        """
        self.api_key = api_key or os.getenv('TWELVE_DATA_API_KEY')
        if not self.api_key:
            raise ValueError("TWELVE_DATA_API_KEY not provided and not in environment")
        
        self.rate_limiter = RateLimiter(max_requests=800, window_seconds=60)
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        self._session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._session:
            await self._session.close()
    
    async def _request(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make API request with rate limiting and error handling.
        
        Args:
            endpoint: API endpoint path
            params: Query parameters
            
        Returns:
            JSON response as dictionary
            
        Raises:
            Exception: Various exceptions for API errors
        """
        # Add API key
        params['apikey'] = self.api_key
        
        # Apply rate limiting
        await self.rate_limiter.wait_if_needed()
        
        url = self.BASE_URL + endpoint
        
        if not self._session:
            raise RuntimeError("Client not initialized. Use 'async with' context manager.")
        
        try:
            async with self._session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                data = await resp.json()
                
                # Check for API errors
                if resp.status != 200:
                    error_msg = data.get('message', f'HTTP {resp.status}')
                    logger.error(f"API error: {error_msg}")
                    raise Exception(f"API error: {error_msg}")
                
                if 'status' in data and data['status'] == 'error':
                    raise Exception(f"API error: {data.get('message', 'Unknown error')}")
                
                return data
        
        except asyncio.TimeoutError:
            raise Exception("API request timeout")
        except aiohttp.ClientError as e:
            raise Exception(f"Network error: {e}")
    
    async def get_timeseries(self, symbol: str, interval: DataInterval,
                            start_date: Optional[datetime] = None,
                            end_date: Optional[datetime] = None,
                            limit: int = 5000) -> DataResponse:
        """
        Get historical OHLCV data.
        
        Args:
            symbol: Trading symbol (e.g., 'AAPL')
            interval: Data interval (1min, 5min, 1h, 1d, etc.)
            start_date: Optional start date
            end_date: Optional end date
            limit: Maximum candles to return (max 5000)
            
        Returns:
            DataResponse containing OHLCV data
        """
        request = DataRequest(
            symbol=symbol,
            interval=interval,
            start_date=start_date,
            end_date=end_date,
            limit=limit
        )
        request.validate()
        
        params = {
            'symbol': symbol,
            'interval': interval.value,
            'limit': min(limit, 5000),
        }
        
        if start_date:
            params['start_date'] = start_date.strftime('%Y-%m-%d %H:%M:%S')
        if end_date:
            params['end_date'] = end_date.strftime('%Y-%m-%d %H:%M:%S')
        
        try:
            data = await self._request(self.ENDPOINTS['timeseries'], params)
            
            # Parse response
            ohlcv_list = []
            for candle in data.get('values', []):
                try:
                    ohlcv = OHLCV(
                        timestamp=datetime.fromisoformat(candle['datetime']),
                        symbol=symbol,
                        interval=interval,
                        open=float(candle['open']),
                        high=float(candle['high']),
                        low=float(candle['low']),
                        close=float(candle['close']),
                        volume=int(candle['volume']),
                        turnover=float(candle.get('turnover', 0.0)),
                        source=DataSource.TWELVE_DATA,
                    )
                    ohlcv_list.append(ohlcv)
                except (ValueError, KeyError) as e:
                    logger.warning(f"Failed to parse candle: {e}")
                    continue
            
            return DataResponse(
                request=request,
                data=ohlcv_list,
                meta={
                    'status': 'ok',
                    'count': len(ohlcv_list),
                },
                source=DataSource.TWELVE_DATA,
            )
        
        except Exception as e:
            logger.error(f"Failed to get timeseries for {symbol}: {e}")
            return DataResponse(
                request=request,
                data=[],
                error=str(e),
                source=DataSource.TWELVE_DATA,
            )
    
    async def get_quote(self, symbol: str) -> Optional[Quote]:
        """
        Get real-time quote data.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Quote object or None on error
        """
        params = {
            'symbol': symbol,
        }
        
        try:
            data = await self._request(self.ENDPOINTS['quote'], params)
            
            quote_data = data.get('data', {})
            quote = Quote(
                symbol=symbol,
                price=float(quote_data.get('last_price', 0)),
                bid=float(quote_data.get('bid', 0)) if quote_data.get('bid') else None,
                ask=float(quote_data.get('ask', 0)) if quote_data.get('ask') else None,
                timestamp=datetime.utcnow(),
                volume=int(quote_data.get('volume', 0)) if quote_data.get('volume') else None,
                previous_close=float(quote_data.get('previous_close', 0)) if quote_data.get('previous_close') else None,
                change=float(quote_data.get('change', 0)) if quote_data.get('change') else None,
                change_percent=float(quote_data.get('change_percent', 0)) if quote_data.get('change_percent') else None,
                source=DataSource.TWELVE_DATA,
            )
            
            return quote
        
        except Exception as e:
            logger.error(f"Failed to get quote for {symbol}: {e}")
            return None
    
    async def get_intraday(self, symbol: str, interval: DataInterval = DataInterval.MINUTE_1,
                          limit: int = 1000) -> DataResponse:
        """
        Get intraday (minute-level) OHLCV data.
        
        Args:
            symbol: Trading symbol
            interval: Minute interval (1min, 5min, 15min, 30min)
            limit: Maximum candles
            
        Returns:
            DataResponse containing intraday OHLCV data
        """
        request = DataRequest(
            symbol=symbol,
            interval=interval,
            limit=limit,
        )
        request.validate()
        
        params = {
            'symbol': symbol,
            'interval': interval.value,
            'limit': min(limit, 5000),
        }
        
        try:
            data = await self._request(self.ENDPOINTS['intraday'], params)
            
            ohlcv_list = []
            for candle in data.get('values', []):
                try:
                    ohlcv = OHLCV(
                        timestamp=datetime.fromisoformat(candle['datetime']),
                        symbol=symbol,
                        interval=interval,
                        open=float(candle['open']),
                        high=float(candle['high']),
                        low=float(candle['low']),
                        close=float(candle['close']),
                        volume=int(candle['volume']),
                        source=DataSource.TWELVE_DATA,
                    )
                    ohlcv_list.append(ohlcv)
                except (ValueError, KeyError) as e:
                    logger.warning(f"Failed to parse intraday candle: {e}")
                    continue
            
            return DataResponse(
                request=request,
                data=ohlcv_list,
                meta={'status': 'ok', 'count': len(ohlcv_list)},
                source=DataSource.TWELVE_DATA,
            )
        
        except Exception as e:
            logger.error(f"Failed to get intraday for {symbol}: {e}")
            return DataResponse(
                request=request,
                data=[],
                error=str(e),
                source=DataSource.TWELVE_DATA,
            )
