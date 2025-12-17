from typing import Any

from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaCriteriaChecker, CyodaEntity
from application.entity.order.version_1.order import Order


class RiskCheckCriterion(CyodaCriteriaChecker):
    """
    Risk check criterion for Order that validates risk controls.
    """

    def __init__(self) -> None:
        super().__init__(
            name="RiskCheckCriterion",
            description="Validates Order against risk control rules",
        )

    async def check(self, entity: CyodaEntity, **kwargs: Any) -> bool:
        """
        Check if the order passes risk control checks.

        Args:
            entity: The CyodaEntity to validate (expected to be Order)
            **kwargs: Additional criteria parameters

        Returns:
            True if the order passes risk checks, False otherwise
        """
        try:
            self.logger.info(
                f"Performing risk checks on order {getattr(entity, 'technical_id', '<unknown>')}"
            )

            order = cast_entity(entity, Order)

            if order.quantity > 1000000:
                self.logger.warning(
                    f"Order {order.technical_id} exceeds max order size limit"
                )
                return False

            if order.price and order.quantity:
                notional = order.price * order.quantity
                if notional > 10000000:
                    self.logger.warning(
                        f"Order {order.technical_id} exceeds max notional limit: {notional}"
                    )
                    return False

            self.logger.info(
                f"Order {order.technical_id} passed all risk checks"
            )
            return True

        except Exception as e:
            self.logger.error(
                f"Error performing risk checks on order {getattr(entity, 'technical_id', '<unknown>')}: {str(e)}"
            )
            return False

