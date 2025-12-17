from quart import Blueprint, request, jsonify
from common.service.service import get_entity_service
from application.entity.market_data.version_1.market_data import MarketData

market_data_routes = Blueprint('market_data_routes', __name__, url_prefix='/api/market_data')

@market_data_routes.route('/', methods=['POST'])
async def create_market_data():
    """
    Creates a new market data entity.
    """
    data = await request.get_json()
    entity_service = get_entity_service()
    market_data = await entity_service.create(MarketData.ENTITY_NAME, MarketData.ENTITY_VERSION, data)
    return jsonify(market_data.to_dict()), 201

@market_data_routes.route('/<entity_id>', methods=['GET'])
async def get_market_data(entity_id: str):
    """
    Retrieves a market data entity by its ID.
    """
    entity_service = get_entity_service()
    market_data = await entity_service.get(entity_id)
    return jsonify(market_data.to_dict())
