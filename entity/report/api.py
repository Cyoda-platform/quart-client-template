# Here is the `api.py` file implementing the entity report endpoint based on your requirements:
# 
# ```python
from quart import Blueprint, request, jsonify
from app_init.app_init import entity_service, cyoda_token
from common.config.config import ENTITY_VERSION

api_bp_report = Blueprint('api/report', __name__)

@api_bp_report.route('/report/<report_id>', methods=['GET'])
async def get_report(report_id):
    """API endpoint to fetch the report by its ID."""
    try:
        # Get the report entity using the entity service
        report_details = await entity_service.get_item(
            cyoda_token, 'report', ENTITY_VERSION, report_id
        )
        return jsonify({"report_details": report_details}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
# ```
# 
# ### Explanation:
# - The `get_report` function is designed to fetch the report details by its ID. It uses the `get_item` method from `entity_service` to retrieve the report.
# - The function handles exceptions and returns appropriate JSON responses, including a successful response with the report details or an error message if something goes wrong.