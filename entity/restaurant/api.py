# Here’s an implementation of the `api.py` file for saving the restaurant entity using Quart. This file includes a blueprint for the restaurant API and incorporates the specified constants (`ENTITY_VERSION` and `cyoda_token`).
# 
# ```python
# File: api.py

from quart import Blueprint, request, jsonify
from logic.app_init import entity_service

# Constants
ENTITY_VERSION = "1.0"  # Example entity version, modify as needed
cyoda_token = "your_token_here"  # Replace with your actual token

api_bp_restaurant = Blueprint('api/restaurant', __name__)

@api_bp_restaurant.route('/restaurant', methods=['POST'])
async def save_restaurant():
    data = await request.json
    
    # Validate incoming data (basic validation example)
    if not data or 'restaurant_id' not in data:
        return jsonify({"error": "Invalid restaurant data"}), 400
    
    # Prepare restaurant entity for saving
    restaurant_entity = {
        "restaurantId": data["restaurant_id"],
        "name": data.get("name"),
        "menu": data.get("menu"),
        "location": data.get("location"),
        "contact_info": data.get("contact_info"),
        "opening_hours": data.get("opening_hours"),
        "entityVersion": ENTITY_VERSION,
        "token": cyoda_token  # Include the token for processing
    }
    
    # Save the restaurant entity in the repository
    await entity_service.add_item(restaurant_entity)

    return jsonify({"message": "Restaurant saved successfully", "restaurantId": restaurant_entity["restaurantId"]}), 201
# ```
# 
# ### Explanation
# - **Blueprint**: Created a blueprint named `api_bp_restaurant` for handling restaurant-related API routes.
# - **Route**: Defined a POST endpoint `/restaurant` for saving restaurant data.
# - **Data Validation**: Included basic validation to ensure the `restaurant_id` is provided.
# - **Entity Preparation**: Constructed a restaurant entity using the incoming JSON data and included the constants for entity version and token.
# - **Saving the Entity**: Used `entity_service.add_item` to save the restaurant entity in the repository.
# 
# Feel free to ask if you need further modifications or additional features!