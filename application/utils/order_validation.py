"""
Order Validation Utilities

Provides validation functions for Order entity payloads used by processors
to ensure data integrity and business rule compliance.
"""

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class OrderValidationError(Exception):
    """Custom exception for Order validation errors."""

    def __init__(self, message: str, field: Optional[str] = None, value: Any = None):
        self.message = message
        self.field = field
        self.value = value
        super().__init__(message)


class OrderValidator:
    """
    Utility class for validating Order entity payloads.

    Provides static methods for validating individual fields and complete order payloads
    according to the functional requirements.
    """

    # Validation constants
    MIN_CUSTOMER_ID_LENGTH = 3
    MAX_CUSTOMER_ID_LENGTH = 100
    MIN_AMOUNT = 0.01
    MAX_AMOUNT = 1000000.0
    MAX_DESCRIPTION_LENGTH = 500
    VALID_STATUSES = ["created", "updated", "cancelled"]

    @staticmethod
    def validate_customer_id(customer_id: Any) -> str:
        """
        Validate customer_id field.

        Args:
            customer_id: The customer ID to validate

        Returns:
            Validated and cleaned customer ID

        Raises:
            OrderValidationError: If validation fails
        """
        if customer_id is None:
            raise OrderValidationError(
                "Customer ID is required", "customer_id", customer_id
            )

        if not isinstance(customer_id, str):
            raise OrderValidationError(
                "Customer ID must be a string", "customer_id", customer_id
            )

        cleaned_id = customer_id.strip()

        if not cleaned_id:
            raise OrderValidationError(
                "Customer ID cannot be empty", "customer_id", customer_id
            )

        if len(cleaned_id) < OrderValidator.MIN_CUSTOMER_ID_LENGTH:
            raise OrderValidationError(
                f"Customer ID must be at least {OrderValidator.MIN_CUSTOMER_ID_LENGTH} characters long",
                "customer_id",
                customer_id,
            )

        if len(cleaned_id) > OrderValidator.MAX_CUSTOMER_ID_LENGTH:
            raise OrderValidationError(
                f"Customer ID must be at most {OrderValidator.MAX_CUSTOMER_ID_LENGTH} characters long",
                "customer_id",
                customer_id,
            )

        return cleaned_id

    @staticmethod
    def validate_amount(amount: Any) -> float:
        """
        Validate amount field.

        Args:
            amount: The amount to validate

        Returns:
            Validated amount rounded to 2 decimal places

        Raises:
            OrderValidationError: If validation fails
        """
        if amount is None:
            raise OrderValidationError("Amount is required", "amount", amount)

        try:
            amount_float = float(amount)
        except (ValueError, TypeError):
            raise OrderValidationError(
                "Amount must be a valid number", "amount", amount
            )

        if amount_float <= 0:
            raise OrderValidationError(
                "Amount must be greater than 0", "amount", amount
            )

        if amount_float < OrderValidator.MIN_AMOUNT:
            raise OrderValidationError(
                f"Amount must be at least {OrderValidator.MIN_AMOUNT}", "amount", amount
            )

        if amount_float > OrderValidator.MAX_AMOUNT:
            raise OrderValidationError(
                f"Amount must be at most {OrderValidator.MAX_AMOUNT}", "amount", amount
            )

        return round(amount_float, 2)

    @staticmethod
    def validate_description(description: Any) -> Optional[str]:
        """
        Validate description field.

        Args:
            description: The description to validate

        Returns:
            Validated and cleaned description or None

        Raises:
            OrderValidationError: If validation fails
        """
        if description is None:
            return None

        if not isinstance(description, str):
            raise OrderValidationError(
                "Description must be a string", "description", description
            )

        cleaned_description = description.strip()

        if not cleaned_description:
            return None

        if len(cleaned_description) > OrderValidator.MAX_DESCRIPTION_LENGTH:
            raise OrderValidationError(
                f"Description must be at most {OrderValidator.MAX_DESCRIPTION_LENGTH} characters long",
                "description",
                description,
            )

        return cleaned_description

    @staticmethod
    def validate_status(status: Any) -> Optional[str]:
        """
        Validate status field.

        Args:
            status: The status to validate

        Returns:
            Validated status

        Raises:
            OrderValidationError: If validation fails
        """
        if status is None:
            return None

        if not isinstance(status, str):
            raise OrderValidationError("Status must be a string", "status", status)

        if status not in OrderValidator.VALID_STATUSES:
            raise OrderValidationError(
                f"Status must be one of: {OrderValidator.VALID_STATUSES}",
                "status",
                status,
            )

        return status

    @staticmethod
    def validate_order_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate complete order payload.

        Args:
            payload: Dictionary containing order data

        Returns:
            Validated and cleaned order payload

        Raises:
            OrderValidationError: If validation fails
        """
        if not isinstance(payload, dict):
            raise OrderValidationError("Order payload must be a dictionary")

        validated_payload: Dict[str, Any] = {}
        errors = []

        # Validate required fields
        try:
            customer_id = OrderValidator.validate_customer_id(
                payload.get("customer_id")
            )
            validated_payload["customer_id"] = customer_id
        except OrderValidationError as e:
            errors.append(e.message)

        try:
            amount = OrderValidator.validate_amount(payload.get("amount"))
            validated_payload["amount"] = amount
        except OrderValidationError as e:
            errors.append(e.message)

        # Validate optional fields
        try:
            description = OrderValidator.validate_description(
                payload.get("description")
            )
            if description is not None:
                validated_payload["description"] = description
        except OrderValidationError as e:
            errors.append(e.message)

        try:
            status = OrderValidator.validate_status(payload.get("status"))
            if status is not None:
                validated_payload["status"] = status
        except OrderValidationError as e:
            errors.append(e.message)

        # If there are validation errors, raise a combined error
        if errors:
            raise OrderValidationError(f"Validation failed: {'; '.join(errors)}")

        # Copy other fields that don't need validation
        for key, value in payload.items():
            if key not in validated_payload:
                validated_payload[key] = value

        return validated_payload

    @staticmethod
    def validate_order_update_payload(
        payload: Dict[str, Any], current_status: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Validate order update payload with additional business rules.

        Args:
            payload: Dictionary containing order update data
            current_status: Current status of the order being updated

        Returns:
            Validated and cleaned order update payload

        Raises:
            OrderValidationError: If validation fails
        """
        validated_payload = OrderValidator.validate_order_payload(payload)

        # Additional validation for updates
        if current_status == "cancelled":
            raise OrderValidationError("Cannot update a cancelled order")

        return validated_payload

    @staticmethod
    def validate_order_cancellation(current_status: Optional[str] = None) -> bool:
        """
        Validate if an order can be cancelled based on its current status.

        Args:
            current_status: Current status of the order

        Returns:
            True if order can be cancelled

        Raises:
            OrderValidationError: If order cannot be cancelled
        """
        if current_status == "cancelled":
            raise OrderValidationError("Order is already cancelled")

        if current_status not in ["created", "updated", None]:
            raise OrderValidationError(
                f"Cannot cancel order with status: {current_status}"
            )

        return True


def validate_order_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convenience function for validating order payloads.

    Args:
        payload: Dictionary containing order data

    Returns:
        Validated and cleaned order payload

    Raises:
        OrderValidationError: If validation fails
    """
    return OrderValidator.validate_order_payload(payload)


def validate_order_for_update(
    payload: Dict[str, Any], current_status: Optional[str] = None
) -> Dict[str, Any]:
    """
    Convenience function for validating order update payloads.

    Args:
        payload: Dictionary containing order update data
        current_status: Current status of the order being updated

    Returns:
        Validated and cleaned order update payload

    Raises:
        OrderValidationError: If validation fails
    """
    return OrderValidator.validate_order_update_payload(payload, current_status)


def validate_order_for_cancellation(current_status: Optional[str] = None) -> bool:
    """
    Convenience function for validating order cancellation.

    Args:
        current_status: Current status of the order

    Returns:
        True if order can be cancelled

    Raises:
        OrderValidationError: If order cannot be cancelled
    """
    return OrderValidator.validate_order_cancellation(current_status)
