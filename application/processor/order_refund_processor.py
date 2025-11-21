"""
OrderRefundProcessor for Cyoda Client Application

Handles async refund processing for Order entities during the cancel transition.
Validates cancel reason is provided and processes refunds for paid orders.
"""

import asyncio
import logging
import uuid
from typing import Any

from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor
from application.entity.order.version_1.order import Order


class OrderRefundProcessor(CyodaProcessor):
    """
    Processor for Order refund processing that handles async refund gateway integration
    and validates cancel reason requirements during order cancellation.
    """

    def __init__(self) -> None:
        super().__init__(
            name="OrderRefundProcessor",
            description="Processes Order refunds through async refund gateway integration and validates cancel reason",
        )
        # Ensure logger attribute is present for type-checkers/readers
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Process refund for the cancelled Order entity.

        Args:
            entity: The Order entity to process refund for
            **kwargs: Additional processing parameters

        Returns:
            The order entity with updated refund status and transaction details
        """
        try:
            self.logger.info(
                f"Processing refund for cancelled Order {getattr(entity, 'technical_id', '<unknown>')}"
            )

            # Cast the entity to Order for type-safe operations
            order = cast_entity(entity, Order)

            # Validate cancel reason is provided (required for cancellation)
            if not self._validate_cancel_reason(order):
                raise ValueError(f"Order {order.technical_id} cancellation requires a valid cancel reason")

            # Check if refund is needed
            if order.requires_refund():
                # Process refund asynchronously
                refund_result = await self._process_refund_async(order)
                
                # Update order with refund details
                order.refund_transaction_id = refund_result["refund_transaction_id"]
                
                self.logger.info(
                    f"Refund processing completed for Order {order.technical_id} with transaction: {refund_result['refund_transaction_id']}"
                )
            else:
                self.logger.info(
                    f"No refund required for Order {order.technical_id} (payment status: {order.payment_status})"
                )

            return order

        except Exception as e:
            self.logger.error(
                f"Error processing refund for Order {getattr(entity, 'technical_id', '<unknown>')}: {str(e)}"
            )
            raise

    def _validate_cancel_reason(self, order: Order) -> bool:
        """
        Validate that cancel reason is provided and meets requirements.

        Args:
            order: The Order entity to validate

        Returns:
            True if cancel reason is valid, False otherwise
        """
        if not order.cancel_reason:
            self.logger.warning(f"Order {order.technical_id} cancellation missing required cancel_reason")
            return False

        if len(order.cancel_reason.strip()) == 0:
            self.logger.warning(f"Order {order.technical_id} cancel_reason cannot be empty")
            return False

        if len(order.cancel_reason) > 500:
            self.logger.warning(f"Order {order.technical_id} cancel_reason too long (max 500 characters)")
            return False

        return True

    async def _process_refund_async(self, order: Order) -> dict[str, Any]:
        """
        Simulate async refund processing with external payment gateway.

        Args:
            order: The Order entity to process refund for

        Returns:
            Dictionary containing refund result with refund_transaction_id
        """
        self.logger.info(f"Initiating async refund processing for Order {order.technical_id}")

        # Validate order has payment to refund
        if not order.payment_transaction_id:
            raise ValueError(f"Order {order.technical_id} has no payment transaction to refund")

        if order.payment_status != "completed":
            raise ValueError(f"Order {order.technical_id} payment status {order.payment_status} cannot be refunded")

        # Simulate async refund gateway call
        await asyncio.sleep(0.1)  # Simulate network delay

        # Generate refund transaction ID
        refund_transaction_id = f"rfnd_{uuid.uuid4().hex[:12]}"

        # Simulate refund processing logic
        refund_result = await self._simulate_refund_gateway(order, refund_transaction_id)

        self.logger.info(
            f"Refund gateway response for Order {order.technical_id}: {refund_result['status']}"
        )

        return refund_result

    async def _simulate_refund_gateway(self, order: Order, refund_transaction_id: str) -> dict[str, Any]:
        """
        Simulate refund gateway processing.

        Args:
            order: The Order entity
            refund_transaction_id: Generated refund transaction ID

        Returns:
            Refund result dictionary
        """
        # Simulate async processing delay
        await asyncio.sleep(0.05)

        # Simulate refund success (refunds typically have higher success rate than payments)
        # For demo purposes: 95% success rate
        import random
        
        if random.random() < 0.05:
            # Simulate refund failure
            self.logger.warning(f"Refund failed for Order {order.technical_id}")
            return {
                "status": "failed",
                "refund_transaction_id": refund_transaction_id,
                "error_code": "REFUND_DECLINED",
                "error_message": "Original payment method no longer valid"
            }
        else:
            # Simulate refund success
            return {
                "status": "completed",
                "refund_transaction_id": refund_transaction_id,
                "refund_amount": order.total,
                "original_transaction_id": order.payment_transaction_id,
                "gateway_response": "REFUND_APPROVED",
                "estimated_settlement_days": 3
            }

    async def _handle_refund_failure(self, order: Order, error_details: dict[str, Any]) -> None:
        """
        Handle refund failure scenarios.

        Args:
            order: The Order entity
            error_details: Details about the refund failure
        """
        self.logger.error(
            f"Refund failed for Order {order.technical_id}: {error_details.get('error_message', 'Unknown error')}"
        )

        # Could trigger additional workflows here like:
        # - Create manual refund task for customer service
        # - Send notification to finance team
        # - Schedule retry refund attempt
        # - Update order with refund failure status

    def _log_cancellation_details(self, order: Order) -> None:
        """
        Log cancellation details for audit purposes.

        Args:
            order: The cancelled Order entity
        """
        self.logger.info(
            f"Order {order.technical_id} cancelled - Reason: {order.cancel_reason}, "
            f"Original Total: {order.total}, Payment Status: {order.payment_status}"
        )
