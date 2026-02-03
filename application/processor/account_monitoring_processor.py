"""
AccountMonitoringProcessor for account monitoring.

Monitors account health and compliance status.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor
from application.entity.account.version_1.account import Account


class AccountMonitoringProcessor(CyodaProcessor):
    """Monitors account health and compliance."""

    def __init__(self) -> None:
        super().__init__(name="AccountMonitoringProcessor")
        self.logger = logging.getLogger(__name__)

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Monitor account.

        Args:
            entity: The account entity to process
            **kwargs: Additional processing parameters

        Returns:
            The processed account entity
        """
        try:
            self.logger.info(f"Monitoring account {getattr(entity, 'technical_id', '<unknown>')}")

            account = cast_entity(entity, Account)

            # Check margin requirement
            if account.margin_requirement > account.total_equity * 0.5:
                self.logger.warning(f"Account {account.technical_id} margin requirement high")

            # Check buying power
            if account.buying_power < 0:
                self.logger.warning(f"Account {account.technical_id} insufficient buying power")

            account.updated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

            self.logger.info(f"Account {account.technical_id} monitored")
            return account

        except Exception as e:
            self.logger.error(f"Error monitoring account: {str(e)}")
            raise

