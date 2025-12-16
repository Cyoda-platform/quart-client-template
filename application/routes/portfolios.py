"""
Portfolio management API routes for the trading platform.

Provides REST endpoints for Portfolio CRUD operations.
"""

import logging
from typing import Any, Dict

from quart import Blueprint
from quart_schema import validate_request, validate_response

from application.entity.portfolio.version_1.portfolio import Portfolio
from services.services import get_entity_service

logger = logging.getLogger(__name__)

portfolios_bp = Blueprint("portfolios", __name__, url_prefix="/api/portfolios")


@portfolios_bp.route("", methods=["POST"])
@validate_request(Portfolio)
@validate_response(Portfolio, status_code=201)
async def create_portfolio(data: Portfolio) -> tuple[Dict[str, Any], int]:
    """Create a new Portfolio."""
    try:
        entity_service = get_entity_service()
        portfolio_data = data.model_dump(by_alias=True)
        response = await entity_service.save(
            entity=portfolio_data,
            entity_class=Portfolio.ENTITY_NAME,
            entity_version=str(Portfolio.ENTITY_VERSION),
        )
        portfolio_data["id"] = response.metadata.id
        portfolio_data["state"] = response.metadata.state
        logger.info(f"Portfolio created: {response.metadata.id}")
        return portfolio_data, 201
    except Exception as e:
        logger.error(f"Failed to create Portfolio: {str(e)}")
        return {"error": str(e)}, 400


@portfolios_bp.route("/<portfolio_id>", methods=["GET"])
async def get_portfolio(portfolio_id: str) -> tuple[Dict[str, Any], int]:
    """Get Portfolio by technical ID."""
    try:
        entity_service = get_entity_service()
        response = await entity_service.get_by_id(
            entity_id=portfolio_id,
            entity_class=Portfolio.ENTITY_NAME,
            entity_version=str(Portfolio.ENTITY_VERSION),
        )
        if response is None:
            return {"error": "Portfolio not found"}, 404
        portfolio_data = response.entity.model_dump(by_alias=True)
        portfolio_data["id"] = response.metadata.id
        portfolio_data["state"] = response.metadata.state
        return portfolio_data, 200
    except Exception as e:
        logger.error(f"Failed to get Portfolio: {str(e)}")
        return {"error": str(e)}, 404


@portfolios_bp.route("/<portfolio_id>", methods=["PUT"])
@validate_request(Portfolio)
async def update_portfolio(
    portfolio_id: str, data: Portfolio
) -> tuple[Dict[str, Any], int]:
    """Update a Portfolio."""
    try:
        entity_service = get_entity_service()
        portfolio_data = data.model_dump(by_alias=True)
        response = await entity_service.update(
            entity=portfolio_data,
            entity_class=Portfolio.ENTITY_NAME,
            entity_version=str(Portfolio.ENTITY_VERSION),
        )
        portfolio_data["id"] = response.metadata.id
        portfolio_data["state"] = response.metadata.state
        logger.info(f"Portfolio updated: {portfolio_id}")
        return portfolio_data, 200
    except Exception as e:
        logger.error(f"Failed to update Portfolio: {str(e)}")
        return {"error": str(e)}, 400


@portfolios_bp.route("/<portfolio_id>", methods=["DELETE"])
async def delete_portfolio(portfolio_id: str) -> tuple[Dict[str, str], int]:
    """Delete a Portfolio."""
    try:
        entity_service = get_entity_service()
        await entity_service.delete_by_id(
            entity_id=portfolio_id,
            entity_class=Portfolio.ENTITY_NAME,
            entity_version=str(Portfolio.ENTITY_VERSION),
        )
        logger.info(f"Portfolio deleted: {portfolio_id}")
        return {"message": "Portfolio deleted successfully"}, 200
    except Exception as e:
        logger.error(f"Failed to delete Portfolio: {str(e)}")
        return {"error": str(e)}, 400
