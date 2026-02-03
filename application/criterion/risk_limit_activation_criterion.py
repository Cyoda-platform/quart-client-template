"""
RiskLimitActivationCriterion for risk limit activation.

Validates risk limits are ready for activation.
"""

import logging
from typing import Any

from application.entity.risk_limit.version_1.risk_limit import RiskLimit
from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaCriteriaChecker, CyodaEntity


class RiskLimitActivationCriterion(CyodaCriteriaChecker):
    """Validates risk limits are ready for activation."""

    def __init__(self) -> None:
        super().__init__(
            name="RiskLimitActivationCriterion",
            description="Validates risk limit configuration",
        )
        self.logger = logging.getLogger(__name__)

    async def check(self, entity: CyodaEntity, **kwargs: Any) -> bool:
        """
        Check if risk limit is ready for activation.

        Args:
            entity: The risk limit entity to validate
            **kwargs: Additional criteria parameters

        Returns:
            True if risk limit can be activated, False otherwise
        """
        try:
            self.logger.info(
                f"Validating risk limit {getattr(entity, 'technical_id', '<unknown>')}"
            )

            limit = cast_entity(entity, RiskLimit)

            # Validate required fields
            if not limit.account_id or not limit.limit_type:
                self.logger.warning(
                    f"Risk limit {limit.technical_id} missing required fields"
                )
                return False

            # Validate limit value
            if limit.limit_value <= 0:
                self.logger.warning(
                    f"Risk limit {limit.technical_id} invalid limit value"
                )
                return False

            # Validate current usage
            if limit.current_usage > limit.limit_value:
                self.logger.warning(
                    f"Risk limit {limit.technical_id} usage exceeds limit"
                )
                return False

            # Validate limit type
            if limit.limit_type not in limit.LIMIT_TYPES:
                self.logger.warning(
                    f"Risk limit {limit.technical_id} invalid limit type"
                )
                return False

            self.logger.info(f"Risk limit {limit.technical_id} ready for activation")
            return True

        except Exception as e:
            self.logger.error(f"Error validating risk limit: {str(e)}")
            return False
