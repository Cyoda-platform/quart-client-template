"""
Settlement Processors for Enterprise Payment Processing System

Handles settlement reconciliation and completion.
"""

import logging
from typing import Any, Dict, List

from application.entity.settlement import Settlement
from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor


class SettlementReconciliationProcessor(CyodaProcessor):
    """Processor for settlement reconciliation"""

    def __init__(self) -> None:
        super().__init__(
            name="SettlementReconciliationProcessor",
            description="Reconciles settlement batches and validates transactions",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Reconcile the settlement batch.

        Args:
            entity: The Settlement to reconcile
            **kwargs: Additional processing parameters

        Returns:
            The settlement with reconciliation results
        """
        try:
            self.logger.info(
                f"Reconciling settlement {getattr(entity, 'technical_id', '<unknown>')}"
            )

            settlement = cast_entity(entity, Settlement)

            # Perform reconciliation
            discrepancies = self._check_for_discrepancies(settlement)
            reconciliation_status = (
                "RECONCILED" if not discrepancies else "DISCREPANCIES"
            )
            notes = self._generate_reconciliation_notes(settlement, discrepancies)

            # Set reconciliation results
            settlement.set_reconciliation_result(
                reconciliation_status, notes, discrepancies
            )

            # Mark as completed if no discrepancies
            if not discrepancies:
                settlement.mark_completed()

            self.logger.info(
                f"Settlement {settlement.technical_id} reconciliation completed: "
                f"status={reconciliation_status}, discrepancies={len(discrepancies) if discrepancies else 0}"
            )

            return settlement

        except Exception as e:
            self.logger.error(
                f"Error reconciling settlement {getattr(entity, 'technical_id', '<unknown>')}: {str(e)}"
            )
            raise

    def _check_for_discrepancies(self, settlement: Settlement) -> List[Dict[str, Any]]:
        """Check for discrepancies in the settlement"""
        discrepancies: List[Dict[str, Any]] = []

        # Check transaction count
        if settlement.transaction_count != len(settlement.transaction_ids):
            discrepancies.append(
                {
                    "type": "TRANSACTION_COUNT_MISMATCH",
                    "expected": settlement.transaction_count,
                    "actual": len(settlement.transaction_ids),
                }
            )

        # Check total amount (simplified)
        if settlement.total_amount < 0:
            discrepancies.append(
                {
                    "type": "NEGATIVE_AMOUNT",
                    "amount": settlement.total_amount,
                }
            )

        return discrepancies

    def _generate_reconciliation_notes(
        self, settlement: Settlement, discrepancies: List[Dict[str, Any]]
    ) -> str:
        """Generate reconciliation notes"""
        if not discrepancies:
            return f"Settlement {settlement.settlement_batch_id} reconciled successfully with {settlement.transaction_count} transactions totaling {settlement.total_amount} {settlement.currency}"
        else:
            return f"Settlement {settlement.settlement_batch_id} reconciliation found {len(discrepancies)} discrepancies"
