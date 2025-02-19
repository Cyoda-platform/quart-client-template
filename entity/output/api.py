from quart import Blueprint, request, jsonify
from app_init.app_init import entity_service, cyoda_token
from common.config.config import ENTITY_VERSION
import uuid
import asyncio

api_bp_output = Blueprint('api/output', __name__)

ENTITY_MODEL = 'output'

@api_bp_output.route('/output', methods=['POST'])
async def add_output():
    """Create a new output."""
    data = await request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400
    try:
        output_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model=ENTITY_MODEL,
            entity_version=ENTITY_VERSION,
            entity=data
        )
        return jsonify({'output_id': output_id}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp_output.route('/output/<id>', methods=['GET'])
async def get_id(id):
    """Retrieve a output by ID."""
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

@api_bp_output.route('/outputs', methods=['GET'])
async def get_outputs():
    """Retrieve all outputs entries."""
    try:
        data = await entity_service.get_items(
            token=cyoda_token,
            entity_model=ENTITY_MODEL,
            entity_version=ENTITY_VERSION
        )
        return jsonify({"data": data}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
