import json
import logging
from typing import Any, Optional

from common.entity.entity_factory import create_entity
from common.grpc_client.constants import (
    CRITERIA_CALC_REQ_EVENT_TYPE,
    CRITERIA_CALC_RESP_EVENT_TYPE,
)
from common.grpc_client.handlers.base import Handler
from common.grpc_client.responses.spec import ResponseSpec
from common.proto.cloudevents_pb2 import CloudEvent

logger = logging.getLogger(__name__)


class CriteriaCalcRequestHandler(Handler):
    async def handle(
        self, request: CloudEvent, services: Any = None
    ) -> Optional[ResponseSpec]:
        data = json.loads(request.text_data)
        criteria_name = data.get("criteriaName")

        # Get entity type from model key
        model_key = data["payload"]["meta"]["modelKey"]["name"]
        entity_type = model_key.lower()  # Convert to lowercase for our entity factory

        # Create entity using our factory system
        try:
            entity = create_entity(entity_type, data["payload"]["data"])
        except ValueError:
            logger.error(f"Unknown entity type: {entity_type}")
            # Fallback: create a generic CyodaEntity
            from common.entity.cyoda_entity import CyodaEntity

            entity = CyodaEntity(**data["payload"]["data"])

        # Set technical_id from gRPC request
        entity.technical_id = data["entityId"]

        # Add transition information to metadata
        if "transition" in data and "name" in data["transition"]:
            entity.add_metadata("current_transition", data["transition"]["name"])

        matches = None
        try:
            logger.info(
                f"[PROCESSING] Starting {CRITERIA_CALC_REQ_EVENT_TYPE} - Criteria: {criteria_name}, "
                f"EntityId: {data['entityId']}, RequestId: {data.get('requestId')}"
            )

            # Use processor_manager from services
            processor_manager = services.processor_manager if services else None
            if not processor_manager:
                raise ValueError("processor_manager not available in services")

            matches = await processor_manager.check_criteria(
                criteria_name=criteria_name, entity=entity
            )

            # Convert entity back to dict for response (criteria checking might modify entity)
            data["payload"]["data"] = entity.to_dict()
            logger.info(
                f"[PROCESSING] Success {CRITERIA_CALC_REQ_EVENT_TYPE} - "
                f"Criteria: {criteria_name}, EntityId: {data['entityId']}"
            )

        except Exception as e:
            logger.error(
                f"[PROCESSING] Error {CRITERIA_CALC_REQ_EVENT_TYPE} - "
                f"Criteria: {criteria_name}, EntityId: {data['entityId']}"
            )
            logger.exception("Error processing entity", exc_info=e)

            # Mark entity as failed using metadata
            entity.add_metadata("failed", True)
            entity.add_metadata("error_message", str(e))
            entity.set_state("FAILED")

            # Convert entity back to dict for response
            data["payload"]["data"] = entity.to_dict()
            matches = False

        return ResponseSpec(
            response_type=CRITERIA_CALC_RESP_EVENT_TYPE,
            data={
                "requestId": data.get("requestId"),
                "entityId": data.get("entityId"),
                "matches": matches,
            },
            success=True,
        )
