import logging
from typing import Any

from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor
from application.entity.cart import Cart


class RecalculateTotalsProcessor(CyodaProcessor):
    def __init__(self) -> None:
        super().__init__(
            name="RecalculateTotalsProcessor",
            description="Recalculates cart totals based on line items",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        try:
            self.logger.info(
                f"Recalculating totals for cart {getattr(entity, 'technical_id', '<unknown>')}"
            )

            cart = cast_entity(entity, Cart)

            total_items = 0
            grand_total = 0.0

            for line in cart.lines:
                qty = line.get("qty", 0)
                price = line.get("price", 0.0)
                total_items += qty
                grand_total += qty * price

            cart.totalItems = total_items
            cart.grandTotal = grand_total

            self.logger.info(
                f"Cart {cart.technical_id} totals recalculated: items={total_items}, total={grand_total}"
            )

            return cart

        except Exception as e:
            self.logger.error(
                f"Error recalculating totals for cart {getattr(entity, 'technical_id', '<unknown>')}: {str(e)}"
            )
            raise

