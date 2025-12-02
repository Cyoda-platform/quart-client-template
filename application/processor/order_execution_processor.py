"""
OrderExecutionProcessor for Real-Time Trading Platform

Handles order execution simulation, trade creation, and portfolio updates
for filled orders in the trading platform.
"""

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from application.entity.order.version_1.order import Order
from application.entity.trade.version_1.trade import Trade
from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor
from services.services import get_entity_service


class OrderExecutionProcessor(CyodaProcessor):
    """
    Processor for Order that simulates order execution and creates trades.
    """

    def __init__(self) -> None:
        super().__init__(
            name="OrderExecutionProcessor",
            description="Executes orders and creates corresponding trades",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Execute the Order and create corresponding Trade entities.

        Args:
            entity: The Order to execute (must be in 'submitted' state)
            **kwargs: Additional processing parameters

        Returns:
            The order with execution data
        """
        try:
            self.logger.info(
                f"Executing Order {getattr(entity, 'technical_id', '<unknown>')}"
            )

            # Cast the entity to Order for type-safe operations
            order = cast_entity(entity, Order)

            # Simulate order execution
            execution_data = await self._execute_order(order)
            order.set_execution_data(execution_data)

            # Create trade if order was filled
            if execution_data.get("filled_quantity", 0) > 0:
                await self._create_trade(order, execution_data)

            # Log execution completion
            self.logger.info(
                f"Order {order.technical_id} executed: {execution_data['status']}"
            )

            return order

        except Exception as e:
            self.logger.error(
                f"Error executing Order {getattr(entity, 'technical_id', '<unknown>')}: {str(e)}"
            )
            raise

    async def _execute_order(self, order: Order) -> Dict[str, Any]:
        """
        Simulate order execution based on order type and market conditions.

        Args:
            order: The Order entity to execute

        Returns:
            Dictionary containing execution results
        """
        current_timestamp = (
            datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        )

        execution_data: Dict[str, Any] = {
            "executed_at": current_timestamp,
            "status": "FILLED",
            "filled_quantity": 0,
            "remaining_quantity": order.quantity,
            "execution_price": 0.0,
            "executions": [],
        }

        # Simulate market price (in real system would come from market data)
        market_price = self._get_simulated_market_price(order.symbol)

        if order.is_market_order():
            # Market orders execute immediately at market price
            execution_data["filled_quantity"] = order.quantity
            execution_data["remaining_quantity"] = 0
            execution_data["execution_price"] = market_price
            execution_data["executions"].append(
                {  # type: ignore
                    "quantity": order.quantity,
                    "price": market_price,
                    "timestamp": current_timestamp,
                }
            )
        elif order.is_limit_order() and order.price:
            # Limit orders execute if market price is favorable
            if self._should_limit_order_execute(order, market_price):
                execution_data["filled_quantity"] = order.quantity
                execution_data["remaining_quantity"] = 0
                execution_data["execution_price"] = order.price
                execution_data["executions"].append(
                    {  # type: ignore
                        "quantity": order.quantity,
                        "price": order.price,
                        "timestamp": current_timestamp,
                    }
                )
            else:
                execution_data["status"] = "PENDING"
                execution_data["message"] = "Limit order waiting for favorable price"

        # Update order fill information
        if execution_data["filled_quantity"] > 0:  # type: ignore
            order.update_fill(
                execution_data["filled_quantity"],  # type: ignore
                execution_data["execution_price"],  # type: ignore
            )

        return execution_data

    def _get_simulated_market_price(self, symbol: str) -> float:
        """
        Get simulated market price for a symbol.
        In real implementation, this would come from market data feeds.
        """
        # Simple simulation based on symbol hash for consistency
        base_price = 100.0 + (hash(symbol) % 1000) / 10.0
        return round(base_price, 2)

    def _should_limit_order_execute(self, order: Order, market_price: float) -> bool:
        """
        Determine if a limit order should execute based on market price.
        """
        if not order.price:
            return False

        if order.side == "BUY":
            # Buy limit executes if market price <= limit price
            return market_price <= order.price
        else:  # SELL
            # Sell limit executes if market price >= limit price
            return market_price >= order.price

    async def _create_trade(self, order: Order, execution_data: Dict[str, Any]) -> None:
        """
        Create a Trade entity for the executed order.

        Args:
            order: The executed Order
            execution_data: Execution details
        """
        try:
            entity_service = get_entity_service()

            # Calculate settlement date (T+2 for equities)
            execution_time = datetime.fromisoformat(
                execution_data["executed_at"].replace("Z", "+00:00")
            )
            settlement_date = execution_time + timedelta(days=2)

            # Create Trade entity
            trade = Trade(
                tradeId=f"TRD-{str(uuid.uuid4())[:8]}",
                orderId=order.order_id,
                symbol=order.symbol,
                side=order.side,
                quantity=execution_data["filled_quantity"],  # type: ignore
                price=execution_data["execution_price"],  # type: ignore
                portfolioId=order.portfolio_id,
                executionTime=execution_data["executed_at"],  # type: ignore
                settlementDate=settlement_date.isoformat().replace("+00:00", "Z"),
                exchange="SIMULATED",
                commission=self._calculate_commission(
                    execution_data["filled_quantity"],  # type: ignore
                    execution_data["execution_price"],  # type: ignore
                ),
            )

            # Convert to dict for EntityService
            trade_data = trade.model_dump(by_alias=True)

            # Save the Trade entity
            response = await entity_service.save(
                entity=trade_data,
                entity_class=Trade.ENTITY_NAME,
                entity_version=str(Trade.ENTITY_VERSION),
            )

            created_trade_id = response.metadata.id

            self.logger.info(
                f"Created Trade {created_trade_id} for Order {order.order_id}"
            )

        except Exception as e:
            self.logger.error(
                f"Failed to create Trade for Order {order.order_id}: {str(e)}"
            )
            # Don't raise - order execution should still succeed

    def _calculate_commission(self, quantity: int, price: float) -> float:
        """
        Calculate commission for the trade.
        Simple flat rate + percentage model.
        """
        notional_value = quantity * price
        flat_fee = 5.0  # $5 flat fee
        percentage_fee = notional_value * 0.001  # 0.1% of notional
        return round(flat_fee + percentage_fee, 2)
