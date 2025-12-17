import logging
from typing import Any

from application.entity.position.version_1.position import Position
from common.entity.cyoda_entity import CyodaEntity
from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaProcessor


class PositionReconciliationProcessor(CyodaProcessor):
    """
    Processor for reconciling positions.
    """

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Processes the position entity for reconciliation.
        """
        position = cast_entity(entity, Position)
        logging.info(
            f"Reconciling position for instrument: {position.instrument_id} in portfolio: {position.portfolio_id}"
        )
        # In a real implementation, we would compare with external data.
        # For now, we assume reconciliation is successful.
        return position
