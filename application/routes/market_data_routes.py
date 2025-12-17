from typing import Any, Dict, Tuple

from quart import Blueprint, request

from application.entity.market_data.version_1.market_data import MarketData
from services.services import get_entity_service

market_data_routes = Blueprint(
    "market_data_routes", __name__, url_prefix="/api/market_data"
)


@market_data_routes.route("/", methods=["POST"])
async def create_market_data() -> Tuple[Dict[str, Any], int]:
    """
    Creates a new market data entity.
    """
    data = await request.get_json()
    entity_service = get_entity_service()
    market_data = await entity_service.save(
        data, MarketData.ENTITY_NAME, MarketData.ENTITY_VERSION
    )
    return market_data.data.model_dump(), 201


@market_data_routes.route("/<entity_id>", methods=["GET"])
async def get_market_data(entity_id: str) -> Tuple[Dict[str, Any], int]:
    """
    Retrieves a market data entity by its ID.
    """
    entity_service = get_entity_service()
    market_data = await entity_service.get_by_id(
        entity_id, MarketData.ENTITY_NAME, MarketData.ENTITY_VERSION
    )
    if market_data:
        return market_data.data.model_dump(), 200
    return {}, 404
