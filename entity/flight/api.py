from quart import Blueprint, request, jsonify
from app_init.app_init import entity_service, cyoda_token
from common.config.config import ENTITY_VERSION
import uuid
import asyncio

api_bp_flight = Blueprint('api/flight', __name__)

ENTITY_MODEL = 'flight'

@api_bp_flight.route('/flights/<flight_id>', methods=['GET'])
async def get_flight_id(flight_id):
    """Retrieve flight information."""
    try:
        data = await entity_service.get_item(
            token=cyoda_token,
            entity_model=ENTITY_MODEL,
            entity_version=ENTITY_VERSION,
            technical_id=flight_id
        )
        return jsonify({"data": data}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
