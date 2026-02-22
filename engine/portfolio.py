import logging
import math
from datetime import datetime
from database import db
from config import TRADING_CAPITAL

logger = logging.getLogger(__name__)

def calculate_portfolio_metrics():
    """Calculate portfolio summary and strategy breakdown"""
    logger.info("Calculating portfolio metrics...")
    
    initial_capital = TRADING_CAPITAL
    
    # Load positions
    pos_query = "SELECT * FROM paper_positions WHERE quantity != 0"
    positions = db.execute(pos_query)
    
    # Load trades
    trade_query = "SELECT * FROM trade_log ORDER BY timestamp DESC LIMIT 1000"
    trades = db.execute(trade_query)
    
    # Calculate unrealized PnL
    total_unrealized_pnl = 0
    for pos in positions:
        total_unrealized_pnl += float(pos.get('unrealized_pnl', 0))
    
    # Calculate realized PnL
    realized_pnl = 0
    buy_trades = {}
    for trade in trades:
        symbol = trade['symbol']
        if trade['side'] == 'BUY':
            if symbol not in buy_trades:
                buy_trades[symbol] = []
            buy_trades[symbol].append(trade)
        elif trade['side'] == 'SELL':
            if symbol in buy_trades and buy_trades[symbol]:
                buy_trade = buy_trades[symbol].pop(0)
                pnl = (float(trade['price']) - float(buy_trade['price'])) * trade['quantity']
                realized_pnl += pnl
    
    # Portfolio metrics
    total_portfolio_value = initial_capital + realized_pnl + total_unrealized_pnl
    
    # Calculate Sharpe ratio (simplified)
    sharpe_ratio = 0.8  # Placeholder
    
    # Max drawdown
    max_drawdown = -5.0  # Placeholder
    
    # Win rate
    winning_trades = sum(1 for t in trades if t['side'] == 'SELL' and t.get('pnl', 0) > 0)
    total_trades = sum(1 for t in trades if t['side'] == 'SELL')
    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
    
    # CAGR
    cagr = ((total_portfolio_value - initial_capital) / initial_capital) * 100
    
    # Insert portfolio summary
    summary_query = """
    INSERT INTO portfolio_summary 
    (total_portfolio_value, total_unrealized_pnl, realized_pnl, sharpe_ratio, max_drawdown, win_rate, cagr, num_positions, num_trades, timestamp)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    
    timestamp = datetime.utcnow()
    db.execute(summary_query, (
        round(total_portfolio_value, 2),
        round(total_unrealized_pnl, 2),
        round(realized_pnl, 2),
        round(sharpe_ratio, 2),
        round(max_drawdown, 2),
        round(win_rate, 2),
        round(cagr, 2),
        len(positions),
        total_trades,
        timestamp,
    ))
    
    logger.info(f"Portfolio: ${total_portfolio_value:.2f} | P&L: ${realized_pnl + total_unrealized_pnl:.2f}")
    
    # Strategy breakdown
    strategy_breakdown = {}
    for pos in positions:
        strategy = pos.get('strategy_type', 'unknown')
        if strategy not in strategy_breakdown:
            strategy_breakdown[strategy] = {
                'num_positions': 0,
                'total_position_value': 0,
                'total_unrealized_pnl': 0,
            }
        strategy_breakdown[strategy]['num_positions'] += 1
        strategy_breakdown[strategy]['total_position_value'] += float(pos.get('position_value', 0))
        strategy_breakdown[strategy]['total_unrealized_pnl'] += float(pos.get('unrealized_pnl', 0))
    
    # Insert strategy breakdown
    breakdown_query = """
    INSERT OR REPLACE INTO strategy_breakdown 
    (strategy_type, num_positions, total_position_value, total_unrealized_pnl, timestamp)
    VALUES (?, ?, ?, ?, ?)
    """
    
    for strategy, data in strategy_breakdown.items():
        db.execute(breakdown_query, (
            strategy,
            data['num_positions'],
            round(data['total_position_value'], 2),
            round(data['total_unrealized_pnl'], 2),
            timestamp,
        ))
        logger.info(f"  {strategy}: {data['num_positions']} positions, ${data['total_position_value']:.2f}")
    
    return {
        'portfolio': {
            'total_value': total_portfolio_value,
            'unrealized_pnl': total_unrealized_pnl,
            'realized_pnl': realized_pnl,
            'num_positions': len(positions),
        },
        'strategies': strategy_breakdown,
    }

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    calculate_portfolio_metrics()
