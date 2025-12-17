from quart import Blueprint, request, jsonify
from common.service.service import get_entity_service
from application.entity.order.version_1.order import Order

order_routes = Blueprint('order_routes', __name__, url_prefix='/api/orders')

@order_routes.route('/', methods=['POST'])
async def create_order():
    """
    Creates a new order.
    """
    data = await request.get_json()
    entity_service = get_entity_service()
    order = await entity_service.create(Order.ENTITY_NAME, Order.ENTITY_VERSION, data)
    return jsonify(order.to_dict()), 201

@order_routes.route('/<entity_id>', methods=['GET'])
async def get_order(entity_id: str):
    """
    Retrieves an order by its ID.
    """
    entity_service = get_entity_service()
    order = await entity_service.get(entity_id)
    return jsonify(order.to_dict())

@order_routes.route('/<entity_id>', methods=['PUT'])
async def update_order(entity_id: str):
    """
    Updates an order by applying a transition.
    """
    data = await request.get_json()
    transition = data.get('transition')
    if not transition:
        return jsonify({"error": "transition is required"}), 400

    entity_service = get_entity_service()
    order = await entity_service.update(entity_id, transition)
    return jsonify(order.to_dict())
