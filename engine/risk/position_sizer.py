"""
Position Sizing Engine
======================

Implements various position sizing algorithms to determine optimal trade sizes
based on risk parameters and portfolio metrics.

Algorithms:
- Fixed Fractional: Risk a fixed percentage of portfolio per trade
- Kelly Criterion: Mathematically optimal position sizing based on win rate and payoff ratio
- Dynamic Sizing: Adjust position size based on volatility and win rate
"""

import logging
import math
from typing import Dict, Tuple, Optional

logger = logging.getLogger(__name__)


class PositionSizer:
    """Calculates optimal position sizes based on risk parameters."""

    def __init__(
        self,
        portfolio_value: float,
        risk_per_trade: float = 0.02,  # 2% default
        max_position_size: float = 0.05,  # 5% max per asset
        max_total_exposure: float = 1.0,  # 100% max total exposure
    ):
        """
        Initialize PositionSizer.

        Args:
            portfolio_value: Current portfolio value in USD
            risk_per_trade: Risk as percentage of portfolio per trade (0.02 = 2%)
            max_position_size: Max position size as percentage of portfolio per asset (0.05 = 5%)
            max_total_exposure: Max total exposure as percentage of portfolio (1.0 = 100%, no leverage)
        """
        self.portfolio_value = portfolio_value
        self.risk_per_trade = risk_per_trade
        self.max_position_size = max_position_size
        self.max_total_exposure = max_total_exposure

    def fixed_fractional(
        self, entry_price: float, stop_loss_price: float
    ) -> Dict[str, float]:
        """
        Fixed Fractional Position Sizing

        Risk a fixed percentage of portfolio per trade. Position size is determined by:
        - Risk amount: portfolio_value * risk_per_trade
        - Dollar risk per share: entry_price - stop_loss_price
        - Shares to buy: risk_amount / dollar_risk_per_share

        Args:
            entry_price: Entry price for the trade
            stop_loss_price: Stop loss price

        Returns:
            Dict with shares, position_value, risk_amount, dollar_risk_per_share
        """
        if entry_price <= 0 or stop_loss_price < 0:
            raise ValueError("Entry price must be positive, stop loss must be >= 0")

        if entry_price <= stop_loss_price:
            raise ValueError("Entry price must be above stop loss price")

        # Calculate risk amount in dollars
        risk_amount = self.portfolio_value * self.risk_per_trade

        # Calculate dollar risk per share
        dollar_risk_per_share = entry_price - stop_loss_price

        # Calculate number of shares
        shares = risk_amount / dollar_risk_per_share

        # Calculate position value
        position_value = shares * entry_price

        # Apply max position size constraint
        max_position_value = self.portfolio_value * self.max_position_size
        if position_value > max_position_value:
            shares = max_position_value / entry_price
            position_value = max_position_value
            logger.warning(
                f"Position size capped at max {self.max_position_size*100}% of portfolio"
            )

        return {
            "shares": math.floor(shares),
            "position_value": position_value,
            "risk_amount": risk_amount,
            "dollar_risk_per_share": dollar_risk_per_share,
            "method": "fixed_fractional",
        }

    def kelly_criterion(
        self,
        win_rate: float,
        win_loss_ratio: float,
        entry_price: float,
        stop_loss_price: float,
    ) -> Dict[str, float]:
        """
        Kelly Criterion Position Sizing

        The Kelly Criterion provides the mathematically optimal position size:
        f* = (bp - q) / b

        Where:
        - f* = optimal fraction of capital to risk
        - b = win/loss ratio (average win / average loss)
        - p = win rate (probability of win)
        - q = loss rate (1 - p)

        Args:
            win_rate: Win rate as decimal (0.55 = 55%)
            win_loss_ratio: Average win size / average loss size
            entry_price: Entry price for the trade
            stop_loss_price: Stop loss price

        Returns:
            Dict with kelly_fraction, shares, position_value, recommended_fractional

        Raises:
            ValueError: If inputs are invalid
        """
        if not (0 < win_rate < 1):
            raise ValueError("Win rate must be between 0 and 1")
        if win_loss_ratio <= 0:
            raise ValueError("Win/loss ratio must be positive")
        if entry_price <= 0:
            raise ValueError("Entry price must be positive")

        b = win_loss_ratio
        p = win_rate
        q = 1 - p

        # Calculate Kelly fraction
        kelly_fraction = (b * p - q) / b

        # Kelly is often too aggressive in practice, so use fractional Kelly (50-75%)
        # Default to 50% Kelly for safety
        fractional_kelly = kelly_fraction * 0.5

        # Cap Kelly fraction at max position size
        kelly_fraction_capped = min(fractional_kelly, self.max_position_size)

        if kelly_fraction < 0:
            logger.warning("Kelly fraction is negative; consider reducing risk")
            kelly_fraction_capped = 0

        # Calculate position using kelly fraction
        position_value = self.portfolio_value * kelly_fraction_capped
        shares = position_value / entry_price

        # Apply max position size constraint
        max_position_value = self.portfolio_value * self.max_position_size
        if position_value > max_position_value:
            shares = max_position_value / entry_price
            position_value = max_position_value

        return {
            "kelly_fraction": kelly_fraction,
            "fractional_kelly": fractional_kelly,
            "kelly_fraction_capped": kelly_fraction_capped,
            "shares": math.floor(shares),
            "position_value": position_value,
            "method": "kelly_criterion",
        }

    def dynamic_sizing(
        self,
        volatility: float,
        win_rate: float,
        current_positions: int,
    ) -> Dict[str, float]:
        """
        Dynamic Position Sizing

        Adjust position size based on market volatility and trading performance.
        Lower volatility and higher win rate = larger positions.

        Args:
            volatility: Current volatility (daily returns std dev) as decimal (0.02 = 2%)
            win_rate: Win rate as decimal (0.55 = 55%)
            current_positions: Current number of open positions

        Returns:
            Dict with volatility_factor, win_rate_factor, position_factor, recommended_risk
        """
        if not (0 < volatility < 1):
            raise ValueError("Volatility must be between 0 and 1")
        if not (0 <= win_rate <= 1):
            raise ValueError("Win rate must be between 0 and 1")

        # Volatility factor: higher volatility = lower position size
        # Use inverse relationship: 2% volatility = 1.0 factor, 5% volatility = 0.4 factor
        target_volatility = 0.02
        volatility_factor = min(target_volatility / volatility, 1.0)

        # Win rate factor: higher win rate = larger positions
        # 50% win rate = 1.0, 70% win rate = 1.4, 40% win rate = 0.6
        win_rate_factor = 1.0 + (win_rate - 0.5) * 0.8

        # Exposure factor: reduce size as we add more positions (diversification)
        # Assumes max 50 positions
        max_positions_factor = max(1.0 - (current_positions / 50.0) * 0.5, 0.5)

        # Combined position factor
        position_factor = volatility_factor * win_rate_factor * max_positions_factor

        # Cap at max risk per trade
        recommended_risk = self.risk_per_trade * position_factor
        recommended_risk = min(recommended_risk, self.risk_per_trade * 2.0)  # Max 4% if excellent conditions
        recommended_risk = max(recommended_risk, self.risk_per_trade * 0.5)  # Min 1% if poor conditions

        return {
            "volatility_factor": round(volatility_factor, 3),
            "win_rate_factor": round(win_rate_factor, 3),
            "position_factor": round(position_factor, 3),
            "recommended_risk_percentage": round(recommended_risk, 4),
            "method": "dynamic_sizing",
        }

    def validate_position(
        self,
        shares: float,
        entry_price: float,
        current_exposure: float,
    ) -> Tuple[bool, str]:
        """
        Validate a proposed position against risk constraints.

        Args:
            shares: Number of shares to buy
            entry_price: Entry price
            current_exposure: Current total portfolio exposure (0.0-1.0)

        Returns:
            Tuple of (is_valid, reason)
        """
        position_value = shares * entry_price
        new_exposure = current_exposure + (position_value / self.portfolio_value)

        # Check max position size
        position_pct = position_value / self.portfolio_value
        if position_pct > self.max_position_size:
            return (
                False,
                f"Position {position_pct*100:.2f}% exceeds max {self.max_position_size*100}%",
            )

        # Check total exposure
        if new_exposure > self.max_total_exposure:
            return (
                False,
                f"Total exposure {new_exposure*100:.2f}% exceeds max {self.max_total_exposure*100}%",
            )

        # Check for minimum position size (avoid penny positions)
        if position_value < 100:
            return False, "Position value too small (minimum $100)"

        return True, "Position valid"


if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)

    sizer = PositionSizer(portfolio_value=100000, risk_per_trade=0.02)

    # Example 1: Fixed Fractional Sizing
    print("=" * 60)
    print("Fixed Fractional Position Sizing")
    print("=" * 60)
    result = sizer.fixed_fractional(entry_price=150.0, stop_loss_price=147.0)
    print(f"Entry: $150.00, Stop Loss: $147.00 (2% risk)")
    print(f"Shares: {result['shares']}")
    print(f"Position Value: ${result['position_value']:.2f}")
    print(f"Risk Amount: ${result['risk_amount']:.2f}")
    print()

    # Example 2: Kelly Criterion
    print("=" * 60)
    print("Kelly Criterion Position Sizing")
    print("=" * 60)
    result = sizer.kelly_criterion(win_rate=0.55, win_loss_ratio=1.5, entry_price=150.0, stop_loss_price=147.0)
    print(f"Win Rate: 55%, Win/Loss Ratio: 1.5x")
    print(f"Kelly Fraction: {result['kelly_fraction']:.4f}")
    print(f"Fractional Kelly (50%): {result['fractional_kelly']:.4f}")
    print(f"Shares: {result['shares']}")
    print()

    # Example 3: Dynamic Sizing
    print("=" * 60)
    print("Dynamic Position Sizing")
    print("=" * 60)
    result = sizer.dynamic_sizing(volatility=0.025, win_rate=0.58, current_positions=5)
    print(f"Volatility: 2.5%, Win Rate: 58%, Current Positions: 5")
    print(f"Volatility Factor: {result['volatility_factor']}")
    print(f"Win Rate Factor: {result['win_rate_factor']}")
    print(f"Recommended Risk: {result['recommended_risk_percentage']*100:.2f}%")
