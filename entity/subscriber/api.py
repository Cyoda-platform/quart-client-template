from quart import Blueprint, request, jsonify
from app_init.app_init import entity_service, cyoda_token
from common.config.config import ENTITY_VERSION
import uuid
import asyncio

api_bp_subscriber = Blueprint('api/subscriber', __name__)

ENTITY_MODEL = 'subscriber'

@api_bp_subscriber.route('/subscribers', methods=['POST'])
async def add_subscriber():
    """Create a new subscriber."""
    data = await request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400
    try:
        subscriber_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model=ENTITY_MODEL,
            entity_version=ENTITY_VERSION,
            entity=data
        )
        return jsonify({'subscriber_id': subscriber_id}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp_subscriber.route('/subscribers/<int:subscriber_id>', methods=['GET'])
async def get_subscriber_id(subscriber_id):
    """Retrieve subscriber information."""
    try:
        data = await entity_service.get_item(
            token=cyoda_token,
            entity_model=ENTITY_MODEL,
            entity_version=ENTITY_VERSION,
            technical_id=subscriber_id
        )
        return jsonify({"data": data}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
