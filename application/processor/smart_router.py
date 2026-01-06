"""
SmartRouter processor for institutional trading platform.

Decides venue/broker routing and creates execution instructions with price/qty splits.
Used on order_processing.transition 'process' (ASYNC_NEW_TX).
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor


class SmartRouter(CyodaProcessor):
    """
    Routes orders to appropriate venues/brokers and creates execution instructions.
    """

    def __init__(self) -> None:
        super().__init__(
            name="SmartRouter",
            description="Routes orders to venues and creates execution instructions",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Route the order and create execution instructions.

        Args:
            entity: The order entity to route
            **kwargs: Additional routing parameters

        Returns:
            The order entity with routing instructions
        """
        try:
            self.logger.info(
                f"Routing order {getattr(entity, 'technical_id', '<unknown>')}"
            )

            order_id = getattr(entity, "technical_id", None)

            # Determine routing strategy
            routing_plan = self._determine_routing(entity)

            # Create execution instructions
            execution_instructions = self._create_execution_instructions(
                entity, routing_plan
            )

            # Store routing information on entity
            if not hasattr(entity, "routingMetadata"):
                entity.routingMetadata = {}
            entity.routingMetadata["plan"] = routing_plan
            entity.routingMetadata["instructions"] = execution_instructions
            entity.routingMetadata["routed_at"] = (
                datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            )

            self.logger.info(
                f"Order {order_id} routed to {len(execution_instructions)} venue(s)"
            )
            return entity

        except Exception as e:
            self.logger.error(f"Error routing order: {str(e)}")
            raise

    def _determine_routing(self, entity: CyodaEntity) -> Dict[str, Any]:
        """
        Determine the routing strategy for the order.

        Args:
            entity: The order entity

        Returns:
            Routing plan dictionary
        """
        # TODO: Integrate with venue connectivity service
        # TODO: Load venue configuration and liquidity data
        # TODO: Implement smart routing algorithm (VWAP, TWAP, etc.)

        instrument_id = getattr(entity, "instrumentId", None)
        quantity = getattr(entity, "quantity", 0)
        side = getattr(entity, "side", None)

        # Simple routing: split between primary and secondary venues
        primary_qty = int(quantity * 0.7)
        secondary_qty = quantity - primary_qty

        routing_plan = {
            "strategy": "split_venue",
            "splits": [
                {
                    "venue": "PRIMARY_EXCHANGE",
                    "quantity": primary_qty,
                    "priority": 1,
                },
                {
                    "venue": "SECONDARY_BROKER",
                    "quantity": secondary_qty,
                    "priority": 2,
                },
            ],
        }

        self.logger.debug(f"Routing plan for {instrument_id}: {routing_plan}")
        return routing_plan

    def _create_execution_instructions(
        self, entity: CyodaEntity, routing_plan: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Create execution instructions for each venue.

        Args:
            entity: The order entity
            routing_plan: The routing plan

        Returns:
            List of execution instructions
        """
        instructions: List[Dict[str, Any]] = []
        order_id = getattr(entity, "technical_id", None)

        for split in routing_plan.get("splits", []):
            instruction = {
                "instruction_id": str(uuid.uuid4()),
                "order_id": order_id,
                "venue": split["venue"],
                "quantity": split["quantity"],
                "side": getattr(entity, "side", None),
                "order_type": getattr(entity, "orderType", None),
                "price": getattr(entity, "price", None),
                "time_in_force": getattr(entity, "timeInForce", "DAY"),
                "created_at": (
                    datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
                ),
                "status": "PENDING",
            }
            instructions.append(instruction)

        return instructions

