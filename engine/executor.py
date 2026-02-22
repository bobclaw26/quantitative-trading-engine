import logging
from datetime import datetime
from database import db
from config import TRADING_CAPITAL, RISK_PER_TRADE

logger = logging.getLogger(__name__)

def load_positions():
    """Load all open positions"""
    query = "SELECT * FROM paper_positions WHERE quantity != 0"
    results = db.execute(query)
    return {row['symbol']: dict(row) for row in results}

def load_signals():
    """Load latest signals for each symbol"""
    query = "SELECT * FROM signals ORDER BY timestamp DESC"
    all_signals = db.execute(query)
    
    # Get latest signal for each symbol/strategy combination
    latest = {}
    for sig in all_signals:
        key = (sig['symbol'], sig['strategy_type'])
        if key not in latest:
            latest[key] = sig
    
    return {sig['symbol']: dict(sig) for sig in latest.values()}

def load_prices():
    """Load current prices"""
    query = "SELECT DISTINCT symbol FROM market_prices"
    symbols = db.execute(query)
    
    prices = {}
    for sym_row in symbols:
        symbol = sym_row['symbol']
        price_query = "SELECT close FROM market_prices WHERE symbol = ? ORDER BY timestamp DESC LIMIT 1"
        price_results = db.execute(price_query, (symbol,))
        if price_results:
            prices[symbol] = float(price_results[0]['close'])
    
    return prices

def load_portfolio_value():
    """Load current portfolio value"""
    query = "SELECT total_portfolio_value FROM portfolio_summary ORDER BY timestamp DESC LIMIT 1"
    results = db.execute(query)
    if results:
        return float(results[0]['total_portfolio_value'])
    return TRADING_CAPITAL

def execute_trades():
    """Match signals to prices and execute trades"""
    logger.info("Starting trade execution...")
    
    positions = load_positions()
    signals = load_signals()
    prices = load_prices()
    portfolio_value = load_portfolio_value()
    
    trades = []
    timestamp = datetime.utcnow()
    capital_per_trade = portfolio_value * RISK_PER_TRADE
    
    for symbol, signal in signals.items():
        if symbol not in prices:
            logger.warning(f"No price for {symbol}")
            continue
        
        current_price = prices[symbol]
        existing_pos = positions.get(symbol)
        
        signal_val = signal.get('signal', 0)
        signal_strength = signal.get('signal_strength', 0)
        
        if signal_val == 0:
            # No signal
            if existing_pos and existing_pos['quantity'] != 0:
                # Close position
                side = 'SELL' if existing_pos['quantity'] > 0 else 'BUY'
                quantity = abs(existing_pos['quantity'])
                trades.append({
                    'symbol': symbol,
                    'side': side,
                    'quantity': quantity,
                    'price': current_price,
                    'strategy_type': existing_pos['strategy_type'],
                    'timestamp': timestamp,
                })
                logger.info(f"Closing {symbol}: {side} {quantity} @ ${current_price:.2f}")
        
        elif signal_val == 1 and not existing_pos:
            # Long signal, no existing position
            position_size = capital_per_trade / current_price * signal_strength
            quantity = int(position_size)
            if quantity > 0:
                trades.append({
                    'symbol': symbol,
                    'side': 'BUY',
                    'quantity': quantity,
                    'price': current_price,
                    'strategy_type': signal['strategy_type'],
                    'timestamp': timestamp,
                })
                logger.info(f"Opening LONG {symbol}: BUY {quantity} @ ${current_price:.2f}")
        
        elif signal_val == -1 and not existing_pos:
            # Short signal, no existing position
            position_size = capital_per_trade / current_price * signal_strength
            quantity = int(position_size)
            if quantity > 0:
                trades.append({
                    'symbol': symbol,
                    'side': 'SELL',
                    'quantity': quantity,
                    'price': current_price,
                    'strategy_type': signal['strategy_type'],
                    'timestamp': timestamp,
                })
                logger.info(f"Opening SHORT {symbol}: SELL {quantity} @ ${current_price:.2f}")
    
    # Insert trades and update positions
    if trades:
        trade_query = "INSERT INTO trade_log (symbol, side, quantity, price, pnl, strategy_type, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)"
        
        for trade in trades:
            db.execute(trade_query, (
                trade['symbol'],
                trade['side'],
                trade['quantity'],
                trade['price'],
                0,  # Will calculate PnL later
                trade['strategy_type'],
                trade['timestamp'],
            ))
            
            # Update position
            if trade['side'] == 'BUY':
                pos_query = """
                INSERT OR REPLACE INTO paper_positions (symbol, quantity, entry_price, current_price, unrealized_pnl, position_value, strategy_type, entry_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """
                db.execute(pos_query, (
                    trade['symbol'],
                    trade['quantity'],
                    trade['price'],
                    trade['price'],
                    0,
                    trade['quantity'] * trade['price'],
                    trade['strategy_type'],
                    timestamp,
                ))
            elif trade['side'] == 'SELL':
                # Close position
                db.execute("DELETE FROM paper_positions WHERE symbol=?", (trade['symbol'],))
        
        logger.info(f"Executed {len(trades)} trades")
    else:
        logger.info("No trades executed")
    
    # Update unrealized PnL for all positions
    positions = load_positions()
    for symbol, pos in positions.items():
        if symbol in prices:
            unrealized = (prices[symbol] - pos['entry_price']) * pos['quantity']
            position_value = prices[symbol] * pos['quantity']
            db.execute(
                "UPDATE paper_positions SET unrealized_pnl=?, current_price=?, position_value=? WHERE symbol=?",
                (unrealized, prices[symbol], position_value, symbol)
            )
    
    return trades

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    execute_trades()
