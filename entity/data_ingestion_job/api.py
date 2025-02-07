# ```python
import logging
from quart import Blueprint, request
from app_init.app_init import entity_service
from common.config.config import ENTITY_VERSION, cyoda_token

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

api_bp_data_ingestion_job = Blueprint('api/data_ingestion_job', __name__)

@api_bp_data_ingestion_job.route('/add', methods=['POST'])
async def add_data_ingestion_job():
    """API endpoint to add the data ingestion job entity."""
    try:
        data = await request.get_json()
        job_id = f"job_{data['job_sequence_id']}"
        data_ingestion_job = {
            "job_id": job_id,
            "job_name": "Data Ingestion Job for Products",
            "scheduled_time": data["scheduled_time"],
            "status": "pending",
            "total_records_processed": 0,
            "successful_records": 0,
            "failed_records": 0,
            "request_parameters": {
                "api_url": "https://automationexercise.com/api/productsList",
                "request_method": "GET"
            }
        }
        data_ingestion_job_id = await entity_service.add_item(
            cyoda_token,
            "data_ingestion_job",
            ENTITY_VERSION,
            data_ingestion_job
        )
        logger.info(f"Data ingestion job added successfully with ID: {data_ingestion_job_id}")
        return {"technical_id": data_ingestion_job_id}, 201
    except Exception as e:
        logger.error(f"Error adding data ingestion job: {e}")
        return {"error": str(e)}, 500
# ```