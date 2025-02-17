from quart import Blueprint, request, jsonify
from app_init.app_init import entity_service, cyoda_token
from common.config.config import ENTITY_VERSION
import uuid
import asyncio

api_bp_api = Blueprint('api/api', __name__)

ENTITY_MODEL = 'api'

@api_bp_api.route('/api/flights/search', methods=['POST'])
async def add_api():
    """Create a new api."""
    data = await request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400
    try:
        api_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model=ENTITY_MODEL,
            entity_version=ENTITY_VERSION,
            entity=data
        )
        return jsonify({'api_id': api_id}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp_api.route('/api/flights/filter', methods=['POST'])
async def add_api():
    """Create a new api."""
    data = await request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400
    try:
        api_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model=ENTITY_MODEL,
            entity_version=ENTITY_VERSION,
            entity=data
        )
        return jsonify({'api_id': api_id}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp_api.route('/api/<id>', methods=['GET'])
async def get_id(id):
    """Retrieve a api by ID."""
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

@api_bp_api.route('/apis', methods=['GET'])
async def get_apis():
    """Retrieve all apis entries."""
    try:
        data = await entity_service.get_items(
            token=cyoda_token,
            entity_model=ENTITY_MODEL,
            entity_version=ENTITY_VERSION
        )
        return jsonify({"data": data}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
