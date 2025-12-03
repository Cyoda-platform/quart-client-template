"""
Position Routes for Trading Platform

Manages all Position-related API endpoints including position tracking,
P&L calculations, and risk metrics.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from quart import Blueprint, jsonify, request
from quart.typing import ResponseReturnValue
from quart_schema import operation_id, tag

from common.service.entity_service import SearchConditionRequest
from services.services import get_entity_service
from application.entity.position.version_1.position import Position

logger = logging.getLogger(__name__)

# Service proxy
class _ServiceProxy:
    def __getattr__(self, name: str) -> Any:
        return getattr(get_entity_service(), name)

service = _ServiceProxy()

def _to_entity_dict(data: Any) -> Dict[str, Any]:
    return data.model_dump(by_alias=True) if hasattr(data, "model_dump") else data

positions_bp = Blueprint("positions", __name__, url_prefix="/api/positions")

@positions_bp.route("", methods=["POST"])
@tag(["positions"])
@operation_id("create_position")
async def create_position() -> ResponseReturnValue:
    """Create a new position"""
    try:
        data = await request.get_json()
        
        # Create Position entity
        position = Position(**data)
        entity_data = position.model_dump(by_alias=True)

        # Save the position
        response = await service.save(
            entity=entity_data,
            entity_class=Position.ENTITY_NAME,
            entity_version=str(Position.ENTITY_VERSION),
        )

        logger.info("Created Position with ID: %s", response.metadata.id)
        return _to_entity_dict(response.data), 201

    except ValueError as e:
        logger.warning("Validation error creating position: %s", str(e))
        return {"error": str(e), "code": "VALIDATION_ERROR"}, 400
    except Exception as e:
        logger.exception("Error creating position: %s", str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500

@positions_bp.route("/<position_id>", methods=["GET"])
@tag(["positions"])
@operation_id("get_position")
async def get_position(position_id: str) -> ResponseReturnValue:
    """Get position by ID"""
    try:
        response = await service.get_by_id(
            entity_id=position_id,
            entity_class=Position.ENTITY_NAME,
            entity_version=str(Position.ENTITY_VERSION),
        )

        if not response:
            return {"error": "Position not found", "code": "NOT_FOUND"}, 404

        return _to_entity_dict(response.data), 200

    except Exception as e:
        logger.exception("Error getting position %s: %s", position_id, str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500

@positions_bp.route("/by-portfolio/<portfolio_id>", methods=["GET"])
@tag(["positions"])
@operation_id("get_positions_by_portfolio")
async def get_positions_by_portfolio(portfolio_id: str) -> ResponseReturnValue:
    """Get all positions for a specific portfolio"""
    try:
        builder = SearchConditionRequest.builder()
        builder.equals("portfolioId", portfolio_id)
        condition = builder.build()

        entities = await service.search(
            entity_class=Position.ENTITY_NAME,
            condition=condition,
            entity_version=str(Position.ENTITY_VERSION),
        )

        entity_list = [_to_entity_dict(r.data) for r in entities]
        return {"positions": entity_list, "total": len(entity_list)}, 200

    except Exception as e:
        logger.exception("Error getting positions for portfolio %s: %s", portfolio_id, str(e))
        return {"error": str(e)}, 500

@positions_bp.route("/by-symbol/<symbol>", methods=["GET"])
@tag(["positions"])
@operation_id("get_positions_by_symbol")
async def get_positions_by_symbol(symbol: str) -> ResponseReturnValue:
    """Get all positions for a specific symbol"""
    try:
        builder = SearchConditionRequest.builder()
        builder.equals("symbol", symbol)
        condition = builder.build()

        entities = await service.search(
            entity_class=Position.ENTITY_NAME,
            condition=condition,
            entity_version=str(Position.ENTITY_VERSION),
        )

        entity_list = [_to_entity_dict(r.data) for r in entities]
        return {"positions": entity_list, "total": len(entity_list)}, 200

    except Exception as e:
        logger.exception("Error getting positions for symbol %s: %s", symbol, str(e))
        return {"error": str(e)}, 500

@positions_bp.route("/<position_id>/calculate", methods=["POST"])
@tag(["positions"])
@operation_id("calculate_position")
async def calculate_position(position_id: str) -> ResponseReturnValue:
    """Trigger position calculation"""
    try:
        response = await service.execute_transition(
            entity_id=position_id,
            transition="calculate",
            entity_class=Position.ENTITY_NAME,
            entity_version=str(Position.ENTITY_VERSION),
        )

        logger.info("Calculated position %s", position_id)
        return {
            "id": response.metadata.id,
            "message": "Position calculated successfully",
            "newState": response.metadata.state,
        }, 200

    except Exception as e:
        logger.exception("Error calculating position %s: %s", position_id, str(e))
        return {"error": str(e)}, 500

@positions_bp.route("", methods=["GET"])
@tag(["positions"])
@operation_id("list_positions")
async def list_positions() -> ResponseReturnValue:
    """List positions with optional filtering"""
    try:
        # Get query parameters
        portfolio_id = request.args.get("portfolioId")
        symbol = request.args.get("symbol")
        client_id = request.args.get("clientId")

        # Build search conditions
        search_conditions = {}
        if portfolio_id:
            search_conditions["portfolioId"] = portfolio_id
        if symbol:
            search_conditions["symbol"] = symbol
        if client_id:
            search_conditions["clientId"] = client_id

        if search_conditions:
            builder = SearchConditionRequest.builder()
            for field, value in search_conditions.items():
                builder.equals(field, value)
            condition = builder.build()

            entities = await service.search(
                entity_class=Position.ENTITY_NAME,
                condition=condition,
                entity_version=str(Position.ENTITY_VERSION),
            )
        else:
            entities = await service.find_all(
                entity_class=Position.ENTITY_NAME,
                entity_version=str(Position.ENTITY_VERSION),
            )

        entity_list = [_to_entity_dict(r.data) for r in entities]
        return {"positions": entity_list, "total": len(entity_list)}, 200

    except Exception as e:
        logger.exception("Error listing positions: %s", str(e))
        return {"error": str(e)}, 500
