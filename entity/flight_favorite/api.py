from quart import Blueprint, request, jsonify
from app_init.app_init import entity_service, cyoda_token
from common.config.config import ENTITY_VERSION
import uuid
import asyncio

api_bp_flight_favorite = Blueprint('api/flight_favorite', __name__)

ENTITY_MODEL = 'flight_favorite'

@api_bp_flight_favorite.route('/flights/favorites', methods=['POST'])
async def add_flight_favorite():
    """Create a new flight_favorite."""
    data = await request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400
    try:
        flight_favorite_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model=ENTITY_MODEL,
            entity_version=ENTITY_VERSION,
            entity=data
        )
        return jsonify({'flight_favorite_id': flight_favorite_id}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp_flight_favorite.route('/flight_favorite/<id>', methods=['GET'])
async def get_id(id):
    """Retrieve a flight_favorite by ID."""
    try:
        data = await entity_service.get_item(
            token=cyoda_token,
            entity_model=ENTITY_MODEL,
            entity_version=ENTITY_VERSION,
            technical_id=id
        )
        return jsonify({"data": data}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp_flight_favorite.route('/flight_favorites', methods=['GET'])
async def get_flight_favorites():
    """Retrieve all flight_favorites entries."""
    try:
        data = await entity_service.get_items(
            token=cyoda_token,
            entity_model=ENTITY_MODEL,
            entity_version=ENTITY_VERSION
        )
        return jsonify({"data": data}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
