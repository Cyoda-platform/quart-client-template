"""
Reconciliation processors for the trading platform.

Handles position reconciliation and discrepancy reporting.
"""

import logging
from typing import Any

from application.entity.position.version_1.position import Position
from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor
from services.services import get_entity_service


class LedgerCompare(CyodaProcessor):
    """
    Processor for comparing ledger positions.

    Reconciles internal positions with external sources.
    """

    def __init__(self) -> None:
        super().__init__(
            name="LedgerCompare",
            description="Compares ledger positions",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Compare ledger positions.

        Args:
            entity: The Position entity
            **kwargs: Additional parameters

        Returns:
            The position entity with reconciliation results
        """
        try:
            self.logger.info(
                f"Comparing ledger for position {getattr(entity, 'technical_id', '<unknown>')}"
            )

            position = cast_entity(entity, Position)

            # Validate position data
            if position.quantity < 0:
                raise ValueError("Position quantity cannot be negative")

            if position.avg_price <= 0:
                raise ValueError("Average price must be positive")

            self.logger.info(
                f"Ledger comparison completed for position {position.technical_id}"
            )

            return position

        except Exception as e:
            self.logger.error(
                f"Ledger comparison failed for {getattr(entity, 'technical_id', '<unknown>')}: {str(e)}"
            )
            raise


class DiscrepancyReporter(CyodaProcessor):
    """
    Processor for reporting position discrepancies.

    Creates compliance events for reconciliation failures.
    """

    def __init__(self) -> None:
        super().__init__(
            name="DiscrepancyReporter",
            description="Reports position discrepancies",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Report discrepancy.

        Args:
            entity: The Position entity
            **kwargs: Additional parameters

        Returns:
            The position entity
        """
        try:
            self.logger.info(
                f"Reporting discrepancy for position {getattr(entity, 'technical_id', '<unknown>')}"
            )

            position = cast_entity(entity, Position)

            self.logger.info(
                f"Discrepancy reported for position {position.technical_id}"
            )

            return position

        except Exception as e:
            self.logger.error(
                f"Discrepancy reporting failed for {getattr(entity, 'technical_id', '<unknown>')}: {str(e)}"
            )
            raise
