import logging
from typing import Any, Dict

from quart import Blueprint
from quart.typing import ResponseReturnValue
from quart_schema import operation_id, tag, validate

from application.entity.trade.version_1.trade import Trade
from services.services import get_entity_service

logger = logging.getLogger(__name__)

trades_bp = Blueprint("trades", __name__, url_prefix="/api/trades")


def _to_entity_dict(data: Any) -> Dict[str, Any]:
    return data.model_dump(by_alias=True) if hasattr(data, "model_dump") else data


@trades_bp.route("", methods=["POST"])
@tag(["trades"])
@operation_id("create_trade")
@validate(request=Trade, responses={201: (Dict[str, Any], None)})
async def create_trade(data: Trade) -> ResponseReturnValue:
    """Create a new trade"""
    try:
        entity_data = data.model_dump(by_alias=True)
        response = await get_entity_service().save(
            entity=entity_data,
            entity_class=Trade.ENTITY_NAME,
            entity_version=str(Trade.ENTITY_VERSION),
        )
        logger.info(f"Created trade {response.metadata.id}")
        return _to_entity_dict(response.data), 201
    except Exception as e:
        logger.exception(f"Error creating trade: {str(e)}")
        return {"error": str(e)}, 400


@trades_bp.route("/<trade_id>", methods=["GET"])
@tag(["trades"])
@operation_id("get_trade")
@validate(responses={200: (Dict[str, Any], None)})
async def get_trade(trade_id: str) -> ResponseReturnValue:
    """Get trade by ID"""
    try:
        response = await get_entity_service().get_by_id(
            entity_id=trade_id,
            entity_class=Trade.ENTITY_NAME,
            entity_version=str(Trade.ENTITY_VERSION),
        )
        if not response:
            return {"error": "Trade not found"}, 404
        return _to_entity_dict(response.data), 200
    except Exception as e:
        logger.exception(f"Error getting trade: {str(e)}")
        return {"error": str(e)}, 400


@trades_bp.route("", methods=["GET"])
@tag(["trades"])
@operation_id("list_trades")
@validate(responses={200: (Dict[str, Any], None)})
async def list_trades() -> ResponseReturnValue:
    """List all trades"""
    try:
        entities = await get_entity_service().find_all(
            entity_class=Trade.ENTITY_NAME,
            entity_version=str(Trade.ENTITY_VERSION),
        )
        entity_list = [_to_entity_dict(r.data) for r in entities]
        return {"trades": entity_list, "total": len(entity_list)}, 200
    except Exception as e:
        logger.exception(f"Error listing trades: {str(e)}")
        return {"error": str(e)}, 400
