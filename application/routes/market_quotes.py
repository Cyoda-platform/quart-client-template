"""
MarketQuote Routes for Trading Platform

Manages all MarketQuote-related API endpoints.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from quart import Blueprint
from quart.typing import ResponseReturnValue
from quart_schema import operation_id, tag, validate

from common.exception import is_not_found
from services.services import get_entity_service
from application.entity.market_quote.version_1.market_quote import MarketQuote

logger = logging.getLogger(__name__)


class _ServiceProxy:
    def __getattr__(self, name: str) -> Any:
        return getattr(get_entity_service(), name)


service = _ServiceProxy()


def _to_entity_dict(data: Any) -> Dict[str, Any]:
    return data.model_dump(by_alias=True) if hasattr(data, "model_dump") else data


market_quotes_bp = Blueprint("market_quotes", __name__, url_prefix="/api/market-quotes")


@market_quotes_bp.route("", methods=["POST"])
@tag(["market-quotes"])
@operation_id("create_market_quote")
@validate(request=MarketQuote, responses={201: (dict, None), 400: (dict, None), 500: (dict, None)})
async def create_market_quote(data: MarketQuote) -> ResponseReturnValue:
    """Create a new market quote"""
    try:
        entity_data = data.model_dump(by_alias=True)
        response = await service.save(
            entity=entity_data,
            entity_class=MarketQuote.ENTITY_NAME,
            entity_version=str(MarketQuote.ENTITY_VERSION),
        )
        logger.info(f"Created market quote with ID: {response.metadata.id}")
        return _to_entity_dict(response.data), 201
    except Exception as e:
        logger.error(f"Error creating market quote: {str(e)}")
        return {"error": str(e)}, 500


@market_quotes_bp.route("/<entity_id>", methods=["GET"])
@tag(["market-quotes"])
@operation_id("get_market_quote")
@validate(responses={200: (dict, None), 404: (dict, None), 500: (dict, None)})
async def get_market_quote(entity_id: str) -> ResponseReturnValue:
    """Get a market quote by ID"""
    try:
        response = await service.get(
            entity_id=entity_id,
            entity_class=MarketQuote.ENTITY_NAME,
        )
        if is_not_found(response):
            return {"error": "Market quote not found"}, 404
        return _to_entity_dict(response.data), 200
    except Exception as e:
        logger.error(f"Error getting market quote: {str(e)}")
        return {"error": str(e)}, 500


@market_quotes_bp.route("", methods=["GET"])
@tag(["market-quotes"])
@operation_id("list_market_quotes")
@validate(responses={200: (dict, None), 500: (dict, None)})
async def list_market_quotes() -> ResponseReturnValue:
    """List all market quotes"""
    try:
        response = await service.list(
            entity_class=MarketQuote.ENTITY_NAME,
            limit=100,
            offset=0,
        )
        quotes = [_to_entity_dict(item) for item in response.data]
        return {"quotes": quotes, "total": len(quotes)}, 200
    except Exception as e:
        logger.error(f"Error listing market quotes: {str(e)}")
        return {"error": str(e)}, 500

