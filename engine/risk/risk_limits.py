"""
Risk Limits & Enforcement
==========================

Enforces risk constraints and circuit breakers to prevent catastrophic losses.

Features:
- Maximum drawdown limits
- Position sizing limits
- Daily loss limits
- Exposure limits per asset/sector
- Circuit breaker triggering
- Risk audit logging
"""

import logging
from typing import Dict, List, Tuple, Optional
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)


class RiskLimit(Enum):
    """Risk limit types."""
    MAX_DRAWDOWN = "max_drawdown"
    DAILY_LOSS = "daily_loss"
    MAX_POSITION_SIZE = "max_position_size"
    MAX_SECTOR_EXPOSURE = "max_sector_exposure"
    TOTAL_EXPOSURE = "total_exposure"


class CircuitBreakerStatus(Enum):
    """Circuit breaker status."""
    CLOSED = "closed"  # Normal operation
    WARNING = "warning"  # Alert but still trading
    OPEN = "open"  # No new trades allowed


class RiskLimitEnforcer:
    """Enforces risk constraints and manages circuit breakers."""

    def __init__(
        self,
        initial_capital: float = 100000,
        max_portfolio_drawdown_pct: float = 20.0,
        max_daily_loss_pct: float = 5.0,
        max_position_size_pct: float = 5.0,
        max_sector_exposure_pct: float = 25.0,
        max_total_exposure_pct: float = 100.0,
    ):
        """
        Initialize RiskLimitEnforcer.

        Args:
            initial_capital: Starting portfolio value
            max_portfolio_drawdown_pct: Maximum portfolio drawdown allowed (%)
            max_daily_loss_pct: Maximum daily loss allowed (%)
            max_position_size_pct: Maximum position size as % of portfolio
            max_sector_exposure_pct: Maximum sector exposure as % of portfolio
            max_total_exposure_pct: Maximum total exposure as % of portfolio
        """
        self.initial_capital = initial_capital
        self.max_portfolio_drawdown_pct = max_portfolio_drawdown_pct
        self.max_daily_loss_pct = max_daily_loss_pct
        self.max_position_size_pct = max_position_size_pct
        self.max_sector_exposure_pct = max_sector_exposure_pct
        self.max_total_exposure_pct = max_total_exposure_pct

        self.circuit_breaker_status = CircuitBreakerStatus.CLOSED
        self.risk_audit_log = []

    def check_max_drawdown(
        self, current_portfolio_value: float, peak_portfolio_value: Optional[float] = None
    ) -> Tuple[bool, str, float]:
        """
        Check if maximum drawdown limit has been breached.

        Args:
            current_portfolio_value: Current portfolio value
            peak_portfolio_value: Highest portfolio value (default: initial_capital)

        Returns:
            Tuple of (is_within_limits, reason, current_drawdown_pct)
        """
        peak = peak_portfolio_value or self.initial_capital

        if current_portfolio_value > peak:
            peak = current_portfolio_value

        drawdown_pct = ((peak - current_portfolio_value) / peak) * 100

        is_within_limits = drawdown_pct <= self.max_portfolio_drawdown_pct

        reason = f"Drawdown: {drawdown_pct:.2f}% {'OK' if is_within_limits else 'BREACH'}"

        if not is_within_limits:
            logger.warning(f"MAX DRAWDOWN BREACHED: {reason}")
            self._log_risk_event(
                "max_drawdown_breach",
                {"current_drawdown": drawdown_pct, "max_allowed": self.max_portfolio_drawdown_pct},
            )

        return is_within_limits, reason, drawdown_pct

    def check_daily_loss(
        self, daily_pnl: float, portfolio_value: float
    ) -> Tuple[bool, str, float]:
        """
        Check if daily loss limit has been breached.

        Args:
            daily_pnl: Daily profit/loss in dollars (negative = loss)
            portfolio_value: Current portfolio value

        Returns:
            Tuple of (is_within_limits, reason, daily_loss_pct)
        """
        daily_loss_pct = abs(daily_pnl) / portfolio_value * 100

        is_within_limits = daily_loss_pct <= self.max_daily_loss_pct

        reason = f"Daily Loss: {daily_loss_pct:.2f}% {'OK' if is_within_limits else 'BREACH'}"

        if not is_within_limits:
            logger.warning(f"DAILY LOSS LIMIT BREACHED: {reason}")
            self._log_risk_event(
                "daily_loss_breach",
                {"daily_loss": daily_loss_pct, "max_allowed": self.max_daily_loss_pct},
            )

        return is_within_limits, reason, daily_loss_pct

    def check_position_size(
        self, position_value: float, portfolio_value: float, symbol: str = ""
    ) -> Tuple[bool, str, float]:
        """
        Check if position size is within limits.

        Args:
            position_value: Position value in dollars
            portfolio_value: Current portfolio value
            symbol: Stock symbol (optional, for logging)

        Returns:
            Tuple of (is_within_limits, reason, position_size_pct)
        """
        position_size_pct = (position_value / portfolio_value) * 100

        is_within_limits = position_size_pct <= self.max_position_size_pct

        reason = f"{symbol or 'Position'}: {position_size_pct:.2f}% {'OK' if is_within_limits else 'BREACH'}"

        if not is_within_limits:
            logger.warning(f"POSITION SIZE LIMIT BREACHED: {reason}")
            self._log_risk_event(
                "position_size_breach",
                {
                    "symbol": symbol,
                    "position_size": position_size_pct,
                    "max_allowed": self.max_position_size_pct,
                },
            )

        return is_within_limits, reason, position_size_pct

    def check_sector_exposure(
        self, sector_exposure_value: float, portfolio_value: float, sector: str = ""
    ) -> Tuple[bool, str, float]:
        """
        Check if sector exposure is within limits.

        Args:
            sector_exposure_value: Total sector exposure in dollars
            portfolio_value: Current portfolio value
            sector: Sector name (optional, for logging)

        Returns:
            Tuple of (is_within_limits, reason, sector_exposure_pct)
        """
        sector_exposure_pct = (sector_exposure_value / portfolio_value) * 100

        is_within_limits = sector_exposure_pct <= self.max_sector_exposure_pct

        reason = f"{sector or 'Sector'}: {sector_exposure_pct:.2f}% {'OK' if is_within_limits else 'BREACH'}"

        if not is_within_limits:
            logger.warning(f"SECTOR EXPOSURE LIMIT BREACHED: {reason}")
            self._log_risk_event(
                "sector_exposure_breach",
                {
                    "sector": sector,
                    "exposure": sector_exposure_pct,
                    "max_allowed": self.max_sector_exposure_pct,
                },
            )

        return is_within_limits, reason, sector_exposure_pct

    def check_total_exposure(
        self, total_position_value: float, portfolio_value: float
    ) -> Tuple[bool, str, float]:
        """
        Check if total portfolio exposure is within limits.

        Args:
            total_position_value: Total value of all positions in dollars
            portfolio_value: Current portfolio value

        Returns:
            Tuple of (is_within_limits, reason, total_exposure_pct)
        """
        total_exposure_pct = (total_position_value / portfolio_value) * 100

        is_within_limits = total_exposure_pct <= self.max_total_exposure_pct

        reason = f"Total Exposure: {total_exposure_pct:.2f}% {'OK' if is_within_limits else 'BREACH'}"

        if not is_within_limits:
            logger.warning(f"TOTAL EXPOSURE LIMIT BREACHED: {reason}")
            self._log_risk_event(
                "total_exposure_breach",
                {
                    "exposure": total_exposure_pct,
                    "max_allowed": self.max_total_exposure_pct,
                },
            )

        return is_within_limits, reason, total_exposure_pct

    def evaluate_all_limits(
        self, portfolio_metrics: Dict[str, float]
    ) -> Dict[str, Tuple[bool, str, float]]:
        """
        Evaluate all risk limits at once.

        Args:
            portfolio_metrics: Dict with keys like 'portfolio_value', 'daily_pnl', etc.

        Returns:
            Dict of {limit_name: (is_within, reason, value)}
        """
        results = {}

        # Drawdown check
        if "current_portfolio_value" in portfolio_metrics:
            results["max_drawdown"] = self.check_max_drawdown(
                portfolio_metrics["current_portfolio_value"],
                portfolio_metrics.get("peak_portfolio_value"),
            )

        # Daily loss check
        if "daily_pnl" in portfolio_metrics and "portfolio_value" in portfolio_metrics:
            results["daily_loss"] = self.check_daily_loss(
                portfolio_metrics["daily_pnl"],
                portfolio_metrics["portfolio_value"],
            )

        # Position size check
        if all(k in portfolio_metrics for k in ["position_value", "portfolio_value"]):
            results["position_size"] = self.check_position_size(
                portfolio_metrics["position_value"],
                portfolio_metrics["portfolio_value"],
                portfolio_metrics.get("symbol", ""),
            )

        # Total exposure check
        if all(k in portfolio_metrics for k in ["total_position_value", "portfolio_value"]):
            results["total_exposure"] = self.check_total_exposure(
                portfolio_metrics["total_position_value"],
                portfolio_metrics["portfolio_value"],
            )

        return results

    def check_circuit_breaker(
        self, breach_count: int, warning_threshold: int = 1, breach_threshold: int = 2
    ) -> CircuitBreakerStatus:
        """
        Evaluate circuit breaker status based on breach count.

        Args:
            breach_count: Number of active limit breaches
            warning_threshold: Breach count to trigger WARNING
            breach_threshold: Breach count to trigger OPEN

        Returns:
            New circuit breaker status
        """
        if breach_count >= breach_threshold:
            self.circuit_breaker_status = CircuitBreakerStatus.OPEN
            logger.critical(f"CIRCUIT BREAKER OPEN: {breach_count} limit breaches detected")
        elif breach_count >= warning_threshold:
            self.circuit_breaker_status = CircuitBreakerStatus.WARNING
            logger.warning(f"CIRCUIT BREAKER WARNING: {breach_count} limit breaches")
        else:
            self.circuit_breaker_status = CircuitBreakerStatus.CLOSED
            logger.info("Circuit breaker status: CLOSED (normal operation)")

        return self.circuit_breaker_status

    def can_trade(self) -> Tuple[bool, str]:
        """
        Determine if new trades are allowed based on circuit breaker status.

        Returns:
            Tuple of (can_trade, reason)
        """
        if self.circuit_breaker_status == CircuitBreakerStatus.OPEN:
            return False, "Circuit breaker OPEN: Emergency stop active"
        elif self.circuit_breaker_status == CircuitBreakerStatus.WARNING:
            return False, "Circuit breaker WARNING: New trades paused"
        else:
            return True, "Circuit breaker CLOSED: Normal operation"

    def _log_risk_event(self, event_type: str, details: Dict) -> None:
        """
        Log a risk event for audit trail.

        Args:
            event_type: Type of risk event
            details: Event details dict
        """
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "details": details,
            "circuit_breaker_status": self.circuit_breaker_status.value,
        }
        self.risk_audit_log.append(event)
        logger.info(f"Risk event logged: {event_type} - {details}")

    def get_audit_log(self) -> List[Dict]:
        """Get complete risk audit log."""
        return self.risk_audit_log

    def get_audit_log_summary(self) -> Dict[str, int]:
        """Get summary of risk events."""
        summary = {}
        for event in self.risk_audit_log:
            event_type = event["event_type"]
            summary[event_type] = summary.get(event_type, 0) + 1
        return summary


if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)

    enforcer = RiskLimitEnforcer(
        initial_capital=100000,
        max_portfolio_drawdown_pct=20.0,
        max_daily_loss_pct=5.0,
        max_position_size_pct=5.0,
    )

    print("=" * 60)
    print("Risk Limit Enforcement Example")
    print("=" * 60)

    # Check drawdown
    is_ok, reason, dd = enforcer.check_max_drawdown(
        current_portfolio_value=82000, peak_portfolio_value=100000
    )
    print(f"Drawdown Check: {reason} - {is_ok}")
    print()

    # Check daily loss
    is_ok, reason, loss = enforcer.check_daily_loss(
        daily_pnl=-2000, portfolio_value=95000
    )
    print(f"Daily Loss Check: {reason} - {is_ok}")
    print()

    # Check position size
    is_ok, reason, pct = enforcer.check_position_size(
        position_value=6000, portfolio_value=100000, symbol="AAPL"
    )
    print(f"Position Size Check: {reason} - {is_ok}")
    print()

    # Circuit breaker
    print("=" * 60)
    print("Circuit Breaker Status")
    print("=" * 60)
    status = enforcer.check_circuit_breaker(breach_count=2)
    can_trade, reason = enforcer.can_trade()
    print(f"Status: {status.value}")
    print(f"Can Trade: {can_trade} - {reason}")
