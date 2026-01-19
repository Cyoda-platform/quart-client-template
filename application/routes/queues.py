"""
Queue Routes for Claims Platform Application

Manages all Queue-related API endpoints including CRUD operations
as specified in functional requirements.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from quart import Blueprint, jsonify, request
from quart.typing import ResponseReturnValue
from quart_schema import (
    operation_id,
    tag,
    validate,
)

from services.services import get_entity_service

from ..entity.queue import Queue

logger = logging.getLogger(__name__)


class _ServiceProxy:
    def __getattr__(self, name: str) -> Any:
        return getattr(get_entity_service(), name)


service = _ServiceProxy()


def _to_entity_dict(data: Any) -> Dict[str, Any]:
    return data.model_dump(by_alias=True) if hasattr(data, "model_dump") else data


queues_bp = Blueprint("queues", __name__, url_prefix="/api/queues")


@queues_bp.route("", methods=["POST"])
@tag(["queues"])
@operation_id("create_queue")
@validate(
    request=Queue,
    responses={
        201: (Dict[str, Any], None),
        400: (Dict[str, Any], None),
        500: (Dict[str, Any], None),
    },
)
async def create_queue(data: Queue) -> ResponseReturnValue:
    """Create a new queue with comprehensive validation"""
    try:
        entity_data = data.model_dump(by_alias=True)
        response = await service.save(
            entity=entity_data,
            entity_class=Queue.ENTITY_NAME,
            entity_version=str(Queue.ENTITY_VERSION),
        )
        logger.info("Created Queue with ID: %s", response.metadata.id)
        return _to_entity_dict(response.data), 201
    except ValueError as e:
        logger.warning("Validation error creating Queue: %s", str(e))
        return {"error": str(e), "code": "VALIDATION_ERROR"}, 400
    except Exception as e:
        logger.exception("Error creating Queue: %s", str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500


@queues_bp.route("/<entity_id>", methods=["GET"])
@tag(["queues"])
@operation_id("get_queue")
@validate(
    responses={
        200: (Dict[str, Any], None),
        404: (Dict[str, Any], None),
        400: (Dict[str, Any], None),
        500: (Dict[str, Any], None),
    }
)
async def get_queue(entity_id: str) -> ResponseReturnValue:
    """Get Queue by ID with validation"""
    try:
        if not entity_id or len(entity_id.strip()) == 0:
            return {"error": "Entity ID is required", "code": "INVALID_ID"}, 400

        response = await service.get_by_id(
            entity_id=entity_id,
            entity_class=Queue.ENTITY_NAME,
            entity_version=str(Queue.ENTITY_VERSION),
        )

        if not response:
            return {"error": "Queue not found", "code": "NOT_FOUND"}, 404

        return _to_entity_dict(response.data), 200
    except ValueError as e:
        logger.warning("Invalid entity ID %s: %s", entity_id, str(e))
        return {"error": str(e), "code": "INVALID_ID"}, 400
    except Exception as e:
        logger.exception("Error getting Queue %s: %s", entity_id, str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500


@queues_bp.route("", methods=["GET"])
@tag(["queues"])
@operation_id("list_queues")
@validate(
    responses={
        200: (Dict[str, Any], None),
        400: (Dict[str, Any], None),
        500: (Dict[str, Any], None),
    }
)
async def list_queues() -> ResponseReturnValue:
    """List all queues with optional filtering and pagination"""
    try:
        limit = request.args.get("limit", default=50, type=int)
        offset = request.args.get("offset", default=0, type=int)

        entities = await service.find_all(
            entity_class=Queue.ENTITY_NAME,
            entity_version=str(Queue.ENTITY_VERSION),
        )

        entity_list = [_to_entity_dict(r.data) for r in entities]
        start = offset
        end = start + limit
        paginated_entities = entity_list[start:end]

        return jsonify({"entities": paginated_entities, "total": len(entity_list)}), 200
    except Exception as e:
        logger.exception("Error listing Queues: %s", str(e))
        return jsonify({"error": str(e)}), 500


@queues_bp.route("/<entity_id>", methods=["PUT"])
@tag(["queues"])
@operation_id("update_queue")
@validate(
    request=Queue,
    responses={
        200: (Dict[str, Any], None),
        404: (Dict[str, Any], None),
        400: (Dict[str, Any], None),
        500: (Dict[str, Any], None),
    },
)
async def update_queue(entity_id: str, data: Queue) -> ResponseReturnValue:
    """Update Queue"""
    try:
        if not entity_id or len(entity_id.strip()) == 0:
            return {"error": "Entity ID is required", "code": "INVALID_ID"}, 400

        entity_data: Dict[str, Any] = data.model_dump(by_alias=True)

        response = await service.update(
            entity_id=entity_id,
            entity=entity_data,
            entity_class=Queue.ENTITY_NAME,
            entity_version=str(Queue.ENTITY_VERSION),
        )

        logger.info("Updated Queue %s", entity_id)
        return jsonify(_to_entity_dict(response.data)), 200
    except ValueError as e:
        logger.warning("Validation error updating Queue %s: %s", entity_id, str(e))
        return jsonify({"error": str(e), "code": "VALIDATION_ERROR"}), 400
    except Exception as e:
        logger.exception("Error updating Queue %s: %s", entity_id, str(e))
        return jsonify({"error": str(e), "code": "INTERNAL_ERROR"}), 500


@queues_bp.route("/<entity_id>", methods=["DELETE"])
@tag(["queues"])
@operation_id("delete_queue")
@validate(
    responses={
        200: (Dict[str, Any], None),
        404: (Dict[str, Any], None),
        400: (Dict[str, Any], None),
        500: (Dict[str, Any], None),
    }
)
async def delete_queue(entity_id: str) -> ResponseReturnValue:
    """Delete Queue with validation"""
    try:
        if not entity_id or len(entity_id.strip()) == 0:
            return {"error": "Entity ID is required", "code": "INVALID_ID"}, 400

        await service.delete_by_id(
            entity_id=entity_id,
            entity_class=Queue.ENTITY_NAME,
            entity_version=str(Queue.ENTITY_VERSION),
        )

        logger.info("Deleted Queue %s", entity_id)
        return {
            "success": True,
            "message": "Queue deleted successfully",
            "entity_id": entity_id,
        }, 200
    except ValueError as e:
        logger.warning("Invalid entity ID %s: %s", entity_id, str(e))
        return {"error": str(e), "code": "INVALID_ID"}, 400
    except Exception as e:
        logger.exception("Error deleting Queue %s: %s", entity_id, str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500

