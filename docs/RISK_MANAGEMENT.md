# Risk Management Framework
## Autonomous Trading System - Phase 1

**Status:** Phase 1 - Complete  
**Last Updated:** 2024-03-24  
**Owner:** Risk Management Team

---

## Executive Summary

The Risk Management Framework provides comprehensive protection for the autonomous trading system through automated position sizing, stop-loss enforcement, risk metrics calculation, and circuit breaker controls.

**Key Principles:**
- ✅ Fixed fractional position sizing (2% risk per trade)
- ✅ Hard stop-losses at -2% per position
- ✅ Maximum portfolio drawdown monitoring (20% limit)
- ✅ Daily loss limits (5% max)
- ✅ Circuit breaker emergency stops
- ✅ Complete audit trail and risk reporting

---

## Portfolio Constraints (Phase 1)

| Constraint | Value | Rationale |
|-----------|-------|-----------|
| **Initial Capital** | $100,000 | Starting portfolio size |
| **Max Position Size** | 5% of portfolio | Max $5,000 per asset |
| **Max Portfolio Drawdown** | 20% | Circuit breaker threshold |
| **Max Daily Loss** | 5% | $5,000 per day |
| **Default Stop Loss** | -2% | Per-trade loss limit |
| **Max Total Exposure** | 100% | No leverage Phase 1 |
| **Default Take Profit** | +5% | Default profit target |
| **Max Positions** | 50 | Diversification limit |

---

## Architecture

### Module Overview

```
engine/risk/
├── __init__.py              # Package initialization
├── position_sizer.py        # Position sizing algorithms
├── stop_loss.py             # Stop-loss & take-profit management
├── risk_metrics.py          # Risk calculation engine
└── risk_limits.py           # Risk enforcement & circuit breakers
```

### Integration Points

```
Main Trading Flow
    ↓
Signal Generator → Position Sizer → Stop Loss Manager → Executor
                       ↓               ↓
              Risk Limit Enforcer ← Circuit Breaker
                       ↓
              Risk Metrics Engine
                       ↓
              Dashboard & Alerts
```

---

## Position Sizing

### 1. Fixed Fractional Sizing (Primary)

**Algorithm:**
```
Risk Amount = Portfolio Value × Risk Per Trade (2%)
Dollar Risk Per Share = Entry Price - Stop Loss Price
Shares = Risk Amount / Dollar Risk Per Share
```

**Example:**
```
Portfolio: $100,000
Entry: $150.00
Stop Loss: $147.00 (-2%)

Risk Amount = $100,000 × 0.02 = $2,000
Dollar Risk = $150 - $147 = $3
Shares = $2,000 / $3 = 666 shares

Position Value = 666 × $150 = $99,900 (capped at 5% = $5,000)
Final Shares = $5,000 / $150 = 33 shares
```

**Implementation:**
```python
from engine.risk import PositionSizer

sizer = PositionSizer(
    portfolio_value=100000,
    risk_per_trade=0.02,        # 2%
    max_position_size=0.05,     # 5%
    max_total_exposure=1.0      # 100%
)

result = sizer.fixed_fractional(
    entry_price=150.0,
    stop_loss_price=147.0
)
# Returns: {shares: 33, position_value: $4950, risk_amount: $2000, ...}
```

### 2. Kelly Criterion (Advanced)

**Algorithm:**
```
Kelly Fraction (f*) = (b × p - q) / b
Where:
  b = win/loss ratio (avg win / avg loss)
  p = win probability
  q = loss probability (1-p)

Fractional Kelly = Kelly × 0.5 (conservative 50% Kelly)
```

**Example:**
```
Win Rate: 55% (p=0.55)
Win/Loss Ratio: 1.5x (average win is 1.5× average loss)
q = 1 - 0.55 = 0.45

Kelly = (1.5 × 0.55 - 0.45) / 1.5 = 0.283 (28.3%)
Fractional Kelly = 28.3% × 0.5 = 14.15% (capped at 5% max)
```

**Use Cases:**
- After sufficient trading history (100+ trades)
- When win rate and payoff ratio are reliable
- With strict position sizing caps

### 3. Dynamic Sizing

**Factors:**
- **Volatility Factor:** Lower vol = larger positions (vol target: 2%)
- **Win Rate Factor:** Higher win rate = larger positions
- **Position Factor:** More open positions = smaller new positions

**Example:**
```
Volatility: 2.5% (slightly elevated)
Win Rate: 58% (profitable)
Current Positions: 5

Results:
  Volatility Factor: 0.80 (slightly reduced)
  Win Rate Factor: 1.07 (slightly increased)
  Position Factor: 0.68 (5 of 50 positions)
  
  Recommended Risk: 2% × 0.80 × 1.07 × 0.68 = 1.16% (between min 1% and max 4%)
```

**Implementation:**
```python
result = sizer.dynamic_sizing(
    volatility=0.025,
    win_rate=0.58,
    current_positions=5
)
# Returns: {volatility_factor: 0.80, win_rate_factor: 1.07, ...}
```

---

## Stop-Loss & Take-Profit Management

### Stop-Loss Types

#### 1. Fixed Percentage Stop-Loss (Recommended Phase 1)

**Default:** -2% below entry price

```python
from engine.risk import StopLossManager

manager = StopLossManager(default_stop_loss_pct=0.02)

result = manager.calculate_fixed_stop_loss(
    entry_price=150.0,
    stop_loss_pct=0.02
)
# Returns: {stop_price: $147.00, stop_loss_type: 'fixed', ...}
```

#### 2. Trailing Stop Loss

Follows the highest price, maintaining a fixed distance below.

```python
result = manager.calculate_trailing_stop(
    entry_price=150.0,
    current_price=155.0,
    highest_price=157.5,
    trailing_stop_pct=0.03  # 3% trailing distance
)
# Stop = $157.5 × (1 - 0.03) = $152.78
```

**Use Cases:**
- Protect profits when price moves favorably
- Automatically capture gains
- Reduce risk as trade becomes profitable

#### 3. ATR-Based Stop Loss

Adjusts stop loss to volatility using Average True Range.

```python
result = manager.calculate_atr_based_stop(
    entry_price=150.0,
    atr=2.5,
    atr_multiplier=2.0  # 2x ATR below entry
)
# Stop = $150 - (2.5 × 2) = $145
```

**Benefits:**
- Adapts to market conditions
- Tighter stops in low vol, wider stops in high vol
- Reduces false stops in volatile markets

### Take-Profit Targeting

**Default Ratio:** Risk:Reward = 1:2.5

```python
result = manager.calculate_take_profit(
    entry_price=100.0,
    take_profit_pct=0.05  # 5% profit target
)
# Target = $105.00
# Reward/Risk = 5% / 2% = 2.5:1
```

**Position Management:**
```python
# Example: Partial profit taking at different levels
Entry: $100
Target 1: $102 (2% profit) - Sell 33% position
Target 2: $105 (5% profit) - Sell 33% position
Target 3: $110 (10% profit) - Sell remaining with trailing stop
```

---

## Risk Metrics

### 1. Maximum Drawdown

**Definition:** Largest peak-to-trough decline in portfolio value

**Phase 1 Limit:** 20% max

```python
from engine.risk import RiskMetricsEngine

engine = RiskMetricsEngine()

result = engine.calculate_max_drawdown([
    100000, 101000, 99500, 102000, 98000, 101500
])
# Example: 13.6% drawdown (102000 → 88000)
```

**Monitoring:**
- Check daily during market hours
- Alert at 15% (warning)
- Circuit breaker trigger at 20% (stop trading)

### 2. Value at Risk (VaR)

**Definition:** Maximum loss expected with X% confidence

**Phase 1:** 95% confidence level (daily)

```python
result = engine.calculate_var(
    returns=[0.01, -0.02, 0.015, -0.01, ...],
    confidence_level=0.95
)
# Example: 2.3% daily VaR
# Interpretation: 95% of days, max loss ≤ 2.3%
```

**Per $100K Portfolio:**
- 1% VaR = max $1,000 daily loss (95% confidence)
- 2% VaR = max $2,000 daily loss (95% confidence)
- 5% VaR = max $5,000 daily loss (95% confidence)

### 3. Sharpe Ratio

**Definition:** Return per unit of risk

**Formula:** (Annual Return - Risk-Free Rate) / Volatility

**Interpretation:**
- 0.5: Poor
- 1.0: Acceptable
- 2.0: Very good
- 3.0+: Excellent

### 4. Sortino Ratio

**Definition:** Return per unit of *downside* risk (ignores upside volatility)

**Better than Sharpe for:** Trading systems that have frequent small gains with rare large losses

### 5. Concentration Risk (Herfindahl Index)

**Formula:** HHI = Σ(position_pct)²

**Levels:**
- < 0.25: Well diversified
- 0.25-0.5: Moderate concentration
- > 0.5: High concentration

**Example:**
```python
positions = {
    'AAPL': 40000,
    'MSFT': 30000,
    'GOOGL': 20000,
    'AMZN': 10000
}

result = engine.calculate_concentration_risk(positions)
# HHI = 0.30 (moderate concentration)
# Top 3 holdings = 90%
```

---

## Risk Limits & Circuit Breakers

### Limit Hierarchy

**Level 1 - Position Level:**
- Max position size: 5% of portfolio
- Max position loss: -2% (hard stop-loss)

**Level 2 - Portfolio Level:**
- Max daily loss: -5% ($5,000 on $100K)
- Max total exposure: 100% (no leverage)
- Max sector exposure: 25% per sector

**Level 3 - Circuit Breaker:**
- Warning: 1 limit breach → pause new trades
- Open: 2+ limit breaches → emergency stop

### Circuit Breaker Logic

```
CLOSED (Normal) → 0 breaches
    ↓ (on breach)
WARNING → 1 breach active (no new trades)
    ↓ (on 2nd breach)
OPEN → 2+ breaches (complete stop)
    ↓ (manual reset required)
CLOSED (after incident review)
```

**Implementation:**
```python
from engine.risk import RiskLimitEnforcer

enforcer = RiskLimitEnforcer(
    initial_capital=100000,
    max_portfolio_drawdown_pct=20.0,
    max_daily_loss_pct=5.0,
    max_position_size_pct=5.0
)

# Check a breach
is_ok, reason, dd = enforcer.check_max_drawdown(
    current_portfolio_value=82000,
    peak_portfolio_value=100000
)
# 18% drawdown is OK

# Check circuit breaker
status = enforcer.check_circuit_breaker(breach_count=2)
can_trade, msg = enforcer.can_trade()
# Circuit OPEN, cannot trade
```

---

## Risk Audit & Reporting

### Daily Risk Report

**Contents:**
1. Portfolio Metrics
   - Total value, cash, positions
   - Unrealized/realized P&L

2. Risk Metrics
   - Current drawdown vs 20% limit
   - Daily loss vs 5% limit
   - VaR at 95% confidence
   - Sharpe ratio, win rate

3. Exposure Analysis
   - Total exposure vs 100% limit
   - Top 10 holdings
   - Sector breakdown
   - Concentration risk (HHI)

4. Position Analysis
   - Open positions vs limits
   - Distance to stop losses
   - Active trades nearing profit targets

5. Circuit Breaker Status
   - Current status (CLOSED/WARNING/OPEN)
   - Active limit breaches
   - Recent risk events

6. Recommendations
   - Positions to reduce if concentration high
   - Sectors approaching limits
   - Risk events requiring action

### Risk Audit Trail

**Logged Events:**
- Position size breaches
- Daily loss breaches
- Drawdown breaches
- Sector exposure breaches
- Circuit breaker state changes
- Manual overrides (if enabled)

**Access:**
```python
audit_log = enforcer.get_audit_log()
summary = enforcer.get_audit_log_summary()

for event in audit_log:
    print(event)
    # {
    #   'timestamp': '2024-03-24T15:30:00.000Z',
    #   'event_type': 'max_drawdown_breach',
    #   'details': {...},
    #   'circuit_breaker_status': 'closed'
    # }
```

---

## Testing & Validation

### Test Coverage

**Position Sizing (test_position_sizer.py)**
- Fixed fractional with various stop losses
- Kelly criterion with different win rates
- Dynamic sizing with volatility changes
- Position validation against limits

**Stop-Loss Management (test_stop_loss.py)**
- Fixed, trailing, and ATR-based stops
- Stop trigger detection
- Profit target detection
- Position exit metrics

**Risk Metrics (test_risk_metrics.py)**
- Drawdown calculation
- VaR at multiple confidence levels
- Sharpe/Sortino ratio calculation
- Concentration risk (HHI)
- Exposure limit checking

**Risk Limits (test_risk_limits.py)**
- Individual limit checking
- Circuit breaker state transitions
- Audit log generation
- Multi-limit evaluation

### Running Tests

```bash
# Install pytest
pip install pytest

# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_position_sizer.py -v

# Run with coverage
pytest tests/ --cov=engine/risk --cov-report=html
```

---

## Integration Guide

### Adding to Trading Signal

```python
from engine.risk import PositionSizer, StopLossManager, RiskLimitEnforcer

class TradingEngine:
    def __init__(self):
        self.sizer = PositionSizer(portfolio_value=100000)
        self.stop_loss_mgr = StopLossManager()
        self.risk_enforcer = RiskLimitEnforcer()
    
    def generate_trade(self, symbol, signal, entry_price, current_portfolio):
        # 1. Calculate position size
        position = self.sizer.fixed_fractional(
            entry_price=entry_price,
            stop_loss_price=entry_price * 0.98  # 2% stop
        )
        
        # 2. Calculate stop loss
        stop = self.stop_loss_mgr.calculate_fixed_stop_loss(entry_price)
        
        # 3. Calculate take profit
        target = self.stop_loss_mgr.calculate_take_profit(entry_price)
        
        # 4. Validate against limits
        is_valid, reason = self.sizer.validate_position(
            shares=position['shares'],
            entry_price=entry_price,
            current_exposure=current_portfolio['exposure']
        )
        
        if not is_valid:
            logger.warning(f"Position rejected: {reason}")
            return None
        
        # 5. Check circuit breaker
        can_trade, msg = self.risk_enforcer.can_trade()
        if not can_trade:
            logger.error(f"Trading blocked: {msg}")
            return None
        
        return {
            'symbol': symbol,
            'shares': position['shares'],
            'entry_price': entry_price,
            'stop_loss': stop['stop_price'],
            'take_profit': target['target_price'],
            'risk_amount': position['risk_amount'],
        }
```

### Real-Time Risk Monitoring

```python
def monitor_portfolio(self, portfolio_data):
    """Called every minute during trading hours"""
    
    metrics = {
        'current_portfolio_value': portfolio_data['total_value'],
        'peak_portfolio_value': portfolio_data['peak_value'],
        'daily_pnl': portfolio_data['daily_pnl'],
        'portfolio_value': portfolio_data['total_value'],
        'total_position_value': portfolio_data['position_value'],
    }
    
    # Evaluate all limits
    limit_results = self.risk_enforcer.evaluate_all_limits(metrics)
    
    breach_count = sum(1 for ok, _, _ in limit_results.values() if not ok)
    
    # Update circuit breaker
    status = self.risk_enforcer.check_circuit_breaker(breach_count)
    
    if status != CircuitBreakerStatus.CLOSED:
        logger.warning(f"Circuit breaker: {status.value}")
        # Send alerts, stop new trades, etc.
```

---

## Future Enhancements (Phase 2+)

### Phase 2: Advanced Features
- [ ] Leverage support (margin up to 2:1)
- [ ] Sector/industry rotation constraints
- [ ] Correlation-based position sizing
- [ ] Volatility regimes (low/normal/high vol strategies)
- [ ] Heat maps for exposure visualization

### Phase 3: ML Integration
- [ ] Dynamic stop loss using ML predictions
- [ ] Optimal position sizing based on regime detection
- [ ] Anomaly detection in drawdown patterns
- [ ] Adaptive risk limits based on market conditions

### Phase 4: Advanced Risk
- [ ] Expected Shortfall (CVaR) instead of VaR
- [ ] Stress testing scenarios
- [ ] Scenario analysis for systemic shocks
- [ ] Real-time factor exposure tracking

---

## Configuration

### Environment Variables

```bash
# Risk configuration
RISK_PER_TRADE=0.02              # 2% risk per trade
MAX_POSITION_SIZE=0.05           # 5% max position
MAX_PORTFOLIO_DRAWDOWN=20.0      # 20% max drawdown
MAX_DAILY_LOSS=5.0               # 5% max daily loss
MAX_SECTOR_EXPOSURE=25.0         # 25% per sector
DEFAULT_STOP_LOSS_PCT=0.02       # 2% stop loss
DEFAULT_TAKE_PROFIT_PCT=0.05     # 5% take profit
```

### Configuration File (risk_config.py)

```python
# Can be added to engine/config.py
RISK_CONFIG = {
    'position_sizing': {
        'method': 'fixed_fractional',  # or 'kelly', 'dynamic'
        'risk_per_trade': 0.02,
        'max_position_size_pct': 0.05,
    },
    'stop_loss': {
        'method': 'fixed',  # or 'trailing', 'atr'
        'fixed_pct': 0.02,
        'trailing_pct': 0.03,
        'atr_multiplier': 2.0,
    },
    'limits': {
        'max_drawdown_pct': 20.0,
        'max_daily_loss_pct': 5.0,
        'max_sector_exposure_pct': 25.0,
        'max_total_exposure_pct': 100.0,
    },
    'circuit_breaker': {
        'warning_threshold': 1,
        'open_threshold': 2,
    }
}
```

---

## Troubleshooting

### Common Issues

**Q: Positions are too small**
- A: Check portfolio_value in PositionSizer initialization
- A: Verify risk_per_trade is appropriate (2% typical)
- A: Check stop_loss_price is not too close to entry

**Q: Circuit breaker keeps opening**
- A: Review limit settings; may be too conservative
- A: Increase max drawdown limit if 20% is unrealistic
- A: Check for correlated losses triggering multiple breaches

**Q: Risk metrics are erratic**
- A: Need minimum 10 observations for VaR
- A: Need minimum 2 observations for Sharpe ratio
- A: Check portfolio_values list is in chronological order

**Q: Position size exceeds max**
- A: Wide stop losses get capped at max_position_size
- A: Consider tighter stop losses
- A: Check max_position_size constraint

---

## References

- **Kelly Criterion:** https://en.wikipedia.org/wiki/Kelly_criterion
- **Value at Risk:** https://en.wikipedia.org/wiki/Value_at_risk
- **Sharpe Ratio:** https://en.wikipedia.org/wiki/Sharpe_ratio
- **Sortino Ratio:** https://en.wikipedia.org/wiki/Sortino_ratio
- **Position Sizing:** "Trade Your Way to Financial Freedom" - Van Tharp

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2024-03-24 | Risk Manager | Initial Phase 1 documentation |

---

**Last Updated:** 2024-03-24  
**Status:** ✅ Phase 1 Complete  
**Approved:** Risk Management Team
