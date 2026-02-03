"""
ExecutionReportingProcessor for execution report generation.

Generates and validates execution reports from order fills.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor
from application.entity.execution_report.version_1.execution_report import ExecutionReport


class ExecutionReportingProcessor(CyodaProcessor):
    """Generates execution reports from order fills."""

    def __init__(self) -> None:
        super().__init__(name="ExecutionReportingProcessor")
        self.logger = logging.getLogger(__name__)

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Generate execution report.

        Args:
            entity: The execution report entity to process
            **kwargs: Additional processing parameters

        Returns:
            The processed execution report entity
        """
        try:
            self.logger.info(f"Generating execution report {getattr(entity, 'technical_id', '<unknown>')}")

            report = cast_entity(entity, ExecutionReport)

            # Validate execution data
            if report.fill_quantity <= 0:
                raise ValueError("Fill quantity must be positive")

            if report.fill_price < 0:
                raise ValueError("Fill price cannot be negative")

            self.logger.info(f"Execution report {report.technical_id} generated")
            return report

        except Exception as e:
            self.logger.error(f"Error generating execution report: {str(e)}")
            raise

