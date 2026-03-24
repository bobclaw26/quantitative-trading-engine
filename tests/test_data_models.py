"""
Unit tests for data models (OHLCV, Tick, Quote, etc.).
"""

import pytest
from datetime import datetime
from src.data.models import (
    OHLCV, Tick, Quote, DataInterval, DataSource, 
    DataRequest, DataResponse
)


class TestOHLCV:
    """Test OHLCV candle model."""
    
    def test_ohlcv_creation(self):
        """Test creating a valid OHLCV candle."""
        now = datetime.utcnow()
        candle = OHLCV(
            timestamp=now,
            symbol='AAPL',
            interval=DataInterval.DAY_1,
            open=150.0,
            high=155.0,
            low=149.0,
            close=152.0,
            volume=1000000,
            source=DataSource.TWELVE_DATA
        )
        
        assert candle.symbol == 'AAPL'
        assert candle.close == 152.0
        assert candle.volume == 1000000
    
    def test_ohlcv_validation_high_low(self):
        """Test that high < low is caught."""
        now = datetime.utcnow()
        with pytest.raises(ValueError):
            OHLCV(
                timestamp=now,
                symbol='AAPL',
                interval=DataInterval.DAY_1,
                open=150.0,
                high=149.0,  # Less than low
                low=149.0,
                close=152.0,
                volume=1000000
            )
    
    def test_ohlcv_validation_high_bounds(self):
        """Test that high is not less than open/close."""
        now = datetime.utcnow()
        with pytest.raises(ValueError):
            OHLCV(
                timestamp=now,
                symbol='AAPL',
                interval=DataInterval.DAY_1,
                open=150.0,
                high=148.0,  # Less than open
                low=147.0,
                close=152.0,
                volume=1000000
            )
    
    def test_ohlcv_validation_volume(self):
        """Test that negative volume is caught."""
        now = datetime.utcnow()
        with pytest.raises(ValueError):
            OHLCV(
                timestamp=now,
                symbol='AAPL',
                interval=DataInterval.DAY_1,
                open=150.0,
                high=155.0,
                low=149.0,
                close=152.0,
                volume=-100  # Negative volume
            )
    
    def test_ohlcv_to_dict(self):
        """Test OHLCV serialization."""
        now = datetime.utcnow()
        candle = OHLCV(
            timestamp=now,
            symbol='AAPL',
            interval=DataInterval.HOUR_1,
            open=150.0,
            high=155.0,
            low=149.0,
            close=152.0,
            volume=1000000
        )
        
        data = candle.to_dict()
        assert data['symbol'] == 'AAPL'
        assert data['interval'] == '1h'
        assert data['close'] == 152.0


class TestTick:
    """Test Tick data model."""
    
    def test_tick_creation(self):
        """Test creating a tick."""
        now = datetime.utcnow()
        tick = Tick(
            timestamp=now,
            symbol='AAPL',
            price=150.5,
            bid=150.4,
            ask=150.6,
            volume=1000
        )
        
        assert tick.symbol == 'AAPL'
        assert tick.price == 150.5
        assert tick.bid == 150.4
    
    def test_tick_to_dict(self):
        """Test tick serialization."""
        now = datetime.utcnow()
        tick = Tick(
            timestamp=now,
            symbol='AAPL',
            price=150.5
        )
        
        data = tick.to_dict()
        assert data['symbol'] == 'AAPL'
        assert data['price'] == 150.5


class TestQuote:
    """Test Quote data model."""
    
    def test_quote_creation(self):
        """Test creating a quote."""
        now = datetime.utcnow()
        quote = Quote(
            symbol='AAPL',
            price=150.5,
            bid=150.4,
            ask=150.6,
            timestamp=now,
            volume=100000,
            change=2.5,
            change_percent=1.69
        )
        
        assert quote.symbol == 'AAPL'
        assert quote.price == 150.5
        assert quote.change_percent == 1.69
    
    def test_quote_to_dict(self):
        """Test quote serialization."""
        quote = Quote(
            symbol='AAPL',
            price=150.5
        )
        
        data = quote.to_dict()
        assert data['symbol'] == 'AAPL'
        assert data['price'] == 150.5


class TestDataInterval:
    """Test DataInterval enum."""
    
    def test_interval_values(self):
        """Test interval enum values."""
        assert DataInterval.MINUTE_1.value == '1min'
        assert DataInterval.HOUR_1.value == '1h'
        assert DataInterval.DAY_1.value == '1d'
        assert DataInterval.WEEK_1.value == '1w'
        assert DataInterval.MONTH_1.value == '1mo'


class TestDataRequest:
    """Test DataRequest model."""
    
    def test_request_creation(self):
        """Test creating a data request."""
        now = datetime.utcnow()
        req = DataRequest(
            symbol='AAPL',
            interval=DataInterval.DAY_1,
            start_date=now,
            limit=1000
        )
        
        assert req.symbol == 'AAPL'
        assert req.interval == DataInterval.DAY_1
    
    def test_request_validation(self):
        """Test request validation."""
        now = datetime.utcnow()
        
        # Valid request should pass
        req = DataRequest(
            symbol='AAPL',
            start_date=now,
            end_date=now
        )
        req.validate()  # Should not raise
        
        # Start > end should fail
        with pytest.raises(ValueError):
            req = DataRequest(
                symbol='AAPL',
                start_date=now,
                end_date=now - pytest.importorskip('datetime').timedelta(days=1)
            )
            req.validate()
        
        # Invalid order should fail
        with pytest.raises(ValueError):
            req = DataRequest(symbol='AAPL', order='invalid')
            req.validate()


class TestDataResponse:
    """Test DataResponse model."""
    
    def test_response_creation(self):
        """Test creating a response."""
        req = DataRequest(symbol='AAPL')
        resp = DataResponse(request=req)
        
        assert resp.request.symbol == 'AAPL'
        assert len(resp.data) == 0
        assert resp.error is None
    
    def test_response_is_success(self):
        """Test success determination."""
        req = DataRequest(symbol='AAPL')
        
        # Empty response with no error
        resp = DataResponse(request=req)
        assert not resp.is_success()
        
        # Error response
        resp = DataResponse(request=req, error="API Error")
        assert not resp.is_success()
        
        # Response with data
        now = datetime.utcnow()
        candle = OHLCV(
            timestamp=now,
            symbol='AAPL',
            interval=DataInterval.DAY_1,
            open=150.0,
            high=155.0,
            low=149.0,
            close=152.0,
            volume=1000000
        )
        resp = DataResponse(request=req, data=[candle])
        assert resp.is_success()
    
    def test_response_to_dict(self):
        """Test response serialization."""
        req = DataRequest(symbol='AAPL')
        resp = DataResponse(request=req)
        
        data = resp.to_dict()
        assert data['request']['symbol'] == 'AAPL'
        assert data['error'] is None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
