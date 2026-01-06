"""
RiskValidationCriterion validates risk control parameters.

Checks limit configuration and threshold consistency.
"""

import logging
from typing import Any

from application.entity.risk_control import RiskControl
from common.criterion.base import CyodaCriterion, CyodaEntity
from common.entity.entity_casting import cast_entity


class RiskValidationCriterion(CyodaCriterion):
    """Validates risk control configuration."""

    def __init__(self) -> None:
        super().__init__(
            name="RiskValidationCriterion",
            description="Validates risk control configuration and thresholds",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def evaluate(self, entity: CyodaEntity, **kwargs: Any) -> bool:
        """Evaluate if risk control is properly configured."""
        try:
            risk_control = cast_entity(entity, RiskControl)

            # Check limit configuration
            if not self._check_limit_config(risk_control):
                self.logger.warning(
                    f"Risk control {risk_control.risk_id} has invalid limit config"
                )
                return False

            # Check threshold consistency
            if not self._check_threshold_consistency(risk_control):
                self.logger.warning(
                    f"Risk control {risk_control.risk_id} has inconsistent thresholds"
                )
                return False

            # Check action configuration
            if not self._check_action_config(risk_control):
                self.logger.warning(
                    f"Risk control {risk_control.risk_id} has invalid action config"
                )
                return False

            self.logger.info(f"Risk control {risk_control.risk_id} passed validation")
            return True

        except Exception as e:
            self.logger.error(f"Error validating risk control: {str(e)}")
            return False

    def _check_limit_config(self, risk_control: RiskControl) -> bool:
        """Check if limit is properly configured."""
        return risk_control.limit_value > 0 and risk_control.risk_type in [
            "POSITION_LIMIT",
            "NOTIONAL_LIMIT",
            "VAR_LIMIT",
            "SECTOR_LIMIT",
        ]

    def _check_threshold_consistency(self, risk_control: RiskControl) -> bool:
        """Check if thresholds are consistent."""
        return (
            0 <= risk_control.warning_threshold <= 100
            and 0 <= risk_control.critical_threshold <= 100
            and risk_control.warning_threshold <= risk_control.critical_threshold
        )

    def _check_action_config(self, risk_control: RiskControl) -> bool:
        """Check if action is properly configured."""
        return risk_control.action_on_breach in ["ALERT", "RESTRICT", "BLOCK"]
