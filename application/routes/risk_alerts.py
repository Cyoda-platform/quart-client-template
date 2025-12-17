import logging
from typing import Any, Dict

from quart import Blueprint, jsonify, request
from quart.typing import ResponseReturnValue
from quart_schema import operation_id, tag, validate

from application.entity.risk_alert.version_1.risk_alert import RiskAlert
from services.services import get_entity_service

logger = logging.getLogger(__name__)


class _ServiceProxy:
    def __getattr__(self, name: str) -> Any:
        return getattr(get_entity_service(), name)


service = _ServiceProxy()


def _to_entity_dict(data: Any) -> Dict[str, Any]:
    return data.model_dump(by_alias=True) if hasattr(data, "model_dump") else data


risk_alerts_bp = Blueprint("risk_alerts", __name__, url_prefix="/api/risk-alerts")


@risk_alerts_bp.route("", methods=["POST"])
@tag(["risk-alerts"])
@operation_id("create_risk_alert")
@validate(
    request=RiskAlert,
    responses={
        201: (Dict[str, Any], None),
        400: (Dict[str, str], None),
        500: (Dict[str, str], None),
    },
)
async def create_risk_alert(data: RiskAlert) -> ResponseReturnValue:
    """Create a new RiskAlert"""
    try:
        entity_data = data.model_dump(by_alias=True)
        response = await service.save(
            entity=entity_data,
            entity_class=RiskAlert.ENTITY_NAME,
            entity_version=str(RiskAlert.ENTITY_VERSION),
        )
        logger.info("Created RiskAlert with ID: %s", response.metadata.id)
        return _to_entity_dict(response.data), 201
    except ValueError as e:
        logger.warning("Validation error creating RiskAlert: %s", str(e))
        return {"error": str(e), "code": "VALIDATION_ERROR"}, 400
    except Exception as e:
        logger.exception("Error creating RiskAlert: %s", str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500


@risk_alerts_bp.route("/<entity_id>", methods=["GET"])
@tag(["risk-alerts"])
@operation_id("get_risk_alert")
@validate(
    responses={
        200: (Dict[str, Any], None),
        404: (Dict[str, str], None),
        500: (Dict[str, str], None),
    }
)
async def get_risk_alert(entity_id: str) -> ResponseReturnValue:
    """Get RiskAlert by ID"""
    try:
        if not entity_id or len(entity_id.strip()) == 0:
            return {"error": "Entity ID is required", "code": "INVALID_ID"}, 400

        response = await service.get_by_id(
            entity_id=entity_id,
            entity_class=RiskAlert.ENTITY_NAME,
            entity_version=str(RiskAlert.ENTITY_VERSION),
        )

        if not response:
            return {"error": "RiskAlert not found", "code": "NOT_FOUND"}, 404

        return _to_entity_dict(response.data), 200
    except Exception as e:
        logger.exception("Error getting RiskAlert %s: %s", entity_id, str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500


@risk_alerts_bp.route("", methods=["GET"])
@tag(["risk-alerts"])
@operation_id("list_risk_alerts")
@validate(
    responses={
        200: (Dict[str, Any], None),
        500: (Dict[str, str], None),
    }
)
async def list_risk_alerts() -> ResponseReturnValue:
    """List all RiskAlerts"""
    try:
        entities = await service.find_all(
            entity_class=RiskAlert.ENTITY_NAME,
            entity_version=str(RiskAlert.ENTITY_VERSION),
        )
        entity_list = [_to_entity_dict(r.data) for r in entities]
        return jsonify({"entities": entity_list, "total": len(entity_list)}), 200
    except Exception as e:
        logger.exception("Error listing RiskAlerts: %s", str(e))
        return jsonify({"error": str(e)}), 500


@risk_alerts_bp.route("/<entity_id>", methods=["PUT"])
@tag(["risk-alerts"])
@operation_id("update_risk_alert")
@validate(
    request=RiskAlert,
    responses={
        200: (Dict[str, Any], None),
        404: (Dict[str, str], None),
        500: (Dict[str, str], None),
    },
)
async def update_risk_alert(entity_id: str, data: RiskAlert) -> ResponseReturnValue:
    """Update RiskAlert"""
    try:
        if not entity_id or len(entity_id.strip()) == 0:
            return {"error": "Entity ID is required", "code": "INVALID_ID"}, 400

        entity_data: Dict[str, Any] = data.model_dump(by_alias=True)
        response = await service.update(
            entity_id=entity_id,
            entity=entity_data,
            entity_class=RiskAlert.ENTITY_NAME,
            entity_version=str(RiskAlert.ENTITY_VERSION),
        )

        logger.info("Updated RiskAlert %s", entity_id)
        return jsonify(_to_entity_dict(response.data)), 200
    except Exception as e:
        logger.exception("Error updating RiskAlert %s: %s", entity_id, str(e))
        return jsonify({"error": str(e), "code": "INTERNAL_ERROR"}), 500


@risk_alerts_bp.route("/<entity_id>", methods=["DELETE"])
@tag(["risk-alerts"])
@operation_id("delete_risk_alert")
@validate(
    responses={
        200: (Dict[str, Any], None),
        404: (Dict[str, str], None),
        500: (Dict[str, str], None),
    }
)
async def delete_risk_alert(entity_id: str) -> ResponseReturnValue:
    """Delete RiskAlert"""
    try:
        if not entity_id or len(entity_id.strip()) == 0:
            return {"error": "Entity ID is required", "code": "INVALID_ID"}, 400

        await service.delete_by_id(
            entity_id=entity_id,
            entity_class=RiskAlert.ENTITY_NAME,
            entity_version=str(RiskAlert.ENTITY_VERSION),
        )

        logger.info("Deleted RiskAlert %s", entity_id)
        return {"success": True, "message": "RiskAlert deleted successfully"}, 200
    except Exception as e:
        logger.exception("Error deleting RiskAlert %s: %s", entity_id, str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500


@risk_alerts_bp.route("/<entity_id>/transitions", methods=["POST"])
@tag(["risk-alerts"])
@operation_id("trigger_risk_alert_transition")
@validate(
    responses={
        200: (Dict[str, Any], None),
        500: (Dict[str, str], None),
    }
)
async def trigger_risk_alert_transition(entity_id: str) -> ResponseReturnValue:
    """Trigger workflow transition for RiskAlert"""
    try:
        data = await request.get_json()
        transition_name = data.get("transition_name")

        if not transition_name:
            return {"error": "transition_name is required"}, 400

        response = await service.execute_transition(
            entity_id=entity_id,
            transition=transition_name,
            entity_class=RiskAlert.ENTITY_NAME,
            entity_version=str(RiskAlert.ENTITY_VERSION),
        )

        logger.info(
            "Executed transition '%s' on RiskAlert %s", transition_name, entity_id
        )
        return (
            jsonify({"id": response.metadata.id, "state": response.metadata.state}),
            200,
        )
    except Exception as e:
        logger.exception(
            "Error executing transition on RiskAlert %s: %s", entity_id, str(e)
        )
        return jsonify({"error": str(e)}), 500
