"""
InteractionEventValidationCriterion for validating interaction events.

Validates that an Interaction entity has required fields (subscriber_id,
email_send_id) before recording the interaction.
"""

from typing import Any

from application.entity.interaction.version_1.interaction import Interaction
from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaCriteriaChecker, CyodaEntity


class InteractionEventValidationCriterion(CyodaCriteriaChecker):
    """
    Validation criterion for Interaction entities.
    """

    def __init__(self) -> None:
        super().__init__(
            name="InteractionEventValidationCriterion",
            description="Validates Interaction event data",
        )

    async def check(self, entity: CyodaEntity, **kwargs: Any) -> bool:
        """
        Check if the Interaction entity is valid.

        Args:
            entity: The CyodaEntity to validate (expected to be Interaction)
            **kwargs: Additional criteria parameters

        Returns:
            True if the entity is valid, False otherwise
        """
        try:
            self.logger.info(
                f"Validating entity {getattr(entity, 'technical_id', '<unknown>')}"
            )

            interaction = cast_entity(entity, Interaction)

            # Validate required fields
            if not interaction.subscriber_id:
                self.logger.warning(
                    f"Entity {interaction.technical_id} has no subscriber_id"
                )
                return False

            if not interaction.email_send_id:
                self.logger.warning(
                    f"Entity {interaction.technical_id} has no email_send_id"
                )
                return False

            self.logger.info(f"Entity {interaction.technical_id} validation passed")
            return True

        except Exception as e:
            self.logger.error(f"Validation error: {str(e)}")
            return False
