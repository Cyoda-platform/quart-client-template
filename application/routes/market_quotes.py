"""
Market quote management API routes for the trading platform.

Provides REST endpoints for market quote CRUD operations.
"""

import logging
from typing import Any, Dict

from quart import Blueprint, jsonify, request
from quart_schema import validate_request, validate_response

from application.entity.market_quote.version_1.market_quote import MarketQuote
from services.services import get_entity_service

logger = logging.getLogger(__name__)

market_quotes_bp = Blueprint("market_quotes", __name__, url_prefix="/api/market-quotes")


@market_quotes_bp.route("", methods=["POST"])
@validate_request(MarketQuote)
@validate_response(MarketQuote, status_code=201)
async def create_market_quote(data: MarketQuote) -> tuple[Dict[str, Any], int]:
    """Create a new market quote."""
    try:
        entity_service = get_entity_service()
        quote_data = data.model_dump(by_alias=True)
        response = await entity_service.save(
            entity=quote_data,
            entity_class=MarketQuote.ENTITY_NAME,
            entity_version=str(MarketQuote.ENTITY_VERSION),
        )
        quote_data["id"] = response.metadata.id
        quote_data["state"] = response.metadata.state
        logger.info(f"Market quote created: {response.metadata.id}")
        return quote_data, 201
    except Exception as e:
        logger.error(f"Failed to create market quote: {str(e)}")
        return {"error": str(e)}, 400


@market_quotes_bp.route("/<quote_id>", methods=["GET"])
async def get_market_quote(quote_id: str) -> tuple[Dict[str, Any], int]:
    """Get market quote by technical ID."""
    try:
        entity_service = get_entity_service()
        response = await entity_service.get_by_id(
            entity_id=quote_id,
            entity_class=MarketQuote.ENTITY_NAME,
            entity_version=str(MarketQuote.ENTITY_VERSION),
        )
        quote_data = response.entity.model_dump(by_alias=True)
        quote_data["id"] = response.metadata.id
        quote_data["state"] = response.metadata.state
        return quote_data, 200
    except Exception as e:
        logger.error(f"Failed to get market quote: {str(e)}")
        return {"error": str(e)}, 404


@market_quotes_bp.route("/<quote_id>", methods=["PUT"])
@validate_request(MarketQuote)
async def update_market_quote(
    quote_id: str, data: MarketQuote
) -> tuple[Dict[str, Any], int]:
    """Update a market quote."""
    try:
        entity_service = get_entity_service()
        quote_data = data.model_dump(by_alias=True)
        response = await entity_service.save(
            entity=quote_data,
            entity_class=MarketQuote.ENTITY_NAME,
            entity_version=str(MarketQuote.ENTITY_VERSION),
        )
        quote_data["id"] = response.metadata.id
        quote_data["state"] = response.metadata.state
        logger.info(f"Market quote updated: {quote_id}")
        return quote_data, 200
    except Exception as e:
        logger.error(f"Failed to update market quote: {str(e)}")
        return {"error": str(e)}, 400


@market_quotes_bp.route("/<quote_id>", methods=["DELETE"])
async def delete_market_quote(quote_id: str) -> tuple[Dict[str, str], int]:
    """Delete a market quote."""
    try:
        entity_service = get_entity_service()
        await entity_service.delete_by_id(
            entity_id=quote_id,
            entity_class=MarketQuote.ENTITY_NAME,
            entity_version=str(MarketQuote.ENTITY_VERSION),
        )
        logger.info(f"Market quote deleted: {quote_id}")
        return {"message": "Market quote deleted successfully"}, 200
    except Exception as e:
        logger.error(f"Failed to delete market quote: {str(e)}")
        return {"error": str(e)}, 400
