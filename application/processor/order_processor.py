"""
OrderProcessor for Cyoda Client Application

Handles the business logic for processing Order instances.
Calculates the totalAmount based on item quantities and prices,
and updates the order accordingly.
"""

import logging
from typing import Any

from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor
from application.entity.order.version_1.order import Order


class OrderProcessor(CyodaProcessor):
    """
    Processor for Order that calculates total amount from items.
    
    This processor is triggered on create and update transitions
    to ensure the totalAmount is always accurate based on the
    current items in the order.
    """
    
    def __init__(self) -> None:
        super().__init__(
            name="OrderProcessor",
            description="Processes Order instances and calculates total amount from items",
        )
        # Ensure logger attribute is present for type-checkers/readers.
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )
    
    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Process the Order by calculating the total amount.
        
        Args:
            entity: The Order entity to process
            **kwargs: Additional processing parameters
            
        Returns:
            The processed order with updated totalAmount
        """
        try:
            self.logger.info(
                f"Processing Order {getattr(entity, 'technical_id', '<unknown>')}"
            )
            
            # Cast the entity to Order for type-safe operations
            order = cast_entity(entity, Order)
            
            # Calculate and update total amount
            calculated_total = self._calculate_total_amount(order)
            order.total_amount = calculated_total
            
            self.logger.info(
                f"Order {order.technical_id or order.entity_id} total amount calculated: {calculated_total}"
            )
            
            # Log order details for debugging
            self.logger.debug(
                f"Order details - Customer: {order.customer_id}, "
                f"Items: {len(order.items)}, Status: {order.status}, "
                f"Total: {order.total_amount}"
            )
            
            return order
            
        except Exception as e:
            self.logger.error(
                f"Error processing Order {getattr(entity, 'technical_id', '<unknown>')}: {str(e)}"
            )
            raise
    
    def _calculate_total_amount(self, order: Order) -> float:
        """
        Calculate the total amount for the order.
        
        Args:
            order: The Order entity
            
        Returns:
            The calculated total amount (sum of quantity * price for all items)
        """
        if not order.items:
            self.logger.warning(f"Order {order.entity_id} has no items")
            return 0.0
        
        total = 0.0
        for i, item in enumerate(order.items):
            item_total = item.quantity * item.price
            total += item_total
            
            self.logger.debug(
                f"Item {i+1}: Product {item.product_id}, "
                f"Qty: {item.quantity}, Price: {item.price}, "
                f"Subtotal: {item_total}"
            )
        
        # Round to 2 decimal places for currency precision
        total = round(total, 2)
        
        self.logger.info(f"Calculated total amount: {total}")
        return total
