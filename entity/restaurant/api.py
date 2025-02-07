# Here’s an example of an `api.py` file for the Quart application that implements an API endpoint to save the **Restaurant** entity. The code uses a Blueprint for organization and handles incoming requests to save restaurant details.
# 
# ```python
from quart import Blueprint, request, jsonify
from app_init.app_init import entity_service
from common.config.config import ENTITY_VERSION, CYODA_TOKEN

api_bp_restaurant = Blueprint('api/restaurant', __name__)

@api_bp_restaurant.route('/restaurant', methods=['POST'])
async def create_restaurant():
    """API endpoint to create a new restaurant entity."""
    data = await request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    try:
        # Add the restaurant entity using the entity service
        restaurant_id = await entity_service.add_item(
            CYODA_TOKEN, "restaurant", ENTITY_VERSION, data
        )
        return jsonify({"restaurant_id": restaurant_id}), 201
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500
# ```
# 
# ### Explanation:
# - **Blueprint**: The `api_bp_restaurant` Blueprint organizes the restaurant-related API routes.
# - **Endpoint**: The `/restaurant` POST endpoint allows clients to send restaurant data as JSON.
# - **Entity Saving**: The endpoint uses `entity_service.add_item` to save the restaurant entity, utilizing the constant `CYODA_TOKEN` for the token and `ENTITY_VERSION` for the version.
# - **Error Handling**: The API handles errors and returns appropriate HTTP status codes.
# 
# Let me know if you have any modifications or further questions!