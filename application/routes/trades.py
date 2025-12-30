"""
Trade routes for institutional trading platform.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from quart import Blueprint, jsonify, request
from quart.typing import ResponseReturnValue
from quart_schema import operation_id, tag, validate

from application.entity.trade import Trade
from common.exception import is_not_found
from services.services import get_entity_service

logger = logging.getLogger(__name__)

trades_bp = Blueprint("trades", __name__, url_prefix="/api/trades")


class _ServiceProxy:
    def __getattr__(self, name: str) -> Any:
        return getattr(get_entity_service(), name)


service = _ServiceProxy()


def _to_entity_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """Convert entity data to response format."""
    return data if isinstance(data, dict) else data.model_dump(by_alias=True)


@trades_bp.route("", methods=["POST"])
@tag(["trades"])
@operation_id("create_trade")
@validate(request=Trade)
async def create_trade(data: Trade) -> ResponseReturnValue:
    """Create a new Trade"""
    try:
        entity_data = data.model_dump(by_alias=True)
        response = await service.save(
            entity=entity_data,
            entity_class=Trade.ENTITY_NAME,
            entity_version=str(Trade.ENTITY_VERSION),
        )
        logger.info("Created Trade with ID: %s", response.metadata.id)
        return _to_entity_dict(response.data), 201
    except Exception as e:
        logger.error("Error creating trade: %s", str(e))
        return {"error": str(e)}, 500


@trades_bp.route("/<entity_id>", methods=["GET"])
@tag(["trades"])
@operation_id("get_trade")
async def get_trade(entity_id: str) -> ResponseReturnValue:
    """Get a Trade by ID"""
    try:
        response = await service.get(
            entity_id=entity_id,
            entity_class=Trade.ENTITY_NAME,
        )
        if is_not_found(response):
            return {"error": "Not found"}, 404
        return _to_entity_dict(response.data), 200
    except Exception as e:
        logger.error("Error getting trade: %s", str(e))
        return {"error": str(e)}, 500


@trades_bp.route("", methods=["GET"])
@tag(["trades"])
@operation_id("list_trades")
async def list_trades() -> ResponseReturnValue:
    """List all Trades"""
    try:
        response = await service.list(
            entity_class=Trade.ENTITY_NAME,
        )
        return {"data": response.data}, 200
    except Exception as e:
        logger.error("Error listing trades: %s", str(e))
        return {"error": str(e)}, 500
