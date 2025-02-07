# Here’s an example of an `api.py` file for the Quart application that implements an API endpoint to save the **Order** entity. The code uses a Blueprint for organization and handles incoming requests to save order details.
# 
# ```python
from quart import Blueprint, request, jsonify
from app_init.app_init import entity_service
from common.config.config import ENTITY_VERSION, CYODA_TOKEN

api_bp_order = Blueprint('api/order', __name__)

@api_bp_order.route('/order', methods=['POST'])
async def create_order():
    """API endpoint to create a new order entity."""
    data = await request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    try:
        # Add the order entity using the entity service
        order_id = await entity_service.add_item(
            CYODA_TOKEN, "order", ENTITY_VERSION, data
        )
        return jsonify({"order_id": order_id}), 201
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500
# ```
# 
# ### Explanation:
# - **Blueprint**: The `api_bp_order` Blueprint organizes the order-related API routes.
# - **Endpoint**: The `/order` POST endpoint allows clients to send order data as JSON.
# - **Entity Saving**: The endpoint uses `entity_service.add_item` to save the order entity, utilizing the constant `CYODA_TOKEN` for the token and `ENTITY_VERSION` for the version.
# - **Error Handling**: The API handles errors and returns appropriate HTTP status codes.
# 
# Let me know if you have any modifications or further questions!