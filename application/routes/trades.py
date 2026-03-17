"""
Trade management routes for institutional trading platform.

Provides REST API endpoints for trade capture and reporting.
"""

import logging
from typing import Any

from quart import Blueprint
from quart_schema import validate_request, validate_response

from application.entity.trade.version_1.trade import Trade
from services.services import get_entity_service

logger = logging.getLogger(__name__)

trades_bp = Blueprint("trades", __name__, url_prefix="/api/trades")


class _ServiceProxy:
    """Lazy proxy to avoid initializing services at import time."""

    def __getattr__(self, name: str) -> Any:
        return getattr(get_entity_service(), name)


service = _ServiceProxy()


@trades_bp.post("")
@validate_request(Trade)
@validate_response(Trade, 201)
async def create_trade(data: Trade) -> tuple[dict[str, Any], int]:
    """Capture a new trade."""
    try:
        entity_data = data.model_dump(by_alias=True)
        response = await service.save(
            entity=entity_data,
            entity_class=Trade.ENTITY_NAME,
            entity_version=str(Trade.ENTITY_VERSION),
        )
        logger.info(f"Captured trade: {response.metadata.id}")
        return response.data, 201
    except Exception as e:
        logger.error(f"Error capturing trade: {str(e)}")
        return {"error": str(e)}, 400


@trades_bp.get("/<trade_id>")
@validate_response(Trade, 200)
async def get_trade(trade_id: str) -> tuple[dict[str, Any], int]:
    """Get trade by ID."""
    try:
        response = await service.get(
            entity_id=trade_id,
            entity_class=Trade.ENTITY_NAME,
        )
        return response.data, 200
    except Exception as e:
        logger.error(f"Error getting trade: {str(e)}")
        return {"error": str(e)}, 404


@trades_bp.put("/<trade_id>")
@validate_request(Trade)
@validate_response(Trade, 200)
async def update_trade(trade_id: str, data: Trade) -> tuple[dict[str, Any], int]:
    """Update a trade."""
    try:
        entity_data = data.model_dump(by_alias=True)
        response = await service.update(
            entity_id=trade_id,
            entity=entity_data,
            entity_class=Trade.ENTITY_NAME,
        )
        logger.info(f"Updated trade: {trade_id}")
        return response.data, 200
    except Exception as e:
        logger.error(f"Error updating trade: {str(e)}")
        return {"error": str(e)}, 400


@trades_bp.post("/<trade_id>/transitions/<transition_name>")
async def transition_trade(
    trade_id: str, transition_name: str
) -> tuple[dict[str, Any], int]:
    """Trigger a workflow transition on a trade."""
    try:
        response = await service.transition(
            entity_id=trade_id,
            transition_name=transition_name,
            entity_class=Trade.ENTITY_NAME,
        )
        logger.info(f"Transitioned trade {trade_id} to {transition_name}")
        return response.data, 200
    except Exception as e:
        logger.error(f"Error transitioning trade: {str(e)}")
        return {"error": str(e)}, 400
