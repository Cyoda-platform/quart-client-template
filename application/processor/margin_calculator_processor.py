"""
MarginCalculator processor for institutional trading platform.

Calculates margin requirements for positions and accounts.
"""

import logging
from typing import Any

from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor
from application.entity.account import Account


class MarginCalculator(CyodaProcessor):
    """
    Calculates margin requirements for accounts.
    """

    def __init__(self) -> None:
        super().__init__(
            name="MarginCalculator",
            description="Calculates margin requirements",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Calculate margin requirements for the account.

        Args:
            entity: The Account entity

        Returns:
            The account with updated margin calculations
        """
        try:
            self.logger.info(
                f"Calculating margin for account {getattr(entity, 'technical_id', '<unknown>')}"
            )

            account = cast_entity(entity, Account)

            # Calculate margin based on positions and leverage
            margin_required = self._calculate_margin_requirement(account)
            account.margin_balance = max(0, account.cash_balance - margin_required)

            self.logger.info(
                f"Account {account.technical_id} margin calculated: {account.margin_balance}"
            )

            return account

        except Exception as e:
            self.logger.error(
                f"Error calculating margin for {getattr(entity, 'technical_id', '<unknown>')}: {str(e)}"
            )
            raise

    def _calculate_margin_requirement(self, account: Account) -> float:
        """
        Calculate margin requirement for the account.

        Args:
            account: The account

        Returns:
            The margin requirement amount
        """
        # Simplified margin calculation
        # In production, this would consider all positions
        return account.total_equity * 0.3 if account.total_equity else 0.0

