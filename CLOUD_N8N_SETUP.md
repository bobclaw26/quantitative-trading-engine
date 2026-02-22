# Cloud n8n Setup Guide - Fixed for Web Deployment

This guide replaces the original `DEPLOYMENT_RUNBOOK.md` for cloud-compatible n8n deployment.

## Key Changes from Original

✅ **Removed:** n8n Data Tables (not available in cloud/web n8n)  
✅ **Added:** PostgreSQL database integration (cloud-compatible)  
✅ **Fixed:** Custom node references  
✅ **Added:** Environment variable setup

---

## Prerequisites

1. **n8n Cloud Account** (or self-hosted n8n)
2. **PostgreSQL Database** (cloud or self-hosted)
   - Recommended: AWS RDS, Azure Database, Heroku Postgres, or Supabase (free tier available)
3. **Polygon.io API Key** (free tier works)
4. **Alpha Vantage API Key** (free tier for market data)

---

## Step 1: Set Up PostgreSQL

### Option A: Free Cloud PostgreSQL (Recommended)

Use **Supabase** (free tier):

1. Go to https://supabase.com
2. Sign up for free account
3. Create new project
4. In SQL Editor, run this script to create all tables:

```sql
-- Create market_prices table
CREATE TABLE IF NOT EXISTS market_prices (
  id SERIAL PRIMARY KEY,
  symbol TEXT NOT NULL,
  timestamp BIGINT NOT NULL,
  close DECIMAL(10, 2),
  open DECIMAL(10, 2),
  high DECIMAL(10, 2),
  low DECIMAL(10, 2),
  volume BIGINT,
  ingestion_run_id TEXT,
  UNIQUE(symbol, timestamp)
);

CREATE INDEX IF NOT EXISTS idx_market_prices_symbol ON market_prices(symbol);
CREATE INDEX IF NOT EXISTS idx_market_prices_timestamp ON market_prices(timestamp);

-- Create signals table
CREATE TABLE IF NOT EXISTS signals (
  id SERIAL PRIMARY KEY,
  symbol TEXT NOT NULL,
  strategy_type TEXT,
  signal INTEGER,
  signal_strength DECIMAL(3, 2),
  z_score DECIMAL(5, 2),
  momentum_score DECIMAL(10, 2),
  rsi DECIMAL(5, 2),
  realized_vol DECIMAL(5, 4),
  recommended_size DECIMAL(5, 2),
  timestamp TIMESTAMP,
  UNIQUE(symbol, timestamp, strategy_type)
);

CREATE INDEX IF NOT EXISTS idx_signals_timestamp ON signals(timestamp);
CREATE INDEX IF NOT EXISTS idx_signals_strategy ON signals(strategy_type);

-- Create paper_positions table
CREATE TABLE IF NOT EXISTS paper_positions (
  symbol TEXT PRIMARY KEY,
  quantity INTEGER,
  entry_price DECIMAL(10, 2),
  current_price DECIMAL(10, 2),
  unrealized_pnl DECIMAL(15, 2),
  position_value DECIMAL(15, 2),
  strategy_type TEXT,
  entry_date TIMESTAMP
);

-- Create trade_log table
CREATE TABLE IF NOT EXISTS trade_log (
  id SERIAL PRIMARY KEY,
  symbol TEXT,
  side TEXT,
  quantity INTEGER,
  price DECIMAL(10, 2),
  pnl DECIMAL(15, 2),
  strategy_type TEXT,
  timestamp TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_trade_log_symbol ON trade_log(symbol);
CREATE INDEX IF NOT EXISTS idx_trade_log_timestamp ON trade_log(timestamp);

-- Create portfolio_summary table
CREATE TABLE IF NOT EXISTS portfolio_summary (
  id SERIAL PRIMARY KEY,
  total_portfolio_value DECIMAL(15, 2),
  total_unrealized_pnl DECIMAL(15, 2),
  realized_pnl DECIMAL(15, 2),
  sharpe_ratio DECIMAL(5, 2),
  max_drawdown DECIMAL(5, 2),
  win_rate DECIMAL(5, 2),
  cagr DECIMAL(5, 2),
  num_positions INTEGER,
  num_trades INTEGER,
  timestamp TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_portfolio_summary_timestamp ON portfolio_summary(timestamp);

-- Create strategy_breakdown table
CREATE TABLE IF NOT EXISTS strategy_breakdown (
  id SERIAL PRIMARY KEY,
  strategy_type TEXT,
  num_positions INTEGER,
  total_position_value DECIMAL(15, 2),
  total_unrealized_pnl DECIMAL(15, 2),
  timestamp TIMESTAMP,
  UNIQUE(strategy_type, timestamp)
);

CREATE INDEX IF NOT EXISTS idx_strategy_breakdown_timestamp ON strategy_breakdown(timestamp);

-- Create ingestion_logs table
CREATE TABLE IF NOT EXISTS ingestion_logs (
  id SERIAL PRIMARY KEY,
  run_id TEXT UNIQUE,
  timestamp TIMESTAMP,
  status TEXT,
  records_inserted INTEGER,
  error_message TEXT
);

CREATE INDEX IF NOT EXISTS idx_ingestion_logs_timestamp ON ingestion_logs(timestamp);
```

5. **Get connection details:**
   - In Supabase dashboard: Settings → Database → Connection String
   - Copy the PostgreSQL connection string (looks like: `postgresql://user:password@host:5432/database`)

### Option B: Self-Hosted PostgreSQL

If you have your own PostgreSQL instance, get the connection string in this format:
```
postgresql://username:password@hostname:5432/dbname
```

---

## Step 2: Configure n8n PostgreSQL Credentials

1. **In n8n Cloud/Web:**
   - Go to Settings → Credentials
   - Click "New Credential"
   - Select "PostgreSQL"
   - Fill in:
     - **Host:** (from your connection string)
     - **Database:** (from your connection string)
     - **User:** (from your connection string)
     - **Password:** (from your connection string)
     - **Port:** 5432
   - Test connection → Save

2. **Name it:** "PostgreSQL" (referenced in all workflows)

---

## Step 3: Set Environment Variables in n8n

1. In n8n, go to **Settings → Environment Variables**
2. Add these variables:

```
ALPHA_VANTAGE_API_KEY=your_alpha_vantage_key_here
POLYGON_API_KEY=your_polygon_api_key_here
TRADING_CAPITAL=100000
```

Get API keys:
- Alpha Vantage: https://www.alphavantage.co/
- Polygon.io: https://polygon.io/

---

## Step 4: Import Workflows

1. Download the 5 fixed workflow JSON files:
   - `01-data-ingestion-workflow.json`
   - `02-signal-engine-workflow.json`
   - `03-execution-engine-workflow.json`
   - `04-portfolio-aggregator-workflow.json`
   - `05-dashboard-api-workflow.json`

2. In n8n Cloud/Web:
   - Click "+" to create new workflow
   - Click the three-dot menu → "Import from file"
   - Select each JSON file one by one
   - For each workflow:
     - Find all "PostgreSQL" nodes
     - Set the credentials to the PostgreSQL connection you created in Step 2

3. **Verify:** Each workflow should show "PostgreSQL" nodes (not "Data Table" nodes)

---

## Step 5: Activate Workflows

In n8n, for each of the 5 workflows:

1. Open the workflow
2. Click the **toggle** in the top-right to activate it
3. Set cron schedules:
   - **Workflow 1 (Ingestion):** `*/5 * * * *` (every 5 minutes)
   - **Workflow 2 (Signals):** `*/15 * * * *` (every 15 minutes)
   - **Workflow 3 (Execution):** `*/30 * * * *` (every 30 minutes)
   - **Workflow 4 (Portfolio):** `0 * * * *` (every hour)
   - **Workflow 5 (Dashboard):** Always active (webhook)

---

## Step 6: Test the System

### Test 1: Run Market Data Ingestion

1. Open **Workflow 1** (Data Ingestion)
2. Click "Execute Workflow" (play button)
3. Check PostgreSQL:
   ```sql
   SELECT COUNT(*) FROM market_prices;
   ```
   Should return > 0

### Test 2: Run Signal Engine

1. Open **Workflow 2** (Signal Engine)
2. Click "Execute Workflow"
3. Check:
   ```sql
   SELECT COUNT(*) FROM signals;
   ```
   Should return > 0

### Test 3: Run Execution Engine

1. Open **Workflow 3** (Execution Engine)
2. Click "Execute Workflow"
3. Check:
   ```sql
   SELECT COUNT(*) FROM paper_positions WHERE quantity != 0;
   ```
   Should show open positions

### Test 4: Run Portfolio Aggregator

1. Wait 1 hour (or manually trigger Workflow 4)
2. Check:
   ```sql
   SELECT * FROM portfolio_summary ORDER BY timestamp DESC LIMIT 1;
   ```
   Should show portfolio metrics

### Test 5: Test Dashboard API

1. Open **Workflow 5** (Dashboard API)
2. Copy the webhook URL from the "Webhook" node
3. Open browser and visit: `YOUR_WEBHOOK_URL`
4. Should return JSON with portfolio data

---

## Step 7: Deploy Dashboard (Optional)

The `dashboard.html` file included in this folder needs to be hosted. Options:

### Option A: GitHub Pages (Free)

1. Create a GitHub repo
2. Push `dashboard.html` to the repo
3. Enable GitHub Pages in settings
4. Access at: `https://yourusername.github.io/repo-name/dashboard.html`

### Option B: Netlify (Free)

1. Go to https://netlify.com
2. Drag & drop `dashboard.html`
3. Get public URL

### Option C: Self-Host

Host on any web server, then update the API endpoint in `dashboard.html`:

```html
<script>
const API_URL = 'YOUR_WEBHOOK_URL_HERE';
</script>
```

---

## Troubleshooting

### "PostgreSQL connection failed"

- **Check:** Connection string is correct
- **Check:** Database credentials are right
- **Check:** Firewall allows your n8n IP (Supabase: Settings → Database → Allowed IPs)
- **Test:** Run `SELECT 1` in PostgreSQL console

### "No data in workflows"

- **Check:** API keys are valid (test in browser: `https://api.example.com/...`)
- **Check:** Workflows are activated (toggle = ON)
- **Check:** Cron schedule matches actual time
- **Run manually:** Click play button to test immediately

### "Dashboard shows 404"

- **Check:** Webhook URL in `dashboard.html` is correct
- **Check:** Workflow 5 is activated
- **Test:** Curl the webhook URL

```bash
curl 'YOUR_WEBHOOK_URL'
```

---

## Performance Tips

### Reduce API Calls

Change cron schedules to run less frequently:

```
*/5 * * * *   → */15 * * * *   (3x cost savings)
*/15 * * * *  → */30 * * * *   (2x cost savings)
*/30 * * * *  → 0 * * * *      (30x cost savings)
```

### Database Cleanup

Add cleanup jobs in Workflow 4 (Portfolio Aggregator):

```sql
-- Delete market prices older than 90 days
DELETE FROM market_prices WHERE timestamp < EXTRACT(EPOCH FROM NOW()) * 1000 - 90*24*60*60*1000;

-- Delete signals older than 30 days
DELETE FROM signals WHERE timestamp < NOW() - INTERVAL '30 days';

-- Archive closed positions
-- (keep open positions, archive closed ones)
```

---

## Next Steps

1. ✅ Let it run for 30 days in paper trading
2. ✅ Monitor portfolio metrics (Sharpe ratio, drawdown, win rate)
3. ✅ Adjust strategy parameters (see README.md)
4. ✅ Consider live trading integration (with real broker API)

---

## Cost Summary

| Item | Monthly Cost |
|------|--------------|
| n8n Cloud Pro | $25 |
| API Calls (~50k/mo) | $50 |
| PostgreSQL (Supabase free tier) | Free |
| **Total** | **~$75/month** |

---

## Support

- n8n Docs: https://docs.n8n.io
- PostgreSQL Docs: https://www.postgresql.org/docs/
- Community: n8n.io/slack

