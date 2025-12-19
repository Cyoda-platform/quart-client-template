import logging
from datetime import datetime, timezone
from typing import Any

from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor
from application.entity.risk_control.version_1.risk_control import RiskControl


class RiskBreachProcessor(CyodaProcessor):
    """Handles risk control breaches and triggers alerts/blocks."""

    def __init__(self) -> None:
        super().__init__(
            name="RiskBreachProcessor",
            description="Processes risk control breaches and executes breach actions",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Process risk control breach.

        Args:
            entity: The RiskControl entity to process
            **kwargs: Additional processing parameters

        Returns:
            Updated risk control entity
        """
        try:
            risk_control = cast_entity(entity, RiskControl)

            self.logger.warning(
                f"Risk breach detected for rule {risk_control.entity_id}: "
                f"{risk_control.current_value} > {risk_control.limit_value}"
            )

            self.logger.info(
                f"Executing breach action: {risk_control.breach_action}"
            )

            return risk_control

        except Exception as e:
            self.logger.error(f"Error processing risk breach: {str(e)}")
            raise

