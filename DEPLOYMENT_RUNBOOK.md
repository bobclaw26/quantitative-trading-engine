# Quantitative Trading Engine - Deployment Runbook

## Overview

This document provides step-by-step instructions to deploy and configure the complete quantitative trading engine in n8n Cloud.

**System Components:**
1. Market Data Ingestion (5-min cron)
2. Signal Generator (15-min cron)
3. Execution Engine (30-min cron)
4. Portfolio Aggregator (hourly cron)
5. Dashboard API (webhook)

**Total execution time:** ~2-3 seconds per cycle
**Cost:** ~$50-100/month on n8n Cloud (Pro plan)

---

## Prerequisites

✅ n8n Cloud account (Enterprise or Pro tier for Data Tables)
✅ Polygon.io API key (free tier is sufficient)
✅ Basic n8n workflow experience
✅ ~30 minutes setup time

**API Keys Required:**
- Polygon.io (https://polygon.io) - Free tier includes historical + real-time quotes
- Optional: Alpha Vantage or Yahoo Finance as fallback

---

## Step 1: Create Data Tables

### 1.1 Access n8n Data Tables

1. Log into n8n Cloud
2. Navigate to **Data** → **Data Tables**
3. Click **+ Create New Table**

### 1.2 Create `market_prices` Table

**Field Configuration:**

| Name | Type | Options |
|------|------|---------|
| symbol | String | Indexed |
| timestamp | DateTime | Indexed |
| close | Number | Decimal |
| open | Number | Decimal |
| high | Number | Decimal |
| low | Number | Decimal |
| volume | Number | Integer |

**Actions:** Click "Create Table"

### 1.3 Create `signals` Table

| Name | Type | Options |
|------|------|---------|
| symbol | String | Indexed |
| strategy_type | String | - |
| signal | Number | Integer |
| signal_strength | Number | Decimal |
| z_score | Number | Decimal |
| momentum_score | Number | Decimal |
| rsi | Number | Decimal |
| realized_vol | Number | Decimal |
| recommended_size | Number | Decimal |
| timestamp | DateTime | Indexed |

### 1.4 Create `paper_positions` Table

| Name | Type | Options |
|------|------|---------|
| symbol | String | Primary Key |
| quantity | Number | Integer |
| entry_price | Number | Decimal |
| current_price | Number | Decimal |
| unrealized_pnl | Number | Decimal |
| position_value | Number | Decimal |
| strategy_type | String | - |
| entry_date | DateTime | - |

### 1.5 Create `trade_log` Table

| Name | Type | Options |
|------|------|---------|
| symbol | String | Indexed |
| side | String | - |
| quantity | Number | Integer |
| price | Number | Decimal |
| pnl | Number | Decimal |
| strategy_type | String | - |
| timestamp | DateTime | Indexed |

### 1.6 Create `portfolio_summary` Table

| Name | Type | Options |
|------|------|---------|
| total_portfolio_value | Number | Decimal |
| total_unrealized_pnl | Number | Decimal |
| realized_pnl | Number | Decimal |
| sharpe_ratio | Number | Decimal |
| max_drawdown | Number | Decimal |
| win_rate | Number | Decimal |
| cagr | Number | Decimal |
| num_positions | Number | Integer |
| num_trades | Number | Integer |
| timestamp | DateTime | Indexed |

### 1.7 Create `strategy_breakdown` Table

| Name | Type | Options |
|------|------|---------|
| strategy_type | String | - |
| num_positions | Number | Integer |
| total_position_value | Number | Decimal |
| total_unrealized_pnl | Number | Decimal |
| timestamp | DateTime | Indexed |

### 1.8 Create `ingestion_logs` Table

| Name | Type | Options |
|------|------|---------|
| run_id | String | Primary Key |
| timestamp | DateTime | Indexed |
| status | String | - |
| records_inserted | Number | Integer |
| error_message | String | - |

---

## Step 2: Set Up API Credentials

### 2.1 Create Polygon.io Credential

1. Go to **Settings** → **Credentials**
2. Click **+ Create New**
3. Choose **Generic API Key**
4. **Name:** "Polygon API"
5. **Header Name:** `Authorization`
6. **Header Value:** `Bearer YOUR_POLYGON_API_KEY`
7. Save

### 2.2 (Optional) Create Alpha Vantage Credential

1. Repeat above
2. **Name:** "Alpha Vantage API"
3. **Environment Variable:** `ALPHA_VANTAGE_API_KEY`

---

## Step 3: Import Workflows

### 3.1 Create Workflow 1: Market Data Ingestion

1. **New Workflow** → **Blank**
2. **Name:** "Quantitative Trading Engine - Market Data Ingestion"
3. Copy from: `01-data-ingestion-workflow.json`
4. **Configure nodes:**
   - **Cron trigger:** Set timezone to your preferred zone
   - **HTTP Request:** Select "Polygon API" credential
   - Save & Activate ✅

### 3.2 Create Workflow 2: Signal Engine

1. **New Workflow** → **Blank**
2. **Name:** "Quantitative Trading Engine - Signal Generator"
3. Copy from: `02-signal-engine-workflow.json`
4. **Configure nodes:**
   - Select correct Data Table names (verify spelling)
   - All Code nodes should run as-is
   - Save & Activate ✅

### 3.3 Create Workflow 3: Execution Engine

1. **New Workflow** → **Blank**
2. **Name:** "Quantitative Trading Engine - Execution Engine"
3. Copy from: `03-execution-engine-workflow.json`
4. **Configure Data Table references**
5. Save & Activate ✅

### 3.4 Create Workflow 4: Portfolio Aggregator

1. **New Workflow** → **Blank**
2. **Name:** "Quantitative Trading Engine - Portfolio Aggregator"
3. Copy from: `04-portfolio-aggregator-workflow.json`
4. Save & Activate ✅

### 3.5 Create Workflow 5: Dashboard API

1. **New Workflow** → **Blank**
2. **Name:** "Quantitative Trading Engine - Dashboard API"
3. Copy from: `05-dashboard-api-workflow.json`
4. **Configure:**
   - Copy the webhook URL after saving
   - All Data Table references must match exactly
5. Save & Activate ✅

---

## Step 4: Initialize Portfolio

### 4.1 Insert Initial Capital Record

1. Go to **Data** → **portfolio_summary** table
2. Click **+ Add Row**
3. Insert:
   ```json
   {
     "total_portfolio_value": 100000,
     "total_unrealized_pnl": 0,
     "realized_pnl": 0,
     "sharpe_ratio": 0,
     "max_drawdown": 0,
     "win_rate": 0,
     "cagr": 0,
     "num_positions": 0,
     "num_trades": 0,
     "timestamp": "2024-01-01T00:00:00Z"
   }
   ```

---

## Step 5: Deploy Dashboard

### 5.1 Host Dashboard Frontend

**Option A: n8n Hosting**
1. Create new workflow → **Webhook trigger** (GET)
2. Add **Script node** → return HTML file
3. Set **Response mode** to "responseNode"
4. Add **Respond to Webhook** node with HTML content

**Option B: External Hosting (Recommended)**
1. Deploy `dashboard.html` to:
   - GitHub Pages
   - Netlify (free)
   - Vercel
   - Your own server

2. **Update Dashboard Config:**
   - Open `dashboard.html`
   - Line ~120: Update `API_URL`
   ```javascript
   const API_URL = 'YOUR_N8N_WEBHOOK_URL_HERE';
   ```
   - Replace with webhook URL from Workflow 5

3. **Test:**
   ```bash
   # Open in browser
   open dashboard.html
   
   # Should show: "Loading dashboard..." → then live data
   ```

### 5.2 Enable CORS (if needed)

If running dashboard on different domain:

1. Go to your n8n instance settings
2. Enable CORS headers
3. Add dashboard domain to whitelist

---

## Step 6: Verify & Test

### 6.1 Test Data Ingestion

1. Open **Workflow 1** (Market Data Ingestion)
2. Click **Test Workflow**
3. Check **market_prices** table
4. Should have 15 rows (one per symbol)

### 6.2 Test Signal Generation

1. Wait 5 minutes (or manually run Workflow 1 again)
2. Open **Workflow 2** (Signal Generator)
3. Click **Test Workflow**
4. Check **signals** table
5. Should have multiple rows with strategy_type values

### 6.3 Test Execution

1. Open **Workflow 3** (Execution Engine)
2. Click **Test Workflow**
3. Check **paper_positions** table
4. Should show open positions (or be empty if no strong signals)

### 6.4 Test Portfolio Metrics

1. Open **Workflow 4** (Portfolio Aggregator)
2. Click **Test Workflow**
3. Check **portfolio_summary** table
4. Should show latest metrics

### 6.5 Test Dashboard API

1. Open **Workflow 5** webhook URL directly in browser
2. Should return JSON (see `EXAMPLE_API_RESPONSE.json`)
3. Open `dashboard.html`
4. Should display live data

---

## Step 7: Schedule Workflows

All workflows should auto-run on their cron schedule. To verify:

1. Each workflow shows **Active** ✅
2. Check **Execution History** for completed runs
3. Each workflow runs at designed interval:
   - Ingestion: Every 5 minutes
   - Signals: Every 15 minutes
   - Execution: Every 30 minutes
   - Portfolio: Every hour

---

## Step 8: Monitor & Maintain

### 8.1 Daily Checks

- ✅ Dashboard loads without errors
- ✅ Signals are generating (not stuck)
- ✅ Trades are executing (check trade_log)
- ✅ Portfolio value is updating

### 8.2 Weekly Checks

- ✅ Sharpe ratio / Max drawdown are reasonable
- ✅ Win rate trending upward
- ✅ No stuck positions

### 8.3 Alert Setup (Optional)

Create a 6th workflow to monitor failures:

```
Trigger: Daily at 9:00 AM
→ Query all workflows for errors
→ If any failed: Send email alert
→ Log to portfolio_summary
```

---

## Troubleshooting

### Issue: Data Tables show no data

**Solution:**
1. Check if workflows are running
2. Verify API credentials in HTTP nodes
3. Check n8n execution logs for errors
4. Manually run Workflow 1

### Issue: Dashboard shows "Error: HTTP 404"

**Solution:**
1. Verify webhook URL in `dashboard.html`
2. Ensure Workflow 5 is active
3. Test webhook directly: `curl YOUR_WEBHOOK_URL`
4. Check n8n CORS settings

### Issue: Trades not executing

**Solution:**
1. Check **signals** table has data
2. Verify **market_prices** is updating
3. Run Workflow 3 manually → check logs
4. Confirm position sizing logic isn't filtering all signals

### Issue: Sharpe ratio is NaN

**Solution:**
1. Need at least 30 days of portfolio history
2. Check portfolio_summary has multiple rows
3. Verify returns calculation in Workflow 4

---

## Performance Tuning

### Optimize for Cost

1. **Increase cron intervals:**
   - Change Ingestion to every 15 min (not during market hours)
   - Change Signals to every 30 min
   - Change Execution to every 60 min

2. **Reduce number of symbols:**
   - Edit Workflow 1, Code node "Fetch Polygon API"
   - Keep only top 5-10 symbols

3. **Archive old data:**
   - Weekly: Delete records >90 days from market_prices
   - Monthly: Archive closed positions from paper_positions

### Optimize for Speed

1. **Parallelize workflows:**
   - Run multiple strategy branches in parallel (already done in Workflow 2)

2. **Cache price data:**
   - Store in Redis (Polygon API caching)

3. **Reduce code complexity:**
   - Remove unnecessary calculations in Signal Engine

---

## Customization

### Add New Trading Pair (Stat Arb)

Edit Workflow 2, Code node "Statistical Arbitrage Signals":

```javascript
const pairs = [
  { long: 'AAPL', short: 'MSFT' },  // Add here
  // ... existing pairs
];
```

### Change Position Sizing

Edit Workflow 3, Code node "Match Signals...":

```javascript
const capital = portfolio.total_portfolio_value * 0.02;  // Change 0.01 to 0.02
```

### Add New Metric

Edit Workflow 4, Code node "Calculate Portfolio Metrics":

```javascript
const sortino_ratio = ...;  // Add calculation
return { ..., sortino_ratio };
```

---

## Production Checklist

- [ ] All 5 workflows are active
- [ ] Data Tables initialized
- [ ] API credentials set
- [ ] Dashboard deployed & accessible
- [ ] Initial portfolio value set ($100k)
- [ ] Workflows running on schedule
- [ ] Dashboard shows live data
- [ ] Error monitoring set up
- [ ] Backup strategy documented

---

## Support & Debugging

**n8n Community:** https://community.n8n.io
**n8n Docs:** https://docs.n8n.io
**Polygon.io Docs:** https://polygon.io/docs

**Common API Issues:**
- 401 Unauthorized → Check API key
- 403 Forbidden → Check API plan limits
- 404 Not Found → Check symbol validity
- 429 Too Many Requests → Reduce frequency

---

## Cost Estimate (n8n Cloud Pro)

| Item | Cost/Month |
|------|-----------|
| Workflows (5 × $5) | $25 |
| Data Table Storage (100MB) | $10 |
| Executions (50k @ $0.001) | $50 |
| **Total** | **~$85** |

---

## Next Steps

After deployment, consider:

1. **Add risk management:**
   - Stop-loss orders
   - Maximum position limits
   - Portfolio-level risk controls

2. **Expand strategies:**
   - Mean Reversion with Kalman filter
   - Momentum with regime detection
   - Machine learning signal prediction

3. **Integrate broker:**
   - Real trading (paper → live)
   - Interactive Brokers API
   - Alpaca API

4. **Advanced analytics:**
   - Factor analysis (Fama-French)
   - Attribution analysis
   - Stress testing

---

**Deployment complete!** 🎉

Your quantitative trading engine is now live. Monitor the dashboard for the first few hours to ensure everything is running smoothly. Happy trading!
