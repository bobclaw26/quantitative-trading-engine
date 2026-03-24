"""
Stop Loss & Take Profit Management
===================================

Manages stop-loss orders and take-profit targets to automatically exit positions
based on predefined risk/reward parameters.

Features:
- Fixed percentage stop losses
- Trailing stops
- Profit targets with dynamic adjustment
- Stop loss validation and enforcement
"""

import logging
from enum import Enum
from typing import Dict, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class StopLossType(Enum):
    """Types of stop loss orders."""
    FIXED = "fixed"  # Fixed percentage below entry
    TRAILING = "trailing"  # Trails behind highest price
    VOLATILITY_BASED = "volatility_based"  # Based on ATR or std dev


class StopLossManager:
    """Manages stop-loss orders and take-profit targets."""

    def __init__(
        self,
        default_stop_loss_pct: float = 0.02,  # 2% default
        default_take_profit_pct: float = 0.05,  # 5% default take profit
        trailing_stop_pct: float = 0.03,  # 3% trailing stop
    ):
        """
        Initialize StopLossManager.

        Args:
            default_stop_loss_pct: Default stop loss as % below entry (0.02 = 2%)
            default_take_profit_pct: Default take profit as % above entry (0.05 = 5%)
            trailing_stop_pct: Trailing stop distance as % below peak (0.03 = 3%)
        """
        self.default_stop_loss_pct = default_stop_loss_pct
        self.default_take_profit_pct = default_take_profit_pct
        self.trailing_stop_pct = trailing_stop_pct

    def calculate_fixed_stop_loss(
        self, entry_price: float, stop_loss_pct: Optional[float] = None
    ) -> Dict[str, float]:
        """
        Calculate fixed stop loss price.

        Args:
            entry_price: Entry price of the position
            stop_loss_pct: Stop loss percentage (optional, uses default if not provided)

        Returns:
            Dict with stop_price, risk_amount_pct, stop_loss_type
        """
        if entry_price <= 0:
            raise ValueError("Entry price must be positive")

        stop_pct = stop_loss_pct or self.default_stop_loss_pct

        if not (0 < stop_pct < 1):
            raise ValueError("Stop loss percentage must be between 0 and 1")

        stop_price = entry_price * (1 - stop_pct)

        return {
            "stop_price": round(stop_price, 2),
            "entry_price": entry_price,
            "stop_loss_pct": stop_pct,
            "risk_amount_pct": stop_pct,
            "stop_loss_type": StopLossType.FIXED.value,
        }

    def calculate_take_profit(
        self, entry_price: float, take_profit_pct: Optional[float] = None
    ) -> Dict[str, float]:
        """
        Calculate take profit target price.

        Args:
            entry_price: Entry price of the position
            take_profit_pct: Take profit percentage (optional, uses default if not provided)

        Returns:
            Dict with target_price, profit_amount_pct, reward_to_risk_ratio
        """
        if entry_price <= 0:
            raise ValueError("Entry price must be positive")

        tp_pct = take_profit_pct or self.default_take_profit_pct

        if not (0 < tp_pct < 1):
            raise ValueError("Take profit percentage must be between 0 and 1")

        target_price = entry_price * (1 + tp_pct)

        # Calculate reward to risk ratio (assuming default 2% stop loss)
        risk_pct = self.default_stop_loss_pct
        reward_to_risk = tp_pct / risk_pct

        return {
            "target_price": round(target_price, 2),
            "entry_price": entry_price,
            "profit_pct": tp_pct,
            "reward_to_risk_ratio": round(reward_to_risk, 2),
        }

    def calculate_trailing_stop(
        self,
        entry_price: float,
        current_price: float,
        highest_price: float,
        trailing_stop_pct: Optional[float] = None,
    ) -> Dict[str, float]:
        """
        Calculate trailing stop loss price.

        Trailing stop follows the highest price reached, maintaining a fixed distance below.

        Args:
            entry_price: Original entry price
            current_price: Current market price
            highest_price: Highest price reached since entry
            trailing_stop_pct: Trailing stop distance as % (optional, uses default if not provided)

        Returns:
            Dict with stop_price, highest_price, trailing_distance, is_triggered
        """
        if entry_price <= 0 or current_price <= 0:
            raise ValueError("Prices must be positive")

        trail_pct = trailing_stop_pct or self.trailing_stop_pct

        # Trailing stop is X% below the highest price reached
        stop_price = highest_price * (1 - trail_pct)

        # Check if stop is triggered (current price <= stop price)
        is_triggered = current_price <= stop_price

        return {
            "stop_price": round(stop_price, 2),
            "current_price": current_price,
            "highest_price": highest_price,
            "trailing_distance_pct": trail_pct,
            "is_triggered": is_triggered,
            "stop_loss_type": StopLossType.TRAILING.value,
        }

    def calculate_atr_based_stop(
        self,
        entry_price: float,
        atr: float,
        atr_multiplier: float = 2.0,
    ) -> Dict[str, float]:
        """
        Calculate stop loss based on Average True Range (ATR).

        ATR-based stops are adjusted to market volatility:
        - High volatility = wider stops
        - Low volatility = tighter stops

        Args:
            entry_price: Entry price of the position
            atr: Average True Range value
            atr_multiplier: How many ATRs to use for stop (2.0 = 2x ATR)

        Returns:
            Dict with stop_price, atr, atr_multiplier, stop_loss_type
        """
        if entry_price <= 0 or atr <= 0:
            raise ValueError("Entry price and ATR must be positive")

        if atr_multiplier <= 0:
            raise ValueError("ATR multiplier must be positive")

        # Stop is ATR * multiplier below entry
        stop_price = entry_price - (atr * atr_multiplier)

        # Calculate as percentage for reporting
        stop_loss_pct = (entry_price - stop_price) / entry_price

        return {
            "stop_price": round(stop_price, 2),
            "entry_price": entry_price,
            "atr": round(atr, 2),
            "atr_multiplier": atr_multiplier,
            "stop_loss_pct": round(stop_loss_pct, 4),
            "stop_loss_type": StopLossType.VOLATILITY_BASED.value,
        }

    def check_stop_trigger(
        self,
        current_price: float,
        stop_price: float,
        side: str = "LONG",
    ) -> Tuple[bool, str]:
        """
        Check if a stop loss has been triggered.

        Args:
            current_price: Current market price
            stop_price: Stop loss price
            side: Position side ("LONG" or "SHORT")

        Returns:
            Tuple of (is_triggered, reason)
        """
        if side == "LONG":
            if current_price <= stop_price:
                return True, f"Stop triggered: price ${current_price:.2f} <= stop ${stop_price:.2f}"
            return False, f"Price ${current_price:.2f} above stop ${stop_price:.2f}"
        elif side == "SHORT":
            if current_price >= stop_price:
                return True, f"Stop triggered: price ${current_price:.2f} >= stop ${stop_price:.2f}"
            return False, f"Price ${current_price:.2f} below stop ${stop_price:.2f}"
        else:
            raise ValueError("Side must be 'LONG' or 'SHORT'")

    def check_profit_target(
        self,
        current_price: float,
        target_price: float,
        side: str = "LONG",
    ) -> Tuple[bool, str]:
        """
        Check if a take profit target has been reached.

        Args:
            current_price: Current market price
            target_price: Take profit target price
            side: Position side ("LONG" or "SHORT")

        Returns:
            Tuple of (is_triggered, reason)
        """
        if side == "LONG":
            if current_price >= target_price:
                return True, f"Target reached: price ${current_price:.2f} >= target ${target_price:.2f}"
            return False, f"Price ${current_price:.2f} below target ${target_price:.2f}"
        elif side == "SHORT":
            if current_price <= target_price:
                return True, f"Target reached: price ${current_price:.2f} <= target ${target_price:.2f}"
            return False, f"Price ${current_price:.2f} above target ${target_price:.2f}"
        else:
            raise ValueError("Side must be 'LONG' or 'SHORT'")

    def calculate_position_exit(
        self,
        entry_price: float,
        current_price: float,
        shares: int,
        stop_price: float,
    ) -> Dict[str, float]:
        """
        Calculate exit metrics for a position.

        Args:
            entry_price: Entry price
            current_price: Current price
            shares: Number of shares
            stop_price: Stop loss price

        Returns:
            Dict with current_pnl, stop_loss_pnl, win_loss_ratio, etc.
        """
        # Current unrealized P&L
        unrealized_pnl = (current_price - entry_price) * shares
        unrealized_pnl_pct = (current_price - entry_price) / entry_price

        # P&L if stop triggered
        stop_loss_amount = (stop_price - entry_price) * shares
        stop_loss_pct = (stop_price - entry_price) / entry_price

        # Distance to stop
        distance_to_stop = current_price - stop_price
        distance_to_stop_pct = distance_to_stop / current_price

        return {
            "unrealized_pnl": round(unrealized_pnl, 2),
            "unrealized_pnl_pct": round(unrealized_pnl_pct, 4),
            "stop_loss_amount": round(stop_loss_amount, 2),
            "stop_loss_pct": round(stop_loss_pct, 4),
            "distance_to_stop": round(distance_to_stop, 2),
            "distance_to_stop_pct": round(distance_to_stop_pct, 4),
        }


if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)

    manager = StopLossManager()

    # Example 1: Fixed Stop Loss
    print("=" * 60)
    print("Fixed Stop Loss")
    print("=" * 60)
    result = manager.calculate_fixed_stop_loss(entry_price=150.0, stop_loss_pct=0.02)
    print(f"Entry: $150.00, Stop Loss: 2%")
    print(f"Stop Price: ${result['stop_price']}")
    print()

    # Example 2: Take Profit
    print("=" * 60)
    print("Take Profit Target")
    print("=" * 60)
    result = manager.calculate_take_profit(entry_price=150.0, take_profit_pct=0.05)
    print(f"Entry: $150.00, Take Profit: 5%")
    print(f"Target Price: ${result['target_price']}")
    print(f"Reward/Risk Ratio: {result['reward_to_risk_ratio']}:1")
    print()

    # Example 3: Trailing Stop
    print("=" * 60)
    print("Trailing Stop Loss")
    print("=" * 60)
    result = manager.calculate_trailing_stop(
        entry_price=150.0, current_price=155.0, highest_price=157.5
    )
    print(f"Entry: $150.00, Current: $155.00, High: $157.50")
    print(f"Trailing Stop (3%): ${result['stop_price']}")
    print(f"Triggered: {result['is_triggered']}")
    print()

    # Example 4: ATR-Based Stop
    print("=" * 60)
    print("ATR-Based Stop Loss")
    print("=" * 60)
    result = manager.calculate_atr_based_stop(entry_price=150.0, atr=2.5)
    print(f"Entry: $150.00, ATR: ${2.5}")
    print(f"Stop Price (2x ATR): ${result['stop_price']}")
