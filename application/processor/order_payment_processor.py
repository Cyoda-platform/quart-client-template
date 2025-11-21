"""
OrderPaymentProcessor for Cyoda Client Application

Handles async payment processing for Order entities during the create transition.
Simulates payment gateway integration and updates order with payment status.
"""

import asyncio
import logging
import uuid
from typing import Any

from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor
from application.entity.order.version_1.order import Order


class OrderPaymentProcessor(CyodaProcessor):
    """
    Processor for Order payment processing that handles async payment gateway integration
    and updates the order with payment status and transaction details.
    """

    def __init__(self) -> None:
        super().__init__(
            name="OrderPaymentProcessor",
            description="Processes Order payment through async payment gateway integration",
        )
        # Ensure logger attribute is present for type-checkers/readers
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Process payment for the Order entity.

        Args:
            entity: The Order entity to process payment for
            **kwargs: Additional processing parameters

        Returns:
            The order entity with updated payment status and transaction details
        """
        try:
            self.logger.info(
                f"Processing payment for Order {getattr(entity, 'technical_id', '<unknown>')}"
            )

            # Cast the entity to Order for type-safe operations
            order = cast_entity(entity, Order)

            # Validate order is ready for payment processing
            if not self._is_payment_ready(order):
                raise ValueError(f"Order {order.technical_id} is not ready for payment processing")

            # Process payment asynchronously
            payment_result = await self._process_payment_async(order)

            # Update order with payment details
            order.payment_status = payment_result["status"]
            order.payment_transaction_id = payment_result["transaction_id"]

            self.logger.info(
                f"Payment processing completed for Order {order.technical_id} with status: {payment_result['status']}"
            )

            return order

        except Exception as e:
            self.logger.error(
                f"Error processing payment for Order {getattr(entity, 'technical_id', '<unknown>')}: {str(e)}"
            )
            # Update order with failed payment status
            if hasattr(entity, 'payment_status'):
                entity.payment_status = "failed"
            raise

    def _is_payment_ready(self, order: Order) -> bool:
        """
        Check if the order is ready for payment processing.

        Args:
            order: The Order entity to check

        Returns:
            True if order is ready for payment, False otherwise
        """
        # Check required fields are present
        if not order.order_id or not order.items or order.total <= 0:
            self.logger.warning(f"Order {order.technical_id} missing required fields for payment")
            return False

        # Check order is not already processed
        if order.payment_status in ["completed", "processing"]:
            self.logger.warning(f"Order {order.technical_id} already has payment status: {order.payment_status}")
            return False

        return True

    async def _process_payment_async(self, order: Order) -> dict[str, Any]:
        """
        Simulate async payment processing with external payment gateway.

        Args:
            order: The Order entity to process payment for

        Returns:
            Dictionary containing payment result with status and transaction_id
        """
        self.logger.info(f"Initiating async payment processing for Order {order.technical_id}")

        # Simulate async payment gateway call
        await asyncio.sleep(0.1)  # Simulate network delay

        # Generate transaction ID
        transaction_id = f"txn_{uuid.uuid4().hex[:12]}"

        # Simulate payment processing logic
        payment_result = await self._simulate_payment_gateway(order, transaction_id)

        self.logger.info(
            f"Payment gateway response for Order {order.technical_id}: {payment_result['status']}"
        )

        return payment_result

    async def _simulate_payment_gateway(self, order: Order, transaction_id: str) -> dict[str, Any]:
        """
        Simulate payment gateway processing.

        Args:
            order: The Order entity
            transaction_id: Generated transaction ID

        Returns:
            Payment result dictionary
        """
        # Simulate async processing delay
        await asyncio.sleep(0.05)

        # Simulate payment success/failure based on order total
        # For demo purposes: orders over 1000 have 10% failure rate, others succeed
        import random
        
        if order.total > 1000 and random.random() < 0.1:
            # Simulate payment failure
            return {
                "status": "failed",
                "transaction_id": transaction_id,
                "error_code": "INSUFFICIENT_FUNDS",
                "error_message": "Payment declined by issuing bank"
            }
        else:
            # Simulate payment success
            return {
                "status": "completed",
                "transaction_id": transaction_id,
                "gateway_response": "APPROVED",
                "authorization_code": f"auth_{uuid.uuid4().hex[:8]}"
            }

    async def _handle_payment_failure(self, order: Order, error_details: dict[str, Any]) -> None:
        """
        Handle payment failure scenarios.

        Args:
            order: The Order entity
            error_details: Details about the payment failure
        """
        self.logger.warning(
            f"Payment failed for Order {order.technical_id}: {error_details.get('error_message', 'Unknown error')}"
        )

        # Update order with failure details
        order.payment_status = "failed"
        
        # Could trigger additional workflows here like:
        # - Send notification to customer
        # - Create retry payment task
        # - Update inventory if needed
