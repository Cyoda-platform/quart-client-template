"""
RiskCheckCriterion for institutional trading platform.

Determines if risk checks should be performed.
"""

from typing import Any

from application.entity.risk_profile import RiskProfile
from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaCriteriaChecker, CyodaEntity


class RiskCheckCriterion(CyodaCriteriaChecker):
    """
    Determines if risk checks should be performed on a RiskProfile.
    """

    def __init__(self) -> None:
        super().__init__(
            name="RiskCheckCriterion",
            description="Determines if risk checks should be performed",
        )

    async def check(self, entity: CyodaEntity, **kwargs: Any) -> bool:
        """
        Check if risk checks should be performed.

        Args:
            entity: The RiskProfile entity

        Returns:
            True if checks should be performed, False otherwise
        """
        try:
            risk_profile = cast_entity(entity, RiskProfile)

            # Perform checks if profile is active
            if not risk_profile.account_id:
                return False

            # Check if limits are defined
            if risk_profile.max_daily_loss <= 0:
                return False

            return True

        except Exception:
            return False
