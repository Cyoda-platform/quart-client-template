"""
OrderValidator processor for institutional trading platform.

Validates incoming orders against schema, required fields, and basic business rules.
Used on order_processing.transition 'validate' (SYNC).
"""

import logging
from typing import Any

from common.processor.base import CyodaEntity, CyodaProcessor


class OrderValidator(CyodaProcessor):
    """
    Validates incoming orders for schema compliance, required fields, and business rules.
    """

    def __init__(self) -> None:
        super().__init__(
            name="OrderValidator",
            description="Validates incoming orders against schema and business rules",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Validate the order entity.

        Args:
            entity: The order entity to validate
            **kwargs: Additional validation parameters

        Returns:
            The validated order entity

        Raises:
            ValueError: If validation fails
        """
        try:
            self.logger.info(
                f"Validating order {getattr(entity, 'technical_id', '<unknown>')}"
            )

            order_id = getattr(entity, "technical_id", None)

            # Validate required fields
            self._validate_required_fields(entity)

            # Validate field types and ranges
            self._validate_field_types(entity)

            # Validate business rules
            self._validate_business_rules(entity)

            self.logger.info(f"Order {order_id} validation passed")
            return entity

        except ValueError as e:
            self.logger.error(f"Order validation failed: {str(e)}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error validating order: {str(e)}")
            raise

    def _validate_required_fields(self, entity: CyodaEntity) -> None:
        """
        Validate that all required fields are present.

        Args:
            entity: The order entity to validate

        Raises:
            ValueError: If required fields are missing
        """
        required_fields = [
            "accountId",
            "instrumentId",
            "side",
            "orderType",
            "quantity",
        ]

        for field in required_fields:
            if not hasattr(entity, field) or getattr(entity, field) is None:
                raise ValueError(f"Required field missing: {field}")

    def _validate_field_types(self, entity: CyodaEntity) -> None:
        """
        Validate field types and value ranges.

        Args:
            entity: The order entity to validate

        Raises:
            ValueError: If field types or ranges are invalid
        """
        # Validate side
        side = getattr(entity, "side", None)
        if side not in ["BUY", "SELL"]:
            raise ValueError(f"Invalid side: {side}. Must be BUY or SELL")

        # Validate orderType
        order_type = getattr(entity, "orderType", None)
        valid_types = ["MARKET", "LIMIT", "STOP", "STOP_LIMIT", "IOC", "FOK"]
        if order_type not in valid_types:
            raise ValueError(f"Invalid orderType: {order_type}")

        # Validate quantity
        quantity = getattr(entity, "quantity", None)
        if not isinstance(quantity, (int, float)) or quantity <= 0:
            raise ValueError(f"Invalid quantity: {quantity}. Must be positive")

        # Validate price if LIMIT order
        if order_type == "LIMIT":
            price = getattr(entity, "price", None)
            if price is None or not isinstance(price, (int, float)) or price <= 0:
                raise ValueError(f"Invalid price for LIMIT order: {price}")

    def _validate_business_rules(self, entity: CyodaEntity) -> None:
        """
        Validate business rules specific to the trading platform.

        Args:
            entity: The order entity to validate

        Raises:
            ValueError: If business rules are violated
        """
        # TODO: Integrate with risk limits service
        # - Check account daily order limit
        # - Check instrument trading hours
        # - Check account status (active, suspended, etc.)

        quantity = getattr(entity, "quantity", None)
        max_order_size = 1000000  # TODO: Load from configuration

        if quantity is not None and quantity > max_order_size:
            raise ValueError(
                f"Order quantity {quantity} exceeds maximum {max_order_size}"
            )

        self.logger.debug("Business rules validation passed")
