import requests
import time
import logging
from config import ALPHA_VANTAGE_API_KEY, API_CALL_DELAY, MAX_RETRIES

logger = logging.getLogger(__name__)

class AlphaVantageClient:
    BASE_URL = "https://www.alphavantage.co/query"
    
    def __init__(self, api_key=None):
        self.api_key = api_key or ALPHA_VANTAGE_API_KEY
        self.session = requests.Session()
        self.last_call = 0
    
    def _rate_limit(self):
        """Respect Alpha Vantage rate limit (5 calls/min for free tier)"""
        elapsed = time.time() - self.last_call
        if elapsed < API_CALL_DELAY:
            time.sleep(API_CALL_DELAY - elapsed)
        self.last_call = time.time()
    
    def _retry_request(self, params, retries=0):
        """Retry with exponential backoff"""
        try:
            self._rate_limit()
            response = self.session.get(self.BASE_URL, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # Check for API errors
            if 'Error Message' in data:
                raise ValueError(f"API Error: {data['Error Message']}")
            if 'Note' in data:
                logger.warning(f"API Rate limit: {data['Note']}")
                if retries < MAX_RETRIES:
                    time.sleep(60)  # Wait 60 seconds
                    return self._retry_request(params, retries + 1)
            
            return data
        except Exception as e:
            logger.error(f"API request failed: {e}")
            if retries < MAX_RETRIES:
                time.sleep(5 * (retries + 1))
                return self._retry_request(params, retries + 1)
            raise
    
    def get_quote(self, symbol):
        """Get latest quote for a symbol"""
        params = {
            'function': 'GLOBAL_QUOTE',
            'symbol': symbol,
            'apikey': self.api_key
        }
        data = self._retry_request(params)
        
        if 'Global Quote' not in data:
            logger.warning(f"No quote data for {symbol}")
            return None
        
        quote = data['Global Quote']
        return {
            'symbol': symbol,
            'close': float(quote.get('05. price', 0)),
            'open': float(quote.get('02. open', 0)),
            'high': float(quote.get('03. high', 0)),
            'low': float(quote.get('04. low', 0)),
            'volume': int(quote.get('06. volume', 0)),
        }
    
    def get_daily(self, symbol, outputsize='full'):
        """Get daily prices for a symbol (last 20 or 5000 days)"""
        params = {
            'function': 'TIME_SERIES_DAILY',
            'symbol': symbol,
            'outputsize': outputsize,
            'apikey': self.api_key
        }
        data = self._retry_request(params)
        
        if 'Time Series (Daily)' not in data:
            logger.warning(f"No daily data for {symbol}")
            return []
        
        ts = data['Time Series (Daily)']
        prices = []
        for date_str in sorted(ts.keys()):
            day = ts[date_str]
            prices.append({
                'symbol': symbol,
                'date': date_str,
                'close': float(day['4. close']),
                'open': float(day['1. open']),
                'high': float(day['2. high']),
                'low': float(day['3. low']),
                'volume': int(day['5. volume']),
            })
        return prices

# Global client instance
client = AlphaVantageClient()
