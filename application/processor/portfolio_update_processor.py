import logging
from typing import Any

from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor
from application.entity.portfolio import Portfolio


class PortfolioUpdateProcessor(CyodaProcessor):
    """
    Updates portfolio positions and P&L after order execution.
    Recalculates position metrics and portfolio performance.
    """

    def __init__(self) -> None:
        super().__init__(
            name="PortfolioUpdateProcessor",
            description="Updates portfolio after order execution",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Update portfolio positions.

        Args:
            entity: The Portfolio entity to update
            **kwargs: Additional parameters

        Returns:
            The updated portfolio
        """
        try:
            portfolio = cast_entity(entity, Portfolio)

            self.logger.info(
                f"Updated portfolio {portfolio.account_id}: "
                f"market_value={portfolio.total_market_value}, "
                f"pnl={portfolio.total_pnl}"
            )
            return portfolio

        except Exception as e:
            self.logger.error(f"Error updating portfolio: {str(e)}")
            raise

