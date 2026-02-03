"""
ExecutionConfirmationCriterion for execution confirmation.

Confirms execution reports are ready for settlement.
"""

import logging
from typing import Any

from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaCriteriaChecker, CyodaEntity
from application.entity.execution_report.version_1.execution_report import ExecutionReport


class ExecutionConfirmationCriterion(CyodaCriteriaChecker):
    """Confirms execution reports are ready for settlement."""

    def __init__(self) -> None:
        super().__init__(
            name="ExecutionConfirmationCriterion",
            description="Confirms execution report data",
        )
        self.logger = logging.getLogger(__name__)

    async def check(self, entity: CyodaEntity, **kwargs: Any) -> bool:
        """
        Check if execution report is ready for settlement.

        Args:
            entity: The execution report entity to validate
            **kwargs: Additional criteria parameters

        Returns:
            True if execution is confirmed, False otherwise
        """
        try:
            self.logger.info(f"Confirming execution {getattr(entity, 'technical_id', '<unknown>')}")

            report = cast_entity(entity, ExecutionReport)

            # Validate required fields
            if not report.order_id or not report.account_id:
                self.logger.warning(f"Execution {report.technical_id} missing required fields")
                return False

            # Validate execution data
            if report.fill_quantity <= 0 or report.fill_price < 0:
                self.logger.warning(f"Execution {report.technical_id} invalid fill data")
                return False

            # Validate venue
            if not report.venue:
                self.logger.warning(f"Execution {report.technical_id} missing venue")
                return False

            self.logger.info(f"Execution {report.technical_id} confirmed")
            return True

        except Exception as e:
            self.logger.error(f"Error confirming execution: {str(e)}")
            return False

