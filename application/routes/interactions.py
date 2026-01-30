"""
Interaction Routes for Weekly Cat Fact Subscription Application

Manages all Interaction-related API endpoints including CRUD operations
and tracking event recording.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from quart import Blueprint
from quart.typing import ResponseReturnValue
from quart_schema import operation_id, tag, validate

from application.entity.interaction.version_1.interaction import Interaction
from services.services import get_entity_service


class _ServiceProxy:
    def __getattr__(self, name: str) -> Any:
        return getattr(get_entity_service(), name)


service = _ServiceProxy()
logger = logging.getLogger(__name__)


def _to_entity_dict(data: Any) -> Dict[str, Any]:
    return data.model_dump(by_alias=True) if hasattr(data, "model_dump") else data


interactions_bp = Blueprint("interactions", __name__, url_prefix="/api/interactions")


@interactions_bp.route("", methods=["POST"])
@tag(["interactions"])
@operation_id("create_interaction")
@validate(
    request=Interaction,
    responses={
        201: (dict, None),
        400: (dict, None),
        500: (dict, None),
    },
)
async def create_interaction(data: Interaction) -> ResponseReturnValue:
    """Create a new Interaction (tracking event)"""
    try:
        entity_data = data.model_dump(by_alias=True)
        response = await service.save(
            entity=entity_data,
            entity_class=Interaction.ENTITY_NAME,
            entity_version=str(Interaction.ENTITY_VERSION),
        )
        logger.info("Created Interaction with ID: %s", response.metadata.id)
        return _to_entity_dict(response.data), 201
    except ValueError as e:
        logger.warning("Validation error: %s", str(e))
        return {"error": str(e), "code": "VALIDATION_ERROR"}, 400
    except Exception as e:
        logger.exception("Error creating Interaction: %s", str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500


@interactions_bp.route("/<entity_id>", methods=["GET"])
@tag(["interactions"])
@operation_id("get_interaction")
@validate(
    responses={
        200: (dict, None),
        404: (dict, None),
        500: (dict, None),
    }
)
async def get_interaction(entity_id: str) -> ResponseReturnValue:
    """Get Interaction by ID"""
    try:
        if not entity_id or len(entity_id.strip()) == 0:
            return {"error": "Entity ID is required", "code": "INVALID_ID"}, 400

        response = await service.get_by_id(
            entity_id=entity_id,
            entity_class=Interaction.ENTITY_NAME,
            entity_version=str(Interaction.ENTITY_VERSION),
        )

        if not response:
            return {"error": "Interaction not found", "code": "NOT_FOUND"}, 404

        return _to_entity_dict(response.data), 200
    except Exception as e:
        logger.exception("Error getting Interaction: %s", str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500


@interactions_bp.route("/<entity_id>", methods=["DELETE"])
@tag(["interactions"])
@operation_id("delete_interaction")
@validate(
    responses={
        200: (dict, None),
        404: (dict, None),
        500: (dict, None),
    }
)
async def delete_interaction(entity_id: str) -> ResponseReturnValue:
    """Delete Interaction by ID"""
    try:
        if not entity_id or len(entity_id.strip()) == 0:
            return {"error": "Entity ID is required", "code": "INVALID_ID"}, 400

        await service.delete(
            entity_id=entity_id,
            entity_class=Interaction.ENTITY_NAME,
            entity_version=str(Interaction.ENTITY_VERSION),
        )

        return {"message": "Interaction deleted successfully"}, 200
    except Exception as e:
        logger.exception("Error deleting Interaction: %s", str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500
