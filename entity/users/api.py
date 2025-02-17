from quart import Blueprint, request, jsonify
from app_init.app_init import entity_service, cyoda_token
from common.config.config import ENTITY_VERSION
import uuid
import asyncio

api_bp_users = Blueprint('api/users', __name__)

ENTITY_MODEL = 'users'

@api_bp_users.route('/users/create', methods=['POST'])
async def add_users():
    """Create a new users."""
    data = await request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400
    try:
        users_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model=ENTITY_MODEL,
            entity_version=ENTITY_VERSION,
            entity=data
        )
        return jsonify({'users_id': users_id}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp_users.route('/users/login', methods=['POST'])
async def add_users():
    """Create a new users."""
    data = await request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400
    try:
        users_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model=ENTITY_MODEL,
            entity_version=ENTITY_VERSION,
            entity=data
        )
        return jsonify({'users_id': users_id}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp_users.route('/users/<id>', methods=['GET'])
async def get_id(id):
    """Retrieve a users by ID."""
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

@api_bp_users.route('/user', methods=['GET'])
async def get_userss():
    """Retrieve all user entries."""
    try:
        data = await entity_service.get_items(
            token=cyoda_token,
            entity_model=ENTITY_MODEL,
            entity_version=ENTITY_VERSION
        )
        return jsonify({"data": data}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
