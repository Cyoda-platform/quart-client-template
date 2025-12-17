from typing import Any, Dict, Tuple

from quart import Blueprint

from application.entity.trade.version_1.trade import Trade
from services.services import get_entity_service

trade_routes = Blueprint("trade_routes", __name__, url_prefix="/api/trades")


@trade_routes.route("/<entity_id>", methods=["GET"])
async def get_trade(entity_id: str) -> Tuple[Dict[str, Any], int]:
    """
    Retrieves a trade by its ID.
    """
    entity_service = get_entity_service()
    trade = await entity_service.get_by_id(
        entity_id, Trade.ENTITY_NAME, Trade.ENTITY_VERSION
    )
    if trade:
        return trade.data.model_dump(), 200
    return {}, 404
