import logging
from typing import Any, Dict

from quart import Blueprint, jsonify, request
from quart.typing import ResponseReturnValue
from quart_schema import operation_id, tag, validate

from application.entity.risk import Risk
from application.models import RiskRequest, RiskResponse, ErrorResponse
from services.services import get_entity_service

logger = logging.getLogger(__name__)


class _ServiceProxy:
    def __getattr__(self, name: str) -> Any:
        return getattr(get_entity_service(), name)


service = _ServiceProxy()

risks_bp = Blueprint("risks", __name__, url_prefix="/api/risks")


@risks_bp.route("", methods=["POST"])
@tag(["risks"])
@operation_id("create_risk")
@validate(
    request=RiskRequest,
    responses={201: (RiskResponse, None), 400: (ErrorResponse, None)},
)
async def create_risk(data: RiskRequest) -> ResponseReturnValue:
    """Create new risk control."""
    try:
        entity_data = data.model_dump(by_alias=True)
        response = await service.save(
            entity=entity_data,
            entity_class=Risk.ENTITY_NAME,
            entity_version=str(Risk.ENTITY_VERSION),
        )
        logger.info(f"Created risk control for {data.symbol}")
        return _to_dict(response.data), 201
    except Exception as e:
        logger.error(f"Error creating risk control: {str(e)}")
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500


@risks_bp.route("/<entity_id>", methods=["GET"])
@tag(["risks"])
@operation_id("get_risk")
@validate(responses={200: (RiskResponse, None), 404: (ErrorResponse, None)})
async def get_risk(entity_id: str) -> ResponseReturnValue:
    """Get risk control by ID."""
    try:
        response = await service.get_by_id(
            entity_id=entity_id,
            entity_class=Risk.ENTITY_NAME,
            entity_version=str(Risk.ENTITY_VERSION),
        )
        if not response:
            return {"error": "Not found"}, 404
        return _to_dict(response.data), 200
    except Exception as e:
        logger.error(f"Error getting risk control: {str(e)}")
        return {"error": str(e)}, 500


@risks_bp.route("", methods=["GET"])
@tag(["risks"])
@operation_id("list_risks")
@validate(responses={200: (Dict[str, Any], None)})
async def list_risks() -> ResponseReturnValue:
    """List all risk controls."""
    try:
        results = await service.find_all(
            entity_class=Risk.ENTITY_NAME,
            entity_version=str(Risk.ENTITY_VERSION),
        )
        entities = [_to_dict(r.data) for r in results]
        return {"entities": entities, "total": len(entities)}, 200
    except Exception as e:
        logger.error(f"Error listing risk controls: {str(e)}")
        return {"error": str(e)}, 500


@risks_bp.route("/<entity_id>", methods=["PUT"])
@tag(["risks"])
@operation_id("update_risk")
@validate(
    request=RiskRequest,
    responses={200: (RiskResponse, None), 404: (ErrorResponse, None)},
)
async def update_risk(entity_id: str, data: RiskRequest) -> ResponseReturnValue:
    """Update risk control."""
    try:
        entity_data = data.model_dump(by_alias=True)
        response = await service.update(
            entity_id=entity_id,
            entity=entity_data,
            entity_class=Risk.ENTITY_NAME,
            entity_version=str(Risk.ENTITY_VERSION),
        )
        logger.info(f"Updated risk control {entity_id}")
        return _to_dict(response.data), 200
    except Exception as e:
        logger.error(f"Error updating risk control: {str(e)}")
        return {"error": str(e)}, 500


@risks_bp.route("/<entity_id>", methods=["DELETE"])
@tag(["risks"])
@operation_id("delete_risk")
@validate(responses={200: (Dict[str, Any], None)})
async def delete_risk(entity_id: str) -> ResponseReturnValue:
    """Delete risk control by ID."""
    try:
        await service.delete_by_id(
            entity_id=entity_id,
            entity_class=Risk.ENTITY_NAME,
            entity_version=str(Risk.ENTITY_VERSION),
        )
        logger.info(f"Deleted risk control {entity_id}")
        return {"success": True, "message": "Deleted"}, 200
    except Exception as e:
        logger.error(f"Error deleting risk control: {str(e)}")
        return {"error": str(e)}, 500


def _to_dict(data: Any) -> Dict[str, Any]:
    """Convert entity to dict."""
    return data.model_dump(by_alias=True) if hasattr(data, "model_dump") else data

