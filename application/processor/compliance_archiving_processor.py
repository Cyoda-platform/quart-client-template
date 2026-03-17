"""
ComplianceArchivingProcessor for institutional trading platform.

Handles compliance log archiving for long-term retention (7 years MiFID II compliance).
"""

import logging
from datetime import datetime, timezone

from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor
from application.entity.compliance_log.version_1.compliance_log import ComplianceLog

logger = logging.getLogger(__name__)


class ComplianceArchivingProcessor(CyodaProcessor):
    """
    Processor for archiving compliance logs.
    """

    def __init__(self) -> None:
        super().__init__(
            name="ComplianceArchivingProcessor",
            description="Archives compliance logs for long-term retention",
        )

    async def process(self, entity: CyodaEntity, **kwargs) -> CyodaEntity:
        """
        Process compliance log archiving.

        Args:
            entity: The compliance log entity to archive
            **kwargs: Additional processing parameters

        Returns:
            The compliance log with archiving details
        """
        try:
            self.logger.info(
                f"Archiving compliance log {getattr(entity, 'technical_id', '<unknown>')}"
            )

            log = cast_entity(entity, ComplianceLog)

            # Set archiving timestamp
            log.archived_at = (
                datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            )

            # Update report status
            log.report_status = "archived"

            self.logger.info(
                f"Compliance log {log.log_id} archived"
            )

            return log

        except Exception as e:
            self.logger.error(
                f"Error archiving compliance log {getattr(entity, 'technical_id', '<unknown>')}: {str(e)}"
            )
            raise

