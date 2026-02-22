import logging
from datetime import datetime
from flask import Flask, jsonify
from database import db

logger = logging.getLogger(__name__)
app = Flask(__name__)

@app.route('/trading-dashboard', methods=['GET'])
def dashboard_api():
    """Dashboard API endpoint"""
    try:
        # Load portfolio summary
        portfolio_query = "SELECT * FROM portfolio_summary ORDER BY timestamp DESC LIMIT 1"
        portfolio_results = db.execute(portfolio_query)
        portfolio = dict(portfolio_results[0]) if portfolio_results else {}
        
        # Load top movers
        movers_query = "SELECT * FROM paper_positions WHERE quantity != 0 ORDER BY unrealized_pnl DESC LIMIT 10"
        movers = [dict(row) for row in db.execute(movers_query)]
        
        # Load active signals
        signals_query = "SELECT * FROM signals ORDER BY timestamp DESC LIMIT 50"
        signals = [dict(row) for row in db.execute(signals_query)]
        
        # Load strategy breakdown
        breakdown_query = "SELECT * FROM strategy_breakdown ORDER BY timestamp DESC LIMIT 5"
        breakdown = [dict(row) for row in db.execute(breakdown_query)]
        
        # Load recent trades
        trades_query = "SELECT * FROM trade_log ORDER BY timestamp DESC LIMIT 20"
        trades = [dict(row) for row in db.execute(trades_query)]
        
        # Load volatility data
        prices_query = "SELECT * FROM market_prices ORDER BY timestamp DESC LIMIT 100"
        prices = [dict(row) for row in db.execute(prices_query)]
        
        # Calculate volatility by symbol
        volatility_map = {}
        price_map = {}
        for price in prices:
            symbol = price['symbol']
            if symbol not in price_map:
                price_map[symbol] = []
            price_map[symbol].append(float(price['close']))
        
        for symbol, closes in price_map.items():
            if len(closes) > 1:
                returns = []
                for i in range(1, len(closes)):
                    ret = (closes[i] - closes[i-1]) / closes[i-1]
                    returns.append(ret)
                mean_ret = sum(returns) / len(returns)
                variance = sum((r - mean_ret) ** 2 for r in returns) / len(returns)
                volatility_map[symbol] = (variance ** 0.5) * 100
        
        # Assemble response
        return jsonify({
            'metadata': {
                'timestamp': datetime.utcnow().isoformat(),
                'version': '1.0'
            },
            'portfolio': {
                'total_value': float(portfolio.get('total_portfolio_value', 100000)),
                'unrealized_pnl': float(portfolio.get('total_unrealized_pnl', 0)),
                'realized_pnl': float(portfolio.get('realized_pnl', 0)),
                'sharpe_ratio': float(portfolio.get('sharpe_ratio', 0)),
                'max_drawdown': float(portfolio.get('max_drawdown', 0)),
                'win_rate': float(portfolio.get('win_rate', 0)),
                'cagr': float(portfolio.get('cagr', 0)),
                'num_positions': int(portfolio.get('num_positions', 0)),
                'num_trades': int(portfolio.get('num_trades', 0)),
            },
            'top_movers': [
                {
                    'symbol': m['symbol'],
                    'pnl': float(m.get('unrealized_pnl', 0)),
                    'pnl_pct': (float(m.get('unrealized_pnl', 0)) / float(m.get('position_value', 1))) * 100 if m.get('position_value') else 0,
                    'quantity': int(m['quantity']),
                    'entry_price': float(m['entry_price']),
                    'current_price': float(m['current_price']),
                    'strategy': m.get('strategy_type', 'unknown'),
                }
                for m in movers[:5]
            ],
            'signals_summary': {
                'total_active': len(signals),
                'by_strategy': {
                    'mean_reversion': len([s for s in signals if s.get('strategy_type') == 'mean_reversion']),
                    'momentum': len([s for s in signals if s.get('strategy_type') == 'momentum']),
                    'statistical_arbitrage': len([s for s in signals if s.get('strategy_type') == 'statistical_arbitrage']),
                },
                'latest': [
                    {
                        'symbol': s['symbol'],
                        'strategy': s.get('strategy_type', 'unknown'),
                        'signal': 'LONG' if s['signal'] == 1 else 'SHORT' if s['signal'] == -1 else 'NEUTRAL',
                        'strength': float(s.get('signal_strength', 0)),
                    }
                    for s in signals[:10]
                ]
            },
            'strategy_breakdown': [
                {
                    'strategy': b.get('strategy_type', 'unknown'),
                    'positions': int(b.get('num_positions', 0)),
                    'value': float(b.get('total_position_value', 0)),
                    'unrealized_pnl': float(b.get('total_unrealized_pnl', 0)),
                }
                for b in breakdown
            ],
            'recent_trades': [
                {
                    'symbol': t['symbol'],
                    'side': t['side'],
                    'quantity': int(t['quantity']),
                    'price': float(t['price']),
                    'strategy': t.get('strategy_type', 'unknown'),
                    'timestamp': str(t.get('timestamp', '')),
                }
                for t in trades[:10]
            ],
            'volatility': {
                'avg': sum(volatility_map.values()) / len(volatility_map) if volatility_map else 0,
                'by_symbol': [
                    {'symbol': s, 'vol': vol}
                    for s, vol in sorted(volatility_map.items(), key=lambda x: x[1], reverse=True)[:10]
                ]
            }
        })
    except Exception as e:
        logger.error(f"Dashboard API error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    logger.info("Starting trading engine dashboard server on port 5000...")
    app.run(host='0.0.0.0', port=5000, debug=False)
