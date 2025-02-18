from quart import Blueprint, request, jsonify
from app_init.app_init import entity_service, cyoda_token
from common.config.config import ENTITY_VERSION
import uuid
import asyncio

api_bp_flight_filter = Blueprint('api/flight_filter', __name__)

ENTITY_MODEL = 'flight_filter'

@api_bp_flight_filter.route('/flights/filter', methods=['GET'])
async def get_flight_filters():
    """Retrieve flight_filter information."""
    try:
        data = await entity_service.get_items(
            token=cyoda_token,
            entity_model=ENTITY_MODEL,
            entity_version=ENTITY_VERSION
        )
        return jsonify({"data": data}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
