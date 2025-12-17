from quart import Blueprint, request, jsonify
from common.service.service import get_entity_service
from application.entity.position.version_1.position import Position

position_routes = Blueprint('position_routes', __name__, url_prefix='/api/positions')

@position_routes.route('/', methods=['POST'])
async def create_position():
    """
    Creates a new position.
    """
    data = await request.get_json()
    entity_service = get_entity_service()
    position = await entity_service.create(Position.ENTITY_NAME, Position.ENTITY_VERSION, data)
    return jsonify(position.to_dict()), 201

@position_routes.route('/<entity_id>', methods=['GET'])
async def get_position(entity_id: str):
    """
    Retrieves a position by its ID.
    """
    entity_service = get_entity_service()
    position = await entity_service.get(entity_id)
    return jsonify(position.to_dict())

@position_routes.route('/<entity_id>', methods=['PUT'])
async def update_position(entity_id: str):
    """
    Updates a position by applying a transition.
    """
    data = await request.get_json()
    transition = data.get('transition')
    if not transition:
        return jsonify({"error": "transition is required"}), 400

    entity_service = get_entity_service()
    position = await entity_service.update(entity_id, transition)
    return jsonify(position.to_dict())
