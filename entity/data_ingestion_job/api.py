# ```python
import logging
from quart import Blueprint, request
from app_init.app_init import entity_service, cyoda_token
from common.config.config import ENTITY_VERSION

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

api_bp_data_ingestion_job = Blueprint('api_data_ingestion_job', __name__)

@api_bp_data_ingestion_job.route('/add', methods=['POST'])
async def add_data_ingestion_job():
    """API endpoint to add the data ingestion job entity."""
    try:
        job_data = await request.get_json()
        job_id = await entity_service.add_item(
            cyoda_token,
            "data_ingestion_job",
            ENTITY_VERSION,
            {
                "job_id": job_data["job_id"],
                "name": job_data["name"],
                "scheduled_time": job_data["scheduled_time"],
                "status": job_data["status"],
                "raw_data_entity": job_data["raw_data_entity"]
            }
        )
        return {"job_id": job_id}, 201
    except Exception as e:
        logger.error(f"Error adding data ingestion job: {e}")
        return {"error": "Failed to add data ingestion job."}, 500
# ```