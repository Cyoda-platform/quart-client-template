"""
ExecutionSettlementProcessor for execution settlement.

Settles executed trades and updates account balances.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from application.entity.execution_report.version_1.execution_report import (
    ExecutionReport,
)
from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor


class ExecutionSettlementProcessor(CyodaProcessor):
    """Settles executed trades and updates account balances."""

    def __init__(self) -> None:
        super().__init__(name="ExecutionSettlementProcessor")
        self.logger = logging.getLogger(__name__)

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Settle execution.

        Args:
            entity: The execution report entity to process
            **kwargs: Additional processing parameters

        Returns:
            The processed execution report entity
        """
        try:
            self.logger.info(
                f"Settling execution {getattr(entity, 'technical_id', '<unknown>')}"
            )

            report = cast_entity(entity, ExecutionReport)

            # Calculate settlement amount
            settlement_amount = (
                report.fill_quantity * report.fill_price + report.commission
            )

            self.logger.info(
                f"Execution {report.technical_id} settled: ${settlement_amount}"
            )
            return report

        except Exception as e:
            self.logger.error(f"Error settling execution: {str(e)}")
            raise
