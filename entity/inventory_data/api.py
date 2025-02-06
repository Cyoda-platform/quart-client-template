# Here’s a `api.py` file for the Quart application that defines an API endpoint to save the `inventory_data` entity. This implementation uses `Blueprint` for organizational purposes.
# 
# ### `api.py`
# 
# ```python
from quart import Blueprint, request, jsonify
from app_init.app_init import entity_service
from common.config.config import ENTITY_VERSION, cyoda_token
import logging

api_bp_inventory_data = Blueprint('api/inventory_data', __name__)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@api_bp_inventory_data.route('/save', methods=['POST'])
async def save_inventory_data():
    """Endpoint to save inventory data."""
    try:
        data = await request.get_json()
        if not data:
            return jsonify({"error": "Invalid input"}), 400

        # Save the inventory data entity
        saved_entity = await entity_service.add_item(cyoda_token, "inventory_data", ENTITY_VERSION, data)
        
        logger.info(f"Inventory data saved with ID: {saved_entity}")
        return jsonify({"message": "Inventory data saved successfully", "id": saved_entity}), 201

    except Exception as e:
        logger.error(f"Error saving inventory data: {e}")
        return jsonify({"error": "Internal server error"}), 500
# ```
# 
# ### Explanation
# 
# - **Blueprint**: The `api_bp_inventory_data` is created as a Blueprint to manage routes related to `inventory_data`.
# - **Route**: The `/save` route listens for POST requests containing the inventory data in JSON format.
# - **Saving Logic**: The function checks for valid data and calls `entity_service.add_item()` to save the inventory data.
# - **Logging and Error Handling**: Logging is implemented for tracking, and error handling provides appropriate responses for different scenarios.
# 
# Feel free to modify or let me know if you need further enhancements!