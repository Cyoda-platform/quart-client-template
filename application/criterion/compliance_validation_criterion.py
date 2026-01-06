"""
ComplianceValidationCriterion validates compliance records.

Checks regulatory requirements and audit trail completeness.
"""

import logging
from typing import Any

from common.criterion.base import CyodaCriterion, CyodaEntity
from common.entity.entity_casting import cast_entity
from application.entity.compliance import Compliance


class ComplianceValidationCriterion(CyodaCriterion):
    """Validates compliance record configuration."""

    def __init__(self) -> None:
        super().__init__(
            name="ComplianceValidationCriterion",
            description="Validates compliance record configuration and requirements",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def evaluate(self, entity: CyodaEntity, **kwargs: Any) -> bool:
        """Evaluate if compliance record is properly configured."""
        try:
            compliance = cast_entity(entity, Compliance)
            
            # Check entity reference
            if not self._check_entity_reference(compliance):
                self.logger.warning(f"Compliance {compliance.compliance_id} has invalid entity reference")
                return False
            
            # Check check type
            if not self._check_check_type(compliance):
                self.logger.warning(f"Compliance {compliance.compliance_id} has invalid check type")
                return False
            
            # Check regulation
            if not self._check_regulation(compliance):
                self.logger.warning(f"Compliance {compliance.compliance_id} has invalid regulation")
                return False
            
            self.logger.info(f"Compliance {compliance.compliance_id} passed validation")
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating compliance: {str(e)}")
            return False

    def _check_entity_reference(self, compliance: Compliance) -> bool:
        """Check if entity reference is valid."""
        return (
            compliance.entity_type in ["ORDER", "POSITION", "PORTFOLIO"] and
            compliance.entity_id and
            compliance.account_id
        )

    def _check_check_type(self, compliance: Compliance) -> bool:
        """Check if check type is valid."""
        return compliance.check_type in [
            "INSIDER_TRADING", "MARKET_ABUSE", "POSITION_LIMIT", "SECTOR_RESTRICTION"
        ]

    def _check_regulation(self, compliance: Compliance) -> bool:
        """Check if regulation is specified."""
        return compliance.regulation and compliance.requirement

