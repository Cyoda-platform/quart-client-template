"""
OrderValidationProcessor

Validates orders against accounts and risk limits.
"""

import logging
from typing import Any, List, Optional

from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor
from common.service.entity_service import SearchConditionRequest, EntityResponse
from services.services import get_entity_service
from application.entity.order.version_1.order import Order
from application.entity.account.version_1.account import Account
from application.entity.risk_limit.version_1.risk_limit import RiskLimit


class OrderValidationProcessor(CyodaProcessor):
    def __init__(self) -> None:
        super().__init__(
            name="OrderValidationProcessor",
            description="Validates orders and checks risk limits",
        )
        self.logger: logging.Logger = getattr(self, "logger", logging.getLogger(__name__))

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        try:
            order = cast_entity(entity, Order)
            self.logger.info(f"Validating order {order.order_id}")

            # Default to FAIL
            validation_status = "FAIL"
            rejection_reason = ""
            status = "REJECTED"

            entity_service = get_entity_service()

            # 1. Check Account
            search_req = SearchConditionRequest.builder().equals("account_id", order.account_id).build()
            accounts: List[EntityResponse] = await entity_service.search("Account", search_req)
            
            if not accounts:
                rejection_reason = f"Account {order.account_id} not found"
            else:
                account_wrapper = accounts[0]
                # cast_entity needs CyodaEntity, accounts[0].data is CyodaEntity
                account = cast_entity(account_wrapper.data, Account)
                
                if not account.is_active:
                    rejection_reason = f"Account {order.account_id} is inactive"
                else:
                    # 2. Check Risk Limits
                    # We look for limits for this account
                    search_limit = SearchConditionRequest.builder().equals("account_id", order.account_id).build()
                    limits: List[EntityResponse] = await entity_service.search("RiskLimit", search_limit)
                    
                    limit_breached = False
                    for limit_resp in limits:
                        limit = cast_entity(limit_resp.data, RiskLimit)
                        if limit.limit_type == "ORDER_SIZE_LIMIT":
                            if order.quantity > limit.threshold:
                                limit_breached = True
                                rejection_reason = f"Order quantity {order.quantity} exceeds limit {limit.threshold}"
                                break
                        # Add other checks as needed
                    
                    if not limit_breached:
                        validation_status = "PASS"
                        status = "ACCEPTED"
                        rejection_reason = None

            # Update Order fields
            order.validation_status = validation_status
            order.status = status
            order.rejection_reason = rejection_reason
            
            self.logger.info(f"Order {order.order_id} validation result: {validation_status}")
            return order

        except Exception as e:
            self.logger.error(f"Error processing order {getattr(entity, 'technical_id', 'unknown')}: {str(e)}")
            raise
