"""
RiskControl Routes for Institutional Trading Platform

Manages all RiskControl-related API endpoints.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from quart import Blueprint, jsonify, request
from quart.typing import ResponseReturnValue
from quart_schema import operation_id, tag, validate

from application.entity.risk_control import RiskControl
from services.services import get_entity_service

logger = logging.getLogger(__name__)


class _ServiceProxy:
    def __getattr__(self, name: str) -> Any:
        return getattr(get_entity_service(), name)


service = _ServiceProxy()


def _to_entity_dict(data: Any) -> Dict[str, Any]:
    return data.model_dump(by_alias=True) if hasattr(data, "model_dump") else data


risk_controls_bp = Blueprint("risk_controls", __name__, url_prefix="/api/risk-controls")


@risk_controls_bp.route("", methods=["POST"])
@tag(["risk-controls"])
@operation_id("create_risk_control")
@validate(
    request=RiskControl,
    responses={201: (Dict[str, Any], None), 400: (Dict[str, Any], None)},
)
async def create_risk_control(data: RiskControl) -> ResponseReturnValue:
    """Create a new RiskControl"""
    try:
        entity_data = data.model_dump(by_alias=True)
        response = await service.save(
            entity=entity_data,
            entity_class=RiskControl.ENTITY_NAME,
            entity_version=str(RiskControl.ENTITY_VERSION),
        )
        logger.info("Created RiskControl with ID: %s", response.metadata.id)
        return _to_entity_dict(response.data), 201
    except ValueError as e:
        logger.warning("Validation error creating RiskControl: %s", str(e))
        return {"error": str(e), "code": "VALIDATION_ERROR"}, 400
    except Exception as e:
        logger.exception("Error creating RiskControl: %s", str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500


@risk_controls_bp.route("/<entity_id>", methods=["GET"])
@tag(["risk-controls"])
@operation_id("get_risk_control")
@validate(responses={200: (Dict[str, Any], None), 404: (Dict[str, Any], None)})
async def get_risk_control(entity_id: str) -> ResponseReturnValue:
    """Get RiskControl by ID"""
    try:
        if not entity_id or len(entity_id.strip()) == 0:
            return {"error": "Entity ID is required", "code": "INVALID_ID"}, 400

        response = await service.get_by_id(
            entity_id=entity_id,
            entity_class=RiskControl.ENTITY_NAME,
            entity_version=str(RiskControl.ENTITY_VERSION),
        )

        if not response:
            return {"error": "RiskControl not found", "code": "NOT_FOUND"}, 404

        return _to_entity_dict(response.data), 200
    except Exception as e:
        logger.exception("Error getting RiskControl %s: %s", entity_id, str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500


@risk_controls_bp.route("", methods=["GET"])
@tag(["risk-controls"])
@operation_id("list_risk_controls")
@validate(responses={200: (Dict[str, Any], None), 500: (Dict[str, Any], None)})
async def list_risk_controls() -> ResponseReturnValue:
    """List all RiskControls"""
    try:
        entities = await service.find_all(
            entity_class=RiskControl.ENTITY_NAME,
            entity_version=str(RiskControl.ENTITY_VERSION),
        )
        entity_list = [_to_entity_dict(r.data) for r in entities]
        return jsonify({"entities": entity_list, "total": len(entity_list)}), 200
    except Exception as e:
        logger.exception("Error listing RiskControls: %s", str(e))
        return jsonify({"error": str(e)}), 500


@risk_controls_bp.route("/<entity_id>", methods=["PUT"])
@tag(["risk-controls"])
@operation_id("update_risk_control")
@validate(
    request=RiskControl,
    responses={200: (Dict[str, Any], None), 404: (Dict[str, Any], None)},
)
async def update_risk_control(entity_id: str, data: RiskControl) -> ResponseReturnValue:
    """Update RiskControl"""
    try:
        if not entity_id or len(entity_id.strip()) == 0:
            return {"error": "Entity ID is required", "code": "INVALID_ID"}, 400

        entity_data: Dict[str, Any] = data.model_dump(by_alias=True)
        transition: Optional[str] = request.args.get("transition")

        response = await service.update(
            entity_id=entity_id,
            entity=entity_data,
            entity_class=RiskControl.ENTITY_NAME,
            transition=transition,
            entity_version=str(RiskControl.ENTITY_VERSION),
        )

        logger.info("Updated RiskControl %s", entity_id)
        return jsonify(_to_entity_dict(response.data)), 200
    except Exception as e:
        logger.exception("Error updating RiskControl %s: %s", entity_id, str(e))
        return jsonify({"error": str(e), "code": "INTERNAL_ERROR"}), 500


@risk_controls_bp.route("/<entity_id>", methods=["DELETE"])
@tag(["risk-controls"])
@operation_id("delete_risk_control")
@validate(responses={200: (Dict[str, Any], None), 404: (Dict[str, Any], None)})
async def delete_risk_control(entity_id: str) -> ResponseReturnValue:
    """Delete RiskControl"""
    try:
        if not entity_id or len(entity_id.strip()) == 0:
            return {"error": "Entity ID is required", "code": "INVALID_ID"}, 400

        await service.delete_by_id(
            entity_id=entity_id,
            entity_class=RiskControl.ENTITY_NAME,
            entity_version=str(RiskControl.ENTITY_VERSION),
        )

        logger.info("Deleted RiskControl %s", entity_id)
        return {
            "success": True,
            "message": "RiskControl deleted successfully",
            "entity_id": entity_id,
        }, 200
    except Exception as e:
        logger.exception("Error deleting RiskControl %s: %s", entity_id, str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500


@risk_controls_bp.route("/<entity_id>/transitions", methods=["GET"])
@tag(["risk-controls"])
@operation_id("get_risk_control_transitions")
@validate(responses={200: (Dict[str, Any], None), 500: (Dict[str, Any], None)})
async def get_risk_control_transitions(entity_id: str) -> ResponseReturnValue:
    """Get available transitions for RiskControl"""
    try:
        transitions = await service.get_transitions(
            entity_id=entity_id,
            entity_class=RiskControl.ENTITY_NAME,
            entity_version=str(RiskControl.ENTITY_VERSION),
        )
        return (
            jsonify({"entity_id": entity_id, "available_transitions": transitions}),
            200,
        )
    except Exception as e:
        logger.exception(
            "Error getting transitions for RiskControl %s: %s", entity_id, str(e)
        )
        return jsonify({"error": str(e)}), 500


@risk_controls_bp.route("/<entity_id>/transitions", methods=["POST"])
@tag(["risk-controls"])
@operation_id("trigger_risk_control_transition")
@validate(responses={200: (Dict[str, Any], None), 500: (Dict[str, Any], None)})
async def trigger_risk_control_transition(entity_id: str) -> ResponseReturnValue:
    """Trigger workflow transition for RiskControl"""
    try:
        transition_name = request.args.get("transition")
        if not transition_name:
            return {"error": "transition parameter required"}, 400

        response = await service.execute_transition(
            entity_id=entity_id,
            transition=transition_name,
            entity_class=RiskControl.ENTITY_NAME,
            entity_version=str(RiskControl.ENTITY_VERSION),
        )

        logger.info(
            "Executed transition '%s' on RiskControl %s", transition_name, entity_id
        )
        return (
            jsonify(
                {
                    "id": response.metadata.id,
                    "message": "Transition executed successfully",
                    "newState": response.metadata.state,
                }
            ),
            200,
        )
    except Exception as e:
        logger.exception(
            "Error executing transition on RiskControl %s: %s", entity_id, str(e)
        )
        return jsonify({"error": str(e)}), 500
