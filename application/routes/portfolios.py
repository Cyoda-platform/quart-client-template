"""
Portfolio Routes for Trading Platform

Manages all Portfolio-related API endpoints including portfolio queries,
performance tracking, and risk metrics.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from quart import Blueprint, jsonify, request
from quart.typing import ResponseReturnValue
from quart_schema import operation_id, tag

from common.service.entity_service import SearchConditionRequest
from services.services import get_entity_service
from application.entity.portfolio.version_1.portfolio import Portfolio

logger = logging.getLogger(__name__)

# Service proxy
class _ServiceProxy:
    def __getattr__(self, name: str) -> Any:
        return getattr(get_entity_service(), name)

service = _ServiceProxy()

def _to_entity_dict(data: Any) -> Dict[str, Any]:
    return data.model_dump(by_alias=True) if hasattr(data, "model_dump") else data

portfolios_bp = Blueprint("portfolios", __name__, url_prefix="/api/portfolios")

@portfolios_bp.route("", methods=["POST"])
@tag(["portfolios"])
@operation_id("create_portfolio")
async def create_portfolio() -> ResponseReturnValue:
    """Create a new portfolio"""
    try:
        data = await request.get_json()
        
        # Create Portfolio entity
        portfolio = Portfolio(**data)
        entity_data = portfolio.model_dump(by_alias=True)

        # Save the portfolio
        response = await service.save(
            entity=entity_data,
            entity_class=Portfolio.ENTITY_NAME,
            entity_version=str(Portfolio.ENTITY_VERSION),
        )

        logger.info("Created Portfolio with ID: %s", response.metadata.id)
        return _to_entity_dict(response.data), 201

    except ValueError as e:
        logger.warning("Validation error creating portfolio: %s", str(e))
        return {"error": str(e), "code": "VALIDATION_ERROR"}, 400
    except Exception as e:
        logger.exception("Error creating portfolio: %s", str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500

@portfolios_bp.route("/<portfolio_id>", methods=["GET"])
@tag(["portfolios"])
@operation_id("get_portfolio")
async def get_portfolio(portfolio_id: str) -> ResponseReturnValue:
    """Get portfolio by ID"""
    try:
        response = await service.get_by_id(
            entity_id=portfolio_id,
            entity_class=Portfolio.ENTITY_NAME,
            entity_version=str(Portfolio.ENTITY_VERSION),
        )

        if not response:
            return {"error": "Portfolio not found", "code": "NOT_FOUND"}, 404

        return _to_entity_dict(response.data), 200

    except Exception as e:
        logger.exception("Error getting portfolio %s: %s", portfolio_id, str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500

@portfolios_bp.route("/by-client/<client_id>", methods=["GET"])
@tag(["portfolios"])
@operation_id("get_portfolios_by_client")
async def get_portfolios_by_client(client_id: str) -> ResponseReturnValue:
    """Get all portfolios for a specific client"""
    try:
        builder = SearchConditionRequest.builder()
        builder.equals("clientId", client_id)
        condition = builder.build()

        entities = await service.search(
            entity_class=Portfolio.ENTITY_NAME,
            condition=condition,
            entity_version=str(Portfolio.ENTITY_VERSION),
        )

        entity_list = [_to_entity_dict(r.data) for r in entities]
        return {"portfolios": entity_list, "total": len(entity_list)}, 200

    except Exception as e:
        logger.exception("Error getting portfolios for client %s: %s", client_id, str(e))
        return {"error": str(e)}, 500

@portfolios_bp.route("/<portfolio_id>/calculate", methods=["POST"])
@tag(["portfolios"])
@operation_id("calculate_portfolio")
async def calculate_portfolio(portfolio_id: str) -> ResponseReturnValue:
    """Trigger portfolio calculation"""
    try:
        response = await service.execute_transition(
            entity_id=portfolio_id,
            transition="calculate",
            entity_class=Portfolio.ENTITY_NAME,
            entity_version=str(Portfolio.ENTITY_VERSION),
        )

        logger.info("Calculated portfolio %s", portfolio_id)
        return {
            "id": response.metadata.id,
            "message": "Portfolio calculated successfully",
            "newState": response.metadata.state,
        }, 200

    except Exception as e:
        logger.exception("Error calculating portfolio %s: %s", portfolio_id, str(e))
        return {"error": str(e)}, 500

@portfolios_bp.route("/<portfolio_id>/performance", methods=["GET"])
@tag(["portfolios"])
@operation_id("get_portfolio_performance")
async def get_portfolio_performance(portfolio_id: str) -> ResponseReturnValue:
    """Get portfolio performance metrics"""
    try:
        response = await service.get_by_id(
            entity_id=portfolio_id,
            entity_class=Portfolio.ENTITY_NAME,
            entity_version=str(Portfolio.ENTITY_VERSION),
        )

        if not response:
            return {"error": "Portfolio not found", "code": "NOT_FOUND"}, 404

        portfolio_data = _to_entity_dict(response.data)
        
        # Extract performance metrics
        performance = {
            "totalValue": portfolio_data.get("totalValue"),
            "dailyPnl": portfolio_data.get("dailyPnl"),
            "totalPnl": portfolio_data.get("totalPnl"),
            "unrealizedPnl": portfolio_data.get("unrealizedPnl"),
            "realizedPnl": portfolio_data.get("realizedPnl"),
            "var95": portfolio_data.get("var95"),
            "beta": portfolio_data.get("beta"),
            "sharpeRatio": portfolio_data.get("sharpeRatio"),
            "maxDrawdown": portfolio_data.get("maxDrawdown"),
            "lastUpdated": portfolio_data.get("lastUpdated"),
        }

        return {"portfolioId": portfolio_id, "performance": performance}, 200

    except Exception as e:
        logger.exception("Error getting portfolio performance %s: %s", portfolio_id, str(e))
        return {"error": str(e)}, 500

@portfolios_bp.route("", methods=["GET"])
@tag(["portfolios"])
@operation_id("list_portfolios")
async def list_portfolios() -> ResponseReturnValue:
    """List all portfolios"""
    try:
        entities = await service.find_all(
            entity_class=Portfolio.ENTITY_NAME,
            entity_version=str(Portfolio.ENTITY_VERSION),
        )

        entity_list = [_to_entity_dict(r.data) for r in entities]
        return {"portfolios": entity_list, "total": len(entity_list)}, 200

    except Exception as e:
        logger.exception("Error listing portfolios: %s", str(e))
        return {"error": str(e)}, 500
