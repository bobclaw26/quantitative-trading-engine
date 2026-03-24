"""
Data models for OHLCV (Open, High, Low, Close, Volume) and tick data.
Designed for compatibility with both real-time and historical data sources.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List
from enum import Enum


class DataInterval(str, Enum):
    """Supported time intervals for OHLCV data."""
    MINUTE_1 = "1min"
    MINUTE_5 = "5min"
    MINUTE_15 = "15min"
    MINUTE_30 = "30min"
    HOUR_1 = "1h"
    HOUR_4 = "4h"
    DAY_1 = "1d"
    WEEK_1 = "1w"
    MONTH_1 = "1mo"


class DataSource(str, Enum):
    """Supported data sources."""
    TWELVE_DATA = "twelve_data"
    ALPHA_VANTAGE = "alpha_vantage"
    CACHE = "cache"


@dataclass
class OHLCV:
    """
    OHLCV (Open, High, Low, Close, Volume) candle data.
    
    Standard candlestick data point with timestamp, prices, and volume.
    """
    timestamp: datetime
    symbol: str
    interval: DataInterval
    open: float
    high: float
    low: float
    close: float
    volume: int
    source: DataSource = DataSource.TWELVE_DATA
    
    # Optional metadata
    turnover: Optional[float] = None  # Total value traded
    
    def __post_init__(self):
        """Validate OHLCV data integrity."""
        if self.high < self.low:
            raise ValueError(f"High ({self.high}) cannot be less than Low ({self.low})")
        if self.high < self.open or self.high < self.close:
            raise ValueError("High must be >= both open and close")
        if self.low > self.open or self.low > self.close:
            raise ValueError("Low must be <= both open and close")
        if self.volume < 0:
            raise ValueError("Volume cannot be negative")
    
    def to_dict(self) -> dict:
        """Convert OHLCV to dictionary."""
        return {
            'timestamp': self.timestamp.isoformat(),
            'symbol': self.symbol,
            'interval': self.interval.value,
            'open': self.open,
            'high': self.high,
            'low': self.low,
            'close': self.close,
            'volume': self.volume,
            'source': self.source.value,
            'turnover': self.turnover,
        }


@dataclass
class Tick:
    """
    Individual tick data (trade-level data).
    
    Represents a single transaction or quote update.
    """
    timestamp: datetime
    symbol: str
    price: float
    bid: Optional[float] = None
    ask: Optional[float] = None
    bid_volume: Optional[int] = None
    ask_volume: Optional[int] = None
    volume: Optional[int] = None
    source: DataSource = DataSource.TWELVE_DATA
    
    def to_dict(self) -> dict:
        """Convert Tick to dictionary."""
        return {
            'timestamp': self.timestamp.isoformat(),
            'symbol': self.symbol,
            'price': self.price,
            'bid': self.bid,
            'ask': self.ask,
            'bid_volume': self.bid_volume,
            'ask_volume': self.ask_volume,
            'volume': self.volume,
            'source': self.source.value,
        }


@dataclass
class Quote:
    """
    Real-time quote data (latest bid/ask/price).
    
    Lightweight data for fast market updates.
    """
    symbol: str
    price: float
    bid: Optional[float] = None
    ask: Optional[float] = None
    timestamp: Optional[datetime] = None
    volume: Optional[int] = None
    previous_close: Optional[float] = None
    change: Optional[float] = None
    change_percent: Optional[float] = None
    source: DataSource = DataSource.TWELVE_DATA
    
    def to_dict(self) -> dict:
        """Convert Quote to dictionary."""
        return {
            'symbol': self.symbol,
            'price': self.price,
            'bid': self.bid,
            'ask': self.ask,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'volume': self.volume,
            'previous_close': self.previous_close,
            'change': self.change,
            'change_percent': self.change_percent,
            'source': self.source.value,
        }


@dataclass
class DataRequest:
    """
    Request for data from the API.
    
    Encapsulates parameters for data queries.
    """
    symbol: str
    interval: DataInterval = DataInterval.DAY_1
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    limit: Optional[int] = None
    order: str = 'asc'  # 'asc' or 'desc'
    
    def validate(self):
        """Validate request parameters."""
        if not self.symbol:
            raise ValueError("Symbol is required")
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValueError("start_date cannot be after end_date")
        if self.order not in ('asc', 'desc'):
            raise ValueError("order must be 'asc' or 'desc'")


@dataclass
class DataResponse:
    """
    Response from data API queries.
    
    Contains queried data and metadata.
    """
    request: DataRequest
    data: List[OHLCV] = field(default_factory=list)
    meta: dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    source: DataSource = DataSource.TWELVE_DATA
    error: Optional[str] = None
    
    def is_success(self) -> bool:
        """Check if response contains valid data."""
        return self.error is None and len(self.data) > 0
    
    def to_dict(self) -> dict:
        """Convert response to dictionary."""
        return {
            'request': {
                'symbol': self.request.symbol,
                'interval': self.request.interval.value,
                'start_date': self.request.start_date.isoformat() if self.request.start_date else None,
                'end_date': self.request.end_date.isoformat() if self.request.end_date else None,
            },
            'data': [d.to_dict() for d in self.data],
            'meta': self.meta,
            'timestamp': self.timestamp.isoformat(),
            'source': self.source.value,
            'error': self.error,
        }
