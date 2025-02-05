# ```python
import logging
from quart import Blueprint, request, jsonify
from app_init.app_init import entity_service
from common.config.config import ENTITY_VERSION, cyoda_token

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

api_bp_data_ingestion_job = Blueprint('api_data_ingestion_job', __name__)

@api_bp_data_ingestion_job.route('/add', methods=['POST'])
async def add_data_ingestion_job():
    """API endpoint to add the data_ingestion_job entity."""
    try:
        job_data = await request.get_json()
        logger.info(f"Received request to add data_ingestion_job: {job_data}")

        # Add the data ingestion job entity
        job_id = await entity_service.add_item(
            cyoda_token,
            "data_ingestion_job",
            ENTITY_VERSION,
            {
                "job_id": "job_001",
                "name": "data_ingestion_job",
                "status": "pending",
                "scheduled_time": "2023-10-01T10:00:00Z",
                "request_parameters": {
                    "symbol": "BTCUSDT"
                }
            }
        )
        return jsonify({"id": job_id}), 201

    except Exception as e:
        logger.error(f"Error adding data_ingestion_job: {e}")
        return jsonify({"error": "Failed to add data_ingestion_job"}), 500
# ```