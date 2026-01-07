"""
Settlement Routes for Enterprise Payment Processing System

Manages all Settlement-related API endpoints.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from quart import Blueprint, jsonify
from quart.typing import ResponseReturnValue
from quart_schema import operation_id, tag, validate

from application.entity.settlement import Settlement
from services.services import get_entity_service


class _ServiceProxy:
    def __getattr__(self, name: str) -> Any:
        return getattr(get_entity_service(), name)


service = _ServiceProxy()
logger = logging.getLogger(__name__)


def _to_entity_dict(data: Any) -> Dict[str, Any]:
    return data.model_dump(by_alias=True) if hasattr(data, "model_dump") else data


settlements_bp = Blueprint("settlements", __name__, url_prefix="/api/settlements")


@settlements_bp.route("", methods=["POST"])
@tag(["settlements"])
@operation_id("create_settlement")
@validate(
    request=Settlement,
    responses={
        201: (Dict[str, Any], None),
        400: (Dict[str, Any], None),
        500: (Dict[str, Any], None),
    },
)
async def create_settlement(
    data: Settlement,
) -> ResponseReturnValue:
    """Create a new Settlement"""
    try:
        entity_data = data.model_dump(by_alias=True)
        response = await service.save(
            entity=entity_data,
            entity_class=Settlement.ENTITY_NAME,
            entity_version=str(Settlement.ENTITY_VERSION),
        )
        logger.info("Created Settlement with ID: %s", response.metadata.id)
        return _to_entity_dict(response.data), 201

    except ValueError as e:
        logger.warning("Validation error creating Settlement: %s", str(e))
        return {"error": str(e), "code": "VALIDATION_ERROR"}, 400
    except Exception as e:
        logger.exception("Error creating Settlement: %s", str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500


@settlements_bp.route("/<entity_id>", methods=["GET"])
@tag(["settlements"])
@operation_id("get_settlement")
@validate(
    responses={
        200: (Dict[str, Any], None),
        404: (Dict[str, Any], None),
        500: (Dict[str, Any], None),
    }
)
async def get_settlement(entity_id: str) -> ResponseReturnValue:
    """Get Settlement by ID"""
    try:
        if not entity_id or len(entity_id.strip()) == 0:
            return {"error": "Entity ID is required", "code": "INVALID_ID"}, 400

        response = await service.get_by_id(
            entity_id=entity_id,
            entity_class=Settlement.ENTITY_NAME,
            entity_version=str(Settlement.ENTITY_VERSION),
        )

        if not response:
            return {"error": "Settlement not found", "code": "NOT_FOUND"}, 404

        return _to_entity_dict(response.data), 200

    except Exception as e:
        logger.exception("Error getting Settlement %s: %s", entity_id, str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500


@settlements_bp.route("", methods=["GET"])
@tag(["settlements"])
@operation_id("list_settlements")
@validate(
    responses={
        200: (Dict[str, Any], None),
        500: (Dict[str, Any], None),
    }
)
async def list_settlements() -> ResponseReturnValue:
    """List all Settlements"""
    try:
        entities = await service.find_all(
            entity_class=Settlement.ENTITY_NAME,
            entity_version=str(Settlement.ENTITY_VERSION),
        )
        entity_list = [_to_entity_dict(r.data) for r in entities]
        return jsonify({"entities": entity_list, "total": len(entity_list)}), 200

    except Exception as e:
        logger.exception("Error listing Settlements: %s", str(e))
        return jsonify({"error": str(e)}), 500


@settlements_bp.route("/<entity_id>", methods=["PUT"])
@tag(["settlements"])
@operation_id("update_settlement")
@validate(
    request=Settlement,
    responses={
        200: (Dict[str, Any], None),
        404: (Dict[str, Any], None),
        500: (Dict[str, Any], None),
    },
)
async def update_settlement(entity_id: str, data: Settlement) -> ResponseReturnValue:
    """Update Settlement"""
    try:
        if not entity_id or len(entity_id.strip()) == 0:
            return {"error": "Entity ID is required", "code": "INVALID_ID"}, 400

        entity_data: Dict[str, Any] = data.model_dump(by_alias=True)
        response = await service.update(
            entity_id=entity_id,
            entity=entity_data,
            entity_class=Settlement.ENTITY_NAME,
            entity_version=str(Settlement.ENTITY_VERSION),
        )

        logger.info("Updated Settlement %s", entity_id)
        return jsonify(_to_entity_dict(response.data)), 200

    except Exception as e:
        logger.exception("Error updating Settlement %s: %s", entity_id, str(e))
        return jsonify({"error": str(e), "code": "INTERNAL_ERROR"}), 500


@settlements_bp.route("/<entity_id>", methods=["DELETE"])
@tag(["settlements"])
@operation_id("delete_settlement")
@validate(
    responses={
        200: (Dict[str, Any], None),
        404: (Dict[str, Any], None),
        500: (Dict[str, Any], None),
    }
)
async def delete_settlement(entity_id: str) -> ResponseReturnValue:
    """Delete Settlement"""
    try:
        if not entity_id or len(entity_id.strip()) == 0:
            return {"error": "Entity ID is required", "code": "INVALID_ID"}, 400

        await service.delete_by_id(
            entity_id=entity_id,
            entity_class=Settlement.ENTITY_NAME,
            entity_version=str(Settlement.ENTITY_VERSION),
        )

        logger.info("Deleted Settlement %s", entity_id)
        return {"success": True, "message": "Settlement deleted successfully"}, 200

    except Exception as e:
        logger.exception("Error deleting Settlement %s: %s", entity_id, str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500
