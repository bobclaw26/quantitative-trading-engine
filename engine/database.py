import sqlite3
import logging
from contextlib import contextmanager

logger = logging.getLogger(__name__)

# Use SQLite for local implementation
DB_PATH = "/home/bob/.openclaw/workspace/trading-engine/trading_engine.db"

class Database:
    def __init__(self, db_path=None):
        self.db_path = db_path or DB_PATH
        logger.info(f"Using SQLite database: {self.db_path}")
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def execute(self, query, params=None):
        """Execute query and return results"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                
                # Check if it's a SELECT query
                if query.strip().upper().startswith('SELECT'):
                    rows = cursor.fetchall()
                    return [dict(row) for row in rows]
                else:
                    conn.commit()
                    return cursor.rowcount
        except Exception as e:
            logger.error(f"Query error: {e}")
            logger.error(f"Query: {query}")
            logger.error(f"Params: {params}")
            raise
    
    def execute_many(self, query, params_list):
        """Execute query multiple times with different params"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                for params in params_list:
                    cursor.execute(query, params)
                conn.commit()
                return cursor.rowcount
        except Exception as e:
            logger.error(f"Batch query error: {e}")
            raise
    
    def create_tables(self):
        """Create all required tables"""
        queries = [
            # Market prices
            """
            CREATE TABLE IF NOT EXISTS market_prices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                timestamp INTEGER NOT NULL,
                close REAL,
                open REAL,
                high REAL,
                low REAL,
                volume INTEGER,
                ingestion_run_id TEXT,
                UNIQUE(symbol, timestamp)
            );
            """,
            "CREATE INDEX IF NOT EXISTS idx_market_prices_symbol ON market_prices(symbol);",
            "CREATE INDEX IF NOT EXISTS idx_market_prices_timestamp ON market_prices(timestamp);",
            
            # Signals
            """
            CREATE TABLE IF NOT EXISTS signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                strategy_type TEXT,
                signal INTEGER,
                signal_strength REAL,
                z_score REAL,
                momentum_score REAL,
                rsi REAL,
                realized_vol REAL,
                recommended_size REAL,
                timestamp TIMESTAMP
            );
            """,
            "CREATE INDEX IF NOT EXISTS idx_signals_timestamp ON signals(timestamp);",
            "CREATE INDEX IF NOT EXISTS idx_signals_strategy ON signals(strategy_type);",
            
            # Positions
            """
            CREATE TABLE IF NOT EXISTS paper_positions (
                symbol TEXT PRIMARY KEY,
                quantity INTEGER,
                entry_price REAL,
                current_price REAL,
                unrealized_pnl REAL,
                position_value REAL,
                strategy_type TEXT,
                entry_date TIMESTAMP
            );
            """,
            
            # Trade log
            """
            CREATE TABLE IF NOT EXISTS trade_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT,
                side TEXT,
                quantity INTEGER,
                price REAL,
                pnl REAL,
                strategy_type TEXT,
                timestamp TIMESTAMP
            );
            """,
            "CREATE INDEX IF NOT EXISTS idx_trade_log_symbol ON trade_log(symbol);",
            "CREATE INDEX IF NOT EXISTS idx_trade_log_timestamp ON trade_log(timestamp);",
            
            # Portfolio summary
            """
            CREATE TABLE IF NOT EXISTS portfolio_summary (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                total_portfolio_value REAL,
                total_unrealized_pnl REAL,
                realized_pnl REAL,
                sharpe_ratio REAL,
                max_drawdown REAL,
                win_rate REAL,
                cagr REAL,
                num_positions INTEGER,
                num_trades INTEGER,
                timestamp TIMESTAMP
            );
            """,
            "CREATE INDEX IF NOT EXISTS idx_portfolio_summary_timestamp ON portfolio_summary(timestamp);",
            
            # Strategy breakdown
            """
            CREATE TABLE IF NOT EXISTS strategy_breakdown (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                strategy_type TEXT,
                num_positions INTEGER,
                total_position_value REAL,
                total_unrealized_pnl REAL,
                timestamp TIMESTAMP
            );
            """,
            "CREATE INDEX IF NOT EXISTS idx_strategy_breakdown_timestamp ON strategy_breakdown(timestamp);",
            
            # Ingestion logs
            """
            CREATE TABLE IF NOT EXISTS ingestion_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT UNIQUE,
                timestamp TIMESTAMP,
                status TEXT,
                records_inserted INTEGER,
                error_message TEXT
            );
            """,
            "CREATE INDEX IF NOT EXISTS idx_ingestion_logs_timestamp ON ingestion_logs(timestamp);",
        ]
        
        for query in queries:
            try:
                self.execute(query)
                if "CREATE TABLE" in query:
                    table_name = query.split("TABLE")[1].split("(")[0].strip()
                    logger.info(f"Table created/verified: {table_name}")
            except Exception as e:
                # Ignore "already exists" errors
                if "already exists" not in str(e).lower():
                    logger.error(f"Table creation error: {e}")

# Global database instance
db = Database()
