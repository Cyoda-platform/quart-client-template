"""
ComplianceReportingProcessor for institutional trading platform.

Handles compliance log reporting and audit trail management.
"""

from typing import Any

import logging
from datetime import datetime, timezone

from application.entity.compliance_log.version_1.compliance_log import ComplianceLog
from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor

logger = logging.getLogger(__name__)


class ComplianceReportingProcessor(CyodaProcessor):
    """
    Processor for reporting compliance logs.
    """

    def __init__(self) -> None:
        super().__init__(
            name="ComplianceReportingProcessor",
            description="Reports compliance logs to regulatory authorities",
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Process compliance reporting.

        Args:
            entity: The compliance log entity to report
            **kwargs: Additional processing parameters

        Returns:
            The compliance log with reporting details
        """
        try:
            self.logger.info(
                f"Reporting compliance log {getattr(entity, 'technical_id', '<unknown>')}"
            )

            log = cast_entity(entity, ComplianceLog)

            # Set reporting timestamp
            log.reported_at = (
                datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            )

            # Update report status
            log.report_status = "reported"

            self.logger.info(f"Compliance log {log.log_id} reported: {log.event_type}")

            return log

        except Exception as e:
            self.logger.error(
                f"Error reporting compliance log {getattr(entity, 'technical_id', '<unknown>')}: {str(e)}"
            )
            raise
