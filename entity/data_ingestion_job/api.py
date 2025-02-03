from quart import Blueprint, jsonify, request
from app_init.app_init import entity_service
from common.config.config import ENTITY_VERSION
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

api_bp = Blueprint('api', __name__)


@api_bp.route('/')
async def home():
    return 'Welcome to the main app!'

@api_bp.route('/data_ingestion_job', methods=['POST'])
async def save_data_ingestion_job():
    data = await request.json
    try:
        job_id = data.get("job_id")
        job_name = data.get("job_name")
        scheduled_time = data.get("scheduled_time")
        status = data.get("status")
        start_time = data.get("start_time")
        end_time = data.get("end_time")
        total_records_processed = data.get("total_records_processed")
        successful_records = data.get("successful_records")
        failed_records = data.get("failed_records")
        failure_reason = data.get("failure_reason", [])
        
        # Building the entity for saving
        entity_data = {
            "job_id": job_id,
            "job_name": job_name,
            "scheduled_time": scheduled_time,
            "status": status,
            "start_time": start_time,
            "end_time": end_time,
            "total_records_processed": total_records_processed,
            "successful_records": successful_records,
            "failed_records": failed_records,
            "failure_reason": failure_reason
        }

        # Save the entity
        saved_entity_id = await entity_service.add_item(
            request.headers.get("token"), "data_ingestion_job", ENTITY_VERSION, entity_data
        )
        return jsonify({"message": "Data ingestion job saved successfully.", "entity_id": saved_entity_id}), 201

    except Exception as e:
        logger.error(f"Error saving data ingestion job: {e}")
        return jsonify({"error": str(e)}), 500
