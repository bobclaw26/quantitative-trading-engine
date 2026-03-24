"""
Tests for RiskLimitEnforcer
===========================

Unit tests for risk limit enforcement and circuit breaker logic.
"""

import pytest
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "engine"))

from risk.risk_limits import RiskLimitEnforcer, CircuitBreakerStatus


class TestRiskLimitEnforcer:
    """Test suite for RiskLimitEnforcer class."""

    def setup_method(self):
        """Initialize test fixtures."""
        self.enforcer = RiskLimitEnforcer(
            initial_capital=100000,
            max_portfolio_drawdown_pct=20.0,
            max_daily_loss_pct=5.0,
            max_position_size_pct=5.0,
            max_sector_exposure_pct=25.0,
            max_total_exposure_pct=100.0,
        )

    def test_initialization(self):
        """Test enforcer initialization."""
        assert self.enforcer.initial_capital == 100000
        assert self.enforcer.max_portfolio_drawdown_pct == 20.0
        assert self.enforcer.circuit_breaker_status == CircuitBreakerStatus.CLOSED

    def test_check_max_drawdown_within_limits(self):
        """Test max drawdown check when within limits."""
        is_ok, reason, dd = self.enforcer.check_max_drawdown(
            current_portfolio_value=82000, peak_portfolio_value=100000
        )

        # 18% drawdown < 20% limit
        assert is_ok is True
        assert dd == pytest.approx(18.0, abs=0.1)

    def test_check_max_drawdown_breach(self):
        """Test max drawdown breach detection."""
        is_ok, reason, dd = self.enforcer.check_max_drawdown(
            current_portfolio_value=78000, peak_portfolio_value=100000
        )

        # 22% drawdown > 20% limit
        assert is_ok is False
        assert dd == pytest.approx(22.0, abs=0.1)

    def test_check_daily_loss_within_limits(self):
        """Test daily loss check when within limits."""
        is_ok, reason, loss = self.enforcer.check_daily_loss(
            daily_pnl=-2000, portfolio_value=100000
        )

        # 2% loss < 5% limit
        assert is_ok is True
        assert loss == pytest.approx(2.0, abs=0.1)

    def test_check_daily_loss_breach(self):
        """Test daily loss breach detection."""
        is_ok, reason, loss = self.enforcer.check_daily_loss(
            daily_pnl=-6000, portfolio_value=100000
        )

        # 6% loss > 5% limit
        assert is_ok is False
        assert loss == pytest.approx(6.0, abs=0.1)

    def test_check_position_size_within_limits(self):
        """Test position size check when within limits."""
        is_ok, reason, pct = self.enforcer.check_position_size(
            position_value=4000, portfolio_value=100000, symbol="AAPL"
        )

        # 4% < 5% limit
        assert is_ok is True
        assert pct == 4.0

    def test_check_position_size_breach(self):
        """Test position size breach detection."""
        is_ok, reason, pct = self.enforcer.check_position_size(
            position_value=6000, portfolio_value=100000, symbol="AAPL"
        )

        # 6% > 5% limit
        assert is_ok is False
        assert pct == 6.0

    def test_check_sector_exposure_within_limits(self):
        """Test sector exposure check when within limits."""
        is_ok, reason, exp = self.enforcer.check_sector_exposure(
            sector_exposure_value=20000, portfolio_value=100000, sector="Tech"
        )

        # 20% < 25% limit
        assert is_ok is True
        assert exp == 20.0

    def test_check_sector_exposure_breach(self):
        """Test sector exposure breach detection."""
        is_ok, reason, exp = self.enforcer.check_sector_exposure(
            sector_exposure_value=30000, portfolio_value=100000, sector="Tech"
        )

        # 30% > 25% limit
        assert is_ok is False
        assert exp == 30.0

    def test_check_total_exposure_within_limits(self):
        """Test total exposure check when within limits."""
        is_ok, reason, exp = self.enforcer.check_total_exposure(
            total_position_value=80000, portfolio_value=100000
        )

        # 80% < 100% limit
        assert is_ok is True
        assert exp == 80.0

    def test_check_total_exposure_breach(self):
        """Test total exposure breach detection."""
        is_ok, reason, exp = self.enforcer.check_total_exposure(
            total_position_value=110000, portfolio_value=100000
        )

        # 110% > 100% limit (with leverage, which is not allowed in Phase 1)
        assert is_ok is False

    def test_evaluate_all_limits(self):
        """Test evaluating all limits at once."""
        metrics = {
            "current_portfolio_value": 90000,
            "peak_portfolio_value": 100000,
            "daily_pnl": -3000,
            "portfolio_value": 100000,
            "position_value": 4500,
            "symbol": "AAPL",
            "total_position_value": 70000,
        }

        results = self.enforcer.evaluate_all_limits(metrics)

        assert "max_drawdown" in results
        assert "daily_loss" in results
        assert "position_size" in results
        assert "total_exposure" in results

    def test_circuit_breaker_closed(self):
        """Test circuit breaker stays closed with no breaches."""
        status = self.enforcer.check_circuit_breaker(breach_count=0)

        assert status == CircuitBreakerStatus.CLOSED

    def test_circuit_breaker_warning(self):
        """Test circuit breaker warning with one breach."""
        status = self.enforcer.check_circuit_breaker(breach_count=1)

        assert status == CircuitBreakerStatus.WARNING

    def test_circuit_breaker_open(self):
        """Test circuit breaker opens with two breaches."""
        status = self.enforcer.check_circuit_breaker(breach_count=2)

        assert status == CircuitBreakerStatus.OPEN

    def test_can_trade_when_closed(self):
        """Test that trading is allowed when circuit breaker is closed."""
        self.enforcer.circuit_breaker_status = CircuitBreakerStatus.CLOSED

        can_trade, reason = self.enforcer.can_trade()

        assert can_trade is True

    def test_cannot_trade_when_warning(self):
        """Test that trading is not allowed in warning state."""
        self.enforcer.circuit_breaker_status = CircuitBreakerStatus.WARNING

        can_trade, reason = self.enforcer.can_trade()

        assert can_trade is False

    def test_cannot_trade_when_open(self):
        """Test that trading is not allowed when circuit breaker is open."""
        self.enforcer.circuit_breaker_status = CircuitBreakerStatus.OPEN

        can_trade, reason = self.enforcer.can_trade()

        assert can_trade is False
        assert "OPEN" in reason

    def test_risk_audit_log(self):
        """Test that risk events are logged."""
        # Trigger a breach
        self.enforcer.check_max_drawdown(
            current_portfolio_value=70000, peak_portfolio_value=100000
        )

        audit_log = self.enforcer.get_audit_log()

        assert len(audit_log) > 0
        assert audit_log[0]["event_type"] == "max_drawdown_breach"

    def test_audit_log_summary(self):
        """Test audit log summary generation."""
        # Trigger multiple breaches
        self.enforcer.check_max_drawdown(78000, 100000)
        self.enforcer.check_daily_loss(-6000, 100000)
        self.enforcer.check_position_size(6000, 100000)

        summary = self.enforcer.get_audit_log_summary()

        assert "max_drawdown_breach" in summary
        assert "daily_loss_breach" in summary
        assert "position_size_breach" in summary


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
