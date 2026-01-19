"""
Claim Routes for Claims Platform Application

Manages all Claim-related API endpoints including CRUD operations
and workflow transitions as specified in functional requirements.
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
    validate_querystring,
)

from common.service.entity_service import SearchConditionRequest
from services.services import get_entity_service

from ..entity.claim import Claim

logger = logging.getLogger(__name__)


class _ServiceProxy:
    def __getattr__(self, name: str) -> Any:
        return getattr(get_entity_service(), name)


service = _ServiceProxy()


def _to_entity_dict(data: Any) -> Dict[str, Any]:
    return data.model_dump(by_alias=True) if hasattr(data, "model_dump") else data


claims_bp = Blueprint("claims", __name__, url_prefix="/api/claims")


@claims_bp.route("", methods=["POST"])
@tag(["claims"])
@operation_id("create_claim")
@validate(
    request=Claim,
    responses={
        201: (Dict[str, Any], None),
        400: (Dict[str, Any], None),
        500: (Dict[str, Any], None),
    },
)
async def create_claim(data: Claim) -> ResponseReturnValue:
    """Create a new claim with comprehensive validation"""
    try:
        entity_data = data.model_dump(by_alias=True)
        response = await service.save(
            entity=entity_data,
            entity_class=Claim.ENTITY_NAME,
            entity_version=str(Claim.ENTITY_VERSION),
        )
        logger.info("Created Claim with ID: %s", response.metadata.id)
        return _to_entity_dict(response.data), 201
    except ValueError as e:
        logger.warning("Validation error creating Claim: %s", str(e))
        return {"error": str(e), "code": "VALIDATION_ERROR"}, 400
    except Exception as e:
        logger.exception("Error creating Claim: %s", str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500


@claims_bp.route("/<entity_id>", methods=["GET"])
@tag(["claims"])
@operation_id("get_claim")
@validate(
    responses={
        200: (Dict[str, Any], None),
        404: (Dict[str, Any], None),
        400: (Dict[str, Any], None),
        500: (Dict[str, Any], None),
    }
)
async def get_claim(entity_id: str) -> ResponseReturnValue:
    """Get Claim by ID with validation"""
    try:
        if not entity_id or len(entity_id.strip()) == 0:
            return {"error": "Entity ID is required", "code": "INVALID_ID"}, 400

        response = await service.get_by_id(
            entity_id=entity_id,
            entity_class=Claim.ENTITY_NAME,
            entity_version=str(Claim.ENTITY_VERSION),
        )

        if not response:
            return {"error": "Claim not found", "code": "NOT_FOUND"}, 404

        return _to_entity_dict(response.data), 200
    except ValueError as e:
        logger.warning("Invalid entity ID %s: %s", entity_id, str(e))
        return {"error": str(e), "code": "INVALID_ID"}, 400
    except Exception as e:
        logger.exception("Error getting Claim %s: %s", entity_id, str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500


@claims_bp.route("", methods=["GET"])
@tag(["claims"])
@operation_id("list_claims")
@validate(
    responses={
        200: (Dict[str, Any], None),
        400: (Dict[str, Any], None),
        500: (Dict[str, Any], None),
    }
)
async def list_claims() -> ResponseReturnValue:
    """List all claims with optional filtering and pagination"""
    try:
        limit = request.args.get("limit", default=50, type=int)
        offset = request.args.get("offset", default=0, type=int)

        entities = await service.find_all(
            entity_class=Claim.ENTITY_NAME,
            entity_version=str(Claim.ENTITY_VERSION),
        )

        entity_list = [_to_entity_dict(r.data) for r in entities]
        start = offset
        end = start + limit
        paginated_entities = entity_list[start:end]

        return jsonify({"entities": paginated_entities, "total": len(entity_list)}), 200
    except Exception as e:
        logger.exception("Error listing Claims: %s", str(e))
        return jsonify({"error": str(e)}), 500


@claims_bp.route("/<entity_id>", methods=["PUT"])
@tag(["claims"])
@operation_id("update_claim")
@validate(
    request=Claim,
    responses={
        200: (Dict[str, Any], None),
        404: (Dict[str, Any], None),
        400: (Dict[str, Any], None),
        500: (Dict[str, Any], None),
    },
)
async def update_claim(entity_id: str, data: Claim) -> ResponseReturnValue:
    """Update Claim and optionally trigger workflow transition"""
    try:
        if not entity_id or len(entity_id.strip()) == 0:
            return {"error": "Entity ID is required", "code": "INVALID_ID"}, 400

        transition: Optional[str] = request.args.get("transition")
        entity_data: Dict[str, Any] = data.model_dump(by_alias=True)

        response = await service.update(
            entity_id=entity_id,
            entity=entity_data,
            entity_class=Claim.ENTITY_NAME,
            transition=transition,
            entity_version=str(Claim.ENTITY_VERSION),
        )

        logger.info("Updated Claim %s", entity_id)
        return jsonify(_to_entity_dict(response.data)), 200
    except ValueError as e:
        logger.warning("Validation error updating Claim %s: %s", entity_id, str(e))
        return jsonify({"error": str(e), "code": "VALIDATION_ERROR"}), 400
    except Exception as e:
        logger.exception("Error updating Claim %s: %s", entity_id, str(e))
        return jsonify({"error": str(e), "code": "INTERNAL_ERROR"}), 500


@claims_bp.route("/<entity_id>", methods=["DELETE"])
@tag(["claims"])
@operation_id("delete_claim")
@validate(
    responses={
        200: (Dict[str, Any], None),
        404: (Dict[str, Any], None),
        400: (Dict[str, Any], None),
        500: (Dict[str, Any], None),
    }
)
async def delete_claim(entity_id: str) -> ResponseReturnValue:
    """Delete Claim with validation"""
    try:
        if not entity_id or len(entity_id.strip()) == 0:
            return {"error": "Entity ID is required", "code": "INVALID_ID"}, 400

        await service.delete_by_id(
            entity_id=entity_id,
            entity_class=Claim.ENTITY_NAME,
            entity_version=str(Claim.ENTITY_VERSION),
        )

        logger.info("Deleted Claim %s", entity_id)
        return {
            "success": True,
            "message": "Claim deleted successfully",
            "entity_id": entity_id,
        }, 200
    except ValueError as e:
        logger.warning("Invalid entity ID %s: %s", entity_id, str(e))
        return {"error": str(e), "code": "INVALID_ID"}, 400
    except Exception as e:
        logger.exception("Error deleting Claim %s: %s", entity_id, str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500


@claims_bp.route("/<entity_id>/transitions", methods=["GET"])
@tag(["claims"])
@operation_id("get_claim_transitions")
@validate(
    responses={
        200: (Dict[str, Any], None),
        404: (Dict[str, Any], None),
        500: (Dict[str, Any], None),
    }
)
async def get_claim_transitions(entity_id: str) -> ResponseReturnValue:
    """Get available workflow transitions for Claim"""
    try:
        transitions = await service.get_transitions(
            entity_id=entity_id,
            entity_class=Claim.ENTITY_NAME,
            entity_version=str(Claim.ENTITY_VERSION),
        )

        return (
            jsonify(
                {
                    "entity_id": entity_id,
                    "available_transitions": transitions,
                    "current_state": None,
                }
            ),
            200,
        )
    except Exception as e:
        logger.exception(
            "Error getting transitions for Claim %s: %s", entity_id, str(e)
        )
        return jsonify({"error": str(e)}), 500


@claims_bp.route("/<entity_id>/transition", methods=["POST"])
@tag(["claims"])
@operation_id("trigger_claim_transition")
@validate(
    responses={
        200: (Dict[str, Any], None),
        404: (Dict[str, Any], None),
        400: (Dict[str, Any], None),
        500: (Dict[str, Any], None),
    },
)
async def trigger_claim_transition(entity_id: str) -> ResponseReturnValue:
    """Trigger a specific workflow transition"""
    try:
        json_data = await request.json
        transition_name = json_data.get("transition_name") if json_data else None
        if not transition_name:
            return {
                "error": "transition_name is required",
                "code": "MISSING_FIELD",
            }, 400

        current_entity = await service.get_by_id(
            entity_id=entity_id,
            entity_class=Claim.ENTITY_NAME,
            entity_version=str(Claim.ENTITY_VERSION),
        )

        if not current_entity:
            return jsonify({"error": "Claim not found"}), 404

        previous_state = current_entity.metadata.state

        response = await service.execute_transition(
            entity_id=entity_id,
            transition=transition_name,
            entity_class=Claim.ENTITY_NAME,
            entity_version=str(Claim.ENTITY_VERSION),
        )

        logger.info("Executed transition '%s' on Claim %s", transition_name, entity_id)

        return (
            jsonify(
                {
                    "id": response.metadata.id,
                    "message": "Transition executed successfully",
                    "previousState": previous_state,
                    "newState": response.metadata.state,
                }
            ),
            200,
        )
    except Exception as e:
        logger.exception(
            "Error executing transition on Claim %s: %s", entity_id, str(e)
        )
        return jsonify({"error": str(e)}), 500
