"""
LimitRule management API routes for the trading platform.

Provides REST endpoints for LimitRule CRUD operations.
"""

import logging
from typing import Any, Dict

from quart import Blueprint
from quart_schema import validate_request, validate_response

from application.entity.limit_rule.version_1.limit_rule import LimitRule
from services.services import get_entity_service

logger = logging.getLogger(__name__)

limit_rules_bp = Blueprint("limit_rules", __name__, url_prefix="/api/limit_rules")


@limit_rules_bp.route("", methods=["POST"])
@validate_request(LimitRule)
@validate_response(LimitRule, status_code=201)
async def create_limitrule(data: LimitRule) -> tuple[Dict[str, Any], int]:
    """Create a new LimitRule."""
    try:
        entity_service = get_entity_service()
        limitrule_data = data.model_dump(by_alias=True)
        response = await entity_service.save(
            entity=limitrule_data,
            entity_class=LimitRule.ENTITY_NAME,
            entity_version=str(LimitRule.ENTITY_VERSION),
        )
        limitrule_data["id"] = response.metadata.id
        limitrule_data["state"] = response.metadata.state
        logger.info(f"LimitRule created: {response.metadata.id}")
        return limitrule_data, 201
    except Exception as e:
        logger.error(f"Failed to create LimitRule: {str(e)}")
        return {"error": str(e)}, 400


@limit_rules_bp.route("/<limitrule_id>", methods=["GET"])
async def get_limitrule(limitrule_id: str) -> tuple[Dict[str, Any], int]:
    """Get LimitRule by technical ID."""
    try:
        entity_service = get_entity_service()
        response = await entity_service.get_by_id(
            entity_id=limitrule_id,
            entity_class=LimitRule.ENTITY_NAME,
            entity_version=str(LimitRule.ENTITY_VERSION),
        )
        if response is None:
            return {"error": "LimitRule not found"}, 404
        limitrule_data = response.entity.model_dump(by_alias=True)
        limitrule_data["id"] = response.metadata.id
        limitrule_data["state"] = response.metadata.state
        return limitrule_data, 200
    except Exception as e:
        logger.error(f"Failed to get LimitRule: {str(e)}")
        return {"error": str(e)}, 404


@limit_rules_bp.route("/<limitrule_id>", methods=["PUT"])
@validate_request(LimitRule)
async def update_limitrule(
    limitrule_id: str, data: LimitRule
) -> tuple[Dict[str, Any], int]:
    """Update a LimitRule."""
    try:
        entity_service = get_entity_service()
        limitrule_data = data.model_dump(by_alias=True)
        response = await entity_service.update(
            entity=limitrule_data,
            entity_class=LimitRule.ENTITY_NAME,
            entity_version=str(LimitRule.ENTITY_VERSION),
        )
        limitrule_data["id"] = response.metadata.id
        limitrule_data["state"] = response.metadata.state
        logger.info(f"LimitRule updated: {limitrule_id}")
        return limitrule_data, 200
    except Exception as e:
        logger.error(f"Failed to update LimitRule: {str(e)}")
        return {"error": str(e)}, 400


@limit_rules_bp.route("/<limitrule_id>", methods=["DELETE"])
async def delete_limitrule(limitrule_id: str) -> tuple[Dict[str, str], int]:
    """Delete a LimitRule."""
    try:
        entity_service = get_entity_service()
        await entity_service.delete_by_id(
            entity_id=limitrule_id,
            entity_class=LimitRule.ENTITY_NAME,
            entity_version=str(LimitRule.ENTITY_VERSION),
        )
        logger.info(f"LimitRule deleted: {limitrule_id}")
        return {"message": "LimitRule deleted successfully"}, 200
    except Exception as e:
        logger.error(f"Failed to delete LimitRule: {str(e)}")
        return {"error": str(e)}, 400
