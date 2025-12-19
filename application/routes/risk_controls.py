import logging
from typing import Any, Dict

from quart import Blueprint
from quart.typing import ResponseReturnValue
from quart_schema import operation_id, tag, validate

from application.entity.risk_control.version_1.risk_control import RiskControl
from services.services import get_entity_service

logger = logging.getLogger(__name__)

risk_controls_bp = Blueprint("risk_controls", __name__, url_prefix="/api/risk-controls")


def _to_entity_dict(data: Any) -> Dict[str, Any]:
    return data.model_dump(by_alias=True) if hasattr(data, "model_dump") else data


@risk_controls_bp.route("", methods=["POST"])
@tag(["risk-controls"])
@operation_id("create_risk_control")
@validate(request=RiskControl, responses={201: (Dict[str, Any], None)})
async def create_risk_control(data: RiskControl) -> ResponseReturnValue:
    """Create a new risk control rule"""
    try:
        entity_data = data.model_dump(by_alias=True)
        response = await get_entity_service().save(
            entity=entity_data,
            entity_class=RiskControl.ENTITY_NAME,
            entity_version=str(RiskControl.ENTITY_VERSION),
        )
        logger.info(f"Created risk control {response.metadata.id}")
        return _to_entity_dict(response.data), 201
    except Exception as e:
        logger.exception(f"Error creating risk control: {str(e)}")
        return {"error": str(e)}, 400


@risk_controls_bp.route("/<control_id>", methods=["GET"])
@tag(["risk-controls"])
@operation_id("get_risk_control")
@validate(responses={200: (Dict[str, Any], None)})
async def get_risk_control(control_id: str) -> ResponseReturnValue:
    """Get risk control by ID"""
    try:
        response = await get_entity_service().get_by_id(
            entity_id=control_id,
            entity_class=RiskControl.ENTITY_NAME,
            entity_version=str(RiskControl.ENTITY_VERSION),
        )
        if not response:
            return {"error": "Risk control not found"}, 404
        return _to_entity_dict(response.data), 200
    except Exception as e:
        logger.exception(f"Error getting risk control: {str(e)}")
        return {"error": str(e)}, 400


@risk_controls_bp.route("", methods=["GET"])
@tag(["risk-controls"])
@operation_id("list_risk_controls")
@validate(responses={200: (Dict[str, Any], None)})
async def list_risk_controls() -> ResponseReturnValue:
    """List all risk controls"""
    try:
        entities = await get_entity_service().find_all(
            entity_class=RiskControl.ENTITY_NAME,
            entity_version=str(RiskControl.ENTITY_VERSION),
        )
        entity_list = [_to_entity_dict(r.data) for r in entities]
        return {"risk_controls": entity_list, "total": len(entity_list)}, 200
    except Exception as e:
        logger.exception(f"Error listing risk controls: {str(e)}")
        return {"error": str(e)}, 400
