import logging
from typing import Any, Dict

from quart import Blueprint
from quart.typing import ResponseReturnValue
from quart_schema import operation_id, tag, validate

from application.entity.position.version_1.position import Position
from services.services import get_entity_service

logger = logging.getLogger(__name__)

positions_bp = Blueprint("positions", __name__, url_prefix="/api/positions")


def _to_entity_dict(data: Any) -> Dict[str, Any]:
    return data.model_dump(by_alias=True) if hasattr(data, "model_dump") else data


@positions_bp.route("", methods=["POST"])
@tag(["positions"])
@operation_id("create_position")
@validate(request=Position, responses={201: (Dict[str, Any], None)})
async def create_position(data: Position) -> ResponseReturnValue:
    """Create a new position"""
    try:
        entity_data = data.model_dump(by_alias=True)
        response = await get_entity_service().save(
            entity=entity_data,
            entity_class=Position.ENTITY_NAME,
            entity_version=str(Position.ENTITY_VERSION),
        )
        logger.info(f"Created position {response.metadata.id}")
        return _to_entity_dict(response.data), 201
    except Exception as e:
        logger.exception(f"Error creating position: {str(e)}")
        return {"error": str(e)}, 400


@positions_bp.route("/<position_id>", methods=["GET"])
@tag(["positions"])
@operation_id("get_position")
@validate(responses={200: (Dict[str, Any], None)})
async def get_position(position_id: str) -> ResponseReturnValue:
    """Get position by ID"""
    try:
        response = await get_entity_service().get_by_id(
            entity_id=position_id,
            entity_class=Position.ENTITY_NAME,
            entity_version=str(Position.ENTITY_VERSION),
        )
        if not response:
            return {"error": "Position not found"}, 404
        return _to_entity_dict(response.data), 200
    except Exception as e:
        logger.exception(f"Error getting position: {str(e)}")
        return {"error": str(e)}, 400


@positions_bp.route("", methods=["GET"])
@tag(["positions"])
@operation_id("list_positions")
@validate(responses={200: (Dict[str, Any], None)})
async def list_positions() -> ResponseReturnValue:
    """List all positions"""
    try:
        entities = await get_entity_service().find_all(
            entity_class=Position.ENTITY_NAME,
            entity_version=str(Position.ENTITY_VERSION),
        )
        entity_list = [_to_entity_dict(r.data) for r in entities]
        return {"positions": entity_list, "total": len(entity_list)}, 200
    except Exception as e:
        logger.exception(f"Error listing positions: {str(e)}")
        return {"error": str(e)}, 400
