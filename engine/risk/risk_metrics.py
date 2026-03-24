"""
Risk Metrics Engine
===================

Calculates comprehensive risk metrics to monitor portfolio health and adherence
to risk constraints.

Metrics:
- Value at Risk (VaR): Maximum potential loss at given confidence level
- Maximum Drawdown: Largest peak-to-trough decline
- Sharpe Ratio: Return per unit of risk
- Sortino Ratio: Return per unit of downside risk
- Concentration Risk: Exposure to individual assets/sectors
- Liquidity Risk: Position size relative to average volume
"""

import logging
import math
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
import statistics

logger = logging.getLogger(__name__)


class RiskMetricsEngine:
    """Calculates and monitors portfolio risk metrics."""

    def __init__(self, risk_free_rate: float = 0.02):
        """
        Initialize RiskMetricsEngine.

        Args:
            risk_free_rate: Annual risk-free rate for Sharpe/Sortino calculations (0.02 = 2%)
        """
        self.risk_free_rate = risk_free_rate

    def calculate_max_drawdown(
        self, portfolio_values: List[float]
    ) -> Dict[str, float]:
        """
        Calculate maximum drawdown from a series of portfolio values.

        Drawdown is the peak-to-trough decline during a specific period.
        Max drawdown is the largest such decline.

        Args:
            portfolio_values: List of portfolio values in chronological order

        Returns:
            Dict with max_drawdown_pct, max_drawdown_amount, peak_value, trough_value
        """
        if len(portfolio_values) < 2:
            raise ValueError("Need at least 2 portfolio values")

        max_drawdown = 0.0
        peak_value = portfolio_values[0]
        trough_value = portfolio_values[0]
        peak_index = 0
        trough_index = 0

        for i, value in enumerate(portfolio_values):
            if value > peak_value:
                peak_value = value
                peak_index = i

            drawdown = (peak_value - value) / peak_value

            if drawdown > max_drawdown:
                max_drawdown = drawdown
                trough_value = value
                trough_index = i

        return {
            "max_drawdown_pct": round(max_drawdown * 100, 2),
            "max_drawdown_amount": round(peak_value - trough_value, 2),
            "peak_value": round(peak_value, 2),
            "trough_value": round(trough_value, 2),
            "peak_index": peak_index,
            "trough_index": trough_index,
        }

    def calculate_var(
        self,
        returns: List[float],
        confidence_level: float = 0.95,
    ) -> Dict[str, float]:
        """
        Calculate Value at Risk (VaR) using historical simulation.

        VaR answers: What is the maximum loss we can expect with X% confidence?

        Args:
            returns: List of historical returns as decimals
            confidence_level: Confidence level (0.95 = 95%)

        Returns:
            Dict with var_pct, var_amount_per_100k, interpretation
        """
        if len(returns) < 10:
            raise ValueError("Need at least 10 return observations")

        if not (0 < confidence_level < 1):
            raise ValueError("Confidence level must be between 0 and 1")

        # Sort returns in ascending order
        sorted_returns = sorted(returns)

        # Calculate the index for the confidence level
        # E.g., 95% confidence on 100 observations = bottom 5 observations
        index = int(len(sorted_returns) * (1 - confidence_level))
        index = max(0, min(index, len(sorted_returns) - 1))

        # VaR is the return at that index (worst expected return at confidence level)
        var_return = sorted_returns[index]

        # Convert to negative for clearer interpretation
        var_pct = abs(var_return) * 100

        # Per $100k portfolio
        var_per_100k = abs(var_return) * 100000

        return {
            "var_pct": round(var_pct, 2),
            "var_amount_per_100k": round(var_per_100k, 2),
            "confidence_level": confidence_level,
            "interpretation": f"With {confidence_level*100:.0f}% confidence, max expected daily loss is {var_pct:.2f}%",
        }

    def calculate_sharpe_ratio(
        self,
        returns: List[float],
        periods_per_year: int = 252,
    ) -> Dict[str, float]:
        """
        Calculate Sharpe Ratio: excess return per unit of volatility.

        Sharpe Ratio = (Average Return - Risk-Free Rate) / Volatility

        Args:
            returns: List of periodic returns as decimals
            periods_per_year: Number of periods per year (252 for daily, 52 for weekly)

        Returns:
            Dict with sharpe_ratio, annualized_return, annualized_volatility
        """
        if len(returns) < 2:
            raise ValueError("Need at least 2 return observations")

        # Calculate average return
        avg_return = statistics.mean(returns)

        # Calculate volatility (standard deviation)
        if len(returns) == 1:
            volatility = 0
        else:
            volatility = statistics.stdev(returns)

        if volatility == 0:
            return {
                "sharpe_ratio": 0.0,
                "annualized_return": round(avg_return * periods_per_year * 100, 2),
                "annualized_volatility": 0.0,
                "note": "Volatility is zero; Sharpe ratio undefined",
            }

        # Annualize metrics
        periods_per_year = float(periods_per_year)
        annualized_return = avg_return * periods_per_year
        annualized_volatility = volatility * math.sqrt(periods_per_year)

        # Calculate Sharpe ratio
        excess_return = annualized_return - self.risk_free_rate
        sharpe_ratio = excess_return / annualized_volatility if annualized_volatility > 0 else 0

        return {
            "sharpe_ratio": round(sharpe_ratio, 4),
            "annualized_return": round(annualized_return * 100, 2),
            "annualized_volatility": round(annualized_volatility * 100, 2),
            "excess_return": round(excess_return * 100, 2),
        }

    def calculate_sortino_ratio(
        self,
        returns: List[float],
        target_return: float = 0.0,
        periods_per_year: int = 252,
    ) -> Dict[str, float]:
        """
        Calculate Sortino Ratio: excess return per unit of downside risk.

        Sortino only penalizes downside volatility (below target return).

        Args:
            returns: List of periodic returns as decimals
            target_return: Target return threshold (0.0 for zero)
            periods_per_year: Number of periods per year

        Returns:
            Dict with sortino_ratio, downside_deviation, excess_return
        """
        if len(returns) < 2:
            raise ValueError("Need at least 2 return observations")

        # Calculate excess returns (returns below target)
        excess_returns = [r - target_return for r in returns]

        # Calculate downside deviation (only negative returns)
        downside_returns = [r for r in excess_returns if r < 0]

        if len(downside_returns) == 0:
            return {
                "sortino_ratio": float("inf"),
                "downside_deviation": 0.0,
                "note": "No downside returns; ratio is infinite",
            }

        downside_variance = sum(r**2 for r in downside_returns) / len(returns)
        downside_deviation = math.sqrt(downside_variance)

        if downside_deviation == 0:
            return {
                "sortino_ratio": float("inf"),
                "downside_deviation": 0.0,
                "note": "Downside deviation is zero",
            }

        # Annualize
        avg_return = statistics.mean(returns)
        annualized_return = avg_return * periods_per_year
        annualized_downside_deviation = downside_deviation * math.sqrt(periods_per_year)

        # Calculate Sortino ratio
        excess_return = annualized_return - self.risk_free_rate
        sortino_ratio = excess_return / annualized_downside_deviation

        return {
            "sortino_ratio": round(sortino_ratio, 4),
            "excess_return": round(excess_return * 100, 2),
            "downside_deviation": round(downside_deviation * 100, 2),
            "annualized_downside_deviation": round(annualized_downside_deviation * 100, 2),
        }

    def calculate_concentration_risk(
        self, positions: Dict[str, float]
    ) -> Dict[str, float]:
        """
        Calculate concentration risk (Herfindahl-Hirschman Index).

        HHI measures how concentrated portfolio is in individual positions.
        HHI = Sum of (position_pct)^2
        - HHI < 0.25: Well diversified
        - HHI 0.25-0.5: Moderate concentration
        - HHI > 0.5: High concentration

        Args:
            positions: Dict of {symbol: position_value}

        Returns:
            Dict with hhi, concentration_level, top_holdings_pct
        """
        if not positions:
            return {
                "hhi": 0.0,
                "concentration_level": "N/A",
                "num_positions": 0,
            }

        total_value = sum(positions.values())

        if total_value == 0:
            return {
                "hhi": 0.0,
                "concentration_level": "N/A",
                "num_positions": len(positions),
            }

        # Calculate HHI
        hhi = 0.0
        for position_value in positions.values():
            pct = position_value / total_value
            hhi += pct**2

        # Determine concentration level
        if hhi < 0.25:
            level = "Well diversified"
        elif hhi < 0.5:
            level = "Moderate concentration"
        else:
            level = "High concentration"

        # Top holdings
        sorted_positions = sorted(positions.items(), key=lambda x: x[1], reverse=True)
        top_3_pct = sum(v / total_value * 100 for _, v in sorted_positions[:3])

        return {
            "hhi": round(hhi, 4),
            "concentration_level": level,
            "num_positions": len(positions),
            "top_3_holdings_pct": round(top_3_pct, 2),
        }

    def calculate_exposure_limits(
        self,
        positions: Dict[str, float],
        portfolio_value: float,
        max_position_pct: float = 0.05,
        max_total_exposure_pct: float = 1.0,
    ) -> Dict[str, any]:
        """
        Calculate exposure relative to limits.

        Args:
            positions: Dict of {symbol: position_value}
            portfolio_value: Total portfolio value
            max_position_pct: Max position size as % of portfolio
            max_total_exposure_pct: Max total exposure as % of portfolio

        Returns:
            Dict with exposure metrics and violations
        """
        if portfolio_value <= 0:
            raise ValueError("Portfolio value must be positive")

        total_exposure = sum(positions.values()) / portfolio_value
        violations = []

        # Check individual position limits
        for symbol, value in positions.items():
            position_pct = value / portfolio_value
            if position_pct > max_position_pct:
                violations.append(
                    f"{symbol}: {position_pct*100:.2f}% exceeds max {max_position_pct*100}%"
                )

        # Check total exposure limit
        if total_exposure > max_total_exposure_pct:
            violations.append(
                f"Total exposure {total_exposure*100:.2f}% exceeds max {max_total_exposure_pct*100}%"
            )

        return {
            "total_exposure_pct": round(total_exposure * 100, 2),
            "max_exposure_pct": round(max_total_exposure_pct * 100, 2),
            "available_capacity_pct": round((max_total_exposure_pct - total_exposure) * 100, 2),
            "num_violations": len(violations),
            "violations": violations,
        }

    def calculate_risk_report(
        self,
        portfolio_value: float,
        positions: Dict[str, float],
        portfolio_values: List[float],
        returns: List[float],
    ) -> Dict[str, any]:
        """
        Generate comprehensive risk report.

        Args:
            portfolio_value: Current portfolio value
            positions: Dict of {symbol: position_value}
            portfolio_values: Historical portfolio values
            returns: Historical returns

        Returns:
            Complete risk report
        """
        report = {
            "timestamp": datetime.utcnow().isoformat(),
            "portfolio_value": round(portfolio_value, 2),
        }

        # Drawdown analysis
        if portfolio_values:
            dd = self.calculate_max_drawdown(portfolio_values)
            report["drawdown"] = dd

        # VaR analysis
        if returns and len(returns) >= 10:
            var = self.calculate_var(returns)
            report["var"] = var

        # Sharpe Ratio
        if returns and len(returns) >= 2:
            sharpe = self.calculate_sharpe_ratio(returns)
            report["sharpe_ratio"] = sharpe

        # Sortino Ratio
        if returns and len(returns) >= 2:
            sortino = self.calculate_sortino_ratio(returns)
            report["sortino_ratio"] = sortino

        # Concentration Risk
        conc = self.calculate_concentration_risk(positions)
        report["concentration"] = conc

        # Exposure Analysis
        exposure = self.calculate_exposure_limits(
            positions, portfolio_value
        )
        report["exposure"] = exposure

        return report


if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)

    engine = RiskMetricsEngine()

    # Sample data
    portfolio_values = [100000, 101000, 99500, 102000, 98000, 101500, 103000, 100500]
    returns = [0.01, -0.015, 0.025, -0.04, 0.035, 0.015, -0.025]
    positions = {"AAPL": 25000, "MSFT": 20000, "GOOGL": 15000, "AMZN": 12000}

    print("=" * 60)
    print("Max Drawdown Analysis")
    print("=" * 60)
    dd = engine.calculate_max_drawdown(portfolio_values)
    print(f"Max Drawdown: {dd['max_drawdown_pct']}%")
    print(f"Peak: ${dd['peak_value']:.2f} → Trough: ${dd['trough_value']:.2f}")
    print()

    print("=" * 60)
    print("Value at Risk (95% confidence)")
    print("=" * 60)
    var = engine.calculate_var(returns, confidence_level=0.95)
    print(f"VaR: {var['var_pct']:.2f}%")
    print(f"Per $100k: ${var['var_amount_per_100k']:.2f}")
    print()

    print("=" * 60)
    print("Sharpe Ratio Analysis")
    print("=" * 60)
    sharpe = engine.calculate_sharpe_ratio(returns)
    print(f"Sharpe Ratio: {sharpe['sharpe_ratio']:.4f}")
    print(f"Annualized Return: {sharpe['annualized_return']}%")
    print()

    print("=" * 60)
    print("Concentration Risk")
    print("=" * 60)
    conc = engine.calculate_concentration_risk(positions)
    print(f"HHI: {conc['hhi']:.4f}")
    print(f"Level: {conc['concentration_level']}")
    print(f"Top 3 Holdings: {conc['top_3_holdings_pct']:.2f}%")
