from quart import Blueprint, request, jsonify
from app_init.app_init import entity_service, cyoda_token
from common.config.config import ENTITY_VERSION
import uuid
import asyncio

api_bp_send_fact = Blueprint('api/send_fact', __name__)

ENTITY_MODEL = 'send_fact'

@api_bp_send_fact.route('/send-facts', methods=['POST'])
async def add_send_fact():
    """Create a new send_fact."""
    data = await request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400
    try:
        send_fact_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model=ENTITY_MODEL,
            entity_version=ENTITY_VERSION,
            entity=data
        )
        return jsonify({'send_fact_id': send_fact_id}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp_send_fact.route('/send_fact/<id>', methods=['GET'])
async def get_id(id):
    """Retrieve a send_fact by ID."""
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

@api_bp_send_fact.route('/send_facts', methods=['GET'])
async def get_send_facts():
    """Retrieve all send_facts entries."""
    try:
        data = await entity_service.get_items(
            token=cyoda_token,
            entity_model=ENTITY_MODEL,
            entity_version=ENTITY_VERSION
        )
        return jsonify({"data": data}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
