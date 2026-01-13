import json
import logging
from typing import Any, Optional

from common.entity.entity_factory import create_entity
from common.exception.grpc_exceptions import (
    HandlerError,
    ProcessingError,
    ValidationError,
)
from common.grpc_client.constants import CALC_REQ_EVENT_TYPE, CALC_RESP_EVENT_TYPE
from common.grpc_client.handlers.base import Handler
from common.grpc_client.responses.spec import ResponseSpec
from common.proto.cloudevents_pb2 import CloudEvent

logger = logging.getLogger(__name__)


class CalcRequestHandler(Handler):
    async def handle(
        self, request: CloudEvent, services: Any = None
    ) -> Optional[ResponseSpec]:
        data = json.loads(request.text_data)
        processor_name = data.get("processorName")

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
        except Exception as e:
            raise ValidationError(
                message=f"Failed to create entity of type '{entity_type}'",
                field_name="entity_type",
                field_value=entity_type,
                original_error=e,
            )

        # Set technical_id from gRPC request
        entity.technical_id = data["entityId"]

        # Add transition information to metadata
        if "transition" in data and "name" in data["transition"]:
            entity.add_metadata("current_transition", data["transition"]["name"])

        try:
            logger.info(
                f"[PROCESSING] Starting {CALC_REQ_EVENT_TYPE} - Processor: {processor_name}, "
                f"EntityId: {data['entityId']}, RequestId: {data.get('requestId')}"
            )

            # Use processor_manager from services
            processor_manager = services.processor_manager if services else None
            if not processor_manager:
                raise HandlerError(
                    handler_name="CalcRequestHandler",
                    event_type=request.type,
                    event_id=request.id,
                    message="processor_manager not available in services",
                )

            entity = await processor_manager.process_entity(
                processor_name=processor_name, entity=entity
            )

            # Convert entity back to dict for response
            data["payload"]["data"] = entity.to_dict()
            logger.info(
                f"[PROCESSING] Success {CALC_REQ_EVENT_TYPE} - "
                f"Processor: {processor_name}, EntityId: {data['entityId']}"
            )

        except Exception as e:
            logger.error(
                f"[PROCESSING] Error {CALC_REQ_EVENT_TYPE} - Processor: {processor_name}, EntityId: {data['entityId']}"
            )

            # Convert to proper error
            processing_error = ProcessingError(
                processor_name=processor_name,
                entity_id=data["entityId"],
                message=str(e),
                original_error=e,
            )

            # Mark entity as failed using metadata
            entity.add_metadata("failed", True)
            entity.add_metadata("error_message", str(e))
            entity.add_metadata("error_details", processing_error.to_dict())
            entity.set_state("FAILED")

            # Convert entity back to dict for response
            data["payload"]["data"] = entity.to_dict()

            # Re-raise the error to be handled by error middleware
            raise processing_error

        return ResponseSpec(
            response_type=CALC_RESP_EVENT_TYPE,
            data={
                "requestId": data.get("requestId"),
                "entityId": data.get("entityId"),
                "payload": data.get("payload"),
            },
            success=True,
        )
