"""
ReconcileFillProcessor for trading platform.

Handles reconciliation of Fill entities against their corresponding Order entities
to validate execution details and ensure data consistency.
"""

import logging
from typing import Any

from application.entity.fill.version_1.fill import Fill
from application.entity.order.version_1.order import Order
from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor
from services.services import get_entity_service


class ReconcileFillProcessor(CyodaProcessor):
    """
    Processor for Fill that validates fills against their orders.

    Retrieves the related Order entity and validates that the fill details
    match the order specifications for reconciliation purposes.
    """

    def __init__(self) -> None:
        super().__init__(
            name="ReconcileFillProcessor",
            description="Reconciles Fill entities against their corresponding Orders",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Process the Fill entity and validate against its Order.

        Args:
            entity: The Fill entity to process
            **kwargs: Additional processing parameters

        Returns:
            The processed and validated Fill entity
        """
        try:
            self.logger.info(
                f"Processing Fill {getattr(entity, 'technical_id', '<unknown>')}"
            )

            # Cast the entity to Fill for type-safe operations
            fill = cast_entity(entity, Fill)

            # Get entity service to retrieve the related order
            entity_service = get_entity_service()

            # Retrieve the related Order entity
            try:
                order_response = await entity_service.get(
                    entity_id=fill.order_id,
                    entity_class=Order.ENTITY_NAME,
                    entity_version=str(Order.ENTITY_VERSION),
                )

                # Extract order data from response
                order_data = order_response.entity
                order = Order(**order_data)

                # Validate fill against order
                self._validate_fill_against_order(fill, order)

                # Mark fill as reconciled
                fill.reconciled = True
                fill.reconciliation_status = "VALID"

                self.logger.info(
                    f"Fill {fill.technical_id} reconciled successfully against "
                    f"Order {fill.order_id}"
                )

            except Exception as e:
                self.logger.error(
                    f"Failed to retrieve or validate Order {fill.order_id} for "
                    f"Fill {fill.technical_id}: {str(e)}"
                )
                fill.reconciled = False
                fill.reconciliation_status = "FAILED"
                fill.reconciliation_error = str(e)

            self.logger.info(f"Fill {fill.technical_id} processed successfully")

            return fill

        except Exception as e:
            self.logger.error(
                f"Error processing Fill {getattr(entity, 'technical_id', '<unknown>')}: {str(e)}"
            )
            raise

    def _validate_fill_against_order(self, fill: Fill, order: Order) -> None:
        """
        Validate fill details against the order specifications.

        Args:
            fill: The Fill entity to validate
            order: The related Order entity

        Raises:
            ValueError: If validation fails
        """
        # Validate instrument_id matches
        if fill.instrument_id != order.instrument_id:
            raise ValueError(
                f"Fill instrument_id {fill.instrument_id} does not match "
                f"Order instrument_id {order.instrument_id}"
            )

        # Validate quantity does not exceed remaining order quantity
        remaining_qty = order.quantity - (order.filled_quantity or 0.0)
        if fill.quantity > remaining_qty:
            self.logger.warning(
                f"Fill quantity {fill.quantity} exceeds remaining order quantity "
                f"{remaining_qty} for Order {order.technical_id}"
            )

        # Validate price for LIMIT orders
        if order.order_type == "LIMIT" and order.price is not None:
            if order.side == "BUY" and fill.fill_price > order.price:
                raise ValueError(
                    f"Fill price {fill.fill_price} exceeds limit price {order.price} "
                    f"for BUY order"
                )
            elif order.side == "SELL" and fill.fill_price < order.price:
                raise ValueError(
                    f"Fill price {fill.fill_price} below limit price {order.price} "
                    f"for SELL order"
                )

        self.logger.info(
            f"Fill {fill.technical_id} validated successfully against "
            f"Order {order.technical_id}"
        )
