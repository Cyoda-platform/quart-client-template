"""
OrderValidationCriterion for Cyoda Client Application

Validates that an Order meets all required business rules for create and update operations.
Handles validation of required fields (orderId, items, total) and updatable fields validation.
"""

from decimal import Decimal
from typing import Any

from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaCriteriaChecker, CyodaEntity
from application.entity.order.version_1.order import Order


class OrderValidationCriterion(CyodaCriteriaChecker):
    """
    Validation criterion for Order entity that checks business rules
    for both create and update operations.
    """

    def __init__(self) -> None:
        super().__init__(
            name="OrderValidationCriterion",
            description="Validates Order business rules and data consistency for create and update operations",
        )

    async def check(self, entity: CyodaEntity, **kwargs: Any) -> bool:
        """
        Check if the order meets all validation criteria.

        Args:
            entity: The CyodaEntity to validate (expected to be Order)
            **kwargs: Additional criteria parameters (may include operation_type)

        Returns:
            True if the entity meets all criteria, False otherwise
        """
        try:
            self.logger.info(
                f"Validating Order entity {getattr(entity, 'technical_id', '<unknown>')}"
            )

            # Cast the entity to Order for type-safe operations
            order = cast_entity(entity, Order)

            # Get operation type from kwargs to determine validation scope
            operation_type = kwargs.get("operation_type", "create")

            if operation_type == "create":
                return await self._validate_create_fields(order)
            elif operation_type == "update":
                return await self._validate_update_fields(order)
            elif operation_type == "cancel":
                return await self._validate_cancel_fields(order)
            else:
                self.logger.warning(f"Unknown operation type: {operation_type}")
                return False

        except Exception as e:
            self.logger.error(
                f"Error validating Order entity {getattr(entity, 'technical_id', '<unknown>')}: {str(e)}"
            )
            return False

    async def _validate_create_fields(self, order: Order) -> bool:
        """
        Validate required fields for order creation: orderId, items, total.

        Args:
            order: The Order entity to validate

        Returns:
            True if all required fields are valid, False otherwise
        """
        # Validate order_id
        if not order.order_id or len(order.order_id.strip()) == 0:
            self.logger.warning(
                f"Order {order.technical_id} has invalid order_id: '{order.order_id}'"
            )
            return False

        # Validate items
        if not order.items or len(order.items) == 0:
            self.logger.warning(
                f"Order {order.technical_id} has no items"
            )
            return False

        # Validate each item
        for i, item in enumerate(order.items):
            if not item.item_id or len(item.item_id.strip()) == 0:
                self.logger.warning(
                    f"Order {order.technical_id} item {i} has invalid item_id"
                )
                return False

            if not item.name or len(item.name.strip()) == 0:
                self.logger.warning(
                    f"Order {order.technical_id} item {i} has invalid name"
                )
                return False

            if item.quantity <= 0:
                self.logger.warning(
                    f"Order {order.technical_id} item {i} has invalid quantity: {item.quantity}"
                )
                return False

            if item.unit_price <= 0:
                self.logger.warning(
                    f"Order {order.technical_id} item {i} has invalid unit_price: {item.unit_price}"
                )
                return False

            # Validate total_price calculation
            expected_total = Decimal(str(item.quantity)) * item.unit_price
            if item.total_price != expected_total:
                self.logger.warning(
                    f"Order {order.technical_id} item {i} total_price {item.total_price} does not match quantity * unit_price {expected_total}"
                )
                return False

        # Validate total
        if order.total <= 0:
            self.logger.warning(
                f"Order {order.technical_id} has invalid total: {order.total}"
            )
            return False

        # Validate total matches sum of item totals
        items_total = sum(item.total_price for item in order.items)
        if order.total != items_total:
            self.logger.warning(
                f"Order {order.technical_id} total {order.total} does not match sum of item totals {items_total}"
            )
            return False

        self.logger.info(
            f"Order {order.technical_id} passed all create validation criteria"
        )
        return True

    async def _validate_update_fields(self, order: Order) -> bool:
        """
        Validate updatable fields for order update: items, total.
        Order ID should not be changed during updates.

        Args:
            order: The Order entity to validate

        Returns:
            True if all updatable fields are valid, False otherwise
        """
        # For updates, we validate the same fields as create except order_id immutability
        # The order_id should already exist and be valid from creation

        # Validate items (same as create)
        if not order.items or len(order.items) == 0:
            self.logger.warning(
                f"Order {order.technical_id} update has no items"
            )
            return False

        # Validate each item (same validation as create)
        for i, item in enumerate(order.items):
            if not item.item_id or len(item.item_id.strip()) == 0:
                self.logger.warning(
                    f"Order {order.technical_id} update item {i} has invalid item_id"
                )
                return False

            if not item.name or len(item.name.strip()) == 0:
                self.logger.warning(
                    f"Order {order.technical_id} update item {i} has invalid name"
                )
                return False

            if item.quantity <= 0:
                self.logger.warning(
                    f"Order {order.technical_id} update item {i} has invalid quantity: {item.quantity}"
                )
                return False

            if item.unit_price <= 0:
                self.logger.warning(
                    f"Order {order.technical_id} update item {i} has invalid unit_price: {item.unit_price}"
                )
                return False

            # Validate total_price calculation
            expected_total = Decimal(str(item.quantity)) * item.unit_price
            if item.total_price != expected_total:
                self.logger.warning(
                    f"Order {order.technical_id} update item {i} total_price {item.total_price} does not match quantity * unit_price {expected_total}"
                )
                return False

        # Validate total (same as create)
        if order.total <= 0:
            self.logger.warning(
                f"Order {order.technical_id} update has invalid total: {order.total}"
            )
            return False

        # Validate total matches sum of item totals
        items_total = sum(item.total_price for item in order.items)
        if order.total != items_total:
            self.logger.warning(
                f"Order {order.technical_id} update total {order.total} does not match sum of item totals {items_total}"
            )
            return False

        self.logger.info(
            f"Order {order.technical_id} passed all update validation criteria"
        )
        return True

    async def _validate_cancel_fields(self, order: Order) -> bool:
        """
        Validate fields required for order cancellation: cancel_reason must be provided.

        Args:
            order: The Order entity to validate

        Returns:
            True if cancel_reason is valid, False otherwise
        """
        # Validate cancel_reason is provided and non-empty
        if not order.cancel_reason or len(order.cancel_reason.strip()) == 0:
            self.logger.warning(
                f"Order {order.technical_id} cancellation requires a cancel_reason"
            )
            return False

        if len(order.cancel_reason) > 500:
            self.logger.warning(
                f"Order {order.technical_id} cancel_reason is too long (max 500 characters)"
            )
            return False

        # Check if order is in a cancellable state
        if not order.is_cancellable():
            self.logger.warning(
                f"Order {order.technical_id} is not in a cancellable state: {order.meta.state}"
            )
            return False

        self.logger.info(
            f"Order {order.technical_id} passed all cancel validation criteria"
        )
        return True
