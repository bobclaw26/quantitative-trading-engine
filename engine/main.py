#!/usr/bin/env python3
import sys
import logging
from datetime import datetime
from database import db
from ingestion import ingest_market_data
from signal_generator import generate_signals
from executor import execute_trades
from portfolio import calculate_portfolio_metrics

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/bob/.openclaw/workspace/trading-engine/logs/trading_engine.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def run_market_data_ingestion():
    """Run market data ingestion workflow"""
    logger.info("=" * 80)
    logger.info("WORKFLOW 1: Market Data Ingestion")
    logger.info("=" * 80)
    try:
        result = ingest_market_data()
        logger.info(f"✓ Ingestion complete: {result['records']} records")
        return True
    except Exception as e:
        logger.error(f"✗ Ingestion failed: {e}")
        return False

def run_signal_generation():
    """Run signal generation workflow"""
    logger.info("=" * 80)
    logger.info("WORKFLOW 2: Signal Generation")
    logger.info("=" * 80)
    try:
        signals = generate_signals()
        if signals:
            logger.info(f"✓ Signal generation complete: {len(signals)} signals")
        else:
            logger.info("✓ Signal generation complete: no signals")
        return True
    except Exception as e:
        logger.error(f"✗ Signal generation failed: {e}")
        return False

def run_trade_execution():
    """Run trade execution workflow"""
    logger.info("=" * 80)
    logger.info("WORKFLOW 3: Trade Execution")
    logger.info("=" * 80)
    try:
        trades = execute_trades()
        logger.info(f"✓ Trade execution complete: {len(trades)} trades")
        return True
    except Exception as e:
        logger.error(f"✗ Trade execution failed: {e}")
        return False

def run_portfolio_aggregation():
    """Run portfolio aggregation workflow"""
    logger.info("=" * 80)
    logger.info("WORKFLOW 4: Portfolio Aggregation")
    logger.info("=" * 80)
    try:
        metrics = calculate_portfolio_metrics()
        logger.info(f"✓ Portfolio aggregation complete")
        logger.info(f"  Portfolio Value: ${metrics['portfolio']['total_value']:.2f}")
        logger.info(f"  P&L: ${metrics['portfolio']['unrealized_pnl']:.2f}")
        logger.info(f"  Positions: {metrics['portfolio']['num_positions']}")
        return True
    except Exception as e:
        logger.error(f"✗ Portfolio aggregation failed: {e}")
        return False

def initialize_system():
    """Initialize database and tables"""
    logger.info("Initializing trading engine database...")
    try:
        db.create_tables()
        logger.info("✓ Database initialized")
        return True
    except Exception as e:
        logger.error(f"✗ Database initialization failed: {e}")
        return False

def run_all():
    """Run all workflows in sequence"""
    logger.info("\n" + "=" * 80)
    logger.info(f"TRADING ENGINE STARTED - {datetime.utcnow().isoformat()}")
    logger.info("=" * 80 + "\n")
    
    success = True
    success = run_market_data_ingestion() and success
    success = run_signal_generation() and success
    success = run_trade_execution() and success
    success = run_portfolio_aggregation() and success
    
    logger.info("\n" + "=" * 80)
    if success:
        logger.info("✓ ALL WORKFLOWS COMPLETED SUCCESSFULLY")
    else:
        logger.info("✗ SOME WORKFLOWS FAILED - CHECK LOGS")
    logger.info("=" * 80 + "\n")
    
    return success

if __name__ == "__main__":
    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == "init":
            initialize_system()
        elif command == "ingest":
            run_market_data_ingestion()
        elif command == "signals":
            run_signal_generation()
        elif command == "execute":
            run_trade_execution()
        elif command == "portfolio":
            run_portfolio_aggregation()
        elif command == "all":
            run_all()
        else:
            print(f"Unknown command: {command}")
            print("Usage: python main.py [init|ingest|signals|execute|portfolio|all]")
    else:
        run_all()
