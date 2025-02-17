# ```python
from quart import Blueprint, request, jsonify
from app_init.app_init import entity_service, cyoda_token
from common.config.config import ENTITY_VERSION

api_bp_flight_filter = Blueprint('api/flight_filter', __name__)

@api_bp_flight_filter.route('/flights/filter', methods=['GET'])
async def filter_flights():
    """API endpoint to filter the available flights based on specified criteria."""
    criteria = request.args.get('criteria')
    value = request.args.get('value')
    
    if not criteria or not value:
        return jsonify({"error": "Criteria and value must be provided"}), 400

    try:
        # Retrieve the available flights using the entity service
        flights_data = await entity_service.get_item(
            token=cyoda_token, entity_model='flights', entity_version=ENTITY_VERSION, id='all_flights'
        )
        
        # Filter the flights based on the specified criteria
        filtered_flights = [flight for flight in flights_data if flight.get(criteria) == value]

        return jsonify({"filtered_flights": filtered_flights}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
# ```