import logging
from datetime import datetime
from uuid import uuid4
from api_client import client
from database import db
from config import SYMBOLS

logger = logging.getLogger(__name__)

def ingest_market_data():
    """Fetch latest prices and store in database"""
    run_id = f"INGEST-{datetime.utcnow().isoformat()}-{uuid4().hex[:8]}"
    timestamp = int(datetime.utcnow().timestamp() * 1000)  # Unix ms
    
    logger.info(f"Starting market data ingestion: {run_id}")
    
    inserted = 0
    errors = []
    
    for symbol in SYMBOLS:
        try:
            logger.info(f"Fetching {symbol}...")
            quote = client.get_quote(symbol)
            
            if not quote or quote['close'] == 0:
                logger.warning(f"Invalid quote for {symbol}")
                continue
            
            query = """
            INSERT OR REPLACE INTO market_prices (symbol, timestamp, close, open, high, low, volume, ingestion_run_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            params = (
                quote['symbol'],
                timestamp,
                quote['close'],
                quote['open'],
                quote['high'],
                quote['low'],
                quote['volume'],
                run_id
            )
            
            db.execute(query, params)
            inserted += 1
            logger.info(f"Inserted {symbol}: ${quote['close']}")
        except Exception as e:
            error_msg = f"{symbol}: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)
    
    # Log ingestion status
    status = "success" if errors == [] else "partial"
    error_msg = " | ".join(errors) if errors else None
    
    log_query = """
    INSERT INTO ingestion_logs (run_id, timestamp, status, records_inserted, error_message)
    VALUES (?, ?, ?, ?, ?)
    """
    db.execute(log_query, (run_id, datetime.utcnow(), status, inserted, error_msg))
    
    logger.info(f"Ingestion complete: {inserted} records inserted")
    return {'run_id': run_id, 'status': status, 'records': inserted, 'errors': errors}

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    ingest_market_data()
