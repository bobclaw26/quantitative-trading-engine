"""
Tests for StopLossManager
=========================

Unit tests for stop-loss and take-profit management.
"""

import pytest
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "engine"))

from risk.stop_loss import StopLossManager, StopLossType


class TestStopLossManager:
    """Test suite for StopLossManager class."""

    def setup_method(self):
        """Initialize test fixtures."""
        self.manager = StopLossManager(
            default_stop_loss_pct=0.02,
            default_take_profit_pct=0.05,
            trailing_stop_pct=0.03,
        )

    def test_calculate_fixed_stop_loss(self):
        """Test fixed stop loss calculation."""
        result = self.manager.calculate_fixed_stop_loss(
            entry_price=150.0, stop_loss_pct=0.02
        )

        assert result["entry_price"] == 150.0
        assert result["stop_price"] == 147.0
        assert result["stop_loss_type"] == StopLossType.FIXED.value

    def test_fixed_stop_loss_uses_default(self):
        """Test that fixed stop loss uses default if not specified."""
        result = self.manager.calculate_fixed_stop_loss(entry_price=100.0)

        expected_stop = 100.0 * (1 - 0.02)
        assert result["stop_price"] == expected_stop

    def test_fixed_stop_loss_validates_input(self):
        """Test stop loss input validation."""
        with pytest.raises(ValueError):
            self.manager.calculate_fixed_stop_loss(entry_price=0)

        with pytest.raises(ValueError):
            self.manager.calculate_fixed_stop_loss(
                entry_price=100.0, stop_loss_pct=1.5
            )

    def test_calculate_take_profit(self):
        """Test take profit target calculation."""
        result = self.manager.calculate_take_profit(
            entry_price=100.0, take_profit_pct=0.05
        )

        assert result["entry_price"] == 100.0
        assert result["target_price"] == 105.0
        assert result["profit_pct"] == 0.05

    def test_take_profit_reward_to_risk(self):
        """Test take profit reward-to-risk calculation."""
        result = self.manager.calculate_take_profit(
            entry_price=100.0, take_profit_pct=0.05
        )

        # With default 2% stop loss: 5% / 2% = 2.5:1
        expected_ratio = 0.05 / 0.02
        assert result["reward_to_risk_ratio"] == expected_ratio

    def test_calculate_trailing_stop(self):
        """Test trailing stop calculation."""
        result = self.manager.calculate_trailing_stop(
            entry_price=100.0,
            current_price=105.0,
            highest_price=107.0,
            trailing_stop_pct=0.03,
        )

        # 107 * (1 - 0.03) = 103.79
        expected_stop = 107.0 * (1 - 0.03)
        assert abs(result["stop_price"] - expected_stop) < 0.01
        assert result["is_triggered"] is False

    def test_trailing_stop_triggered(self):
        """Test trailing stop trigger condition."""
        result = self.manager.calculate_trailing_stop(
            entry_price=100.0,
            current_price=102.0,
            highest_price=107.0,
            trailing_stop_pct=0.03,
        )

        # Current price (102) < stop (103.79)
        assert result["is_triggered"] is True

    def test_calculate_atr_based_stop(self):
        """Test ATR-based stop loss calculation."""
        result = self.manager.calculate_atr_based_stop(
            entry_price=150.0, atr=2.5, atr_multiplier=2.0
        )

        # 150 - (2.5 * 2) = 145
        assert result["stop_price"] == 145.0
        assert result["atr"] == 2.5

    def test_atr_stop_loss_percentage(self):
        """Test ATR stop loss expressed as percentage."""
        result = self.manager.calculate_atr_based_stop(
            entry_price=100.0, atr=2.0, atr_multiplier=2.0
        )

        # (100 - 96) / 100 = 0.04 = 4%
        assert result["stop_loss_pct"] == 0.04

    def test_check_stop_trigger_long_position(self):
        """Test stop trigger check for LONG position."""
        is_triggered, reason = self.manager.check_stop_trigger(
            current_price=145.0, stop_price=147.0, side="LONG"
        )

        assert is_triggered is True
        assert "Stop triggered" in reason

    def test_check_stop_not_triggered_long(self):
        """Test stop not triggered for LONG position."""
        is_triggered, reason = self.manager.check_stop_trigger(
            current_price=150.0, stop_price=147.0, side="LONG"
        )

        assert is_triggered is False

    def test_check_stop_trigger_short_position(self):
        """Test stop trigger check for SHORT position."""
        is_triggered, reason = self.manager.check_stop_trigger(
            current_price=152.0, stop_price=150.0, side="SHORT"
        )

        assert is_triggered is True

    def test_check_profit_target_reached(self):
        """Test profit target reached for LONG position."""
        is_reached, reason = self.manager.check_profit_target(
            current_price=105.0, target_price=105.0, side="LONG"
        )

        assert is_reached is True

    def test_check_profit_target_not_reached(self):
        """Test profit target not reached for LONG position."""
        is_reached, reason = self.manager.check_profit_target(
            current_price=103.0, target_price=105.0, side="LONG"
        )

        assert is_reached is False

    def test_calculate_position_exit(self):
        """Test position exit metrics calculation."""
        result = self.manager.calculate_position_exit(
            entry_price=100.0,
            current_price=105.0,
            shares=100,
            stop_price=98.0,
        )

        # Current P&L: (105 - 100) * 100 = 500
        assert result["unrealized_pnl"] == 500.0
        assert result["unrealized_pnl_pct"] == 0.05

        # Stop loss P&L: (98 - 100) * 100 = -200
        assert result["stop_loss_amount"] == -200.0

        # Distance to stop: 105 - 98 = 7
        assert result["distance_to_stop"] == 7.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
