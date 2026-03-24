"""
Risk Management Package
=======================

Comprehensive risk management and position sizing for autonomous trading.

Modules:
- position_sizer: Position sizing algorithms (fixed fractional, Kelly, dynamic)
- stop_loss: Stop-loss and take-profit management
- risk_metrics: Risk calculation engine (VaR, Sharpe, Sortino, drawdown, etc.)
- risk_limits: Risk limit enforcement and circuit breakers
"""

from .position_sizer import PositionSizer
from .stop_loss import StopLossManager, StopLossType
from .risk_metrics import RiskMetricsEngine
from .risk_limits import RiskLimitEnforcer, RiskLimit, CircuitBreakerStatus

__all__ = [
    "PositionSizer",
    "StopLossManager",
    "StopLossType",
    "RiskMetricsEngine",
    "RiskLimitEnforcer",
    "RiskLimit",
    "CircuitBreakerStatus",
]
