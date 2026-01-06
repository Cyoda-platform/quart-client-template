"""
PnlCalculator processor for institutional trading platform.

Continuous mark-to-market and realized/unrealized P&L calculations using market_tick updates.
Used on position_valuation.transition 'calculate' (SYNC).
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict

from common.processor.base import CyodaEntity, CyodaProcessor


class PnlCalculator(CyodaProcessor):
    """
    Calculates mark-to-market and realized/unrealized P&L for positions.
    """

    def __init__(self) -> None:
        super().__init__(
            name="PnlCalculator",
            description="Calculates mark-to-market and P&L metrics",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Calculate P&L metrics for the position.

        Args:
            entity: The position or market_tick entity
            **kwargs: Additional calculation parameters

        Returns:
            The entity with P&L calculations
        """
        try:
            self.logger.info(
                f"Calculating P&L for {getattr(entity, 'technical_id', '<unknown>')}"
            )

            # Calculate P&L metrics
            pnl_metrics = self._calculate_pnl_metrics(entity)

            # Store P&L results
            if not hasattr(entity, "pnlMetadata"):
                setattr(entity, "pnlMetadata", {})
            pnl_metadata = getattr(entity, "pnlMetadata")
            pnl_metadata.update(pnl_metrics)

            self.logger.info(
                f"P&L calculation completed: realized={pnl_metrics.get('realized_pnl')}, "
                f"unrealized={pnl_metrics.get('unrealized_pnl')}"
            )
            return entity

        except Exception as e:
            self.logger.error(f"Error calculating P&L: {str(e)}")
            raise

    def _calculate_pnl_metrics(self, entity: CyodaEntity) -> Dict[str, Any]:
        """
        Calculate comprehensive P&L metrics.

        Args:
            entity: The position or market_tick entity

        Returns:
            Dictionary with P&L metrics
        """
        metrics: Dict[str, Any] = {
            "realized_pnl": 0.0,
            "unrealized_pnl": 0.0,
            "total_pnl": 0.0,
            "pnl_percentage": 0.0,
            "calculated_at": (
                datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            ),
        }

        # Get position data
        quantity = getattr(entity, "quantity", 0)
        avg_price = getattr(entity, "avgPrice", 0)
        realized_pnl = getattr(entity, "realizedPnl", 0)

        # Get market data
        last_price = getattr(entity, "lastPrice", None)
        bid = getattr(entity, "bid", None)
        ask = getattr(entity, "ask", None)

        # Use last_price if available, otherwise use mid-price
        if last_price is not None:
            market_price = last_price
        elif bid is not None and ask is not None:
            market_price = (bid + ask) / 2
        else:
            self.logger.warning("No market price available for P&L calculation")
            return metrics

        # Calculate unrealized P&L
        if quantity != 0 and avg_price > 0:
            unrealized_pnl = quantity * (market_price - avg_price)
            metrics["unrealized_pnl"] = unrealized_pnl

            # Calculate P&L percentage
            total_cost = abs(quantity * avg_price)
            if total_cost > 0:
                metrics["pnl_percentage"] = (unrealized_pnl / total_cost) * 100

        # Use realized P&L from entity
        metrics["realized_pnl"] = realized_pnl

        # Calculate total P&L
        metrics["total_pnl"] = metrics["realized_pnl"] + metrics["unrealized_pnl"]

        return metrics

    def _calculate_portfolio_pnl(
        self, positions: list[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Calculate aggregate P&L across portfolio.

        Args:
            positions: List of position dictionaries

        Returns:
            Portfolio P&L metrics
        """
        # TODO: Integrate with position service to fetch all positions
        # TODO: Aggregate P&L across all positions
        # TODO: Calculate portfolio-level metrics

        portfolio_pnl: Dict[str, Any] = {
            "total_realized_pnl": 0.0,
            "total_unrealized_pnl": 0.0,
            "total_pnl": 0.0,
            "position_count": len(positions),
        }

        for position in positions:
            portfolio_pnl["total_realized_pnl"] += position.get("realizedPnl", 0)
            portfolio_pnl["total_unrealized_pnl"] += position.get("unrealizedPnl", 0)

        portfolio_pnl["total_pnl"] = (
            portfolio_pnl["total_realized_pnl"] + portfolio_pnl["total_unrealized_pnl"]
        )

        return portfolio_pnl
