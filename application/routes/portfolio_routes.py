from quart import Blueprint, request, jsonify
from common.service.service import get_entity_service
from application.entity.portfolio.version_1.portfolio import Portfolio

portfolio_routes = Blueprint('portfolio_routes', __name__, url_prefix='/api/portfolios')

@portfolio_routes.route('/', methods=['POST'])
async def create_portfolio():
    """
    Creates a new portfolio.
    """
    data = await request.get_json()
    entity_service = get_entity_service()
    portfolio = await entity_service.create(Portfolio.ENTITY_NAME, Portfolio.ENTITY_VERSION, data)
    return jsonify(portfolio.to_dict()), 201

@portfolio_routes.route('/<entity_id>', methods=['GET'])
async def get_portfolio(entity_id: str):
    """
    Retrieves a portfolio by its ID.
    """
    entity_service = get_entity_service()
    portfolio = await entity_service.get(entity_id)
    return jsonify(portfolio.to_dict())
