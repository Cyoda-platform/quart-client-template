"""
Limit rule management API routes for the trading platform.

Provides REST endpoints for limit rule CRUD operations.
"""

import logging
from typing import Any, Dict

from quart import Blueprint, jsonify, request
from quart_schema import validate_request, validate_response

from application.entity.limit_rule.version_1.limit_rule import LimitRule
from services.services import get_entity_service

logger = logging.getLogger(__name__)

limit_rules_bp = Blueprint("limit_rules", __name__, url_prefix="/api/limit-rules")


@limit_rules_bp.route("", methods=["POST"])
@validate_request(LimitRule)
@validate_response(LimitRule, status_code=201)
async def create_limit_rule(data: LimitRule) -> tuple[Dict[str, Any], int]:
    """Create a new limit rule."""
    try:
        entity_service = get_entity_service()
        rule_data = data.model_dump(by_alias=True)
        response = await entity_service.save(
            entity=rule_data,
            entity_class=LimitRule.ENTITY_NAME,
            entity_version=str(LimitRule.ENTITY_VERSION),
        )
        rule_data["id"] = response.metadata.id
        rule_data["state"] = response.metadata.state
        logger.info(f"Limit rule created: {response.metadata.id}")
        return rule_data, 201
    except Exception as e:
        logger.error(f"Failed to create limit rule: {str(e)}")
        return {"error": str(e)}, 400


@limit_rules_bp.route("/<rule_id>", methods=["GET"])
async def get_limit_rule(rule_id: str) -> tuple[Dict[str, Any], int]:
    """Get limit rule by technical ID."""
    try:
        entity_service = get_entity_service()
        response = await entity_service.get_by_id(
            entity_id=rule_id,
            entity_class=LimitRule.ENTITY_NAME,
            entity_version=str(LimitRule.ENTITY_VERSION),
        )
        rule_data = response.entity.model_dump(by_alias=True)
        rule_data["id"] = response.metadata.id
        rule_data["state"] = response.metadata.state
        return rule_data, 200
    except Exception as e:
        logger.error(f"Failed to get limit rule: {str(e)}")
        return {"error": str(e)}, 404


@limit_rules_bp.route("/<rule_id>", methods=["PUT"])
@validate_request(LimitRule)
async def update_limit_rule(
    rule_id: str, data: LimitRule
) -> tuple[Dict[str, Any], int]:
    """Update a limit rule."""
    try:
        entity_service = get_entity_service()
        rule_data = data.model_dump(by_alias=True)
        response = await entity_service.save(
            entity=rule_data,
            entity_class=LimitRule.ENTITY_NAME,
            entity_version=str(LimitRule.ENTITY_VERSION),
        )
        rule_data["id"] = response.metadata.id
        rule_data["state"] = response.metadata.state
        logger.info(f"Limit rule updated: {rule_id}")
        return rule_data, 200
    except Exception as e:
        logger.error(f"Failed to update limit rule: {str(e)}")
        return {"error": str(e)}, 400


@limit_rules_bp.route("/<rule_id>", methods=["DELETE"])
async def delete_limit_rule(rule_id: str) -> tuple[Dict[str, str], int]:
    """Delete a limit rule."""
    try:
        entity_service = get_entity_service()
        await entity_service.delete_by_id(
            entity_id=rule_id,
            entity_class=LimitRule.ENTITY_NAME,
            entity_version=str(LimitRule.ENTITY_VERSION),
        )
        logger.info(f"Limit rule deleted: {rule_id}")
        return {"message": "Limit rule deleted successfully"}, 200
    except Exception as e:
        logger.error(f"Failed to delete limit rule: {str(e)}")
        return {"error": str(e)}, 400
