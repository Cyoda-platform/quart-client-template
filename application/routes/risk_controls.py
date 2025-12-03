"""
Risk Control Routes for Trading Platform

Manages all RiskControl-related API endpoints including limit monitoring,
breach management, and risk reporting.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from quart import Blueprint, jsonify, request
from quart.typing import ResponseReturnValue
from quart_schema import operation_id, tag

from common.service.entity_service import SearchConditionRequest
from services.services import get_entity_service
from application.entity.risk_control.version_1.risk_control import RiskControl

logger = logging.getLogger(__name__)

# Service proxy
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
async def create_risk_control() -> ResponseReturnValue:
    """Create a new risk control"""
    try:
        data = await request.get_json()
        
        # Create RiskControl entity
        risk_control = RiskControl(**data)
        entity_data = risk_control.model_dump(by_alias=True)

        # Save the risk control
        response = await service.save(
            entity=entity_data,
            entity_class=RiskControl.ENTITY_NAME,
            entity_version=str(RiskControl.ENTITY_VERSION),
        )

        logger.info("Created RiskControl with ID: %s", response.metadata.id)
        return _to_entity_dict(response.data), 201

    except ValueError as e:
        logger.warning("Validation error creating risk control: %s", str(e))
        return {"error": str(e), "code": "VALIDATION_ERROR"}, 400
    except Exception as e:
        logger.exception("Error creating risk control: %s", str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500

@risk_controls_bp.route("/<control_id>", methods=["GET"])
@tag(["risk-controls"])
@operation_id("get_risk_control")
async def get_risk_control(control_id: str) -> ResponseReturnValue:
    """Get risk control by ID"""
    try:
        response = await service.get_by_id(
            entity_id=control_id,
            entity_class=RiskControl.ENTITY_NAME,
            entity_version=str(RiskControl.ENTITY_VERSION),
        )

        if not response:
            return {"error": "Risk control not found", "code": "NOT_FOUND"}, 404

        return _to_entity_dict(response.data), 200

    except Exception as e:
        logger.exception("Error getting risk control %s: %s", control_id, str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500

@risk_controls_bp.route("", methods=["GET"])
@tag(["risk-controls"])
@operation_id("list_risk_controls")
async def list_risk_controls() -> ResponseReturnValue:
    """List risk controls with optional filtering"""
    try:
        # Get query parameters
        control_type = request.args.get("controlType")
        entity_type = request.args.get("entityType")
        entity_id = request.args.get("entityId")
        is_active = request.args.get("isActive")

        # Build search conditions
        search_conditions = {}
        if control_type:
            search_conditions["controlType"] = control_type
        if entity_type:
            search_conditions["entityType"] = entity_type
        if entity_id:
            search_conditions["entityId"] = entity_id
        if is_active is not None:
            search_conditions["isActive"] = is_active.lower()

        if search_conditions:
            builder = SearchConditionRequest.builder()
            for field, value in search_conditions.items():
                builder.equals(field, value)
            condition = builder.build()

            entities = await service.search(
                entity_class=RiskControl.ENTITY_NAME,
                condition=condition,
                entity_version=str(RiskControl.ENTITY_VERSION),
            )
        else:
            entities = await service.find_all(
                entity_class=RiskControl.ENTITY_NAME,
                entity_version=str(RiskControl.ENTITY_VERSION),
            )

        entity_list = [_to_entity_dict(r.data) for r in entities]
        return {"riskControls": entity_list, "total": len(entity_list)}, 200

    except Exception as e:
        logger.exception("Error listing risk controls: %s", str(e))
        return {"error": str(e)}, 500

@risk_controls_bp.route("/<control_id>/check", methods=["POST"])
@tag(["risk-controls"])
@operation_id("check_risk_control")
async def check_risk_control(control_id: str) -> ResponseReturnValue:
    """Check risk control against current exposure"""
    try:
        response = await service.execute_transition(
            entity_id=control_id,
            transition="check",
            entity_class=RiskControl.ENTITY_NAME,
            entity_version=str(RiskControl.ENTITY_VERSION),
        )

        logger.info("Checked risk control %s", control_id)
        return {
            "id": response.metadata.id,
            "message": "Risk control checked successfully",
            "newState": response.metadata.state,
        }, 200

    except Exception as e:
        logger.exception("Error checking risk control %s: %s", control_id, str(e))
        return {"error": str(e)}, 500

@risk_controls_bp.route("/breaches", methods=["GET"])
@tag(["risk-controls"])
@operation_id("get_risk_breaches")
async def get_risk_breaches() -> ResponseReturnValue:
    """Get all active risk breaches"""
    try:
        builder = SearchConditionRequest.builder()
        builder.equals("status", "BREACHED")
        condition = builder.build()

        entities = await service.search(
            entity_class=RiskControl.ENTITY_NAME,
            condition=condition,
            entity_version=str(RiskControl.ENTITY_VERSION),
        )

        entity_list = [_to_entity_dict(r.data) for r in entities]
        return {"breaches": entity_list, "total": len(entity_list)}, 200

    except Exception as e:
        logger.exception("Error getting risk breaches: %s", str(e))
        return {"error": str(e)}, 500

@risk_controls_bp.route("/<control_id>/acknowledge", methods=["POST"])
@tag(["risk-controls"])
@operation_id("acknowledge_risk_breach")
async def acknowledge_risk_breach(control_id: str) -> ResponseReturnValue:
    """Acknowledge a risk breach"""
    try:
        response = await service.execute_transition(
            entity_id=control_id,
            transition="acknowledge",
            entity_class=RiskControl.ENTITY_NAME,
            entity_version=str(RiskControl.ENTITY_VERSION),
        )

        logger.info("Acknowledged risk breach %s", control_id)
        return {
            "id": response.metadata.id,
            "message": "Risk breach acknowledged successfully",
            "newState": response.metadata.state,
        }, 200

    except Exception as e:
        logger.exception("Error acknowledging risk breach %s: %s", control_id, str(e))
        return {"error": str(e)}, 500

@risk_controls_bp.route("/by-entity/<entity_type>/<entity_id>", methods=["GET"])
@tag(["risk-controls"])
@operation_id("get_risk_controls_by_entity")
async def get_risk_controls_by_entity(entity_type: str, entity_id: str) -> ResponseReturnValue:
    """Get all risk controls for a specific entity"""
    try:
        builder = SearchConditionRequest.builder()
        builder.equals("entityType", entity_type)
        builder.equals("entityId", entity_id)
        condition = builder.build()

        entities = await service.search(
            entity_class=RiskControl.ENTITY_NAME,
            condition=condition,
            entity_version=str(RiskControl.ENTITY_VERSION),
        )

        entity_list = [_to_entity_dict(r.data) for r in entities]
        return {"riskControls": entity_list, "total": len(entity_list)}, 200

    except Exception as e:
        logger.exception("Error getting risk controls for %s %s: %s", entity_type, entity_id, str(e))
        return {"error": str(e)}, 500
