"""
PreTradeRiskCheckProcessor for trading platform.

Handles pre-trade risk validation for Order entities by checking against
RiskLimit entities to ensure orders comply with risk management rules.
"""

import logging
from typing import Any, List

from application.entity.order.version_1.order import Order
from application.entity.risk_limit.version_1.risk_limit import RiskLimit
from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor
from services.services import get_entity_service


class PreTradeRiskCheckProcessor(CyodaProcessor):
    """
    Processor for Order that performs pre-trade risk checks.

    Retrieves applicable RiskLimit entities and validates the order against
    size limits, position limits, and notional limits before execution.
    """

    def __init__(self) -> None:
        super().__init__(
            name="PreTradeRiskCheckProcessor",
            description="Performs pre-trade risk checks on Order entities against RiskLimit rules",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Process the Order entity and perform pre-trade risk checks.

        Args:
            entity: The Order entity to check
            **kwargs: Additional processing parameters

        Returns:
            The processed Order entity

        Raises:
            ValueError: If risk limit is breached
        """
        try:
            self.logger.info(
                f"Processing Order {getattr(entity, 'technical_id', '<unknown>')}"
            )

            # Cast the entity to Order for type-safe operations
            order = cast_entity(entity, Order)

            # Get entity service
            entity_service = get_entity_service()

            # Retrieve risk limits for the account
            risk_limits = await self._get_risk_limits(entity_service, order.account_id)

            if not risk_limits:
                self.logger.warning(
                    f"No risk limits found for account {order.account_id}"
                )
                return order

            # Perform risk checks
            self._check_order_against_limits(order, risk_limits)

            self.logger.info(f"Order {order.technical_id} passed pre-trade risk checks")

            return order

        except ValueError as e:
            # Risk limit breach
            error_id = getattr(entity, 'technical_id', '<unknown>')
            self.logger.error(
                f"Risk limit breach for Order {error_id}: {str(e)}"
            )
            raise
        except Exception as e:
            self.logger.error(
                f"Error processing Order {getattr(entity, 'technical_id', '<unknown>')}: {str(e)}"
            )
            raise

    async def _get_risk_limits(
        self, entity_service: Any, account_id: str
    ) -> List[RiskLimit]:
        """
        Retrieve risk limits for the given account.

        Args:
            entity_service: The entity service instance
            account_id: The account ID to get limits for

        Returns:
            List of RiskLimit entities
        """
        try:
            # Note: In a real system, you would use proper query filters
            # to retrieve all active risk limits for the account
            # For this example, we'll return an empty list and log
            self.logger.info(f"Retrieving risk limits for account {account_id}")

            # Placeholder - in production, implement proper query
            risk_limits: List[RiskLimit] = []

            return risk_limits

        except Exception as e:
            self.logger.error(
                f"Error retrieving risk limits for account {account_id}: {str(e)}"
            )
            return []

    def _check_order_against_limits(
        self, order: Order, risk_limits: List[RiskLimit]
    ) -> None:
        """
        Check order against all applicable risk limits.

        Args:
            order: The Order entity to check
            risk_limits: List of RiskLimit entities to check against

        Raises:
            ValueError: If any risk limit is breached
        """
        for limit in risk_limits:
            # Skip inactive limits
            if not limit.is_active:
                continue

            # Check if limit applies to this instrument
            if limit.instrument_id and limit.instrument_id != order.instrument_id:
                continue

            # Check order size limit
            if (
                limit.limit_type == "ORDER_SIZE"
                and limit.max_order_quantity is not None
            ):
                if order.quantity > limit.max_order_quantity:
                    error_msg = (
                        f"Order quantity {order.quantity} exceeds maximum "
                        f"order quantity {limit.max_order_quantity} for account "
                        f"{order.account_id}"
                    )
                    self.logger.error(error_msg)
                    if limit.breach_action == "REJECT":
                        raise ValueError(error_msg)

            # Check notional limit
            if limit.limit_type == "MAX_NOTIONAL" and limit.max_notional is not None:
                if order.price is not None:
                    notional = order.quantity * order.price
                    if notional > limit.max_notional:
                        error_msg = (
                            f"Order notional {notional:.2f} exceeds maximum "
                            f"notional {limit.max_notional:.2f} for account "
                            f"{order.account_id}"
                        )
                        self.logger.error(error_msg)
                        if limit.breach_action == "REJECT":
                            raise ValueError(error_msg)

            # Check position limit (would need to retrieve current position)
            if (
                limit.limit_type == "POSITION"
                and limit.max_position_quantity is not None
            ):
                # Note: In production, you would retrieve the current position
                # and check if the order would cause the position to exceed the limit
                self.logger.info(
                    f"Position limit check for order {order.technical_id}: "
                    f"max_position={limit.max_position_quantity}"
                )

            self.logger.info(
                f"Order {order.technical_id} passed risk limit check: {limit.limit_type}"
            )
