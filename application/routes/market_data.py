"""
Market data routes for institutional trading platform.

Provides REST API endpoints for real-time market data feeds.
"""

import logging
from typing import Any

from quart import Blueprint
from quart_schema import validate_request, validate_response

from application.entity.market_data.version_1.market_data import MarketData
from services.services import get_entity_service

logger = logging.getLogger(__name__)

market_data_bp = Blueprint("market_data", __name__, url_prefix="/api/market-data")


class _ServiceProxy:
    """Lazy proxy to avoid initializing services at import time."""

    def __getattr__(self, name: str) -> Any:
        return getattr(get_entity_service(), name)


service = _ServiceProxy()


@market_data_bp.post("")
@validate_request(MarketData)
@validate_response(MarketData, 201)
async def create_market_data(data: MarketData) -> tuple[dict[str, Any], int]:
    """Create new market data entry."""
    try:
        entity_data = data.model_dump(by_alias=True)
        response = await service.save(
            entity=entity_data,
            entity_class=MarketData.ENTITY_NAME,
            entity_version=str(MarketData.ENTITY_VERSION),
        )
        logger.info(f"Created market data: {response.metadata.id}")
        return response.data, 201
    except Exception as e:
        logger.error(f"Error creating market data: {str(e)}")
        return {"error": str(e)}, 400


@market_data_bp.get("/<market_data_id>")
@validate_response(MarketData, 200)
async def get_market_data(market_data_id: str) -> tuple[dict[str, Any], int]:
    """Get market data by ID."""
    try:
        response = await service.get(
            entity_id=market_data_id,
            entity_class=MarketData.ENTITY_NAME,
        )
        return response.data, 200
    except Exception as e:
        logger.error(f"Error getting market data: {str(e)}")
        return {"error": str(e)}, 404


@market_data_bp.put("/<market_data_id>")
@validate_request(MarketData)
@validate_response(MarketData, 200)
async def update_market_data(
    market_data_id: str, data: MarketData
) -> tuple[dict[str, Any], int]:
    """Update market data."""
    try:
        entity_data = data.model_dump(by_alias=True)
        response = await service.update(
            entity_id=market_data_id,
            entity=entity_data,
            entity_class=MarketData.ENTITY_NAME,
        )
        logger.info(f"Updated market data: {market_data_id}")
        return response.data, 200
    except Exception as e:
        logger.error(f"Error updating market data: {str(e)}")
        return {"error": str(e)}, 400


@market_data_bp.post("/<market_data_id>/transitions/<transition_name>")
async def transition_market_data(
    market_data_id: str, transition_name: str
) -> tuple[dict[str, Any], int]:
    """Trigger a workflow transition on market data."""
    try:
        response = await service.transition(
            entity_id=market_data_id,
            transition_name=transition_name,
            entity_class=MarketData.ENTITY_NAME,
        )
        logger.info(f"Transitioned market data {market_data_id} to {transition_name}")
        return response.data, 200
    except Exception as e:
        logger.error(f"Error transitioning market data: {str(e)}")
        return {"error": str(e)}, 400

