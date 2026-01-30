"""
CatFact Routes for Weekly Cat Fact Subscription Application

Manages all CatFact-related API endpoints including CRUD operations
and workflow transitions.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from quart import Blueprint
from quart.typing import ResponseReturnValue
from quart_schema import operation_id, tag, validate

from application.entity.cat_fact.version_1.cat_fact import CatFact
from services.services import get_entity_service


class _ServiceProxy:
    def __getattr__(self, name: str) -> Any:
        return getattr(get_entity_service(), name)


service = _ServiceProxy()
logger = logging.getLogger(__name__)


def _to_entity_dict(data: Any) -> Dict[str, Any]:
    return data.model_dump(by_alias=True) if hasattr(data, "model_dump") else data


cat_facts_bp = Blueprint("cat_facts", __name__, url_prefix="/api/cat-facts")


@cat_facts_bp.route("", methods=["POST"])
@tag(["cat-facts"])
@operation_id("create_cat_fact")
@validate(
    request=CatFact,
    responses={
        201: (dict, None),
        400: (dict, None),
        500: (dict, None),
    },
)
async def create_cat_fact(data: CatFact) -> ResponseReturnValue:
    """Create a new CatFact entity"""
    try:
        entity_data = data.model_dump(by_alias=True)
        response = await service.save(
            entity=entity_data,
            entity_class=CatFact.ENTITY_NAME,
            entity_version=str(CatFact.ENTITY_VERSION),
        )
        logger.info("Created CatFact with ID: %s", response.metadata.id)
        return _to_entity_dict(response.data), 201
    except ValueError as e:
        logger.warning("Validation error: %s", str(e))
        return {"error": str(e), "code": "VALIDATION_ERROR"}, 400
    except Exception as e:
        logger.exception("Error creating CatFact: %s", str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500


@cat_facts_bp.route("/<entity_id>", methods=["GET"])
@tag(["cat-facts"])
@operation_id("get_cat_fact")
@validate(
    responses={
        200: (dict, None),
        404: (dict, None),
        500: (dict, None),
    }
)
async def get_cat_fact(entity_id: str) -> ResponseReturnValue:
    """Get CatFact by ID"""
    try:
        if not entity_id or len(entity_id.strip()) == 0:
            return {"error": "Entity ID is required", "code": "INVALID_ID"}, 400

        response = await service.get_by_id(
            entity_id=entity_id,
            entity_class=CatFact.ENTITY_NAME,
            entity_version=str(CatFact.ENTITY_VERSION),
        )

        if not response:
            return {"error": "CatFact not found", "code": "NOT_FOUND"}, 404

        return _to_entity_dict(response.data), 200
    except Exception as e:
        logger.exception("Error getting CatFact: %s", str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500


@cat_facts_bp.route("/<entity_id>", methods=["DELETE"])
@tag(["cat-facts"])
@operation_id("delete_cat_fact")
@validate(
    responses={
        200: (dict, None),
        404: (dict, None),
        500: (dict, None),
    }
)
async def delete_cat_fact(entity_id: str) -> ResponseReturnValue:
    """Delete CatFact by ID"""
    try:
        if not entity_id or len(entity_id.strip()) == 0:
            return {"error": "Entity ID is required", "code": "INVALID_ID"}, 400

        await service.delete(
            entity_id=entity_id,
            entity_class=CatFact.ENTITY_NAME,
            entity_version=str(CatFact.ENTITY_VERSION),
        )

        return {"message": "CatFact deleted successfully"}, 200
    except Exception as e:
        logger.exception("Error deleting CatFact: %s", str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500
