"""
MarketQuote management API routes for the trading platform.

Provides REST endpoints for MarketQuote CRUD operations.
"""

import logging
from typing import Any, Dict

from quart import Blueprint
from quart_schema import validate_request, validate_response

from application.entity.market_quote.version_1.market_quote import MarketQuote
from services.services import get_entity_service

logger = logging.getLogger(__name__)

market_quotes_bp = Blueprint("market_quotes", __name__, url_prefix="/api/market_quotes")


@market_quotes_bp.route("", methods=["POST"])
@validate_request(MarketQuote)
@validate_response(MarketQuote, status_code=201)
async def create_marketquote(data: MarketQuote) -> tuple[Dict[str, Any], int]:
    """Create a new MarketQuote."""
    try:
        entity_service = get_entity_service()
        marketquote_data = data.model_dump(by_alias=True)
        response = await entity_service.save(
            entity=marketquote_data,
            entity_class=MarketQuote.ENTITY_NAME,
            entity_version=str(MarketQuote.ENTITY_VERSION),
        )
        marketquote_data["id"] = response.metadata.id
        marketquote_data["state"] = response.metadata.state
        logger.info(f"MarketQuote created: {response.metadata.id}")
        return marketquote_data, 201
    except Exception as e:
        logger.error(f"Failed to create MarketQuote: {str(e)}")
        return {"error": str(e)}, 400


@market_quotes_bp.route("/<marketquote_id>", methods=["GET"])
async def get_marketquote(marketquote_id: str) -> tuple[Dict[str, Any], int]:
    """Get MarketQuote by technical ID."""
    try:
        entity_service = get_entity_service()
        response = await entity_service.get_by_id(
            entity_id=marketquote_id,
            entity_class=MarketQuote.ENTITY_NAME,
            entity_version=str(MarketQuote.ENTITY_VERSION),
        )
        if response is None:
            return {"error": "MarketQuote not found"}, 404
        marketquote_data = response.entity.model_dump(by_alias=True)
        marketquote_data["id"] = response.metadata.id
        marketquote_data["state"] = response.metadata.state
        return marketquote_data, 200
    except Exception as e:
        logger.error(f"Failed to get MarketQuote: {str(e)}")
        return {"error": str(e)}, 404


@market_quotes_bp.route("/<marketquote_id>", methods=["PUT"])
@validate_request(MarketQuote)
async def update_marketquote(
    marketquote_id: str, data: MarketQuote
) -> tuple[Dict[str, Any], int]:
    """Update a MarketQuote."""
    try:
        entity_service = get_entity_service()
        marketquote_data = data.model_dump(by_alias=True)
        response = await entity_service.update(
            entity=marketquote_data,
            entity_class=MarketQuote.ENTITY_NAME,
            entity_version=str(MarketQuote.ENTITY_VERSION),
        )
        marketquote_data["id"] = response.metadata.id
        marketquote_data["state"] = response.metadata.state
        logger.info(f"MarketQuote updated: {marketquote_id}")
        return marketquote_data, 200
    except Exception as e:
        logger.error(f"Failed to update MarketQuote: {str(e)}")
        return {"error": str(e)}, 400


@market_quotes_bp.route("/<marketquote_id>", methods=["DELETE"])
async def delete_marketquote(marketquote_id: str) -> tuple[Dict[str, str], int]:
    """Delete a MarketQuote."""
    try:
        entity_service = get_entity_service()
        await entity_service.delete_by_id(
            entity_id=marketquote_id,
            entity_class=MarketQuote.ENTITY_NAME,
            entity_version=str(MarketQuote.ENTITY_VERSION),
        )
        logger.info(f"MarketQuote deleted: {marketquote_id}")
        return {"message": "MarketQuote deleted successfully"}, 200
    except Exception as e:
        logger.error(f"Failed to delete MarketQuote: {str(e)}")
        return {"error": str(e)}, 400
