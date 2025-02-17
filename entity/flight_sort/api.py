# ```python
from quart import Blueprint, request, jsonify
from app_init.app_init import entity_service, cyoda_token
from common.config.config import ENTITY_VERSION

api_bp_flight_sort = Blueprint('api/flight_sort', __name__)

@api_bp_flight_sort.route('/flights/sort', methods=['GET'])
async def sort_flights():
    """API endpoint to sort the available flights based on specified criteria."""
    criteria = request.args.get('criteria')
    if not criteria:
        return jsonify({"error": "No sorting criteria provided"}), 400

    try:
        # Retrieve the available flights using the entity service
        flights_data = await entity_service.get_item(
            token=cyoda_token, entity_model='flights', entity_version=ENTITY_VERSION, id='all_flights'
        )
        
        # Sort the flights based on the specified criteria
        sorted_flights = sorted(flights_data, key=lambda x: x.get(criteria))

        return jsonify({"sorted_flights": sorted_flights}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
# ```