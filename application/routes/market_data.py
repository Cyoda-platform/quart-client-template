"""
Market Data Routes for Trading Platform

Manages all MarketData-related API endpoints including real-time feeds,
historical data, and data quality monitoring.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from quart import Blueprint, jsonify, request
from quart.typing import ResponseReturnValue
from quart_schema import operation_id, tag

from common.service.entity_service import SearchConditionRequest
from services.services import get_entity_service
from application.entity.market_data.version_1.market_data import MarketData

logger = logging.getLogger(__name__)

# Service proxy
class _ServiceProxy:
    def __getattr__(self, name: str) -> Any:
        return getattr(get_entity_service(), name)

service = _ServiceProxy()

def _to_entity_dict(data: Any) -> Dict[str, Any]:
    return data.model_dump(by_alias=True) if hasattr(data, "model_dump") else data

market_data_bp = Blueprint("market_data", __name__, url_prefix="/api/market-data")

@market_data_bp.route("", methods=["POST"])
@tag(["market-data"])
@operation_id("publish_market_data")
async def publish_market_data() -> ResponseReturnValue:
    """Publish new market data"""
    try:
        data = await request.get_json()
        
        # Create MarketData entity
        market_data = MarketData(**data)
        entity_data = market_data.model_dump(by_alias=True)

        # Save the market data
        response = await service.save(
            entity=entity_data,
            entity_class=MarketData.ENTITY_NAME,
            entity_version=str(MarketData.ENTITY_VERSION),
        )

        logger.info("Published MarketData with ID: %s", response.metadata.id)
        return _to_entity_dict(response.data), 201

    except ValueError as e:
        logger.warning("Validation error publishing market data: %s", str(e))
        return {"error": str(e), "code": "VALIDATION_ERROR"}, 400
    except Exception as e:
        logger.exception("Error publishing market data: %s", str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500

@market_data_bp.route("/<symbol>", methods=["GET"])
@tag(["market-data"])
@operation_id("get_market_data")
async def get_market_data(symbol: str) -> ResponseReturnValue:
    """Get latest market data for a symbol"""
    try:
        builder = SearchConditionRequest.builder()
        builder.equals("symbol", symbol)
        condition = builder.build()

        entities = await service.search(
            entity_class=MarketData.ENTITY_NAME,
            condition=condition,
            entity_version=str(MarketData.ENTITY_VERSION),
        )

        if not entities:
            return {"error": "Market data not found", "code": "NOT_FOUND"}, 404

        # Return most recent data (assuming sorted by timestamp)
        return _to_entity_dict(entities[0].data), 200

    except Exception as e:
        logger.exception("Error getting market data for %s: %s", symbol, str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500

@market_data_bp.route("", methods=["GET"])
@tag(["market-data"])
@operation_id("list_market_data")
async def list_market_data() -> ResponseReturnValue:
    """List market data with optional filtering"""
    try:
        # Get query parameters
        symbol = request.args.get("symbol")
        exchange = request.args.get("exchange")
        data_source = request.args.get("dataSource")
        market_status = request.args.get("marketStatus")

        # Build search conditions
        search_conditions = {}
        if symbol:
            search_conditions["symbol"] = symbol
        if exchange:
            search_conditions["exchange"] = exchange
        if data_source:
            search_conditions["dataSource"] = data_source
        if market_status:
            search_conditions["marketStatus"] = market_status

        if search_conditions:
            builder = SearchConditionRequest.builder()
            for field, value in search_conditions.items():
                builder.equals(field, value)
            condition = builder.build()

            entities = await service.search(
                entity_class=MarketData.ENTITY_NAME,
                condition=condition,
                entity_version=str(MarketData.ENTITY_VERSION),
            )
        else:
            entities = await service.find_all(
                entity_class=MarketData.ENTITY_NAME,
                entity_version=str(MarketData.ENTITY_VERSION),
            )

        entity_list = [_to_entity_dict(r.data) for r in entities]
        return {"marketData": entity_list, "total": len(entity_list)}, 200

    except Exception as e:
        logger.exception("Error listing market data: %s", str(e))
        return {"error": str(e)}, 500

@market_data_bp.route("/<symbol>/latest", methods=["GET"])
@tag(["market-data"])
@operation_id("get_latest_market_data")
async def get_latest_market_data(symbol: str) -> ResponseReturnValue:
    """Get the latest market data for a symbol"""
    try:
        builder = SearchConditionRequest.builder()
        builder.equals("symbol", symbol)
        condition = builder.build()

        entities = await service.search(
            entity_class=MarketData.ENTITY_NAME,
            condition=condition,
            entity_version=str(MarketData.ENTITY_VERSION),
        )

        if not entities:
            return {"error": "Market data not found", "code": "NOT_FOUND"}, 404

        # Find the most recent entry
        latest_data = None
        latest_timestamp = None
        
        for entity in entities:
            data = _to_entity_dict(entity.data)
            timestamp = data.get("marketTimestamp")
            if not latest_timestamp or (timestamp and timestamp > latest_timestamp):
                latest_timestamp = timestamp
                latest_data = data

        if not latest_data:
            return {"error": "No valid market data found", "code": "NOT_FOUND"}, 404

        return latest_data, 200

    except Exception as e:
        logger.exception("Error getting latest market data for %s: %s", symbol, str(e))
        return {"error": str(e)}, 500

@market_data_bp.route("/<data_id>/validate", methods=["POST"])
@tag(["market-data"])
@operation_id("validate_market_data")
async def validate_market_data(data_id: str) -> ResponseReturnValue:
    """Validate market data quality"""
    try:
        response = await service.execute_transition(
            entity_id=data_id,
            transition="validate",
            entity_class=MarketData.ENTITY_NAME,
            entity_version=str(MarketData.ENTITY_VERSION),
        )

        logger.info("Validated market data %s", data_id)
        return {
            "id": response.metadata.id,
            "message": "Market data validated successfully",
            "newState": response.metadata.state,
        }, 200

    except Exception as e:
        logger.exception("Error validating market data %s: %s", data_id, str(e))
        return {"error": str(e)}, 500

@market_data_bp.route("/bulk", methods=["POST"])
@tag(["market-data"])
@operation_id("publish_bulk_market_data")
async def publish_bulk_market_data() -> ResponseReturnValue:
    """Publish multiple market data entries in bulk"""
    try:
        data = await request.get_json()
        
        if not isinstance(data, list):
            return {"error": "Expected array of market data entries", "code": "INVALID_FORMAT"}, 400

        results = []
        errors = []

        for i, entry in enumerate(data):
            try:
                # Create MarketData entity
                market_data = MarketData(**entry)
                entity_data = market_data.model_dump(by_alias=True)

                # Save the market data
                response = await service.save(
                    entity=entity_data,
                    entity_class=MarketData.ENTITY_NAME,
                    entity_version=str(MarketData.ENTITY_VERSION),
                )

                results.append({
                    "index": i,
                    "id": response.metadata.id,
                    "symbol": entry.get("symbol"),
                    "status": "success"
                })

            except Exception as e:
                errors.append({
                    "index": i,
                    "symbol": entry.get("symbol", "unknown"),
                    "error": str(e)
                })

        logger.info("Bulk published %d market data entries, %d errors", len(results), len(errors))
        
        return {
            "successful": len(results),
            "failed": len(errors),
            "results": results,
            "errors": errors
        }, 200 if not errors else 207  # 207 Multi-Status for partial success

    except Exception as e:
        logger.exception("Error in bulk market data publish: %s", str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500
