from quart import Blueprint, jsonify
from common.service.service import get_entity_service

trade_routes = Blueprint('trade_routes', __name__, url_prefix='/api/trades')

@trade_routes.route('/<entity_id>', methods=['GET'])
async def get_trade(entity_id: str):
    """
    Retrieves a trade by its ID.
    """
    entity_service = get_entity_service()
    trade = await entity_service.get(entity_id)
    return jsonify(trade.to_dict())
