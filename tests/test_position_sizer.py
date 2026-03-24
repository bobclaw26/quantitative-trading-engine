"""
Tests for PositionSizer
=======================

Unit tests for position sizing algorithms.
"""

import pytest
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "engine"))

from risk.position_sizer import PositionSizer


class TestPositionSizer:
    """Test suite for PositionSizer class."""

    def setup_method(self):
        """Initialize test fixtures."""
        self.sizer = PositionSizer(
            portfolio_value=100000,
            risk_per_trade=0.02,
            max_position_size=0.05,
            max_total_exposure=1.0,
        )

    def test_initialization(self):
        """Test PositionSizer initialization."""
        assert self.sizer.portfolio_value == 100000
        assert self.sizer.risk_per_trade == 0.02
        assert self.sizer.max_position_size == 0.05

    def test_fixed_fractional_basic(self):
        """Test basic fixed fractional sizing."""
        result = self.sizer.fixed_fractional(entry_price=150.0, stop_loss_price=147.0)

        assert result["method"] == "fixed_fractional"
        assert result["shares"] > 0
        assert result["position_value"] > 0
        assert result["risk_amount"] == 100000 * 0.02  # 2% of $100k = $2000

    def test_fixed_fractional_validates_prices(self):
        """Test that fixed fractional validates price inputs."""
        with pytest.raises(ValueError):
            self.sizer.fixed_fractional(entry_price=0, stop_loss_price=147.0)

        with pytest.raises(ValueError):
            self.sizer.fixed_fractional(entry_price=150.0, stop_loss_price=150.0)

    def test_fixed_fractional_respects_max_position_size(self):
        """Test that fixed fractional respects max position size constraint."""
        # Very wide stop loss would exceed max position size
        result = self.sizer.fixed_fractional(entry_price=100.0, stop_loss_price=50.0)

        # Position should be capped at 5% of portfolio
        max_position_value = 100000 * 0.05
        assert result["position_value"] <= max_position_value

    def test_kelly_criterion_basic(self):
        """Test Kelly criterion calculation."""
        result = self.sizer.kelly_criterion(
            win_rate=0.55,
            win_loss_ratio=1.5,
            entry_price=150.0,
            stop_loss_price=147.0,
        )

        assert result["method"] == "kelly_criterion"
        assert "kelly_fraction" in result
        assert "fractional_kelly" in result
        assert result["shares"] > 0

    def test_kelly_criterion_validates_inputs(self):
        """Test Kelly criterion input validation."""
        with pytest.raises(ValueError):
            self.sizer.kelly_criterion(
                win_rate=1.5,  # Invalid
                win_loss_ratio=1.5,
                entry_price=150.0,
                stop_loss_price=147.0,
            )

        with pytest.raises(ValueError):
            self.sizer.kelly_criterion(
                win_rate=0.55,
                win_loss_ratio=-1.5,  # Invalid
                entry_price=150.0,
                stop_loss_price=147.0,
            )

    def test_kelly_criterion_conservative_fraction(self):
        """Test that Kelly uses fractional (conservative) sizing."""
        result = self.sizer.kelly_criterion(
            win_rate=0.55,
            win_loss_ratio=1.5,
            entry_price=150.0,
            stop_loss_price=147.0,
        )

        # Should use 50% Kelly
        assert result["fractional_kelly"] == result["kelly_fraction"] * 0.5

    def test_dynamic_sizing_basic(self):
        """Test dynamic position sizing."""
        result = self.sizer.dynamic_sizing(
            volatility=0.025,  # 2.5%
            win_rate=0.58,  # 58%
            current_positions=5,
        )

        assert result["method"] == "dynamic_sizing"
        assert "volatility_factor" in result
        assert "win_rate_factor" in result
        assert "recommended_risk_percentage" in result

    def test_dynamic_sizing_lower_volatility_higher_position(self):
        """Test that lower volatility results in larger positions."""
        result_low_vol = self.sizer.dynamic_sizing(
            volatility=0.01, win_rate=0.50, current_positions=0
        )
        result_high_vol = self.sizer.dynamic_sizing(
            volatility=0.05, win_rate=0.50, current_positions=0
        )

        assert (
            result_low_vol["recommended_risk_percentage"]
            > result_high_vol["recommended_risk_percentage"]
        )

    def test_dynamic_sizing_higher_win_rate_larger_position(self):
        """Test that higher win rate results in larger positions."""
        result_low_wr = self.sizer.dynamic_sizing(
            volatility=0.02, win_rate=0.40, current_positions=0
        )
        result_high_wr = self.sizer.dynamic_sizing(
            volatility=0.02, win_rate=0.70, current_positions=0
        )

        assert (
            result_high_wr["recommended_risk_percentage"]
            > result_low_wr["recommended_risk_percentage"]
        )

    def test_validate_position_within_limits(self):
        """Test position validation for within-limits position."""
        is_valid, reason = self.sizer.validate_position(
            shares=200, entry_price=100.0, current_exposure=0.3
        )

        assert is_valid is True

    def test_validate_position_exceeds_max_size(self):
        """Test position validation when exceeding max position size."""
        # 10% of portfolio > 5% max
        is_valid, reason = self.sizer.validate_position(
            shares=1000, entry_price=100.0, current_exposure=0.0
        )

        assert is_valid is False
        assert "exceeds max" in reason

    def test_validate_position_exceeds_total_exposure(self):
        """Test position validation when exceeding total exposure limit."""
        # 80% current + 30% new = 110% > 100% max
        is_valid, reason = self.sizer.validate_position(
            shares=300, entry_price=100.0, current_exposure=0.80
        )

        assert is_valid is False
        assert "exceeds max" in reason

    def test_validate_position_too_small(self):
        """Test that very small positions are rejected."""
        is_valid, reason = self.sizer.validate_position(
            shares=1, entry_price=1.0, current_exposure=0.0
        )

        assert is_valid is False
        assert "too small" in reason.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
