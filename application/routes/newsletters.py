"""
Newsletter Routes for the newsletter application.

Manages all Newsletter-related API endpoints including creation and status.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from quart import Blueprint
from quart.typing import ResponseReturnValue
from quart_schema import operation_id, tag, validate

from application.entity.newsletter import Newsletter
from services.services import get_entity_service


class _ServiceProxy:
    def __getattr__(self, name: str) -> Any:
        return getattr(get_entity_service(), name)


service = _ServiceProxy()
logger = logging.getLogger(__name__)


def _to_entity_dict(data: Any) -> Dict[str, Any]:
    return data.model_dump(by_alias=True) if hasattr(data, "model_dump") else data


newsletters_bp = Blueprint("newsletters", __name__, url_prefix="/api/newsletters")


@newsletters_bp.route("", methods=["POST"])
@tag(["newsletters"])
@operation_id("create_newsletter")
@validate(
    request=Newsletter,
    responses={
        201: (Dict[str, Any], None),
        400: (Dict[str, Any], None),
        500: (Dict[str, Any], None),
    },
)
async def create_newsletter(data: Newsletter) -> ResponseReturnValue:
    """Create a new newsletter"""
    try:
        entity_data = data.model_dump(by_alias=True)

        response = await service.save(
            entity=entity_data,
            entity_class=Newsletter.ENTITY_NAME,
            entity_version=str(Newsletter.ENTITY_VERSION),
        )

        logger.info("Created Newsletter with ID: %s", response.metadata.id)
        return _to_entity_dict(response.data), 201

    except ValueError as e:
        logger.warning("Validation error creating Newsletter: %s", str(e))
        return {"error": str(e), "code": "VALIDATION_ERROR"}, 400
    except Exception as e:
        logger.exception("Error creating Newsletter: %s", str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500


@newsletters_bp.route("/<entity_id>", methods=["GET"])
@tag(["newsletters"])
@operation_id("get_newsletter")
@validate(
    responses={
        200: (Dict[str, Any], None),
        404: (Dict[str, Any], None),
        400: (Dict[str, Any], None),
        500: (Dict[str, Any], None),
    }
)
async def get_newsletter(entity_id: str) -> ResponseReturnValue:
    """Get Newsletter by ID"""
    try:
        if not entity_id or len(entity_id.strip()) == 0:
            return {"error": "Entity ID is required", "code": "INVALID_ID"}, 400

        response = await service.get_by_id(
            entity_id=entity_id,
            entity_class=Newsletter.ENTITY_NAME,
            entity_version=str(Newsletter.ENTITY_VERSION),
        )

        if not response:
            return {"error": "Newsletter not found", "code": "NOT_FOUND"}, 404

        return _to_entity_dict(response.data), 200

    except ValueError as e:
        logger.warning("Invalid entity ID %s: %s", entity_id, str(e))
        return {"error": str(e), "code": "INVALID_ID"}, 400
    except Exception as e:
        logger.exception("Error getting Newsletter %s: %s", entity_id, str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500


@newsletters_bp.route("", methods=["GET"])
@tag(["newsletters"])
@operation_id("list_newsletters")
@validate(
    responses={
        200: (Dict[str, Any], None),
        500: (Dict[str, Any], None),
    }
)
async def list_newsletters() -> ResponseReturnValue:
    """List all newsletters"""
    try:
        results = await service.find_all(
            entity_class=Newsletter.ENTITY_NAME,
            entity_version=str(Newsletter.ENTITY_VERSION),
        )

        entities = [_to_entity_dict(r.data) for r in results]
        return {"entities": entities, "total": len(entities)}, 200

    except Exception as e:
        logger.exception("Error listing Newsletters: %s", str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500
