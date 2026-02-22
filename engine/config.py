import os
from pathlib import Path

# API Keys
ALPHA_VANTAGE_API_KEY = "HHTBY253E9Q9RPVV"

# Trading Engine
TRADING_CAPITAL = 100000
RISK_PER_TRADE = 0.01  # 1% per trade
MAX_POSITIONS = 50

# Symbols to track
SYMBOLS = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA', 'JPM', 'BAC', 'WFC', 'XOM', 'CVX', 'MCD', 'NKE', 'COST']

# Stat Arb pairs
PAIRS = [
    ('MSFT', 'GOOGL'),
    ('JPM', 'BAC'),
    ('XOM', 'CVX'),
    ('TSLA', 'GOOGL'),
    ('NVDA', 'META'),
]

# Paths
WORKSPACE_DIR = Path(__file__).parent.parent
LOG_DIR = WORKSPACE_DIR / "logs"
DATA_DIR = WORKSPACE_DIR / "data"

LOG_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)

# API Settings
API_CALL_DELAY = 0.5  # seconds between API calls (Alpha Vantage free tier limit)
MAX_RETRIES = 3
