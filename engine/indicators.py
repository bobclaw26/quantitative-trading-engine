import math
import logging

logger = logging.getLogger(__name__)

def calculate_sma(prices, period=20):
    """Calculate Simple Moving Average"""
    if len(prices) < period:
        return None
    return sum(prices[:period]) / period

def calculate_std_dev(prices, mean, period=20):
    """Calculate standard deviation"""
    if len(prices) < period:
        return None
    variance = sum((p - mean) ** 2 for p in prices[:period]) / period
    return math.sqrt(variance)

def calculate_bollinger_bands(prices, period=20, num_std=2):
    """Calculate Bollinger Bands"""
    sma = calculate_sma(prices, period)
    if not sma:
        return None, None, None
    
    std = calculate_std_dev(prices, sma, period)
    if not std:
        return None, None, None
    
    upper = sma + (num_std * std)
    lower = sma - (num_std * std)
    return upper, sma, lower

def calculate_rsi(prices, period=14):
    """Calculate Relative Strength Index"""
    if len(prices) < period + 1:
        return None
    
    gains = []
    losses = []
    
    for i in range(1, period + 1):
        change = prices[i] - prices[i-1]
        if change > 0:
            gains.append(change)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(change))
    
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    
    if avg_loss == 0:
        return 100 if avg_gain > 0 else 50
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_volatility(prices, period=30):
    """Calculate realized volatility"""
    if len(prices) < period + 1:
        return None
    
    returns = []
    for i in range(1, period + 1):
        ret = (prices[i] - prices[i-1]) / prices[i-1]
        returns.append(ret)
    
    mean_ret = sum(returns) / len(returns)
    variance = sum((r - mean_ret) ** 2 for r in returns) / len(returns)
    volatility = math.sqrt(variance)
    return volatility

def calculate_momentum(prices, period=90):
    """Calculate 90-day momentum"""
    if len(prices) < period + 1:
        return None
    
    current = prices[0]
    past = prices[period]
    momentum = (current - past) / past * 100
    return momentum

def calculate_all_indicators(prices):
    """Calculate all technical indicators for a price series"""
    if not prices or len(prices) < 100:
        return None
    
    try:
        indicators = {
            'current_price': prices[0],
            'sma20': calculate_sma(prices, 20),
            'sma90': calculate_sma(prices, 90),
            'rsi': calculate_rsi(prices, 14),
            'volatility': calculate_volatility(prices, 30),
            'momentum': calculate_momentum(prices, 90),
        }
        
        upper, middle, lower = calculate_bollinger_bands(prices, 20, 2)
        indicators['bb_upper'] = upper
        indicators['bb_middle'] = middle
        indicators['bb_lower'] = lower
        
        # Filter out None values
        return {k: v for k, v in indicators.items() if v is not None}
    except Exception as e:
        logger.error(f"Indicator calculation error: {e}")
        return None
