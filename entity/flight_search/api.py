from quart import Blueprint, request, jsonify
from app_init.app_init import entity_service, cyoda_token
from common.config.config import ENTITY_VERSION
import uuid
import asyncio

api_bp_flight_search = Blueprint('api/flight_search', __name__)

ENTITY_MODEL = 'flight_search'

@api_bp_flight_search.route('/flights/search', methods=['POST'])
async def add_flight_search():
    """Create a new flight_search."""
    data = await request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400
    try:
        flight_search_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model=ENTITY_MODEL,
            entity_version=ENTITY_VERSION,
            entity=data
        )
        return jsonify({'flight_search_id': flight_search_id}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp_flight_search.route('/flight_search/<id>', methods=['GET'])
async def get_id(id):
    """Retrieve a flight_search by ID."""
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

@api_bp_flight_search.route('/flight_searches', methods=['GET'])
async def get_flight_searchs():
    """Retrieve all flight_searches entries."""
    try:
        data = await entity_service.get_items(
            token=cyoda_token,
            entity_model=ENTITY_MODEL,
            entity_version=ENTITY_VERSION
        )
        return jsonify({"data": data}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
