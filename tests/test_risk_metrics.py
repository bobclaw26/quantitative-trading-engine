"""
Tests for RiskMetricsEngine
===========================

Unit tests for risk metrics calculations.
"""

import pytest
import sys
import math
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "engine"))

from risk.risk_metrics import RiskMetricsEngine


class TestRiskMetricsEngine:
    """Test suite for RiskMetricsEngine class."""

    def setup_method(self):
        """Initialize test fixtures."""
        self.engine = RiskMetricsEngine(risk_free_rate=0.02)

    def test_calculate_max_drawdown_simple(self):
        """Test max drawdown calculation with simple sequence."""
        portfolio_values = [100, 110, 105, 95, 100, 102]

        result = self.engine.calculate_max_drawdown(portfolio_values)

        # Max drawdown: 110 -> 95 = 15 / 110 = 13.64%
        assert result["max_drawdown_pct"] == pytest.approx(13.64, abs=0.01)
        assert result["peak_value"] == 110
        assert result["trough_value"] == 95

    def test_max_drawdown_with_recovery(self):
        """Test max drawdown doesn't reset when recovering to new high."""
        portfolio_values = [100, 50, 75, 120, 60]

        result = self.engine.calculate_max_drawdown(portfolio_values)

        # Max drawdown: 120 -> 60 = 60 / 120 = 50%
        assert result["max_drawdown_pct"] == 50.0

    def test_calculate_var_basic(self):
        """Test VaR calculation."""
        returns = [-0.05, -0.03, -0.02, -0.01, 0, 0.01, 0.02, 0.03, 0.05, 0.08]

        result = self.engine.calculate_var(returns, confidence_level=0.95)

        assert "var_pct" in result
        assert "var_amount_per_100k" in result
        assert result["confidence_level"] == 0.95

    def test_var_with_high_confidence(self):
        """Test VaR with different confidence levels."""
        returns = [-0.05] * 5 + [0.05] * 95

        var_90 = self.engine.calculate_var(returns, confidence_level=0.90)
        var_95 = self.engine.calculate_var(returns, confidence_level=0.95)

        # Higher confidence = larger expected loss
        assert var_95["var_pct"] >= var_90["var_pct"]

    def test_calculate_sharpe_ratio(self):
        """Test Sharpe ratio calculation."""
        returns = [0.01, 0.02, 0.01, 0.00, -0.01, 0.02, 0.01]

        result = self.engine.calculate_sharpe_ratio(returns)

        assert "sharpe_ratio" in result
        assert "annualized_return" in result
        assert "annualized_volatility" in result

    def test_sharpe_ratio_zero_volatility(self):
        """Test Sharpe ratio with zero volatility."""
        returns = [0.01] * 5  # No variation

        result = self.engine.calculate_sharpe_ratio(returns)

        assert result["sharpe_ratio"] == 0.0
        assert "undefined" in result.get("note", "").lower()

    def test_calculate_sortino_ratio(self):
        """Test Sortino ratio calculation."""
        returns = [0.01, 0.02, 0.01, 0.00, -0.01, 0.02, 0.01]

        result = self.engine.calculate_sortino_ratio(returns)

        assert "sortino_ratio" in result
        assert "downside_deviation" in result

    def test_sortino_ratio_no_downside(self):
        """Test Sortino ratio when no downside returns."""
        returns = [0.01, 0.02, 0.03, 0.02, 0.01]

        result = self.engine.calculate_sortino_ratio(returns)

        # Should be infinite (no losses)
        assert result["sortino_ratio"] == float("inf")

    def test_calculate_concentration_risk(self):
        """Test concentration risk calculation."""
        positions = {
            "AAPL": 40000,
            "MSFT": 30000,
            "GOOGL": 20000,
            "AMZN": 10000,
        }

        result = self.engine.calculate_concentration_risk(positions)

        assert "hhi" in result
        assert "concentration_level" in result
        assert result["num_positions"] == 4

    def test_concentration_well_diversified(self):
        """Test concentration for well-diversified portfolio."""
        # 10 equal positions = 10% each
        positions = {f"S{i}": 10000 for i in range(10)}

        result = self.engine.calculate_concentration_risk(positions)

        # HHI = 10 * (0.1)^2 = 0.1
        assert result["hhi"] == pytest.approx(0.1, abs=0.01)
        assert "well diversified" in result["concentration_level"].lower()

    def test_concentration_highly_concentrated(self):
        """Test concentration for concentrated portfolio."""
        positions = {"AAPL": 90000, "MSFT": 10000}

        result = self.engine.calculate_concentration_risk(positions)

        # HHI = (0.9)^2 + (0.1)^2 = 0.82
        assert result["hhi"] == pytest.approx(0.82, abs=0.01)

    def test_calculate_exposure_limits(self):
        """Test exposure limit checking."""
        positions = {
            "AAPL": 6000,  # 6% - over 5% limit
            "MSFT": 4000,  # 4% - ok
        }

        result = self.engine.calculate_exposure_limits(
            positions, portfolio_value=100000, max_position_pct=0.05
        )

        assert result["total_exposure_pct"] == 10.0
        assert result["num_violations"] == 1
        assert any("AAPL" in v for v in result["violations"])

    def test_exposure_total_exceeds_limit(self):
        """Test total exposure exceeding limit."""
        positions = {
            "AAPL": 60000,
            "MSFT": 50000,  # Total 110%
        }

        result = self.engine.calculate_exposure_limits(
            positions, portfolio_value=100000, max_total_exposure_pct=1.0
        )

        assert result["total_exposure_pct"] == 110.0
        assert result["num_violations"] >= 1

    def test_risk_report_complete(self):
        """Test complete risk report generation."""
        portfolio_values = [100000, 101000, 99500, 102000]
        returns = [0.01, -0.015, 0.025]
        positions = {"AAPL": 25000, "MSFT": 20000}

        report = self.engine.calculate_risk_report(
            portfolio_value=102000,
            positions=positions,
            portfolio_values=portfolio_values,
            returns=returns,
        )

        assert "timestamp" in report
        assert "portfolio_value" in report
        assert "drawdown" in report
        assert "concentration" in report
        assert "exposure" in report


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
