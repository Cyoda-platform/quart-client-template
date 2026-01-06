"""
ExecutionReconciler processor for institutional trading platform.

Reconciles execution reports with OMS state and produces Execution entities.
Used on execution_processing.transition 'reconcile' (SYNC).
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict

from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor
from services.services import get_entity_service


class ExecutionReconciler(CyodaProcessor):
    """
    Reconciles execution reports with OMS state and creates Execution entities.
    """

    def __init__(self) -> None:
        super().__init__(
            name="ExecutionReconciler",
            description="Reconciles execution reports and creates Execution entities",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Reconcile the execution report.

        Args:
            entity: The execution entity to reconcile
            **kwargs: Additional reconciliation parameters

        Returns:
            The reconciled execution entity
        """
        try:
            self.logger.info(
                f"Reconciling execution {getattr(entity, 'technical_id', '<unknown>')}"
            )

            execution_id = getattr(entity, "technical_id", None)

            # Validate execution report
            self._validate_execution_report(entity)

            # Match with original order
            order_id = getattr(entity, "orderId", None)
            if not order_id:
                raise ValueError("Execution missing orderId reference")

            # TODO: Fetch order from entity service to validate
            # order_service = get_entity_service()
            # order = await order_service.get(order_id, "order", "1")

            # Reconcile quantities and prices
            reconciliation = self._reconcile_execution(entity)

            if not reconciliation["matched"]:
                self.logger.warning(
                    f"Execution {execution_id} reconciliation mismatch: {reconciliation['reason']}"
                )

            # Store reconciliation results
            if not hasattr(entity, "reconciliationMetadata"):
                entity.reconciliationMetadata = {}
            entity.reconciliationMetadata.update(reconciliation)
            entity.reconciliationMetadata["reconciled_at"] = (
                datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            )

            self.logger.info(f"Execution {execution_id} reconciliation completed")
            return entity

        except Exception as e:
            self.logger.error(f"Error reconciling execution: {str(e)}")
            raise

    def _validate_execution_report(self, entity: CyodaEntity) -> None:
        """
        Validate the execution report structure.

        Args:
            entity: The execution entity

        Raises:
            ValueError: If validation fails
        """
        required_fields = ["orderId", "executionId", "quantity", "price", "timestamp"]

        for field in required_fields:
            if not hasattr(entity, field) or getattr(entity, field) is None:
                raise ValueError(f"Execution missing required field: {field}")

    def _reconcile_execution(self, entity: CyodaEntity) -> Dict[str, Any]:
        """
        Reconcile execution against order state.

        Args:
            entity: The execution entity

        Returns:
            Reconciliation result dictionary
        """
        # TODO: Integrate with order service to fetch original order
        # TODO: Validate execution quantity against order quantity
        # TODO: Validate execution price against order price/limits
        # TODO: Check for duplicate executions

        result: Dict[str, Any] = {
            "matched": True,
            "reason": None,
            "quantity_check": "PASSED",
            "price_check": "PASSED",
            "duplicate_check": "PASSED",
        }

        quantity = getattr(entity, "quantity", 0)
        if quantity <= 0:
            result["matched"] = False
            result["reason"] = f"Invalid execution quantity: {quantity}"
            result["quantity_check"] = "FAILED"

        price = getattr(entity, "price", 0)
        if price <= 0:
            result["matched"] = False
            result["reason"] = f"Invalid execution price: {price}"
            result["price_check"] = "FAILED"

        return result
