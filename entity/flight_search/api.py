# ```python
from quart import Blueprint, request, jsonify
from app_init.app_init import entity_service, cyoda_token
from common.config.config import ENTITY_VERSION

api_bp_flight_search = Blueprint('api/flight_search', __name__)

@api_bp_flight_search.route('/flights/search', methods=['POST'])
async def search_flights():
    """API endpoint to search for flights between two airports."""
    data = await request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400

    try:
        # Add the flight search entity using the entity service
        flight_search_id = await entity_service.add_item(
            token=cyoda_token, entity_model='flight_search', entity_version=ENTITY_VERSION, entity=data
        )
        return jsonify({"flight_search_id": flight_search_id}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp_flight_search.route('/flights/search', methods=['GET'])
async def get_flight_search():
    """API endpoint to retrieve flight search results."""
    try:
        entity_id = request.args.get('id')
        # Retrieve the flight search entity using the entity service
        data = await entity_service.get_item(
            token=cyoda_token, entity_model='flight_search', entity_version=ENTITY_VERSION, id=entity_id
        )
        return jsonify({"data": data}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
# ```