import logging
from datetime import datetime
from indicators import calculate_all_indicators
from config import PAIRS

logger = logging.getLogger(__name__)

class MeanReversionStrategy:
    """Buy oversold, sell overbought (Bollinger Bands + RSI)"""
    
    @staticmethod
    def generate_signal(indicators):
        if not indicators:
            return None
        
        current = indicators.get('current_price')
        rsi = indicators.get('rsi')
        upper = indicators.get('bb_upper')
        lower = indicators.get('bb_lower')
        
        if not all([current, rsi, upper, lower]):
            return None
        
        signal = 0
        signal_strength = 0
        
        # Long: price below lower band AND RSI < 30
        if current < lower and rsi < 30:
            signal = 1
            signal_strength = min(1.0, (30 - rsi) / 30)
        # Short: price above upper band AND RSI > 70
        elif current > upper and rsi > 70:
            signal = -1
            signal_strength = min(1.0, (rsi - 70) / 30)
        
        return {
            'signal': signal,
            'signal_strength': signal_strength,
            'z_score': (current - indicators.get('sma20', current)) / (upper - lower) if (upper - lower) else 0,
            'rsi': rsi,
            'realized_vol': indicators.get('volatility', 0),
        }

class MomentumStrategy:
    """Trend following via cross-sectional ranking"""
    
    @staticmethod
    def generate_signals(indicators_dict):
        """Generate momentum signals for all symbols
        
        indicators_dict: {symbol: indicators}
        """
        if not indicators_dict:
            return {}
        
        # Sort by momentum score
        sorted_symbols = sorted(
            indicators_dict.items(),
            key=lambda x: x[1].get('momentum', 0),
            reverse=True
        )
        
        threshold_long = max(1, len(sorted_symbols) // 5)  # Top 20%
        threshold_short = max(1, len(sorted_symbols) * 4 // 5)  # Bottom 20%
        
        signals = {}
        for idx, (symbol, indicators) in enumerate(sorted_symbols):
            signal = 0
            signal_strength = 0
            
            if idx < threshold_long:
                signal = 1
                signal_strength = 1.0 - (idx / threshold_long) * 0.3
            elif idx >= threshold_short:
                signal = -1
                signal_strength = ((idx - threshold_short) / (len(sorted_symbols) - threshold_short)) * 0.3 + 0.7
            
            if signal != 0:
                signals[symbol] = {
                    'signal': signal,
                    'signal_strength': signal_strength,
                    'z_score': 0,
                    'momentum': indicators.get('momentum', 0),
                    'rsi': indicators.get('rsi', 50),
                    'realized_vol': indicators.get('volatility', 0.02),
                }
        
        return signals

class StatisticalArbitrageStrategy:
    """Pairs trading with z-score"""
    
    @staticmethod
    def generate_signals(price_dict):
        """Generate stat arb signals
        
        price_dict: {symbol: current_price}
        """
        signals = {}
        
        for long_sym, short_sym in PAIRS:
            if long_sym not in price_dict or short_sym not in price_dict:
                continue
            
            long_price = price_dict[long_sym]
            short_price = price_dict[short_sym]
            
            # Simple z-score (simplified - real calculation would use historical spreads)
            spread = long_price - short_price
            z_score = (spread - 100) / 50  # Placeholder
            
            signal = 0
            if z_score > 2:
                signal = -1  # Short spread
            elif z_score < -2:
                signal = 1   # Long spread
            
            if signal != 0:
                pair_name = f"{long_sym}/{short_sym}"
                signals[pair_name] = {
                    'signal': signal,
                    'signal_strength': min(1.0, abs(z_score) / 3),
                    'z_score': z_score,
                    'momentum': 0,
                    'rsi': 50,
                    'realized_vol': 0.015,
                }
        
        return signals

def merge_signals(mean_rev_signals, momentum_signals, stat_arb_signals):
    """Merge signals from all strategies with position sizing"""
    all_signals = []
    
    for symbol, sig in mean_rev_signals.items():
        all_signals.append({
            'symbol': symbol,
            'strategy_type': 'mean_reversion',
            **sig,
            'timestamp': datetime.utcnow(),
        })
    
    for symbol, sig in momentum_signals.items():
        all_signals.append({
            'symbol': symbol,
            'strategy_type': 'momentum',
            **sig,
            'timestamp': datetime.utcnow(),
        })
    
    for symbol, sig in stat_arb_signals.items():
        all_signals.append({
            'symbol': symbol,
            'strategy_type': 'statistical_arbitrage',
            **sig,
            'timestamp': datetime.utcnow(),
        })
    
    # Add position sizing (volatility-adjusted)
    for signal in all_signals:
        vol = signal.get('realized_vol', 0.02)
        signal['recommended_size'] = round(
            (0.01 / vol) * abs(signal['signal']) * signal.get('signal_strength', 0),
            4
        )
    
    return all_signals
