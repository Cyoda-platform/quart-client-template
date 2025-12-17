from typing import Any

from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaCriteriaChecker, CyodaEntity
from application.entity.order.version_1.order import Order


class OrderValidationCriterion(CyodaCriteriaChecker):
    """
    Validation criterion for Order that checks all business rules.
    """

    def __init__(self) -> None:
        super().__init__(
            name="OrderValidationCriterion",
            description="Validates Order business rules and data consistency",
        )

    async def check(self, entity: CyodaEntity, **kwargs: Any) -> bool:
        """
        Check if the order meets all validation criteria.

        Args:
            entity: The CyodaEntity to validate (expected to be Order)
            **kwargs: Additional criteria parameters

        Returns:
            True if the order meets all criteria, False otherwise
        """
        try:
            self.logger.info(
                f"Validating order {getattr(entity, 'technical_id', '<unknown>')}"
            )

            order = cast_entity(entity, Order)

            if not order.client_id or len(order.client_id.strip()) == 0:
                self.logger.warning(
                    f"Order {order.technical_id} has invalid client_id"
                )
                return False

            if not order.account or len(order.account.strip()) == 0:
                self.logger.warning(
                    f"Order {order.technical_id} has invalid account"
                )
                return False

            if not order.instrument or len(order.instrument.strip()) == 0:
                self.logger.warning(
                    f"Order {order.technical_id} has invalid instrument"
                )
                return False

            if order.quantity <= 0:
                self.logger.warning(
                    f"Order {order.technical_id} has invalid quantity: {order.quantity}"
                )
                return False

            if order.order_type in ["LIMIT", "STOP"] and (
                order.price is None or order.price <= 0
            ):
                self.logger.warning(
                    f"Order {order.technical_id} requires price for {order.order_type} orders"
                )
                return False

            self.logger.info(
                f"Order {order.technical_id} passed all validation criteria"
            )
            return True

        except Exception as e:
            self.logger.error(
                f"Error validating order {getattr(entity, 'technical_id', '<unknown>')}: {str(e)}"
            )
            return False

