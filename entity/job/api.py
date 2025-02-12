# Here is the `api.py` file implementing the entity job endpoints based on your requirements:
# 
# ```python
from quart import Blueprint, request, jsonify
from app_init.app_init import entity_service, cyoda_token
from common.config.config import ENTITY_VERSION

api_bp_job = Blueprint('api/job', __name__)

@api_bp_job.route('/job', methods=['POST'])
async def add_job():
    """API endpoint to create a new report for Bitcoin conversion rates."""
    data = await request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400

    try:
        # Add the job entity using the entity service
        job_id = await entity_service.add_item(
            cyoda_token, 'job', ENTITY_VERSION, data
        )
        return jsonify({"job_id": job_id}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp_job.route('/report/<report_id>', methods=['GET'])
async def get_report(report_id):
    """API endpoint to retrieve the report details by report ID."""
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
# - The `add_job` function handles the creation of a new job report for Bitcoin conversion rates. It expects JSON data in the request body and uses the `add_item` method from `entity_service` to create the job.
# - The `get_report` function retrieves the details of a report using its ID. It uses the `get_item` method from `entity_service` to fetch the report details.
# - Both functions handle exceptions and return appropriate JSON responses.