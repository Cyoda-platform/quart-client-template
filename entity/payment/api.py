# Here’s an example of an `api.py` file for the Quart application that implements an API endpoint to save the **Payment** entity. The code uses a Blueprint for organization and handles incoming requests to save payment details.
# 
# ```python
from quart import Blueprint, request, jsonify
from app_init.app_init import entity_service
from common.config.config import ENTITY_VERSION, CYODA_TOKEN

api_bp_payment = Blueprint('api/payment', __name__)

@api_bp_payment.route('/payment', methods=['POST'])
async def create_payment():
    """API endpoint to create a new payment entity."""
    data = await request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    try:
        # Add the payment entity using the entity service
        payment_id = await entity_service.add_item(
            CYODA_TOKEN, "payment", ENTITY_VERSION, data
        )
        return jsonify({"payment_id": payment_id}), 201
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500
# ```
# 
# ### Explanation:
# - **Blueprint**: The `api_bp_payment` Blueprint organizes the payment-related API routes.
# - **Endpoint**: The `/payment` POST endpoint allows clients to send payment data as JSON. 
# - **Entity Saving**: The endpoint uses `entity_service.add_item` to save the payment entity, utilizing the constant `CYODA_TOKEN` for the token and `ENTITY_VERSION` for the version.
# - **Error Handling**: The API handles errors and returns appropriate HTTP status codes.
# 
# Let me know if you have any modifications or further questions!