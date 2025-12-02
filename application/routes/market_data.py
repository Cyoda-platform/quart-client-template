"""
MarketData Routes for Real-Time Trading Platform

Manages all MarketData-related API endpoints including CRUD operations
and real-time market data streaming.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from quart import Blueprint, jsonify, request
from quart.typing import ResponseReturnValue

from common.exception import is_not_found
from services.services import get_entity_service
from application.entity.market_data.version_1.market_data import MarketData

# Create blueprint for market data routes
market_data_bp = Blueprint("market_data", __name__, url_prefix="/api/market-data")

logger = logging.getLogger(__name__)


@market_data_bp.route("", methods=["POST"])
async def create_market_data() -> ResponseReturnValue:
    """Create new market data entry"""
    try:
        data = await request.get_json()
        if not data:
            return jsonify({"error": "Request body is required"}), 400

        entity_service = get_entity_service()
        
        # Save the market data
        response = await entity_service.save(
            entity=data,
            entity_class=MarketData.ENTITY_NAME,
            entity_version=str(MarketData.ENTITY_VERSION),
        )

        return jsonify({
            "id": response.metadata.id,
            "state": response.metadata.state,
            "message": "Market data created successfully"
        }), 201

    except Exception as e:
        logger.error(f"Error creating market data: {str(e)}")
        return jsonify({"error": "Failed to create market data"}), 500


@market_data_bp.route("/<data_id>", methods=["GET"])
async def get_market_data(data_id: str) -> ResponseReturnValue:
    """Get market data by ID"""
    try:
        entity_service = get_entity_service()
        
        response = await entity_service.get_by_id(
            entity_id=data_id,
            entity_class=MarketData.ENTITY_NAME,
            entity_version=str(MarketData.ENTITY_VERSION),
        )

        if is_not_found(response):
            return jsonify({"error": "Market data not found"}), 404

        return jsonify(response.entity), 200

    except Exception as e:
        logger.error(f"Error getting market data {data_id}: {str(e)}")
        return jsonify({"error": "Failed to get market data"}), 500


@market_data_bp.route("/symbol/<symbol>", methods=["GET"])
async def get_market_data_by_symbol(symbol: str) -> ResponseReturnValue:
    """Get latest market data for a symbol"""
    try:
        entity_service = get_entity_service()
        
        from common.service.entity_service import SearchConditionRequest
        search_request = SearchConditionRequest(
            entity_class=MarketData.ENTITY_NAME,
            entity_version=str(MarketData.ENTITY_VERSION),
            conditions=[{
                "field": "symbol",
                "operator": "EQUALS",
                "value": symbol.upper()
            }]
        )
        
        response = await entity_service.search(search_request)
        
        if not response.entities:
            return jsonify({"error": "Market data not found for symbol"}), 404

        # Return the most recent entry (assuming sorted by timestamp)
        latest_data = response.entities[0]
        return jsonify(latest_data), 200

    except Exception as e:
        logger.error(f"Error getting market data for symbol {symbol}: {str(e)}")
        return jsonify({"error": "Failed to get market data"}), 500


@market_data_bp.route("", methods=["GET"])
async def list_market_data() -> ResponseReturnValue:
    """List market data with optional filtering"""
    try:
        entity_service = get_entity_service()
        
        # Get query parameters
        symbol = request.args.get("symbol")
        exchange = request.args.get("exchange")
        instrument_type = request.args.get("instrument_type")
        market_status = request.args.get("market_status")
        
        # Build search conditions if filters provided
        conditions = []
        if symbol:
            conditions.append({
                "field": "symbol",
                "operator": "EQUALS",
                "value": symbol.upper()
            })
        if exchange:
            conditions.append({
                "field": "exchange",
                "operator": "EQUALS",
                "value": exchange.upper()
            })
        if instrument_type:
            conditions.append({
                "field": "instrumentType",
                "operator": "EQUALS",
                "value": instrument_type
            })
        if market_status:
            conditions.append({
                "field": "marketStatus",
                "operator": "EQUALS",
                "value": market_status
            })

        if conditions:
            from common.service.entity_service import SearchConditionRequest
            search_request = SearchConditionRequest(
                entity_class=MarketData.ENTITY_NAME,
                entity_version=str(MarketData.ENTITY_VERSION),
                conditions=conditions
            )
            response = await entity_service.search(search_request)
            market_data_list = response.entities
        else:
            response = await entity_service.find_all(
                entity_class=MarketData.ENTITY_NAME,
                entity_version=str(MarketData.ENTITY_VERSION),
            )
            market_data_list = response.entities

        return jsonify({
            "market_data": market_data_list,
            "count": len(market_data_list)
        }), 200

    except Exception as e:
        logger.error(f"Error listing market data: {str(e)}")
        return jsonify({"error": "Failed to list market data"}), 500


@market_data_bp.route("/<data_id>", methods=["PUT"])
async def update_market_data(data_id: str) -> ResponseReturnValue:
    """Update market data entry"""
    try:
        data = await request.get_json()
        if not data:
            return jsonify({"error": "Request body is required"}), 400

        entity_service = get_entity_service()
        
        # Get transition if specified
        transition = data.pop("transition", None)
        
        response = await entity_service.update(
            entity_id=data_id,
            entity=data,
            entity_class=MarketData.ENTITY_NAME,
            entity_version=str(MarketData.ENTITY_VERSION),
            transition=transition,
        )

        if is_not_found(response):
            return jsonify({"error": "Market data not found"}), 404

        return jsonify({
            "id": response.metadata.id,
            "state": response.metadata.state,
            "message": "Market data updated successfully"
        }), 200

    except Exception as e:
        logger.error(f"Error updating market data {data_id}: {str(e)}")
        return jsonify({"error": "Failed to update market data"}), 500


@market_data_bp.route("/symbols", methods=["GET"])
async def get_symbols() -> ResponseReturnValue:
    """Get list of available symbols"""
    try:
        entity_service = get_entity_service()
        
        response = await entity_service.find_all(
            entity_class=MarketData.ENTITY_NAME,
            entity_version=str(MarketData.ENTITY_VERSION),
        )

        # Extract unique symbols
        symbols = list(set(data.get("symbol", "") for data in response.entities))
        symbols.sort()

        return jsonify({
            "symbols": symbols,
            "count": len(symbols)
        }), 200

    except Exception as e:
        logger.error(f"Error getting symbols: {str(e)}")
        return jsonify({"error": "Failed to get symbols"}), 500


@market_data_bp.route("/<data_id>", methods=["DELETE"])
async def delete_market_data(data_id: str) -> ResponseReturnValue:
    """Delete market data entry"""
    try:
        entity_service = get_entity_service()
        
        response = await entity_service.delete(
            entity_id=data_id,
            entity_class=MarketData.ENTITY_NAME,
            entity_version=str(MarketData.ENTITY_VERSION),
        )

        if is_not_found(response):
            return jsonify({"error": "Market data not found"}), 404

        return jsonify({"message": "Market data deleted successfully"}), 200

    except Exception as e:
        logger.error(f"Error deleting market data {data_id}: {str(e)}")
        return jsonify({"error": "Failed to delete market data"}), 500
