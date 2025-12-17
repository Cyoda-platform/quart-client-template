from quart import Blueprint, request, jsonify
from services.services import get_entity_service
from application.entity.portfolio.version_1.portfolio import Portfolio
from typing import Dict, Tuple, Any

portfolio_routes = Blueprint('portfolio_routes', __name__, url_prefix='/api/portfolios')

@portfolio_routes.route('/', methods=['POST'])
async def create_portfolio() -> Tuple[Dict[str, Any], int]:
    """
    Creates a new portfolio.
    """
    data = await request.get_json()
    entity_service = get_entity_service()
    portfolio = await entity_service.save(data, Portfolio.ENTITY_NAME, Portfolio.ENTITY_VERSION)
    return portfolio.data.model_dump(), 201

@portfolio_routes.route('/<entity_id>', methods=['GET'])
async def get_portfolio(entity_id: str) -> Tuple[Dict[str, Any], int]:
    """
    Retrieves a portfolio by its ID.
    """
    entity_service = get_entity_service()
    portfolio = await entity_service.get_by_id(entity_id, Portfolio.ENTITY_NAME, Portfolio.ENTITY_VERSION)
    if portfolio:
        return portfolio.data.model_dump(), 200
    return {}, 404
