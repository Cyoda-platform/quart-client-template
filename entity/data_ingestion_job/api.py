from app_init.app_init import entity_service, cyoda_token
import logging
from quart import Blueprint, jsonify, request

from common.config.config import ENTITY_VERSION

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

api_bp = Blueprint('api', __name__)


@api_bp.route('/')
async def home():
    return 'Welcome to the main app!'


@api_bp.route('/data_ingestion_job', methods=['POST'])
async def save_data_download_job():
    """Endpoint to save the data_download_job entity."""
    job_data = await request.json
    logger.info("Received data_download_job data: %s", job_data)

    try:
        # Validate incoming data, should include job_id, job_name, etc.
        if "job_id" not in job_data or "job_name" not in job_data:
            return jsonify({"error": "job_id and job_name are required"}), 400

        # Save the data_download_job using the entity service
        job_entity_id = await entity_service.add_item(
            cyoda_token, "data_ingestion_job", ENTITY_VERSION, job_data
        )

        return jsonify({"status": "success", "job_id": job_entity_id}), 201
    except Exception as e:
        logger.error(f"Error saving data_download_job: {e}")
        return jsonify({"error": str(e)}), 500
