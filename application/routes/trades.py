"""
Trade Routes for Trading Platform

Manages all Trade-related API endpoints.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from quart import Blueprint, jsonify, request
from quart.typing import ResponseReturnValue
from quart_schema import operation_id, tag, validate

from common.exception import is_not_found
from services.services import get_entity_service
from application.entity.trade.version_1.trade import Trade

logger = logging.getLogger(__name__)


class _ServiceProxy:
    def __getattr__(self, name: str) -> Any:
        return getattr(get_entity_service(), name)


service = _ServiceProxy()


def _to_entity_dict(data: Any) -> Dict[str, Any]:
    return data.model_dump(by_alias=True) if hasattr(data, "model_dump") else data


trades_bp = Blueprint("trades", __name__, url_prefix="/api/trades")


@trades_bp.route("", methods=["POST"])
@tag(["trades"])
@operation_id("create_trade")
@validate(request=Trade, responses={201: (dict, None), 400: (dict, None), 500: (dict, None)})
async def create_trade(data: Trade) -> ResponseReturnValue:
    """Create a new trade"""
    try:
        entity_data = data.model_dump(by_alias=True)
        response = await service.save(
            entity=entity_data,
            entity_class=Trade.ENTITY_NAME,
            entity_version=str(Trade.ENTITY_VERSION),
        )
        logger.info(f"Created trade with ID: {response.metadata.id}")
        return _to_entity_dict(response.data), 201
    except Exception as e:
        logger.error(f"Error creating trade: {str(e)}")
        return {"error": str(e)}, 500


@trades_bp.route("/<entity_id>", methods=["GET"])
@tag(["trades"])
@operation_id("get_trade")
@validate(responses={200: (dict, None), 404: (dict, None), 500: (dict, None)})
async def get_trade(entity_id: str) -> ResponseReturnValue:
    """Get a trade by ID"""
    try:
        response = await service.get(
            entity_id=entity_id,
            entity_class=Trade.ENTITY_NAME,
        )
        if is_not_found(response):
            return {"error": "Trade not found"}, 404
        return _to_entity_dict(response.data), 200
    except Exception as e:
        logger.error(f"Error getting trade: {str(e)}")
        return {"error": str(e)}, 500


@trades_bp.route("", methods=["GET"])
@tag(["trades"])
@operation_id("list_trades")
@validate(responses={200: (dict, None), 500: (dict, None)})
async def list_trades() -> ResponseReturnValue:
    """List all trades"""
    try:
        response = await service.list(
            entity_class=Trade.ENTITY_NAME,
            limit=100,
            offset=0,
        )
        trades = [_to_entity_dict(item) for item in response.data]
        return {"trades": trades, "total": len(trades)}, 200
    except Exception as e:
        logger.error(f"Error listing trades: {str(e)}")
        return {"error": str(e)}, 500

