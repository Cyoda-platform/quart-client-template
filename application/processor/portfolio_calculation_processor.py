"""
PortfolioCalculationProcessor for Trading Platform

Handles portfolio valuation, P&L calculation, and risk metrics
computation for real-time portfolio management.
"""

import logging
from typing import Any
from decimal import Decimal
from datetime import datetime, timezone

from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor
from application.entity.portfolio.version_1.portfolio import Portfolio


class PortfolioCalculationProcessor(CyodaProcessor):
    """
    Processor for Portfolio calculations including valuation,
    P&L computation, and risk metrics calculation.
    """

    def __init__(self) -> None:
        super().__init__(
            name="PortfolioCalculationProcessor",
            description="Calculates portfolio values, P&L, and risk metrics",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Process the Portfolio calculations.

        Args:
            entity: The Portfolio to calculate (must be in 'created' state)
            **kwargs: Additional processing parameters

        Returns:
            The portfolio with updated calculations
        """
        try:
            self.logger.info(
                f"Calculating Portfolio {getattr(entity, 'technical_id', '<unknown>')}"
            )

            # Cast the entity to Portfolio for type-safe operations
            portfolio = cast_entity(entity, Portfolio)

            # Perform portfolio calculations
            calculations = await self._calculate_portfolio_metrics(portfolio)
            
            # Update portfolio with calculated values
            portfolio.total_value = calculations["total_value"]
            portfolio.market_value = calculations["market_value"]
            portfolio.invested_value = calculations["invested_value"]
            portfolio.daily_pnl = calculations["daily_pnl"]
            portfolio.total_pnl = calculations["total_pnl"]
            portfolio.unrealized_pnl = calculations["unrealized_pnl"]
            portfolio.realized_pnl = calculations["realized_pnl"]
            
            # Update risk metrics
            portfolio.var95 = calculations["var95"]
            portfolio.beta = calculations["beta"]
            portfolio.sharpe_ratio = calculations["sharpe_ratio"]
            portfolio.max_drawdown = calculations["max_drawdown"]
            
            # Update position counts
            portfolio.position_count = calculations["position_count"]
            portfolio.long_positions = calculations["long_positions"]
            portfolio.short_positions = calculations["short_positions"]
            
            # Update timestamp
            portfolio.last_updated = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

            self.logger.info(
                f"Portfolio {portfolio.technical_id} calculated successfully - "
                f"Total Value: {portfolio.total_value}, P&L: {portfolio.total_pnl}"
            )

            return portfolio

        except Exception as e:
            self.logger.error(
                f"Error calculating portfolio {getattr(entity, 'technical_id', '<unknown>')}: {str(e)}"
            )
            raise

    async def _calculate_portfolio_metrics(self, portfolio: Portfolio) -> dict:
        """
        Calculate comprehensive portfolio metrics.

        Args:
            portfolio: The Portfolio to calculate

        Returns:
            Dictionary containing calculated metrics
        """
        # Simulate portfolio positions and market data
        # In real system, would query positions and market data services
        
        positions = await self._get_portfolio_positions(portfolio.client_id)
        market_data = await self._get_market_data()
        
        # Calculate basic values
        cash_balance = portfolio.cash_balance or Decimal("0")
        market_value = self._calculate_market_value(positions, market_data)
        invested_value = self._calculate_invested_value(positions)
        total_value = cash_balance + market_value
        
        # Calculate P&L
        unrealized_pnl = market_value - invested_value
        realized_pnl = self._calculate_realized_pnl(positions)
        total_pnl = unrealized_pnl + realized_pnl
        daily_pnl = self._calculate_daily_pnl(positions, market_data)
        
        # Calculate risk metrics
        var95 = self._calculate_var95(positions, market_data)
        beta = self._calculate_beta(positions, market_data)
        sharpe_ratio = self._calculate_sharpe_ratio(total_pnl, total_value)
        max_drawdown = self._calculate_max_drawdown(portfolio)
        
        # Count positions
        position_count = len(positions)
        long_positions = len([p for p in positions if p["quantity"] > 0])
        short_positions = len([p for p in positions if p["quantity"] < 0])
        
        return {
            "total_value": total_value,
            "market_value": market_value,
            "invested_value": invested_value,
            "daily_pnl": daily_pnl,
            "total_pnl": total_pnl,
            "unrealized_pnl": unrealized_pnl,
            "realized_pnl": realized_pnl,
            "var95": var95,
            "beta": beta,
            "sharpe_ratio": sharpe_ratio,
            "max_drawdown": max_drawdown,
            "position_count": position_count,
            "long_positions": long_positions,
            "short_positions": short_positions,
        }

    async def _get_portfolio_positions(self, client_id: str) -> list:
        """Get positions for the portfolio client."""
        # Simulate portfolio positions
        return [
            {"symbol": "AAPL", "quantity": Decimal("100"), "avg_price": Decimal("150"), "realized_pnl": Decimal("500")},
            {"symbol": "MSFT", "quantity": Decimal("50"), "avg_price": Decimal("300"), "realized_pnl": Decimal("200")},
            {"symbol": "GOOGL", "quantity": Decimal("-10"), "avg_price": Decimal("2500"), "realized_pnl": Decimal("-100")},
        ]

    async def _get_market_data(self) -> dict:
        """Get current market prices."""
        return {
            "AAPL": Decimal("155"),
            "MSFT": Decimal("305"),
            "GOOGL": Decimal("2480"),
        }

    def _calculate_market_value(self, positions: list, market_data: dict) -> Decimal:
        """Calculate total market value of positions."""
        total = Decimal("0")
        for pos in positions:
            price = market_data.get(pos["symbol"], pos["avg_price"])
            total += pos["quantity"] * price
        return total

    def _calculate_invested_value(self, positions: list) -> Decimal:
        """Calculate total invested value (cost basis)."""
        total = Decimal("0")
        for pos in positions:
            total += abs(pos["quantity"]) * pos["avg_price"]
        return total

    def _calculate_realized_pnl(self, positions: list) -> Decimal:
        """Calculate total realized P&L."""
        return sum(pos["realized_pnl"] for pos in positions)

    def _calculate_daily_pnl(self, positions: list, market_data: dict) -> Decimal:
        """Calculate daily P&L (simplified)."""
        # Simulate daily P&L calculation
        return Decimal("1250.50")

    def _calculate_var95(self, positions: list, market_data: dict) -> Decimal:
        """Calculate Value at Risk 95%."""
        # Simplified VaR calculation
        total_value = self._calculate_market_value(positions, market_data)
        return total_value * Decimal("0.02")  # 2% VaR

    def _calculate_beta(self, positions: list, market_data: dict) -> Decimal:
        """Calculate portfolio beta."""
        # Simplified beta calculation
        return Decimal("1.15")

    def _calculate_sharpe_ratio(self, total_pnl: Decimal, total_value: Decimal) -> Decimal:
        """Calculate Sharpe ratio."""
        if total_value == 0:
            return Decimal("0")
        return_rate = total_pnl / total_value
        # Simplified Sharpe ratio (assuming risk-free rate of 2%)
        return (return_rate - Decimal("0.02")) / Decimal("0.15")

    def _calculate_max_drawdown(self, portfolio: Portfolio) -> Decimal:
        """Calculate maximum drawdown."""
        # Simplified max drawdown calculation
        return Decimal("0.05")  # 5% max drawdown
