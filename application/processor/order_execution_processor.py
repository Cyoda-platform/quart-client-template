"""
OrderExecutionProcessor for Trading Platform

Handles order execution logic including market order processing,
position updates, and trade settlement.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict
from decimal import Decimal

from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor
from application.entity.order.version_1.order import Order
from application.entity.position.version_1.position import Position
from services.services import get_entity_service


class OrderExecutionProcessor(CyodaProcessor):
    """
    Processor for Order execution that handles trade execution,
    position updates, and settlement processing.
    """

    def __init__(self) -> None:
        super().__init__(
            name="OrderExecutionProcessor",
            description="Processes order execution, updates positions and handles trade settlement",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Process the Order execution according to trading requirements.

        Args:
            entity: The Order to execute (must be in 'compliance_approved' state)
            **kwargs: Additional processing parameters

        Returns:
            The executed order with updated execution details
        """
        try:
            self.logger.info(
                f"Executing Order {getattr(entity, 'technical_id', '<unknown>')}"
            )

            # Cast the entity to Order for type-safe operations
            order = cast_entity(entity, Order)

            # Execute the order
            execution_details = await self._execute_order(order)
            
            # Update order with execution details
            order.executed_quantity = execution_details["executed_quantity"]
            order.executed_price = execution_details["executed_price"]
            order.execution_time = execution_details["execution_time"]
            order.execution_venue = execution_details["execution_venue"]
            order.commission = execution_details["commission"]
            order.net_amount = execution_details["net_amount"]

            # Update or create position
            await self._update_position(order, execution_details)

            # Log execution completion
            self.logger.info(
                f"Order {order.technical_id} executed successfully - "
                f"Qty: {order.executed_quantity}, Price: {order.executed_price}"
            )

            return order

        except Exception as e:
            self.logger.error(
                f"Error executing order {getattr(entity, 'technical_id', '<unknown>')}: {str(e)}"
            )
            raise

    async def _execute_order(self, order: Order) -> Dict[str, Any]:
        """
        Execute the order and return execution details.

        Args:
            order: The Order to execute

        Returns:
            Dictionary containing execution details
        """
        current_timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        execution_id = str(uuid.uuid4())

        # Simulate market execution (in real system, this would connect to exchange)
        executed_quantity = order.quantity
        
        # For market orders, use current market price simulation
        if order.order_type == "MARKET":
            executed_price = self._get_market_price(order.symbol)
        else:
            # For limit orders, use the limit price
            executed_price = order.price or self._get_market_price(order.symbol)

        # Calculate commission (0.1% of trade value)
        gross_amount = executed_quantity * executed_price
        commission = gross_amount * Decimal("0.001")
        
        # Calculate net amount
        if order.side == "BUY":
            net_amount = gross_amount + commission
        else:
            net_amount = gross_amount - commission

        execution_details = {
            "executed_quantity": executed_quantity,
            "executed_price": executed_price,
            "execution_time": current_timestamp,
            "execution_venue": "SIMULATED_EXCHANGE",
            "execution_id": execution_id,
            "commission": commission,
            "gross_amount": gross_amount,
            "net_amount": net_amount,
        }

        return execution_details

    def _get_market_price(self, symbol: str) -> Decimal:
        """
        Get current market price for the symbol.
        In real system, this would query market data service.

        Args:
            symbol: Trading symbol

        Returns:
            Current market price
        """
        # Simulate market prices based on symbol
        market_prices = {
            "AAPL": Decimal("150.00"),
            "MSFT": Decimal("300.00"),
            "GOOGL": Decimal("2500.00"),
            "TSLA": Decimal("200.00"),
            "AMZN": Decimal("3000.00"),
        }
        
        return market_prices.get(symbol, Decimal("100.00"))

    async def _update_position(self, order: Order, execution_details: Dict[str, Any]) -> None:
        """
        Update or create position based on order execution.

        Args:
            order: The executed order
            execution_details: Execution details from order processing
        """
        entity_service = get_entity_service()

        try:
            # Calculate trade quantity (negative for sell orders)
            trade_quantity = order.executed_quantity
            if order.side == "SELL":
                trade_quantity = -trade_quantity

            # Try to find existing position
            # In real system, would query by client_id and instrument_id
            position_data = {
                "clientId": order.client_id,
                "instrumentId": order.instrument_id,
                "symbol": order.symbol,
                "quantity": trade_quantity,
                "averagePrice": order.executed_price,
                "costBasis": abs(trade_quantity) * order.executed_price,
                "realizedPnl": Decimal("0"),
            }

            # Create new position using Pydantic model
            position = Position(**position_data)
            position_dict = position.model_dump(by_alias=True)

            # Save the position
            response = await entity_service.save(
                entity=position_dict,
                entity_class=Position.ENTITY_NAME,
                entity_version=str(Position.ENTITY_VERSION),
            )

            created_position_id = response.metadata.id
            self.logger.info(
                f"Created/Updated Position {created_position_id} for {order.symbol}"
            )

        except Exception as e:
            self.logger.error(
                f"Failed to update position for order {order.technical_id}: {str(e)}"
            )
            # Don't fail the order execution if position update fails
            pass
