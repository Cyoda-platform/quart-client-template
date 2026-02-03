"""
MarketData Routes for Institutional Trading Platform

Manages all MarketDataTick-related API endpoints.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from quart import Blueprint
from quart.typing import ResponseReturnValue
from quart_schema import operation_id, tag, validate

from common.exception import is_not_found
from services.services import get_entity_service

from application.entity.market_data_tick.version_1.market_data_tick import MarketDataTick


class _ServiceProxy:
    def __getattr__(self, name: str) -> Any:
        return getattr(get_entity_service(), name)


service = _ServiceProxy()
logger = logging.getLogger(__name__)


def _to_entity_dict(data: Any) -> Dict[str, Any]:
    return data.model_dump(by_alias=True) if hasattr(data, "model_dump") else data


market_data_bp = Blueprint("market_data", __name__, url_prefix="/api/market-data")


@market_data_bp.route("", methods=["POST"])
@tag(["market-data"])
@operation_id("create_market_data_tick")
@validate(request=MarketDataTick, responses={201: (dict, None), 400: (dict, None), 500: (dict, None)})
async def create_market_data_tick(data: MarketDataTick) -> ResponseReturnValue:
    """Create a new market data tick"""
    try:
        entity_data = data.model_dump(by_alias=True)
        response = await service.save(
            entity=entity_data,
            entity_class=MarketDataTick.ENTITY_NAME,
            entity_version=str(MarketDataTick.ENTITY_VERSION),
        )
        return _to_entity_dict(response.data), 201
    except Exception as e:
        logger.error(f"Error creating market data tick: {str(e)}")
        return {"error": str(e)}, 500


@market_data_bp.route("/<entity_id>", methods=["GET"])
@tag(["market-data"])
@operation_id("get_market_data_tick")
@validate(responses={200: (dict, None), 404: (dict, None), 500: (dict, None)})
async def get_market_data_tick(entity_id: str) -> ResponseReturnValue:
    """Get a market data tick by ID"""
    try:
        response = await service.get(
            entity_id=entity_id,
            entity_class=MarketDataTick.ENTITY_NAME,
            entity_version=str(MarketDataTick.ENTITY_VERSION),
        )
        if is_not_found(response):
            return {"error": "Market data tick not found"}, 404
        return _to_entity_dict(response.data), 200
    except Exception as e:
        logger.error(f"Error getting market data tick: {str(e)}")
        return {"error": str(e)}, 500


@market_data_bp.route("", methods=["GET"])
@tag(["market-data"])
@operation_id("list_market_data_ticks")
@validate(responses={200: (dict, None), 500: (dict, None)})
async def list_market_data_ticks() -> ResponseReturnValue:
    """List all market data ticks"""
    try:
        response = await service.list(
            entity_class=MarketDataTick.ENTITY_NAME,
            entity_version=str(MarketDataTick.ENTITY_VERSION),
            limit=100,
            offset=0,
        )
        return {"marketDataTicks": [_to_entity_dict(item) for item in response.data]}, 200
    except Exception as e:
        logger.error(f"Error listing market data ticks: {str(e)}")
        return {"error": str(e)}, 500


@market_data_bp.route("/<entity_id>/transition", methods=["POST"])
@tag(["market-data"])
@operation_id("transition_market_data_tick")
@validate(request=dict, responses={200: (dict, None), 400: (dict, None), 500: (dict, None)})
async def transition_market_data_tick(entity_id: str, data: dict) -> ResponseReturnValue:
    """Trigger a workflow transition on a market data tick"""
    try:
        transition_name = data.get("transitionName")
        if not transition_name:
            return {"error": "transitionName is required"}, 400

        response = await service.transition(
            entity_id=entity_id,
            entity_class=MarketDataTick.ENTITY_NAME,
            entity_version=str(MarketDataTick.ENTITY_VERSION),
            transition_name=transition_name,
        )
        return _to_entity_dict(response.data), 200
    except Exception as e:
        logger.error(f"Error transitioning market data tick: {str(e)}")
        return {"error": str(e)}, 500

