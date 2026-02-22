import logging
from datetime import datetime
from database import db
from indicators import calculate_all_indicators
from strategies import MeanReversionStrategy, MomentumStrategy, StatisticalArbitrageStrategy, merge_signals
from config import SYMBOLS

logger = logging.getLogger(__name__)

def load_price_history(symbol, limit=100):
    """Load price history for a symbol"""
    query = "SELECT close FROM market_prices WHERE symbol = ? ORDER BY timestamp DESC LIMIT ?"
    results = db.execute(query, (symbol, limit))
    if not results:
        return []
    return [float(row['close']) for row in results]

def generate_signals():
    """Generate trading signals from all strategies"""
    logger.info("Starting signal generation...")
    
    # Load current prices for all symbols
    price_query = "SELECT DISTINCT symbol FROM market_prices"
    symbol_results = db.execute(price_query)
    
    if not symbol_results:
        logger.warning("No price data available")
        return
    
    symbols = [row['symbol'] for row in symbol_results]
    
    # Get latest prices
    price_dict = {}
    for sym in symbols:
        price_query = "SELECT close FROM market_prices WHERE symbol = ? ORDER BY timestamp DESC LIMIT 1"
        price_results = db.execute(price_query, (sym,))
        if price_results:
            price_dict[sym] = float(price_results[0]['close'])
    
    if not price_dict:
        logger.warning("No price data available")
        return
    
    # Calculate indicators for all symbols
    indicators_dict = {}
    mean_rev_signals = {}
    
    for symbol in SYMBOLS:
        if symbol not in price_dict:
            continue
        
        try:
            prices = load_price_history(symbol, 100)
            if not prices:
                continue
            
            indicators = calculate_all_indicators(prices)
            if not indicators:
                continue
            
            indicators_dict[symbol] = indicators
            
            # Mean reversion
            signal = MeanReversionStrategy.generate_signal(indicators)
            if signal and signal['signal'] != 0:
                mean_rev_signals[symbol] = signal
                logger.info(f"{symbol} Mean Reversion: signal={signal['signal']}, strength={signal['signal_strength']:.2f}")
        except Exception as e:
            logger.error(f"Error processing {symbol}: {e}")
    
    # Generate momentum signals
    momentum_signals = MomentumStrategy.generate_signals(indicators_dict)
    for symbol, sig in momentum_signals.items():
        logger.info(f"{symbol} Momentum: signal={sig['signal']}")
    
    # Generate stat arb signals
    stat_arb_signals = StatisticalArbitrageStrategy.generate_signals(price_dict)
    for symbol, sig in stat_arb_signals.items():
        logger.info(f"{symbol} Stat Arb: signal={sig['signal']}")
    
    # Merge all signals
    all_signals = merge_signals(mean_rev_signals, momentum_signals, stat_arb_signals)
    
    if not all_signals:
        logger.info("No signals generated")
        return
    
    # Insert signals into database
    insert_query = """
    INSERT OR REPLACE INTO signals 
    (symbol, strategy_type, signal, signal_strength, z_score, momentum_score, rsi, realized_vol, recommended_size, timestamp)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    
    for sig in all_signals:
        try:
            db.execute(insert_query, (
                sig['symbol'],
                sig['strategy_type'],
                sig['signal'],
                sig['signal_strength'],
                sig.get('z_score', 0),
                sig.get('momentum', 0),
                sig.get('rsi', 50),
                sig.get('realized_vol', 0.02),
                sig.get('recommended_size', 0),
                sig['timestamp'],
            ))
        except Exception as e:
            logger.error(f"Error inserting signal for {sig['symbol']}: {e}")
    
    logger.info(f"Signal generation complete: {len(all_signals)} signals inserted")
    return all_signals

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    generate_signals()
