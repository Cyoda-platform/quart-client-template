# Here's the `api.py` file implementing the user entity endpoints as per your request, following the provided template:
# 
# ```python
from quart import Blueprint, request, jsonify
from app_init.app_init import entity_service, cyoda_token
from common.config.config import ENTITY_VERSION

api_bp_user = Blueprint('api/user', __name__)

@api_bp_user.route('/users/create', methods=['POST'])
async def add_user():
    """API endpoint to create a new user."""
    data = await request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400

    try:
        # Add the user entity using the entity service
        user_id = await entity_service.add_item(
            cyoda_token, 'user', ENTITY_VERSION, data
        )
        return jsonify({"user_id": user_id}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp_user.route('/users/', methods=['GET'])
async def get_user():
    """API endpoint to retrieve a user entity."""
    try:
        entity_id = request.args.get('id')
        # Get the user entity using the entity service
        user_data = await entity_service.get_item(
            cyoda_token, 'user', ENTITY_VERSION, entity_id
        )
        return jsonify({"user_data": user_data}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
# ```
# 
# ### Explanation:
# - The `add_user` function handles the creation of a new user by accepting a JSON payload and using the `add_item` method from `entity_service`.
# - The `get_user` function retrieves user data based on the provided ID using the `get_item` method.
# - Both functions handle exceptions and return appropriate HTTP status codes and messages.