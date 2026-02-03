"""
AccountActivationProcessor for account activation.

Activates trading accounts and initializes account parameters.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor
from application.entity.account.version_1.account import Account


class AccountActivationProcessor(CyodaProcessor):
    """Activates trading accounts."""

    def __init__(self) -> None:
        super().__init__(name="AccountActivationProcessor")
        self.logger = logging.getLogger(__name__)

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Activate account.

        Args:
            entity: The account entity to process
            **kwargs: Additional processing parameters

        Returns:
            The processed account entity
        """
        try:
            self.logger.info(f"Activating account {getattr(entity, 'technical_id', '<unknown>')}")

            account = cast_entity(entity, Account)

            # Validate account data
            if account.cash_balance < 0:
                raise ValueError("Cash balance cannot be negative")

            if account.total_equity <= 0:
                raise ValueError("Total equity must be positive")

            account.is_active = True
            account.updated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

            self.logger.info(f"Account {account.technical_id} activated")
            return account

        except Exception as e:
            self.logger.error(f"Error activating account: {str(e)}")
            raise

